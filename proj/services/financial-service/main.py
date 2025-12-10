"""
Financial Service
Flask service for Financial Agent with LangGraph workflows.
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

from backend.financial_agent.graphs.first_time_generation_graph import first_time_generation_graph, FirstTimeGenerationState
from backend.financial_agent.graphs.refresh_graph import refresh_graph, RefreshState
from backend.financial_agent.chroma_manager import FinancialChromaManager
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
chroma_manager = FinancialChromaManager()
a2a_router = A2ARouter()

# Register with A2A router
a2a_router.register_agent(
    agent_id="financial-service",
    agent_url="http://localhost:8001",
    metadata={"service": "financial", "version": "1.0"}
)


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "service": "financial-service",
        "port": 8001
    }), 200


@app.route('/first_generation', methods=['POST'])
def first_generation():
    """
    First time generation of financial data for a project.
    
    Expected JSON:
    {
        "project_id": "string",
        "document_id": "string"
    }
    """
    try:
        data = request.get_json()
        if not data or 'project_id' not in data or 'document_id' not in data:
            return jsonify({"error": "project_id and document_id are required"}), 400
        
        project_id = data['project_id']
        document_id = data['document_id']
        
        # Initialize state
        initial_state: FirstTimeGenerationState = {
            "project_id": project_id,
            "document_id": document_id,
            "llm_manager": llm_manager,
            "embeddings_manager": embeddings_manager,
            "chroma_manager": chroma_manager,
            "orchestrator": None,  # Can be added later
            "a2a_router": a2a_router,
            "financial_details_result": {},
            "transactions_result": {},
            "expenses_result": {},
            "revenue_result": {},
            "anomaly_result": {},
            "overall_success": False,
            "error": ""
        }
        
        # Run graph
        result = first_time_generation_graph.invoke(initial_state)
        
        # Format response
        response = {
            "success": result.get("overall_success", False),
            "project_id": project_id,
            "document_id": document_id,
            "financial_details": result.get("financial_details_result", {}),
            "transactions": result.get("transactions_result", {}),
            "expenses": result.get("expenses_result", {}),
            "revenue": result.get("revenue_result", {}),
            "anomaly_detection": result.get("anomaly_result", {})
        }
        
        if result.get("error"):
            response["error"] = result["error"]
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Error in first_generation: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/refresh/<project_id>', methods=['POST'])
def refresh(project_id: str):
    """
    Refresh financial data for a project.
    
    Args:
        project_id: Project identifier
    """
    try:
        # Initialize state
        initial_state: RefreshState = {
            "project_id": project_id,
            "llm_manager": llm_manager,
            "embeddings_manager": embeddings_manager,
            "chroma_manager": chroma_manager,
            "db_manager": db_manager,
            "orchestrator": None,
            "a2a_router": a2a_router,
            "new_documents": [],
            "last_update": "",
            "refresh_result": {},
            "success": False,
            "error": "",
            "financial_data_dir": "data/financial"
        }
        
        # Run graph
        result = refresh_graph.invoke(initial_state)
        
        # Format response
        response = {
            "success": result.get("success", False),
            "project_id": project_id,
            "new_documents_processed": len(result.get("new_documents", [])),
            "refresh_result": result.get("refresh_result", {})
        }
        
        if result.get("error"):
            response["error"] = result["error"]
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Error in refresh: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/status/<project_id>', methods=['GET'])
def status(project_id: str):
    """
    Get financial status for a project.
    
    Args:
        project_id: Project identifier
    """
    try:
        # Get current financial data
        financial_details = chroma_manager.get_financial_data('financial_details', project_id)
        transactions = chroma_manager.get_financial_data('transactions', project_id)
        
        # Calculate totals
        total_expenses = sum(
            float(t.get('metadata', {}).get('amount', 0))
            for t in transactions
            if t.get('metadata', {}).get('transaction_type') == 'expense'
        )
        
        total_revenue = sum(
            float(t.get('metadata', {}).get('amount', 0))
            for t in transactions
            if t.get('metadata', {}).get('transaction_type') == 'revenue'
        )
        
        response = {
            "project_id": project_id,
            "financial_details_count": len(financial_details),
            "transactions_count": len(transactions),
            "total_expenses": total_expenses,
            "total_revenue": total_revenue
        }
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Error in status: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/a2a/message', methods=['POST'])
def handle_a2a_message():
    """
    Handle A2A protocol messages (e.g., refresh requests from scheduler).
    
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
            
            if action == "refresh":
                if project_id:
                    # Trigger refresh
                    initial_state: RefreshState = {
                        "project_id": project_id,
                        "llm_manager": llm_manager,
                        "embeddings_manager": embeddings_manager,
                        "chroma_manager": chroma_manager,
                        "db_manager": db_manager,
                        "orchestrator": None,
                        "a2a_router": a2a_router,
                        "new_documents": [],
                        "last_update": "",
                        "refresh_result": {},
                        "success": False,
                        "error": "",
                        "financial_data_dir": "data/financial"
                    }
                    
                    result = refresh_graph.invoke(initial_state)
                    
                    # Send response
                    response_msg = A2AMessage.create_response(
                        sender_agent="financial-service",
                        recipient_agent=message.sender_agent,
                        payload={
                            "success": result.get("success", False),
                            "project_id": project_id
                        },
                        correlation_id=message.message_id
                    )
                    
                    return jsonify(response_msg.to_dict()), 200
            
            elif action == "get_financial_data":
                # Get financial data (expenses, revenue, budget, health)
                data_type = message.payload.get("data_type")
                if not project_id or not data_type:
                    return jsonify({"error": "project_id and data_type required"}), 400
                
                try:
                    from backend.financial_agent.data_interface import FinancialDataInterface
                    from backend.financial_agent.financial_agent import FinancialAgent
                    
                    # Create temporary financial agent for data access
                    financial_agent = FinancialAgent(llm_manager, embeddings_manager, db_manager)
                    fin_interface = FinancialDataInterface(financial_agent)
                    
                    if data_type == "expenses":
                        data = fin_interface.get_expenses(project_id)
                    elif data_type == "revenue":
                        data = fin_interface.get_revenue(project_id)
                    elif data_type == "budget":
                        data = fin_interface.get_budget_info(project_id)
                    elif data_type == "health":
                        data = fin_interface.get_financial_health(project_id)
                    else:
                        return jsonify({"error": f"Unknown data_type: {data_type}"}), 400
                    
                    response_msg = A2AMessage.create_response(
                        sender_agent="financial-service",
                        recipient_agent=message.sender_agent,
                        payload={"data": data},
                        correlation_id=message.message_id
                    )
                    
                    return jsonify(response_msg.to_dict()), 200
                except Exception as e:
                    logger.error(f"Error getting financial data: {e}")
                    error_msg = A2AMessage.create_error(
                        sender_agent="financial-service",
                        recipient_agent=message.sender_agent,
                        error_message=str(e),
                        correlation_id=message.message_id
                    )
                    return jsonify(error_msg.to_dict()), 500
            
            elif action == "get_transactions":
                # Get transactions with optional filters
                filters = message.payload.get("filters")
                if not project_id:
                    return jsonify({"error": "project_id required"}), 400
                
                try:
                    from backend.financial_agent.data_interface import FinancialDataInterface
                    from backend.financial_agent.financial_agent import FinancialAgent
                    
                    financial_agent = FinancialAgent(llm_manager, embeddings_manager, db_manager)
                    fin_interface = FinancialDataInterface(financial_agent)
                    
                    transactions = fin_interface.get_transactions(project_id, filters)
                    
                    response_msg = A2AMessage.create_response(
                        sender_agent="financial-service",
                        recipient_agent=message.sender_agent,
                        payload={"transactions": transactions},
                        correlation_id=message.message_id
                    )
                    
                    return jsonify(response_msg.to_dict()), 200
                except Exception as e:
                    logger.error(f"Error getting transactions: {e}")
                    error_msg = A2AMessage.create_error(
                        sender_agent="financial-service",
                        recipient_agent=message.sender_agent,
                        error_message=str(e),
                        correlation_id=message.message_id
                    )
                    return jsonify(error_msg.to_dict()), 500
            
            elif action == "get_anomalies":
                # Get anomalies
                severity_filter = message.payload.get("severity_filter", "all")
                if not project_id:
                    return jsonify({"error": "project_id required"}), 400
                
                try:
                    from backend.financial_agent.agents.anomaly_detection_agent import AnomalyDetectionAgent
                    
                    anomaly_agent = AnomalyDetectionAgent(chroma_manager)
                    result = anomaly_agent.get_anomalies(project_id, severity_filter)
                    
                    response_msg = A2AMessage.create_response(
                        sender_agent="financial-service",
                        recipient_agent=message.sender_agent,
                        payload={"result": result},
                        correlation_id=message.message_id
                    )
                    
                    return jsonify(response_msg.to_dict()), 200
                except Exception as e:
                    logger.error(f"Error getting anomalies: {e}")
                    error_msg = A2AMessage.create_error(
                        sender_agent="financial-service",
                        recipient_agent=message.sender_agent,
                        error_message=str(e),
                        correlation_id=message.message_id
                    )
                    return jsonify(error_msg.to_dict()), 500
        
        return jsonify({"error": "Unknown action"}), 400
        
    except Exception as e:
        logger.error(f"Error handling A2A message: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    logger.info("Starting Financial Service on port 8001")
    app.run(host='0.0.0.0', port=8001, debug=True)
