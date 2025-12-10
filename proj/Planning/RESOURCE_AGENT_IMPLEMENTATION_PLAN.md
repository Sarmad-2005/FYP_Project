# Resource Agent/Microservice Implementation Plan

## Overview

The Resource Agent is a LangGraph-based microservice that manages task optimization and resource allocation for projects. It follows the same architectural pattern as the Financial and Performance agents, with worker agents, LangGraph workflows, and a dedicated dashboard.

---

## Architecture Overview

### 1. Main Components

1. **ResourceAgent** (Main Coordinator)
   - Similar structure to `PerformanceAgent` and `FinancialAgent`
   - Manages two worker agents: TaskOptimizationAgent and ResourceOptimizationAgent
   - Uses centralized `ResourceChromaManager` for data storage
   - Supports both monolithic and microservice modes

2. **ResourceChromaManager** (Centralized Storage)
   - Dedicated ChromaDB manager for resource data
   - Collections follow naming convention: `project_resource_*`
   - Manages collections for tasks, task analysis, dependencies, critical path, work teams, and resource assignments

3. **Worker Agents:**
   - **TaskOptimizationAgent**: Task analysis, dependency mapping, critical path calculation
   - **ResourceOptimizationAgent**: Work team management, budget allocation, resource assignment

4. **LangGraph Workflows:**
   - `first_time_generation_graph.py`: Initial resource analysis workflow
   - `refresh_graph.py`: Incremental update workflow
   - Nodes in `nodes/` directory for each workflow step

5. **Resource Service** (`proj/services/resource-service/main.py`)
   - Flask service on port 8004
   - HTTP endpoints for resource operations
   - A2A protocol support
   - Fallback to monolithic mode

---

## Phase 1: Core Infrastructure

### 1.1 Create Resource Agent Structure

**Directory Structure:**
```
proj/backend/resource_agent/
├── __init__.py
├── resource_agent.py          # Main coordinator
├── chroma_manager.py          # Centralized ChromaDB manager
├── agents/
│   ├── __init__.py
│   ├── task_optimization_agent.py
│   └── resource_optimization_agent.py
├── graphs/
│   ├── __init__.py
│   ├── first_time_generation_graph.py
│   └── refresh_graph.py
└── nodes/
    ├── __init__.py
    ├── task_analysis_nodes.py
    ├── dependency_nodes.py
    ├── critical_path_nodes.py
    └── resource_allocation_nodes.py
```

### 1.2 ResourceChromaManager

**File: `proj/backend/resource_agent/chroma_manager.py`**

**Collections:**
- `project_resource_tasks_analysis` - Task priority, complexity, estimated time
- `project_resource_task_dependencies` - Task dependencies (task_id, depends_on: [task_ids])
- `project_resource_critical_path` - Critical path analysis results
- `project_resource_work_teams` - Work teams (people/organizations)
- `project_resource_assignments` - Resource assignments to work teams

**Metadata Structure:**
```python
# Task Analysis
{
    'project_id': str,
    'task_id': str,  # Reference to original task from performance agent
    'task_name': str,
    'priority': str,  # 'High', 'Medium', 'Low'
    'complexity': str,  # 'Simple', 'Moderate', 'Complex', 'Very Complex'
    'estimated_time_hours': float,
    'created_at': str
}

# Task Dependencies
{
    'project_id': str,
    'task_id': str,
    'task_name': str,
    'depends_on': [task_ids],  # List of task IDs this task depends on
    'created_at': str
}

# Critical Path
{
    'project_id': str,
    'path_tasks': [task_ids],  # Ordered list of tasks in critical path
    'total_duration_hours': float,
    'created_at': str
}

# Work Teams
{
    'project_id': str,
    'team_member_id': str,
    'name': str,
    'type': str,  # 'person' or 'organization'
    'assigned_resources': float,  # Amount in PKR
    'created_at': str
}
```

---

## Phase 2: Task Optimization Worker Agent

### 2.1 TaskOptimizationAgent

**File: `proj/backend/resource_agent/agents/task_optimization_agent.py`**

**Functionalities:**

#### 2.1.1 Retrieve All Tasks
- Method: `get_all_project_tasks(project_id: str) -> List[Dict]`
- Retrieves tasks from Performance Agent's `project_tasks` collection
- Uses PerformanceChromaManager to fetch tasks
- Returns list of tasks with their details

