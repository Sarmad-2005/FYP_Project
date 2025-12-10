"""
Critical Path Calculation Nodes for LangGraph
"""

from typing import Dict, Any
from ..agents.task_optimization_agent import TaskOptimizationAgent


def calculate_critical_path_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate critical path using CPM algorithm"""
    try:
        project_id = state['project_id']
        chroma_manager = state['chroma_manager']
        
        task_agent = TaskOptimizationAgent(chroma_manager)
        result = task_agent.calculate_critical_path(project_id)
        
        state['critical_path_result'] = result
        
        return state
        
    except Exception as e:
        state['error'] = f"Error calculating critical path: {str(e)}"
        state['critical_path_result'] = {'success': False, 'error': str(e)}
        return state

