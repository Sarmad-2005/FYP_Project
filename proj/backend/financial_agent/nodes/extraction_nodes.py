"""
Extraction Nodes for Financial Agent
Node functions that wrap worker agent extraction methods.
"""

from typing import Dict, Any
from ..agents.financial_details_agent import FinancialDetailsAgent
from ..agents.transaction_agent import TransactionAgent


def extract_details_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract financial details from document.
    Wraps FinancialDetailsAgent.extract_financial_details()
    
    Args:
        state: Graph state containing project_id, document_id, etc.
        
    Returns:
        Updated state with financial_details_result
    """
    try:
        project_id = state.get("project_id")
        document_id = state.get("document_id")
        llm_manager = state.get("llm_manager")
        embeddings_manager = state.get("embeddings_manager")
        chroma_manager = state.get("chroma_manager")
        
        if not all([project_id, document_id, llm_manager, embeddings_manager, chroma_manager]):
            state["financial_details_result"] = {'success': False, 'error': 'Missing required state fields'}
            state["error"] = 'Missing required state fields'
            return state
        
        # Initialize agent
        details_agent = FinancialDetailsAgent(chroma_manager)
        
        # Extract details
        result = details_agent.extract_financial_details(
            project_id, document_id, llm_manager, embeddings_manager
        )
        
        state["financial_details_result"] = result
        if "error" not in state:
            state["error"] = ""
        return state
    except Exception as e:
        state["financial_details_result"] = {'success': False, 'error': str(e)}
        state["error"] = str(e)
        return state


def extract_transactions_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract transactions from document.
    Wraps TransactionAgent.extract_transactions()
    
    Args:
        state: Graph state
        
    Returns:
        Updated state with transactions_result
    """
    try:
        project_id = state.get("project_id")
        document_id = state.get("document_id")
        llm_manager = state.get("llm_manager")
        embeddings_manager = state.get("embeddings_manager")
        chroma_manager = state.get("chroma_manager")
        
        if not all([project_id, document_id, llm_manager, embeddings_manager, chroma_manager]):
            state["transactions_result"] = {'success': False, 'error': 'Missing required state fields'}
            state["error"] = 'Missing required state fields'
            return state
        
        # Initialize agent
        transaction_agent = TransactionAgent(chroma_manager)
        
        # Extract transactions
        result = transaction_agent.extract_transactions(
            project_id, document_id, llm_manager, embeddings_manager
        )
        
        state["transactions_result"] = result
        if "error" not in state:
            state["error"] = ""
        return state
    except Exception as e:
        state["transactions_result"] = {'success': False, 'error': str(e)}
        state["error"] = str(e)
        return state


def extract_from_new_docs_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract financial data from new documents.
    
    Args:
        state: Graph state with new_documents list
        
    Returns:
        Updated state
    """
    try:
        project_id = state["project_id"]
        new_documents = state.get("new_documents", [])
        llm_manager = state["llm_manager"]
        embeddings_manager = state["embeddings_manager"]
        chroma_manager = state["chroma_manager"]
        
        if not new_documents:
            return state
        
        # Initialize agents
        details_agent = FinancialDetailsAgent(chroma_manager)
        transaction_agent = TransactionAgent(chroma_manager)
        
        # Process each new document
        for document in new_documents:
            document_id = document['id']
            
            # Extract details
            details_agent.extract_financial_details(
                project_id, document_id, llm_manager, embeddings_manager
            )
            
            # Extract transactions
            transaction_agent.extract_transactions(
                project_id, document_id, llm_manager, embeddings_manager
            )
        
        state["refresh_result"] = {
            'documents_processed': len(new_documents),
            'success': True
        }
        return state
    except Exception as e:
        state["refresh_result"] = {'success': False, 'error': str(e)}
        state["error"] = str(e)
        return state
