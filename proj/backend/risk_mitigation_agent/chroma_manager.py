"""
Centralized ChromaDB Manager for Risk Mitigation Agent System
Handles all ChromaDB operations with consistent naming and error handling
"""

# Import patched chromadb
from backend.chromadb_patch import chromadb
import re
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer


class RiskChromaManager:
    """Centralized ChromaDB manager for Risk Mitigation Agent system"""
    
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
        
        # Collection naming pattern
        self._name_pattern = re.compile(r"[^a-zA-Z0-9_-]")
        
        # Risk mitigation agent collections
        self.collections = {
            'risk_bottlenecks': 'project_risk_bottlenecks',
            'mitigation_suggestions': 'project_risk_mitigation_suggestions',
            'consequences': 'project_risk_consequences',
            'ordering': 'project_risk_ordering',
            'enhanced_bottlenecks': 'project_risk_enhanced_bottlenecks'
        }
        
        # Initialize risk collections
        self._initialize_risk_collections()
    
    def _initialize_risk_collections(self):
        """Initialize all risk mitigation agent collections"""
        try:
            for collection_type, collection_name in self.collections.items():
                self.client.get_or_create_collection(
                    name=collection_name,
                    embedding_function=self.embedding_function,
                    metadata={"description": f"Project risk {collection_type} storage"}
                )
        except Exception as e:
            print(f"Error initializing risk collections: {e}")
    
    def get_risk_collection(self, collection_type: str):
        """Get risk mitigation agent collection"""
        try:
            if collection_type not in self.collections:
                print(f"Warning: Unknown collection type '{collection_type}', available: {list(self.collections.keys())}")
                raise ValueError(f"Invalid collection type: {collection_type}")
            
            collection_name = self.collections[collection_type]
            return self.client.get_or_create_collection(
                name=collection_name,
                embedding_function=self.embedding_function,
                metadata={"description": f"Project risk {collection_type} storage"}
            )
        except Exception as e:
            print(f"Error getting risk collection {collection_type}: {e}")
            return None
    
    def store_risk_data(self, collection_type: str, data: List[Dict], 
                       project_id: str, metadata: Dict[str, Any] = None) -> int:
        """Store risk data in appropriate collection"""
        try:
            collection = self.get_risk_collection(collection_type)
            if not collection:
                return 0
            
            stored_count = 0
            for i, item in enumerate(data):
                # Use provided ID if present, otherwise generate
                item_id = item.get('id') or f"{collection_type}_{project_id}_{i}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                
                # Create embedding
                text_content = item.get('text', item.get('content', ''))
                embedding = self.model.encode([text_content]).tolist()[0]
                
                # Prepare metadata
                raw_metadata = {
                    'project_id': project_id,
                    'created_at': datetime.now().isoformat(),
                    **(metadata or {}),
                    **item.get('metadata', {})
                }
                
                # Convert lists and dicts to JSON strings
                final_metadata = {}
                for key, value in raw_metadata.items():
                    if isinstance(value, (list, dict)):
                        final_metadata[key] = json.dumps(value)
                    elif value is None:
                        final_metadata[key] = ''
                    else:
                        final_metadata[key] = value
                
                # Store in collection
                collection.add(
                    embeddings=[embedding],
                    documents=[text_content],
                    metadatas=[final_metadata],
                    ids=[item_id]
                )
                
                stored_count += 1
            
            return stored_count
            
        except Exception as e:
            print(f"Error storing risk data: {e}")
            import traceback
            traceback.print_exc()
            return 0
    
    def get_risk_data(self, collection_type: str, project_id: str) -> List[Dict]:
        """Get risk data for a project"""
        try:
            collection = self.get_risk_collection(collection_type)
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
                        try:
                            parsed = json.loads(value)
                            if isinstance(parsed, (list, dict)):
                                parsed_metadata[key] = parsed
                            else:
                                parsed_metadata[key] = value
                        except (json.JSONDecodeError, ValueError):
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
            print(f"Error getting risk data: {e}")
            return []
    
    def get_risk_data_by_id(self, collection_type: str, item_id: str) -> Optional[Dict]:
        """Get specific risk data item by ID"""
        try:
            collection = self.get_risk_collection(collection_type)
            if not collection:
                return None
            
            results = collection.get(ids=[item_id])
            if not results['ids']:
                return None
            
            # Parse metadata
            metadata = results['metadatas'][0]
            parsed_metadata = {}
            for key, value in metadata.items():
                if isinstance(value, str) and value:
                    try:
                        parsed = json.loads(value)
                        if isinstance(parsed, (list, dict)):
                            parsed_metadata[key] = parsed
                        else:
                            parsed_metadata[key] = value
                    except (json.JSONDecodeError, ValueError):
                        parsed_metadata[key] = value
                else:
                    parsed_metadata[key] = value
            
            return {
                'id': results['ids'][0],
                'content': results['documents'][0],
                'metadata': parsed_metadata
            }
            
        except Exception as e:
            print(f"Error getting risk data by ID: {e}")
            return None
    
    def update_risk_data(self, collection_type: str, item_id: str, 
                       updates: Dict[str, Any]) -> bool:
        """Update risk data item"""
        try:
            collection = self.get_risk_collection(collection_type)
            if not collection:
                return False
            
            # Get existing item
            existing = collection.get(ids=[item_id])
            if not existing['ids']:
                return False
            
            # Update metadata
            new_metadata = existing['metadatas'][0].copy()
            
            # Convert updates to JSON strings if needed
            for key, value in updates.items():
                if isinstance(value, (list, dict)):
                    new_metadata[key] = json.dumps(value)
                elif value is None:
                    new_metadata[key] = ''
                else:
                    new_metadata[key] = value
            
            # Update in collection
            collection.update(
                ids=[item_id],
                metadatas=[new_metadata]
            )
            
            return True
            
        except Exception as e:
            print(f"Error updating risk data: {e}")
            return False
    
    def delete_risk_data(self, collection_type: str, item_id: str) -> bool:
        """Delete risk data item"""
        try:
            collection = self.get_risk_collection(collection_type)
            if not collection:
                return False
            
            collection.delete(ids=[item_id])
            return True
            
        except Exception as e:
            print(f"Error deleting risk data: {e}")
            return False

