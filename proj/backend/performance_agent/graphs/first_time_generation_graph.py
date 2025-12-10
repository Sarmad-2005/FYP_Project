"""
First Time Generation Graph for Performance Agent
LangGraph state machine for initial performance data extraction and analysis.
"""

from typing import TypedDict, Any
from langgraph.graph import StateGraph, END

from ..nodes.extraction_nodes import (
    extract_milestones_node,
    extract_tasks_node,
    extract_bottlenecks_node,
    extract_requirements_node,
    extract_actors_node
)
from ..nodes.analysis_nodes import (
    extract_details_node,
    generate_suggestions_node
)


class PerformanceGenerationState(TypedDict):
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
    milestones_result: dict
    tasks_result: dict
    bottlenecks_result: dict
    requirements_result: dict
    actors_result: dict
    details_result: dict
    suggestions_result: dict
    
    # Final results
    completion_score: float
    overall_success: bool
    error: str


def create_first_time_generation_graph():
    """
    Create and compile the first time generation graph.
    
    Returns:
        Compiled LangGraph StateGraph
    """
    # Create graph
    workflow = StateGraph(PerformanceGenerationState)
    
    # Add nodes
    workflow.add_node("extract_milestones", extract_milestones_node)
    workflow.add_node("extract_tasks", extract_tasks_node)
    workflow.add_node("extract_bottlenecks", extract_bottlenecks_node)
    workflow.add_node("extract_requirements", extract_requirements_node)
    workflow.add_node("extract_actors", extract_actors_node)
    workflow.add_node("extract_details", extract_details_node)
    workflow.add_node("generate_suggestions", generate_suggestions_node)
    
    # Define edges
    workflow.set_entry_point("extract_milestones")
    workflow.add_edge("extract_milestones", "extract_tasks")
    workflow.add_edge("extract_tasks", "extract_bottlenecks")
    workflow.add_edge("extract_bottlenecks", "extract_requirements")
    workflow.add_edge("extract_requirements", "extract_actors")
    workflow.add_edge("extract_actors", "extract_details")
    workflow.add_edge("extract_details", "generate_suggestions")
    workflow.add_edge("generate_suggestions", END)
    
    # Compile graph
    return workflow.compile()


# Create the graph instance
first_time_generation_graph = create_first_time_generation_graph()
