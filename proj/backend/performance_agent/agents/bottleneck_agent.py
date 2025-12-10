"""
Bottleneck Analysis Agent
Identifies project bottlenecks from documents using AI analysis
"""

import chromadb
import re
import json
from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer
from datetime import datetime


class BottleneckAgent:
    """Agent for identifying and managing project bottlenecks"""
    
    def __init__(self, chroma_manager=None):
        # Use centralized ChromaDB manager or create own if not provided
        if chroma_manager:
            self.chroma_manager = chroma_manager
            self.client = chroma_manager.client
        else:
            # Initialize ChromaDB client for bottlenecks storage
            self.client = chromadb.PersistentClient(path="./chroma_db")
        
        # Initialize embedding model
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Bottlenecks collection name
        self.bottlenecks_collection_name = "project_bottlenecks"
        
        # Create or get bottlenecks collection
        self.bottlenecks_collection = self.client.get_or_create_collection(
            name=self.bottlenecks_collection_name,
            metadata={"description": "Project bottlenecks storage"}
        )
    
    def extract_bottlenecks_from_document(self, project_id: str, document_id: str, 
                                        llm_manager, similarity_threshold: float = 0.20) -> Dict[str, Any]:
        """
        Extract bottlenecks from a specific document
        
        Args:
            project_id (str): Project identifier
            document_id (str): Document identifier
            llm_manager: LLM manager instance
            similarity_threshold (float): Minimum similarity for context retrieval
            
        Returns:
            dict: Success status and extracted bottlenecks
        """
        try:
            # Get document embeddings from existing collection
            document_embeddings = self._get_document_embeddings(project_id, document_id)
            
            if not document_embeddings:
                return {
                    "success": False,
                    "error": "No embeddings found for document",
                    "bottlenecks_count": 0
                }
            
            # Create bottleneck extraction query
            bottleneck_query = "bottlenecks constraints issues problems risks challenges obstacles barriers"
            query_embedding = self.model.encode([bottleneck_query]).tolist()[0]
            
            # Find relevant context using similarity search
            relevant_context = self._find_relevant_context(
                document_embeddings, query_embedding, similarity_threshold
            )
            
            if not relevant_context:
                return {
                    "success": False,
                    "error": "No relevant context found for bottleneck extraction",
                    "bottlenecks_count": 0
                }
            
            # Prepare context for LLM
            context_text = self._prepare_context_for_llm(relevant_context)
            
            # Create bottleneck extraction prompt
            prompt = self._create_bottleneck_prompt(context_text, project_id, document_id)
            
            # Get LLM response
            llm_response = llm_manager.simple_chat(prompt)
            
            if not llm_response.get('success'):
                return {
                    "success": False,
                    "error": f"LLM error: {llm_response.get('error', 'Unknown error')}",
                    "bottlenecks_count": 0
                }
            
            # Parse bottlenecks from LLM response
            bottlenecks = self._parse_bottlenecks_from_response(llm_response['response'])
            
            if not bottlenecks:
                return {
                    "success": False,
                    "error": "No bottlenecks could be parsed from LLM response",
                    "bottlenecks_count": 0
                }
            
            # Store bottlenecks in ChromaDB
            stored_count = self._store_bottlenecks(project_id, document_id, bottlenecks)
            
            return {
                "success": True,
                "bottlenecks_count": stored_count,
                "bottlenecks": bottlenecks,
                "context_used": len(relevant_context)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Bottleneck extraction failed: {str(e)}",
                "bottlenecks_count": 0
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
    
    def _create_bottleneck_prompt(self, context: str, project_id: str, document_id: str) -> str:
        """Create prompt for bottleneck extraction"""
        return f"""You are analyzing a project document to identify bottlenecks and constraints. 

CONTEXT FROM DOCUMENT:
{context}

Please extract project bottlenecks from the above context. Return ONLY a JSON array of bottleneck objects, where each bottleneck has:
- "bottleneck": The bottleneck description
- "category": Category (e.g., "Resource", "Technical", "Process", "Timeline", "Budget", "Communication")
- "severity": Severity level ("Critical", "High", "Medium", "Low")
- "impact": Impact description

Format your response as a valid JSON array. Do not include any other text, explanations, or formatting.

Example format:
[
  {{
    "bottleneck": "Limited development team capacity",
    "category": "Resource", 
    "severity": "High",
    "impact": "Delays in feature delivery"
  }},
  {{
    "bottleneck": "Legacy system integration challenges",
    "category": "Technical",
    "severity": "Critical",
    "impact": "Blocking new feature development"
  }}
]

Extract bottlenecks now:"""
    
    def _parse_bottlenecks_from_response(self, response: str) -> List[Dict]:
        """Parse bottlenecks from LLM response"""
        try:
            # Clean the response
            response = response.strip()
            
            # Remove any markdown formatting
            if response.startswith('```json'):
                response = response[7:]
            if response.endswith('```'):
                response = response[:-3]
            
            # Try to parse JSON
            bottlenecks = json.loads(response)
            
            # Validate structure
            if not isinstance(bottlenecks, list):
                return []
            
            parsed_bottlenecks = []
            for bottleneck in bottlenecks:
                if isinstance(bottleneck, dict) and 'bottleneck' in bottleneck:
                    parsed_bottlenecks.append({
                        'bottleneck': bottleneck.get('bottleneck', ''),
                        'category': bottleneck.get('category', 'General'),
                        'severity': bottleneck.get('severity', 'Medium'),
                        'impact': bottleneck.get('impact', 'Unknown impact')
                    })
            
            return parsed_bottlenecks
            
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {e}")
            # Fallback: try to extract bottlenecks using regex
            return self._extract_bottlenecks_with_regex(response)
        except Exception as e:
            print(f"Error parsing bottlenecks: {e}")
            return []
    
    def _extract_bottlenecks_with_regex(self, response: str) -> List[Dict]:
        """Fallback method to extract bottlenecks using regex"""
        bottlenecks = []
        
        # Look for bullet points or numbered lists
        lines = response.split('\n')
        
        for line in lines:
            line = line.strip()
            if line and (line.startswith('-') or line.startswith('•') or line.startswith('*')):
                bottleneck_text = line[1:].strip()
                if bottleneck_text:
                    bottlenecks.append({
                        'bottleneck': bottleneck_text,
                        'category': 'General',
                        'severity': 'Medium',
                        'impact': 'Unknown impact'
                    })
        
        return bottlenecks
    
    def _store_bottlenecks(self, project_id: str, document_id: str, bottlenecks: List[Dict]) -> int:
        """Store bottlenecks in ChromaDB"""
        try:
            stored_count = 0
            
            for i, bottleneck in enumerate(bottlenecks):
                # Create unique ID for bottleneck
                bottleneck_id = f"bottleneck_{project_id}_{document_id}_{i}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                bottleneck['id'] = bottleneck_id
                
                # Create embedding for bottleneck text
                bottleneck_text = bottleneck['bottleneck']
                embedding = self.model.encode([bottleneck_text]).tolist()[0]
                
                # Prepare metadata
                metadata = {
                    'project_id': project_id,
                    'document_id': document_id,
                    'bottleneck_text': bottleneck_text,
                    'category': bottleneck['category'],
                    'severity': bottleneck['severity'],
                    'impact': bottleneck['impact'],
                    'created_at': datetime.now().isoformat(),
                    'source_document': document_id
                }
                
                # Store in ChromaDB
                self.bottlenecks_collection.add(
                    embeddings=[embedding],
                    documents=[bottleneck_text],
                    metadatas=[metadata],
                    ids=[bottleneck_id]
                )
                
                stored_count += 1
            
            return stored_count
            
        except Exception as e:
            print(f"Error storing bottlenecks: {e}")
            return 0
    
    def get_project_bottlenecks(self, project_id: str) -> List[Dict]:
        """Get all bottlenecks for a project (excludes suggestions)"""
        try:
            # Query bottlenecks collection
            results = self.bottlenecks_collection.query(
                query_embeddings=[[0.0] * 384],  # Dummy query
                where={"project_id": project_id},
                n_results=1000  # Get all bottlenecks for project
            )
            
            bottlenecks = []
            for i, (bottleneck_text, metadata) in enumerate(zip(
                results['documents'][0], 
                results['metadatas'][0]
            )):
                # Skip suggestions (only include actual bottlenecks)
                if metadata.get('type') == 'bottleneck_suggestion':
                    continue
                    
                bottlenecks.append({
                    'id': results['ids'][0][i],
                    'bottleneck': bottleneck_text,
                    'category': metadata.get('category', 'General'),
                    'severity': metadata.get('severity', 'Medium'),
                    'impact': metadata.get('impact', 'Unknown impact'),
                    'created_at': metadata.get('created_at', ''),
                    'source_document': metadata.get('source_document', '')
                })
            
            return bottlenecks
            
        except Exception as e:
            print(f"Error getting project bottlenecks: {e}")
            return []
    
    def extract_bottleneck_details(self, project_id: str, bottleneck_text: str, 
                                 llm_manager, similarity_threshold: float = 0.20) -> Dict[str, Any]:
        """
        Extract detailed information for a specific bottleneck across all project documents
        
        Args:
            project_id (str): Project identifier
            bottleneck_text (str): Bottleneck to analyze
            llm_manager: LLM manager instance
            similarity_threshold (float): Minimum similarity for context retrieval
            
        Returns:
            dict: Success status and bottleneck details
        """
        try:
            # Get all bottlenecks for this project to find relevant context
            all_bottlenecks = self.get_project_bottlenecks(project_id)
            
            # Find bottlenecks with similar text (for cross-document analysis)
            relevant_bottlenecks = []
            for bottleneck in all_bottlenecks:
                if bottleneck_text.lower() in bottleneck.get('bottleneck', '').lower():
                    relevant_bottlenecks.append(bottleneck)
            
            if not relevant_bottlenecks:
                return {
                    "success": False,
                    "error": "No relevant bottlenecks found for details extraction"
                }
            
            # Prepare context from relevant bottlenecks
            context_text = ""
            for bottleneck in relevant_bottlenecks:
                context_text += f"Bottleneck: {bottleneck.get('bottleneck', '')}\n"
                context_text += f"Category: {bottleneck.get('category', '')}\n"
                context_text += f"Severity: {bottleneck.get('severity', '')}\n"
                context_text += f"Impact: {bottleneck.get('impact', '')}\n"
                context_text += f"Source Document: {bottleneck.get('source_document', '')}\n\n"
            
            # Create detailed analysis prompt
            prompt = f"""
            Analyze the following bottleneck and provide detailed information:
            
            Bottleneck: {bottleneck_text}
            
            Context from project documents:
            {context_text}
            
            Please provide detailed analysis including:
            1. Root cause analysis
            2. Impact assessment
            3. Risk factors
            4. Mitigation strategies
            5. Prevention measures
            6. Timeline for resolution
            7. Resource requirements
            
            Format your response as structured details that can be parsed.
            """
            
            # Get LLM response
            llm_response = llm_manager.simple_chat(prompt)
            
            # Parse details from response
            details = self._parse_bottleneck_details_from_response(llm_response)
            
            return {
                "success": True,
                "details": details,
                "source_documents": [b.get('source_document', '') for b in relevant_bottlenecks]
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Bottleneck details extraction failed: {str(e)}"
            }
    
    def _parse_bottleneck_details_from_response(self, response: Dict[str, Any]) -> str:
        """Parse bottleneck details from LLM response"""
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
            return f"Error parsing bottleneck details: {str(e)}"
    
    def generate_bottleneck_suggestions(self, project_id: str, bottlenecks: List[Dict], 
                                      llm_manager, similarity_threshold: float = 0.20) -> Dict[str, Any]:
        """
        Generate suggestions for bottlenecks based on extracted data
        
        Args:
            project_id (str): Project identifier
            bottlenecks (List[Dict]): List of extracted bottlenecks
            llm_manager: LLM manager instance
            similarity_threshold (float): Minimum similarity for context retrieval
            
        Returns:
            dict: Success status and generated suggestions
        """
        try:
            if not bottlenecks:
                return {
                    "success": False,
                    "error": "No bottlenecks available for suggestion generation",
                    "suggestions": []
                }
            
            # Prepare context from bottlenecks
            context_text = ""
            for bottleneck in bottlenecks:
                context_text += f"Bottleneck: {bottleneck.get('bottleneck', '')}\n"
                context_text += f"Category: {bottleneck.get('category', '')}\n"
                context_text += f"Severity: {bottleneck.get('severity', '')}\n"
                context_text += f"Impact: {bottleneck.get('impact', '')}\n\n"
            
            # Create suggestion generation prompt
            prompt = f"""
            Based on the following project bottlenecks, generate actionable suggestions for bottleneck resolution and project improvement:
            
            BOTTLENECKS:
            {context_text}
            
            Please provide suggestions for:
            1. Bottleneck resolution strategies
            2. Risk mitigation and prevention measures
            3. Resource reallocation and optimization
            4. Process improvement and automation
            5. Communication and stakeholder management
            6. Timeline adjustments and contingency planning
            7. Technology and tool recommendations
            8. Monitoring and early warning systems
            
            Format your response as a JSON array of suggestion objects, where each suggestion has:
            - "suggestion": The suggestion text
            - "category": Category (e.g., "Resolution", "Risk Management", "Resource", "Process", "Communication", "Timeline", "Technology", "Monitoring")
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
                "error": f"Bottleneck suggestion generation failed: {str(e)}",
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
