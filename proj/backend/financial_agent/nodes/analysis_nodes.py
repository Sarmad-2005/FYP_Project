"""
Analysis Nodes for Financial Agent
Node functions that wrap worker agent analysis methods.
"""

from typing import Dict, Any
from ..agents.expense_agent import ExpenseAgent
from ..agents.revenue_agent import RevenueAgent
from ..agents.anomaly_detection_agent import AnomalyDetectionAgent
from backend.a2a_protocol.a2a_message import A2AMessage, MessageType, Priority


def analyze_expenses_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze expenses from transactions.
    Wraps ExpenseAgent.analyze_expenses()
    
    Args:
        state: Graph state
        
    Returns:
        Updated state with expenses_result
    """
    try:
        project_id = state.get("project_id")
        chroma_manager = state.get("chroma_manager")
        orchestrator = state.get("orchestrator")
        llm_manager = state.get("llm_manager")
        a2a_router = state.get("a2a_router")
        
        if not project_id or not chroma_manager:
            state["expenses_result"] = {'error': 'Missing required state fields', 'total_expenses': 0}
            state["error"] = 'Missing required state fields'
            return state
        
        # Get transactions
        transactions = chroma_manager.get_financial_data('transactions', project_id)
        
        # Initialize agent
        expense_agent = ExpenseAgent(chroma_manager, orchestrator, llm_manager)
        
        # Analyze expenses
        result = expense_agent.analyze_expenses(project_id, transactions)
        
        # If A2A router available, request performance data if needed
        if a2a_router and a2a_router.is_agent_registered("performance-service"):
            try:
                # Request tasks and milestones for context
                request_msg = A2AMessage.create_request(
                    sender_agent="financial-service",
                    recipient_agent="performance-service",
                    payload={
                        "action": "get_tasks_and_milestones",
                        "project_id": project_id
                    }
                )
                response = a2a_router.send_message(request_msg)
                if response and response.message_type == MessageType.RESPONSE:
                    result["performance_context"] = response.payload
            except Exception as e:
                # Non-critical, continue without performance context
                pass
        
        state["expenses_result"] = result
        if "error" not in state:
            state["error"] = ""
        return state
    except Exception as e:
        state["expenses_result"] = {'error': str(e), 'total_expenses': 0}
        state["error"] = str(e)
        return state


def analyze_revenue_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze revenue from transactions.
    Wraps RevenueAgent.analyze_revenue()
    
    Args:
        state: Graph state
        
    Returns:
        Updated state with revenue_result
    """
    try:
        project_id = state["project_id"]
        chroma_manager = state["chroma_manager"]
        orchestrator = state.get("orchestrator")
        llm_manager = state.get("llm_manager")
        a2a_router = state.get("a2a_router")
        
        # Get transactions
        transactions = chroma_manager.get_financial_data('transactions', project_id)
        
        # Initialize agent
        revenue_agent = RevenueAgent(chroma_manager, orchestrator, llm_manager)
        
        # Analyze revenue
        result = revenue_agent.analyze_revenue(project_id, transactions)
        
        # If A2A router available, request performance data if needed
        if a2a_router and a2a_router.is_agent_registered("performance-service"):
            try:
                request_msg = A2AMessage.create_request(
                    sender_agent="financial-service",
                    recipient_agent="performance-service",
                    payload={
                        "action": "get_milestones",
                        "project_id": project_id
                    }
                )
                response = a2a_router.send_message(request_msg)
                if response and response.message_type == MessageType.RESPONSE:
                    result["performance_context"] = response.payload
            except Exception as e:
                pass
        
        state["revenue_result"] = result
        return state
    except Exception as e:
        state["revenue_result"] = {'error': str(e), 'total_revenue': 0}
        state["error"] = str(e)
        return state


def detect_anomalies_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Detect anomalies in transactions.
    Wraps AnomalyDetectionAgent.detect_anomalies()
    
    Args:
        state: Graph state
        
    Returns:
        Updated state with anomaly_result
    """
    try:
        project_id = state["project_id"]
        chroma_manager = state["chroma_manager"]
        
        # Get transactions
        transactions = chroma_manager.get_financial_data('transactions', project_id)
        
        # Initialize agent
        anomaly_agent = AnomalyDetectionAgent(chroma_manager)
        
        # Detect anomalies
        result = anomaly_agent.detect_anomalies(project_id, transactions)
        
        state["anomaly_result"] = result
        state["overall_success"] = (
            state.get("financial_details_result", {}).get("success", False) and
            state.get("transactions_result", {}).get("success", False)
        )
        return state
    except Exception as e:
        state["anomaly_result"] = {'success': False, 'error': str(e)}
        state["error"] = str(e)
        return state


def recalculate_metrics_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recalculate all financial metrics after refresh.
    
    Args:
        state: Graph state
        
    Returns:
        Updated state
    """
    try:
        project_id = state["project_id"]
        chroma_manager = state["chroma_manager"]
        orchestrator = state.get("orchestrator")
        llm_manager = state.get("llm_manager")
        
        # Get all transactions
        transactions = chroma_manager.get_financial_data('transactions', project_id)
        
        # Recalculate expenses
        expense_agent = ExpenseAgent(chroma_manager, orchestrator, llm_manager)
        expense_agent.analyze_expenses(project_id, transactions)
        
        # Recalculate revenue
        revenue_agent = RevenueAgent(chroma_manager, orchestrator, llm_manager)
        revenue_agent.analyze_revenue(project_id, transactions)
        
        # Recalculate anomalies
        anomaly_agent = AnomalyDetectionAgent(chroma_manager)
        anomaly_agent.detect_anomalies(project_id, transactions)
        
        state["refresh_result"]["metrics_recalculated"] = True
        state["success"] = True
        return state
    except Exception as e:
        state["refresh_result"]["metrics_recalculated"] = False
        state["error"] = str(e)
        state["success"] = False
        return state


def update_timestamp_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update last financial update timestamp.
    
    Args:
        state: Graph state
        
    Returns:
        Updated state
    """
    try:
        import os
        import json
        from datetime import datetime
        
        project_id = state["project_id"]
        financial_data_dir = state.get("financial_data_dir", "data/financial")
        
        # Ensure directory exists
        os.makedirs(financial_data_dir, exist_ok=True)
        
        # Update timestamp file
        update_file = os.path.join(financial_data_dir, f"{project_id}_last_update.json")
        data = {
            'project_id': project_id,
            'last_update': datetime.now().isoformat()
        }
        with open(update_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        state["refresh_result"]["timestamp_updated"] = True
        state["success"] = True
        return state
    except Exception as e:
        state["refresh_result"]["timestamp_updated"] = False
        state["error"] = str(e)
        state["success"] = False
        return state
