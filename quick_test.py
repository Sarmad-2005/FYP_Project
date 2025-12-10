"""Quick test to verify Phase 1 implementation."""
from backend.a2a_protocol.a2a_message import A2AMessage, MessageType, Priority
from backend.a2a_router.router import A2ARouter

# Test message creation
msg = A2AMessage.create_request('sender', 'recipient', {'test': 'data'})
print(f"✓ Message created: {msg.message_id[:8]}...")
print(f"✓ Type: {msg.message_type.value}")

# Test router
router = A2ARouter()
router.register_agent('test_agent', agent_url='http://localhost:8001')
print(f"✓ Agent registered: {router.is_agent_registered('test_agent')}")

# Test serialization
json_str = msg.to_json()
restored = A2AMessage.from_json(json_str)
print(f"✓ Serialization works: {restored.sender_agent == msg.sender_agent}")

print("\n✓ Phase 1 basic functionality verified!")
