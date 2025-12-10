"""
Dependency Creation Nodes for LangGraph
"""

from typing import Dict, Any
from ..agents.task_optimization_agent import TaskOptimizationAgent


def create_dependencies_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Create task dependencies using LLM"""
    try:
        project_id = state['project_id']
        llm_manager = state['llm_manager']
        chroma_manager = state['chroma_manager']
        
        task_agent = TaskOptimizationAgent(chroma_manager)
        result = task_agent.create_task_dependencies(project_id, llm_manager)
        
        state['dependencies_result'] = result
        
        return state
        
    except Exception as e:
        state['error'] = f"Error creating dependencies: {str(e)}"
        state['dependencies_result'] = {'success': False, 'error': str(e)}
        return state

