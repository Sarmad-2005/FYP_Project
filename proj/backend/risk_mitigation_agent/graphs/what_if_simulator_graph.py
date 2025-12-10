"""
What If Simulator Graph for Risk Mitigation Agent
LangGraph state machine for What If Scenario Simulator workflow.
"""

from typing import TypedDict, Any
from langgraph.graph import StateGraph, END

from ..nodes.bottleneck_fetch_nodes import fetch_bottlenecks_node
from ..nodes.bottleneck_ordering_nodes import order_bottlenecks_node
from ..nodes.graph_generation_nodes import generate_graph_node


class WhatIfSimulatorState(TypedDict):
    """State for What If Simulator workflow."""
    project_id: str
    llm_manager: Any
    chroma_manager: Any
    orchestrator: Any
    performance_agent: Any
    what_if_simulator: Any
    
    # Results from each step
    bottlenecks: list
    bottlenecks_count: int
    ordered_bottlenecks: list
    graph_data: dict
    
    # Final results
    success: bool
    error: str


def create_what_if_simulator_graph():
    """
    Create and compile the What If Simulator graph.
    
    Returns:
        Compiled LangGraph StateGraph
    """
    # Create graph
    workflow = StateGraph(WhatIfSimulatorState)
    
    # Add nodes
    workflow.add_node("fetch_bottlenecks", fetch_bottlenecks_node)
    workflow.add_node("order_bottlenecks", order_bottlenecks_node)
    workflow.add_node("generate_graph", generate_graph_node)
    
    # Define edges
    workflow.set_entry_point("fetch_bottlenecks")
    workflow.add_edge("fetch_bottlenecks", "order_bottlenecks")
    workflow.add_edge("order_bottlenecks", "generate_graph")
    workflow.add_edge("generate_graph", END)
    
    # Compile graph
    return workflow.compile()


# Create the graph instance
what_if_simulator_graph = create_what_if_simulator_graph()

