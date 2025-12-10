# Import patched chromadb
from backend.chromadb_patch import chromadb
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any
import re
import json
from .enhanced_pdf_processor import EnhancedPDFProcessor

class EmbeddingsManager:
    def __init__(self):
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(path="./chroma_db")
        
        # Initialize L6 model for embeddings
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Initialize enhanced PDF processor for text extraction
        self.pdf_processor = EnhancedPDFProcessor()
        
        # Use a short, valid collection naming scheme compliant with ChromaDB constraints (3-63 chars)
        # Format: p_<first8(project)>_d_<first8(document)>
        self._name_pattern = re.compile(r"[^a-zA-Z0-9_-]")

    def _safe_collection_name(self, project_id: str, document_id: str) -> str:
        """Create a short, valid collection name for ChromaDB.
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

    def create_embeddings_from_pdf(self, project_id: str, document_id: str, pdf_path: str) -> bool:
        """Create embeddings from PDF: LangChain for extraction, L6 for embeddings, ChromaDB for storage."""
        try:
            collection_name = self._safe_collection_name(project_id, document_id)
            
            # Create or get collection
            collection = self.client.get_or_create_collection(
                name=collection_name,
                metadata={"project_id": project_id, "document_id": document_id}
            )
            
            # Extract sentences and tables using enhanced PDF processor
            sentences, tables = self.pdf_processor.process_pdf(pdf_path)
            
            if not sentences and not tables:
                print("No content extracted from PDF")
                return False
            
            # Prepare data for embedding
            texts = []
            metadatas = []
            ids = []
            
            # Add sentences
            for i, sentence in enumerate(sentences):
                texts.append(sentence)
                metadatas.append({
                    "type": "sentence",
                    "project_id": project_id,
                    "document_id": document_id,
                    "index": i
                })
                ids.append(f"sentence_{i}")
            
            # Add tables
            for i, table in enumerate(tables):
                table_text = self.pdf_processor.table_to_text(table)
                texts.append(table_text)
                metadatas.append({
                    "type": "table",
                    "project_id": project_id,
                    "document_id": document_id,
                    "index": i,
                    "row_count": table.get('row_count', 0),
                    "column_count": table.get('column_count', 0),
                    "page": table.get('page', 0)
                })
                ids.append(f"table_{i}")
            
            # Generate embeddings using L6 model
            embeddings = self.model.encode(texts).tolist()
            
            # Store in ChromaDB
            collection.add(
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas,
                ids=ids
            )
            
            print(f"Successfully created {len(texts)} embeddings from PDF")
            return True
            
        except Exception as e:
            print(f"Error creating embeddings from PDF: {e}")
            return False

    def create_embeddings(self, project_id: str, document_id: str, sentences: List[str], tables: List[Dict]) -> bool:
        """Create embeddings for sentences and tables and store in ChromaDB"""
        try:
            collection_name = self._safe_collection_name(project_id, document_id)
            
            # Create or get collection
            collection = self.client.get_or_create_collection(
                name=collection_name,
                metadata={"project_id": project_id, "document_id": document_id}
            )
            
            # Prepare data for embedding
            texts = []
            metadatas = []
            ids = []
            
            # Add sentences
            for i, sentence in enumerate(sentences):
                texts.append(sentence)
                metadatas.append({
                    "type": "sentence",
                    "project_id": project_id,
                    "document_id": document_id,
                    "index": i
                })
                ids.append(f"sentence_{i}")
            
            # Add tables
            for i, table in enumerate(tables):
                # Support both dict-shaped tables and pre-rendered text tables
                is_dict_table = isinstance(table, dict)
                table_text = self._table_to_text(table) if is_dict_table else str(table)
                
                # Ensure table_text is a string
                table_text_str = str(table_text) if not isinstance(table_text, str) else table_text
                texts.append(table_text_str)
                metadatas.append({
                    "type": "table",
                    "project_id": project_id,
                    "document_id": document_id,
                    "index": i,
                    "row_count": (table.get('row_count', 0) if is_dict_table else 0),
                    "column_count": (table.get('column_count', 0) if is_dict_table else 0)
                })
                ids.append(f"table_{i}")
            
            # Generate embeddings
            embeddings = self.model.encode(texts).tolist()
            
            # Debug: Check what we're about to send to ChromaDB
            print(f"About to send to ChromaDB:")
            print(f"  texts count: {len(texts)}")
            print(f"  texts types: {[type(t) for t in texts]}")
            print(f"  metadatas count: {len(metadatas)}")
            print(f"  metadatas types: {[type(m) for m in metadatas]}")
            
            # Ensure all texts are strings
            texts = [str(text) for text in texts]
            
            # Store in ChromaDB
            collection.add(
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas,
                ids=ids
            )
            
            return True
            
        except Exception as e:
            print(f"Error creating embeddings: {e}")
            return False

    def get_document_embeddings(self, project_id: str, document_id: str) -> List[Dict]:
        """Retrieve embeddings for a specific document"""
        try:
            collection_name = self._safe_collection_name(project_id, document_id)
            
            # Get collection
            collection = self.client.get_collection(name=collection_name)
            
            # Get all items from collection
            results = collection.get(include=['embeddings', 'documents', 'metadatas'])
            
            # Format results
            embeddings_data = []
            for i, (embedding, document, metadata) in enumerate(zip(
                results['embeddings'], 
                results['documents'], 
                results['metadatas']
            )):
                embeddings_data.append({
                    'id': results['ids'][i],
                    'type': metadata['type'],
                    'content': document,
                    'embedding': embedding,
                    'metadata': metadata
                })
            
            return embeddings_data
            
        except Exception as e:
            print(f"Error retrieving embeddings: {e}")
            return []

    def search_embeddings(self, project_id: str, document_id: str, query: str, n_results: int = 5) -> List[Dict]:
        """Search embeddings within a specific document"""
        try:
            collection_name = self._safe_collection_name(project_id, document_id)
            
            # Get collection
            collection = self.client.get_collection(name=collection_name)
            
            # Generate query embedding
            query_embedding = self.model.encode([query]).tolist()[0]
            
            # Search
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                include=['documents', 'metadatas', 'distances']
            )
            
            # Format results
            search_results = []
            for i, (document, metadata, distance) in enumerate(zip(
                results['documents'][0], 
                results['metadatas'][0], 
                results['distances'][0]
            )):
                search_results.append({
                    'content': document,
                    'metadata': metadata,
                    'similarity_score': 1 - distance,  # Convert distance to similarity
                    'rank': i + 1
                })
            
            return search_results
            
        except Exception as e:
            print(f"Error searching embeddings: {e}")
            return []

    def _table_to_text(self, table: Dict) -> str:
        """Convert table data to text representation"""
        try:
            text_parts = []
            
            # Add headers
            if table.get('headers'):
                text_parts.append("Headers: " + " | ".join(table['headers']))
            
            # Add rows
            if table.get('rows'):
                text_parts.append("Data:")
                for row in table['rows']:
                    text_parts.append(" | ".join(str(cell) for cell in row))
            
            return "\n".join(text_parts)
            
        except Exception as e:
            print(f"Error converting table to text: {e}")
            return str(table)
    
    def get_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text string using the sentence transformer model.
        Used by orchestrator for semantic routing.
        
        Args:
            text: Text string to embed
            
        Returns:
            List of floats representing the embedding vector
        """
        try:
            embedding = self.model.encode(text)
            return embedding.tolist()
        except Exception as e:
            print(f"Error generating embedding: {e}")
            return None

