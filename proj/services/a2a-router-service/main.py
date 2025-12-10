"""
A2A Router Service
Flask service exposing A2A router functionality via HTTP endpoints.
"""

import sys
import os
from flask import Flask, request, jsonify
import logging

# Add project root to path to import backend modules
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, project_root)

from backend.a2a_router.router import A2ARouter
from backend.a2a_protocol.a2a_message import A2AMessage, MessageType, Priority

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
router = A2ARouter()


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "service": "a2a-router",
        "agents_registered": len(router.list_agents())
    }), 200


@app.route('/register', methods=['POST'])
def register_agent():
    """
    Register an agent with the router.
    
    Expected JSON:
    {
        "agent_id": "string",
        "agent_url": "string (optional)",
        "metadata": {} (optional)
    }
    """
    try:
        data = request.get_json()
        if not data or 'agent_id' not in data:
            return jsonify({"error": "agent_id is required"}), 400
        
        router.register_agent(
            agent_id=data['agent_id'],
            agent_url=data.get('agent_url'),
            metadata=data.get('metadata')
        )
        
        return jsonify({
            "status": "success",
            "message": f"Agent {data['agent_id']} registered successfully"
        }), 201
    except Exception as e:
        logger.error(f"Error registering agent: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/unregister/<agent_id>', methods=['DELETE'])
def unregister_agent(agent_id):
    """Unregister an agent."""
    try:
        router.unregister_agent(agent_id)
        return jsonify({
            "status": "success",
            "message": f"Agent {agent_id} unregistered"
        }), 200
    except Exception as e:
        logger.error(f"Error unregistering agent: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/agents', methods=['GET'])
def list_agents():
    """List all registered agents."""
    try:
        agents = router.list_agents()
        agents_info = {
            agent_id: router.get_agent_info(agent_id)
            for agent_id in agents
        }
        return jsonify({
            "agents": agents_info,
            "count": len(agents)
        }), 200
    except Exception as e:
        logger.error(f"Error listing agents: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/send', methods=['POST'])
def send_message():
    """
    Send an A2A message.
    
    Expected JSON: A2AMessage dictionary
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body is required"}), 400
        
        # Create message from dictionary
        message = A2AMessage.from_dict(data)
        
        # Send message
        response = router.send_message(message)
        
        if response:
            return jsonify({
                "status": "success",
                "response": response.to_dict()
            }), 200
        else:
            return jsonify({
                "status": "success",
                "message": "Message sent, no response required"
            }), 200
    except ValueError as e:
        return jsonify({"error": f"Invalid message: {str(e)}"}), 400
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/history', methods=['GET'])
def get_history():
    """
    Get message history.
    
    Query parameters:
    - limit: Maximum number of messages (optional)
    - agent_id: Filter by agent ID (optional)
    - message_type: Filter by message type (optional)
    """
    try:
        limit = request.args.get('limit', type=int)
        agent_id = request.args.get('agent_id')
        message_type_str = request.args.get('message_type')
        
        message_type = None
        if message_type_str:
            try:
                message_type = MessageType(message_type_str)
            except ValueError:
                return jsonify({"error": f"Invalid message_type: {message_type_str}"}), 400
        
        history = router.get_message_history(
            limit=limit,
            agent_id=agent_id,
            message_type=message_type
        )
        
        return jsonify({
            "history": history,
            "count": len(history)
        }), 200
    except Exception as e:
        logger.error(f"Error getting history: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/stats', methods=['GET'])
def get_stats():
    """Get router statistics."""
    try:
        stats = router.get_stats()
        return jsonify(stats), 200
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/clear-history', methods=['POST'])
def clear_history():
    """Clear message history."""
    try:
        router.clear_history()
        return jsonify({
            "status": "success",
            "message": "History cleared"
        }), 200
    except Exception as e:
        logger.error(f"Error clearing history: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    logger.info("Starting A2A Router Service on port 8004")
    app.run(host='0.0.0.0', port=8004, debug=True)
