"""
Centralized ChromaDB Manager for Financial Agent System
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


class FinancialChromaManager:
    """Centralized ChromaDB manager for Financial Agent system"""
    
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
        
        # Financial agent collections
        self.collections = {
            'financial_details': 'project_financial_details',
            'transactions': 'project_transactions',
            'expense_analysis': 'project_expense_analysis',
            'revenue_analysis': 'project_revenue_analysis',
            'financial_suggestions': 'project_financial_suggestions',
            'anomaly_alerts': 'project_anomaly_alerts',
            'reviewed_anomalies': 'project_reviewed_anomalies',
            'actor_transaction_mappings': 'project_actor_transaction_mappings'
        }
        
        # Initialize financial collections
        self._initialize_financial_collections()
    
    def _initialize_financial_collections(self):
        """Initialize all financial agent collections"""
        try:
            for collection_type, collection_name in self.collections.items():
                self.client.get_or_create_collection(
                    name=collection_name,
                    embedding_function=self.embedding_function,
                    metadata={"description": f"Financial {collection_type} storage"}
                )
            print("✅ Financial ChromaDB collections initialized")
        except Exception as e:
            print(f"Error initializing financial collections: {e}")
    
    def get_financial_collection(self, collection_type: str):
        """Get financial agent collection"""
        try:
            if collection_type not in self.collections:
                raise ValueError(f"Invalid collection type: {collection_type}")
            
            collection_name = self.collections[collection_type]
            return self.client.get_collection(name=collection_name)
        except Exception as e:
            print(f"Error getting financial collection {collection_type}: {e}")
            return None
    
    def store_financial_data(self, collection_type: str, data: List[Dict], 
                           project_id: str, data_type: str = None):
        """
        Store financial data in ChromaDB
        
        Args:
            collection_type: Type of collection (financial_details, transactions, etc.)
            data: List of data items to store
            project_id: Project identifier
            data_type: Specific data type (optional)
        """
        try:
            collection = self.get_financial_collection(collection_type)
            if not collection:
                return False
            
            ids = []
            documents = []
            metadatas = []
            embeddings = []
            
            for item in data:
                # Generate unique ID using UUID to avoid collisions
                if 'id' in item and item['id']:
                    item_id = item['id']
                else:
                    item_id = f"{collection_type}_{project_id[:8]}_{str(uuid.uuid4())[:8]}"
                ids.append(item_id)
                
                # Document text for embedding
                doc_text = item.get('text', item.get('description', str(item)))
                documents.append(doc_text)
                
                # Generate embedding
                embedding = self.model.encode(doc_text).tolist()
                embeddings.append(embedding)
                
                # Metadata - convert lists/dicts to JSON strings for ChromaDB compatibility
                raw_metadata = item.get('metadata', {})
                raw_metadata['project_id'] = project_id
                raw_metadata['created_at'] = datetime.now().isoformat()
                if data_type:
                    raw_metadata['type'] = data_type
                
                # Convert lists and dicts to JSON strings (ChromaDB only accepts primitives)
                metadata = {}
                for key, value in raw_metadata.items():
                    if isinstance(value, (list, dict)):
                        metadata[key] = json.dumps(value)
                    elif value is None:
                        metadata[key] = ''  # Convert None to empty string
                    else:
                        metadata[key] = value
                
                metadatas.append(metadata)
            
            # Store in ChromaDB
            if ids:
                collection.add(
                    ids=ids,
                    documents=documents,
                    embeddings=embeddings,
                    metadatas=metadatas
                )
                print(f"✅ Stored {len(ids)} items in {collection_type}")
                return True
            
            return False
            
        except Exception as e:
            print(f"Error storing financial data: {e}")
            return False
    
    def get_financial_data(self, collection_type: str, project_id: str, 
                          filters: Optional[Dict] = None) -> List[Dict]:
        """
        Get financial data from ChromaDB
        
        Args:
            collection_type: Type of collection
            project_id: Project identifier
            filters: Optional filters for metadata
            
        Returns:
            List of financial data items
        """
        try:
            collection = self.get_financial_collection(collection_type)
            if not collection:
                return []
            
            # Build where clause
            where_clause = {"project_id": project_id}
            if filters:
                where_clause.update(filters)
            
            # Query collection
            results = collection.get(
                where=where_clause,
                include=['documents', 'metadatas', 'embeddings']
            )
            
            # Format results
            data_items = []
            if results and results['ids']:
                for i, item_id in enumerate(results['ids']):
                    raw_metadata = results['metadatas'][i] if i < len(results['metadatas']) else {}
                    
                    # Parse JSON strings back to lists/dicts
                    parsed_metadata = {}
                    for key, value in raw_metadata.items():
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
                    
                    data_items.append({
                        'id': item_id,
                        'text': results['documents'][i] if i < len(results['documents']) else '',
                        'metadata': parsed_metadata
                    })
            
            return data_items
            
        except Exception as e:
            print(f"Error getting financial data: {e}")
            return []
    
    def query_financial_data(self, collection_type: str, query_text: str, 
                            project_id: str, n_results: int = 10) -> List[Dict]:
        """
        Query financial data using semantic search
        
        Args:
            collection_type: Type of collection
            query_text: Query text for semantic search
            project_id: Project identifier
            n_results: Number of results to return
            
        Returns:
            List of matching financial data items
        """
        try:
            collection = self.get_financial_collection(collection_type)
            if not collection:
                return []
            
            # Generate query embedding
            query_embedding = self.model.encode(query_text).tolist()
            
            # Query collection
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where={"project_id": project_id},
                include=['documents', 'metadatas', 'distances']
            )
            
            # Format results
            data_items = []
            if results and results['ids'] and len(results['ids']) > 0:
                for i, item_id in enumerate(results['ids'][0]):
                    data_items.append({
                        'id': item_id,
                        'text': results['documents'][0][i] if i < len(results['documents'][0]) else '',
                        'metadata': results['metadatas'][0][i] if i < len(results['metadatas'][0]) else {},
                        'distance': results['distances'][0][i] if i < len(results['distances'][0]) else 1.0
                    })
            
            return data_items
            
        except Exception as e:
            print(f"Error querying financial data: {e}")
            return []
    
    def update_financial_data(self, collection_type: str, item_id: str, 
                             new_data: Dict):
        """
        Update financial data in ChromaDB
        
        Args:
            collection_type: Type of collection
            item_id: Item identifier
            new_data: New data to update
        """
        try:
            collection = self.get_financial_collection(collection_type)
            if not collection:
                return False
            
            # Update document and metadata
            doc_text = new_data.get('text', new_data.get('description', str(new_data)))
            embedding = self.model.encode(doc_text).tolist()
            
            metadata = new_data.get('metadata', {})
            metadata['updated_at'] = datetime.now().isoformat()
            
            collection.update(
                ids=[item_id],
                documents=[doc_text],
                embeddings=[embedding],
                metadatas=[metadata]
            )
            
            return True
            
        except Exception as e:
            print(f"Error updating financial data: {e}")
            return False
    
    def delete_financial_data(self, collection_type: str, item_id: str):
        """Delete financial data from ChromaDB"""
        try:
            collection = self.get_financial_collection(collection_type)
            if not collection:
                return False
            
            collection.delete(ids=[item_id])
            return True
            
        except Exception as e:
            print(f"Error deleting financial data: {e}")
            return False

