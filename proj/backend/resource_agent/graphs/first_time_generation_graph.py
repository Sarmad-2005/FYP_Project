"""
First Time Generation Graph for Resource Agent
LangGraph state machine for initial resource analysis
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


class ResourceGenerationState(TypedDict):
    """State for first time generation workflow."""
    project_id: str
    document_id: str
    llm_manager: Any
    embeddings_manager: Any
    chroma_manager: Any
    db_manager: Any
    orchestrator: Any
    a2a_router: Any
    
    # Results from each step
    tasks_retrieved: list
    tasks_count: int
    task_analysis_result: dict
    dependencies_result: dict
    critical_path_result: dict
    
    # Final results
    overall_success: bool
    error: str


def create_first_time_generation_graph():
    """
    Create and compile the first time generation graph.
    
    Returns:
        Compiled LangGraph StateGraph
    """
    # Create graph
    workflow = StateGraph(ResourceGenerationState)
    
    # Add nodes
    workflow.add_node("retrieve_tasks", retrieve_tasks_node)
    workflow.add_node("analyze_tasks", analyze_tasks_node)
    workflow.add_node("create_dependencies", create_dependencies_node)
    workflow.add_node("calculate_critical_path", calculate_critical_path_node)
    
    # Define edges
    workflow.set_entry_point("retrieve_tasks")
    workflow.add_edge("retrieve_tasks", "analyze_tasks")
    workflow.add_edge("analyze_tasks", "create_dependencies")
    workflow.add_edge("create_dependencies", "calculate_critical_path")
    workflow.add_edge("calculate_critical_path", END)
    
    # Compile graph
    return workflow.compile()


# Create the graph instance
first_time_generation_graph = create_first_time_generation_graph()

