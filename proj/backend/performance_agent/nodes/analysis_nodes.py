"""
Analysis Nodes for Performance Agent
Node functions that wrap worker agent analysis methods.
"""

from typing import Dict, Any
from ..agents.milestone_agent import MilestoneAgent
from ..agents.task_agent import TaskAgent
from ..agents.bottleneck_agent import BottleneckAgent
from backend.a2a_protocol.a2a_message import A2AMessage, MessageType


def extract_details_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract details for all entities (milestones, tasks, bottlenecks).
    
    Args:
        state: Graph state
        
    Returns:
        Updated state with details_result
    """
    try:
        project_id = state.get("project_id")
        document_id = state.get("document_id")
        llm_manager = state.get("llm_manager")
        chroma_manager = state.get("chroma_manager")
        
        if not all([project_id, document_id, llm_manager, chroma_manager]):
            state["details_result"] = {'success': False, 'error': 'Missing required state fields'}
            state["error"] = 'Missing required state fields'
            return state
        
        # Initialize agents
        milestone_agent = MilestoneAgent(chroma_manager)
        task_agent = TaskAgent(chroma_manager)
        bottleneck_agent = BottleneckAgent(chroma_manager)
        
        details_summary = {
            'milestone_details_count': 0,
            'task_details_count': 0,
            'bottleneck_details_count': 0,
            'completion_statuses': []
        }
        
        # Extract milestone details
        milestones_result = state.get("milestones_result", {})
        if milestones_result.get('success') and milestones_result.get('milestones'):
            for milestone in milestones_result.get('milestones', []):
                details_result = milestone_agent.extract_milestone_details(
                    project_id, milestone.get('milestone', ''), llm_manager
                )
                if details_result.get('success'):
                    details_summary['milestone_details_count'] += 1
        
        # Extract task details and completion status
        tasks_result = state.get("tasks_result", {})
        if tasks_result.get('success') and tasks_result.get('tasks'):
            for task in tasks_result.get('tasks', []):
                # Extract task details
                details_result = task_agent.extract_task_details(
                    project_id, task.get('task', ''), llm_manager
                )
                if details_result.get('success'):
                    details_summary['task_details_count'] += 1
                
                # Determine completion status
                completion_result = task_agent.determine_task_completion_status(
                    project_id, document_id, task.get('task', ''), llm_manager
                )
                if completion_result.get('success'):
                    details_summary['completion_statuses'].append(
                        completion_result.get('completion_status', 0)
                    )
        
        # Extract bottleneck details
        bottlenecks_result = state.get("bottlenecks_result", {})
        if bottlenecks_result.get('success') and bottlenecks_result.get('bottlenecks'):
            for bottleneck in bottlenecks_result.get('bottlenecks', []):
                details_result = bottleneck_agent.extract_bottleneck_details(
                    project_id, bottleneck.get('bottleneck', ''), llm_manager
                )
                if details_result.get('success'):
                    details_summary['bottleneck_details_count'] += 1
        
        # Calculate completion score
        if details_summary['completion_statuses']:
            state["completion_score"] = sum(details_summary['completion_statuses']) / len(details_summary['completion_statuses'])
        else:
            state["completion_score"] = 0.0
        
        state["details_result"] = {
            'success': True,
            **details_summary
        }
        if "error" not in state:
            state["error"] = ""
        return state
    except Exception as e:
        state["details_result"] = {'success': False, 'error': str(e)}
        state["error"] = str(e)
        return state


def generate_suggestions_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate AI suggestions for all entities.
    
    Args:
        state: Graph state
        
    Returns:
        Updated state with suggestions_result
    """
    try:
        project_id = state.get("project_id")
        llm_manager = state.get("llm_manager")
        chroma_manager = state.get("chroma_manager")
        a2a_router = state.get("a2a_router")
        
        if not all([project_id, llm_manager, chroma_manager]):
            state["suggestions_result"] = {'success': False, 'error': 'Missing required state fields'}
            state["error"] = 'Missing required state fields'
            return state
        
        # Initialize agents
        milestone_agent = MilestoneAgent(chroma_manager)
        task_agent = TaskAgent(chroma_manager)
        bottleneck_agent = BottleneckAgent(chroma_manager)
        
        suggestions = {}
        
        # Generate milestone suggestions
        milestones_result = state.get("milestones_result", {})
        if milestones_result.get('success') and milestones_result.get('milestones'):
            milestone_suggestions = milestone_agent.generate_milestone_suggestions(
                project_id, milestones_result.get('milestones', []), llm_manager
            )
            if milestone_suggestions.get('success'):
                suggestions['milestone_suggestions'] = milestone_suggestions.get('suggestions', [])
        
        # Generate task suggestions
        tasks_result = state.get("tasks_result", {})
        if tasks_result.get('success') and tasks_result.get('tasks'):
            task_suggestions = task_agent.generate_task_suggestions(
                project_id, tasks_result.get('tasks', []), llm_manager
            )
            if task_suggestions.get('success'):
                suggestions['task_suggestions'] = task_suggestions.get('suggestions', [])
        
        # Generate bottleneck suggestions
        bottlenecks_result = state.get("bottlenecks_result", {})
        if bottlenecks_result.get('success') and bottlenecks_result.get('bottlenecks'):
            bottleneck_suggestions = bottleneck_agent.generate_bottleneck_suggestions(
                project_id, bottlenecks_result.get('bottlenecks', []), llm_manager
            )
            if bottleneck_suggestions.get('success'):
                suggestions['bottleneck_suggestions'] = bottleneck_suggestions.get('suggestions', [])
        
        # If A2A router available, request financial data if needed
        if a2a_router and a2a_router.is_agent_registered("financial-service"):
            try:
                request_msg = A2AMessage.create_request(
                    sender_agent="performance-service",
                    recipient_agent="financial-service",
                    payload={
                        "action": "get_financial_summary",
                        "project_id": project_id
                    }
                )
                response = a2a_router.send_message(request_msg)
                if response and response.message_type == MessageType.RESPONSE:
                    suggestions["financial_context"] = response.payload
            except Exception as e:
                # Non-critical, continue without financial context
                pass
        
        state["suggestions_result"] = {
            'success': True,
            'suggestions': suggestions
        }
        
        # Determine overall success
        state["overall_success"] = (
            state.get("milestones_result", {}).get("success", False) and
            state.get("tasks_result", {}).get("success", False) and
            state.get("bottlenecks_result", {}).get("success", False)
        )
        
        if "error" not in state:
            state["error"] = ""
        return state
    except Exception as e:
        state["suggestions_result"] = {'success': False, 'error': str(e)}
        state["error"] = str(e)
        return state


