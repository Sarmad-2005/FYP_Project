"""
Task Extraction Agent
Extracts project tasks from documents using AI analysis
"""

import chromadb
import re
import json
from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer
from datetime import datetime


class TaskAgent:
    """Agent for extracting and managing project tasks"""
    
    def __init__(self, chroma_manager=None):
        # Use centralized ChromaDB manager or create own if not provided
        if chroma_manager:
            self.chroma_manager = chroma_manager
            self.client = chroma_manager.client
        else:
            # Initialize ChromaDB client for tasks storage
            self.client = chromadb.PersistentClient(path="./chroma_db")
        
        # Initialize embedding model
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Tasks collection name
        self.tasks_collection_name = "project_tasks"
        
        # Create or get tasks collection
        self.tasks_collection = self.client.get_or_create_collection(
            name=self.tasks_collection_name,
            metadata={"description": "Project tasks storage"}
        )
    
    def extract_tasks_from_document(self, project_id: str, document_id: str, 
                                  llm_manager, similarity_threshold: float = 0.20) -> Dict[str, Any]:
        """
        Extract tasks from a specific document
        
        Args:
            project_id (str): Project identifier
            document_id (str): Document identifier
            llm_manager: LLM manager instance
            similarity_threshold (float): Minimum similarity for context retrieval
            
        Returns:
            dict: Success status and extracted tasks
        """
        try:
            # Get document embeddings from existing collection
            document_embeddings = self._get_document_embeddings(project_id, document_id)
            
            if not document_embeddings:
                return {
                    "success": False,
                    "error": "No embeddings found for document",
                    "tasks_count": 0
                }
            
            # Create task extraction query
            task_query = "tasks activities deliverables work items assignments responsibilities"
            query_embedding = self.model.encode([task_query]).tolist()[0]
            
            # Find relevant context using similarity search
            relevant_context = self._find_relevant_context(
                document_embeddings, query_embedding, similarity_threshold
            )
            
            if not relevant_context:
                return {
                    "success": False,
                    "error": "No relevant context found for task extraction",
                    "tasks_count": 0
                }
            
            # Prepare context for LLM
            context_text = self._prepare_context_for_llm(relevant_context)
            
            # Create task extraction prompt
            prompt = self._create_task_prompt(context_text, project_id, document_id)
            
            # Get LLM response
            llm_response = llm_manager.simple_chat(prompt)
            
            if not llm_response.get('success'):
                return {
                    "success": False,
                    "error": f"LLM error: {llm_response.get('error', 'Unknown error')}",
                    "tasks_count": 0
                }
            
            # Parse tasks from LLM response
            tasks = self._parse_tasks_from_response(llm_response['response'])
            
            if not tasks:
                return {
                    "success": False,
                    "error": "No tasks could be parsed from LLM response",
                    "tasks_count": 0
                }
            
            # Store tasks in ChromaDB
            stored_count = self._store_tasks(project_id, document_id, tasks)
            
            return {
                "success": True,
                "tasks_count": stored_count,
                "tasks": tasks,
                "context_used": len(relevant_context)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Task extraction failed: {str(e)}",
                "tasks_count": 0
            }
    
    def _get_document_embeddings(self, project_id: str, document_id: str) -> List[Dict]:
        """Get embeddings from the document's ChromaDB collection"""
        try:
            if hasattr(self, 'chroma_manager'):
                # Use centralized manager
                return self.chroma_manager.get_document_embeddings(project_id, document_id)
            
            # Fallback to individual client
            collection_name = f"p_{project_id[:8]}_d_{document_id[:8]}"
            
            # Get collection
            collection = self.client.get_collection(name=collection_name)
            
            # Get all embeddings
            results = collection.get(include=['embeddings', 'documents', 'metadatas'])
            
            embeddings_data = []
            for i, (embedding, document, metadata) in enumerate(zip(
                results['embeddings'], 
                results['documents'], 
                results['metadatas']
            )):
                embeddings_data.append({
                    'content': document,
                    'embedding': embedding,
                    'metadata': metadata,
                    'id': results['ids'][i]
                })
            
            return embeddings_data
            
        except Exception as e:
            print(f"Error getting document embeddings: {e}")
            return []
    
    def _find_relevant_context(self, embeddings: List[Dict], query_embedding: List[float], 
                             threshold: float) -> List[Dict]:
        """Find embeddings above similarity threshold"""
        relevant_context = []
        
        for embedding_data in embeddings:
            # Calculate cosine similarity
            similarity = self._cosine_similarity(query_embedding, embedding_data['embedding'])
            
            if similarity >= threshold:
                embedding_data['similarity'] = similarity
                relevant_context.append(embedding_data)
        
        # Sort by similarity (highest first)
        relevant_context.sort(key=lambda x: x['similarity'], reverse=True)
        
        return relevant_context
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        import numpy as np
        
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)
        
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def _prepare_context_for_llm(self, relevant_context: List[Dict]) -> str:
        """Prepare context text for LLM processing"""
        context_parts = []
        
        for i, context in enumerate(relevant_context):
            content_type = context['metadata'].get('type', 'unknown')
            content = context['content']
            similarity = context.get('similarity', 0.0)
            
            if content_type == 'table':
                context_parts.append(f"[Table {i+1}] (Similarity: {similarity:.3f})\n{content}")
            else:
                context_parts.append(f"[Text {i+1}] (Similarity: {similarity:.3f})\n{content}")
        
        return "\n\n".join(context_parts)
    
    def _create_task_prompt(self, context: str, project_id: str, document_id: str) -> str:
        """Create prompt for task extraction"""
        return f"""You are analyzing a project document to extract tasks and activities. 

CONTEXT FROM DOCUMENT:
{context}

Please extract project tasks from the above context. Return ONLY a JSON array of task objects, where each task has:
- "task": The task description
- "category": Category (e.g., "Development", "Testing", "Documentation", "Review", "Deployment")
- "priority": Priority level ("High", "Medium", "Low")
- "status": Current status ("Not Started", "In Progress", "Completed", "Blocked")

Format your response as a valid JSON array. Do not include any other text, explanations, or formatting.

Example format:
[
  {{
    "task": "Implement user authentication system",
    "category": "Development", 
    "priority": "High",
    "status": "Not Started"
  }},
  {{
    "task": "Write unit tests for authentication",
    "category": "Testing",
    "priority": "Medium",
    "status": "Not Started"
  }}
]

Extract tasks now:"""
    
    def _parse_tasks_from_response(self, response: str) -> List[Dict]:
        """Parse tasks from LLM response"""
        try:
            # Clean the response
            response = response.strip()
            
            # Remove any markdown formatting
            if response.startswith('```json'):
                response = response[7:]
            if response.endswith('```'):
                response = response[:-3]
            
            # Try to parse JSON
            tasks = json.loads(response)
            
            # Validate structure
            if not isinstance(tasks, list):
                return []
            
            parsed_tasks = []
            for task in tasks:
                if isinstance(task, dict) and 'task' in task:
                    parsed_tasks.append({
                        'task': task.get('task', ''),
                        'category': task.get('category', 'General'),
                        'priority': task.get('priority', 'Medium'),
                        'status': task.get('status', 'Not Started')
                    })
            
            return parsed_tasks
            
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {e}")
            # Fallback: try to extract tasks using regex
            return self._extract_tasks_with_regex(response)
        except Exception as e:
            print(f"Error parsing tasks: {e}")
            return []
    
    def _extract_tasks_with_regex(self, response: str) -> List[Dict]:
        """Fallback method to extract tasks using regex"""
        tasks = []
        
        # Look for bullet points or numbered lists
        lines = response.split('\n')
        
        for line in lines:
            line = line.strip()
            if line and (line.startswith('-') or line.startswith('•') or line.startswith('*')):
                task_text = line[1:].strip()
                if task_text:
                    tasks.append({
                        'task': task_text,
                        'category': 'General',
                        'priority': 'Medium',
                        'status': 'Not Started'
                    })
        
        return tasks
    
    def _store_tasks(self, project_id: str, document_id: str, tasks: List[Dict]) -> int:
        """Store tasks in ChromaDB"""
        try:
            stored_count = 0
            
            for i, task in enumerate(tasks):
                # Create unique ID for task
                task_id = f"task_{project_id}_{document_id}_{i}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                task['id'] = task_id
                
                # Create embedding for task text
                task_text = task['task']
                embedding = self.model.encode([task_text]).tolist()[0]
                
                # Prepare metadata
                metadata = {
                    'project_id': project_id,
                    'document_id': document_id,
                    'task_text': task_text,
                    'category': task['category'],
                    'priority': task['priority'],
                    'status': task['status'],
                    'created_at': datetime.now().isoformat(),
                    'source_document': document_id
                }
                
                # Store in ChromaDB
                self.tasks_collection.add(
                    embeddings=[embedding],
                    documents=[task_text],
                    metadatas=[metadata],
                    ids=[task_id]
                )
                
                stored_count += 1
            
            return stored_count
            
        except Exception as e:
            print(f"Error storing tasks: {e}")
            return 0
    
    def get_project_tasks(self, project_id: str) -> List[Dict]:
        """Get all tasks for a project (excludes suggestions)"""
        try:
            # Query tasks collection
            results = self.tasks_collection.query(
                query_embeddings=[[0.0] * 384],  # Dummy query
                where={"project_id": project_id},
                n_results=1000  # Get all tasks for project
            )
            
            tasks = []
            for i, (task_text, metadata) in enumerate(zip(
                results['documents'][0], 
                results['metadatas'][0]
            )):
                # Skip suggestions (only include actual tasks)
                if metadata.get('type') == 'task_suggestion':
                    continue
                    
                tasks.append({
                    'id': results['ids'][0][i],
                    'task': task_text,
                    'category': metadata.get('category', 'General'),
                    'priority': metadata.get('priority', 'Medium'),
                    'status': metadata.get('status', 'Not Started'),
                    'created_at': metadata.get('created_at', ''),
                    'source_document': metadata.get('source_document', ''),
                    'completion_status': metadata.get('completion_status', 0),
                    'final_completion_status': metadata.get('final_completion_status', 0),
                    'completion_percentage': metadata.get('completion_percentage', 0.0)
                })
            
            return tasks
            
        except Exception as e:
            print(f"Error getting project tasks: {e}")
            return []
    
    def extract_task_details(self, project_id: str, task_text: str, 
                           llm_manager, similarity_threshold: float = 0.20) -> Dict[str, Any]:
        """
        Extract detailed information for a specific task across all project documents
        
        Args:
            project_id (str): Project identifier
            task_text (str): Task to analyze
            llm_manager: LLM manager instance
            similarity_threshold (float): Minimum similarity for context retrieval
            
        Returns:
            dict: Success status and task details
        """
        try:
            # Get all tasks for this project to find relevant context
            all_tasks = self.get_project_tasks(project_id)
            
            # Find tasks with similar text (for cross-document analysis)
            relevant_tasks = []
            for task in all_tasks:
                if task_text.lower() in task.get('task', '').lower():
                    relevant_tasks.append(task)
            
            if not relevant_tasks:
                return {
                    "success": False,
                    "error": "No relevant tasks found for details extraction"
                }
            
            # Prepare context from relevant tasks
            context_text = ""
            for task in relevant_tasks:
                context_text += f"Task: {task.get('task', '')}\n"
                context_text += f"Category: {task.get('category', '')}\n"
                context_text += f"Priority: {task.get('priority', '')}\n"
                context_text += f"Status: {task.get('status', '')}\n"
                context_text += f"Source Document: {task.get('source_document', '')}\n\n"
            
            # Create detailed analysis prompt
            prompt = f"""
            Analyze the following task and provide detailed information:
            
            Task: {task_text}
            
            Context from project documents:
            {context_text}
            
            Please provide detailed analysis including:
            1. Task description and scope
            2. Key deliverables
            3. Dependencies and prerequisites
            4. Success criteria
            5. Timeline and milestones
            6. Resource requirements
            7. Risk factors and mitigation
            8. Progress indicators
            
            Format your response as structured details that can be parsed.
            """
            
            # Get LLM response
            llm_response = llm_manager.simple_chat(prompt)
            
            # Parse details from response
            details = self._parse_task_details_from_response(llm_response)
            
            return {
                "success": True,
                "details": details,
                "source_documents": [t.get('source_document', '') for t in relevant_tasks]
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Task details extraction failed: {str(e)}"
            }
    
    def _parse_task_details_from_response(self, response: Dict[str, Any]) -> str:
        """Parse task details from LLM response"""
        try:
            # simple_chat returns a dict like {"response": "...", "success": True}
            if isinstance(response, dict):
                if 'error' in response:
                    return f"Error: {response['error']}"
                if 'response' in response:
                    return response['response'].strip()
                # Fallback if dict structure is different
                return str(response)
            # If it's already a string
            return response.strip()
        except Exception as e:
            return f"Error parsing task details: {str(e)}"
    
    def generate_task_suggestions(self, project_id: str, tasks: List[Dict], 
                                llm_manager, similarity_threshold: float = 0.20) -> Dict[str, Any]:
        """
        Generate suggestions for tasks based on extracted data
        
        Args:
            project_id (str): Project identifier
            tasks (List[Dict]): List of extracted tasks
            llm_manager: LLM manager instance
            similarity_threshold (float): Minimum similarity for context retrieval
            
        Returns:
            dict: Success status and generated suggestions
        """
        try:
            if not tasks:
                return {
                    "success": False,
                    "error": "No tasks available for suggestion generation",
                    "suggestions": []
                }
            
            # Prepare context from tasks
            context_text = ""
            for task in tasks:
                context_text += f"Task: {task.get('task', '')}\n"
                context_text += f"Category: {task.get('category', '')}\n"
                context_text += f"Priority: {task.get('priority', '')}\n"
                context_text += f"Status: {task.get('status', '')}\n\n"
            
            # Create suggestion generation prompt
            prompt = f"""
            Based on the following project tasks, generate actionable suggestions for task management and project improvement:
            
            TASKS:
            {context_text}
            
            Please provide suggestions for:
            1. Task prioritization and sequencing
            2. Resource allocation and assignment
            3. Timeline optimization and scheduling
            4. Risk mitigation and contingency planning
            5. Quality assurance and testing strategies
            6. Communication and collaboration improvements
            7. Automation opportunities
            8. Performance monitoring and tracking
            
            Format your response as a JSON array of suggestion objects, where each suggestion has:
            - "suggestion": The suggestion text
            - "category": Category (e.g., "Planning", "Resource", "Timeline", "Risk", "Quality", "Communication", "Automation", "Monitoring")
            - "priority": Priority level ("High", "Medium", "Low")
            - "source": Source ("AI Analysis")
            
            Return ONLY a valid JSON array. Do not include any other text.
            """
            
            # Get LLM response
            llm_response = llm_manager.simple_chat(prompt)
            
            # Check if LLM call was successful
            if not llm_response.get('success'):
                return {
                    "success": False,
                    "error": f"LLM call failed: {llm_response.get('error', 'Unknown error')}",
                    "suggestions": []
                }
            
            # Extract response text from dictionary
            response_text = llm_response.get('response', '')
            
            # Debug: Log LLM response
            print(f"   📄 LLM Response (first 500 chars): {response_text[:500]}")
            
            # Parse suggestions from response text
            suggestions = self._parse_suggestions_from_response(response_text)
            
            # Filter out empty suggestions
            valid_suggestions = [s for s in suggestions if s.get('suggestion', '').strip()]
            
            if len(valid_suggestions) < len(suggestions):
                print(f"   ⚠️  Filtered out {len(suggestions) - len(valid_suggestions)} empty suggestions")
            
            return {
                "success": True,
                "suggestions": valid_suggestions,
                "count": len(valid_suggestions)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Task suggestion generation failed: {str(e)}",
                "suggestions": []
            }
    
    def _parse_suggestions_from_response(self, response: str) -> List[Dict]:
        """Parse suggestions from LLM response"""
        try:
            import json
            import re
            
            # Clean response - remove markdown code blocks if present
            response_cleaned = response.strip()
            if response_cleaned.startswith('```'):
                response_cleaned = re.sub(r'```json\n|```\n|```', '', response_cleaned).strip()
            
            # Try to parse as JSON first
            suggestions = json.loads(response_cleaned)
            if isinstance(suggestions, list):
                print(f"   ✅ Parsed {len(suggestions)} suggestions from JSON")
                return suggestions
            else:
                print(f"   ⚠️  LLM returned non-list JSON: {type(suggestions)}")
                return []
        except json.JSONDecodeError as e:
            print(f"   ⚠️  JSON parsing failed: {e}")
            # Fallback: extract suggestions using regex
            suggestions = []
            lines = response.split('\n')
            for line in lines:
                line_stripped = line.strip()
                # Skip empty lines and lines that are just headers
                if not line_stripped or line_stripped.lower() in ['suggestion:', 'suggestions:', 'recommendation:', 'recommendations:']:
                    continue
                    
                if ('suggestion' in line_stripped.lower() or 'recommend' in line_stripped.lower()) and len(line_stripped) > 15:
                    # Extract meaningful text after common prefixes
                    text = re.sub(r'^[-*•]\s*', '', line_stripped)  # Remove bullet points
                    text = re.sub(r'^\d+\.\s*', '', text)  # Remove numbering
                    
                    if text:
                        suggestions.append({
                            'suggestion': text,
                            'category': 'General',
                            'priority': 'Medium',
                            'source': 'AI Analysis'
                        })
            
            print(f"   📝 Fallback: Extracted {len(suggestions)} suggestions from text")
            return suggestions
        except Exception as e:
            print(f"   ❌ Error parsing suggestions: {e}")
            return []
    
    def determine_task_completion_status(self, project_id: str, document_id: str, 
                                       task_text: str, llm_manager, 
                                       similarity_threshold: float = 0.20) -> Dict[str, Any]:
        """
        Determine completion status of a specific task against a document
        
        Args:
            project_id (str): Project identifier
            document_id (str): Document identifier
            task_text (str): Task to analyze
            llm_manager: LLM manager instance
            similarity_threshold (float): Minimum similarity for context retrieval
            
        Returns:
            dict: Success status and completion status (0 or 1)
        """
        try:
            # Get document embeddings
            document_embeddings = self._get_document_embeddings(project_id, document_id)
            
            if not document_embeddings:
                return {
                    "success": False,
                    "error": "No embeddings found for document",
                    "completion_status": 0
                }
            
            # Create task completion query
            task_embedding = self.model.encode([task_text]).tolist()[0]
            
            # Find relevant context
            relevant_context = self._find_relevant_context(
                document_embeddings, task_embedding, similarity_threshold
            )
            
            if not relevant_context:
                return {
                    "success": False,
                    "error": "No relevant context found for task completion analysis",
                    "completion_status": 0
                }
            
            # Prepare context for LLM
            context_text = self._prepare_context_for_llm(relevant_context)
            
            # Create task completion prompt
            prompt = self._create_task_completion_prompt(context_text, task_text)
            
            # Get LLM response
            llm_response = llm_manager.simple_chat(prompt)
            
            if not llm_response.get('success'):
                return {
                    "success": False,
                    "error": f"LLM error: {llm_response.get('error', 'Unknown error')}",
                    "completion_status": 0
                }
            
            # Parse completion status
            completion_status = self._parse_completion_status(llm_response['response'])
            
            return {
                "success": True,
                "completion_status": completion_status,
                "context_used": len(relevant_context)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Task completion analysis failed: {str(e)}",
                "completion_status": 0
            }
    
    def _create_task_completion_prompt(self, context: str, task_text: str) -> str:
        """Create prompt for task completion analysis"""
        return f"""You are analyzing whether a specific task has been completed based on document content.

TASK TO ANALYZE: {task_text}

CONTEXT FROM DOCUMENT:
{context}

Based on the above context, determine if this task has been completed. Look for:
- Evidence of completion (mentions of "completed", "finished", "done")
- Progress indicators (percentages, status updates)
- Deliverables or outputs mentioned
- Any signs that the task is ongoing or incomplete

Respond with ONLY a single number:
- 1 if the task appears to be completed
- 0 if the task is not completed or status is unclear

Do not include any other text or explanation."""
    
    def _parse_completion_status(self, response: str) -> int:
        """Parse completion status from LLM response"""
        try:
            # Clean response and extract number
            response = response.strip().lower()
            
            # Look for explicit completion indicators
            completed_keywords = ['completed', 'done', 'finished', 'complete']
            incomplete_keywords = ['not completed', 'incomplete', 'not done', 'in progress', 'pending', 'ongoing']
            
            # Check for explicit status first
            if any(keyword in response for keyword in incomplete_keywords):
                return 0
            elif any(keyword in response for keyword in completed_keywords):
                return 1
            
            # Fall back to looking for explicit 1 or 0 (not just as substring)
            # Split into words and check for standalone 1 or 0
            words = response.split()
            for word in words:
                # Remove punctuation
                word_clean = word.strip('.,;:!?()')
                if word_clean == '1':
                    return 1
                elif word_clean == '0':
                    return 0
            
            # Default to 0 (not completed) if unclear
            return 0
                
        except Exception as e:
            print(f"Error parsing completion status: {e}")
            return 0
