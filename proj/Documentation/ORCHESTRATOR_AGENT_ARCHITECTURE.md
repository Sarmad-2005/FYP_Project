# Orchestrator Agent Architecture

## Overview
The Orchestrator Agent manages inter-agent communication by routing data retrieval requests between major agents (Performance Agent, Financial Agent, etc.) using semantic similarity matching.

---

## Core Purpose
- **NOT for user queries**: Orchestrator does NOT route user requests
- **Only for inter-agent data transfer**: When one major agent needs data from another major agent
- **Semantic routing**: Uses cosine similarity to match data queries to appropriate agent functions

---

## Directory Structure

```
proj/
└── backend/
    ├── orchestrator/
    │   ├── __init__.py
    │   ├── orchestrator_agent.py         # Main orchestrator logic
    │   ├── agent_registry.py             # Registry of all major agents
    │   └── data_router.py                # Data retrieval routing logic
    │
    ├── performance_agent/
    │   ├── __init__.py
    │   ├── performance_agent.py
    │   ├── data_interface.py             # NEW - Data retrieval interface
    │   ├── chroma_manager.py
    │   └── agents/
    │       └── ...
    │
    └── financial_agent/
        ├── __init__.py
        ├── financial_agent.py            # Main financial agent
        ├── data_interface.py             # NEW - Data retrieval interface
        ├── chroma_manager.py             # Financial data storage
        └── agents/
            ├── __init__.py
            ├── budget_agent.py           # Worker: Budget analysis
            ├── expense_agent.py          # Worker: Expense tracking
            ├── revenue_agent.py          # Worker: Revenue projection
            └── risk_agent.py             # Worker: Financial risk assessment
```

---

## Component Details

### 1. Orchestrator Agent (`orchestrator_agent.py`)

```python
"""
Orchestrator Agent - Routes data retrieval requests between major agents
"""

from backend.embeddings import get_embedding
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from typing import Dict, Any, Optional

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
                embedding = self.embeddings_manager.get_embedding(func_desc)
                self.function_embeddings[agent_name][func_name] = embedding
                
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
        best_match = {
            "agent": None,
            "function": None,
            "similarity": -1.0
        }
        
        # Compare query with all function embeddings
        for agent_name, functions in self.function_embeddings.items():
            for func_name, func_embedding in functions.items():
                
                # Calculate cosine similarity
                similarity = cosine_similarity(
                    [query_embedding],
                    [func_embedding]
                )[0][0]
                
                # Update best match if this is better
                if similarity > best_match["similarity"]:
                    best_match = {
                        "agent": agent_name,
                        "function": func_name,
                        "similarity": similarity
                    }
        
        # Only return if similarity is above threshold
        if best_match["similarity"] > 0.5:  # Configurable threshold
            return best_match
        
        return None
    
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
```

---

### 2. Agent Registry (`agent_registry.py`)

```python
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
```

---

### 3. Performance Agent Data Interface (`performance_agent/data_interface.py`)

