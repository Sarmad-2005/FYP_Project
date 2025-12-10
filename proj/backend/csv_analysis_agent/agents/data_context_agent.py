"""
Data Context Agent
Worker agent for retrieving financial project context via A2A protocol
"""

from typing import Dict, Any, Optional
from backend.a2a_protocol.a2a_message import A2AMessage, MessageType


class DataContextAgent:
    """Worker agent for building financial context via A2A protocol"""
    
    def __init__(self, a2a_router, anomaly_agent=None):
        """
        Initialize Data Context Agent
        
        Args:
            a2a_router: A2ARouter instance for inter-service communication
            anomaly_agent: AnomalyDetectionAgent instance (optional, for backward compatibility)
        """
        self.a2a_router = a2a_router
        self.anomaly_agent = anomaly_agent
    
    def get_full_context(self, project_id: str) -> Dict[str, Any]:
        """
        Get complete financial context for a project
        
        Args:
            project_id: Project identifier
            
        Returns:
            Complete financial context
        """
        try:
            context = {
                'success': True,
                'project_id': project_id,
                'budget': self._get_budget_context(project_id),
                'expenses': self._get_expense_context(project_id),
                'revenue': self._get_revenue_context(project_id),
                'transactions': self._get_transaction_context(project_id),
                'anomalies': self._get_anomaly_context(project_id),
                'health': self._get_health_context(project_id)
            }
            
            return context
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _get_budget_context(self, project_id: str) -> Dict[str, Any]:
        """Get budget information via A2A"""
        try:
            if not self.a2a_router:
                return {'error': 'A2A router not available'}
            
            request_msg = A2AMessage.create_request(
                sender_agent="csv-analysis-service",
                recipient_agent="financial-service",
                payload={
                    "action": "get_financial_data",
                    "project_id": project_id,
                    "data_type": "budget"
                }
            )
            
            response = self.a2a_router.send_message(request_msg)
            if not response or response.message_type != MessageType.RESPONSE:
                return {'error': 'Failed to retrieve budget data'}
            
            budget = response.payload.get("data", {})
            return {
                'total': budget.get('total_budget', 0),
                'utilized': budget.get('total_expenses', 0),
                'remaining': budget.get('remaining_budget', 0),
                'utilization_percentage': budget.get('utilization_percentage', 0)
            }
        except Exception as e:
            return {'error': str(e)}
    
    def _get_expense_context(self, project_id: str) -> Dict[str, Any]:
        """Get expense information via A2A"""
        try:
            if not self.a2a_router:
                return {'error': 'A2A router not available'}
            
            request_msg = A2AMessage.create_request(
                sender_agent="csv-analysis-service",
                recipient_agent="financial-service",
                payload={
                    "action": "get_financial_data",
                    "project_id": project_id,
                    "data_type": "expenses"
                }
            )
            
            response = self.a2a_router.send_message(request_msg)
            if not response or response.message_type != MessageType.RESPONSE:
                return {'error': 'Failed to retrieve expense data'}
            
            expenses = response.payload.get("data", {})
            return {
                'total': expenses.get('total_expenses', 0),
                'count': expenses.get('count', 0),
                'by_category': expenses.get('by_category', {}),
                'by_vendor': expenses.get('by_vendor', {}),
                'top_category': max(
                    expenses.get('by_category', {}).items(),
                    key=lambda x: x[1],
                    default=('N/A', 0)
                )[0] if expenses.get('by_category') else 'N/A'
            }
        except Exception as e:
            return {'error': str(e)}
    
    def _get_revenue_context(self, project_id: str) -> Dict[str, Any]:
        """Get revenue information via A2A"""
        try:
            if not self.a2a_router:
                return {'error': 'A2A router not available'}
            
            request_msg = A2AMessage.create_request(
                sender_agent="csv-analysis-service",
                recipient_agent="financial-service",
                payload={
                    "action": "get_financial_data",
                    "project_id": project_id,
                    "data_type": "revenue"
                }
            )
            
            response = self.a2a_router.send_message(request_msg)
            if not response or response.message_type != MessageType.RESPONSE:
                return {'error': 'Failed to retrieve revenue data'}
            
            revenue = response.payload.get("data", {})
            return {
                'total': revenue.get('total_revenue', 0),
                'count': revenue.get('count', 0),
                'by_source': revenue.get('by_source', {}),
                'top_source': max(
                    revenue.get('by_source', {}).items(),
                    key=lambda x: x[1],
                    default=('N/A', 0)
                )[0] if revenue.get('by_source') else 'N/A'
            }
        except Exception as e:
            return {'error': str(e)}
    
    def _get_transaction_context(self, project_id: str) -> Dict[str, Any]:
        """Get transaction summary via A2A"""
        try:
            if not self.a2a_router:
                return {'error': 'A2A router not available'}
            
            request_msg = A2AMessage.create_request(
                sender_agent="csv-analysis-service",
                recipient_agent="financial-service",
                payload={
                    "action": "get_transactions",
                    "project_id": project_id,
                    "filters": None
                }
            )
            
            response = self.a2a_router.send_message(request_msg)
            if not response or response.message_type != MessageType.RESPONSE:
                return {'error': 'Failed to retrieve transaction data'}
            
            transactions = response.payload.get("transactions", [])
            
            expense_txns = [t for t in transactions if t.get('metadata', {}).get('transaction_type') == 'expense']
            revenue_txns = [t for t in transactions if t.get('metadata', {}).get('transaction_type') == 'revenue']
            
            return {
                'total_count': len(transactions),
                'expense_count': len(expense_txns),
                'revenue_count': len(revenue_txns),
                'recent': transactions[:5] if transactions else []
            }
        except Exception as e:
            return {'error': str(e)}
    
    def _get_anomaly_context(self, project_id: str) -> Dict[str, Any]:
        """Get anomaly information via A2A or direct agent"""
        try:
            # Try A2A first if router is available
            if self.a2a_router and self.a2a_router.is_agent_registered("financial-service"):
                request_msg = A2AMessage.create_request(
                    sender_agent="csv-analysis-service",
                    recipient_agent="financial-service",
                    payload={
                        "action": "get_anomalies",
                        "project_id": project_id,
                        "severity_filter": "all"
                    }
                )
                
                response = self.a2a_router.send_message(request_msg)
                if response and response.message_type == MessageType.RESPONSE:
                    anomalies = response.payload.get("result", {})
                else:
                    anomalies = {}
            # Fallback to direct agent if available
            elif self.anomaly_agent:
                anomalies = self.anomaly_agent.get_anomalies(project_id, 'all')
            else:
                return {'count': 0, 'error': 'Anomaly data source not available'}
            
            if not anomalies.get('success'):
                return {'count': 0}
            
            return {
                'count': anomalies.get('total_count', 0),
                'critical': anomalies.get('severity_counts', {}).get('critical', 0),
                'high': anomalies.get('severity_counts', {}).get('high', 0),
                'medium': anomalies.get('severity_counts', {}).get('medium', 0),
                'low': anomalies.get('severity_counts', {}).get('low', 0),
                'recent': anomalies.get('anomalies', [])[:3]
            }
        except Exception as e:
            return {'error': str(e), 'count': 0}
    
    def _get_health_context(self, project_id: str) -> Dict[str, Any]:
        """Get financial health information via A2A"""
        try:
            if not self.a2a_router:
                return {'error': 'A2A router not available'}
            
            request_msg = A2AMessage.create_request(
                sender_agent="csv-analysis-service",
                recipient_agent="financial-service",
                payload={
                    "action": "get_financial_data",
                    "project_id": project_id,
                    "data_type": "health"
                }
            )
            
            response = self.a2a_router.send_message(request_msg)
            if not response or response.message_type != MessageType.RESPONSE:
                return {'error': 'Failed to retrieve health data'}
            
            health = response.payload.get("data", {})
            return {
                'score': health.get('health_score', 0),
                'status': health.get('status', 'Unknown'),
                'net_balance': health.get('net_balance', 0)
            }
        except Exception as e:
            return {'error': str(e)}
    
    def build_context_summary(self, project_id: str) -> str:
        """
        Build a text summary of financial context
        
        Args:
            project_id: Project identifier
            
        Returns:
            Text summary of context
        """
        context = self.get_full_context(project_id)
        
        if not context.get('success'):
            return "Unable to retrieve financial context"
        
        summary_parts = []
        
        # Budget
        budget = context['budget']
        if 'error' not in budget:
            summary_parts.append(
                f"Budget: PKR {budget['total']:,.0f} (Utilized: {budget['utilization_percentage']:.1f}%)"
            )
        
        # Expenses
        expenses = context['expenses']
        if 'error' not in expenses:
            summary_parts.append(
                f"Expenses: PKR {expenses['total']:,.0f} ({expenses['count']} transactions, Top category: {expenses['top_category']})"
            )
        
        # Revenue
        revenue = context['revenue']
        if 'error' not in revenue:
            summary_parts.append(
                f"Revenue: PKR {revenue['total']:,.0f} ({revenue['count']} transactions, Top source: {revenue['top_source']})"
            )
        
        # Health
        health = context['health']
        if 'error' not in health:
            summary_parts.append(
                f"Financial Health: {health['score']:.0f}/100 ({health['status']}), Net Balance: PKR {health['net_balance']:,.0f}"
            )
        
        # Anomalies
        anomalies = context['anomalies']
        if 'error' not in anomalies and anomalies['count'] > 0:
            summary_parts.append(
                f"Anomalies: {anomalies['count']} detected (Critical: {anomalies['critical']}, High: {anomalies['high']})"
            )
        
        return "\n".join(summary_parts)

