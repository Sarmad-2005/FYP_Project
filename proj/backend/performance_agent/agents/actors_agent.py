"""
Actors Extraction Agent
Identifies actors/entities/organizations/people involved in project requirements.
"""

from typing import List, Dict, Any
from datetime import datetime
import json
import re
import numpy as np
from sentence_transformers import SentenceTransformer


class ActorsAgent:
    """Agent for extracting and managing project actors/stakeholders"""

    def __init__(self, chroma_manager=None):
        self.chroma_manager = chroma_manager
        self.model = SentenceTransformer('all-MiniLM-L6-v2')

    # ---- Public API ----
    def extract_actors_from_document(self, project_id: str, document_id: str, llm_manager, similarity_threshold: float = 0.20) -> Dict[str, Any]:
        try:
            embeddings = self._get_document_embeddings(project_id, document_id)
            if not embeddings:
                return {"success": False, "error": "No embeddings found", "actors_count": 0}

            query_embedding = self.model.encode(["actors stakeholders entities organizations people roles responsibilities" ]).tolist()[0]
            relevant_context = self._find_relevant_context(embeddings, query_embedding, similarity_threshold)
            if not relevant_context:
                return {"success": False, "error": "No relevant context found", "actors_count": 0}

            context_text = self._prepare_context_for_llm(relevant_context)
            prompt = self._create_actors_prompt(context_text, project_id, document_id)
            llm_response = llm_manager.simple_chat(prompt)
            if not llm_response.get('success'):
                return {"success": False, "error": llm_response.get('error', 'LLM error'), "actors_count": 0}

            response_text = llm_response['response']
            print(f"   📝 LLM Response (first 500 chars): {response_text[:500]}")
            actors = self._parse_actors_from_response(response_text)
            if not actors:
                print(f"   ⚠️  Failed to parse actors from response")
                print(f"   📄 Full response: {response_text}")
                return {"success": False, "error": "No actors parsed", "actors_count": 0}
            print(f"   ✅ Parsed {len(actors)} actors successfully")

            stored_count = self._store_actors(project_id, document_id, actors)
            return {
                "success": True,
                "actors_count": stored_count,
                "actors": actors,
                "context_used": len(relevant_context)
            }
        except Exception as e:
            return {"success": False, "error": f"Actors extraction failed: {str(e)}", "actors_count": 0}

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
            sim = ctx.get('similarity', 0.0)
            parts.append(f"[Context {i+1}] (Similarity: {sim:.3f})\n{ctx['content']}")
        return "\n\n".join(parts)

    def _create_actors_prompt(self, context: str, project_id: str, document_id: str) -> str:
        return f"""You are extracting project actors/stakeholders from documentation.

PROJECT ID: {project_id}
DOCUMENT ID: {document_id}

CONTEXT:
{context}

Return ONLY a JSON array. Each actor object must have:
- "name": actor identifier or name
- "actor_type": Person | Organization | Team | Vendor | Client | Role
- "role": role/responsibility description
- "requirements": array of requirement references they handle (if any)
- "notes": optional notes or contact info if present
"""

    def _parse_actors_from_response(self, response: str) -> List[Dict]:
        try:
            txt = response.strip()
            # Remove markdown code blocks
            if txt.startswith('```json'):
                txt = txt[7:]
            elif txt.startswith('```'):
                txt = txt[3:]
            if txt.endswith('```'):
                txt = txt[:-3]
            txt = txt.strip()
            
            # Try to find JSON array in the response
            import re
            json_match = re.search(r'\[[\s\S]*\]', txt)
            if json_match:
                txt = json_match.group(0)
            
            data = json.loads(txt)
            if not isinstance(data, list):
                # If it's a dict, try to extract a list from it
                if isinstance(data, dict):
                    # Check common keys that might contain the list
                    for key in ['actors', 'stakeholders', 'entities', 'data', 'results']:
                        if key in data and isinstance(data[key], list):
                            data = data[key]
                            break
                    else:
                        return self._extract_actors_with_regex(response)
                else:
                    return self._extract_actors_with_regex(response)
            
            parsed = []
            for item in data:
                if isinstance(item, dict):
                    # Try multiple possible field names for actor name
                    actor_name = (item.get('name') or item.get('actor_name') or 
                                item.get('stakeholder') or item.get('entity') or 
                                item.get('person') or item.get('organization') or '')
                    
                    if actor_name:
                        parsed.append({
                            'name': actor_name,
                            'actor_type': (item.get('actor_type') or item.get('type') or 
                                         item.get('entity_type') or 'Person'),
                            'role': (item.get('role') or item.get('responsibility') or 
                                    item.get('position') or ''),
                            'requirements': item.get('requirements', []),
                            'notes': (item.get('notes') or item.get('description') or 
                                     item.get('details') or '')
                        })
            
            if parsed:
                return parsed
            else:
                return self._extract_actors_with_regex(response)
        except Exception as e:
            print(f"Error parsing actors JSON: {e}")
            print(f"Response was: {response[:500]}")
            return self._extract_actors_with_regex(response)

    def _extract_actors_with_regex(self, response: str) -> List[Dict]:
        actors = []
        for line in response.split('\n'):
            line = line.strip()
            if line and (line.startswith('-') or line.startswith('*') or line.startswith('•')):
                text = line[1:].strip()
                if text:
                    actors.append({
                        'name': text,
                        'actor_type': 'Person',
                        'role': '',
                        'requirements': [],
                        'notes': ''
                    })
        return actors

    def _store_actors(self, project_id: str, document_id: str, actors: List[Dict]) -> int:
        if not self.chroma_manager:
            return 0
        data = []
        for idx, actor in enumerate(actors):
            item_id = f"actors_{project_id}_{document_id}_{idx}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            actor['id'] = item_id
            data.append({
                'id': item_id,
                'text': actor.get('name', ''),
                'metadata': {
                    'project_id': project_id,
                    'document_id': document_id,
                    'actor_type': actor.get('actor_type', 'Person'),
                    'role': actor.get('role', ''),
                    'requirements': actor.get('requirements', []),
                    'notes': actor.get('notes', ''),
                    'created_at': datetime.now().isoformat()
                }
            })
        return self.chroma_manager.store_performance_data('actors', data, project_id, document_id)
