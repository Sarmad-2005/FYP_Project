"""
Resource Agent - Main Coordinator
Manages task optimization and resource allocation for projects
"""

import os
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from .agents.task_optimization_agent import TaskOptimizationAgent
from .agents.resource_optimization_agent import ResourceOptimizationAgent
from .chroma_manager import ResourceChromaManager


class ResourceAgent:
    """Main Resource Agent coordinator"""
    
    def __init__(self, llm_manager, embeddings_manager, db_manager, orchestrator=None):
        """
        Initialize Resource Agent
        
        Args:
            llm_manager: LLM manager instance
            embeddings_manager: Embeddings manager instance
            db_manager: Database manager instance
            orchestrator: Orchestrator instance (optional)
        """
        self.llm_manager = llm_manager
        self.embeddings_manager = embeddings_manager
        self.db_manager = db_manager
        self.orchestrator = orchestrator
        
        # Initialize centralized ChromaDB manager
        self.chroma_manager = ResourceChromaManager()
        
        # Initialize worker agents
        self.task_optimization_agent = TaskOptimizationAgent(self.chroma_manager)
        self.resource_optimization_agent = ResourceOptimizationAgent(self.chroma_manager)
        
        # Resource data storage
        self.resource_data_dir = 'data/resource'
        self._ensure_resource_data_directory()
    
    def _ensure_resource_data_directory(self):
        """Create resource data directory if it doesn't exist"""
        if not os.path.exists(self.resource_data_dir):
            os.makedirs(self.resource_data_dir)
    
    def first_time_generation(self, project_id: str, document_id: str) -> Dict[str, Any]:
        """
        First time generation of all resource metrics for a project
        
        Args:
            project_id: Project identifier
            document_id: Document identifier
            
        Returns:
            Dict with results of first time generation
        """
        results = {
            'project_id': project_id,
            'document_id': document_id,
            'timestamp': datetime.now().isoformat(),
            'task_analysis': {'success': False, 'count': 0},
            'dependencies': {'success': False, 'count': 0},
            'critical_path': {'success': False, 'path_length': 0},
            'overall_success': False
        }
        
        try:
            print(f"\n{'='*80}")
            print(f"🔧 STARTING FIRST-TIME RESOURCE ANALYSIS")
            print(f"📁 Project ID: {project_id}")
            print(f"📄 Document ID: {document_id}")
            print(f"{'='*80}\n")
            
            # Step 1: Analyze all tasks
            print("📊 STEP 1/3: Analyzing Tasks (Priority, Complexity, Time)...")
            task_analysis_result = self.task_optimization_agent.analyze_all_tasks(
                project_id, self.llm_manager
            )
            results['task_analysis']['success'] = task_analysis_result['success']
            results['task_analysis']['count'] = task_analysis_result.get('tasks_analyzed', 0)
            results['task_analysis']['error'] = task_analysis_result.get('error')
            print(f"   ✅ Tasks Analyzed: {results['task_analysis']['count']}")
            
            # Step 2: Create task dependencies
            print("\n🔗 STEP 2/3: Creating Task Dependencies...")
            dependencies_result = self.task_optimization_agent.create_task_dependencies(
                project_id, self.llm_manager
            )
            results['dependencies']['success'] = dependencies_result.get('success', False)
            results['dependencies']['count'] = dependencies_result.get('dependencies_created', 0)
            results['dependencies']['error'] = dependencies_result.get('error')
            results['dependencies']['warning'] = dependencies_result.get('warning')
            if results['dependencies']['count'] > 0:
                print(f"   ✅ Dependencies Created: {results['dependencies']['count']}")
            else:
                print(f"   ⚠️ No Dependencies Created: {dependencies_result.get('warning', 'API limits or errors')}")
                print(f"   Continuing with critical path calculation using task durations only...")
            
            # Step 3: Calculate critical path
            print("\n📈 STEP 3/3: Calculating Critical Path...")
            critical_path_result = self.task_optimization_agent.calculate_critical_path(project_id)
            results['critical_path']['success'] = critical_path_result['success']
            results['critical_path']['path_length'] = critical_path_result.get('critical_tasks_count', 0)
            results['critical_path']['total_duration'] = critical_path_result.get('total_duration_hours', 0)
            results['critical_path']['error'] = critical_path_result.get('error')
            print(f"   ✅ Critical Path: {results['critical_path']['path_length']} tasks, "
                  f"{results['critical_path']['total_duration']:.1f} hours")
            
            # Determine overall success (dependencies are optional if API fails)
            results['overall_success'] = (
                results['task_analysis']['success'] and
                results['critical_path']['success']
            )
            
            print(f"\n{'='*80}")
            print(f"✅ RESOURCE ANALYSIS COMPLETE!")
            print(f"   Tasks Analyzed: {results['task_analysis']['count']}")
            print(f"   Dependencies: {results['dependencies']['count']}")
            print(f"   Critical Path: {results['critical_path']['path_length']} tasks")
            print(f"{'='*80}\n")
            
            # Save results
            self._save_resource_results(project_id, results)
            
            return results
            
        except Exception as e:
            print(f"❌ Error in first-time generation: {e}")
            results['error'] = str(e)
            return results
    
    def refresh_resource_data(self, project_id: str) -> Dict[str, Any]:
        """
        Refresh resource data (re-analyze if new tasks added)
        
        Args:
            project_id: Project identifier
            
        Returns:
            Dict with updated resource data
        """
        try:
            print(f"\n{'='*80}")
            print(f"🔄 REFRESHING RESOURCE DATA - Project: {project_id}")
            print(f"{'='*80}\n")
            
            # Check if there are new tasks
            current_tasks = self.task_optimization_agent.get_all_project_tasks(project_id)
            analyzed_tasks = self.chroma_manager.get_resource_data('tasks_analysis', project_id)
            
            # Check if we need to re-analyze
            if len(current_tasks) > len(analyzed_tasks):
                print(f"📋 Found {len(current_tasks) - len(analyzed_tasks)} new tasks, re-analyzing...")
                
                # Re-analyze all tasks
                task_analysis_result = self.task_optimization_agent.analyze_all_tasks(
                    project_id, self.llm_manager
                )
                
                # Re-create dependencies
                dependencies_result = self.task_optimization_agent.create_task_dependencies(
                    project_id, self.llm_manager
                )
                
                # Recalculate critical path
                critical_path_result = self.task_optimization_agent.calculate_critical_path(project_id)
                
                return {
                    'success': True,
                    'project_id': project_id,
                    'tasks_analyzed': task_analysis_result.get('tasks_analyzed', 0),
                    'dependencies_created': dependencies_result.get('dependencies_created', 0),
                    'critical_path_length': critical_path_result.get('critical_tasks_count', 0)
                }
            else:
                print("✅ No new tasks found - resource data is up to date")
                return self._get_current_resource_data(project_id)
            
        except Exception as e:
            print(f"❌ Error refreshing resource data: {e}")
            return {'success': False, 'error': str(e), 'project_id': project_id}
    
    def _get_current_resource_data(self, project_id: str) -> Dict[str, Any]:
        """Get current resource data without processing"""
        try:
            # Get task analysis
            task_analysis = self.chroma_manager.get_resource_data('tasks_analysis', project_id)
            
            # Get dependencies
            dependencies = self.chroma_manager.get_resource_data('task_dependencies', project_id)
            
            # Get critical path
            critical_path_data = self.chroma_manager.get_resource_data('critical_path', project_id)
            critical_path = critical_path_data[0] if critical_path_data else {}
            
            # Get work team
            work_team = self.resource_optimization_agent.get_work_team(project_id)
            
            return {
                'success': True,
                'project_id': project_id,
                'tasks_analyzed_count': len(task_analysis),
                'dependencies_count': len(dependencies),
                'critical_path_length': len(critical_path.get('path_tasks', [])) if isinstance(critical_path.get('path_tasks'), list) else 0,
                'critical_path_duration': critical_path.get('total_duration_hours', 0),
                'work_team_count': len(work_team),
                'last_analysis': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Error getting current resource data: {str(e)}",
                'project_id': project_id
            }
    
    def _save_resource_results(self, project_id: str, results: Dict):
        """Save resource results to file"""
        try:
            results_file = os.path.join(
                self.resource_data_dir,
                f"{project_id}_resource_analysis.json"
            )
            
            with open(results_file, 'w') as f:
                json.dump(results, f, indent=2)
                
        except Exception as e:
            print(f"Error saving resource results: {e}")
    
    def get_task_analysis(self, project_id: str) -> List[Dict]:
        """Get task analysis for a project"""
        try:
            return self.chroma_manager.get_resource_data('tasks_analysis', project_id)
        except Exception as e:
            print(f"Error getting task analysis: {e}")
            return []
    
    def get_task_dependencies(self, project_id: str) -> List[Dict]:
        """Get task dependencies for a project"""
        try:
            return self.chroma_manager.get_resource_data('task_dependencies', project_id)
        except Exception as e:
            print(f"Error getting task dependencies: {e}")
            return []
    
    def get_critical_path(self, project_id: str) -> Dict[str, Any]:
        """Get critical path for a project"""
        try:
            critical_path_data = self.chroma_manager.get_resource_data('critical_path', project_id)
            if critical_path_data:
                return critical_path_data[0]
            return {}
        except Exception as e:
            print(f"Error getting critical path: {e}")
            return {}
    
    def get_work_team(self, project_id: str) -> List[Dict]:
        """Get work team for a project"""
        try:
            return self.resource_optimization_agent.get_work_team(project_id)
        except Exception as e:
            print(f"Error getting work team: {e}")
            return []
    
    def get_financial_summary(self, project_id: str) -> Dict[str, Any]:
        """Get financial summary for resource allocation"""
        try:
            return self.resource_optimization_agent.get_project_financial_summary(project_id)
        except Exception as e:
            print(f"Error getting financial summary: {e}")
            return {'success': False, 'error': str(e)}