def update_existing_entities_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update existing entities with new document data (entity concatenation).
    
    Args:
        state: Graph state
        
    Returns:
        Updated state
    """
    try:
        project_id = state.get("project_id")
        new_documents = state.get("new_documents", [])
        llm_manager = state.get("llm_manager")
        chroma_manager = state.get("chroma_manager")
        
        if not project_id or not chroma_manager:
            state["refresh_result"]["entities_updated"] = False
            state["error"] = 'Missing required state fields'
            return state
        
        # Initialize agents
        milestone_agent = MilestoneAgent(chroma_manager)
        task_agent = TaskAgent(chroma_manager)
        bottleneck_agent = BottleneckAgent(chroma_manager)
        
        # Get existing entities
        existing_milestones = milestone_agent.get_project_milestones(project_id)
        existing_tasks = task_agent.get_project_tasks(project_id)
        existing_bottlenecks = bottleneck_agent.get_project_bottlenecks(project_id)
        
        # Update details for existing entities from new documents
        updated_count = 0
        for document in new_documents:
            document_id = document['id']
            
            # Update milestone details
            for milestone in existing_milestones:
                milestone_agent.extract_milestone_details(
                    project_id, milestone.get('milestone', ''), llm_manager
                )
                updated_count += 1
            
            # Update task details
            for task in existing_tasks:
                task_agent.extract_task_details(
                    project_id, task.get('task', ''), llm_manager
                )
                updated_count += 1
            
            # Update bottleneck details
            for bottleneck in existing_bottlenecks:
                bottleneck_agent.extract_bottleneck_details(
                    project_id, bottleneck.get('bottleneck', ''), llm_manager
                )
                updated_count += 1
        
        state["refresh_result"]["entities_updated"] = True
        state["refresh_result"]["updated_count"] = updated_count
        state["success"] = True
        return state
    except Exception as e:
        state["refresh_result"]["entities_updated"] = False
        state["error"] = str(e)
        state["success"] = False
        return state


def recalculate_completion_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recalculate completion scores after refresh.
    
    Args:
        state: Graph state
        
    Returns:
        Updated state
    """
    try:
        import os
        import json
        from datetime import datetime
        
        project_id = state.get("project_id")
        chroma_manager = state.get("chroma_manager")
        performance_data_dir = state.get("performance_data_dir", "data/performance")
        
        if not project_id or not chroma_manager:
            state["refresh_result"]["completion_recalculated"] = False
            state["error"] = 'Missing required state fields'
            return state
        
        # Get all tasks
        task_agent = TaskAgent(chroma_manager)
        tasks = task_agent.get_project_tasks(project_id)
        
        # Recalculate completion (simplified - actual logic would be more complex)
        completion_statuses = []
        for task in tasks:
            # Get completion status from task metadata if available
            metadata = task.get('metadata', {})
            completion = metadata.get('completion_status', 0)
            if isinstance(completion, (int, float)):
                completion_statuses.append(completion)
        
        if completion_statuses:
            completion_score = sum(completion_statuses) / len(completion_statuses)
        else:
            completion_score = 0.0
        
        # Update timestamp
        os.makedirs(performance_data_dir, exist_ok=True)
        update_file = os.path.join(performance_data_dir, f"{project_id}_last_update.json")
        data = {
            'project_id': project_id,
            'last_update': datetime.now().isoformat(),
            'completion_score': completion_score
        }
        with open(update_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        state["refresh_result"]["completion_recalculated"] = True
        state["refresh_result"]["completion_score"] = completion_score
        state["success"] = True
        return state
    except Exception as e:
        state["refresh_result"]["completion_recalculated"] = False
        state["error"] = str(e)
        state["success"] = False
        return state
