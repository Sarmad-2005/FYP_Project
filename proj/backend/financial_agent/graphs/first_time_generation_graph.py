"""
First Time Generation Graph for Financial Agent
LangGraph state machine for initial financial data extraction and analysis.
"""

from typing import TypedDict, Annotated, Literal, Any
from langgraph.graph import StateGraph, END

from ..nodes.extraction_nodes import extract_details_node, extract_transactions_node
from ..nodes.analysis_nodes import analyze_expenses_node, analyze_revenue_node, detect_anomalies_node


class FirstTimeGenerationState(TypedDict):
    """State for first time generation workflow."""
    project_id: str
    document_id: str
    llm_manager: Any
    embeddings_manager: Any
    chroma_manager: Any
    orchestrator: Any
    a2a_router: Any
    
    # Results from each step
    financial_details_result: dict
    transactions_result: dict
    expenses_result: dict
    revenue_result: dict
    anomaly_result: dict
    
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
    workflow = StateGraph(FirstTimeGenerationState)
    
    # Add nodes
    workflow.add_node("extract_details", extract_details_node)
    workflow.add_node("extract_transactions", extract_transactions_node)
    workflow.add_node("analyze_expenses", analyze_expenses_node)
    workflow.add_node("analyze_revenue", analyze_revenue_node)
    workflow.add_node("detect_anomalies", detect_anomalies_node)
    
    # Define edges
    workflow.set_entry_point("extract_details")
    workflow.add_edge("extract_details", "extract_transactions")
    workflow.add_edge("extract_transactions", "analyze_expenses")
    workflow.add_edge("analyze_expenses", "analyze_revenue")
    workflow.add_edge("analyze_revenue", "detect_anomalies")
    workflow.add_edge("detect_anomalies", END)
    
    # Compile graph
    return workflow.compile()


# Create the graph instance
first_time_generation_graph = create_first_time_generation_graph()