```python
"""
Performance Agent Data Interface
Exposes data retrieval functions for orchestrator
"""

from typing import Dict, List, Any, Callable, Optional

class PerformanceDataInterface:
    """
    Data interface for Performance Agent
    Provides standardized access to performance data for other agents
    """
    
    def __init__(self, performance_agent):
        """
        Initialize data interface
        
        Args:
            performance_agent: Instance of PerformanceAgent
        """
        self.agent = performance_agent
    
    def get_data_functions(self) -> Dict[str, Callable]:
        """
        Get all data retrieval functions
        
        Returns:
            Dict mapping function names to callable functions
        """
        return {
            "get_tasks": self.get_tasks,
            "get_milestones": self.get_milestones,
            "get_bottlenecks": self.get_bottlenecks,
            "get_task_details": self.get_task_details,
            "get_milestone_details": self.get_milestone_details,
            "get_bottleneck_details": self.get_bottleneck_details,
            "get_task_suggestions": self.get_task_suggestions,
            "get_milestone_suggestions": self.get_milestone_suggestions,
            "get_bottleneck_suggestions": self.get_bottleneck_suggestions,
            "get_all_suggestions": self.get_all_suggestions
        }
    
    def get_function_descriptions(self) -> Dict[str, str]:
        """
        Get descriptions for all data functions (used for cosine similarity)
        
        Returns:
            Dict mapping function names to natural language descriptions
        """
        return {
            "get_tasks": "Retrieve all project tasks with their status, priority, and category information",
            
            "get_milestones": "Retrieve all project milestones with their timeline, priority, and completion status",
            
            "get_bottlenecks": "Retrieve all identified project bottlenecks with severity, impact, and category information",
            
            "get_task_details": "Get detailed information and analysis for a specific task including descriptions from all documents",
            
            "get_milestone_details": "Get detailed information and analysis for a specific milestone including descriptions from all documents",
            
            "get_bottleneck_details": "Get detailed information and analysis for a specific bottleneck including root causes and impacts",
            
            "get_task_suggestions": "Retrieve AI-generated suggestions and recommendations for task management and optimization",
            
            "get_milestone_suggestions": "Retrieve AI-generated suggestions and recommendations for milestone planning and achievement",
            
            "get_bottleneck_suggestions": "Retrieve AI-generated suggestions and recommendations for bottleneck resolution and mitigation",
            
            "get_all_suggestions": "Retrieve all AI-generated suggestions for tasks, milestones, and bottlenecks in the project"
        }
    
    # ========== Data Retrieval Function Implementations ==========
    
    def get_tasks(self, project_id: str, filters: Optional[Dict] = None) -> List[Dict]:
        """
        Get all tasks for a project
        
        Args:
            project_id: Project identifier
            filters: Optional filters (status, priority, category)
            
        Returns:
            List of task dictionaries
        """
        tasks = self.agent.chroma_manager.get_performance_data('tasks', project_id)
        
        if filters:
            tasks = self._apply_filters(tasks, filters)
        
        return tasks
    
    def get_milestones(self, project_id: str, filters: Optional[Dict] = None) -> List[Dict]:
        """
        Get all milestones for a project
        
        Args:
            project_id: Project identifier
            filters: Optional filters (priority, category)
            
        Returns:
            List of milestone dictionaries
        """
        milestones = self.agent.chroma_manager.get_performance_data('milestones', project_id)
        
        if filters:
            milestones = self._apply_filters(milestones, filters)
        
        return milestones
    
    def get_bottlenecks(self, project_id: str, filters: Optional[Dict] = None) -> List[Dict]:
        """
        Get all bottlenecks for a project
        
        Args:
            project_id: Project identifier
            filters: Optional filters (severity, impact, category)
            
        Returns:
            List of bottleneck dictionaries
        """
        bottlenecks = self.agent.chroma_manager.get_performance_data('bottlenecks', project_id)
        
        if filters:
            bottlenecks = self._apply_filters(bottlenecks, filters)
        
        return bottlenecks
    
    def get_task_details(self, project_id: str, task_id: str) -> Dict:
        """
        Get detailed information for a specific task
        
        Args:
            project_id: Project identifier
            task_id: Task identifier
            
        Returns:
            Task details dictionary
        """
        # Get task details from ChromaDB
        details = self.agent.chroma_manager.get_performance_data(
            'tasks', 
            project_id,
            filters={'parent_id': task_id}
        )
        
        return {
            'task_id': task_id,
            'details': details
        }
    
    def get_milestone_details(self, project_id: str, milestone_id: str) -> Dict:
        """
        Get detailed information for a specific milestone
        
        Args:
            project_id: Project identifier
            milestone_id: Milestone identifier
            
        Returns:
            Milestone details dictionary
        """
        details = self.agent.chroma_manager.get_performance_data(
            'milestones',
            project_id,
            filters={'parent_id': milestone_id}
        )
        
        return {
            'milestone_id': milestone_id,
            'details': details
        }
    
    def get_bottleneck_details(self, project_id: str, bottleneck_id: str) -> Dict:
        """
        Get detailed information for a specific bottleneck
        
        Args:
            project_id: Project identifier
            bottleneck_id: Bottleneck identifier
            
        Returns:
            Bottleneck details dictionary
        """
        details = self.agent.chroma_manager.get_performance_data(
            'bottlenecks',
            project_id,
            filters={'parent_id': bottleneck_id}
        )
        
        return {
            'bottleneck_id': bottleneck_id,
            'details': details
        }
    
    def get_task_suggestions(self, project_id: str) -> List[Dict]:
        """
        Get AI-generated suggestions for tasks
        
        Args:
            project_id: Project identifier
            
        Returns:
            List of suggestion dictionaries
        """
        suggestions = self.agent.get_suggestions(project_id, 'tasks')
        return suggestions.get('task_suggestions', [])
    
    def get_milestone_suggestions(self, project_id: str) -> List[Dict]:
        """
        Get AI-generated suggestions for milestones
        
        Args:
            project_id: Project identifier
            
        Returns:
            List of suggestion dictionaries
        """
        suggestions = self.agent.get_suggestions(project_id, 'milestones')
        return suggestions.get('milestone_suggestions', [])
    
    def get_bottleneck_suggestions(self, project_id: str) -> List[Dict]:
        """
        Get AI-generated suggestions for bottlenecks
        
        Args:
            project_id: Project identifier
            
        Returns:
            List of suggestion dictionaries
        """
        suggestions = self.agent.get_suggestions(project_id, 'bottlenecks')
        return suggestions.get('bottleneck_suggestions', [])
    
    def get_all_suggestions(self, project_id: str) -> Dict[str, List[Dict]]:
        """
        Get all suggestions for a project
        
        Args:
            project_id: Project identifier
            
        Returns:
            Dict with task_suggestions, milestone_suggestions, bottleneck_suggestions
        """
        return self.agent.get_suggestions(project_id)
    
    def _apply_filters(self, data: List[Dict], filters: Dict) -> List[Dict]:
        """Apply filters to data"""
        filtered_data = data
        
        for key, value in filters.items():
            filtered_data = [
                item for item in filtered_data
                if item.get('metadata', {}).get(key) == value
            ]
        
        return filtered_data
```

