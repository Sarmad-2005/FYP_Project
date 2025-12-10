"""
Performance Service
Flask service for Performance Agent with LangGraph workflows.
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

from backend.performance_agent.graphs.first_time_generation_graph import first_time_generation_graph, PerformanceGenerationState
from backend.performance_agent.graphs.refresh_graph import refresh_graph, PerformanceRefreshState
from backend.performance_agent.chroma_manager import PerformanceChromaManager
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
chroma_manager = PerformanceChromaManager()
a2a_router = A2ARouter()

# Register with A2A router
a2a_router.register_agent(
    agent_id="performance-service",
    agent_url="http://localhost:8002",
    metadata={"service": "performance", "version": "1.0"}
)


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "service": "performance-service",
        "port": 8002
    }), 200


@app.route('/first_generation', methods=['POST'])
def first_generation():
    """
    First time generation of performance data for a project.
    
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
        initial_state: PerformanceGenerationState = {
            "project_id": project_id,
            "document_id": document_id,
            "llm_manager": llm_manager,
            "embeddings_manager": embeddings_manager,
            "chroma_manager": chroma_manager,
            "db_manager": db_manager,
            "orchestrator": None,  # Can be added later
            "a2a_router": a2a_router,
            "milestones_result": {},
            "tasks_result": {},
            "bottlenecks_result": {},
            "requirements_result": {},
            "actors_result": {},
            "details_result": {},
            "suggestions_result": {},
            "completion_score": 0.0,
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
            "milestones": result.get("milestones_result", {}),
            "tasks": result.get("tasks_result", {}),
            "bottlenecks": result.get("bottlenecks_result", {}),
            "requirements": result.get("requirements_result", {}),
            "actors": result.get("actors_result", {}),
            "details": result.get("details_result", {}),
            "suggestions": result.get("suggestions_result", {}),
            "completion_score": result.get("completion_score", 0.0)
        }
        
        if result.get("error"):
            response["error"] = result["error"]
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Error in first_generation: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/extract_requirements', methods=['POST'])
def extract_requirements():
    """Extract requirements from a document"""
    try:
        data = request.get_json()
        project_id = data.get('project_id')
        document_id = data.get('document_id')
        if not all([project_id, document_id]):
            return jsonify({"error": "project_id and document_id are required"}), 400
        # Directly use agent (PerformanceAgent coordinates internally)
        from backend.performance_agent.performance_agent import PerformanceAgent
        perf_agent = PerformanceAgent(llm_manager, embeddings_manager, db_manager)
        result = perf_agent.requirements_agent.extract_requirements_from_document(project_id, document_id, llm_manager)
        return jsonify(result), 200 if result.get('success') else 500
    except Exception as e:
        logger.error(f"Error in extract_requirements: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/extract_actors', methods=['POST'])
def extract_actors():
    """Extract actors/stakeholders from a document"""
    try:
        data = request.get_json()
        project_id = data.get('project_id')
        document_id = data.get('document_id')
        if not all([project_id, document_id]):
            return jsonify({"error": "project_id and document_id are required"}), 400
        from backend.performance_agent.performance_agent import PerformanceAgent
        perf_agent = PerformanceAgent(llm_manager, embeddings_manager, db_manager)
        result = perf_agent.actors_agent.extract_actors_from_document(project_id, document_id, llm_manager)
        return jsonify(result), 200 if result.get('success') else 500
    except Exception as e:
        logger.error(f"Error in extract_actors: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/requirements/<project_id>', methods=['GET'])
def get_requirements(project_id: str):
    """Get requirements for a project"""
    try:
        data = chroma_manager.get_performance_data('requirements', project_id)
        return jsonify({'requirements': data}), 200
    except Exception as e:
        logger.error(f"Error fetching requirements: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/actors/<project_id>', methods=['GET'])
def get_actors(project_id: str):
    """Get actors/stakeholders for a project"""
    try:
        data = chroma_manager.get_performance_data('actors', project_id)
        return jsonify({'actors': data}), 200
    except Exception as e:
        logger.error(f"Error fetching actors: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/refresh/<project_id>', methods=['POST'])
def refresh(project_id: str):
    """
    Refresh performance data for a project.
    
    Args:
        project_id: Project identifier
    """
    try:
        # Initialize state
        initial_state: PerformanceRefreshState = {
            "project_id": project_id,
            "llm_manager": llm_manager,
            "embeddings_manager": embeddings_manager,
            "chroma_manager": chroma_manager,
            "db_manager": db_manager,
            "orchestrator": None,
            "a2a_router": a2a_router,
            "performance_data_dir": "data/performance",
            "new_documents": [],
            "last_update": "",
            "refresh_result": {},
            "success": False,
            "error": ""
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
    Get performance status for a project.
    
    Args:
        project_id: Project identifier
    """
    try:
        from backend.performance_agent.agents.milestone_agent import MilestoneAgent
        from backend.performance_agent.agents.task_agent import TaskAgent
        from backend.performance_agent.agents.bottleneck_agent import BottleneckAgent
        
        # Get entities
        milestone_agent = MilestoneAgent(chroma_manager)
        task_agent = TaskAgent(chroma_manager)
        bottleneck_agent = BottleneckAgent(chroma_manager)
        
        milestones = milestone_agent.get_project_milestones(project_id)
        tasks = task_agent.get_project_tasks(project_id)
        bottlenecks = bottleneck_agent.get_project_bottlenecks(project_id)
        
        response = {
            "project_id": project_id,
            "milestones_count": len(milestones),
            "tasks_count": len(tasks),
            "bottlenecks_count": len(bottlenecks)
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
        
        # Handle refresh request
        if message.message_type == MessageType.REQUEST:
            if message.payload.get("action") == "refresh":
                project_id = message.payload.get("project_id")
                if project_id:
                    # Trigger refresh
                    initial_state: PerformanceRefreshState = {
                        "project_id": project_id,
                        "llm_manager": llm_manager,
                        "embeddings_manager": embeddings_manager,
                        "chroma_manager": chroma_manager,
                        "db_manager": db_manager,
                        "orchestrator": None,
                        "a2a_router": a2a_router,
                        "performance_data_dir": "data/performance",
                        "new_documents": [],
                        "last_update": "",
                        "refresh_result": {},
                        "success": False,
                        "error": ""
                    }
                    
                    result = refresh_graph.invoke(initial_state)
                    
                    # Send response
                    response_msg = A2AMessage.create_response(
                        sender_agent="performance-service",
                        recipient_agent=message.sender_agent,
                        payload={
                            "success": result.get("success", False),
                            "project_id": project_id
                        },
                        correlation_id=message.message_id
                    )
                    
                    return jsonify(response_msg.to_dict()), 200
        
        return jsonify({"error": "Unknown action"}), 400
        
    except Exception as e:
        logger.error(f"Error handling A2A message: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    logger.info("Starting Performance Service on port 8002")
    app.run(host='0.0.0.0', port=8002, debug=True)
