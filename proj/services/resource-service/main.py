"""
Resource Service
Flask service for Resource Agent with LangGraph workflows.
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

from backend.resource_agent.graphs.first_time_generation_graph import first_time_generation_graph, ResourceGenerationState
from backend.resource_agent.graphs.refresh_graph import refresh_graph, ResourceRefreshState
from backend.resource_agent.chroma_manager import ResourceChromaManager
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
chroma_manager = ResourceChromaManager()
a2a_router = A2ARouter()

# Register with A2A router
a2a_router.register_agent(
    agent_id="resource-service",
    agent_url="http://localhost:8004",
    metadata={"service": "resource", "version": "1.0"}
)


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "service": "resource-service",
        "port": 8004
    }), 200


@app.route('/first_generation', methods=['POST'])
def first_generation():
    """
    First time generation of resource data for a project.
    
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
        initial_state: ResourceGenerationState = {
            "project_id": project_id,
            "document_id": document_id,
            "llm_manager": llm_manager,
            "embeddings_manager": embeddings_manager,
            "chroma_manager": chroma_manager,
            "db_manager": db_manager,
            "orchestrator": None,
            "a2a_router": a2a_router,
            "tasks_retrieved": [],
            "tasks_count": 0,
            "task_analysis_result": {},
            "dependencies_result": {},
            "critical_path_result": {},
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
            "task_analysis": result.get("task_analysis_result", {}),
            "dependencies": result.get("dependencies_result", {}),
            "critical_path": result.get("critical_path_result", {})
        }
        
        if result.get("error"):
            response["error"] = result["error"]
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Error in first_generation: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/tasks/<project_id>', methods=['GET'])
def get_tasks(project_id: str):
    """Get task analysis for a project"""
    try:
        from backend.resource_agent.resource_agent import ResourceAgent
        resource_agent = ResourceAgent(llm_manager, embeddings_manager, db_manager)
        tasks = resource_agent.get_task_analysis(project_id)
        return jsonify({'tasks': tasks}), 200
    except Exception as e:
        logger.error(f"Error fetching tasks: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/dependencies/<project_id>', methods=['GET'])
def get_dependencies(project_id: str):
    """Get task dependencies for a project"""
    try:
        from backend.resource_agent.resource_agent import ResourceAgent
        resource_agent = ResourceAgent(llm_manager, embeddings_manager, db_manager)
        dependencies = resource_agent.get_task_dependencies(project_id)
        return jsonify({'dependencies': dependencies}), 200
    except Exception as e:
        logger.error(f"Error fetching dependencies: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/critical_path/<project_id>', methods=['GET'])
def get_critical_path(project_id: str):
    """Get critical path for a project"""
    try:
        from backend.resource_agent.resource_agent import ResourceAgent
        resource_agent = ResourceAgent(llm_manager, embeddings_manager, db_manager)
        critical_path = resource_agent.get_critical_path(project_id)
        return jsonify({'critical_path': critical_path}), 200
    except Exception as e:
        logger.error(f"Error fetching critical path: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/work_team/<project_id>', methods=['GET'])
def get_work_team(project_id: str):
    """Get work team for a project"""
    try:
        from backend.resource_agent.resource_agent import ResourceAgent
        resource_agent = ResourceAgent(llm_manager, embeddings_manager, db_manager)
        work_team = resource_agent.get_work_team(project_id)
        return jsonify({'work_team': work_team}), 200
    except Exception as e:
        logger.error(f"Error fetching work team: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/work_team/<project_id>', methods=['POST'])
def add_work_team_member(project_id: str):
    """Add a work team member"""
    try:
        data = request.get_json()
        if not data or 'name' not in data:
            return jsonify({"error": "name is required"}), 400
        
        from backend.resource_agent.resource_agent import ResourceAgent
        resource_agent = ResourceAgent(llm_manager, embeddings_manager, db_manager)
        
        result = resource_agent.resource_optimization_agent.add_work_team_member(
            project_id,
            data['name'],
            data.get('type', 'person')
        )
        
        return jsonify(result), 200 if result.get('success') else 500
        
    except Exception as e:
        logger.error(f"Error adding work team member: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/work_team/<team_member_id>', methods=['PUT'])
def update_work_team_member(team_member_id: str):
    """Update a work team member"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body is required"}), 400
        
        from backend.resource_agent.resource_agent import ResourceAgent
        resource_agent = ResourceAgent(llm_manager, embeddings_manager, db_manager)
        
        success = resource_agent.resource_optimization_agent.update_work_team_member(
            team_member_id,
            data
        )
        
        return jsonify({'success': success}), 200 if success else 500
        
    except Exception as e:
        logger.error(f"Error updating work team member: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/work_team/<team_member_id>', methods=['DELETE'])
def delete_work_team_member(team_member_id: str):
    """Delete a work team member"""
    try:
        from backend.resource_agent.resource_agent import ResourceAgent
        resource_agent = ResourceAgent(llm_manager, embeddings_manager, db_manager)
        
        success = resource_agent.resource_optimization_agent.delete_work_team_member(team_member_id)
        
        return jsonify({'success': success}), 200 if success else 500
        
    except Exception as e:
        logger.error(f"Error deleting work team member: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/financial_summary/<project_id>', methods=['GET'])
def get_financial_summary(project_id: str):
    """Get financial summary for resource allocation"""
    try:
        from backend.resource_agent.resource_agent import ResourceAgent
        resource_agent = ResourceAgent(llm_manager, embeddings_manager, db_manager)
        summary = resource_agent.get_financial_summary(project_id)
        return jsonify(summary), 200
    except Exception as e:
        logger.error(f"Error fetching financial summary: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/assign_resources/<project_id>', methods=['POST'])
def assign_resources(project_id: str):
    """AI-based resource assignment"""
    try:
        from backend.resource_agent.resource_agent import ResourceAgent
        resource_agent = ResourceAgent(llm_manager, embeddings_manager, db_manager)
        
        result = resource_agent.resource_optimization_agent.assign_resources_ai(
            project_id,
            llm_manager
        )
        
        return jsonify(result), 200 if result.get('success') else 500
        
    except Exception as e:
        logger.error(f"Error assigning resources: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/resource_assignment/<team_member_id>', methods=['PUT'])
def update_resource_assignment(team_member_id: str):
    """Manually update resource assignment"""
    try:
        data = request.get_json()
        if not data or 'amount' not in data:
            return jsonify({"error": "amount is required"}), 400
        
        from backend.resource_agent.resource_agent import ResourceAgent
        resource_agent = ResourceAgent(llm_manager, embeddings_manager, db_manager)
        
        success = resource_agent.resource_optimization_agent.update_resource_assignment(
            team_member_id,
            float(data['amount'])
        )
        
        return jsonify({'success': success}), 200 if success else 500
        
    except Exception as e:
        logger.error(f"Error updating resource assignment: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/refresh/<project_id>', methods=['POST'])
def refresh(project_id: str):
    """
    Refresh resource data for a project.
    
    Args:
        project_id: Project identifier
    """
    try:
        # Initialize state
        initial_state: ResourceRefreshState = {
            "project_id": project_id,
            "llm_manager": llm_manager,
            "chroma_manager": chroma_manager,
            "db_manager": db_manager,
            "a2a_router": a2a_router,
            "new_tasks_found": False,
            "tasks_retrieved": [],
            "task_analysis_result": {},
            "dependencies_result": {},
            "critical_path_result": {},
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
            "new_tasks_found": result.get("new_tasks_found", False),
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
    Get resource status for a project.
    
    Args:
        project_id: Project identifier
    """
    try:
        from backend.resource_agent.resource_agent import ResourceAgent
        resource_agent = ResourceAgent(llm_manager, embeddings_manager, db_manager)
        
        status_data = resource_agent._get_current_resource_data(project_id)
        
        return jsonify(status_data), 200
        
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
                    initial_state: ResourceRefreshState = {
                        "project_id": project_id,
                        "llm_manager": llm_manager,
                        "chroma_manager": chroma_manager,
                        "db_manager": db_manager,
                        "a2a_router": a2a_router,
                        "new_tasks_found": False,
                        "tasks_retrieved": [],
                        "task_analysis_result": {},
                        "dependencies_result": {},
                        "critical_path_result": {},
                        "refresh_result": {},
                        "success": False,
                        "error": ""
                    }
                    
                    result = refresh_graph.invoke(initial_state)
                    
                    # Send response
                    response_msg = A2AMessage.create_response(
                        sender_agent="resource-service",
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
    logger.info("Starting Resource Service on port 8004")
    app.run(host='0.0.0.0', port=8004, debug=True)