---

## 4. Financial Agent Structure

### Main Financial Agent (`financial_agent/financial_agent.py`)

```python
"""
Financial Agent - Main Coordinator
Manages financial analysis, budgeting, and risk assessment
"""

from datetime import datetime
from typing import Dict, List, Any, Optional

class FinancialAgent:
    """
    Main Financial Agent coordinator
    Manages budget, expenses, revenue, and financial risk
    """
    
    def __init__(self, llm_manager, embeddings_manager, db_manager, orchestrator):
        """
        Initialize Financial Agent
        
        Args:
            llm_manager: LLM manager instance
            embeddings_manager: Embeddings manager instance
            db_manager: Database manager instance
            orchestrator: Orchestrator agent for inter-agent communication
        """
        self.llm_manager = llm_manager
        self.embeddings_manager = embeddings_manager
        self.db_manager = db_manager
        self.orchestrator = orchestrator
        
        # Import worker agents
        from .agents.budget_agent import BudgetAgent
        from .agents.expense_agent import ExpenseAgent
        from .agents.revenue_agent import RevenueAgent
        from .agents.risk_agent import FinancialRiskAgent
        
        # Initialize worker agents
        self.budget_agent = BudgetAgent()
        self.expense_agent = ExpenseAgent()
        self.revenue_agent = RevenueAgent()
        self.risk_agent = FinancialRiskAgent()
    
    def analyze_project_budget(self, project_id: str) -> Dict[str, Any]:
        """
        Analyze project budget using task and milestone data
        
        This function needs data from Performance Agent:
        - Tasks (to allocate budget per task)
        - Milestones (to track budget by milestone)
        
        Args:
            project_id: Project identifier
            
        Returns:
            Budget analysis results
        """
        try:
            print(f"💰 Analyzing budget for project: {project_id}")
            
            # Request task data from Performance Agent via Orchestrator
            tasks = self.orchestrator.route_data_request(
                query="Get all project tasks with their status and priority",
                requesting_agent="financial_agent",
                project_id=project_id
            )
            
            # Request milestone data from Performance Agent via Orchestrator
            milestones = self.orchestrator.route_data_request(
                query="Get all project milestones with timeline information",
                requesting_agent="financial_agent",
                project_id=project_id
            )
            
            # Now use this data for budget analysis
            budget_analysis = self.budget_agent.analyze_budget(
                project_id=project_id,
                tasks=tasks,
                milestones=milestones
            )
            
            return budget_analysis
            
        except Exception as e:
            print(f"❌ Error analyzing budget: {e}")
            return {"success": False, "error": str(e)}
    
    def assess_financial_risk(self, project_id: str) -> Dict[str, Any]:
        """
        Assess financial risks using bottleneck data
        
        This function needs data from Performance Agent:
        - Bottlenecks (to identify financial risk factors)
        - Bottleneck suggestions (for risk mitigation strategies)
        
        Args:
            project_id: Project identifier
            
        Returns:
            Financial risk assessment results
        """
        try:
            print(f"⚠️ Assessing financial risks for project: {project_id}")
            
            # Request bottleneck data from Performance Agent via Orchestrator
            bottlenecks = self.orchestrator.route_data_request(
                query="Get all project bottlenecks with severity and impact information",
                requesting_agent="financial_agent",
                project_id=project_id
            )
            
            # Request bottleneck suggestions for mitigation strategies
            suggestions = self.orchestrator.route_data_request(
                query="Get AI-generated suggestions for bottleneck resolution",
                requesting_agent="financial_agent",
                project_id=project_id
            )
            
            # Analyze financial risk based on bottlenecks
            risk_assessment = self.risk_agent.assess_risk(
                project_id=project_id,
                bottlenecks=bottlenecks,
                mitigation_suggestions=suggestions
            )
            
            return risk_assessment
            
        except Exception as e:
            print(f"❌ Error assessing financial risk: {e}")
            return {"success": False, "error": str(e)}
```

