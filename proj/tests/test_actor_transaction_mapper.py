import pytest

from backend.financial_agent.agents.actor_transaction_mapper import ActorTransactionMapper


class FakeChromaManager:
    def __init__(self):
        self.stored = []

    def get_financial_data(self, collection_type, project_id, filters=None):
        if collection_type == "transactions":
            return [
                {"id": "txn_1", "text": "Payment to Vendor A", "metadata": {"amount": 1000, "vendor_recipient": "Vendor A", "type": "expense"}},
                {"id": "txn_2", "text": "Ticket sales", "metadata": {"amount": 5000, "vendor_recipient": "Ticket Desk", "type": "revenue"}},
            ]
        if collection_type == "actor_transaction_mappings":
            return self.stored
        return []

    def store_financial_data(self, collection_type, data, project_id, data_type=None):
        if collection_type == "actor_transaction_mappings":
            self.stored.extend(data)
            return True
        return False


class FakeOrchestrator:
    def route_data_request(self, query, requesting_agent, project_id):
        return [
            {"id": "actor_1", "metadata": {"name": "Vendor A", "actor_type": "Vendor", "role": "Supplies materials"}},
            {"id": "actor_2", "metadata": {"name": "Ticket Desk", "actor_type": "Team", "role": "Handles ticketing"}},
        ]


class FakeLLM:
    def simple_chat(self, prompt):
        # Return a deterministic mapping response
        return {
            "success": True,
            "response": """
            [
              {
                "actor_id": "actor_1",
                "actor_name": "Vendor A",
                "actor_type": "Vendor",
                "transactions": [
                  {"transaction_id": "txn_1", "reason": "Vendor match", "confidence": 0.9}
                ],
                "summary": "Vendor A linked to expense txn_1"
              }
            ]
            """
        }


def test_actor_transaction_mapping():
    chroma = FakeChromaManager()
    mapper = ActorTransactionMapper(chroma_manager=chroma, orchestrator=FakeOrchestrator(), llm_manager=FakeLLM())

    result = mapper.map_actors_to_transactions("proj_123")

    assert result["success"] is True
    assert result["count"] == 1
    assert len(chroma.stored) == 1
    meta = chroma.stored[0]["metadata"]
    assert meta["actor_id"] == "actor_1"
    assert meta["transactions"][0]["transaction_id"] == "txn_1"