#### 2.1.2 Analyze Single Task
- Method: `analyze_task(project_id: str, task_id: str, task_details: Dict, llm_manager) -> Dict`
- For each task:
  - Retrieves task details from performance agent
  - Uses LLM to analyze:
    - **Priority**: High/Medium/Low (based on urgency, impact, dependencies)
    - **Complexity**: Simple/Moderate/Complex/Very Complex (based on scope, technical difficulty, resources needed)
    - **Estimated Time**: Hours/days (based on complexity, scope, historical data)
- Stores analysis in `project_resource_tasks_analysis` collection
- Returns analysis result

**LLM Prompt Strategy:**
```
You are analyzing a project task to determine its priority, complexity, and estimated completion time.

TASK DETAILS:
{task_details}

CONTEXT:
{project_context}

ANALYZE:
1. Priority (High/Medium/Low): Consider urgency, impact on project, dependencies
2. Complexity (Simple/Moderate/Complex/Very Complex): Consider scope, technical difficulty, resources needed
3. Estimated Time (in hours): Consider complexity, scope, typical completion rates

OUTPUT FORMAT (JSON):
{
    "priority": "High|Medium|Low",
    "complexity": "Simple|Moderate|Complex|Very Complex",
    "estimated_time_hours": float,
    "reasoning": "brief explanation"
}
```

#### 2.1.3 Process All Tasks
- Method: `analyze_all_tasks(project_id: str, llm_manager) -> Dict`
- Retrieves all tasks for project
- Processes each task one by one using `analyze_task()`
- Returns summary with counts and success status

#### 2.1.4 Create Task Dependencies
- Method: `create_task_dependencies(project_id: str, llm_manager) -> Dict`
- Retrieves:
  - All tasks from performance agent
  - Task analysis (priority, complexity, estimated_time) from resource agent
  - Task details from performance agent
- Uses LLM to determine dependencies between tasks
- **Strategy**: 
  - Send batches of tasks (5-10 at a time) to LLM to avoid token limits
  - For each task, LLM determines which other tasks it depends on
  - Store only task IDs and dependency relationships (not full task details)
- Stores in `project_resource_task_dependencies` collection

**LLM Prompt Strategy (Batch Processing):**
```
You are analyzing task dependencies for a project. Determine which tasks depend on which other tasks.

TASKS TO ANALYZE:
{current_batch_of_tasks}

For each task, identify:
- Tasks that must be completed BEFORE this task can start
- Tasks that this task BLOCKS (tasks that depend on this one)

OUTPUT FORMAT (JSON):
[
    {
        "task_id": "task_id_1",
        "task_name": "Task Name",
        "depends_on": ["task_id_2", "task_id_3"],  # Tasks this depends on
        "reasoning": "brief explanation"
    }
]
```

**Storage Strategy:**
- Store minimal data: task_id, task_name, depends_on (list of task IDs)
- Avoid storing full task details to save tokens and storage
- Reference original tasks in performance agent collection

#### 2.1.5 Critical Path Method
- Method: `calculate_critical_path(project_id: str) -> Dict`
- Retrieves:
  - Task dependencies
  - Task analysis (estimated_time_hours)
  - Task names
- Implements Critical Path Method (CPM) algorithm:
  1. Build dependency graph
  2. Calculate earliest start/finish times (forward pass)
  3. Calculate latest start/finish times (backward pass)
  4. Identify critical path (tasks with zero slack)
  5. Calculate total project duration
- Stores critical path in `project_resource_critical_path` collection
- Returns critical path with highlighted tasks

**Algorithm:**
```python
def calculate_critical_path(dependencies, task_times):
    # Build graph
    graph = build_dependency_graph(dependencies)
    
    # Forward pass: earliest times
    earliest_start = {}
    earliest_finish = {}
    for task in topological_sort(graph):
        earliest_start[task] = max(
            [earliest_finish.get(dep, 0) for dep in dependencies[task].get('depends_on', [])],
            default=0
        )
        earliest_finish[task] = earliest_start[task] + task_times[task]
    
    # Backward pass: latest times
    latest_finish = {}
    latest_start = {}
    project_duration = max(earliest_finish.values())
    
    for task in reversed(topological_sort(graph)):
        latest_finish[task] = min(
            [latest_start.get(succ, project_duration) for succ in get_successors(task, graph)],
            default=project_duration
        )
        latest_start[task] = latest_finish[task] - task_times[task]
    
    # Identify critical path (zero slack)
    critical_path = [
        task for task in graph
        if latest_start[task] - earliest_start[task] == 0
    ]
    
    return {
        'critical_path': critical_path,
        'total_duration': project_duration,
        'task_schedule': {task: {
            'earliest_start': earliest_start[task],
            'latest_start': latest_start[task],
            'slack': latest_start[task] - earliest_start[task]
        } for task in graph}
    }
```

