"""
Bottleneck Ordering Nodes for What If Simulator
"""

from typing import Dict, Any


def order_bottlenecks_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Order bottlenecks by priority using LLM
    
    Args:
        state: WhatIfSimulatorState
        
    Returns:
        Updated state with ordered_bottlenecks
    """
    try:
        bottlenecks = state.get('bottlenecks', [])
        llm_manager = state.get('llm_manager')
        what_if_simulator = state.get('what_if_simulator')
        
        if not bottlenecks:
            print("⚠️ No bottlenecks to order")
            state['ordered_bottlenecks'] = []
            return state
        
        if not what_if_simulator or not llm_manager:
            state['error'] = 'WhatIfSimulatorAgent or LLMManager not initialized'
            state['ordered_bottlenecks'] = bottlenecks
            return state
        
        print(f"📍 Ordering {len(bottlenecks)} bottlenecks by priority...")
        
        ordered_bottlenecks = what_if_simulator.order_bottlenecks_by_priority(
            bottlenecks,
            llm_manager
        )
        
        state['ordered_bottlenecks'] = ordered_bottlenecks
        
        print(f"✅ Ordered {len(ordered_bottlenecks)} bottlenecks")
        
        return state
        
    except Exception as e:
        print(f"❌ Error in order_bottlenecks_node: {e}")
        import traceback
        traceback.print_exc()
        state['error'] = f"Error ordering bottlenecks: {str(e)}"
        state['ordered_bottlenecks'] = state.get('bottlenecks', [])
        return state

