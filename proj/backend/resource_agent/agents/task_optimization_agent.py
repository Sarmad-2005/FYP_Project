"""
Task Optimization Agent
Analyzes tasks for priority, complexity, estimated time, creates dependencies, and calculates critical path
"""

import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from backend.performance_agent.chroma_manager import PerformanceChromaManager


class TaskOptimizationAgent:
    """Agent for task optimization, dependency mapping, and critical path calculation"""
    
    def __init__(self, chroma_manager):
        """
        Initialize Task Optimization Agent
        
        Args:
            chroma_manager: ResourceChromaManager instance
        """
        self.chroma_manager = chroma_manager
        # Access to Performance Agent's ChromaDB to retrieve tasks
        self.performance_chroma = PerformanceChromaManager()
    
    def get_all_project_tasks(self, project_id: str) -> List[Dict]:
        """
        Retrieve all tasks for a project from Performance Agent
        
        Args:
            project_id: Project identifier
            
        Returns:
            List of task dictionaries
        """
        try:
            # Get tasks from Performance Agent's collection
            tasks = self.performance_chroma.get_performance_data('tasks', project_id)
            
            # Filter out suggestions (only get actual tasks)
            actual_tasks = [
                task for task in tasks
                if task.get('metadata', {}).get('type') != 'task_suggestion'
            ]
            
            print(f"📋 Retrieved {len(actual_tasks)} tasks from Performance Agent")
            return actual_tasks
            
        except Exception as e:
            print(f"Error retrieving tasks: {e}")
            return []
    
    def analyze_task(self, project_id: str, task_id: str, task_details: Dict, 
                    llm_manager) -> Dict[str, Any]:
        """
        Analyze a single task for priority, complexity, and estimated time
        
        Args:
            project_id: Project identifier
            task_id: Task identifier
            task_details: Task details dictionary
            llm_manager: LLM manager instance
            
        Returns:
            Dictionary with analysis results
        """
        try:
            task_name = task_details.get('task', task_details.get('content', 'Unknown Task'))
            task_metadata = task_details.get('metadata', {})
            
            # Get task details from performance agent if available
            task_details_text = task_details.get('content', task_name)
            
            # Prepare prompt for LLM
            prompt = f"""You are analyzing a project task to determine its priority, complexity, and estimated completion time.

TASK DETAILS:
Task Name: {task_name}
Task Description: {task_details_text}
Category: {task_metadata.get('category', 'General')}
Status: {task_metadata.get('status', 'Not Started')}

ANALYZE THE FOLLOWING:
1. Priority (High/Medium/Low): Consider urgency, impact on project, dependencies, and importance
2. Complexity (Simple/Moderate/Complex/Very Complex): Consider scope, technical difficulty, resources needed, and interdependencies
3. Estimated Time (in hours): Consider complexity, scope, typical completion rates, and similar tasks

OUTPUT FORMAT (JSON only, no additional text):
{{
    "priority": "High|Medium|Low",
    "complexity": "Simple|Moderate|Complex|Very Complex",
    "estimated_time_hours": float,
    "reasoning": "brief explanation for each determination"
}}

Return ONLY valid JSON, no markdown, no code blocks."""

            # Call LLM
            llm_response = llm_manager.simple_chat(prompt)
            
            # Check if LLM call was successful
            if not llm_response.get('success', True):
                return {
                    'success': False,
                    'error': f"LLM call failed: {llm_response.get('error', 'Unknown error')}",
                    'task_id': task_id
                }
            
            # Extract response text from dictionary
            response_text = llm_response.get('response', '')
            
            # Parse JSON response
            try:
                # Clean response (remove markdown if present)
                response_clean = response_text.strip()
                if response_clean.startswith('```json'):
                    response_clean = response_clean[7:]
                if response_clean.startswith('```'):
                    response_clean = response_clean[3:]
                if response_clean.endswith('```'):
                    response_clean = response_clean[:-3]
                response_clean = response_clean.strip()
                
                analysis = json.loads(response_clean)
                
                # Validate analysis
                if 'priority' not in analysis or 'complexity' not in analysis or 'estimated_time_hours' not in analysis:
                    raise ValueError("Missing required fields in analysis")
                
                # Store analysis in ChromaDB
                analysis_data = [{
                    'id': f"task_analysis_{task_id}",
                    'task_id': task_id,
                    'task_name': task_name,
                    'priority': analysis['priority'],
                    'complexity': analysis['complexity'],
                    'estimated_time_hours': float(analysis['estimated_time_hours']),
                    'reasoning': analysis.get('reasoning', ''),
                    'metadata': {
                        'task_id': task_id,
                        'task_name': task_name,
                        'priority': analysis['priority'],
                        'complexity': analysis['complexity'],
                        'estimated_time_hours': float(analysis['estimated_time_hours']),
                        'reasoning': analysis.get('reasoning', ''),
                        'analyzed_at': datetime.now().isoformat()
                    }
                }]
                
                self.chroma_manager.store_resource_data(
                    'tasks_analysis',
                    analysis_data,
                    project_id
                )
                
                return {
                    'success': True,
                    'task_id': task_id,
                    'task_name': task_name,
                    'analysis': analysis
                }
                
            except (json.JSONDecodeError, ValueError) as e:
                print(f"Error parsing LLM response: {e}")
                print(f"Response was: {response_text[:500]}")
                return {
                    'success': False,
                    'error': f"Failed to parse LLM response: {str(e)}",
                    'task_id': task_id
                }
                
        except Exception as e:
            print(f"Error analyzing task {task_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'task_id': task_id
            }
    
    def analyze_all_tasks(self, project_id: str, llm_manager) -> Dict[str, Any]:
        """
        Analyze all tasks for a project one by one
        
        Args:
            project_id: Project identifier
            llm_manager: LLM manager instance
            
        Returns:
            Dictionary with summary of analysis results
        """
        try:
            print(f"\n{'='*80}")
            print(f"🔍 ANALYZING ALL TASKS - Project: {project_id}")
            print(f"{'='*80}\n")
            
            # Get all tasks
            tasks = self.get_all_project_tasks(project_id)
            
            if not tasks:
                return {
                    'success': False,
                    'error': 'No tasks found for project',
                    'tasks_analyzed': 0
                }
            
            print(f"📋 Found {len(tasks)} tasks to analyze\n")
            
            # Analyze each task
            analyzed_count = 0
            failed_count = 0
            results = []
            
            for i, task in enumerate(tasks, 1):
                task_id = task.get('id', f"task_{i}")
                task_name = task.get('content', task.get('task', 'Unknown'))[:50]
                
                print(f"   [{i}/{len(tasks)}] Analyzing: {task_name}...")
                
                result = self.analyze_task(project_id, task_id, task, llm_manager)
                
                if result['success']:
                    analyzed_count += 1
                    print(f"      ✅ Priority: {result['analysis']['priority']}, "
                          f"Complexity: {result['analysis']['complexity']}, "
                          f"Time: {result['analysis']['estimated_time_hours']}h")
                else:
                    failed_count += 1
                    print(f"      ❌ Failed: {result.get('error', 'Unknown error')}")
                
                results.append(result)
            
            print(f"\n{'='*80}")
            print(f"✅ ANALYSIS COMPLETE")
            print(f"   Analyzed: {analyzed_count}/{len(tasks)}")
            if failed_count > 0:
                print(f"   Failed: {failed_count}")
            print(f"{'='*80}\n")
            
            return {
                'success': True,
                'tasks_analyzed': analyzed_count,
                'tasks_failed': failed_count,
                'total_tasks': len(tasks),
                'results': results
            }
            
        except Exception as e:
            print(f"Error in analyze_all_tasks: {e}")
            return {
                'success': False,
                'error': str(e),
                'tasks_analyzed': 0
            }
    
    def create_task_dependencies(self, project_id: str, llm_manager, 
                                batch_size: int = 8) -> Dict[str, Any]:
        """
        Create task dependencies using LLM (batch processing to avoid token limits)
        
        Args:
            project_id: Project identifier
            llm_manager: LLM manager instance
            batch_size: Number of tasks to process per batch
            
        Returns:
            Dictionary with dependency creation results
        """
        try:
            print(f"\n{'='*80}")
            print(f"🔗 CREATING TASK DEPENDENCIES - Project: {project_id}")
            print(f"{'='*80}\n")
            
            # Get all tasks from performance agent
            tasks = self.get_all_project_tasks(project_id)
            
            # Get task analysis (priority, complexity, time)
            task_analysis = self.chroma_manager.get_resource_data('tasks_analysis', project_id)
            
            # Create lookup for task analysis
            analysis_lookup = {ta.get('task_id'): ta for ta in task_analysis}
            
            if not tasks:
                return {
                    'success': False,
                    'error': 'No tasks found for project',
                    'dependencies_created': 0
                }
            
            print(f"📋 Processing {len(tasks)} tasks in batches of {batch_size}\n")
            
            # Process in batches
            dependencies_created = 0
            all_dependencies = []
            
            for batch_start in range(0, len(tasks), batch_size):
                batch = tasks[batch_start:batch_start + batch_size]
                batch_num = (batch_start // batch_size) + 1
                total_batches = (len(tasks) + batch_size - 1) // batch_size
                
                print(f"   Processing batch {batch_num}/{total_batches} ({len(batch)} tasks)...")
                
                # Prepare batch data for LLM (minimal - just IDs, names, and key info)
                batch_data = []
                for task in batch:
                    task_id = task.get('id')
                    task_name = task.get('content', task.get('task', 'Unknown'))
                    analysis = analysis_lookup.get(task_id, {})
                    
                    batch_data.append({
                        'task_id': task_id,
                        'task_name': task_name,
                        'priority': analysis.get('priority', 'Medium'),
                        'complexity': analysis.get('complexity', 'Moderate'),
                        'estimated_time_hours': analysis.get('estimated_time_hours', 0)
                    })
                
                # Create prompt for batch
                prompt = f"""You are analyzing task dependencies for a project. Determine which tasks depend on which other tasks.

TASKS TO ANALYZE:
{json.dumps(batch_data, indent=2)}

For each task, identify:
- Tasks that must be completed BEFORE this task can start (dependencies)
- Consider: logical sequence, prerequisites, data flow, resource requirements

OUTPUT FORMAT (JSON only, no additional text):
[
    {{
        "task_id": "task_id_1",
        "task_name": "Task Name",
        "depends_on": ["task_id_2", "task_id_3"],
        "reasoning": "brief explanation"
    }}
]

Return ONLY valid JSON array, no markdown, no code blocks."""

                # Call LLM
                llm_response = llm_manager.simple_chat(prompt)
                
                # Check if LLM call was successful
                if not llm_response.get('success', True):
                    print(f"      ❌ LLM call failed: {llm_response.get('error', 'Unknown error')}")
                    continue
                
                # Extract response text from dictionary
                response_text = llm_response.get('response', '')
                
                # Parse JSON response
                try:
                    # Clean response
                    response_clean = response_text.strip()
                    if response_clean.startswith('```json'):
                        response_clean = response_clean[7:]
                    if response_clean.startswith('```'):
                        response_clean = response_clean[3:]
                    if response_clean.endswith('```'):
                        response_clean = response_clean[:-3]
                    response_clean = response_clean.strip()
                    
                    batch_dependencies = json.loads(response_clean)
                    
                    if not isinstance(batch_dependencies, list):
                        raise ValueError("Response is not a list")
                    
                    # Store dependencies
                    for dep in batch_dependencies:
                        task_id = dep.get('task_id')
                        task_name = dep.get('task_name', 'Unknown')
                        depends_on = dep.get('depends_on', [])
                        
                        if not task_id:
                            continue
                        
                        # Store in ChromaDB
                        dep_data = [{
                            'id': f"task_dep_{task_id}",
                            'task_id': task_id,
                            'task_name': task_name,
                            'depends_on': depends_on,  # Will be converted to JSON string in store
                            'metadata': {
                                'task_id': task_id,
                                'task_name': task_name,
                                'depends_on': depends_on,
                                'reasoning': dep.get('reasoning', ''),
                                'created_at': datetime.now().isoformat()
                            }
                        }]
                        
                        self.chroma_manager.store_resource_data(
                            'task_dependencies',
                            dep_data,
                            project_id
                        )
                        
                        dependencies_created += 1
                        all_dependencies.append(dep)
                    
                    print(f"      ✅ Created dependencies for {len(batch_dependencies)} tasks")
                    
                except (json.JSONDecodeError, ValueError) as e:
                    print(f"      ❌ Error parsing batch response: {e}")
                    print(f"      Response was: {response_text[:200]}...")
            
            print(f"\n{'='*80}")
            if dependencies_created > 0:
                print(f"✅ DEPENDENCIES CREATED")
                print(f"   Total: {dependencies_created} task dependencies")
            else:
                print(f"⚠️ DEPENDENCIES CREATION")
                print(f"   No dependencies created (may be due to API limits or errors)")
                print(f"   Critical path will be calculated based on task durations only")
            print(f"{'='*80}\n")
            
            return {
                'success': dependencies_created > 0,  # Success only if at least one dependency created
                'dependencies_created': dependencies_created,
                'total_tasks': len(tasks),
                'dependencies': all_dependencies,
                'warning': 'No dependencies created' if dependencies_created == 0 else None
            }
            
        except Exception as e:
            print(f"Error creating task dependencies: {e}")
            return {
                'success': False,
                'error': str(e),
                'dependencies_created': 0
            }
    
    def calculate_critical_path(self, project_id: str) -> Dict[str, Any]:
        """
        Calculate critical path using Critical Path Method (CPM) algorithm
        
        Args:
            project_id: Project identifier
            
        Returns:
            Dictionary with critical path results
        """
        try:
            print(f"\n{'='*80}")
            print(f"📊 CALCULATING CRITICAL PATH - Project: {project_id}")
            print(f"{'='*80}\n")
            
            # Get task dependencies
            dependencies = self.chroma_manager.get_resource_data('task_dependencies', project_id)
            
            # Get task analysis (for estimated times)
            task_analysis = self.chroma_manager.get_resource_data('tasks_analysis', project_id)
            
            # Get all tasks (for task names)
            tasks = self.get_all_project_tasks(project_id)
            
            if not task_analysis:
                return {
                    'success': False,
                    'error': 'No task analysis found. Run task analysis first.',
                    'critical_path': []
                }
            
            # Build dependency graph and time lookup
            task_times = {}
            task_names = {}
            dependency_graph = {}
            
            # Create time lookup from analysis
            for analysis in task_analysis:
                task_id = analysis.get('task_id')
                if task_id:
                    task_times[task_id] = float(analysis.get('estimated_time_hours', 0))
            
            # Create name lookup from tasks
            for task in tasks:
                task_id = task.get('id')
                if task_id:
                    task_names[task_id] = task.get('content', task.get('task', 'Unknown'))
            
            # Build dependency graph from dependencies if available
            if dependencies:
                for dep in dependencies:
                    task_id = dep.get('task_id')
                    depends_on = dep.get('depends_on', [])
                    
                    if isinstance(depends_on, str):
                        # Parse JSON string if needed
                        try:
                            depends_on = json.loads(depends_on)
                        except:
                            depends_on = []
                    
                    if task_id:
                        dependency_graph[task_id] = depends_on if depends_on else []
                        # Ensure task has time estimate (default to 1 hour if missing)
                        if task_id not in task_times:
                            task_times[task_id] = 1.0
            else:
                # No dependencies - treat all tasks as independent (can run in parallel)
                print("   ⚠️ No dependencies found - treating all tasks as independent")
                for task_id in task_times.keys():
                    dependency_graph[task_id] = []
            
            print(f"   Building dependency graph with {len(dependency_graph)} tasks...")
            
            # CPM Algorithm: Forward Pass (Earliest Start/Finish)
            earliest_start = {}
            earliest_finish = {}
            processed = set()
            
            # If no dependencies, all tasks start at time 0 and run in parallel
            if not dependencies:
                # All tasks are independent - they can all start at time 0
                for task_id in task_times.keys():
                    earliest_start[task_id] = 0
                    earliest_finish[task_id] = task_times.get(task_id, 1.0)
                    processed.add(task_id)
            else:
                # Normal CPM with dependencies
                remaining = set(dependency_graph.keys())
                
                while remaining:
                    # Find tasks with no unprocessed dependencies
                    ready_tasks = [
                        task for task in remaining
                        if all(dep in processed for dep in dependency_graph.get(task, []))
                    ]
                    
                    if not ready_tasks:
                        # Circular dependency or missing tasks - process remaining
                        ready_tasks = list(remaining)
                    
                    for task in ready_tasks:
                        # Calculate earliest start (max of all predecessor finish times)
                        if dependency_graph.get(task):
                            earliest_start[task] = max(
                                [earliest_finish.get(dep, 0) for dep in dependency_graph[task]],
                                default=0
                            )
                        else:
                            earliest_start[task] = 0
                        
                        # Calculate earliest finish
                        earliest_finish[task] = earliest_start[task] + task_times.get(task, 1.0)
                        
                        processed.add(task)
                        remaining.remove(task)
            
            # Project duration (if no dependencies, it's the longest task; otherwise max finish time)
            if earliest_finish:
                project_duration = max(earliest_finish.values())
            elif task_times:
                # No dependencies - all tasks can run in parallel, duration is longest task
                project_duration = max(task_times.values())
            else:
                project_duration = 0
            
            # CPM Algorithm: Backward Pass (Latest Start/Finish)
            latest_finish = {}
            latest_start = {}
            
            if not dependencies:
                # No dependencies - all tasks must finish by project duration
                for task_id in processed:
                    latest_finish[task_id] = project_duration
                    latest_start[task_id] = project_duration - task_times.get(task_id, 1.0)
            else:
                # Normal backward pass with dependencies
                reverse_order = list(reversed(list(processed)))
                
                for task in reverse_order:
                    # Find successors (tasks that depend on this task)
                    successors = [
                        t for t in dependency_graph.keys()
                        if task in dependency_graph.get(t, [])
                    ]
                    
                    if successors:
                        latest_finish[task] = min(
                            [latest_start.get(succ, project_duration) for succ in successors],
                            default=project_duration
                        )
                    else:
                        latest_finish[task] = project_duration
                    
                    latest_start[task] = latest_finish[task] - task_times.get(task, 1.0)
            
            # Identify critical path (tasks with zero slack)
            critical_path = []
            task_schedule = {}
            
            # If no dependencies, all tasks are on critical path (longest duration determines project)
            if not dependencies:
                # Find task(s) with longest duration
                max_duration = max(task_times.values()) if task_times else 0
                for task_id, duration in task_times.items():
                    is_critical = (duration == max_duration)
                    task_schedule[task_id] = {
                        'task_name': task_names.get(task_id, task_id),
                        'earliest_start': 0,
                        'latest_start': 0,
                        'earliest_finish': duration,
                        'latest_finish': duration,
                        'slack': 0 if is_critical else (max_duration - duration),
                        'duration': duration,
                        'is_critical': is_critical
                    }
                    if is_critical:
                        critical_path.append(task_id)
            else:
                # Normal CPM calculation with dependencies
                for task in processed:
                    slack = latest_start[task] - earliest_start[task]
                    task_schedule[task] = {
                        'task_name': task_names.get(task, task),
                        'earliest_start': earliest_start[task],
                        'latest_start': latest_start[task],
                        'earliest_finish': earliest_finish[task],
                        'latest_finish': latest_finish[task],
                        'slack': slack,
                        'duration': task_times.get(task, 1.0),
                        'is_critical': slack == 0
                    }
                    
                    if slack == 0:
                        critical_path.append(task)
            
            # Sort critical path by earliest start (or duration if no dependencies)
            if dependencies:
                critical_path.sort(key=lambda t: earliest_start[t])
            else:
                critical_path.sort(key=lambda t: task_times.get(t, 0), reverse=True)
            
            if dependencies:
                print(f"   ✅ Critical path identified: {len(critical_path)} tasks")
            else:
                print(f"   ✅ Critical path identified: {len(critical_path)} longest task(s) (no dependencies - all tasks independent)")
            print(f"   📅 Total project duration: {project_duration:.1f} hours ({project_duration/8:.1f} days)")
            
            # Store critical path (include task_schedule in metadata)
            critical_path_data = [{
                'id': f"critical_path_{project_id}",
                'path_tasks': critical_path,
                'total_duration_hours': project_duration,
                'task_schedule': task_schedule,  # Include task schedule
                'metadata': {
                    'path_tasks': critical_path,
                    'total_duration_hours': project_duration,
                    'task_count': len(critical_path),
                    'task_schedule': task_schedule,  # Store in metadata too
                    'created_at': datetime.now().isoformat()
                }
            }]
            
            self.chroma_manager.store_resource_data(
                'critical_path',
                critical_path_data,
                project_id
            )
            
            print(f"{'='*80}\n")
            
            return {
                'success': True,
                'critical_path': critical_path,
                'total_duration_hours': project_duration,
                'total_duration_days': project_duration / 8,
                'task_schedule': task_schedule,
                'critical_tasks_count': len(critical_path)
            }
            
        except Exception as e:
            print(f"Error calculating critical path: {e}")
            import traceback
            print(traceback.format_exc())
            return {
                'success': False,
                'error': str(e),
                'critical_path': []
            }