---

## Phase 3: Resource Optimization Worker Agent

### 3.1 ResourceOptimizationAgent

**File: `proj/backend/resource_agent/agents/resource_optimization_agent.py`**

**Functionalities:**

#### 3.1.1 Manage Work Teams
- Method: `add_work_team_member(project_id: str, name: str, type: str) -> Dict`
  - `type`: 'person' or 'organization'
  - Stores in `project_resource_work_teams` collection
  - Each member is a separate card in UI

- Method: `get_work_team(project_id: str) -> List[Dict]`
  - Retrieves all work team members for project

- Method: `update_work_team_member(team_member_id: str, updates: Dict) -> bool`
  - Updates work team member details
  - Supports manual edits from UI

- Method: `delete_work_team_member(team_member_id: str) -> bool`
  - Removes work team member

#### 3.1.2 Retrieve Financial Data
- Method: `get_project_financial_summary(project_id: str) -> Dict`
- Analyzes data storage to determine:
  - **Total Budget**: From Financial Agent's `project_financial_details` collection (detail_type='budget_allocation')
  - **Total Expenses**: From Financial Agent's `project_transactions` collection (transaction_type='expense')
  - **Total Revenue**: From Financial Agent's `project_transactions` collection (transaction_type='revenue')
- Uses FinancialChromaManager to fetch data
- Returns: `{budget: float, expenses: float, revenue: float}`

#### 3.1.3 AI-Based Resource Assignment
- Method: `assign_resources_ai(project_id: str, llm_manager) -> Dict`
- Retrieves:
  - Work team members
  - Financial summary (budget, expenses, revenue)
  - Task analysis (complexity, priority, estimated_time)
- Sends to LLM for intelligent resource allocation
- LLM assigns budget amounts to each work team member based on:
  - Their role/type (person vs organization)
  - Task complexity and priority
  - Project requirements
- Updates `assigned_resources` field in `project_resource_work_teams` collection
- Returns assignment results

**LLM Prompt Strategy:**
```
You are allocating project resources (budget) to work team members.

FINANCIAL SUMMARY:
- Total Budget: {budget} PKR
- Total Expenses: {expenses} PKR
- Total Revenue: {revenue} PKR
- Available for Allocation: {available} PKR

WORK TEAM:
{work_team_members}

TASK ANALYSIS:
{tasks_with_complexity_and_priority}

ALLOCATE resources to each work team member considering:
- Their role and responsibilities
- Task complexity and priority
- Fair distribution
- Project needs

OUTPUT FORMAT (JSON):
[
    {
        "team_member_id": "id",
        "name": "Name",
        "allocated_amount": float,
        "reasoning": "explanation"
    }
]
```

#### 3.1.4 Manual Resource Editing
- Method: `update_resource_assignment(team_member_id: str, amount: float) -> bool`
- Allows manual editing of resource assignments
- Updates `assigned_resources` field in ChromaDB
- Reflects changes immediately in UI

---

## Phase 4: LangGraph Workflows

### 4.1 First Time Generation Graph

**File: `proj/backend/resource_agent/graphs/first_time_generation_graph.py`**

**State:**
```python
class ResourceGenerationState(TypedDict):
    project_id: str
    document_id: str
    llm_manager: Any
    embeddings_manager: Any
    chroma_manager: Any
    db_manager: Any
    orchestrator: Any
    a2a_router: Any
    
    # Results
    tasks_retrieved: List[Dict]
    task_analysis_result: Dict
    dependencies_result: Dict
    critical_path_result: Dict
    
    overall_success: bool
    error: str
```

**Nodes:**
1. `retrieve_tasks_node` - Get all tasks from performance agent
2. `analyze_tasks_node` - Analyze each task (priority, complexity, time)
3. `create_dependencies_node` - Create task dependencies
4. `calculate_critical_path_node` - Calculate critical path

**Edges:**
- Entry → retrieve_tasks → analyze_tasks → create_dependencies → calculate_critical_path → END

### 4.2 Refresh Graph

**File: `proj/backend/resource_agent/graphs/refresh_graph.py`**

