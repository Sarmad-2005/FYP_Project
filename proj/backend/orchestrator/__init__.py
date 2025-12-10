"""
Orchestrator Agent Module
Manages inter-agent communication via registry pattern with semantic routing
"""

from .orchestrator_agent import OrchestratorAgent
from .agent_registry import AgentRegistry

__all__ = ['OrchestratorAgent', 'AgentRegistry']