### Financial Agent Data Interface (`financial_agent/data_interface.py`)

```python
"""
Financial Agent Data Interface
Exposes financial data retrieval functions for orchestrator
"""

from typing import Dict, List, Any, Callable, Optional

class FinancialDataInterface:
    """
    Data interface for Financial Agent
    Provides standardized access to financial data for other agents
    """
    
    def __init__(self, financial_agent):
        self.agent = financial_agent
    
    def get_data_functions(self) -> Dict[str, Callable]:
        """Get all data retrieval functions"""
        return {
            "get_budget": self.get_budget,
            "get_expenses": self.get_expenses,
            "get_revenue": self.get_revenue,
            "get_financial_risks": self.get_financial_risks
        }
    
    def get_function_descriptions(self) -> Dict[str, str]:
        """Get descriptions for semantic matching"""
        return {
            "get_budget": "Retrieve project budget information including allocated amounts, spent amounts, and remaining budget",
            "get_expenses": "Retrieve all project expenses with categories, amounts, and transaction dates",
            "get_revenue": "Retrieve project revenue data including projections and actual revenue streams",
            "get_financial_risks": "Retrieve identified financial risks with probability, impact, and mitigation strategies"
        }
    
    def get_budget(self, project_id: str) -> Dict:
        """Get budget data for project"""
        # Implementation
        pass
    
    def get_expenses(self, project_id: str) -> List[Dict]:
        """Get expense data for project"""
        # Implementation
        pass
    
    def get_revenue(self, project_id: str) -> Dict:
        """Get revenue data for project"""
        # Implementation
        pass
    
    def get_financial_risks(self, project_id: str) -> List[Dict]:
        """Get financial risk data for project"""
        # Implementation
        pass
```

---

## 5. Integration in `app.py`