**State:**
```python
class ResourceRefreshState(TypedDict):
    project_id: str
    llm_manager: Any
    chroma_manager: Any
    db_manager: Any
    a2a_router: Any
    
    new_documents: List[Dict]
    last_update: str
    refresh_result: Dict
    success: bool
    error: str
```

**Nodes:**
1. `check_new_documents_node` - Check for new documents
2. `reanalyze_tasks_node` - Re-analyze tasks if new ones added
3. `update_dependencies_node` - Update dependencies
4. `recalculate_critical_path_node` - Recalculate critical path

---

## Phase 5: Resource Service (Microservice)

### 5.1 Service Structure

**File: `proj/services/resource-service/main.py`**

**Endpoints:**
- `GET /health` - Health check
- `POST /first_generation` - First time resource analysis
- `POST /refresh/<project_id>` - Refresh resource data
- `GET /status/<project_id>` - Get resource status
- `GET /tasks/<project_id>` - Get task analysis
- `GET /dependencies/<project_id>` - Get task dependencies
- `GET /critical_path/<project_id>` - Get critical path
- `POST /work_team/<project_id>` - Add work team member
- `GET /work_team/<project_id>` - Get work team
- `PUT /work_team/<team_member_id>` - Update work team member
- `DELETE /work_team/<team_member_id>` - Delete work team member
- `POST /assign_resources/<project_id>` - AI-based resource assignment
- `PUT /resource_assignment/<team_member_id>` - Manual resource edit
- `POST /a2a/message` - A2A protocol handler

**Port:** 8004

**Docker:** Uses existing image (same as other services)

---

## Phase 6: UI Development

### 6.1 Project Details Page Card

**File: `proj/templates/project_details.html`**

Add Resource Agent card (similar to Performance and Financial cards):
```html
<!-- Resource Agent Container -->
<div class="card mb-6" style="animation: slideInUp 0.9s ease-out;">
    <div class="card-header">
        <h3 class="card-title">
            <i class="fas fa-cogs text-orange-500"></i> Resource Agent
        </h3>
        <div class="flex items-center gap-2">
            <span class="badge badge-warning">Task & Resource Optimization</span>
        </div>
    </div>
    
    <div class="resource-agent-container">
        <!-- Metrics Cards -->
        <div class="grid grid-3 mb-6">
            <div class="metric-card">
                <div class="metric-icon">
                    <i class="fas fa-tasks text-blue-500"></i>
                </div>
                <div class="metric-content">
                    <h4 class="metric-title">Tasks Analyzed</h4>
                    <p class="metric-value" id="resource-tasks-count">0</p>
                </div>
            </div>
            
            <div class="metric-card">
                <div class="metric-icon">
                    <i class="fas fa-project-diagram text-purple-500"></i>
                </div>
                <div class="metric-content">
                    <h4 class="metric-title">Dependencies</h4>
                    <p class="metric-value" id="resource-dependencies-count">0</p>
                </div>
            </div>
            
            <div class="metric-card">
                <div class="metric-icon">
                    <i class="fas fa-users text-green-500"></i>
                </div>
                <div class="metric-content">
                    <h4 class="metric-title">Work Team</h4>
                    <p class="metric-value" id="resource-team-count">0</p>
                </div>
            </div>
        </div>
        
        <button onclick="viewResourceDashboard()" class="btn btn-primary btn-lg">
            <i class="fas fa-chart-pie"></i> Open Resource Dashboard
        </button>
    </div>
</div>
```

### 6.2 Resource Dashboard

**File: `proj/templates/resource_dashboard.html`**

**Dashboard Sections:**

#### 6.2.1 Task Analysis Card
- Display all tasks with:
  - Task name
  - Priority (with color coding)
  - Complexity (with badges)
  - Estimated time (hours/days)
- Table or card layout
- Filter/sort options

#### 6.2.2 Dependencies Graph Card
- Interactive graph visualization
- Use library like D3.js, vis.js, or Cytoscape.js
- Nodes: Tasks
- Edges: Dependencies
- Click to view task details
- Beautiful, modern UI

#### 6.2.3 Critical Path Graph Card
- Graph visualization with critical path highlighted
- Critical path tasks in different color (e.g., red/orange)
- Non-critical tasks in gray/blue
- Show task durations
- Show total project duration
- Interactive: hover for details, click for task info

#### 6.2.4 Work Team Management Card
- List of work team members (people/organizations)
- Each member as a card:
  - Name
  - Type (Person/Organization)
  - Assigned Resources (PKR amount)
  - Edit button
