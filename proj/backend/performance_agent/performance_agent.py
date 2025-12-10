"""
Performance Agent - Main Coordinator
Manages all performance analysis agents and scheduling
"""

import os
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from .agents.milestone_agent import MilestoneAgent
from .agents.task_agent import TaskAgent
from .agents.bottleneck_agent import BottleneckAgent
from .agents.requirements_agent import RequirementsAgent
from .agents.actors_agent import ActorsAgent
from .chroma_manager import PerformanceChromaManager


class PerformanceAgent:
    """Main Performance Agent coordinator"""
    
    def __init__(self, llm_manager, embeddings_manager, db_manager):
        self.llm_manager = llm_manager
        self.embeddings_manager = embeddings_manager
        self.db_manager = db_manager
        
        # Initialize centralized ChromaDB manager
        self.chroma_manager = PerformanceChromaManager()
        
        # Initialize worker agents with shared ChromaDB manager
        self.milestone_agent = MilestoneAgent(self.chroma_manager)
        self.task_agent = TaskAgent(self.chroma_manager)
        self.bottleneck_agent = BottleneckAgent(self.chroma_manager)
        self.requirements_agent = RequirementsAgent(self.chroma_manager)
        self.actors_agent = ActorsAgent(self.chroma_manager)
        
        # Performance data storage
        self.performance_data_dir = 'data/performance'
        self._ensure_performance_data_directory()
    
    def _ensure_performance_data_directory(self):
        """Create performance data directory if it doesn't exist"""
        if not os.path.exists(self.performance_data_dir):
            os.makedirs(self.performance_data_dir)
    
    def first_time_generation(self, project_id: str, document_id: str) -> Dict[str, Any]:
        """
        First time generation of all performance metrics for a project
        
        Args:
            project_id (str): Project identifier
            document_id (str): Document identifier
            
        Returns:
            dict: Results of first time generation
        """
        results = {
            'project_id': project_id,
            'document_id': document_id,
            'timestamp': datetime.now().isoformat(),
            'milestones': {'success': False, 'count': 0, 'details_count': 0, 'suggestions_count': 0},
            'tasks': {'success': False, 'count': 0, 'details_count': 0, 'suggestions_count': 0, 'completion_analysis': False},
            'bottlenecks': {'success': False, 'count': 0, 'details_count': 0, 'suggestions_count': 0},
            'requirements': {'success': False, 'count': 0, 'details_count': 0, 'suggestions_count': 0},
            'actors': {'success': False, 'count': 0, 'details_count': 0, 'linked_requirements_count': 0},
            'completion_score': 0.0,
            'overall_success': False
        }
        
        try:
            print(f"\n{'='*80}")
            print(f"🚀 STARTING FIRST-TIME PERFORMANCE ANALYSIS")
            print(f"📁 Project ID: {project_id}")
            print(f"📄 Document ID: {document_id}")
            print(f"{'='*80}\n")
            
            # 1. Extract milestones
            print("📍 STEP 1/7: Extracting Milestones...")
            milestone_result = self.milestone_agent.extract_milestones_from_document(
                project_id, document_id, self.llm_manager
            )
            results['milestones']['success'] = milestone_result['success']
            results['milestones']['count'] = milestone_result.get('milestones_count', 0)
            results['milestones']['error'] = milestone_result.get('error')
            print(f"   ✅ Milestones: {results['milestones']['count']} found (Success: {results['milestones']['success']})")
            
            # 2. Extract tasks
            print("\n📍 STEP 2/7: Extracting Tasks...")
            task_result = self.task_agent.extract_tasks_from_document(
                project_id, document_id, self.llm_manager
            )
            results['tasks']['success'] = task_result['success']
            results['tasks']['count'] = task_result.get('tasks_count', 0)
            results['tasks']['error'] = task_result.get('error')
            print(f"   ✅ Tasks: {results['tasks']['count']} found (Success: {results['tasks']['success']})")
            
            # 3. Extract bottlenecks
            print("\n📍 STEP 3/7: Extracting Bottlenecks...")
            bottleneck_result = self.bottleneck_agent.extract_bottlenecks_from_document(
                project_id, document_id, self.llm_manager
            )
            results['bottlenecks']['success'] = bottleneck_result['success']
            results['bottlenecks']['count'] = bottleneck_result.get('bottlenecks_count', 0)
            results['bottlenecks']['error'] = bottleneck_result.get('error')
            print(f"   ✅ Bottlenecks: {results['bottlenecks']['count']} found (Success: {results['bottlenecks']['success']})")
            
            # 4. Extract requirements
            print("\n📍 STEP 4: Extracting Requirements...")
            requirements_result = self.requirements_agent.extract_requirements_from_document(
                project_id, document_id, self.llm_manager
            )
            results['requirements']['success'] = requirements_result['success']
            results['requirements']['count'] = requirements_result.get('requirements_count', 0)
            results['requirements']['error'] = requirements_result.get('error')
            print(f"   ✅ Requirements: {results['requirements']['count']} found (Success: {results['requirements']['success']})")

            # 5. Extract actors (after requirements)
            print("\n📍 STEP 5: Extracting Actors...")
            actors_result = self.actors_agent.extract_actors_from_document(
                project_id, document_id, self.llm_manager
            )
            results['actors']['success'] = actors_result['success']
            results['actors']['count'] = actors_result.get('actors_count', 0)
            results['actors']['error'] = actors_result.get('error')
            print(f"   ✅ Actors: {results['actors']['count']} found (Success: {results['actors']['success']})")
            
            # 6. Extract milestone details
            print("\n📍 STEP 6: Extracting Milestone Details...")
            if milestone_result['success'] and milestone_result.get('milestones'):
                milestone_details_count = 0
                total_milestones = len(milestone_result.get('milestones', []))
                print(f"   Processing {total_milestones} milestones...")
                for i, milestone in enumerate(milestone_result.get('milestones', []), 1):
                    print(f"   - Milestone {i}/{total_milestones}: {milestone.get('milestone', 'Unknown')[:50]}...")
                    details_result = self.milestone_agent.extract_milestone_details(
                        project_id, milestone['milestone'], self.llm_manager
                    )
                    if details_result['success']:
                        # Store details in separate collection
                        self._append_milestone_details(
                            milestone.get('id', f"milestone_{project_id}_{i}"),
                            project_id,
                            document_id,
                            details_result['details']
                        )
                        milestone_details_count += 1
                results['milestones']['details_count'] = milestone_details_count
                print(f"   ✅ Details extracted for {milestone_details_count}/{total_milestones} milestones")
            else:
                print(f"   ⏭️ Skipped (no milestones found)")
            
            # 5. Extract task details and completion analysis
            print("\n📍 STEP 5/7: Extracting Task Details & Completion Analysis...")
            if task_result['success'] and task_result.get('tasks'):
                task_details_count = 0
                completion_statuses = []
                total_tasks = len(task_result.get('tasks', []))
                print(f"   Processing {total_tasks} tasks...")
                
                for i, task in enumerate(task_result.get('tasks', []), 1):
                    # Extract task details
                    details_result = self.task_agent.extract_task_details(
                        project_id, task['task'], self.llm_manager
                    )
                    if details_result['success']:
                        # Store details in separate collection
                        self._append_task_details(
                            task.get('id', f"task_{project_id}_{i}"),
                            project_id,
                            document_id,
                            details_result['details']
                        )
                        task_details_count += 1
                    
                    # Analyze task completion status
                    completion_result = self.task_agent.determine_task_completion_status(
                        project_id, document_id, task['task'], self.llm_manager
                    )
                    if completion_result['success']:
                        completion_statuses.append(completion_result['completion_status'])
                
                results['tasks']['details_count'] = task_details_count
                results['tasks']['completion_analysis'] = len(completion_statuses) > 0
                
                # Calculate completion score
                if completion_statuses:
                    results['completion_score'] = sum(completion_statuses) / len(completion_statuses)
            
            # 6. Extract bottleneck details
            if bottleneck_result['success'] and bottleneck_result.get('bottlenecks'):
                bottleneck_details_count = 0
                for i, bottleneck in enumerate(bottleneck_result.get('bottlenecks', []), 1):
                    details_result = self.bottleneck_agent.extract_bottleneck_details(
                        project_id, bottleneck['bottleneck'], self.llm_manager
                    )
                    if details_result['success']:
                        # Store details in separate collection
                        self._append_bottleneck_details(
                            bottleneck.get('id', f"bottleneck_{project_id}_{i}"),
                            project_id,
                            document_id,
                            details_result['details']
                        )
                        bottleneck_details_count += 1
                results['bottlenecks']['details_count'] = bottleneck_details_count
            
            # 6. Calculate completion score
            print("\n📍 STEP 6/7: Calculating Completion Score...")
            
            # 7. Generate suggestions
            print("\n📍 STEP 7/7: Generating AI Suggestions...")
            suggestions = {}
            
            # Generate milestone suggestions
            if milestone_result['success'] and milestone_result.get('milestones'):
                print(f"   Generating milestone suggestions...")
                milestone_suggestions = self.milestone_agent.generate_milestone_suggestions(
                    project_id, milestone_result.get('milestones', []), self.llm_manager
                )
                if milestone_suggestions['success']:
                    suggestions['milestone_suggestions'] = milestone_suggestions['suggestions']
                    results['milestones']['suggestions_count'] = milestone_suggestions.get('count', 0)
            
            # Generate task suggestions
            if task_result['success'] and task_result.get('tasks'):
                task_suggestions = self.task_agent.generate_task_suggestions(
                    project_id, task_result.get('tasks', []), self.llm_manager
                )
                if task_suggestions['success']:
                    suggestions['task_suggestions'] = task_suggestions['suggestions']
                    results['tasks']['suggestions_count'] = task_suggestions.get('count', 0)
            
            # Generate bottleneck suggestions
            if bottleneck_result['success'] and bottleneck_result.get('bottlenecks'):
                bottleneck_suggestions = self.bottleneck_agent.generate_bottleneck_suggestions(
                    project_id, bottleneck_result.get('bottlenecks', []), self.llm_manager
                )
                if bottleneck_suggestions['success']:
                    suggestions['bottleneck_suggestions'] = bottleneck_suggestions['suggestions']
                    results['bottlenecks']['suggestions_count'] = bottleneck_suggestions.get('count', 0)
            
            # 8. Store suggestions
            if suggestions:
                self.store_suggestions(project_id, suggestions)
            
            # 9. Determine overall success
            results['overall_success'] = (
                results['milestones']['success'] and 
                results['tasks']['success'] and 
                results['bottlenecks']['success']
            )
            
            print(f"\n{'='*80}")
            print(f"✅ ANALYSIS COMPLETE!")
            print(f"   Overall Success: {results['overall_success']}")
            print(f"   Milestones: {results['milestones']['count']} ({results['milestones']['details_count']} detailed)")
            print(f"   Tasks: {results['tasks']['count']} ({results['tasks']['details_count']} detailed)")
            print(f"   Bottlenecks: {results['bottlenecks']['count']} ({results['bottlenecks']['details_count']} detailed)")
            print(f"   Completion Score: {results.get('completion_score', 0)}%")
            print(f"{'='*80}\n")
            
            # 10. Save results
            self._save_performance_results(project_id, results)
            
            return results
            
        except Exception as e:
            print(f"\n❌ ERROR in first_time_generation: {str(e)}")
            print(f"   Error type: {type(e).__name__}")
            import traceback
            print(f"   Traceback:\n{traceback.format_exc()}")
            results['error'] = f"First time generation failed: {str(e)}"
            return results
    
    def update_performance_metrics(self, project_id: str, new_document_id: str) -> Dict[str, Any]:
        """
        Update performance metrics when new document is added
        
        Args:
            project_id (str): Project identifier
            new_document_id (str): New document identifier
            
        Returns:
            dict: Update results
        """
        results = {
            'project_id': project_id,
            'new_document_id': new_document_id,
            'timestamp': datetime.now().isoformat(),
            'updates': {}
        }
        
        try:
            # Get existing milestones and update with new document
            existing_milestones = self.milestone_agent.get_project_milestones(project_id)
            
            # Extract new milestones from new document
            new_milestone_result = self.milestone_agent.extract_milestones_from_document(
                project_id, new_document_id, self.llm_manager
            )
            
            if new_milestone_result['success']:
                # Update existing milestones with new context
                self._update_milestone_details(project_id, existing_milestones, new_document_id)
                results['updates']['milestones'] = {
                    'new_count': new_milestone_result.get('milestones_count', 0),
                    'updated_existing': len(existing_milestones)
                }
            
            # Similar updates for tasks and bottlenecks
            # (Implementation will be added when task and bottleneck agents are ready)
            
            return results
            
        except Exception as e:
            results['error'] = f"Update failed: {str(e)}"
            return results
    
    def _update_milestone_details(self, project_id: str, existing_milestones: List[Dict], 
                                new_document_id: str):
        """Update existing milestones with details from new document"""
        try:
            for milestone in existing_milestones:
                # Extract details for this milestone from new document
                milestone_details = self.milestone_agent.extract_milestone_details(
                    project_id, milestone['milestone'], self.llm_manager
                )
                
                if milestone_details['success']:
                    # Store milestone details in separate collection
                    self._append_milestone_details(
                        milestone['id'], 
                        project_id,
                        new_document_id,
                        milestone_details['details']
                    )
                    
        except Exception as e:
            print(f"Error updating milestone details: {e}")
    
    def _save_performance_results(self, project_id: str, results: Dict[str, Any]):
        """Save performance results to file"""
        try:
            results_file = os.path.join(self.performance_data_dir, f"{project_id}_performance.json")
            
            # Load existing results if any
            existing_results = {}
            if os.path.exists(results_file):
                with open(results_file, 'r') as f:
                    existing_results = json.load(f)
            
            # Update with new results
            existing_results[results['timestamp']] = results
            
            # Save updated results
            with open(results_file, 'w') as f:
                json.dump(existing_results, f, indent=2)
                
        except Exception as e:
            print(f"Error saving performance results: {e}")
    
    def get_project_performance_summary(self, project_id: str, include_details: bool = False) -> Dict[str, Any]:
        """Get performance summary for a project"""
        try:
            # Get milestones
            milestones = self.milestone_agent.get_project_milestones(project_id)
            
            # Get tasks
            tasks = self.task_agent.get_project_tasks(project_id)
            
            # Get bottlenecks
            bottlenecks = self.bottleneck_agent.get_project_bottlenecks(project_id)
            
            summary = {
                'project_id': project_id,
                'milestones_count': len(milestones),
                'tasks_count': len(tasks),
                'bottlenecks_count': len(bottlenecks),
                'milestones': milestones,
                'tasks': tasks,
                'bottlenecks': bottlenecks,
                'last_updated': datetime.now().isoformat()
            }
            
            # Optionally include details
            if include_details:
                summary['milestone_details'] = self.get_milestone_details_for_project(project_id)
                summary['task_details'] = self.get_task_details_for_project(project_id)
                summary['bottleneck_details'] = self.get_bottleneck_details_for_project(project_id)
            
            return summary
            
        except Exception as e:
            return {
                'error': f"Error getting performance summary: {str(e)}",
                'project_id': project_id
            }
    
    def immediate_update_performance(self, project_id: str) -> Dict[str, Any]:
        """
        Immediately process new documents and update performance metrics
        Same as 12-hour update but runs on-demand for a single project
        """
        try:
            print(f"\n{'='*80}")
            print(f"🔄 IMMEDIATE PERFORMANCE UPDATE - Project: {project_id}")
            print(f"{'='*80}\n")
            
            # Get project documents
            documents = self.db_manager.get_project_documents(project_id)
            
            if not documents:
                return {
                    'success': False,
                    'error': 'No documents found in project',
                    'project_id': project_id,
                    'new_documents_processed': 0
                }
            
            # Check if there are new documents since last update
            last_update = self._get_last_performance_update(project_id)
            
            # Find new documents
            new_documents = []
            if last_update:
                for document in documents:
                    if document['created_at'] > last_update:
                        new_documents.append(document)
            else:
                # First time update for this project
                new_documents = documents
            
            if not new_documents:
                print("✅ No new documents to process - regenerating suggestions with existing data")
                
                # Even if no new documents, regenerate suggestions with existing data
                try:
                    milestones = self.milestone_agent.get_project_milestones(project_id)
                    tasks = self.task_agent.get_project_tasks(project_id)
                    bottlenecks = self.bottleneck_agent.get_project_bottlenecks(project_id)
                    
                    print("\n🤖 Regenerating AI suggestions...")
                    
                    # Collect suggestions
                    suggestions = {
                        'milestone_suggestions': [],
                        'task_suggestions': [],
                        'bottleneck_suggestions': []
                    }
                    
                    # Generate suggestions for each type
                    if milestones:
                        milestone_suggestions = self.milestone_agent.generate_milestone_suggestions(project_id, milestones, self.llm_manager)
                        if milestone_suggestions['success']:
                            suggestions['milestone_suggestions'] = milestone_suggestions['suggestions']
                            print(f"   ✅ Generated {len(milestone_suggestions['suggestions'])} milestone suggestions")
                        else:
                            print(f"   ⚠️  Milestone suggestions failed: {milestone_suggestions.get('error', 'Unknown')}")
                    
                    if tasks:
                        task_suggestions = self.task_agent.generate_task_suggestions(project_id, tasks, self.llm_manager)
                        if task_suggestions['success']:
                            suggestions['task_suggestions'] = task_suggestions['suggestions']
                            print(f"   ✅ Generated {len(task_suggestions['suggestions'])} task suggestions")
                        else:
                            print(f"   ⚠️  Task suggestions failed: {task_suggestions.get('error', 'Unknown')}")
                    
                    if bottlenecks:
                        bottleneck_suggestions = self.bottleneck_agent.generate_bottleneck_suggestions(project_id, bottlenecks, self.llm_manager)
                        if bottleneck_suggestions['success']:
                            suggestions['bottleneck_suggestions'] = bottleneck_suggestions['suggestions']
                            print(f"   ✅ Generated {len(bottleneck_suggestions['suggestions'])} bottleneck suggestions")
                        else:
                            print(f"   ⚠️  Bottleneck suggestions failed: {bottleneck_suggestions.get('error', 'Unknown')}")
                    
                    # Store suggestions
                    if any(suggestions.values()):
                        self.store_suggestions(project_id, suggestions)
                        print("   💾 Suggestions stored successfully")
                        
                except Exception as e:
                    print(f"   ⚠️  Error generating suggestions: {e}")
                    import traceback
                    print(f"   Traceback: {traceback.format_exc()}")
                
                # Return current data
                return self._get_current_performance_data(project_id)
            
            print(f"📄 Found {len(new_documents)} new document(s) to process")
            
            # Process new documents with embedding verification
            successful_updates = 0
            failed_documents = []
            
            for document in new_documents:
                doc_name = document.get('filename', document['id'][:8])
                print(f"\n{'─'*80}")
                print(f"📄 Processing: {doc_name}")
                print(f"{'─'*80}")
                
                # Verify embeddings exist before processing
                if self._verify_document_embeddings(project_id, document['id']):
                    success = self.update_performance_metrics_for_new_document(project_id, document['id'])
                    if success:
                        successful_updates += 1
                        print(f"✅ Successfully processed: {doc_name}")
                    else:
                        failed_documents.append(doc_name)
                        print(f"❌ Failed to process: {doc_name}")
                else:
                    failed_documents.append(doc_name)
                    print(f"⚠️ Missing embeddings for: {doc_name}")
            
            # Regenerate AI suggestions if documents were processed
            if successful_updates > 0:
                print("\n🤖 Regenerating AI suggestions...")
                try:
                    # Get current data for suggestions
                    milestones = self.milestone_agent.get_project_milestones(project_id)
                    tasks = self.task_agent.get_project_tasks(project_id)
                    bottlenecks = self.bottleneck_agent.get_project_bottlenecks(project_id)
                    
                    # Collect suggestions
                    suggestions = {
                        'milestone_suggestions': [],
                        'task_suggestions': [],
                        'bottleneck_suggestions': []
                    }
                    
                    # Generate suggestions for each type
                    if milestones:
                        milestone_suggestions = self.milestone_agent.generate_milestone_suggestions(project_id, milestones, self.llm_manager)
                        if milestone_suggestions['success']:
                            suggestions['milestone_suggestions'] = milestone_suggestions['suggestions']
                            print(f"   ✅ Generated {len(milestone_suggestions['suggestions'])} milestone suggestions")
                    
                    if tasks:
                        task_suggestions = self.task_agent.generate_task_suggestions(project_id, tasks, self.llm_manager)
                        if task_suggestions['success']:
                            suggestions['task_suggestions'] = task_suggestions['suggestions']
                            print(f"   ✅ Generated {len(task_suggestions['suggestions'])} task suggestions")
                    
                    if bottlenecks:
                        bottleneck_suggestions = self.bottleneck_agent.generate_bottleneck_suggestions(project_id, bottlenecks, self.llm_manager)
                        if bottleneck_suggestions['success']:
                            suggestions['bottleneck_suggestions'] = bottleneck_suggestions['suggestions']
                            print(f"   ✅ Generated {len(bottleneck_suggestions['suggestions'])} bottleneck suggestions")
                    
                    # Store suggestions
                    if any(suggestions.values()):
                        self.store_suggestions(project_id, suggestions)
                        print("   💾 Suggestions stored successfully")
                        
                except Exception as e:
                    print(f"   ⚠️  Error generating suggestions: {e}")
                    import traceback
                    print(f"   Traceback: {traceback.format_exc()}")
                
                # Update timestamp
                self._update_last_performance_update(project_id)
            
            # Get updated data
            updated_data = self._get_current_performance_data(project_id)
            updated_data['new_documents_processed'] = successful_updates
            updated_data['failed_documents'] = failed_documents
            updated_data['total_new_documents'] = len(new_documents)
            
            print(f"\n{'='*80}")
            print(f"✅ IMMEDIATE UPDATE COMPLETE")
            print(f"   Processed: {successful_updates}/{len(new_documents)} documents")
            if failed_documents:
                print(f"   Failed: {', '.join(failed_documents)}")
            print(f"{'='*80}\n")
            
            return updated_data
            
        except Exception as e:
            print(f"❌ Error in immediate performance update: {e}")
            return {
                'success': False,
                'error': f"Immediate update failed: {str(e)}",
                'project_id': project_id,
                'new_documents_processed': 0
            }
    
    def _get_current_performance_data(self, project_id: str) -> Dict[str, Any]:
        """Get current performance data from database without processing"""
        try:
            # Get all current data from ChromaDB
            milestones = self.milestone_agent.get_project_milestones(project_id)
            tasks = self.task_agent.get_project_tasks(project_id)
            bottlenecks = self.bottleneck_agent.get_project_bottlenecks(project_id)
            
            # Get details counts
            milestone_details = self.get_milestone_details_for_project(project_id)
            task_details = self.get_task_details_for_project(project_id)
            bottleneck_details = self.get_bottleneck_details_for_project(project_id)
            requirements = self.chroma_manager.get_performance_data('requirements', project_id)
            actors = self.chroma_manager.get_performance_data('actors', project_id)
            
            # Debug logging
            print(f"📋 Requirements retrieved: {len(requirements)} items")
            if requirements:
                print(f"   Sample requirement structure: {requirements[0] if requirements else 'None'}")
            print(f"👥 Actors retrieved: {len(actors)} items")
            if actors:
                print(f"   Sample actor structure: {actors[0] if actors else 'None'}")
            
            # Count total details
            milestones_details_count = sum(len(details) for details in milestone_details.values())
            tasks_details_count = sum(len(details) for details in task_details.values())
            bottlenecks_details_count = sum(len(details) for details in bottleneck_details.values())
            
            # Calculate completion score based on task completion statuses
            # ONLY count tasks that have undergone completion analysis
            completion_score = 0.0
            analyzed_tasks_count = 0
            completed_count = 0
            
            if tasks:
                for task in tasks:
                    # Check if task has completion analysis
                    final_status = task.get('final_completion_status')
                    completion_status = task.get('completion_status')
                    
                    # Only count tasks that have been analyzed (not default 0 values)
                    if final_status is not None and final_status != 0:
                        analyzed_tasks_count += 1
                        completed_count += final_status
                    elif completion_status is not None and completion_status != 0:
                        analyzed_tasks_count += 1
                        completed_count += completion_status
                    elif 'final_completion_status' in task or 'completion_status' in task:
                        # Task was analyzed but marked as incomplete (status = 0)
                        analyzed_tasks_count += 1
                
                # Calculate completion score only if tasks have been analyzed
                if analyzed_tasks_count > 0:
                    completion_score = (completed_count / analyzed_tasks_count) * 100
                else:
                    completion_score = 0.0  # No completion analysis done yet
            
            print(f"📊 Completion Score Calculation: {completed_count}/{analyzed_tasks_count} analyzed tasks = {completion_score}%")
            
            # Check if tasks have completion analysis
            tasks_completion_analysis = any(
                'completion_status' in task or task.get('status') == 'Completed' 
                for task in tasks
            )
            
            # Format response matching the endpoint expectations
            response = {
                'success': True,
                'project_id': project_id,
                'milestones': {
                    'count': len(milestones),
                    'details_count': milestones_details_count
                },
                'tasks': {
                    'count': len(tasks),
                    'details_count': tasks_details_count,
                    'completion_analysis': tasks_completion_analysis
                },
                'requirements': {
                    'count': len(requirements),
                    'requirements': requirements
                },
                'actors': {
                    'count': len(actors),
                    'actors': actors
                },
                'bottlenecks': {
                    'count': len(bottlenecks),
                    'details_count': bottlenecks_details_count
                },
                'completion_score': completion_score,
                'last_analysis': datetime.now().isoformat(),
                'overall_success': True
            }
            
            return response
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Error getting current performance data: {str(e)}",
                'project_id': project_id,
                'milestones': {'count': 0, 'details_count': 0},
                'tasks': {'count': 0, 'details_count': 0, 'completion_analysis': False},
                'bottlenecks': {'count': 0, 'details_count': 0},
                'completion_score': 0.0,
                'last_analysis': None,
                'overall_success': False
            }
    
    def refresh_performance_data(self, project_id: str) -> Dict[str, Any]:
        """
        Refresh performance data - processes new documents then returns updated metrics
        This runs the full 12-hour update logic immediately on demand
        """
        return self.immediate_update_performance(project_id)
    
    def update_performance_metrics_for_new_document(self, project_id: str, new_document_id: str) -> bool:
        """
        Update performance metrics when a new document is added to an existing project
        
        Args:
            project_id (str): Project identifier
            new_document_id (str): New document identifier
            
        Returns:
            bool: True if all processing succeeded, False otherwise
        """
        results = {
            'project_id': project_id,
            'new_document_id': new_document_id,
            'timestamp': datetime.now().isoformat(),
            'updates': {},
            'success': True
        }
        
        try:
            # Track success of each component
            milestone_success = False
            task_success = False
            bottleneck_success = False
            
            # Extract new milestones from new document
            new_milestone_result = self.milestone_agent.extract_milestones_from_document(
                project_id, new_document_id, self.llm_manager
            )
            
            if new_milestone_result['success']:
                results['updates']['milestones'] = {
                    'new_count': new_milestone_result.get('milestones_count', 0),
                    'success': True
                }
                milestone_success = True
                
                # Update existing milestones with new context
                self._update_existing_milestones_with_new_document(project_id, new_document_id)
            else:
                results['updates']['milestones'] = {
                    'success': False,
                    'error': new_milestone_result.get('error', 'Unknown error')
                }
                results['success'] = False
            
            # Extract new tasks from new document
            new_task_result = self.task_agent.extract_tasks_from_document(
                project_id, new_document_id, self.llm_manager
            )
            
            if new_task_result['success']:
                results['updates']['tasks'] = {
                    'new_count': new_task_result.get('tasks_count', 0),
                    'success': True
                }
                task_success = True
                
                # Update existing tasks with new context
                self._update_existing_tasks_with_new_document(project_id, new_document_id)
            else:
                results['updates']['tasks'] = {
                    'success': False,
                    'error': new_task_result.get('error', 'Unknown error')
                }
                results['success'] = False
            
            # Extract new bottlenecks from new document
            new_bottleneck_result = self.bottleneck_agent.extract_bottlenecks_from_document(
                project_id, new_document_id, self.llm_manager
            )
            
            if new_bottleneck_result['success']:
                results['updates']['bottlenecks'] = {
                    'new_count': new_bottleneck_result.get('bottlenecks_count', 0),
                    'success': True
                }
                bottleneck_success = True
                
                # Update existing bottlenecks with new context
                self._update_existing_bottlenecks_with_new_document(project_id, new_document_id)
            else:
                results['updates']['bottlenecks'] = {
                    'success': False,
                    'error': new_bottleneck_result.get('error', 'Unknown error')
                }
                results['success'] = False
            
            # Extract requirements from new document
            try:
                requirements_result = self.requirements_agent.extract_requirements_from_document(
                    project_id, new_document_id, self.llm_manager
                )
                if requirements_result['success']:
                    results['updates']['requirements'] = {
                        'new_count': requirements_result.get('requirements_count', 0),
                        'success': True
                    }
                    print(f"   ✅ Extracted {requirements_result.get('requirements_count', 0)} requirements")
                else:
                    results['updates']['requirements'] = {
                        'success': False,
                        'error': requirements_result.get('error', 'Unknown error')
                    }
                    print(f"   ⚠️  Requirements extraction failed: {requirements_result.get('error', 'Unknown')}")
            except Exception as e:
                print(f"   ⚠️  Error extracting requirements: {e}")
                results['updates']['requirements'] = {'success': False, 'error': str(e)}
            
            # Extract actors from new document
            try:
                actors_result = self.actors_agent.extract_actors_from_document(
                    project_id, new_document_id, self.llm_manager
                )
                if actors_result['success']:
                    results['updates']['actors'] = {
                        'new_count': actors_result.get('actors_count', 0),
                        'success': True
                    }
                    print(f"   ✅ Extracted {actors_result.get('actors_count', 0)} actors")
                else:
                    results['updates']['actors'] = {
                        'success': False,
                        'error': actors_result.get('error', 'Unknown error')
                    }
                    print(f"   ⚠️  Actors extraction failed: {actors_result.get('error', 'Unknown')}")
            except Exception as e:
                print(f"   ⚠️  Error extracting actors: {e}")
                results['updates']['actors'] = {'success': False, 'error': str(e)}
            
            # Recalculate task completion statuses
            try:
                self._recalculate_task_completion_statuses(project_id, new_document_id)
            except Exception as e:
                print(f"Error recalculating task completion statuses: {e}")
                results['success'] = False
            
            # Log processing results
            self._log_processing_results(project_id, new_document_id, results)
            
            # Return True only if at least one component succeeded
            return milestone_success or task_success or bottleneck_success
            
        except Exception as e:
            results['error'] = f"Update failed: {str(e)}"
            results['success'] = False
            self._log_processing_error(project_id, new_document_id, str(e))
            return False
    
    def extract_requirements_and_actors_for_project(self, project_id: str) -> Dict[str, Any]:
        """
        Extract requirements and actors from all project documents.
        Useful for re-extracting these entities without running full first-time generation.
        
        Args:
            project_id: Project identifier
            
        Returns:
            Dict with extraction results
        """
        try:
            print(f"\n{'='*80}")
            print(f"🔄 EXTRACTING REQUIREMENTS & ACTORS - Project: {project_id}")
            print(f"{'='*80}\n")
            
            # Get all project documents
            documents = self.db_manager.get_project_documents(project_id)
            if not documents:
                return {
                    'success': False,
                    'error': 'No documents found in project',
                    'project_id': project_id,
                    'requirements_count': 0,
                    'actors_count': 0
                }
            
            print(f"📄 Found {len(documents)} document(s) to process")
            
            total_requirements = 0
            total_actors = 0
            successful_docs = 0
            failed_docs = []
            
            for document in documents:
                doc_id = document['id']
                doc_name = document.get('filename', doc_id[:8])
                print(f"\n{'─'*80}")
                print(f"📄 Processing: {doc_name}")
                print(f"{'─'*80}")
                
                # Verify embeddings exist
                if not self._verify_document_embeddings(project_id, doc_id):
                    print(f"⚠️ Missing embeddings for: {doc_name}")
                    failed_docs.append(doc_name)
                    continue
                
                # Extract requirements
                try:
                    requirements_result = self.requirements_agent.extract_requirements_from_document(
                        project_id, doc_id, self.llm_manager
                    )
                    if requirements_result['success']:
                        req_count = requirements_result.get('requirements_count', 0)
                        total_requirements += req_count
                        print(f"   ✅ Extracted {req_count} requirements")
                    else:
                        print(f"   ⚠️  Requirements extraction failed: {requirements_result.get('error', 'Unknown')}")
                except Exception as e:
                    print(f"   ⚠️  Error extracting requirements: {e}")
                
                # Extract actors
                try:
                    actors_result = self.actors_agent.extract_actors_from_document(
                        project_id, doc_id, self.llm_manager
                    )
                    if actors_result['success']:
                        actor_count = actors_result.get('actors_count', 0)
                        total_actors += actor_count
                        print(f"   ✅ Extracted {actor_count} actors")
                    else:
                        print(f"   ⚠️  Actors extraction failed: {actors_result.get('error', 'Unknown')}")
                except Exception as e:
                    print(f"   ⚠️  Error extracting actors: {e}")
                
                successful_docs += 1
            
            print(f"\n{'='*80}")
            print(f"✅ EXTRACTION COMPLETE")
            print(f"   Processed: {successful_docs}/{len(documents)} documents")
            print(f"   Total Requirements: {total_requirements}")
            print(f"   Total Actors: {total_actors}")
            if failed_docs:
                print(f"   Failed: {', '.join(failed_docs)}")
            print(f"{'='*80}\n")
            
            # Get updated data
            updated_data = self._get_current_performance_data(project_id)
            updated_data['extraction_results'] = {
                'requirements_count': total_requirements,
                'actors_count': total_actors,
                'documents_processed': successful_docs,
                'total_documents': len(documents),
                'failed_documents': failed_docs
            }
            
            return updated_data
            
        except Exception as e:
            print(f"❌ Error extracting requirements and actors: {e}")
            import traceback
            print(f"   Traceback: {traceback.format_exc()}")
            return {
                'success': False,
                'error': f"Extraction failed: {str(e)}",
                'project_id': project_id,
                'requirements_count': 0,
                'actors_count': 0
            }
    
    def _update_existing_milestones_with_new_document(self, project_id: str, new_document_id: str):
        """Update existing milestones with details from new document"""
        try:
            existing_milestones = self.milestone_agent.get_project_milestones(project_id)
            
            for milestone in existing_milestones:
                # Extract details for this milestone from new document
                milestone_details = self.milestone_agent.extract_milestone_details(
                    project_id, milestone['milestone'], self.llm_manager
                )
                
                if milestone_details['success']:
                    # Store milestone details in separate collection
                    self._append_milestone_details(
                        milestone['id'],
                        project_id,
                        new_document_id,
                        milestone_details['details']
                    )
                    
        except Exception as e:
            print(f"Error updating milestone details: {e}")
    
    def _update_existing_tasks_with_new_document(self, project_id: str, new_document_id: str):
        """Update existing tasks with details from new document"""
        try:
            existing_tasks = self.task_agent.get_project_tasks(project_id)
            
            for task in existing_tasks:
                # Extract additional details for this task from new document
                task_details = self.task_agent.extract_task_details(
                    project_id, task['task'], self.llm_manager
                )
                
                if task_details['success']:
                    # Store task details in separate collection
                    self._append_task_details(
                        task['id'],
                        project_id,
                        new_document_id,
                        task_details['details']
                    )
                
                # Check completion status against new document
                completion_result = self.task_agent.determine_task_completion_status(
                    project_id, new_document_id, task['task'], self.llm_manager
                )
                
                if completion_result['success']:
                    # Update task completion status
                    self._update_task_completion_status(task['id'], completion_result['completion_status'])
                    
        except Exception as e:
            print(f"Error updating task details: {e}")
    
    def _update_existing_bottlenecks_with_new_document(self, project_id: str, new_document_id: str):
        """Update existing bottlenecks with details from new document"""
        try:
            existing_bottlenecks = self.bottleneck_agent.get_project_bottlenecks(project_id)
            
            for bottleneck in existing_bottlenecks:
                # Extract additional details for this bottleneck from new document
                bottleneck_details = self.bottleneck_agent.extract_bottleneck_details(
                    project_id, bottleneck['bottleneck'], self.llm_manager
                )
                
                if bottleneck_details['success']:
                    # Store bottleneck details in separate collection
                    self._append_bottleneck_details(
                        bottleneck['id'],
                        project_id,
                        new_document_id,
                        bottleneck_details['details']
                    )
                    
        except Exception as e:
            print(f"Error updating bottleneck details: {e}")
    
    def _recalculate_task_completion_statuses(self, project_id: str, new_document_id: str):
        """Recalculate final task completion statuses based on all documents"""
        try:
            print(f"\n🔄 Recalculating task completion statuses for project {project_id}")
            
            # Get all tasks for the project
            all_tasks = self.task_agent.get_project_tasks(project_id)
            print(f"📋 Found {len(all_tasks)} tasks to analyze")
            
            # Get all documents for the project
            project_documents = self.db_manager.get_project_documents(project_id)
            print(f"📄 Checking against {len(project_documents)} documents")
            
            updated_count = 0
            for i, task in enumerate(all_tasks, 1):
                completion_statuses = []
                task_name = task.get('task', 'Unknown')[:50]
                print(f"\n   Task {i}/{len(all_tasks)}: {task_name}...")
                
                # Check completion status against each document
                for document in project_documents:
                    completion_result = self.task_agent.determine_task_completion_status(
                        project_id, document['id'], task['task'], self.llm_manager
                    )
                    
                    if completion_result['success']:
                        completion_statuses.append(completion_result['completion_status'])
                
                # Calculate final completion status (50% threshold)
                if completion_statuses:
                    completion_percentage = sum(completion_statuses) / len(completion_statuses)
                    final_status = 1 if completion_percentage >= 0.5 else 0
                    
                    print(f"      Completion: {completion_percentage:.2%} (final_status: {final_status})")
                    
                    # Update task with final status
                    self._update_task_final_completion_status(task['id'], final_status, completion_percentage)
                    updated_count += 1
                else:
                    print(f"      ⚠️ No completion status calculated")
            
            print(f"\n✅ Updated {updated_count}/{len(all_tasks)} tasks with completion status\n")
                    
        except Exception as e:
            print(f"❌ Error recalculating task completion statuses: {e}")
    
    def _append_milestone_details(self, milestone_id: str, project_id: str, 
                                  document_id: str, new_details: str):
        """Store milestone details in separate collection (no longer appending to metadata)"""
        try:
            # Store details in separate collection - details go to document field, not metadata
            detail_id = self.chroma_manager.store_details(
                detail_type='milestone_details',
                parent_id=milestone_id,
                project_id=project_id,
                document_id=document_id,
                details_text=new_details,
                metadata={'milestone_id': milestone_id}
            )
            
            if detail_id:
                print(f"✅ Stored milestone details: {detail_id}")
                # Update milestone metadata with last_updated timestamp only
                self.chroma_manager.update_performance_data(
                    'milestones', 
                    milestone_id, 
                    {'last_detail_update': datetime.now().isoformat()}
                )
            else:
                print(f"❌ Failed to store milestone details for {milestone_id}")
                        
        except Exception as e:
            print(f"Error storing milestone details: {e}")
    
    def _append_bottleneck_details(self, bottleneck_id: str, project_id: str,
                                   document_id: str, new_details: str):
        """Store bottleneck details in separate collection (no longer appending to metadata)"""
        try:
            # Store details in separate collection - details go to document field, not metadata
            detail_id = self.chroma_manager.store_details(
                detail_type='bottleneck_details',
                parent_id=bottleneck_id,
                project_id=project_id,
                document_id=document_id,
                details_text=new_details,
                metadata={'bottleneck_id': bottleneck_id}
            )
            
            if detail_id:
                print(f"✅ Stored bottleneck details: {detail_id}")
                # Update bottleneck metadata with last_updated timestamp only
                self.chroma_manager.update_performance_data(
                    'bottlenecks', 
                    bottleneck_id, 
                    {'last_detail_update': datetime.now().isoformat()}
                )
            else:
                print(f"❌ Failed to store bottleneck details for {bottleneck_id}")
                        
        except Exception as e:
            print(f"Error storing bottleneck details: {e}")
    
    def _update_task_completion_status(self, task_id: str, completion_status: int):
        """Update task completion status"""
        try:
            # Get the task from ChromaDB
            task_data = self.chroma_manager.get_performance_data('tasks', task_id.split('_')[1])  # Extract project_id
            
            if task_data:
                # Find the specific task
                for task in task_data:
                    if task['id'] == task_id:
                        # Update metadata with completion status
                        self.chroma_manager.update_performance_data(
                            'tasks', 
                            task_id, 
                            {
                                'completion_status': completion_status, 
                                'status_updated_at': datetime.now().isoformat()
                            }
                        )
                        break
                        
        except Exception as e:
            print(f"Error updating task completion status: {e}")
    
    def _append_task_details(self, task_id: str, project_id: str,
                            document_id: str, new_details: str):
        """Store task details in separate collection (no longer appending to metadata)"""
        try:
            # Store details in separate collection - details go to document field, not metadata
            detail_id = self.chroma_manager.store_details(
                detail_type='task_details',
                parent_id=task_id,
                project_id=project_id,
                document_id=document_id,
                details_text=new_details,
                metadata={'task_id': task_id}
            )
            
            if detail_id:
                print(f"✅ Stored task details: {detail_id}")
                # Update task metadata with last_updated timestamp only
                self.chroma_manager.update_performance_data(
                    'tasks', 
                    task_id, 
                    {'last_detail_update': datetime.now().isoformat()}
                )
            else:
                print(f"❌ Failed to store task details for {task_id}")
                        
        except Exception as e:
            print(f"Error storing task details: {e}")
    
    def _update_task_final_completion_status(self, task_id: str, final_status: int, completion_percentage: float):
        """Update task final completion status"""
        try:
            print(f"📝 Updating task {task_id} completion: final_status={final_status}, percentage={completion_percentage:.2%}")
            
            # Update metadata directly
            success = self.chroma_manager.update_performance_data(
                'tasks', 
                task_id, 
                {
                    'final_completion_status': final_status,
                    'completion_percentage': completion_percentage,
                    'final_status_updated_at': datetime.now().isoformat()
                }
            )
            
            if success:
                print(f"✅ Updated task {task_id} completion status")
            else:
                print(f"❌ Failed to update task {task_id} completion status")
                        
        except Exception as e:
            print(f"❌ Error updating task final completion status: {e}")
    
    def store_suggestions(self, project_id: str, suggestions: Dict[str, Any]) -> bool:
        """Store suggestions for milestones, tasks, and bottlenecks"""
        try:
            # Store milestone suggestions
            if 'milestone_suggestions' in suggestions:
                self._store_milestone_suggestions(project_id, suggestions['milestone_suggestions'])
            
            # Store task suggestions
            if 'task_suggestions' in suggestions:
                self._store_task_suggestions(project_id, suggestions['task_suggestions'])
            
            # Store bottleneck suggestions
            if 'bottleneck_suggestions' in suggestions:
                self._store_bottleneck_suggestions(project_id, suggestions['bottleneck_suggestions'])
            
            return True
            
        except Exception as e:
            print(f"Error storing suggestions: {e}")
            return False
    
    def _store_milestone_suggestions(self, project_id: str, suggestions: List[Dict]):
        """Store milestone suggestions"""
        try:
            data = []
            for suggestion in suggestions:
                data.append({
                    'text': suggestion.get('suggestion', ''),
                    'metadata': {
                        'type': 'milestone_suggestion',
                        'priority': suggestion.get('priority', 'Medium'),
                        'category': suggestion.get('category', 'General'),
                        'source': suggestion.get('source', 'AI Analysis')
                    }
                })
            
            self.chroma_manager.store_performance_data('milestones', data, project_id, 'suggestions')
            
        except Exception as e:
            print(f"Error storing milestone suggestions: {e}")
    
    def _store_task_suggestions(self, project_id: str, suggestions: List[Dict]):
        """Store task suggestions"""
        try:
            data = []
            for suggestion in suggestions:
                data.append({
                    'text': suggestion.get('suggestion', ''),
                    'metadata': {
                        'type': 'task_suggestion',
                        'priority': suggestion.get('priority', 'Medium'),
                        'category': suggestion.get('category', 'General'),
                        'source': suggestion.get('source', 'AI Analysis')
                    }
                })
            
            self.chroma_manager.store_performance_data('tasks', data, project_id, 'suggestions')
            
        except Exception as e:
            print(f"Error storing task suggestions: {e}")
    
    def _store_bottleneck_suggestions(self, project_id: str, suggestions: List[Dict]):
        """Store bottleneck suggestions"""
        try:
            data = []
            for suggestion in suggestions:
                data.append({
                    'text': suggestion.get('suggestion', ''),
                    'metadata': {
                        'type': 'bottleneck_suggestion',
                        'priority': suggestion.get('priority', 'Medium'),
                        'category': suggestion.get('category', 'General'),
                        'source': suggestion.get('source', 'AI Analysis')
                    }
                })
            
            self.chroma_manager.store_performance_data('bottlenecks', data, project_id, 'suggestions')
            
        except Exception as e:
            print(f"Error storing bottleneck suggestions: {e}")
    
    def _format_suggestion_for_ui(self, item: Dict) -> Dict:
        """
        Format suggestion data for UI display
        Transforms ChromaDB data structure to match UI expectations
        """
        return {
            'id': item.get('id', ''),
            'text': item.get('content', ''),  # ChromaDB stores text in 'content' field
            'suggestion': item.get('content', ''),  # Also provide as 'suggestion' for backward compatibility
            'priority': item.get('metadata', {}).get('priority', 'Medium'),
            'category': item.get('metadata', {}).get('category', 'General'),
            'source': item.get('metadata', {}).get('source', 'AI Analysis'),
            'type': item.get('metadata', {}).get('type', ''),
            'metadata': item.get('metadata', {})
        }
    
    def get_suggestions(self, project_id: str, suggestion_type: str = None) -> Dict[str, List[Dict]]:
        """Get suggestions for a project"""
        try:
            suggestions = {
                'milestone_suggestions': [],
                'task_suggestions': [],
                'bottleneck_suggestions': []
            }
            
            if suggestion_type is None or suggestion_type == 'milestones':
                milestone_data = self.chroma_manager.get_performance_data('milestones', project_id)
                suggestions['milestone_suggestions'] = [
                    self._format_suggestion_for_ui(item)
                    for item in milestone_data 
                    if item.get('metadata', {}).get('type') == 'milestone_suggestion'
                ]
            
            if suggestion_type is None or suggestion_type == 'tasks':
                task_data = self.chroma_manager.get_performance_data('tasks', project_id)
                suggestions['task_suggestions'] = [
                    self._format_suggestion_for_ui(item)
                    for item in task_data 
                    if item.get('metadata', {}).get('type') == 'task_suggestion'
                ]
            
            if suggestion_type is None or suggestion_type == 'bottlenecks':
                bottleneck_data = self.chroma_manager.get_performance_data('bottlenecks', project_id)
                suggestions['bottleneck_suggestions'] = [
                    self._format_suggestion_for_ui(item)
                    for item in bottleneck_data 
                    if item.get('metadata', {}).get('type') == 'bottleneck_suggestion'
                ]
            
            return suggestions
            
        except Exception as e:
            print(f"Error getting suggestions: {e}")
            return {'milestone_suggestions': [], 'task_suggestions': [], 'bottleneck_suggestions': []}
    
    def schedule_performance_updates(self):
        """
        Scheduled function to update performance metrics every 12 hours
        This should be called by a scheduler (e.g., APScheduler)
        """
        try:
            # Get all projects
            all_projects = self.db_manager.get_all_projects()
            
            for project in all_projects:
                project_id = project['id']
                
                # Get project documents
                documents = self.db_manager.get_project_documents(project_id)
                
                if not documents:
                    continue
                
                # Check if there are new documents since last update
                last_update = self._get_last_performance_update(project_id)
                
                # Find new documents
                new_documents = []
                if last_update:
                    for document in documents:
                        if document['created_at'] > last_update:
                            new_documents.append(document)
                else:
                    # First time update for this project
                    new_documents = documents
                
                # Process new documents with embedding verification
                successful_updates = 0
                for document in new_documents:
                    # Verify embeddings exist before processing
                    if self._verify_document_embeddings(project_id, document['id']):
                        success = self.update_performance_metrics_for_new_document(project_id, document['id'])
                        if success:
                            successful_updates += 1
                        else:
                            # Queue for retry if processing failed
                            self._queue_for_retry(project_id, document['id'])
                    else:
                        # Log missing embeddings
                        self._log_missing_embeddings(project_id, document['id'])
                
                # Only update timestamp if at least one document was successfully processed
                if successful_updates > 0:
                    self._update_last_performance_update(project_id)
                
                # Retry failed documents
                self._retry_failed_documents(project_id)
                
        except Exception as e:
            print(f"Error in scheduled performance updates: {e}")
            self._log_scheduling_error(str(e))
    
    def _get_last_performance_update(self, project_id: str) -> Optional[str]:
        """Get last performance update timestamp for a project"""
        try:
            update_file = os.path.join(self.performance_data_dir, f"{project_id}_last_update.json")
            
            if os.path.exists(update_file):
                with open(update_file, 'r') as f:
                    data = json.load(f)
                    return data.get('last_update')
            
            return None
            
        except Exception as e:
            print(f"Error getting last update timestamp: {e}")
            return None
    
    def _update_last_performance_update(self, project_id: str):
        """Update last performance update timestamp for a project"""
        try:
            update_file = os.path.join(self.performance_data_dir, f"{project_id}_last_update.json")
            
            data = {
                'project_id': project_id,
                'last_update': datetime.now().isoformat()
            }
            
            with open(update_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            print(f"Error updating last update timestamp: {e}")
    
    def _verify_document_embeddings(self, project_id: str, document_id: str) -> bool:
        """Verify that document has embeddings before processing"""
        try:
            # Check if embeddings exist in ChromaDB
            if hasattr(self, 'chroma_manager'):
                embeddings = self.chroma_manager.get_document_embeddings(project_id, document_id)
            else:
                # Fallback to individual agent check
                embeddings = self.milestone_agent._get_document_embeddings(project_id, document_id)
            
            return len(embeddings) > 0
            
        except Exception as e:
            print(f"Error verifying document embeddings: {e}")
            return False
    
    def _log_missing_embeddings(self, project_id: str, document_id: str):
        """Log documents with missing embeddings"""
        try:
            log_file = os.path.join(self.performance_data_dir, f"{project_id}_missing_embeddings.json")
            
            # Load existing log
            missing_docs = []
            if os.path.exists(log_file):
                with open(log_file, 'r') as f:
                    missing_docs = json.load(f)
            
            # Add new missing document
            missing_docs.append({
                'project_id': project_id,
                'document_id': document_id,
                'missing_at': datetime.now().isoformat(),
                'status': 'pending'
            })
            
            # Save updated log
            with open(log_file, 'w') as f:
                json.dump(missing_docs, f, indent=2)
                
        except Exception as e:
            print(f"Error logging missing embeddings: {e}")
    
    def _queue_for_retry(self, project_id: str, document_id: str):
        """Queue document for retry processing"""
        try:
            retry_file = os.path.join(self.performance_data_dir, f"{project_id}_retry_queue.json")
            
            # Load existing retry queue
            retry_queue = []
            if os.path.exists(retry_file):
                with open(retry_file, 'r') as f:
                    retry_queue = json.load(f)
            
            # Add document to retry queue
            retry_queue.append({
                'project_id': project_id,
                'document_id': document_id,
                'failed_at': datetime.now().isoformat(),
                'retry_count': 0,
                'status': 'pending'
            })
            
            # Save updated queue
            with open(retry_file, 'w') as f:
                json.dump(retry_queue, f, indent=2)
                
        except Exception as e:
            print(f"Error queuing document for retry: {e}")
    
    def _retry_failed_documents(self, project_id: str):
        """Retry processing for documents that failed previously"""
        try:
            retry_file = os.path.join(self.performance_data_dir, f"{project_id}_retry_queue.json")
            
            if not os.path.exists(retry_file):
                return
            
            # Load retry queue
            with open(retry_file, 'r') as f:
                retry_queue = json.load(f)
            
            # Process pending retries
            updated_queue = []
            for item in retry_queue:
                if item['status'] == 'pending' and item['retry_count'] < 3:
                    # Verify embeddings still exist
                    if self._verify_document_embeddings(project_id, item['document_id']):
                        success = self.update_performance_metrics_for_new_document(project_id, item['document_id'])
                        if success:
                            item['status'] = 'completed'
                            item['completed_at'] = datetime.now().isoformat()
                        else:
                            item['retry_count'] += 1
                            item['last_retry'] = datetime.now().isoformat()
                    else:
                        item['status'] = 'no_embeddings'
                        item['error'] = 'Embeddings not found'
                
                updated_queue.append(item)
            
            # Save updated queue
            with open(retry_file, 'w') as f:
                json.dump(updated_queue, f, indent=2)
                
        except Exception as e:
            print(f"Error retrying failed documents: {e}")
    
    def _log_scheduling_error(self, error_message: str):
        """Log scheduling errors"""
        try:
            error_file = os.path.join(self.performance_data_dir, "scheduling_errors.json")
            
            # Load existing errors
            errors = []
            if os.path.exists(error_file):
                with open(error_file, 'r') as f:
                    errors = json.load(f)
            
            # Add new error
            errors.append({
                'error': error_message,
                'timestamp': datetime.now().isoformat()
            })
            
            # Save updated errors
            with open(error_file, 'w') as f:
                json.dump(errors, f, indent=2)
                
        except Exception as e:
            print(f"Error logging scheduling error: {e}")
    
    def _log_processing_results(self, project_id: str, document_id: str, results: Dict[str, Any]):
        """Log processing results for monitoring"""
        try:
            log_file = os.path.join(self.performance_data_dir, f"{project_id}_processing_log.json")
            
            # Load existing log
            processing_log = []
            if os.path.exists(log_file):
                with open(log_file, 'r') as f:
                    processing_log = json.load(f)
            
            # Add new processing result
            processing_log.append({
                'project_id': project_id,
                'document_id': document_id,
                'timestamp': datetime.now().isoformat(),
                'success': results.get('success', False),
                'milestone_success': results.get('updates', {}).get('milestones', {}).get('success', False),
                'task_success': results.get('updates', {}).get('tasks', {}).get('success', False),
                'bottleneck_success': results.get('updates', {}).get('bottlenecks', {}).get('success', False),
                'milestone_count': results.get('updates', {}).get('milestones', {}).get('new_count', 0),
                'task_count': results.get('updates', {}).get('tasks', {}).get('new_count', 0),
                'bottleneck_count': results.get('updates', {}).get('bottlenecks', {}).get('new_count', 0),
                'error': results.get('error', None)
            })
            
            # Save updated log
            with open(log_file, 'w') as f:
                json.dump(processing_log, f, indent=2)
                
        except Exception as e:
            print(f"Error logging processing results: {e}")
    
    def _log_processing_error(self, project_id: str, document_id: str, error_message: str):
        """Log processing errors for debugging"""
        try:
            error_file = os.path.join(self.performance_data_dir, f"{project_id}_processing_errors.json")
            
            # Load existing errors
            errors = []
            if os.path.exists(error_file):
                with open(error_file, 'r') as f:
                    errors = json.load(f)
            
            # Add new error
            errors.append({
                'project_id': project_id,
                'document_id': document_id,
                'error': error_message,
                'timestamp': datetime.now().isoformat()
            })
            
            # Save updated errors
            with open(error_file, 'w') as f:
                json.dump(errors, f, indent=2)
                
        except Exception as e:
            print(f"Error logging processing error: {e}")
    
    def get_performance_analytics(self, project_id: str) -> Dict[str, Any]:
        """
        Get comprehensive performance analytics for a project
        NOTE: This is kept for test compatibility. Use refresh_performance_data() for API calls.
        """
        try:
            # Get basic performance summary
            summary = self.get_project_performance_summary(project_id)
            
            if 'error' in summary:
                return summary
            
            # Calculate additional analytics
            analytics = {
                'project_id': project_id,
                'milestones_count': summary['milestones_count'],
                'tasks_count': summary['tasks_count'],
                'bottlenecks_count': summary['bottlenecks_count'],
                'milestones': summary['milestones'],
                'tasks': summary['tasks'],
                'bottlenecks': summary['bottlenecks'],
                'analytics': {
                    'milestone_categories': self._analyze_milestone_categories(summary['milestones']),
                    'task_priorities': self._analyze_task_priorities(summary['tasks']),
                    'bottleneck_severities': self._analyze_bottleneck_severities(summary['bottlenecks']),
                    'completion_rates': self._calculate_completion_rates(summary['tasks'])
                },
                'last_updated': summary['last_updated']
            }
            
            return analytics
            
        except Exception as e:
            return {
                'error': f"Error getting performance analytics: {str(e)}",
                'project_id': project_id
            }
    
    def _analyze_milestone_categories(self, milestones: List[Dict]) -> Dict[str, int]:
        """Analyze milestone categories distribution"""
        categories = {}
        for milestone in milestones:
            category = milestone.get('category', 'General')
            categories[category] = categories.get(category, 0) + 1
        return categories
    
    def _analyze_task_priorities(self, tasks: List[Dict]) -> Dict[str, int]:
        """Analyze task priorities distribution"""
        priorities = {}
        for task in tasks:
            priority = task.get('priority', 'Medium')
            priorities[priority] = priorities.get(priority, 0) + 1
        return priorities
    
    def _analyze_bottleneck_severities(self, bottlenecks: List[Dict]) -> Dict[str, int]:
        """Analyze bottleneck severities distribution"""
        severities = {}
        for bottleneck in bottlenecks:
            severity = bottleneck.get('severity', 'Medium')
            severities[severity] = severities.get(severity, 0) + 1
        return severities
    
    def _calculate_completion_rates(self, tasks: List[Dict]) -> Dict[str, float]:
        """Calculate task completion rates by category"""
        completion_rates = {}
        categories = {}
        
        for task in tasks:
            category = task.get('category', 'General')
            status = task.get('status', 'Not Started')
            
            if category not in categories:
                categories[category] = {'total': 0, 'completed': 0}
            
            categories[category]['total'] += 1
            if status == 'Completed':
                categories[category]['completed'] += 1
        
        for category, data in categories.items():
            if data['total'] > 0:
                completion_rates[category] = data['completed'] / data['total']
            else:
                completion_rates[category] = 0.0
        
        return completion_rates
    
    def get_milestone_details_for_project(self, project_id: str) -> Dict[str, List[Dict]]:
        """Get all milestone details for a project, grouped by parent milestone"""
        try:
            details = self.chroma_manager.get_details_by_project('milestone_details', project_id)
            
            # Group by parent_id
            grouped_details = {}
            for detail in details:
                parent_id = detail.get('parent_id', 'unknown')
                if parent_id not in grouped_details:
                    grouped_details[parent_id] = []
                grouped_details[parent_id].append({
                    'detail_id': detail['id'],
                    'details_text': detail['details_text'],
                    'document_id': detail['metadata'].get('document_id', ''),
                    'created_at': detail['metadata'].get('created_at', '')
                })
            
            return grouped_details
            
        except Exception as e:
            print(f"Error getting milestone details for project: {e}")
            return {}
    
    def get_task_details_for_project(self, project_id: str) -> Dict[str, List[Dict]]:
        """Get all task details for a project, grouped by parent task"""
        try:
            details = self.chroma_manager.get_details_by_project('task_details', project_id)
            
            # Group by parent_id
            grouped_details = {}
            for detail in details:
                parent_id = detail.get('parent_id', 'unknown')
                if parent_id not in grouped_details:
                    grouped_details[parent_id] = []
                grouped_details[parent_id].append({
                    'detail_id': detail['id'],
                    'details_text': detail['details_text'],
                    'document_id': detail['metadata'].get('document_id', ''),
                    'created_at': detail['metadata'].get('created_at', '')
                })
            
            return grouped_details
            
        except Exception as e:
            print(f"Error getting task details for project: {e}")
            return {}
    
    def get_bottleneck_details_for_project(self, project_id: str) -> Dict[str, List[Dict]]:
        """Get all bottleneck details for a project, grouped by parent bottleneck"""
        try:
            details = self.chroma_manager.get_details_by_project('bottleneck_details', project_id)
            
            # Group by parent_id
            grouped_details = {}
            for detail in details:
                parent_id = detail.get('parent_id', 'unknown')
                if parent_id not in grouped_details:
                    grouped_details[parent_id] = []
                grouped_details[parent_id].append({
                    'detail_id': detail['id'],
                    'details_text': detail['details_text'],
                    'document_id': detail['metadata'].get('document_id', ''),
                    'created_at': detail['metadata'].get('created_at', '')
                })
            
            return grouped_details
            
        except Exception as e:
            print(f"Error getting bottleneck details for project: {e}")
            return {}
    
    def get_details_for_item(self, item_type: str, item_id: str) -> List[Dict]:
        """
        Get all details for a specific item (milestone/task/bottleneck)
        
        Args:
            item_type: Type of item ('milestone', 'task', 'bottleneck')
            item_id: ID of the item
            
        Returns:
            List of detail entries sorted by date
        """
        try:
            detail_type = f"{item_type}_details"
            details = self.chroma_manager.get_details_by_parent(detail_type, item_id)
            
            return [{
                'detail_id': d['id'],
                'details_text': d['details_text'],
                'document_id': d.get('document_id', ''),
                'created_at': d.get('created_at', '')
            } for d in details]
            
        except Exception as e:
            print(f"Error getting details for item: {e}")
            return []
