"""
Extraction Nodes for Performance Agent
Node functions that wrap worker agent extraction methods.
"""

from typing import Dict, Any
from ..agents.milestone_agent import MilestoneAgent
from ..agents.task_agent import TaskAgent
from ..agents.bottleneck_agent import BottleneckAgent
from ..agents.requirements_agent import RequirementsAgent
from ..agents.actors_agent import ActorsAgent


def extract_milestones_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract milestones from document.
    Wraps MilestoneAgent.extract_milestones_from_document()
    
    Args:
        state: Graph state containing project_id, document_id, etc.
        
    Returns:
        Updated state with milestones_result
    """
    try:
        project_id = state.get("project_id")
        document_id = state.get("document_id")
        llm_manager = state.get("llm_manager")
        chroma_manager = state.get("chroma_manager")
        
        if not all([project_id, document_id, llm_manager, chroma_manager]):
            state["milestones_result"] = {'success': False, 'error': 'Missing required state fields'}
            state["error"] = 'Missing required state fields'
            return state
        
        # Initialize agent
        milestone_agent = MilestoneAgent(chroma_manager)
        
        # Extract milestones
        result = milestone_agent.extract_milestones_from_document(
            project_id, document_id, llm_manager
        )
        
        state["milestones_result"] = result
        if "error" not in state:
            state["error"] = ""
        return state
    except Exception as e:
        state["milestones_result"] = {'success': False, 'error': str(e)}
        state["error"] = str(e)
        return state


def extract_tasks_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract tasks from document.
    Wraps TaskAgent.extract_tasks_from_document()
    
    Args:
        state: Graph state
        
    Returns:
        Updated state with tasks_result
    """
    try:
        project_id = state.get("project_id")
        document_id = state.get("document_id")
        llm_manager = state.get("llm_manager")
        chroma_manager = state.get("chroma_manager")
        
        if not all([project_id, document_id, llm_manager, chroma_manager]):
            state["tasks_result"] = {'success': False, 'error': 'Missing required state fields'}
            state["error"] = 'Missing required state fields'
            return state
        
        # Initialize agent
        task_agent = TaskAgent(chroma_manager)
        
        # Extract tasks
        result = task_agent.extract_tasks_from_document(
            project_id, document_id, llm_manager
        )
        
        state["tasks_result"] = result
        if "error" not in state:
            state["error"] = ""
        return state
    except Exception as e:
        state["tasks_result"] = {'success': False, 'error': str(e)}
        state["error"] = str(e)
        return state


def extract_bottlenecks_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract bottlenecks from document.
    Wraps BottleneckAgent.extract_bottlenecks_from_document()
    
    Args:
        state: Graph state
        
    Returns:
        Updated state with bottlenecks_result
    """
    try:
        project_id = state.get("project_id")
        document_id = state.get("document_id")
        llm_manager = state.get("llm_manager")
        chroma_manager = state.get("chroma_manager")
        
        if not all([project_id, document_id, llm_manager, chroma_manager]):
            state["bottlenecks_result"] = {'success': False, 'error': 'Missing required state fields'}
            state["error"] = 'Missing required state fields'
            return state
        
        # Initialize agent
        bottleneck_agent = BottleneckAgent(chroma_manager)
        
        # Extract bottlenecks
        result = bottleneck_agent.extract_bottlenecks_from_document(
            project_id, document_id, llm_manager
        )
        
        state["bottlenecks_result"] = result
        if "error" not in state:
            state["error"] = ""
        return state
    except Exception as e:
        state["bottlenecks_result"] = {'success': False, 'error': str(e)}
        state["error"] = str(e)
        return state


def extract_requirements_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Extract requirements from document."""
    try:
        project_id = state.get("project_id")
        document_id = state.get("document_id")
        llm_manager = state.get("llm_manager")
        chroma_manager = state.get("chroma_manager")
        if not all([project_id, document_id, llm_manager, chroma_manager]):
            state["requirements_result"] = {'success': False, 'error': 'Missing required state fields'}
            state["error"] = 'Missing required state fields'
            return state
        agent = RequirementsAgent(chroma_manager)
        result = agent.extract_requirements_from_document(project_id, document_id, llm_manager)
        state["requirements_result"] = result
        state.setdefault("error", "")
        return state
    except Exception as e:
        state["requirements_result"] = {'success': False, 'error': str(e)}
        state["error"] = str(e)
        return state


def extract_actors_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Extract actors/stakeholders from document."""
    try:
        project_id = state.get("project_id")
        document_id = state.get("document_id")
        llm_manager = state.get("llm_manager")
        chroma_manager = state.get("chroma_manager")
        if not all([project_id, document_id, llm_manager, chroma_manager]):
            state["actors_result"] = {'success': False, 'error': 'Missing required state fields'}
            state["error"] = 'Missing required state fields'
            return state
        agent = ActorsAgent(chroma_manager)
        result = agent.extract_actors_from_document(project_id, document_id, llm_manager)
        state["actors_result"] = result
        state.setdefault("error", "")
        return state
    except Exception as e:
        state["actors_result"] = {'success': False, 'error': str(e)}
        state["error"] = str(e)
        return state


def extract_from_new_docs_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract performance data from new documents.
    
    Args:
        state: Graph state with new_documents list
        
    Returns:
        Updated state
    """
    try:
        project_id = state.get("project_id")
        new_documents = state.get("new_documents", [])
        llm_manager = state.get("llm_manager")
        chroma_manager = state.get("chroma_manager")
        
        if not new_documents:
            return state
        
        if not all([project_id, llm_manager, chroma_manager]):
            state["refresh_result"] = {'success': False, 'error': 'Missing required state fields'}
            state["error"] = 'Missing required state fields'
            return state
        
        # Initialize agents
        milestone_agent = MilestoneAgent(chroma_manager)
        task_agent = TaskAgent(chroma_manager)
        bottleneck_agent = BottleneckAgent(chroma_manager)
        requirements_agent = RequirementsAgent(chroma_manager)
        actors_agent = ActorsAgent(chroma_manager)
        
        # Process each new document
        for document in new_documents:
            document_id = document['id']
            
            # Extract milestones
            milestone_agent.extract_milestones_from_document(
                project_id, document_id, llm_manager
            )
            
            # Extract tasks
            task_agent.extract_tasks_from_document(
                project_id, document_id, llm_manager
            )
            
            # Extract bottlenecks
            bottleneck_agent.extract_bottlenecks_from_document(
                project_id, document_id, llm_manager
            )
            
            # Extract requirements
            requirements_agent.extract_requirements_from_document(
                project_id, document_id, llm_manager
            )

            # Extract actors
            actors_agent.extract_actors_from_document(
                project_id, document_id, llm_manager
            )
        
        state["refresh_result"] = {
            'documents_processed': len(new_documents),
            'success': True
        }
        return state
    except Exception as e:
        state["refresh_result"] = {'success': False, 'error': str(e)}
        state["error"] = str(e)
        return state
