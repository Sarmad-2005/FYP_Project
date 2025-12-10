"""
Requirements Extraction Agent
Extracts project requirements from documents using AI analysis.
"""

from typing import List, Dict, Any
from datetime import datetime
import json
import re
import numpy as np
from sentence_transformers import SentenceTransformer


class RequirementsAgent:
    """Agent for extracting and managing project requirements"""

    def __init__(self, chroma_manager=None):
        # Shared chroma manager (preferred path)
        self.chroma_manager = chroma_manager
        # Embedding model
        self.model = SentenceTransformer('all-MiniLM-L6-v2')

    # ---- Public API ----
    def extract_requirements_from_document(self, project_id: str, document_id: str, llm_manager, similarity_threshold: float = 0.20) -> Dict[str, Any]:
        """Extract requirements for a given document"""
        try:
            embeddings = self._get_document_embeddings(project_id, document_id)
            if not embeddings:
                return {"success": False, "error": "No embeddings found for document", "requirements_count": 0}

            query_embedding = self.model.encode(["requirements specifications needs deliverables features functionality scope"]).tolist()[0]
            relevant_context = self._find_relevant_context(embeddings, query_embedding, similarity_threshold)
            if not relevant_context:
                return {"success": False, "error": "No relevant context found", "requirements_count": 0}

            context_text = self._prepare_context_for_llm(relevant_context)
            prompt = self._create_requirements_prompt(context_text, project_id, document_id)
            llm_response = llm_manager.simple_chat(prompt)
            if not llm_response.get('success'):
                return {"success": False, "error": llm_response.get('error', 'LLM error'), "requirements_count": 0}

            requirements = self._parse_requirements_from_response(llm_response['response'])
            if not requirements:
                return {"success": False, "error": "No requirements parsed", "requirements_count": 0}

            stored_count = self._store_requirements(project_id, document_id, requirements)
            return {
                "success": True,
                "requirements_count": stored_count,
                "requirements": requirements,
                "context_used": len(relevant_context)
            }
        except Exception as e:
            return {"success": False, "error": f"Requirement extraction failed: {str(e)}", "requirements_count": 0}

    # ---- Helpers ----
    def _get_document_embeddings(self, project_id: str, document_id: str) -> List[Dict]:
        if self.chroma_manager:
            return self.chroma_manager.get_document_embeddings(project_id, document_id)
        return []

    def _find_relevant_context(self, embeddings: List[Dict], query_embedding: List[float], threshold: float) -> List[Dict]:
        relevant = []
        for emb in embeddings:
            sim = self._cosine_similarity(query_embedding, emb['embedding'])
            if sim >= threshold:
                emb['similarity'] = sim
                relevant.append(emb)
        relevant.sort(key=lambda x: x.get('similarity', 0), reverse=True)
        return relevant

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        v1 = np.array(vec1)
        v2 = np.array(vec2)
        if v1.shape != v2.shape or np.linalg.norm(v1) == 0 or np.linalg.norm(v2) == 0:
            return 0.0
        return float(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)))

    def _prepare_context_for_llm(self, contexts: List[Dict]) -> str:
        parts = []
        for i, ctx in enumerate(contexts):
            content = ctx['content']
            sim = ctx.get('similarity', 0.0)
            parts.append(f"[Context {i+1}] (Similarity: {sim:.3f})\n{content}")
        return "\n\n".join(parts)

    def _create_requirements_prompt(self, context: str, project_id: str, document_id: str) -> str:
        return f"""You are extracting project requirements from documentation.

PROJECT ID: {project_id}
DOCUMENT ID: {document_id}

CONTEXT:
{context}

Return ONLY a JSON array. Each requirement object must have:
- "requirement": requirement statement
- "category": e.g., Functional, Non-Functional, Scope, Integration, Security
- "priority": High | Medium | Low
- "dependencies": array of related requirements or components (can be empty)
- "source": optional source/section info if present
"""

    def _parse_requirements_from_response(self, response: str) -> List[Dict]:
        try:
            txt = response.strip()
            if txt.startswith('```json'):
                txt = txt[7:]
            if txt.endswith('```'):
                txt = txt[:-3]
            data = json.loads(txt)
            if not isinstance(data, list):
                return []
            parsed = []
            for item in data:
                if isinstance(item, dict) and item.get('requirement'):
                    parsed.append({
                        'requirement': item.get('requirement', ''),
                        'category': item.get('category', 'General'),
                        'priority': item.get('priority', 'Medium'),
                        'dependencies': item.get('dependencies', []),
                        'source': item.get('source', '')
                    })
            return parsed
        except Exception:
            return self._extract_requirements_with_regex(response)

    def _extract_requirements_with_regex(self, response: str) -> List[Dict]:
        reqs = []
        for line in response.split('\n'):
            line = line.strip()
            if line and (line.startswith('-') or line.startswith('*') or line.startswith('•')):
                text = line[1:].strip()
                if text:
                    reqs.append({
                        'requirement': text,
                        'category': 'General',
                        'priority': 'Medium',
                        'dependencies': [],
                        'source': ''
                    })
        return reqs

    def _store_requirements(self, project_id: str, document_id: str, requirements: List[Dict]) -> int:
        if not self.chroma_manager:
            return 0
        data = []
        for idx, req in enumerate(requirements):
            item_id = f"requirements_{project_id}_{document_id}_{idx}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            req['id'] = item_id
            data.append({
                'id': item_id,
                'text': req.get('requirement', ''),
                'metadata': {
                    'project_id': project_id,
                    'document_id': document_id,
                    'category': req.get('category', 'General'),
                    'priority': req.get('priority', 'Medium'),
                    'dependencies': req.get('dependencies', []),
                    'source': req.get('source', ''),
                    'created_at': datetime.now().isoformat()
                }
            })
        return self.chroma_manager.store_performance_data('requirements', data, project_id, document_id)
