"""
Resource Allocation Nodes for LangGraph
"""

from typing import Dict, Any
from ..agents.resource_optimization_agent import ResourceOptimizationAgent


def get_financial_data_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Get financial summary for resource allocation"""
    try:
        project_id = state['project_id']
        chroma_manager = state['chroma_manager']
        
        resource_agent = ResourceOptimizationAgent(chroma_manager)
        financial_summary = resource_agent.get_project_financial_summary(project_id)
        
        state['financial_summary'] = financial_summary
        
        return state
        
    except Exception as e:
        state['error'] = f"Error getting financial data: {str(e)}"
        state['financial_summary'] = {'success': False, 'error': str(e)}
        return state


def assign_resources_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Assign resources to work team using AI"""
    try:
        project_id = state['project_id']
        llm_manager = state['llm_manager']
        chroma_manager = state['chroma_manager']
        
        resource_agent = ResourceOptimizationAgent(chroma_manager)
        result = resource_agent.assign_resources_ai(project_id, llm_manager)
        
        state['resource_assignment_result'] = result
        
        return state
        
    except Exception as e:
        state['error'] = f"Error assigning resources: {str(e)}"
        state['resource_assignment_result'] = {'success': False, 'error': str(e)}
        return state

