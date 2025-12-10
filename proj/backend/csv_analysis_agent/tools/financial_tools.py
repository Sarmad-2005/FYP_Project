"""
LangChain Tools for Financial Data Access
Uses A2A protocol for inter-service communication.
"""

from langchain.tools import BaseTool
from typing import Optional
from pydantic import BaseModel, Field
import json
from backend.a2a_protocol.a2a_message import A2AMessage, MessageType


class FinancialDataInput(BaseModel):
    """Input for Financial Data Tool"""
    # Make fields optional to avoid upfront validation failures; we'll validate in _run
    project_id: Optional[str] = Field(default=None, description="Project identifier")
    data_type: Optional[str] = Field(default=None, description="Type of data: 'expenses', 'revenue', 'budget', 'health'")


class FinancialDataTool(BaseTool):
    """Tool for accessing project financial data via A2A protocol"""
    
    name: str = "financial_data"
    description: str = """
    Get financial data for a project including expenses, revenue, budget, and health metrics.
    
    Data types:
    - 'expenses': Total expenses and breakdown by category/vendor
    - 'revenue': Total revenue and breakdown by source
    - 'budget': Budget allocations and utilization
    - 'health': Financial health score and metrics
    
    Input should be a JSON with 'project_id' and 'data_type'.
    """
    args_schema: type[BaseModel] = FinancialDataInput
    a2a_router: Optional[object] = None
    
    def __init__(self, a2a_router, **kwargs):
        """Initialize with A2A router"""
        super().__init__(**kwargs)
        self.a2a_router = a2a_router
    
    def _run(self, project_id: str, data_type: str = None) -> str:
        """Execute financial data retrieval via A2A"""
        try:
            if not self.a2a_router:
                return "Error: A2A router not available"
            
            # Robustness: some agent runs pass a JSON string as the first arg
            if (not data_type or data_type == "") and isinstance(project_id, str):
                stripped = project_id.strip()
                if stripped.startswith('{') and stripped.endswith('}'):
                    try:
                        payload = json.loads(stripped)
                        project_id = payload.get('project_id', project_id)
                        data_type = payload.get('data_type', data_type)
                    except Exception:
                        pass
            
            # Send A2A request to financial-service
            request_msg = A2AMessage.create_request(
                sender_agent="csv-analysis-service",
                recipient_agent="financial-service",
                payload={
                    "action": "get_financial_data",
                    "project_id": project_id,
                    "data_type": data_type
                }
            )
            
            response = self.a2a_router.send_message(request_msg)
            
            if not response or response.message_type != MessageType.RESPONSE:
                return f"Error: Failed to retrieve financial data from financial-service"
            
            data = response.payload.get("data", {})
            
            if data_type == "expenses":
                return f"Expenses data: Total: PKR {data.get('total_expenses', 0):,.0f}, Categories: {data.get('by_category', {})}, Vendors: {data.get('by_vendor', {})}"
            
            elif data_type == "revenue":
                return f"Revenue data: Total: PKR {data.get('total_revenue', 0):,.0f}, Sources: {data.get('by_source', {})}"
            
            elif data_type == "budget":
                return f"Budget: Total: PKR {data.get('total_budget', 0):,.0f}, Utilized: {data.get('utilization_percentage', 0):.1f}%, Remaining: PKR {data.get('remaining_budget', 0):,.0f}"
            
            elif data_type == "health":
                return f"Financial Health: Score: {data.get('health_score', 0):.0f}/100, Status: {data.get('status', 'Unknown')}, Net Balance: PKR {data.get('net_balance', 0):,.0f}"
            
            return f"Unknown data type: {data_type}"
            
        except Exception as e:
            return f"Financial Data Error: {str(e)}"
    
    async def _arun(self, project_id: str, data_type: str) -> str:
        """Async version - not implemented, calls sync version"""
        return self._run(project_id, data_type)


class TransactionInput(BaseModel):
    """Input for Transaction Tool"""
    project_id: str = Field(description="Project identifier")
    filters: Optional[str] = Field(description="Optional JSON string of filters (transaction_type, category, vendor)", default=None)


