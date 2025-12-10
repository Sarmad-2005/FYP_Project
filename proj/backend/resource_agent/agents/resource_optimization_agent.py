"""
Resource Optimization Agent 
Manages work teams and resource allocation 
"""

import json
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid
from backend.financial_agent.chroma_manager import FinancialChromaManager


class ResourceOptimizationAgent:
    """Agent for work team management and resource allocation"""
    
    def __init__(self, chroma_manager):
        """
        Initialize Resource Optimization Agent
        
        Args:
            chroma_manager: ResourceChromaManager instance
        """
        self.chroma_manager = chroma_manager
        # Access to Financial Agent's ChromaDB to retrieve financial data
        self.financial_chroma = FinancialChromaManager()
    
    def add_work_team_member(self, project_id: str, name: str, 
                            member_type: str = 'person') -> Dict[str, Any]:
        """
        Add a work team member (person or organization)
        
        Args:
            project_id: Project identifier
            name: Name of the person or organization
            member_type: 'person' or 'organization'
            
        Returns:
            Dictionary with result
        """
        try:
            if member_type not in ['person', 'organization']:
                return {
                    'success': False,
                    'error': "member_type must be 'person' or 'organization'"
                }
            
            # Generate unique ID
            team_member_id = f"team_{project_id}_{uuid.uuid4().hex[:8]}"
            
            # Store work team member
            member_data = [{
                'id': team_member_id,
                'name': name,
                'type': member_type,
                'assigned_resources': 0.0,
                'metadata': {
                    'name': name,
                    'type': member_type,
                    'assigned_resources': 0.0,
                    'created_at': datetime.now().isoformat()
                }
            }]
            
            success = self.chroma_manager.store_resource_data(
                'work_teams',
                member_data,
                project_id
            )
            
            if success:
                return {
                    'success': True,
                    'team_member_id': team_member_id,
                    'name': name,
                    'type': member_type
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to store work team member'
                }
                
        except Exception as e:
            print(f"Error adding work team member: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_work_team(self, project_id: str) -> List[Dict]:
        """
        Get all work team members for a project
        
        Args:
            project_id: Project identifier
            
        Returns:
            List of work team members
        """
        try:
            members = self.chroma_manager.get_resource_data('work_teams', project_id)
            
            # Format for UI
            formatted_members = []
            for member in members:
                metadata = member.get('metadata', {})
                formatted_members.append({
                    'id': member.get('id'),
                    'name': member.get('name', metadata.get('name', 'Unknown')),
                    'type': member.get('type', metadata.get('type', 'person')),
                    'assigned_resources': float(member.get('assigned_resources', metadata.get('assigned_resources', 0.0))),
                    'created_at': metadata.get('created_at', '')
                })
            
            return formatted_members
            
        except Exception as e:
            print(f"Error getting work team: {e}")
            return []
    
    def update_work_team_member(self, team_member_id: str, updates: Dict) -> bool:
        """
        Update work team member details
        
        Args:
            team_member_id: Team member identifier
            updates: Dictionary of fields to update
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Find which collection contains this member (work_teams)
            # We need to search across projects, but typically we'd have project_id
            # For now, update in work_teams collection
            
            # Get all collections to find the member
            collection = self.chroma_manager.get_resource_collection('work_teams')
            if not collection:
                return False
            
            # Get the member
            existing = collection.get(ids=[team_member_id])
            if not existing['ids']:
                return False
            
            # Update
            return self.chroma_manager.update_resource_data('work_teams', team_member_id, updates)
            
        except Exception as e:
            print(f"Error updating work team member: {e}")
            return False
    
    def delete_work_team_member(self, team_member_id: str) -> bool:
        """
        Delete a work team member
        
        Args:
            team_member_id: Team member identifier
            
        Returns:
            True if successful, False otherwise
        """
        try:
            return self.chroma_manager.delete_resource_data('work_teams', team_member_id)
            
        except Exception as e:
            print(f"Error deleting work team member: {e}")
            return False
    
    def get_project_financial_summary(self, project_id: str) -> Dict[str, Any]:
        """
        Retrieve total budget, expenses, and revenue for a project
        
        Args:
            project_id: Project identifier
            
        Returns:
            Dictionary with budget, expenses, revenue
        """
        try:
            # Get financial details (for budget)
            financial_details = self.financial_chroma.get_financial_data('financial_details', project_id)
            
            # Calculate total budget from financial_details
            total_budget = 0.0
            for detail in financial_details:
                metadata = detail.get('metadata', {})
                detail_type = metadata.get('detail_type', metadata.get('type', ''))
                
                # Count budget allocations
                if detail_type in ['budget_allocation', 'budget']:
                    amount = float(metadata.get('amount', 0))
                    if amount > 0:
                        total_budget += amount
            
            # Get transactions (for expenses and revenue)
            transactions = self.financial_chroma.get_financial_data('transactions', project_id)
            
            # Calculate expenses
            expense_transactions = [
                t for t in transactions
                if t.get('metadata', {}).get('transaction_type') == 'expense'
                and float(t.get('metadata', {}).get('amount', 0)) > 0
            ]
            
            total_expenses = sum(
                float(t.get('metadata', {}).get('amount', 0))
                for t in expense_transactions
            )
            
            # Calculate revenue
            revenue_transactions = [
                t for t in transactions
                if t.get('metadata', {}).get('transaction_type') == 'revenue'
                and float(t.get('metadata', {}).get('amount', 0)) > 0
            ]
            
            total_revenue = sum(
                float(t.get('metadata', {}).get('amount', 0))
                for t in revenue_transactions
            )
            
            return {
                'success': True,
                'budget': total_budget,
                'expenses': total_expenses,
                'revenue': total_revenue,
                'available': total_budget - total_expenses + total_revenue
            }
            
        except Exception as e:
            print(f"Error getting financial summary: {e}")
            return {
                'success': False,
                'error': str(e),
                'budget': 0.0,
                'expenses': 0.0,
                'revenue': 0.0,
                'available': 0.0
            }
    
    def assign_resources_ai(self, project_id: str, llm_manager) -> Dict[str, Any]:
        """
        AI-based resource assignment to work team members
        
        Args:
            project_id: Project identifier
            llm_manager: LLM manager instance
            
        Returns:
            Dictionary with assignment results
        """
        try:
            print(f"\n{'='*80}")
            print(f"💰 AI RESOURCE ASSIGNMENT - Project: {project_id}")
            print(f"{'='*80}\n")
            
            # Get work team
            work_team = self.get_work_team(project_id)
            
            if not work_team:
                return {
                    'success': False,
                    'error': 'No work team members found. Add work team members first.'
                }
            
            # Get financial summary
            financial_summary = self.get_project_financial_summary(project_id)
            
            if not financial_summary['success']:
                return {
                    'success': False,
                    'error': 'Failed to retrieve financial data'
                }
            
            # Get task analysis (for context)
            task_analysis = self.chroma_manager.get_resource_data('tasks_analysis', project_id)
            
            # Prepare prompt
            prompt = f"""You are allocating project resources (budget) to work team members.

FINANCIAL SUMMARY:
- Total Budget: PKR {financial_summary['budget']:,.2f}
- Total Expenses: PKR {financial_summary['expenses']:,.2f}
- Total Revenue: PKR {financial_summary['revenue']:,.2f}
- Available for Allocation: PKR {financial_summary['available']:,.2f}

WORK TEAM:
{json.dumps([{'id': m['id'], 'name': m['name'], 'type': m['type']} for m in work_team], indent=2)}

TASK ANALYSIS (for context):
Total Tasks: {len(task_analysis)}
Complexity Distribution: {self._get_complexity_distribution(task_analysis)}

ALLOCATE resources to each work team member considering:
- Their role and type (person vs organization)
- Fair distribution based on responsibilities
- Project needs and requirements
- Available budget

OUTPUT FORMAT (JSON only, no additional text):
[
    {{
        "team_member_id": "id",
        "name": "Name",
        "allocated_amount": float,
        "reasoning": "explanation for allocation"
    }}
]

Total allocated amount should not exceed available budget: PKR {financial_summary['available']:,.2f}

Return ONLY valid JSON array, no markdown, no code blocks."""

            # Call LLM
            llm_response = llm_manager.simple_chat(prompt)
            
            # Check if LLM call was successful
            if not llm_response.get('success', True):
                return {
                    'success': False,
                    'error': f"LLM call failed: {llm_response.get('error', 'Unknown error')}"
                }
            
            # Extract response text from dictionary
            response_text = llm_response.get('response', '')
            
            # Parse JSON response
            try:
                # Clean response
                response_clean = response_text.strip()
                if response_clean.startswith('```json'):
                    response_clean = response_clean[7:]
                if response_clean.startswith('```'):
                    response_clean = response_clean[3:]
                if response_clean.endswith('```'):
                    response_clean = response_clean[:-3]
                response_clean = response_clean.strip()
                
                assignments = json.loads(response_clean)
                
                if not isinstance(assignments, list):
                    raise ValueError("Response is not a list")
                
                # Update work team members with assigned resources
                updated_count = 0
                total_allocated = 0.0
                
                for assignment in assignments:
                    team_member_id = assignment.get('team_member_id')
                    allocated_amount = float(assignment.get('allocated_amount', 0))
                    
                    if not team_member_id:
                        continue
                    
                    # Update assigned resources
                    success = self.chroma_manager.update_resource_data(
                        'work_teams',
                        team_member_id,
                        {'assigned_resources': allocated_amount}
                    )
                    
                    if success:
                        updated_count += 1
                        total_allocated += allocated_amount
                        print(f"   ✅ {assignment.get('name', team_member_id)}: PKR {allocated_amount:,.2f}")
                
                print(f"\n{'='*80}")
                print(f"✅ RESOURCE ASSIGNMENT COMPLETE")
                print(f"   Allocated: PKR {total_allocated:,.2f} to {updated_count} members")
                print(f"{'='*80}\n")
                
                return {
                    'success': True,
                    'assignments': assignments,
                    'total_allocated': total_allocated,
                    'members_updated': updated_count
                }
                
            except (json.JSONDecodeError, ValueError) as e:
                print(f"Error parsing LLM response: {e}")
                print(f"Response was: {response_text[:200]}...")
                return {
                    'success': False,
                    'error': f"Failed to parse LLM response: {str(e)}"
                }
                
        except Exception as e:
            print(f"Error in assign_resources_ai: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _get_complexity_distribution(self, task_analysis: List[Dict]) -> str:
        """Get complexity distribution for prompt"""
        complexity_count = {}
        for analysis in task_analysis:
            complexity = analysis.get('complexity', 'Moderate')
            complexity_count[complexity] = complexity_count.get(complexity, 0) + 1
        return ', '.join([f"{k}: {v}" for k, v in complexity_count.items()])
    
    def update_resource_assignment(self, team_member_id: str, amount: float) -> bool:
        """
        Manually update resource assignment for a work team member
        
        Args:
            team_member_id: Team member identifier
            amount: New assigned amount
            
        Returns:
            True if successful, False otherwise
        """
        try:
            return self.chroma_manager.update_resource_data(
                'work_teams',
                team_member_id,
                {'assigned_resources': float(amount)}
            )
            
        except Exception as e:
            print(f"Error updating resource assignment: {e}")
            return False

