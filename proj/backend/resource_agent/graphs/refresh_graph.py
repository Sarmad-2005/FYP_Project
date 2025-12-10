"""
Refresh Graph for Resource Agent
LangGraph state machine for refreshing resource data
"""

from typing import TypedDict, Any
from langgraph.graph import StateGraph, END

from ..nodes.task_analysis_nodes import (
    retrieve_tasks_node,
    analyze_tasks_node
)
from ..nodes.dependency_nodes import (
    create_dependencies_node
)
from ..nodes.critical_path_nodes import (
    calculate_critical_path_node
)


class ResourceRefreshState(TypedDict):
    """State for refresh workflow."""
    project_id: str
    llm_manager: Any
    chroma_manager: Any
    db_manager: Any
    a2a_router: Any
    
    # Refresh data
    new_tasks_found: bool
    tasks_retrieved: list
    task_analysis_result: dict
    dependencies_result: dict
    critical_path_result: dict
    
    # Results
    refresh_result: dict
    success: bool
    error: str


def check_new_tasks_node(state: ResourceRefreshState) -> ResourceRefreshState:
    """Check if there are new tasks to analyze"""
    try:
        project_id = state['project_id']
        chroma_manager = state['chroma_manager']
        
        from ..agents.task_optimization_agent import TaskOptimizationAgent
        task_agent = TaskOptimizationAgent(chroma_manager)
        
        # Get current tasks
        current_tasks = task_agent.get_all_project_tasks(project_id)
        
        # Get analyzed tasks
        analyzed_tasks = chroma_manager.get_resource_data('tasks_analysis', project_id)
        
        # Check if new tasks exist
        state['new_tasks_found'] = len(current_tasks) > len(analyzed_tasks)
        state['tasks_retrieved'] = current_tasks
        
        return state
        
    except Exception as e:
        state['error'] = f"Error checking new tasks: {str(e)}"
        state['new_tasks_found'] = False
        return state


def create_refresh_graph():
    """
    Create and compile the refresh graph.
    
    Returns:
        Compiled LangGraph StateGraph
    """
    # Create graph
    workflow = StateGraph(ResourceRefreshState)
    
    # Add nodes
    workflow.add_node("check_new_tasks", check_new_tasks_node)
    workflow.add_node("analyze_tasks", analyze_tasks_node)
    workflow.add_node("create_dependencies", create_dependencies_node)
    workflow.add_node("calculate_critical_path", calculate_critical_path_node)
    
    # Define edges with conditional logic
    workflow.set_entry_point("check_new_tasks")
    
    # Only process if new tasks found
    def should_process(state: ResourceRefreshState) -> str:
        if state.get('new_tasks_found', False):
            return "analyze_tasks"
        else:
            return "end"
    
    workflow.add_conditional_edges(
        "check_new_tasks",
        should_process,
        {
            "analyze_tasks": "analyze_tasks",
            "end": END
        }
    )
    
    workflow.add_edge("analyze_tasks", "create_dependencies")
    workflow.add_edge("create_dependencies", "calculate_critical_path")
    workflow.add_edge("calculate_critical_path", END)
    
    # Compile graph
    return workflow.compile()


# Create the graph instance
refresh_graph = create_refresh_graph()