class TransactionTool(BaseTool):
    """Tool for accessing transaction data via A2A protocol"""
    
    name: str = "transactions"
    description: str = """
    Get transaction data for a project with optional filtering.
    
    Filters can include:
    - transaction_type: 'expense', 'revenue', 'transfer'
    - category: Category name
    - vendor: Vendor name
    
    Input should be a JSON with 'project_id' and optional 'filters' (JSON string).
    """
    args_schema: type[BaseModel] = TransactionInput
    a2a_router: Optional[object] = None
    
    def __init__(self, a2a_router, **kwargs):
        """Initialize with A2A router"""
        super().__init__(**kwargs)
        self.a2a_router = a2a_router
    
    def _run(self, project_id: str, filters: Optional[str] = None) -> str:
        """Execute transaction retrieval via A2A"""
        try:
            if not self.a2a_router:
                return "Error: A2A router not available"
            
            # Parse filters if provided
            filter_dict = None
            # Robustness: handle cases where a JSON string with both params was passed as project_id
            if isinstance(project_id, str):
                stripped = project_id.strip()
                if stripped.startswith('{') and stripped.endswith('}'):
                    try:
                        payload = json.loads(stripped)
                        project_id = payload.get('project_id', project_id)
                        if payload.get('filters') is not None:
                            filters = payload.get('filters')
                    except Exception:
                        pass
            if filters:
                try:
                    filter_dict = json.loads(filters) if isinstance(filters, str) else filters
                except Exception:
                    filter_dict = None
            
            # Send A2A request to financial-service
            request_msg = A2AMessage.create_request(
                sender_agent="csv-analysis-service",
                recipient_agent="financial-service",
                payload={
                    "action": "get_transactions",
                    "project_id": project_id,
                    "filters": filter_dict
                }
            )
            
            response = self.a2a_router.send_message(request_msg)
            
            if not response or response.message_type != MessageType.RESPONSE:
                return "Error: Failed to retrieve transactions from financial-service"
            
            transactions = response.payload.get("transactions", [])
            
            if not transactions:
                return "No transactions found for the given filters"
            
            # Summarize transactions
            total_amount = sum(float(t.get('metadata', {}).get('amount', 0)) for t in transactions)
            categories = set(t.get('metadata', {}).get('category', 'Unknown') for t in transactions)
            
            summary = f"Found {len(transactions)} transactions. Total amount: PKR {total_amount:,.0f}. Categories: {list(categories)}. Sample transactions: {transactions[:3]}"
            
            return summary
            
        except Exception as e:
            return f"Transaction Error: {str(e)}"
    
    async def _arun(self, project_id: str, filters: Optional[str] = None) -> str:
        """Async version - not implemented, calls sync version"""
        return self._run(project_id, filters)


class AnomalyInput(BaseModel):
    """Input for Anomaly Tool"""
    project_id: str = Field(description="Project identifier")
    severity_filter: Optional[str] = Field(description="Filter by severity: 'critical', 'high', 'medium', 'low', 'all'", default="all")


class AnomalyTool(BaseTool):
    """Tool for accessing anomaly detection data via A2A protocol"""
    
    name: str = "anomalies"
    description: str = """
    Get anomaly detection alerts for a project's financial transactions.
    
    Severity levels: 'critical', 'high', 'medium', 'low', 'all'
    
    Input should be a JSON with 'project_id' and optional 'severity_filter'.
    """
    args_schema: type[BaseModel] = AnomalyInput
    a2a_router: Optional[object] = None
    anomaly_agent: Optional[object] = None  # Keep for backward compatibility
    
    def __init__(self, a2a_router=None, anomaly_agent=None, **kwargs):
        """Initialize with A2A router or anomaly agent (for backward compatibility)"""
        super().__init__(**kwargs)
        self.a2a_router = a2a_router
        self.anomaly_agent = anomaly_agent
    
    def _run(self, project_id: str, severity_filter: str = "all") -> str:
        """Execute anomaly retrieval via A2A or direct agent"""
        try:
            # Try A2A first if router is available
            if self.a2a_router and self.a2a_router.is_agent_registered("financial-service"):
                request_msg = A2AMessage.create_request(
                    sender_agent="csv-analysis-service",
                    recipient_agent="financial-service",
                    payload={
                        "action": "get_anomalies",
                        "project_id": project_id,
                        "severity_filter": severity_filter
                    }
                )
                
                response = self.a2a_router.send_message(request_msg)
                
                if response and response.message_type == MessageType.RESPONSE:
                    result = response.payload.get("result", {})
                else:
                    result = {}
            # Fallback to direct agent if available
            elif self.anomaly_agent:
                result = self.anomaly_agent.get_anomalies(project_id, severity_filter)
            else:
                return "Error: Anomaly data source not available"
            
            if not result.get('success'):
                return "No anomaly data available"
            
            total = result.get('total_count', 0)
            severity_counts = result.get('severity_counts', {})
            anomalies = result.get('anomalies', [])
            
            if total == 0:
                return "No anomalies detected for this project"
            
            summary = f"Found {total} anomalies. Severity breakdown: Critical: {severity_counts.get('critical', 0)}, High: {severity_counts.get('high', 0)}, Medium: {severity_counts.get('medium', 0)}, Low: {severity_counts.get('low', 0)}. Sample anomaly: {anomalies[0] if anomalies else 'N/A'}"
            
            return summary
            
        except Exception as e:
            return f"Anomaly Error: {str(e)}"
    
    async def _arun(self, project_id: str, severity_filter: str = "all") -> str:
        """Async version - not implemented, calls sync version"""
        return self._run(project_id, severity_filter)

