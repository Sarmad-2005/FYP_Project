"""
Milestone Extraction Agent
Extracts project milestones from documents using AI analysis
"""

import chromadb
import re
import json
from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer
from datetime import datetime


class MilestoneAgent:
    """Agent for extracting and managing project milestones"""
    
    def __init__(self, chroma_manager=None):
        # Initialize embedding model (always needed)
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Use centralized ChromaDB manager or create own if not provided
        if chroma_manager:
            self.chroma_manager = chroma_manager
            # Initialize collection through chroma_manager
            self.milestones_collection_name = "project_milestones"
            self.milestones_collection = self.chroma_manager.get_performance_collection("milestones")
        else:
            # Fallback to individual client (for backward compatibility)
            self.client = chromadb.PersistentClient(path="./chroma_db")
            self.milestones_collection_name = "project_milestones"
            self.milestones_collection = self.client.get_or_create_collection(
                name=self.milestones_collection_name,
                metadata={"description": "Project milestones storage"}
            )
    
    def extract_milestones_from_document(self, project_id: str, document_id: str, 
                                       llm_manager, similarity_threshold: float = 0.20) -> Dict[str, Any]:
        """
        Extract milestones from a specific document
        
        Args:
            project_id (str): Project identifier
            document_id (str): Document identifier
            llm_manager: LLM manager instance
            similarity_threshold (float): Minimum similarity for context retrieval
            
        Returns:
            dict: Success status and extracted milestones
        """
        try:
            # Get document embeddings from existing collection
            document_embeddings = self._get_document_embeddings(project_id, document_id)
            
            if not document_embeddings:
                return {
                    "success": False,
                    "error": "No embeddings found for document",
                    "milestones_count": 0
                }
            
            # Create milestone extraction query
            milestone_query = "milestones of project deliverables goals objectives targets"
            query_embedding = self.model.encode([milestone_query]).tolist()[0]
            
            print(f"🔍 Milestone extraction:")
            print(f"   - Document embeddings available: {len(document_embeddings)}")
            print(f"   - Query: '{milestone_query}'")
            print(f"   - Similarity threshold: {similarity_threshold}")
            
            # Find relevant context using similarity search
            relevant_context = self._find_relevant_context(
                document_embeddings, query_embedding, similarity_threshold
            )
            
            print(f"   - Relevant context found: {len(relevant_context) if relevant_context else 0} chunks")
            
            if not relevant_context:
                print(f"   ❌ No relevant context found (threshold too high or no matching content)")
                return {
                    "success": False,
                    "error": "No relevant context found for milestone extraction",
                    "milestones_count": 0
                }
            
            # Prepare context for LLM
            context_text = self._prepare_context_for_llm(relevant_context)
            
            print(f"   - Context prepared: {len(context_text)} characters")
            
            # Create milestone extraction prompt
            prompt = self._create_milestone_prompt(context_text, project_id, document_id)
            
            print(f"   - Calling LLM for milestone extraction...")
            
            # Get LLM response
            llm_response = llm_manager.simple_chat(prompt)
            
            if not llm_response.get('success'):
                print(f"   ❌ LLM error: {llm_response.get('error', 'Unknown error')}")
                return {
                    "success": False,
                    "error": f"LLM error: {llm_response.get('error', 'Unknown error')}",
                    "milestones_count": 0
                }
            
            print(f"   ✅ LLM response received: {len(llm_response.get('response', ''))} characters")
            
            # Parse milestones from LLM response
            milestones = self._parse_milestones_from_response(llm_response['response'])
            
            print(f"   - Parsed milestones: {len(milestones) if milestones else 0}")
            
            if not milestones:
                print(f"   ❌ No milestones could be parsed from LLM response")
                print(f"   LLM Response: {llm_response.get('response', '')[:200]}...")
                return {
                    "success": False,
                    "error": "No milestones could be parsed from LLM response",
                    "milestones_count": 0
                }
            
            # Store milestones in ChromaDB
            stored_count = self._store_milestones(project_id, document_id, milestones)
            
            return {
                "success": True,
                "milestones_count": stored_count,
                "milestones": milestones,
                "context_used": len(relevant_context)
            }
            
        except Exception as e:
            print(f"❌ EXCEPTION in extract_milestones_from_document: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": f"Milestone extraction failed: {str(e)}",
                "milestones_count": 0
            }
    
    def _get_document_embeddings(self, project_id: str, document_id: str) -> List[Dict]:
        """Get embeddings from the document's ChromaDB collection"""
        try:
            if hasattr(self, 'chroma_manager'):
                # Use centralized manager
                return self.chroma_manager.get_document_embeddings(project_id, document_id)
            else:
                # Fallback to individual client
                collection_name = f"p_{project_id[:8]}_d_{document_id[:8]}"
                collection = self.client.get_collection(name=collection_name)
                
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
    
    def _create_milestone_prompt(self, context: str, project_id: str, document_id: str) -> str:
        """Create prompt for milestone extraction"""
        return f"""You are analyzing a project document to extract milestones. 

CONTEXT FROM DOCUMENT:
{context}

Please extract project milestones from the above context. Return ONLY a JSON array of milestone objects, where each milestone has:
- "milestone": The milestone description
- "category": Category (e.g., "Development", "Testing", "Deployment", "Review")
- "priority": Priority level ("High", "Medium", "Low")

Format your response as a valid JSON array. Do not include any other text, explanations, or formatting.

Example format:
[
  {{
    "milestone": "Complete user authentication system",
    "category": "Development", 
    "priority": "High"
  }},
  {{
    "milestone": "Conduct security testing",
    "category": "Testing",
    "priority": "High"
  }}
]

Extract milestones now:"""
    
    def _parse_milestones_from_response(self, response: str) -> List[Dict]:
        """Parse milestones from LLM response"""
        try:
            # Clean the response
            response = response.strip()
            
            # Remove any markdown formatting
            if response.startswith('```json'):
                response = response[7:]
            if response.endswith('```'):
                response = response[:-3]
            
            # Try to parse JSON
            milestones = json.loads(response)
            
            # Validate structure
            if not isinstance(milestones, list):
                return []
            
            parsed_milestones = []
            for milestone in milestones:
                if isinstance(milestone, dict) and 'milestone' in milestone:
                    parsed_milestones.append({
                        'milestone': milestone.get('milestone', ''),
                        'category': milestone.get('category', 'General'),
                        'priority': milestone.get('priority', 'Medium')
                    })
            
            return parsed_milestones
            
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {e}")
            # Fallback: try to extract milestones using regex
            return self._extract_milestones_with_regex(response)
        except Exception as e:
            print(f"Error parsing milestones: {e}")
            return []
    
    def _extract_milestones_with_regex(self, response: str) -> List[Dict]:
        """Fallback method to extract milestones using regex"""
        milestones = []
        
        # Look for bullet points or numbered lists
        lines = response.split('\n')
        
        for line in lines:
            line = line.strip()
            if line and (line.startswith('-') or line.startswith('•') or line.startswith('*')):
                milestone_text = line[1:].strip()
                if milestone_text:
                    milestones.append({
                        'milestone': milestone_text,
                        'category': 'General',
                        'priority': 'Medium'
                    })
        
        return milestones
    
    def _store_milestones(self, project_id: str, document_id: str, milestones: List[Dict]) -> int:
        """Store milestones in ChromaDB"""
        try:
            if hasattr(self, 'chroma_manager'):
                # Use centralized manager
                data = []
                for milestone in milestones:
                    # Create deterministic ID so details link correctly
                    item_id = f"milestones_{project_id}_{document_id}_{len(data)}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    milestone['id'] = item_id
                    data.append({
                        'id': item_id,
                        'text': milestone['milestone'],
                        'metadata': {
                            'milestone_text': milestone['milestone'],
                            'category': milestone['category'],
                            'priority': milestone['priority']
                        }
                    })
                return self.chroma_manager.store_performance_data('milestones', data, project_id, document_id)
            else:
                # Fallback to individual client
                stored_count = 0
                
                for i, milestone in enumerate(milestones):
                    milestone_id = f"milestone_{project_id}_{document_id}_{i}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    milestone_text = milestone['milestone']
                    embedding = self.model.encode([milestone_text]).tolist()[0]
                    
                    metadata = {
                        'project_id': project_id,
                        'document_id': document_id,
                        'milestone_text': milestone_text,
                        'category': milestone['category'],
                        'priority': milestone['priority'],
                        'created_at': datetime.now().isoformat(),
                        'source_document': document_id
                    }
                    
                    self.milestones_collection.add(
                        embeddings=[embedding],
                        documents=[milestone_text],
                        metadatas=[metadata],
                        ids=[milestone_id]
                    )
                    
                    stored_count += 1
                
                return stored_count
                
        except Exception as e:
            print(f"Error storing milestones: {e}")
            return 0
    
    def get_project_milestones(self, project_id: str) -> List[Dict]:
        """Get all milestones for a project (excludes suggestions)"""
        try:
            # Query milestones collection
            results = self.milestones_collection.query(
                query_embeddings=[[0.0] * 384],  # Dummy query
                where={"project_id": project_id},
                n_results=1000  # Get all milestones for project
            )
            
            milestones = []
            for i, (milestone_text, metadata) in enumerate(zip(
                results['documents'][0], 
                results['metadatas'][0]
            )):
                # Skip suggestions (only include actual milestones)
                if metadata.get('type') == 'milestone_suggestion':
                    continue
                    
                milestones.append({
                    'id': results['ids'][0][i],
                    'milestone': milestone_text,
                    'category': metadata.get('category', 'General'),
                    'priority': metadata.get('priority', 'Medium'),
                    'created_at': metadata.get('created_at', ''),
                    'source_document': metadata.get('source_document', '')
                })
            
            return milestones
            
        except Exception as e:
            print(f"Error getting project milestones: {e}")
            return []
    
    def extract_milestone_details(self, project_id: str, milestone_text: str, 
                                llm_manager, similarity_threshold: float = 0.20) -> Dict[str, Any]:
        """
        Extract detailed information for a specific milestone across all project documents
        
        Args:
            project_id (str): Project identifier
            milestone_text (str): Milestone to analyze
            llm_manager: LLM manager instance
            similarity_threshold (float): Minimum similarity for context retrieval
            
        Returns:
            dict: Success status and milestone details
        """
        try:
            # Get all project documents from database manager
            # This would need access to db_manager - for now, we'll implement a basic version
            # that searches across existing milestone data
            
            # Create milestone embedding for similarity search
            milestone_embedding = self.model.encode([milestone_text]).tolist()[0]
            
            # Get all milestones for this project to find relevant context
            all_milestones = self.get_project_milestones(project_id)
            
            # Find milestones with similar text (for cross-document analysis)
            relevant_milestones = []
            for milestone in all_milestones:
                if milestone_text.lower() in milestone.get('milestone', '').lower():
                    relevant_milestones.append(milestone)
            
            if not relevant_milestones:
                return {
                    "success": False,
                    "error": "No relevant milestones found for details extraction"
                }
            
            # Prepare context from relevant milestones
            context_text = ""
            for milestone in relevant_milestones:
                context_text += f"Milestone: {milestone.get('milestone', '')}\n"
                context_text += f"Category: {milestone.get('category', '')}\n"
                context_text += f"Priority: {milestone.get('priority', '')}\n"
                context_text += f"Source Document: {milestone.get('source_document', '')}\n\n"
            
            # Create detailed analysis prompt
            prompt = f"""
            Analyze the following milestone and provide detailed information:
            
            Milestone: {milestone_text}
            
            Context from project documents:
            {context_text}
            
            Please provide detailed analysis including:
            1. Description and scope
            2. Key deliverables
            3. Dependencies
            4. Success criteria
            5. Timeline considerations
            6. Risks and challenges
            
            Format your response as structured details that can be parsed.
            """
            
            # Get LLM response
            llm_response = llm_manager.simple_chat(prompt)
            
            # Parse details from response
            details = self._parse_milestone_details_from_response(llm_response)
            
            return {
                "success": True,
                "details": details,
                "source_documents": [m.get('source_document', '') for m in relevant_milestones]
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Milestone details extraction failed: {str(e)}"
            }
    
    def _parse_milestone_details_from_response(self, response: Dict[str, Any]) -> str:
        """Parse milestone details from LLM response"""
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
            return f"Error parsing milestone details: {str(e)}"
    
    def generate_milestone_suggestions(self, project_id: str, milestones: List[Dict], 
                                      llm_manager, similarity_threshold: float = 0.20) -> Dict[str, Any]:
        """
        Generate suggestions for milestones based on extracted data
        
        Args:
            project_id (str): Project identifier
            milestones (List[Dict]): List of extracted milestones
            llm_manager: LLM manager instance
            similarity_threshold (float): Minimum similarity for context retrieval
            
        Returns:
            dict: Success status and generated suggestions
        """
        try:
            if not milestones:
                return {
                    "success": False,
                    "error": "No milestones available for suggestion generation",
                    "suggestions": []
                }
            
            # Prepare context from milestones
            context_text = ""
            for milestone in milestones:
                context_text += f"Milestone: {milestone.get('milestone', '')}\n"
                context_text += f"Category: {milestone.get('category', '')}\n"
                context_text += f"Priority: {milestone.get('priority', '')}\n\n"
            
            # Create suggestion generation prompt
            prompt = f"""
            Based on the following project milestones, generate actionable suggestions for project improvement:
            
            MILESTONES:
            {context_text}
            
            Please provide suggestions for:
            1. Milestone prioritization and sequencing
            2. Risk mitigation strategies
            3. Resource allocation recommendations
            4. Timeline optimization
            5. Quality assurance measures
            6. Stakeholder communication strategies
            
            Format your response as a JSON array of suggestion objects, where each suggestion has:
            - "suggestion": The suggestion text
            - "category": Category (e.g., "Planning", "Risk Management", "Resource", "Timeline", "Quality", "Communication")
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
                "error": f"Milestone suggestion generation failed: {str(e)}",
                "suggestions": []
            }
    
    def _parse_suggestions_from_response(self, response: str) -> List[Dict]:
        """Parse suggestions from LLM response"""
        try:
            import json
            # Try to parse as JSON first
            suggestions = json.loads(response)
            if isinstance(suggestions, list):
                return suggestions
            else:
                return []
        except json.JSONDecodeError:
            # Fallback: extract suggestions using regex
            import re
            suggestions = []
            lines = response.split('\n')
            for line in lines:
                if 'suggestion' in line.lower() or 'recommend' in line.lower():
                    suggestions.append({
                        'suggestion': line.strip(),
                        'category': 'General',
                        'priority': 'Medium',
                        'source': 'AI Analysis'
                    })
            return suggestions
        except Exception as e:
            return []
