"""
Centralized ChromaDB Manager for Performance Agent System
Handles all ChromaDB operations with consistent naming and error handling
"""

# Import patched chromadb
from backend.chromadb_patch import chromadb
import re
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer


class PerformanceChromaManager:
    """Centralized ChromaDB manager for Performance Agent system"""
    
    def __init__(self, chroma_path: str = "./chroma_db"):
        # Single ChromaDB client instance
        self.client = chromadb.PersistentClient(path=chroma_path)
        
        # Initialize embedding model
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Create embedding function to avoid onnxruntime
        from chromadb.utils import embedding_functions
        self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name='all-MiniLM-L6-v2'
        )
        
        # Collection naming pattern (same as EmbeddingsManager)
        self._name_pattern = re.compile(r"[^a-zA-Z0-9_-]")
        
        # Performance agent collections
        self.collections = {
            'milestones': 'project_milestones',
            'tasks': 'project_tasks', 
            'bottlenecks': 'project_bottlenecks',
            # Separate collections for details (large text storage)
            'milestone_details': 'project_milestone_details',
            'task_details': 'project_task_details',
            'bottleneck_details': 'project_bottleneck_details',
            # New entities
            'requirements': 'project_requirements',
            'requirements_details': 'project_requirements_details',
            'actors': 'project_actors',
            'actors_details': 'project_actors_details'
        }
        
        # Initialize performance collections
        self._initialize_performance_collections()
    
    def _safe_collection_name(self, project_id: str, document_id: str) -> str:
        """Create a safe collection name for ChromaDB.
        Ensures 3-63 chars, allowed charset [a-zA-Z0-9_-], starts/ends alphanumeric.
        """
        proj = re.sub(self._name_pattern, "", project_id)[:8] or "p"
        doc = re.sub(self._name_pattern, "", document_id)[:8] or "d"
        name = f"p_{proj}_d_{doc}"
        
        # Ensure starts/ends with alphanumeric
        if not name[0].isalnum():
            name = f"p{name}"
        if not name[-1].isalnum():
            name = f"{name}0"
        
        # Guarantee length boundaries
        return name[:63]
    
    def _initialize_performance_collections(self):
        """Initialize all performance agent collections"""
        try:
            for collection_type, collection_name in self.collections.items():
                self.client.get_or_create_collection(
                    name=collection_name,
                    embedding_function=self.embedding_function,
                    metadata={"description": f"Project {collection_type} storage"}
                )
        except Exception as e:
            print(f"Error initializing performance collections: {e}")
    
    def get_document_collection(self, project_id: str, document_id: str):
        """Get document collection with proper error handling"""
        try:
            collection_name = self._safe_collection_name(project_id, document_id)
            return self.client.get_collection(name=collection_name)
        except Exception as e:
            print(f"Error getting document collection {collection_name}: {e}")
            return None
    
    def get_performance_collection(self, collection_type: str):
        """Get performance agent collection"""
        try:
            if collection_type not in self.collections:
                raise ValueError(f"Invalid collection type: {collection_type}")
            
            collection_name = self.collections[collection_type]
            return self.client.get_collection(name=collection_name)
        except Exception as e:
            print(f"Error getting performance collection {collection_type}: {e}")
            return None
    
    def get_document_embeddings(self, project_id: str, document_id: str) -> List[Dict]:
        """Get document embeddings with proper error handling"""
        try:
            collection_name = self._safe_collection_name(project_id, document_id)
            print(f"🔍 Attempting to get embeddings from collection: {collection_name}")
            
            collection = self.get_document_collection(project_id, document_id)
            if not collection:
                print(f"❌ Collection not found: {collection_name}")
                return []
            
            print(f"✅ Collection found: {collection_name}")
            
            # Get all embeddings
            results = collection.get(include=['embeddings', 'documents', 'metadatas'])
            
            print(f"📊 Collection results:")
            print(f"   - IDs count: {len(results.get('ids', []))}")
            print(f"   - Embeddings count: {len(results.get('embeddings', []))}")
            print(f"   - Documents count: {len(results.get('documents', []))}")
            print(f"   - Metadatas count: {len(results.get('metadatas', []))}")
            
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
            
            print(f"✅ Returned {len(embeddings_data)} embeddings")
            return embeddings_data
            
        except Exception as e:
            print(f"❌ Error getting document embeddings: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def store_performance_data(self, collection_type: str, data: List[Dict], 
                             project_id: str, document_id: str) -> int:
        """Store performance data in appropriate collection"""
        try:
            collection = self.get_performance_collection(collection_type)
            if not collection:
                return 0
            
            stored_count = 0
            for i, item in enumerate(data):
                # Use provided ID if present, otherwise generate
                item_id = item.get('id') or f"{collection_type}_{project_id}_{document_id}_{i}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                
                # Create embedding
                text_content = item.get('text', '')
                embedding = self.model.encode([text_content]).tolist()[0]
                
                # Prepare metadata - convert lists/dicts to JSON strings for ChromaDB compatibility
                raw_metadata = {
                    'project_id': project_id,
                    'document_id': document_id,
                    'id': item_id,
                    'source_document': document_id,
                    'created_at': datetime.now().isoformat(),
                    **item.get('metadata', {})
                }
                
                # Convert lists and dicts to JSON strings (ChromaDB only accepts primitives)
                metadata = {}
                for key, value in raw_metadata.items():
                    if isinstance(value, (list, dict)):
                        metadata[key] = json.dumps(value)
                    elif value is None:
                        metadata[key] = ''  # Convert None to empty string
                    else:
                        metadata[key] = value
                
                # Store in collection
                collection.add(
                    embeddings=[embedding],
                    documents=[text_content],
                    metadatas=[metadata],
                    ids=[item_id]
                )
                
                stored_count += 1
            
            return stored_count
            
        except Exception as e:
            print(f"Error storing performance data: {e}")
            return 0
    
    def get_performance_data(self, collection_type: str, project_id: str) -> List[Dict]:
        """Get performance data for a project"""
        try:
            collection = self.get_performance_collection(collection_type)
            if not collection:
                return []
            
            # Query collection for project data
            results = collection.query(
                query_embeddings=[[0.0] * 384],  # Dummy query
                where={"project_id": project_id},
                n_results=1000  # Get all data for project
            )
            
            data = []
            for i, (document, metadata) in enumerate(zip(
                results['documents'][0], 
                results['metadatas'][0]
            )):
                # Parse JSON strings back to lists/dicts
                parsed_metadata = {}
                for key, value in metadata.items():
                    if isinstance(value, str) and value:
                        # Try to parse as JSON (for lists/dicts that were converted)
                        try:
                            parsed = json.loads(value)
                            # Only use parsed if it's a list or dict (not a plain string)
                            if isinstance(parsed, (list, dict)):
                                parsed_metadata[key] = parsed
                            else:
                                parsed_metadata[key] = value
                        except (json.JSONDecodeError, ValueError):
                            # Not JSON, use as-is
                            parsed_metadata[key] = value
                    else:
                        parsed_metadata[key] = value
                
                data.append({
                    'id': results['ids'][0][i],
                    'content': document,
                    'metadata': parsed_metadata
                })
            
            return data
            
        except Exception as e:
            print(f"Error getting performance data: {e}")
            return []
    
    def update_performance_data(self, collection_type: str, item_id: str, 
                              updates: Dict[str, Any]) -> bool:
        """Update performance data item"""
        try:
            collection = self.get_performance_collection(collection_type)
            if not collection:
                return False
            
            # Get existing item
            existing = collection.get(ids=[item_id])
            if not existing['ids']:
                return False
            
            # Update metadata
            new_metadata = existing['metadatas'][0].copy()
            new_metadata.update(updates)
            
            # Update in collection
            collection.update(
                ids=[item_id],
                metadatas=[new_metadata]
            )
            
            return True
            
        except Exception as e:
            print(f"Error updating performance data: {e}")
            return False
    
    def delete_performance_data(self, collection_type: str, item_id: str) -> bool:
        """Delete performance data item"""
        try:
            collection = self.get_performance_collection(collection_type)
            if not collection:
                return False
            
            collection.delete(ids=[item_id])
            return True
            
        except Exception as e:
            print(f"Error deleting performance data: {e}")
            return False
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics for all collections"""
        stats = {}
        
        try:
            # Get all collections
            all_collections = self.client.list_collections()
            
            for collection_info in all_collections:
                collection_name = collection_info.name
                collection = self.client.get_collection(name=collection_name)
                
                # Get count
                count = collection.count()
                
                stats[collection_name] = {
                    'count': count,
                    'type': 'performance' if collection_name in self.collections.values() else 'document'
                }
            
            return stats
            
        except Exception as e:
            print(f"Error getting collection stats: {e}")
            return {}
    
    def store_details(self, detail_type: str, parent_id: str, project_id: str, 
                     document_id: str, details_text: str, metadata: Dict[str, Any] = None) -> str:
        """
        Store details in separate collection (details stored in document field, not metadata)
        
        Args:
            detail_type: Type of detail collection ('milestone_details', 'task_details', 'bottleneck_details')
            parent_id: ID of parent item (milestone/task/bottleneck)
            project_id: Project identifier
            document_id: Source document identifier
            details_text: The actual detail text (can be large)
            metadata: Additional metadata (small fields only)
            
        Returns:
            str: ID of stored detail entry
        """
        try:
            collection = self.get_performance_collection(detail_type)
            if not collection:
                print(f"Error: Collection {detail_type} not found")
                return ""
            
            # Create unique ID for this detail entry
            detail_id = f"{detail_type}_{parent_id}_{document_id}_{datetime.now().strftime('%Y%m%d_%H%M%S%f')}"
            
            # Create embedding from detail text
            embedding = self.model.encode([details_text]).tolist()[0]
            
            # Prepare metadata (keep it small - no large text!)
            detail_metadata = {
                'parent_id': parent_id,
                'project_id': project_id,
                'document_id': document_id,
                'source_document': document_id,
                'created_at': datetime.now().isoformat(),
                'detail_type': detail_type,
                **(metadata or {})
            }
            
            # Store details TEXT in document field (not metadata!)
            collection.add(
                embeddings=[embedding],
                documents=[details_text],  # Large text goes here
                metadatas=[detail_metadata],  # Only small metadata
                ids=[detail_id]
            )
            
            print(f"✅ Stored detail: {detail_id} ({len(details_text)} chars)")
            return detail_id
            
        except Exception as e:
            print(f"Error storing details: {e}")
            import traceback
            traceback.print_exc()
            return ""
    
    def get_details_by_parent(self, detail_type: str, parent_id: str) -> List[Dict]:
        """
        Get all details for a specific parent item (milestone/task/bottleneck)
        
        Args:
            detail_type: Type of detail collection
            parent_id: ID of parent item
            
        Returns:
            List of detail entries with text and metadata
        """
        try:
            collection = self.get_performance_collection(detail_type)
            if not collection:
                return []
            
            # Query for all details of this parent
            results = collection.query(
                query_embeddings=[[0.0] * 384],  # Dummy query
                where={"parent_id": parent_id},
                n_results=1000
            )
            
            if not results['ids'][0]:
                return []
            
            details = []
            for i, (detail_id, document, metadata) in enumerate(zip(
                results['ids'][0],
                results['documents'][0], 
                results['metadatas'][0]
            )):
                details.append({
                    'id': detail_id,
                    'details_text': document,  # Large text from document field
                    'metadata': metadata,
                    'created_at': metadata.get('created_at', ''),
                    'document_id': metadata.get('document_id', '')
                })
            
            # Sort by creation date
            details.sort(key=lambda x: x['created_at'])
            return details
            
        except Exception as e:
            print(f"Error getting details by parent: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def get_details_by_project(self, detail_type: str, project_id: str) -> List[Dict]:
        """
        Get all details for a project
        
        Args:
            detail_type: Type of detail collection
            project_id: Project identifier
            
        Returns:
            List of detail entries
        """
        try:
            collection = self.get_performance_collection(detail_type)
            if not collection:
                return []
            
            # Query for all details in project
            results = collection.query(
                query_embeddings=[[0.0] * 384],  # Dummy query
                where={"project_id": project_id},
                n_results=10000
            )
            
            if not results['ids'][0]:
                return []
            
            details = []
            for i, (detail_id, document, metadata) in enumerate(zip(
                results['ids'][0],
                results['documents'][0], 
                results['metadatas'][0]
            )):
                details.append({
                    'id': detail_id,
                    'details_text': document,
                    'metadata': metadata,
                    'parent_id': metadata.get('parent_id', ''),
                    'created_at': metadata.get('created_at', '')
                })
            
            return details
            
        except Exception as e:
            print(f"Error getting details by project: {e}")
            return []
    
    def delete_details_by_parent(self, detail_type: str, parent_id: str) -> bool:
        """
        Delete all details for a specific parent item
        
        Args:
            detail_type: Type of detail collection
            parent_id: ID of parent item
            
        Returns:
            bool: Success status
        """
        try:
            details = self.get_details_by_parent(detail_type, parent_id)
            if not details:
                return True
            
            collection = self.get_performance_collection(detail_type)
            if not collection:
                return False
            
            detail_ids = [d['id'] for d in details]
            collection.delete(ids=detail_ids)
            
            print(f"✅ Deleted {len(detail_ids)} details for parent {parent_id}")
            return True
            
        except Exception as e:
            print(f"Error deleting details by parent: {e}")
            return False
