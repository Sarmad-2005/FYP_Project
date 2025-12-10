"""
ChromaDB manager for Document Agent (PSDP/Financial Brief) and Intelligent Document Generator.
Reuses the same persistent client/embedding function pattern used by other agents.
"""

from backend.chromadb_patch import chromadb
from datetime import datetime
from typing import List, Dict, Any, Optional
import re
import json
from sentence_transformers import SentenceTransformer


class DocumentChromaManager:
    def __init__(self, chroma_path: str = "./chroma_db"):
        self.client = chromadb.PersistentClient(path=chroma_path)
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        from chromadb.utils import embedding_functions
        self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name='all-MiniLM-L6-v2'
        )
        self._name_pattern = re.compile(r"[^a-zA-Z0-9_-]")
        self.collections = {
            "doc_agent_documents": "doc_agent_documents",
            "doc_gen_documents": "doc_gen_documents",
        }
        self._initialize_collections()

    def _initialize_collections(self):
        for collection_name in self.collections.values():
            try:
                self.client.get_or_create_collection(
                    name=collection_name,
                    embedding_function=self.embedding_function,
                    metadata={"description": f"Document Agent storage: {collection_name}"}
                )
            except Exception as e:
                print(f"Error initializing collection {collection_name}: {e}")

    def _safe_id(self, prefix: str, project_id: str) -> str:
        proj = re.sub(self._name_pattern, "", project_id)[:8] or "p"
        ts = datetime.now().strftime("%Y%m%d_%H%M%S%f")
        return f"{prefix}_{proj}_{ts}"

    def store_document(self, doc_type: str, project_id: str, title: str, html_content: str,
                       source_snapshot: Dict[str, Any], collection: str) -> str:
        try:
            collection_obj = self.client.get_collection(name=collection)
            doc_id = self._safe_id(doc_type, project_id)
            embedding = self.model.encode([html_content]).tolist()[0]
            
            # ChromaDB metadata only accepts primitive types, so serialize source_snapshot to JSON string
            source_snapshot_json = json.dumps(source_snapshot, default=str) if source_snapshot else "{}"
            
            metadata = {
                "project_id": project_id,
                "doc_type": doc_type,
                "title": title,
                "created_at": datetime.now().isoformat(),
                "source_snapshot": source_snapshot_json,  # Store as JSON string
            }
            collection_obj.add(
                ids=[doc_id],
                embeddings=[embedding],
                documents=[html_content],
                metadatas=[metadata]
            )
            print(f"✅ Stored document {doc_id} in collection {collection}")
            return doc_id
        except Exception as e:
            print(f"❌ Error storing document: {e}")
            import traceback
            traceback.print_exc()
            raise

    def list_documents(self, project_id: str, collection: str) -> List[Dict[str, Any]]:
        try:
            collection_obj = self.client.get_collection(name=collection)
            results = collection_obj.query(
                query_embeddings=[[0.0] * 384],
                where={"project_id": project_id},
                n_results=100
            )
            docs = []
            if results.get("ids") and results["ids"][0]:
                for doc_id, doc_text, meta in zip(results["ids"][0],
                                                  results["documents"][0],
                                                  results["metadatas"][0]):
                    docs.append({
                        "id": doc_id,
                        "title": meta.get("title", meta.get("doc_type", "")),
                        "doc_type": meta.get("doc_type"),
                        "project_id": meta.get("project_id"),
                        "created_at": meta.get("created_at"),
                        "content": doc_text
                    })
            return docs
        except Exception as e:
            print(f"Error listing documents: {e}")
            return []

    def get_document(self, doc_id: str, collection: str) -> Optional[Dict[str, Any]]:
        try:
            collection_obj = self.client.get_collection(name=collection)
            results = collection_obj.get(ids=[doc_id], include=["documents", "metadatas"])
            if results and results.get("ids"):
                return {
                    "id": results["ids"][0],
                    "content": results["documents"][0],
                    "metadata": results["metadatas"][0]
                }
            return None
        except Exception as e:
            print(f"Error fetching document {doc_id}: {e}")
            return None