```python
"""
Main application with orchestrator integration
"""

from flask import Flask
from backend.database import DatabaseManager
from backend.llm_manager import LLMManager
from backend.embeddings import EmbeddingsManager
from backend.performance_agent.performance_agent import PerformanceAgent
from backend.performance_agent.data_interface import PerformanceDataInterface
from backend.financial_agent.financial_agent import FinancialAgent
from backend.financial_agent.data_interface import FinancialDataInterface
from backend.orchestrator.agent_registry import AgentRegistry
from backend.orchestrator.orchestrator_agent import OrchestratorAgent

app = Flask(__name__)

# Initialize core components
db_manager = DatabaseManager()
llm_manager = LLMManager()
embeddings_manager = EmbeddingsManager()

# Initialize agent registry
agent_registry = AgentRegistry()

# Initialize orchestrator
orchestrator = OrchestratorAgent(embeddings_manager, agent_registry)

# Initialize Performance Agent
performance_agent = PerformanceAgent(llm_manager, embeddings_manager, db_manager)

# Register Performance Agent
perf_interface = PerformanceDataInterface(performance_agent)
agent_registry.register_agent("performance_agent", perf_interface)

# Initialize Financial Agent (with orchestrator access)
financial_agent = FinancialAgent(
    llm_manager, 
    embeddings_manager, 
    db_manager, 
    orchestrator
)

# Register Financial Agent
fin_interface = FinancialDataInterface(financial_agent)
agent_registry.register_agent("financial_agent", fin_interface)

print("✅ All agents registered with orchestrator")
```

---

## Usage Examples

### Example 1: Financial Agent Requests Task Data

```python
# In financial_agent.py
def allocate_task_budget(self, project_id: str):
    # Financial agent needs task data from Performance Agent
    
    tasks = self.orchestrator.route_data_request(
        query="Get all tasks with priority information",
        requesting_agent="financial_agent",
        project_id=project_id
    )
    
    # Orchestrator:
    # 1. Creates embedding for "Get all tasks with priority information"
    # 2. Compares with all registered function descriptions
    # 3. Finds best match: performance_agent.get_tasks (similarity: 0.92)
    # 4. Calls performance_agent.get_tasks(project_id)
    # 5. Returns task data to financial_agent
    
    # Now financial agent can use the task data
    for task in tasks:
        budget = self.calculate_budget_for_task(task)
        # ... allocate budget
```

### Example 2: Financial Agent Requests Bottleneck Suggestions

```python
# In financial_agent.py
def identify_cost_risks(self, project_id: str):
    # Financial agent needs bottleneck suggestions
    
    suggestions = self.orchestrator.route_data_request(
        query="Get suggestions for resolving project bottlenecks",
        requesting_agent="financial_agent",
        project_id=project_id
    )
    
    # Orchestrator matches to: performance_agent.get_bottleneck_suggestions
    
    # Analyze financial impact of suggested mitigations
    for suggestion in suggestions:
        cost_impact = self.estimate_mitigation_cost(suggestion)
        # ... assess risk
```

---

## Key Benefits

1. **Loose Coupling**: Agents don't need direct references to each other
2. **Semantic Routing**: Natural language queries automatically routed to correct functions
3. **Scalability**: Easy to add new major agents without modifying existing ones
4. **Flexibility**: Query format doesn't need to be exact - semantic matching handles variations
5. **Type Safety**: All data functions have clear interfaces and return types

---

## Next Steps

1. Implement `PerformanceDataInterface` in performance agent
2. Create basic `FinancialAgent` structure with worker agents
3. Implement `FinancialDataInterface` for financial agent
4. Test orchestrator routing with sample queries
5. Add monitoring/logging for inter-agent communication

---

## Notes

- Orchestrator is **ONLY** for inter-agent data transfer, not for routing user queries
- All data retrieval functions should be read-only (no modifications)
- Cosine similarity threshold is configurable (default: 0.5)
- Function descriptions should be clear and specific for best matching accuracy

