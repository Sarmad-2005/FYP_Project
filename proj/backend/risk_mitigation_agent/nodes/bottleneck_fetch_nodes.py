"""
Bottleneck Fetching Nodes for What If Simulator
"""

from typing import Dict, Any


def fetch_bottlenecks_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fetch bottlenecks from Performance Agent
    
    Args:
        state: WhatIfSimulatorState
        
    Returns:
        Updated state with bottlenecks
    """
    try:
        project_id = state.get('project_id')
        what_if_simulator = state.get('what_if_simulator')
        orchestrator = state.get('orchestrator')
        performance_agent = state.get('performance_agent')
        
        if not what_if_simulator:
            state['error'] = 'WhatIfSimulatorAgent not initialized'
            return state
        
        print(f"📍 Fetching bottlenecks for project {project_id}...")
        
        llm_manager = state.get('llm_manager')
        bottlenecks = what_if_simulator.fetch_project_bottlenecks(
            project_id,
            orchestrator=orchestrator,
            performance_agent=performance_agent,
            llm_manager=llm_manager
        )
        
        state['bottlenecks'] = bottlenecks
        state['bottlenecks_count'] = len(bottlenecks)
        
        print(f"✅ Fetched {len(bottlenecks)} bottlenecks")
        
        return state
        
    except Exception as e:
        print(f"❌ Error in fetch_bottlenecks_node: {e}")
        import traceback
        traceback.print_exc()
        state['error'] = f"Error fetching bottlenecks: {str(e)}"
        state['bottlenecks'] = []
        return state

