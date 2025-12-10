"""
Refresh Graph for Performance Agent
LangGraph state machine for refreshing performance data with new documents.
"""

from typing import TypedDict, Annotated, Literal, Any
from langgraph.graph import StateGraph, END

from ..nodes.extraction_nodes import extract_from_new_docs_node
from ..nodes.analysis_nodes import update_existing_entities_node, recalculate_completion_node


class PerformanceRefreshState(TypedDict):
    """State for refresh workflow."""
    project_id: str
    llm_manager: Any
    embeddings_manager: Any
    chroma_manager: Any
    db_manager: Any
    orchestrator: Any
    a2a_router: Any
    performance_data_dir: str
    
    # Document tracking
    new_documents: list
    last_update: str
    
    # Results
    refresh_result: dict
    success: bool
    error: str


def check_new_documents_node(state: PerformanceRefreshState) -> PerformanceRefreshState:
    """
    Check for new documents since last update.
    
    Args:
        state: Current state
        
    Returns:
        Updated state with new_documents list
    """
    try:
        import os
        import json
        
        project_id = state["project_id"]
        db_manager = state["db_manager"]
        performance_data_dir = state.get("performance_data_dir", "data/performance")
        
        # Get all documents for project
        documents = db_manager.get_documents(project_id)
        
        # Get last update timestamp from file
        update_file = os.path.join(performance_data_dir, f"{project_id}_last_update.json")
        last_update = None
        if os.path.exists(update_file):
            with open(update_file, 'r') as f:
                data = json.load(f)
                last_update = data.get('last_update')
        
        # Filter new documents
        new_documents = []
        if last_update:
            for document in documents:
                if document.get('created_at', '') > last_update:
                    new_documents.append(document)
        else:
            new_documents = documents
        
        state["new_documents"] = new_documents
        state["last_update"] = last_update or ""
        
        return state
    except Exception as e:
        state["error"] = str(e)
        state["success"] = False
        return state


def create_refresh_graph():
    """
    Create and compile the refresh graph.
    
    Returns:
        Compiled LangGraph StateGraph
    """
    # Create graph
    workflow = StateGraph(PerformanceRefreshState)
    
    # Add nodes
    workflow.add_node("check_new_documents", check_new_documents_node)
    workflow.add_node("extract_from_new_docs", extract_from_new_docs_node)
    workflow.add_node("update_existing_entities", update_existing_entities_node)
    workflow.add_node("recalculate_completion", recalculate_completion_node)
    
    # Define edges with conditional logic
    workflow.set_entry_point("check_new_documents")
    
    def should_process(state: PerformanceRefreshState) -> Literal["extract_from_new_docs", "update_existing_entities"]:
        """Conditional edge: process if new documents exist."""
        if state.get("new_documents") and len(state["new_documents"]) > 0:
            return "extract_from_new_docs"
        return "update_existing_entities"
    
    # Add conditional edges with mapping dictionary
    workflow.add_conditional_edges(
        "check_new_documents",
        should_process,
        {
            "extract_from_new_docs": "extract_from_new_docs",
            "update_existing_entities": "update_existing_entities"
        }
    )
    workflow.add_edge("extract_from_new_docs", "update_existing_entities")
    workflow.add_edge("update_existing_entities", "recalculate_completion")
    workflow.add_edge("recalculate_completion", END)
    
    # Compile graph
    return workflow.compile()


# Create the graph instance
refresh_graph = create_refresh_graph()
