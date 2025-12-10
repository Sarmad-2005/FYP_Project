"""
Agent Registry - Central registry for all major agents and their data functions
"""

from typing import Dict, List, Any, Callable, Optional


class AgentRegistry:
    """
    Registry that maintains all major agents and their data retrieval functions
    """
    
    def __init__(self):
        """Initialize empty registry"""
        self.agents = {}                      # Agent name -> agent instance
        self.data_functions = {}              # Agent name -> functions dict
        self.function_descriptions = {}       # Agent name -> descriptions dict
    
    def register_agent(self, agent_name: str, data_interface):
        """
        Register a major agent with its data interface
        
        Args:
            agent_name: Unique identifier (e.g., "performance_agent")
            data_interface: DataInterface instance from the agent
            
        Example:
            >>> perf_interface = PerformanceDataInterface(performance_agent)
            >>> registry.register_agent("performance_agent", perf_interface)
        """
        print(f"📝 Registering agent: {agent_name}")
        
        # Store agent reference
        self.agents[agent_name] = data_interface.agent
        
        # Store data retrieval functions
        self.data_functions[agent_name] = data_interface.get_data_functions()
        
        # Store function descriptions for semantic matching
        self.function_descriptions[agent_name] = data_interface.get_function_descriptions()
        
        func_count = len(self.data_functions[agent_name])
        print(f"   ✅ Registered {func_count} data functions")
    
    def get_registered_agents(self) -> List[str]:
        """Get list of all registered agent names"""
        return list(self.agents.keys())
    
    def get_agent(self, agent_name: str):
        """Get agent instance by name"""
        return self.agents.get(agent_name)
    
    def get_function_descriptions(self, agent_name: str) -> Dict[str, str]:
        """
        Get all function descriptions for an agent
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            Dict mapping function names to descriptions
        """
        return self.function_descriptions.get(agent_name, {})
    
    def execute_data_function(self, agent_name: str, function_name: str, 
                             project_id: str, **kwargs) -> Any:
        """
        Execute a data retrieval function on an agent
        
        Args:
            agent_name: Name of the agent
            function_name: Name of the function to call
            project_id: Project identifier
            **kwargs: Additional parameters
            
        Returns:
            Result from function execution
        """
        if agent_name not in self.data_functions:
            raise ValueError(f"Agent '{agent_name}' not registered")
        
        functions = self.data_functions[agent_name]
        
        if function_name not in functions:
            raise ValueError(f"Function '{function_name}' not found in agent '{agent_name}'")
        
        func = functions[function_name]
        return func(project_id, **kwargs)
    
    def list_all_functions(self) -> Dict[str, List[str]]:
        """
        Get all available functions across all agents
        
        Returns:
            Dict mapping agent names to lists of function names
        """
        return {
            agent_name: list(functions.keys())
            for agent_name, functions in self.data_functions.items()
        }


