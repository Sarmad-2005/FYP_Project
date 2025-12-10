"""
CSV Analysis Service
Flask service for CSV Analysis Agent with A2A integration.
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

from backend.csv_analysis_agent.csv_analysis_agent import CSVAnalysisAgent
from backend.a2a_router.router import A2ARouter
from backend.a2a_protocol.a2a_message import A2AMessage, MessageType
from backend.llm_manager import LLMManager
from backend.financial_agent.agents.anomaly_detection_agent import AnomalyDetectionAgent
from backend.financial_agent.chroma_manager import FinancialChromaManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Initialize managers
llm_manager = LLMManager()
a2a_router = A2ARouter()
chroma_manager = FinancialChromaManager()
anomaly_agent = AnomalyDetectionAgent(chroma_manager)

# Initialize CSV Analysis Agent with A2A router
csv_analysis_agent = CSVAnalysisAgent(llm_manager, a2a_router, anomaly_agent)

# Register with A2A router
a2a_router.register_agent(
    agent_id="csv-analysis-service",
    agent_url="http://localhost:8003",
    metadata={"service": "csv-analysis", "version": "1.0"}
)


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "service": "csv-analysis-service",
        "port": 8003
    }), 200


@app.route('/upload', methods=['POST'])
def upload():
    """
    Upload and process CSV file.
    
    Expected form data:
    - project_id: Project identifier
    - file: CSV file
    """
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400
        
        project_id = request.form.get('project_id')
        if not project_id:
            return jsonify({"error": "project_id is required"}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400
        
        # Save uploaded file temporarily
        import tempfile
        import uuid
        temp_dir = tempfile.gettempdir()
        temp_filename = f"{uuid.uuid4()}_{file.filename}"
        temp_path = os.path.join(temp_dir, temp_filename)
        file.save(temp_path)
        
        try:
            # Process CSV
            result = csv_analysis_agent.upload_csv(project_id, temp_path)
            
            # Clean up temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)
            
            return jsonify(result), 200
            
        except Exception as e:
            # Clean up temp file on error
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise e
        
    except Exception as e:
        logger.error(f"Error in upload: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/ask', methods=['POST'])
def ask():
    """
    Ask a question about CSV data.
    
    Expected JSON:
    {
        "project_id": "string",
        "session_id": "string",
        "question": "string",
        "selected_cells": [] (optional)
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body is required"}), 400
        
        project_id = data.get('project_id')
        session_id = data.get('session_id')
        question = data.get('question')
        selected_cells = data.get('selected_cells', [])
        
        if not all([project_id, session_id, question]):
            return jsonify({"error": "project_id, session_id, and question are required"}), 400
        
        # Ask question
        result = csv_analysis_agent.ask_question(
            project_id, session_id, question, selected_cells
        )
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error in ask: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/export', methods=['POST'])
def export():
    """
    Export CSV data.
    
    Expected JSON:
    {
        "project_id": "string",
        "session_id": "string"
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body is required"}), 400
        
        project_id = data.get('project_id')
        session_id = data.get('session_id')
        
        if not all([project_id, session_id]):
            return jsonify({"error": "project_id and session_id are required"}), 400
        
        # Export CSV
        result = csv_analysis_agent.export_csv(project_id, session_id)
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error in export: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/data', methods=['GET'])
def get_data():
    """
    Get CSV data for a session.
    
    Query parameters:
    - project_id: Project identifier
    - session_id: Session identifier
    """
    try:
        project_id = request.args.get('project_id')
        session_id = request.args.get('session_id')
        
        if not all([project_id, session_id]):
            return jsonify({"error": "project_id and session_id are required"}), 400
        
        # Get CSV data
        result = csv_analysis_agent.get_csv_data(project_id, session_id)
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error in get_data: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/a2a/message', methods=['POST'])
def handle_a2a_message():
    """
    Handle A2A protocol messages.
    
    Expected JSON: A2AMessage dictionary
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body is required"}), 400
        
        message = A2AMessage.from_dict(data)
        
        # Handle requests (if needed in future)
        if message.message_type == MessageType.REQUEST:
            # For now, just acknowledge
            response_msg = A2AMessage.create_response(
                sender_agent="csv-analysis-service",
                recipient_agent=message.sender_agent,
                payload={"status": "received"},
                correlation_id=message.message_id
            )
            
            return jsonify(response_msg.to_dict()), 200
        
        return jsonify({"error": "Unknown message type"}), 400
        
    except Exception as e:
        logger.error(f"Error handling A2A message: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    logger.info("Starting CSV Analysis Service on port 8003")
    app.run(host='0.0.0.0', port=8003, debug=True)
