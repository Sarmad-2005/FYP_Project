"""
Actor to Transaction Mapper
Uses LLM to map performance actors to financial transactions.
"""

from typing import List, Dict, Any
import json
import re
from datetime import datetime


class ActorTransactionMapper:
    """Maps actors to transactions and stores mappings in ChromaDB."""

    def __init__(self, chroma_manager, orchestrator=None, llm_manager=None):
        self.chroma_manager = chroma_manager
        self.orchestrator = orchestrator
        self.llm_manager = llm_manager

    def map_actors_to_transactions(self, project_id: str, actors_override: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Map actors to transactions using LLM and store results.
        
        actors_override: optional list of actors (useful in microservice/A2A mode when orchestrator is external)
        """
        try:
            if not self.llm_manager:
                return {"success": False, "error": "LLM not configured."}

            actors = actors_override if actors_override is not None else self._fetch_actors(project_id)
            if not actors:
                return {"success": False, "error": "No actors found. Run Performance agent first."}
            
            print(f"👥 [Actor-Transaction Mapper] Received {len(actors)} actors")
            if actors:
                print(f"   Sample actor structure: {actors[0] if actors else 'None'}")

            transactions = self.chroma_manager.get_financial_data('transactions', project_id)
            if not transactions:
                return {"success": False, "error": "No transactions found. Run Financial extraction first."}

            prompt = self._build_prompt(project_id, actors, transactions)
            llm_response = self.llm_manager.simple_chat(prompt)

            if not llm_response.get("success"):
                return {"success": False, "error": f"LLM error: {llm_response.get('error', 'Unknown error')}"}

            mappings = self._parse_llm_response(llm_response.get("response", ""))
            if not mappings:
                return {"success": False, "error": "No mappings parsed from LLM response."}

            stored = self._store_mappings(project_id, mappings)

            return {
                "success": True,
                "count": len(stored),
                "mappings": stored
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _fetch_actors(self, project_id: str) -> List[Dict[str, Any]]:
        """Fetch actors via orchestrator from Performance Agent."""
        try:
            actors = self.orchestrator.route_data_request(
                query="Get all project actors/stakeholders with type and role",
                requesting_agent="financial_agent",
                project_id=project_id
            )
            return actors or []
        except Exception as e:
            print(f"Error fetching actors: {e}")
            return []

    def _build_prompt(self, project_id: str, actors: List[Dict[str, Any]], transactions: List[Dict[str, Any]]) -> str:
        """Build LLM prompt for mapping actors to transactions."""
        actors_text = []
        for a in actors:
            meta = a.get("metadata", {})
            # Actors from performance agent have name in 'content' field, not 'name'
            actor_name = a.get("content") or meta.get("name") or a.get("name") or "Unknown Actor"
            actors_text.append({
                "id": a.get("id") or meta.get("id"),
                "name": actor_name,
                "actor_type": meta.get("actor_type") or a.get("actor_type"),
                "role": meta.get("role") or a.get("role"),
                "requirements": meta.get("requirements") or a.get("requirements", [])
            })

        tx_text = []
        for t in transactions:
            meta = t.get("metadata", {})
            tx_text.append({
                "id": t.get("id"),
                "amount": meta.get("amount"),
                "type": meta.get("type"),
                "category": meta.get("category"),
                "vendor": meta.get("vendor_recipient"),
                "description": t.get("text"),
                "date": meta.get("date"),
                "status": meta.get("status")
            })

        return f"""
You are mapping project actors/stakeholders to financial transactions.

PROJECT ID: {project_id}

ACTORS (JSON):
{json.dumps(actors_text, indent=2)}

TRANSACTIONS (JSON):
{json.dumps(tx_text, indent=2)}

TASK:
Determine which transactions each actor is responsible for or related to.

OUTPUT STRICTLY AS JSON ARRAY:
[
  {{
    "actor_id": "string",
    "actor_name": "string",
    "actor_type": "Person/Organization/Team/Vendor/Client/Role",
    "transactions": [
      {{
        "transaction_id": "string",
        "reason": "why this transaction maps to this actor",
        "confidence": 0-1
      }}
    ],
    "summary": "one-line summary of the actor's financial responsibility"
  }}
]

CRITICAL REQUIREMENTS:
- Return ONLY a JSON array, starting with [ and ending with ]
- Each element is an object with actor_id, actor_name, actor_type, transactions array, and summary
- No markdown code blocks, no explanations, no additional text
- If an actor has no matching transactions, still include them with empty transactions array

Rules:
- Use only the provided IDs.
- If no transactions match an actor, return an empty array for that actor's transactions.
- Keep JSON valid. No extra text.
"""

    def _parse_llm_response(self, response_text: str) -> List[Dict[str, Any]]:
        """Parse the LLM JSON response safely with robust extraction."""
        try:
            txt = response_text.strip()
            original_length = len(txt)
            
            # Remove markdown code blocks
            if txt.startswith('```json'):
                txt = txt[7:].strip()
            elif txt.startswith('```'):
                txt = txt[3:].strip()
            if txt.endswith('```'):
                txt = txt[:-3].strip()
            
            # Extract JSON array (handle cases where LLM adds explanation after JSON)
            json_match = re.search(r'\[[\s\S]*?\](?=\s*(?:\n|$|Explanation|In the above|For |The |This |Note|Note that))', txt)
            if not json_match:
                # Try to find any JSON array
                json_match = re.search(r'\[[\s\S]*\]', txt)
            
            if json_match:
                txt = json_match.group(0)
                print(f"   🔍 Extracted JSON array (original: {original_length} chars, extracted: {len(txt)} chars)")
            else:
                print(f"   ⚠️  No JSON array found in response, trying full text")
            
            print(f"   📝 First 300 chars: {txt[:300]}")
            
            # Try to parse JSON
            try:
                data = json.loads(txt)
                if isinstance(data, list):
                    print(f"   ✅ Parsed {len(data)} actor-transaction mappings")
                    return data
                elif isinstance(data, dict):
                    # If LLM returned a dict instead of array, try to convert
                    print(f"   ⚠️  LLM returned dict instead of array, attempting conversion...")
                    # Check if it's a single mapping wrapped in dict
                    if 'actor_id' in data or 'actor_name' in data:
                        return [data]  # Wrap single item in array
                    return []
                else:
                    print(f"   ⚠️  LLM returned unexpected type: {type(data)}")
                    return []
            except json.JSONDecodeError as json_err:
                # Try to fix common JSON issues
                print(f"   ⚠️  Initial JSON parse failed: {json_err}")
                
                # Fix trailing commas
                txt = re.sub(r',\s*\]', ']', txt)
                txt = re.sub(r',\s*}', '}', txt)
                
                try:
                    data = json.loads(txt)
                    if isinstance(data, list):
                        print(f"   ✅ Parsed after fixes: {len(data)} mappings")
                        return data
                except json.JSONDecodeError:
                    print(f"   ❌ JSON parsing failed after fixes")
                    raise json_err
                    
        except Exception as e:
            print(f"   ❌ Error parsing LLM response: {e}")
            print(f"   📄 Response (first 500 chars): {response_text[:500]}")
            import traceback
            traceback.print_exc()
            return []

    def _store_mappings(self, project_id: str, mappings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Store mappings in ChromaDB and return stored items."""
        stored_items = []
        try:
            data_to_store = []
            for m in mappings:
                actor_name = m.get("actor_name", "Unknown")
                txs = m.get("transactions", [])
                summary = m.get("summary", "")
                doc_text = f"Actor {actor_name} mapped to {len(txs)} transactions. Summary: {summary}"

                data_to_store.append({
                    "id": m.get("actor_id"),
                    "text": doc_text,
                    "metadata": {
                        "project_id": project_id,
                        "actor_id": m.get("actor_id"),
                        "actor_name": actor_name,
                        "actor_type": m.get("actor_type"),
                        "transactions": txs,
                        "summary": summary,
                        "created_at": datetime.utcnow().isoformat()
                    }
                })

            if data_to_store:
                self.chroma_manager.store_financial_data(
                    "actor_transaction_mappings",
                    data_to_store,
                    project_id
                )
                stored_items = data_to_store
        except Exception as e:
            print(f"Error storing actor-transaction mappings: {e}")
        return stored_items
