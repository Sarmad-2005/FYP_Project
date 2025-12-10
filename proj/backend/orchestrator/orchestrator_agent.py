"""
Orchestrator Agent - Routes data retrieval requests between major agents
Uses semantic similarity (cosine) for intelligent routing
"""

from typing import Dict, Any, Optional
import numpy as np


class OrchestratorAgent:
    """
    Main orchestrator for inter-agent communication
    Routes data retrieval requests using semantic similarity
    """
    
    def __init__(self, embeddings_manager, agent_registry):
        """
        Initialize orchestrator agent
        
        Args:
            embeddings_manager: Manager for generating embeddings
            agent_registry: Registry containing all major agents
        """
        self.embeddings_manager = embeddings_manager
        self.registry = agent_registry
        self.function_embeddings = {}
        self._initialize_function_embeddings()
    
    def _initialize_function_embeddings(self):
        """
        Pre-compute embeddings for all data retrieval function descriptions
        This is done once at initialization for performance
        """
        print("🔧 Initializing function embeddings for orchestrator...")
        
        for agent_name in self.registry.get_registered_agents():
            self.function_embeddings[agent_name] = {}
            
            # Get function descriptions from registry
            descriptions = self.registry.get_function_descriptions(agent_name)
            
            for func_name, func_desc in descriptions.items():
                # Generate embedding for this function description
                try:
                    embedding = self.embeddings_manager.get_embedding(func_desc)
                    self.function_embeddings[agent_name][func_name] = embedding
                except Exception as e:
                    print(f"   ⚠️ Failed to generate embedding for {agent_name}.{func_name}: {e}")
                
        print(f"✅ Initialized embeddings for {len(self.function_embeddings)} agents")
    
    def route_data_request(self, query: str, requesting_agent: str, 
                          project_id: str, **kwargs) -> Optional[Any]:
        """
        Route data retrieval request to appropriate agent function
        
        Args:
            query: Natural language query (e.g., "Get all tasks for this project")
            requesting_agent: Name of agent making the request (e.g., "financial_agent")
            project_id: Project identifier
            **kwargs: Additional parameters for the function
            
        Returns:
            Data from the appropriate agent, or None if routing fails
            
        Example:
            >>> data = orchestrator.route_data_request(
            ...     query="Get all bottlenecks with high severity",
            ...     requesting_agent="financial_agent",
            ...     project_id="proj_123"
            ... )
        """
        try:
            print(f"\n🔀 Routing data request from '{requesting_agent}'")
            print(f"   Query: '{query}'")
            
            # Generate embedding for the query
            query_embedding = self.embeddings_manager.get_embedding(query)
            
            # Find best matching function across all agents
            best_match = self._find_best_function_match(query_embedding)
            
            if not best_match:
                print(f"❌ No matching function found for query")
                return None
            
            print(f"✅ Matched: {best_match['agent']}.{best_match['function']} "
                  f"(similarity: {best_match['similarity']:.3f})")
            
            # Execute the matched function
            result = self._execute_function(
                agent_name=best_match['agent'],
                function_name=best_match['function'],
                project_id=project_id,
                **kwargs
            )
            
            return result
            
        except Exception as e:
            print(f"❌ Error routing data request: {e}")
            return None
    
    def _find_best_function_match(self, query_embedding) -> Optional[Dict]:
        """
        Find best matching function using cosine similarity
        
        Args:
            query_embedding: Embedding vector of the query
            
        Returns:
            Dict with agent name, function name, and similarity score
        """
        if query_embedding is None:
            print("   ❌ Query embedding is None")
            return None
        
        if not self.function_embeddings:
            print("   ❌ No function embeddings initialized")
            return None
        
        best_match = {
            "agent": None,
            "function": None,
            "similarity": -1.0
        }
        
        # Compare query with all function embeddings
        for agent_name, functions in self.function_embeddings.items():
            for func_name, func_embedding in functions.items():
                if func_embedding is None:
                    continue
                
                # Calculate cosine similarity
                similarity = self._cosine_similarity(query_embedding, func_embedding)
                
                # Update best match if this is better
                if similarity > best_match["similarity"]:
                    best_match = {
                        "agent": agent_name,
                        "function": func_name,
                        "similarity": similarity
                    }
        
        # Log best match even if below threshold
        if best_match["similarity"] > 0:
            print(f"   🔍 Best match: {best_match['agent']}.{best_match['function']} (similarity: {best_match['similarity']:.3f})")
        
        # Only return if similarity is above threshold
        threshold = 0.4  # Lowered from 0.5 to 0.4 for better matching
        if best_match["similarity"] > threshold:
            return best_match
        else:
            print(f"   ❌ Best similarity {best_match['similarity']:.3f} below threshold {threshold}")
        
        return None
    
    def _cosine_similarity(self, vec1, vec2):
        """
        Calculate cosine similarity between two vectors
        
        Args:
            vec1: First vector
            vec2: Second vector
            
        Returns:
            Cosine similarity score (0-1)
        """
        try:
            vec1 = np.array(vec1)
            vec2 = np.array(vec2)
            
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            return dot_product / (norm1 * norm2)
        except Exception as e:
            print(f"Error calculating cosine similarity: {e}")
            return 0.0
    
    def _execute_function(self, agent_name: str, function_name: str, 
                         project_id: str, **kwargs) -> Any:
        """
        Execute the matched function on the appropriate agent
        
        Args:
            agent_name: Name of the agent (e.g., "performance_agent")
            function_name: Name of the function (e.g., "get_tasks")
            project_id: Project identifier
            **kwargs: Additional parameters
            
        Returns:
            Result from the function execution
        """
        return self.registry.execute_data_function(
            agent_name=agent_name,
            function_name=function_name,
            project_id=project_id,
            **kwargs
        )
    
    def get_available_functions(self, agent_name: str = None) -> Dict:
        """
        Get list of available data retrieval functions
        
        Args:
            agent_name: Specific agent name, or None for all agents
            
        Returns:
            Dict of available functions and their descriptions
        """
        if agent_name:
            return self.registry.get_function_descriptions(agent_name)
        else:
            all_functions = {}
            for agent in self.registry.get_registered_agents():
                all_functions[agent] = self.registry.get_function_descriptions(agent)
            return all_functions

