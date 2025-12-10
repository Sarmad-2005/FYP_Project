"""
Risk Mitigation Service
Flask service for Risk Mitigation Agent with LangGraph workflows.
"""

import sys
import os

# Add project root to path FIRST
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, project_root)

# CRITICAL: Import chromadb patch FIRST before any other imports
from backend.chromadb_patch import chromadb

from flask import Flask, request, jsonify
import logging

from backend.risk_mitigation_agent.graphs.what_if_simulator_graph import what_if_simulator_graph, WhatIfSimulatorState
from backend.risk_mitigation_agent.chroma_manager import RiskChromaManager
from backend.risk_mitigation_agent.risk_mitigation_agent import RiskMitigationAgent
from backend.risk_mitigation_agent.agents.what_if_simulator_agent import WhatIfSimulatorAgent
from backend.a2a_router.router import A2ARouter
from backend.a2a_protocol.a2a_message import A2AMessage, MessageType
from backend.llm_manager import LLMManager
from backend.embeddings import EmbeddingsManager
from backend.database import DatabaseManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Initialize managers
llm_manager = LLMManager()
embeddings_manager = EmbeddingsManager()
db_manager = DatabaseManager()
chroma_manager = RiskChromaManager()
a2a_router = A2ARouter()

# Initialize risk mitigation agent
risk_mitigation_agent = RiskMitigationAgent(
    llm_manager,
    embeddings_manager,
    db_manager,
    orchestrator=None,  # Can be added later
    performance_agent=None,  # Will be set if available
    performance_chroma_manager=None  # Will be set if available
)

# Register with A2A router
a2a_router.register_agent(
    agent_id="risk-mitigation-service",
    agent_url="http://localhost:8008",
    metadata={"service": "risk-mitigation", "version": "1.0"}
)


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "service": "risk-mitigation-service",
        "port": 8008
    }), 200


@app.route('/first_generation', methods=['POST'])
def first_generation():
    """
    First time generation of risk mitigation data for a project.
    
    Expected JSON:
    {
        "project_id": "string"
    }
    """
    try:
        data = request.get_json()
        if not data or 'project_id' not in data:
            return jsonify({"error": "project_id is required"}), 400
        
        project_id = data['project_id']
        
        # Run first-time generation
        result = risk_mitigation_agent.initialize_risk_analysis(project_id)
        
        if result.get("success"):
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Error in first_generation: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/what_if_simulator/<project_id>', methods=['GET', 'POST'])
def what_if_simulator(project_id: str):
    """
    Get What If Simulator data for a project.
    Retrieves from DB if available, otherwise generates on-demand.
    
    Args:
        project_id: Project identifier
    """
    try:
        # Use direct method call (checks DB first)
        result = risk_mitigation_agent.get_what_if_simulator_data(project_id)
        
        if result.get("success"):
            return jsonify(result), 200
        else:
            return jsonify(result), 400
        
    except Exception as e:
        logger.error(f"Error in what_if_simulator: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/mitigation/<project_id>/<bottleneck_id>', methods=['POST'])
def get_mitigation(project_id: str, bottleneck_id: str):
    """
    Get mitigation suggestions for a bottleneck.
    
    Args:
        project_id: Project identifier
        bottleneck_id: Bottleneck identifier
    """
    try:
        result = risk_mitigation_agent.get_mitigation_suggestions(project_id, bottleneck_id)
        
        if result.get("success"):
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Error in get_mitigation: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/consequences/<project_id>/<bottleneck_id>', methods=['POST'])
def get_consequences(project_id: str, bottleneck_id: str):
    """
    Get consequences for a bottleneck.
    
    Args:
        project_id: Project identifier
        bottleneck_id: Bottleneck identifier
    """
    try:
        result = risk_mitigation_agent.get_consequences(project_id, bottleneck_id)
        
        if result.get("success"):
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Error in get_consequences: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/risk_summary/<project_id>', methods=['GET'])
def risk_summary(project_id: str):
    """
    Get risk summary for a project.
    
    Args:
        project_id: Project identifier
    """
    try:
        result = risk_mitigation_agent.get_risk_summary(project_id)
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error in risk_summary: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/a2a/message', methods=['POST'])
def handle_a2a_message():
    """
    Handle A2A protocol messages (e.g., requests from other services).
    
    Expected JSON: A2AMessage dictionary
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body is required"}), 400
        
        message = A2AMessage.from_dict(data)
        
        # Handle different action types
        if message.message_type == MessageType.REQUEST:
            action = message.payload.get("action")
            project_id = message.payload.get("project_id")
            
            if action == "get_what_if_simulator":
                if not project_id:
                    return jsonify({"error": "project_id required"}), 400
                
                # Get What If Simulator data
                result = risk_mitigation_agent.get_what_if_simulator_data(project_id)
                
                response_msg = A2AMessage.create_response(
                    sender_agent="risk-mitigation-service",
                    recipient_agent=message.sender_agent,
                    payload=result,
                    correlation_id=message.message_id
                )
                
                return jsonify(response_msg.to_dict()), 200
            
            elif action == "get_mitigation":
                bottleneck_id = message.payload.get("bottleneck_id")
                if not project_id or not bottleneck_id:
                    return jsonify({"error": "project_id and bottleneck_id required"}), 400
                
                result = risk_mitigation_agent.get_mitigation_suggestions(project_id, bottleneck_id)
                
                response_msg = A2AMessage.create_response(
                    sender_agent="risk-mitigation-service",
                    recipient_agent=message.sender_agent,
                    payload=result,
                    correlation_id=message.message_id
                )
                
                return jsonify(response_msg.to_dict()), 200
            
            elif action == "get_consequences":
                bottleneck_id = message.payload.get("bottleneck_id")
                if not project_id or not bottleneck_id:
                    return jsonify({"error": "project_id and bottleneck_id required"}), 400
                
                result = risk_mitigation_agent.get_consequences(project_id, bottleneck_id)
                
                response_msg = A2AMessage.create_response(
                    sender_agent="risk-mitigation-service",
                    recipient_agent=message.sender_agent,
                    payload=result,
                    correlation_id=message.message_id
                )
                
                return jsonify(response_msg.to_dict()), 200
            
            elif action == "get_risk_summary":
                if not project_id:
                    return jsonify({"error": "project_id required"}), 400
                
                result = risk_mitigation_agent.get_risk_summary(project_id)
                
                response_msg = A2AMessage.create_response(
                    sender_agent="risk-mitigation-service",
                    recipient_agent=message.sender_agent,
                    payload=result,
                    correlation_id=message.message_id
                )
                
                return jsonify(response_msg.to_dict()), 200
        
        return jsonify({"error": "Unknown action"}), 400
        
    except Exception as e:
        logger.error(f"Error handling A2A message: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    logger.info("Starting Risk Mitigation Service on port 8008")
    app.run(host='0.0.0.0', port=8008, debug=True)

