"""
Task Analysis Nodes for LangGraph
"""

from typing import Dict, Any
from ..agents.task_optimization_agent import TaskOptimizationAgent


def retrieve_tasks_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Retrieve all tasks from Performance Agent"""
    try:
        project_id = state['project_id']
        chroma_manager = state['chroma_manager']
        
        task_agent = TaskOptimizationAgent(chroma_manager)
        tasks = task_agent.get_all_project_tasks(project_id)
        
        state['tasks_retrieved'] = tasks
        state['tasks_count'] = len(tasks)
        
        return state
        
    except Exception as e:
        state['error'] = f"Error retrieving tasks: {str(e)}"
        return state


def analyze_tasks_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze all tasks for priority, complexity, and estimated time"""
    try:
        project_id = state['project_id']
        llm_manager = state['llm_manager']
        chroma_manager = state['chroma_manager']
        
        task_agent = TaskOptimizationAgent(chroma_manager)
        result = task_agent.analyze_all_tasks(project_id, llm_manager)
        
        state['task_analysis_result'] = result
        
        return state
        
    except Exception as e:
        state['error'] = f"Error analyzing tasks: {str(e)}"
        state['task_analysis_result'] = {'success': False, 'error': str(e)}
        return state

