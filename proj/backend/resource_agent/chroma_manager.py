"""
Centralized ChromaDB Manager for Resource Agent System
Handles all ChromaDB operations with consistent naming and error handling
"""

# Import patched chromadb
from backend.chromadb_patch import chromadb
import re
import json
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer


class ResourceChromaManager:
    """Centralized ChromaDB manager for Resource Agent system"""
    
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
        
        # Resource agent collections
        self.collections = {
            'tasks_analysis': 'project_resource_tasks_analysis',
            'task_dependencies': 'project_resource_task_dependencies',
            'critical_path': 'project_resource_critical_path',
            'work_teams': 'project_resource_work_teams',
            'resource_assignments': 'project_resource_assignments'
        }
        
        # Initialize resource collections
        self._initialize_resource_collections()
    
    def _initialize_resource_collections(self):
        """Initialize all resource agent collections"""
        try:
            for collection_type, collection_name in self.collections.items():
                self.client.get_or_create_collection(
                    name=collection_name,
                    embedding_function=self.embedding_function,
                    metadata={"description": f"Resource {collection_type} storage"}
                )
            print("✅ Resource ChromaDB collections initialized")
        except Exception as e:
            print(f"Error initializing resource collections: {e}")
    
    def get_resource_collection(self, collection_type: str):
        """Get resource agent collection"""
        try:
            if collection_type not in self.collections:
                raise ValueError(f"Invalid collection type: {collection_type}")
            
            collection_name = self.collections[collection_type]
            return self.client.get_collection(name=collection_name)
        except Exception as e:
            print(f"Error getting resource collection {collection_type}: {e}")
            return None
    
    def store_resource_data(self, collection_type: str, data: List[Dict], 
                           project_id: str, data_type: str = None):
        """
        Store resource data in ChromaDB
        
        Args:
            collection_type: Type of collection (tasks_analysis, task_dependencies, etc.)
            data: List of data items to store
            project_id: Project identifier
            data_type: Specific data type (optional)
        """
        try:
            collection = self.get_resource_collection(collection_type)
            if not collection:
                return False
            
            ids = []
            documents = []
            metadatas = []
            embeddings = []
            
            for item in data:
                # Generate unique ID
                if 'id' in item and item['id']:
                    item_id = item['id']
                else:
                    item_id = f"{collection_type}_{project_id}_{uuid.uuid4().hex[:8]}"
                
                # Prepare document text
                if 'text' in item:
                    doc_text = item['text']
                elif 'task_name' in item:
                    doc_text = item['task_name']
                elif 'name' in item:
                    doc_text = item['name']
                else:
                    doc_text = json.dumps(item)
                
                # Prepare metadata
                metadata = item.get('metadata', {})
                metadata['project_id'] = project_id
                metadata['created_at'] = datetime.now().isoformat()
                if data_type:
                    metadata['data_type'] = data_type
                
                # Merge item fields into metadata (excluding 'id', 'text', 'metadata')
                for key, value in item.items():
                    if key not in ['id', 'text', 'metadata']:
                        # Convert complex types to JSON strings for metadata
                        if isinstance(value, (list, dict)):
                            metadata[key] = json.dumps(value)
                        else:
                            metadata[key] = str(value) if not isinstance(value, (str, int, float, bool)) else value
                
                # Create embedding
                embedding = self.model.encode([doc_text]).tolist()[0]
                
                ids.append(item_id)
                documents.append(doc_text)
                metadatas.append(metadata)
                embeddings.append(embedding)
            
            # Store in ChromaDB
            collection.add(
                ids=ids,
                documents=documents,
                metadatas=metadatas,
                embeddings=embeddings
            )
            
            return True
            
        except Exception as e:
            print(f"Error storing resource data: {e}")
            return False
    
    def get_resource_data(self, collection_type: str, project_id: str, 
                         filters: Dict = None) -> List[Dict]:
        """
        Get resource data from ChromaDB
        
        Args:
            collection_type: Type of collection
            project_id: Project identifier
            filters: Optional filters for query
            
        Returns:
            List of data items
        """
        try:
            collection = self.get_resource_collection(collection_type)
            if not collection:
                return []
            
            # Build query filters
            where = {"project_id": project_id}
            if filters:
                where.update(filters)
            
            # Query collection (using query method like PerformanceChromaManager)
            results = collection.query(
                query_embeddings=[[0.0] * 384],  # Dummy query
                where=where,
                n_results=1000  # Get all data for project
            )
            
            # Format results
            data = []
            if results['ids'] and len(results['ids']) > 0:
                for i, item_id in enumerate(results['ids'][0]):
                    document = results['documents'][0][i] if results['documents'] and results['documents'][0] else ''
                    metadata = results['metadatas'][0][i] if results['metadatas'] and results['metadatas'][0] else {}
                    
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
                    
                    item = {
                        'id': item_id,
                        'text': document,
                        'content': document,
                        'metadata': parsed_metadata
                    }
                    # Extract fields from metadata back to item level
                    for key in ['task_id', 'task_name', 'priority', 'complexity', 
                               'estimated_time_hours', 'depends_on', 'name', 'type',
                               'assigned_resources', 'path_tasks', 'total_duration_hours', 'task_schedule']:
                        if key in parsed_metadata:
                            value = parsed_metadata[key]
                            # Parse JSON strings for complex types
                            if isinstance(value, str) and key in ['task_schedule', 'path_tasks', 'depends_on', 'assigned_resources']:
                                try:
                                    parsed = json.loads(value)
                                    item[key] = parsed
                                except (json.JSONDecodeError, ValueError):
                                    item[key] = value
                            else:
                                item[key] = value
                    data.append(item)
            
            return data
            
        except Exception as e:
            print(f"Error getting resource data: {e}")
            return []
    
    def update_resource_data(self, collection_type: str, item_id: str, 
                           updates: Dict) -> bool:
        """
        Update resource data in ChromaDB
        
        Args:
            collection_type: Type of collection
            item_id: Item identifier
            updates: Dictionary of fields to update
            
        Returns:
            True if successful, False otherwise
        """
        try:
            collection = self.get_resource_collection(collection_type)
            if not collection:
                return False
            
            # Get existing item
            existing = collection.get(ids=[item_id])
            if not existing['ids']:
                return False
            
            # Update metadata
            metadata = existing['metadatas'][0].copy()
            # Convert complex types to JSON strings for metadata
            for key, value in updates.items():
                if isinstance(value, (list, dict)):
                    metadata[key] = json.dumps(value)
                else:
                    metadata[key] = value
            metadata['updated_at'] = datetime.now().isoformat()
            
            # Update in ChromaDB
            collection.update(
                ids=[item_id],
                metadatas=[metadata]
            )
            
            return True
            
        except Exception as e:
            print(f"Error updating resource data: {e}")
            return False
    
    def delete_resource_data(self, collection_type: str, item_id: str) -> bool:
        """
        Delete resource data from ChromaDB
        
        Args:
            collection_type: Type of collection
            item_id: Item identifier
            
        Returns:
            True if successful, False otherwise
        """
        try:
            collection = self.get_resource_collection(collection_type)
            if not collection:
                return False
            
            collection.delete(ids=[item_id])
            return True
            
        except Exception as e:
            print(f"Error deleting resource data: {e}")
            return False