- Add new member button
- Delete member button

#### 6.2.5 Resource Assignment Card
- Display financial summary:
  - Total Budget
  - Total Expenses
  - Total Revenue
  - Available for Allocation
- "Assign Resources (AI)" button
- After AI assignment, show allocation results
- Manual edit capability for each team member

**JavaScript File: `proj/static/js/resource-agent.js`**
- Functions for:
  - Loading task analysis
  - Rendering dependencies graph
  - Rendering critical path graph
  - Managing work team
  - Resource assignment
  - API calls to resource service

---

## Phase 7: Integration with Monolith

### 7.1 App.py Routes

**File: `proj/app.py`**

Add routes for resource agent (fallback when microservice unavailable):
```python
# Resource Agent Routes
@app.route('/api/resource/first_generation', methods=['POST'])
def resource_first_generation():
    # Check if microservice is available
    if is_resource_service_available():
        # Forward to microservice
        return forward_to_resource_service('/first_generation', request)
    else:
        # Use monolithic resource agent
        return resource_agent.first_time_generation(...)

# Similar routes for other endpoints
```

### 7.2 Resource Agent Initialization

**File: `proj/app.py`**

```python
from backend.resource_agent.resource_agent import ResourceAgent

# Initialize Resource Agent
resource_agent = ResourceAgent(
    llm_manager=llm_manager,
    embeddings_manager=embeddings_manager,
    db_manager=db_manager,
    orchestrator=orchestrator
)
```

---

## Phase 8: Data Flow

### 8.1 Task Retrieval Flow
1. Resource Agent calls Performance Agent (via A2A or direct)
2. Performance Agent returns tasks from `project_tasks` collection
3. Resource Agent stores task analysis in `project_resource_tasks_analysis`

### 8.2 Dependency Creation Flow
1. Retrieve tasks + analysis from resource collections
2. Retrieve task details from performance agent (minimal, just names/IDs)
3. Batch process with LLM (5-10 tasks per batch)
4. Store dependencies (task_id, depends_on: [task_ids])

### 8.3 Critical Path Flow
1. Retrieve dependencies
2. Retrieve task times from analysis
3. Run CPM algorithm
4. Store critical path
5. Return for visualization

### 8.4 Resource Assignment Flow
1. Retrieve work team from resource collection
2. Retrieve financial data from Financial Agent
3. Send to LLM for allocation
4. Update work team collection with assigned amounts
5. Allow manual edits (update collection directly)

---

## Implementation Order

1. **Phase 1**: Core infrastructure (ResourceAgent, ResourceChromaManager)
2. **Phase 2**: TaskOptimizationAgent (task analysis, dependencies, critical path)
3. **Phase 3**: ResourceOptimizationAgent (work team, resource assignment)
4. **Phase 4**: LangGraph workflows
5. **Phase 5**: Resource Service (microservice)
6. **Phase 6**: UI Development (dashboard, project details card)
7. **Phase 7**: Monolith integration (app.py routes, fallback)

---

## Key Design Decisions

1. **Task Storage**: Reference tasks from Performance Agent, don't duplicate
2. **Dependency Strategy**: Batch processing to avoid token limits, store only IDs
3. **Critical Path**: Algorithm-based (not LLM) for accuracy and performance
4. **Resource Assignment**: LLM-based with manual override capability
5. **Collections**: Follow naming convention `project_resource_*`
6. **Microservice**: Port 8004, uses existing Docker image
7. **Fallback**: Support both monolithic and microservice modes

---

## Testing Checklist

- [ ] Task retrieval from Performance Agent
- [ ] Task analysis (priority, complexity, time)
- [ ] Dependency creation (batch processing)
- [ ] Critical path calculation
- [ ] Work team management (CRUD)
- [ ] Financial data retrieval
- [ ] AI resource assignment
- [ ] Manual resource editing
- [ ] LangGraph workflows
- [ ] Microservice endpoints
- [ ] Monolith fallback
- [ ] UI dashboard
- [ ] Dependencies graph visualization
- [ ] Critical path graph visualization

---

## Notes

- All collections use proper naming conventions consistent with existing agents
- LLM prompts follow the pattern used in Performance and Financial agents
- UI follows the same design patterns as Performance and Financial dashboards
- Critical path uses algorithm (not LLM) for accuracy
- Dependencies stored minimally (IDs only) to save tokens and storage
- Resource assignments support both AI and manual editing

