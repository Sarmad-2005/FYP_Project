"""
Graph Generation Nodes for What If Simulator
"""

from typing import Dict, Any


def generate_graph_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate graph data structure
    
    Args:
        state: WhatIfSimulatorState
        
    Returns:
        Updated state with graph_data
    """
    try:
        ordered_bottlenecks = state.get('ordered_bottlenecks', [])
        what_if_simulator = state.get('what_if_simulator')
        
        if not ordered_bottlenecks:
            print("⚠️ No ordered bottlenecks to generate graph")
            state['graph_data'] = {'nodes': [], 'edges': []}
            return state
        
        if not what_if_simulator:
            state['error'] = 'WhatIfSimulatorAgent not initialized'
            state['graph_data'] = {'nodes': [], 'edges': []}
            return state
        
        print(f"📍 Generating graph data for {len(ordered_bottlenecks)} bottlenecks...")
        
        graph_data = what_if_simulator.generate_graph_data(ordered_bottlenecks)
        
        state['graph_data'] = graph_data
        state['success'] = True
        
        print(f"✅ Generated graph with {len(graph_data.get('nodes', []))} nodes")
        
        return state
        
    except Exception as e:
        print(f"❌ Error in generate_graph_node: {e}")
        import traceback
        traceback.print_exc()
        state['error'] = f"Error generating graph: {str(e)}"
        state['graph_data'] = {'nodes': [], 'edges': []}
        state['success'] = False
        return state

