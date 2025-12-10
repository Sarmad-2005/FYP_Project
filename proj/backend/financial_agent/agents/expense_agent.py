"""
Expense Agent - Analyzes and aggregates project expenses
"""

from typing import Dict, List, Any
from datetime import datetime


class ExpenseAgent:
    """Worker agent for expense analysis with orchestrator integration"""
    
    def __init__(self, chroma_manager, orchestrator=None, llm_manager=None):
        """
        Initialize Expense Agent
        
        Args:
            chroma_manager: FinancialChromaManager instance
            orchestrator: OrchestratorAgent instance for inter-agent communication
            llm_manager: LLMManager instance for LLM-based mapping
        """
        self.chroma_manager = chroma_manager
        self.orchestrator = orchestrator
        self.llm_manager = llm_manager
    
    def analyze_expenses(self, project_id: str, transactions: List[Dict]) -> Dict[str, Any]:
        """
        Analyze project expenses
        
        Args:
            project_id: Project identifier
            transactions: List of transaction dictionaries
            
        Returns:
            Dict with expense analysis results
        """
        try:
            print(f"📊 Analyzing expenses for project {project_id[:8]}...")
            
            # Filter expenses
            expenses = [t for t in transactions 
                       if t.get('metadata', {}).get('transaction_type') == 'expense']
            
            if not expenses:
                return {
                    'total_expenses': 0,
                    'by_category': {},
                    'by_vendor': {},
                    'count': 0
                }
            
            # Calculate totals
            total = sum(float(e.get('metadata', {}).get('amount', 0)) for e in expenses)
            
            # Group by category
            by_category = {}
            for exp in expenses:
                category = exp.get('metadata', {}).get('category', 'unknown')
                amount = float(exp.get('metadata', {}).get('amount', 0))
                by_category[category] = by_category.get(category, 0) + amount
            
            # Group by vendor
            by_vendor = {}
            for exp in expenses:
                vendor = exp.get('metadata', {}).get('vendor_recipient', 'unknown')
                amount = float(exp.get('metadata', {}).get('amount', 0))
                by_vendor[vendor] = by_vendor.get(vendor, 0) + amount
            
            # Get task mapping if orchestrator available
            task_mapping = {}
            if self.orchestrator:
                task_mapping = self._map_expenses_to_tasks(project_id, expenses)
            
            analysis = {
                'total_expenses': total,
                'by_category': by_category,
                'by_vendor': by_vendor,
                'task_mapping': task_mapping,
                'count': len(expenses),
                'currency': 'PKR'
            }
            
            # Store analysis
            self._store_analysis(project_id, analysis)
            
            return analysis
            
        except Exception as e:
            print(f"Error analyzing expenses: {e}")
            return {'total_expenses': 0, 'by_category': {}, 'by_vendor': {}, 'count': 0}
    
    def _map_expenses_to_tasks(self, project_id: str, expenses: List[Dict]) -> Dict[str, float]:
        """
        Map expenses to tasks using LLM with orchestrator data
        
        Args:
            project_id: Project identifier
            expenses: List of expenses
            
        Returns:
            Dict mapping task IDs to expense amounts
        """
        try:
            if not self.orchestrator or not self.llm_manager:
                return {}
            
            # Get tasks from Performance Agent via orchestrator
            tasks = self.orchestrator.route_data_request(
                query="Get all project tasks with their details",
                requesting_agent="financial_agent",
                project_id=project_id
            )
            
            if not tasks:
                print("   ℹ️  No tasks found from Performance Agent (run Performance Agent analysis first)")
                return {}
            
            # Use LLM to map expenses to tasks
            print(f"   🤖 Using LLM to map {len(expenses)} expenses to {len(tasks)} tasks...")
            
            # Prepare context
            tasks_context = self._format_tasks_for_llm(tasks)
            expenses_context = self._format_expenses_for_llm(expenses)
            
            prompt = f"""
You are a financial analyst mapping project expenses to specific tasks.

TASKS:
{tasks_context}

EXPENSES:
{expenses_context}

TASK:
For each expense, determine which task it is most closely related to based on:
- Expense category and description
- Task description and category
- Contextual relevance

Output Format: JSON object mapping expense IDs to task IDs
{{
  "expense_id_1": "task_id_X",
  "expense_id_2": "task_id_Y",
  "expense_id_3": "general_overhead"
}}

Rules:
- Map each expense to the MOST relevant task
- If no clear match exists, use "general_overhead"
- Return ONLY valid JSON, no other text
- Use exact IDs from the provided lists
"""
            
            llm_response = self.llm_manager.simple_chat(prompt)
            
            # Parse LLM response
            import json
            import re
            try:
                # Check for LLM errors
                if isinstance(llm_response, dict):
                    if not llm_response.get('success', False):
                        print(f"   ⚠️  LLM error: {llm_response.get('error', 'Unknown error')}")
                        return {}
                    # Extract the actual response text
                    response_text = llm_response.get('response', '')
                else:
                    response_text = str(llm_response)
                
                # Clean response - remove markdown code blocks if present
                response_text = response_text.strip()
                if response_text.startswith('```json'):
                    response_text = response_text[7:]
                elif response_text.startswith('```'):
                    response_text = response_text[3:]
                if response_text.endswith('```'):
                    response_text = response_text[:-3]
                response_text = response_text.strip()
                
                # Extract JSON object (handle cases where LLM adds explanation after JSON)
                json_match = re.search(r'\{[\s\S]*?\}(?=\s*(?:\n|$|Explanation|In the above|For |The |This))', response_text)
                if json_match:
                    response_text = json_match.group(0)
                else:
                    # Try to find just the first complete JSON object
                    json_match = re.search(r'\{[\s\S]*\}', response_text)
                    if json_match:
                        response_text = json_match.group(0)
                
                print(f"   🔍 Extracted JSON (length: {len(response_text)} chars)")
                print(f"   📝 First 200 chars: {response_text[:200]}")
                
                # Parse JSON
                mapping = json.loads(response_text)
                
                # Aggregate expenses by task
                task_expenses = {}
                for expense_id, task_id in mapping.items():
                    # Find expense amount
                    expense = next((e for e in expenses if e.get('id') == expense_id), None)
                    if expense:
                        amount = float(expense.get('metadata', {}).get('amount', 0))
                        task_expenses[task_id] = task_expenses.get(task_id, 0) + amount
                
                print(f"   ✅ Mapped expenses to {len(task_expenses)} tasks")                
                return task_expenses
                
            except json.JSONDecodeError as e:
                print(f"   ⚠️  Failed to parse LLM response as JSON: {e}")
                print(f"   📄 Response text (first 500 chars): {response_text[:500]}...")
                return {}
            
        except Exception as e:
            print(f"   ❌ Error mapping expenses to tasks: {e}")
            return {}
    
    def _format_tasks_for_llm(self, tasks: List[Dict]) -> str:
        """Format tasks for LLM context"""
        formatted = []
        for i, task in enumerate(tasks[:20], 1):  # Limit to 20 tasks
            task_id = task.get('id', task.get('metadata', {}).get('task_id', f'task_{i}'))
            task_text = task.get('text', task.get('metadata', {}).get('task_text', 'No description'))
            category = task.get('metadata', {}).get('category', 'general')
            formatted.append(f"{i}. ID: {task_id}\n   Description: {task_text}\n   Category: {category}")
        return "\n".join(formatted)
    
    def _format_expenses_for_llm(self, expenses: List[Dict]) -> str:
        """Format expenses for LLM context"""
        formatted = []
        for i, exp in enumerate(expenses[:50], 1):  # Limit to 50 expenses
            exp_id = exp.get('id', f'exp_{i}')
            amount = exp.get('metadata', {}).get('amount', 0)
            category = exp.get('metadata', {}).get('category', 'unknown')
            vendor = exp.get('metadata', {}).get('vendor_recipient', 'unknown')
            desc = exp.get('text', exp.get('metadata', {}).get('description', 'No description'))
            formatted.append(f"{i}. ID: {exp_id}\n   Amount: PKR {amount:,.2f}\n   Category: {category}\n   Vendor: {vendor}\n   Description: {desc}")
        return "\n".join(formatted)

    
    def _store_analysis(self, project_id: str, analysis: Dict):
        """Store expense analysis in ChromaDB"""
        try:
            data_item = {
                'text': f"Expense analysis: Total {analysis['total_expenses']} PKR across {analysis['count']} transactions",
                'metadata': {
                    'project_id': project_id,
                    'analysis_type': 'expense',
                    'total_expenses': analysis['total_expenses'],
                    'transaction_count': analysis['count'],
                    'categories': len(analysis['by_category']),
                    'vendors': len(analysis['by_vendor']),
                    'created_at': datetime.now().isoformat()
                }
            }
            
            self.chroma_manager.store_financial_data(
                'expense_analysis', [data_item], project_id, 'analysis'
            )
            
        except Exception as e:
            print(f"Error storing expense analysis: {e}")
    
    def get_expense_analysis(self, project_id: str) -> Dict:
        """Get expense analysis for a project (recalculated from current transactions)"""
        try:
            # Get all transactions
            transactions = self.chroma_manager.get_financial_data('transactions', project_id)
            
            # Analyze current transactions
            analysis = self.analyze_expenses(project_id, transactions)
            
            return analysis
            
        except Exception as e:
            print(f"Error getting expense analysis: {e}")
            return {'total_expenses': 0, 'by_category': {}, 'by_vendor': {}, 'count': 0}

