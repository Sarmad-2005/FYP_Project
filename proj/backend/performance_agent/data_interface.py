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
            "get_requirements": self.get_requirements,
            "get_actors": self.get_actors,
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
            "get_tasks": "Retrieve all project tasks with their status, priority, and category information from the performance analysis",
            
            "get_milestones": "Retrieve all project milestones with their timeline, priority, and completion status from project tracking",
            
            "get_bottlenecks": "Retrieve all identified project bottlenecks with severity, impact, and category information that may affect project progress",
            
            "get_requirements": "Retrieve project requirements (functional/non-functional) with priority, category, dependencies, and source references",
            
            "get_actors": "Retrieve project actors/stakeholders with type, role, and linked requirements they are responsible for",
            
            "get_task_details": "Get detailed information and analysis for a specific task including descriptions from all documents and completion status",
            
            "get_milestone_details": "Get detailed information and analysis for a specific milestone including descriptions from all project documents",
            
            "get_bottleneck_details": "Get detailed information and analysis for a specific bottleneck including root causes and impacts on the project",
            
            "get_task_suggestions": "Retrieve AI-generated suggestions and recommendations for task management and optimization strategies",
            
            "get_milestone_suggestions": "Retrieve AI-generated suggestions and recommendations for milestone planning and achievement strategies",
            
            "get_bottleneck_suggestions": "Retrieve AI-generated suggestions and recommendations for bottleneck resolution and mitigation strategies",
            
            "get_all_suggestions": "Retrieve all AI-generated suggestions for tasks, milestones, and bottlenecks in the project for comprehensive guidance"
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
        try:
            tasks = self.agent.chroma_manager.get_performance_data('tasks', project_id)
            
            if filters:
                tasks = self._apply_filters(tasks, filters)
            
            return tasks
        except Exception as e:
            print(f"Error getting tasks: {e}")
            return []
    
    def get_milestones(self, project_id: str, filters: Optional[Dict] = None) -> List[Dict]:
        """
        Get all milestones for a project
        
        Args:
            project_id: Project identifier
            filters: Optional filters (priority, category)
            
        Returns:
            List of milestone dictionaries
        """
        try:
            milestones = self.agent.chroma_manager.get_performance_data('milestones', project_id)
            
            if filters:
                milestones = self._apply_filters(milestones, filters)
            
            return milestones
        except Exception as e:
            print(f"Error getting milestones: {e}")
            return []
    
    def get_bottlenecks(self, project_id: str, filters: Optional[Dict] = None) -> List[Dict]:
        """
        Get all bottlenecks for a project
        
        Args:
            project_id: Project identifier
            filters: Optional filters (severity, impact, category)
            
        Returns:
            List of bottleneck dictionaries
        """
        try:
            bottlenecks = self.agent.chroma_manager.get_performance_data('bottlenecks', project_id)
            
            if filters:
                bottlenecks = self._apply_filters(bottlenecks, filters)
            
            return bottlenecks
        except Exception as e:
            print(f"Error getting bottlenecks: {e}")
            return []

    def get_requirements(self, project_id: str, filters: Optional[Dict] = None) -> List[Dict]:
        """Get all requirements for a project"""
        try:
            items = self.agent.chroma_manager.get_performance_data('requirements', project_id)
            if filters:
                items = self._apply_filters(items, filters)
            return items
        except Exception as e:
            print(f"Error getting requirements: {e}")
            return []

    def get_actors(self, project_id: str, filters: Optional[Dict] = None) -> List[Dict]:
        """Get all actors/stakeholders for a project"""
        try:
            items = self.agent.chroma_manager.get_performance_data('actors', project_id)
            if filters:
                items = self._apply_filters(items, filters)
            return items
        except Exception as e:
            print(f"Error getting actors: {e}")
            return []
    
    def get_task_details(self, project_id: str, task_id: str = None) -> Dict:
        """
        Get detailed information for task(s)
        
        Args:
            project_id: Project identifier
            task_id: Task identifier (optional)
            
        Returns:
            Task details dictionary
        """
        try:
            if task_id:
                # Get details for specific task
                details = self.agent.chroma_manager.get_performance_data(
                    'tasks',
                    project_id,
                    filters={'parent_id': task_id, 'type': 'task_detail'}
                )
            else:
                # Get all task details
                details = self.agent.chroma_manager.get_performance_data(
                    'tasks',
                    project_id,
                    filters={'type': 'task_detail'}
                )
            
            return {
                'task_id': task_id,
                'details': details
            }
        except Exception as e:
            print(f"Error getting task details: {e}")
            return {'task_id': task_id, 'details': []}
    
    def get_milestone_details(self, project_id: str, milestone_id: str = None) -> Dict:
        """
        Get detailed information for milestone(s)
        
        Args:
            project_id: Project identifier
            milestone_id: Milestone identifier (optional)
            
        Returns:
            Milestone details dictionary
        """
        try:
            if milestone_id:
                details = self.agent.chroma_manager.get_performance_data(
                    'milestones',
                    project_id,
                    filters={'parent_id': milestone_id, 'type': 'milestone_detail'}
                )
            else:
                details = self.agent.chroma_manager.get_performance_data(
                    'milestones',
                    project_id,
                    filters={'type': 'milestone_detail'}
                )
            
            return {
                'milestone_id': milestone_id,
                'details': details
            }
        except Exception as e:
            print(f"Error getting milestone details: {e}")
            return {'milestone_id': milestone_id, 'details': []}
    
    def get_bottleneck_details(self, project_id: str, bottleneck_id: str = None) -> Dict:
        """
        Get detailed information for bottleneck(s)
        
        Args:
            project_id: Project identifier
            bottleneck_id: Bottleneck identifier (optional)
            
        Returns:
            Bottleneck details dictionary
        """
        try:
            if bottleneck_id:
                details = self.agent.chroma_manager.get_performance_data(
                    'bottlenecks',
                    project_id,
                    filters={'parent_id': bottleneck_id, 'type': 'bottleneck_detail'}
                )
            else:
                details = self.agent.chroma_manager.get_performance_data(
                    'bottlenecks',
                    project_id,
                    filters={'type': 'bottleneck_detail'}
                )
            
            return {
                'bottleneck_id': bottleneck_id,
                'details': details
            }
        except Exception as e:
            print(f"Error getting bottleneck details: {e}")
            return {'bottleneck_id': bottleneck_id, 'details': []}
    
    def get_task_suggestions(self, project_id: str) -> List[Dict]:
        """
        Get AI-generated suggestions for tasks
        
        Args:
            project_id: Project identifier
            
        Returns:
            List of suggestion dictionaries
        """
        try:
            suggestions = self.agent.get_suggestions(project_id, 'tasks')
            return suggestions.get('task_suggestions', [])
        except Exception as e:
            print(f"Error getting task suggestions: {e}")
            return []
    
    def get_milestone_suggestions(self, project_id: str) -> List[Dict]:
        """
        Get AI-generated suggestions for milestones
        
        Args:
            project_id: Project identifier
            
        Returns:
            List of suggestion dictionaries
        """
        try:
            suggestions = self.agent.get_suggestions(project_id, 'milestones')
            return suggestions.get('milestone_suggestions', [])
        except Exception as e:
            print(f"Error getting milestone suggestions: {e}")
            return []
    
    def get_bottleneck_suggestions(self, project_id: str) -> List[Dict]:
        """
        Get AI-generated suggestions for bottlenecks
        
        Args:
            project_id: Project identifier
            
        Returns:
            List of suggestion dictionaries
        """
        try:
            suggestions = self.agent.get_suggestions(project_id, 'bottlenecks')
            return suggestions.get('bottleneck_suggestions', [])
        except Exception as e:
            print(f"Error getting bottleneck suggestions: {e}")
            return []
    
    def get_all_suggestions(self, project_id: str) -> Dict[str, List[Dict]]:
        """
        Get all suggestions for a project
        
        Args:
            project_id: Project identifier
            
        Returns:
            Dict with task_suggestions, milestone_suggestions, bottleneck_suggestions
        """
        try:
            return self.agent.get_suggestions(project_id)
        except Exception as e:
            print(f"Error getting all suggestions: {e}")
            return {
                'task_suggestions': [],
                'milestone_suggestions': [],
                'bottleneck_suggestions': []
            }
    
    def _apply_filters(self, data: List[Dict], filters: Dict) -> List[Dict]:
        """Apply filters to data"""
        filtered_data = data
        
        for key, value in filters.items():
            filtered_data = [
                item for item in filtered_data
                if item.get('metadata', {}).get(key) == value
            ]
        
        return filtered_data





