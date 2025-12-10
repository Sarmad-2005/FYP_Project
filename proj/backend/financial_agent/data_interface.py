"""
Financial Agent Data Interface
Exposes data retrieval functions for orchestrator
"""

from typing import Dict, List, Any, Callable, Optional


class FinancialDataInterface:
    """
    Data interface for Financial Agent
    Provides standardized access to financial data for other agents
    """
    
    def __init__(self, financial_agent):
        """
        Initialize data interface
        
        Args:
            financial_agent: Instance of FinancialAgent
        """
        self.agent = financial_agent
    
    def get_data_functions(self) -> Dict[str, Callable]:
        """
        Get all data retrieval functions
        
        Returns:
            Dict mapping function names to callable functions
        """
        return {
            "get_financial_details": self.get_financial_details,
            "get_transactions": self.get_transactions,
            "get_expenses": self.get_expenses,
            "get_revenue": self.get_revenue,
            "get_budget_info": self.get_budget_info,
            "get_financial_health": self.get_financial_health
        }
    
    def get_function_descriptions(self) -> Dict[str, str]:
        """
        Get descriptions for all data functions (used for cosine similarity)
        
        Returns:
            Dict mapping function names to natural language descriptions
        """
        return {
            "get_financial_details": "Retrieve all financial details including budgets, cost estimates, and payment schedules from project documents",
            
            "get_transactions": "Retrieve all financial transactions including expenses, revenue, payments, and transfers with amounts and dates",
            
            "get_expenses": "Get expense analysis including total expenses, breakdown by category, vendor spending, and expense trends",
            
            "get_revenue": "Get revenue analysis including total revenue, revenue sources, and milestone-linked payments",
            
            "get_budget_info": "Retrieve budget allocations, spending limits, and budget utilization information for the project",
            
            "get_financial_health": "Get financial health score and metrics including revenue vs expenses ratio and financial status"
        }
    
    # ========== Data Retrieval Function Implementations ==========
    
    def get_financial_details(self, project_id: str, filters: Optional[Dict] = None) -> List[Dict]:
        """
        Get all financial details for a project
        
        Args:
            project_id: Project identifier
            filters: Optional filters (detail_type, category)
            
        Returns:
            List of financial detail dictionaries
        """
        try:
            details = self.agent.chroma_manager.get_financial_data(
                'financial_details', project_id, filters
            )
            return details
        except Exception as e:
            print(f"Error getting financial details: {e}")
            return []
    
    def get_transactions(self, project_id: str, filters: Optional[Dict] = None) -> List[Dict]:
        """
        Get all transactions for a project
        
        Args:
            project_id: Project identifier
            filters: Optional filters (transaction_type, date, vendor, status)
            
        Returns:
            List of transaction dictionaries
        """
        try:
            transactions = self.agent.chroma_manager.get_financial_data(
                'transactions', project_id, filters
            )
            return transactions
        except Exception as e:
            print(f"Error getting transactions: {e}")
            return []
    
    def get_expenses(self, project_id: str) -> Dict:
        """
        Get expense analysis for a project
        
        Args:
            project_id: Project identifier
            
        Returns:
            Expense analysis dictionary
        """
        try:
            # Get expense analysis
            expense_analysis = self.agent.expense_agent.get_expense_analysis(project_id)
            
            # If no stored analysis, compute on-the-fly
            if not expense_analysis:
                transactions = self.agent.chroma_manager.get_financial_data(
                    'transactions', project_id
                )
                expense_analysis = self.agent.expense_agent.analyze_expenses(
                    project_id, transactions
                )
            
            return expense_analysis
        except Exception as e:
            print(f"Error getting expenses: {e}")
            return {'total_expenses': 0, 'by_category': {}, 'count': 0}
    
    def get_revenue(self, project_id: str) -> Dict:
        """
        Get revenue analysis for a project
        
        Args:
            project_id: Project identifier
            
        Returns:
            Revenue analysis dictionary
        """
        try:
            # Get revenue analysis
            revenue_analysis = self.agent.revenue_agent.get_revenue_analysis(project_id)
            
            # If no stored analysis, compute on-the-fly
            if not revenue_analysis:
                transactions = self.agent.chroma_manager.get_financial_data(
                    'transactions', project_id
                )
                revenue_analysis = self.agent.revenue_agent.analyze_revenue(
                    project_id, transactions
                )
            
            return revenue_analysis
        except Exception as e:
            print(f"Error getting revenue: {e}")
            return {'total_revenue': 0, 'by_source': {}, 'count': 0}
    
    def get_budget_info(self, project_id: str) -> Dict:
        """
        Get budget information for a project
        
        Args:
            project_id: Project identifier
            
        Returns:
            Budget information dictionary
        """
        try:
            # Get financial details with budget type
            budget_details = self.agent.chroma_manager.get_financial_data(
                'financial_details',
                project_id,
                filters={'detail_type': 'budget_allocation'}
            )
            
            # Calculate total budget
            total_budget = sum(
                float(detail.get('metadata', {}).get('amount', 0))
                for detail in budget_details
            )
            
            # Get expense data
            expense_analysis = self.get_expenses(project_id)
            total_expenses = expense_analysis.get('total_expenses', 0)
            
            return {
                'total_budget': total_budget,
                'total_expenses': total_expenses,
                'remaining_budget': total_budget - total_expenses,
                'utilization_percentage': (total_expenses / total_budget * 100) if total_budget > 0 else 0,
                'budget_details': budget_details
            }
        except Exception as e:
            print(f"Error getting budget info: {e}")
            return {'total_budget': 0, 'total_expenses': 0, 'remaining_budget': 0}
    
    def get_financial_health(self, project_id: str) -> Dict:
        """
        Get financial health score and metrics
        
        Args:
            project_id: Project identifier
            
        Returns:
            Financial health dictionary
        """
        try:
            # Get expense and revenue analysis
            expense_analysis = self.get_expenses(project_id)
            revenue_analysis = self.get_revenue(project_id)
            
            total_expenses = expense_analysis.get('total_expenses', 0)
            total_revenue = revenue_analysis.get('total_revenue', 0)
            
            # Calculate health score
            health_score = self.agent._calculate_financial_health(
                total_expenses,
                total_revenue,
                expense_analysis.get('by_category', {})
            )
            
            # Determine status
            if health_score >= 80:
                status = 'Healthy'
            elif health_score >= 60:
                status = 'Warning'
            else:
                status = 'Critical'
            
            return {
                'health_score': health_score,
                'status': status,
                'total_expenses': total_expenses,
                'total_revenue': total_revenue,
                'net_balance': total_revenue - total_expenses,
                'expense_count': expense_analysis.get('count', 0),
                'revenue_count': revenue_analysis.get('count', 0)
            }
        except Exception as e:
            print(f"Error getting financial health: {e}")
            return {'health_score': 0.0, 'status': 'No Data'}

