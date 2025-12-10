# Predictive Risk Mitigation Agent/Microservice Implementation Plan

## Overview

The Predictive Risk Mitigation Agent is a LangGraph-based microservice that provides risk analysis, prediction, and mitigation strategies for projects. It includes a "What If Scenario Simulator" worker agent that visualizes project bottlenecks in an interactive graph and provides AI-powered mitigation suggestions and consequence analysis.

---

## Architecture Overview

### 1. Main Components

1. **RiskMitigationAgent** (Main Coordinator)
   - Similar structure to `PerformanceAgent` and `FinancialAgent`
   - Manages the What If Simulator worker agent
   - Uses centralized `RiskChromaManager` for data storage
   - Supports both monolithic and microservice modes

2. **RiskChromaManager** (Centralized Storage)
   - Dedicated ChromaDB manager for risk data
   - Collections follow naming convention: `project_risk_*`
   - Manages collections for bottlenecks, risk analysis, mitigation strategies, and consequences

3. **Worker Agent:**
   - **WhatIfSimulatorAgent**: Fetches bottlenecks, orders them by priority, generates interactive graphs, provides mitigation suggestions, and analyzes consequences

4. **LangGraph Workflows:**
   - `what_if_simulator_graph.py`: Main workflow for What If Scenario Simulator
   - Nodes in `nodes/` directory for each workflow step

5. **Risk Mitigation Service** (`proj/services/risk-mitigation-service/main.py`)
   - Flask service on port 8006
   - HTTP endpoints for risk operations
   - A2A protocol support
   - Fallback to monolithic mode
   - Uses existing Docker image (shared with other services)

---

## Phase 1: Core Infrastructure

### 1.1 Create Risk Mitigation Agent Structure

**Directory Structure:**
```
proj/backend/risk_mitigation_agent/
├── __init__.py
├── risk_mitigation_agent.py          # Main coordinator
├── chroma_manager.py                 # Centralized ChromaDB manager
├── agents/
│   ├── __init__.py
│   └── what_if_simulator_agent.py   # Worker agent for What If Simulator
├── graphs/
│   ├── __init__.py
│   └── what_if_simulator_graph.py   # LangGraph workflow
└── nodes/
    ├── __init__.py
    ├── bottleneck_fetch_nodes.py     # Fetch bottlenecks with details
    ├── bottleneck_ordering_nodes.py # Order bottlenecks by priority (LLM)
    ├── graph_generation_nodes.py     # Generate graph data
    ├── mitigation_suggestion_nodes.py # Generate mitigation suggestions (LLM)
    └── consequence_analysis_nodes.py # Analyze consequences (LLM)
```

### 1.2 RiskChromaManager

**File: `proj/backend/risk_mitigation_agent/chroma_manager.py`**

**Collections:**
- `project_risk_bottlenecks` - Cached bottleneck data (references `project_bottlenecks` from Performance Agent)
- `project_risk_mitigation_suggestions` - AI-generated mitigation strategies
- `project_risk_consequences` - Consequence analysis results
- `project_risk_ordering` - Bottleneck ordering results

**Metadata Structure:**
```python
# Risk Bottlenecks (cached from Performance Agent)
{
    'project_id': str,
    'bottleneck_id': str,  # Reference to bottleneck from performance agent
    'bottleneck_title': str,
    'category': str,
    'severity': str,
    'impact': str,
    'order_priority': int,  # Order determined by LLM (1 = first, 2 = second, etc.)
    'created_at': str
}

# Mitigation Suggestions
{
    'project_id': str,
    'bottleneck_id': str,
    'mitigation_points': [str],  # List of mitigation strategies
    'generated_at': str,
    'llm_model': str
}

# Consequences
{
    'project_id': str,
    'bottleneck_id': str,
    'consequence_points': [str],  # List of consequences
    'generated_at': str,
    'llm_model': str
}
```

### 1.3 What If Simulator Agent

**File: `proj/backend/risk_mitigation_agent/agents/what_if_simulator_agent.py`**

**Key Methods:**
- `fetch_project_bottlenecks(project_id: str) -> List[Dict]`: Fetch bottlenecks with details from Performance Agent
- `order_bottlenecks_by_priority(bottlenecks: List[Dict], llm_manager) -> List[Dict]`: Use LLM to order bottlenecks by which will occur first
- `generate_mitigation_suggestions(bottleneck_id: str, bottleneck_title: str, all_bottleneck_titles: List[str], llm_manager) -> Dict`: Generate AI-powered mitigation suggestions
- `analyze_consequences(bottleneck_id: str, bottleneck_title: str, all_bottleneck_titles: List[str], llm_manager) -> Dict`: Analyze consequences of bottleneck
- `generate_graph_data(ordered_bottlenecks: List[Dict]) -> Dict`: Generate data structure for interactive graph

---

## Phase 2: LangGraph Workflow

### 2.1 What If Simulator Graph

**File: `proj/backend/risk_mitigation_agent/graphs/what_if_simulator_graph.py`**

**State Definition:**
```python
class WhatIfSimulatorState(TypedDict):
    project_id: str
    llm_manager: Any
    chroma_manager: Any
    a2a_router: Optional[Any]
    bottlenecks: List[Dict]
    ordered_bottlenecks: List[Dict]
    graph_data: Dict
    selected_bottleneck_id: Optional[str]
    mitigation_result: Dict
    consequence_result: Dict
    error: str
```

**Graph Flow:**
1. **fetch_bottlenecks** → Fetch bottlenecks from Performance Agent (via A2A or direct)
2. **order_bottlenecks** → Use LLM to order bottlenecks by priority
3. **generate_graph** → Generate graph data structure
4. **get_mitigation** (conditional) → Generate mitigation suggestions when node clicked
5. **get_consequences** (conditional) → Analyze consequences when button clicked

**Nodes:**
- `fetch_bottlenecks_node`: Calls WhatIfSimulatorAgent.fetch_project_bottlenecks()
- `order_bottlenecks_node`: Calls WhatIfSimulatorAgent.order_bottlenecks_by_priority()
- `generate_graph_node`: Calls WhatIfSimulatorAgent.generate_graph_data()
- `get_mitigation_node`: Calls WhatIfSimulatorAgent.generate_mitigation_suggestions()
- `get_consequences_node`: Calls WhatIfSimulatorAgent.analyze_consequences()

---

## Phase 3: Backend Service

### 3.1 Risk Mitigation Service

**File: `proj/services/risk-mitigation-service/main.py`**

**Endpoints:**
- `GET /health` - Health check
- `POST /what_if_simulator/<project_id>` - Get What If Simulator data (bottlenecks + graph)
- `POST /mitigation/<project_id>/<bottleneck_id>` - Get mitigation suggestions for a bottleneck
- `POST /consequences/<project_id>/<bottleneck_id>` - Get consequences for a bottleneck
- `POST /a2a/message` - Handle A2A protocol messages

**Port:** 8006

**A2A Integration:**
- Register with A2A router as "risk-mitigation-service"
- Can request bottleneck data from Performance Service via A2A
- Supports both A2A (microservice) and direct calls (monolith)

---

## Phase 4: Frontend Implementation

### 4.1 Project Details Card

**File: `proj/templates/project_details.html`**

Add a new card similar to Performance and Financial Agent cards:

```html
<!-- Risk Mitigation Agent Container -->
<div class="card mb-6" style="animation: slideInUp 0.9s ease-out;">
    <div class="card-header">
        <h3 class="card-title">
            <i class="fas fa-shield-alt text-red-500"></i> Prediction and Risk Mitigation
        </h3>
        <div class="flex items-center gap-2">
            <span class="badge badge-danger">AI-Powered Risk Analysis</span>
        </div>
    </div>
    
    <div class="risk-mitigation-agent-container">
        <!-- Risk Metrics Cards -->
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            <div class="metric-card bg-gradient-to-br from-red-50 to-red-100 border-l-4 border-red-500">
                <div class="metric-icon">
                    <i class="fas fa-exclamation-triangle text-red-600 text-3xl"></i>
                </div>
                <div class="metric-content">
                    <h4 class="metric-title text-gray-700">Bottlenecks</h4>
                    <p class="metric-value text-red-600" id="risk-bottlenecks-count">0</p>
                    <p class="metric-subtitle text-gray-600">Identified risks</p>
                </div>
            </div>
            
            <div class="metric-card bg-gradient-to-br from-orange-50 to-orange-100 border-l-4 border-orange-500">
                <div class="metric-icon">
                    <i class="fas fa-chart-line text-orange-600 text-3xl"></i>
                </div>
                <div class="metric-content">
                    <h4 class="metric-title text-gray-700">Risk Score</h4>
                    <p class="metric-value text-orange-600" id="risk-score">0%</p>
                    <p class="metric-subtitle text-gray-600">Overall risk level</p>
                </div>
            </div>
            
            <div class="metric-card bg-gradient-to-br from-yellow-50 to-yellow-100 border-l-4 border-yellow-500">
                <div class="metric-icon">
                    <i class="fas fa-lightbulb text-yellow-600 text-3xl"></i>
                </div>
                <div class="metric-content">
                    <h4 class="metric-title text-gray-700">Mitigations</h4>
                    <p class="metric-value text-yellow-600" id="mitigations-count">0</p>
                    <p class="metric-subtitle text-gray-600">Available strategies</p>
                </div>
            </div>
        </div>
        
        <!-- Action Buttons -->
        <div class="flex gap-4">
            <button onclick="viewRiskMitigationDashboard()" class="btn btn-danger btn-lg">
                <i class="fas fa-tachometer-alt"></i> Risk Mitigation Dashboard
            </button>
            <button onclick="viewWhatIfSimulator()" class="btn btn-warning btn-lg">
                <i class="fas fa-project-diagram"></i> What If Scenario Simulator
            </button>
        </div>
    </div>
</div>
```

### 4.2 Risk Mitigation Dashboard

**File: `proj/templates/risk_mitigation_dashboard.html`**

Create a comprehensive dashboard showing:
- Risk overview metrics
- Bottleneck summary
- Risk trends
- Mitigation strategies overview
- Links to What If Simulator

### 4.3 What If Scenario Simulator Page

**File: `proj/templates/what_if_simulator.html`**

**Key Features:**
1. **Interactive Graph Visualization**
   - Use a graph library (e.g., D3.js, vis.js, or Cytoscape.js)
   - Nodes represent bottlenecks (boxes with titles)
   - Nodes positioned based on order priority
   - Beautiful, modern styling with animations

2. **Node Interaction**
   - Click on a node → Opens a closable card
   - Card shows:
     - Bottleneck title
     - Category, severity, impact
     - "Get Mitigation Suggestions" button
     - "View Consequences" button

3. **Mitigation Suggestions Card**
   - Opens when "Get Mitigation Suggestions" is clicked
   - Shows loading state while LLM processes
   - Displays JSON-parsed mitigation points as bullet points
   - Beautiful card design with icons
   - Close button

4. **Consequences Card**
   - Opens when "View Consequences" is clicked
   - Shows loading state while LLM processes
   - Displays JSON-parsed consequence points as bullet points
   - Beautiful card design with icons
   - Close button

**Graph Styling Requirements:**
- Modern, clean design
- Color-coded nodes by severity (High = red, Medium = orange, Low = yellow)
- Smooth animations on node click
- Responsive layout
- Beautiful card overlays with shadows and gradients

---

## Phase 5: Backend Routes (app.py)

### 5.1 Add Routes to app.py

**Routes to add:**
```python
# Risk Mitigation Dashboard
@app.route('/risk_mitigation/dashboard/<project_id>')
def risk_mitigation_dashboard(project_id):
    """Render risk mitigation dashboard"""
    # Implementation

# What If Simulator
@app.route('/risk_mitigation/what_if_simulator/<project_id>')
def what_if_simulator(project_id):
    """Render What If Scenario Simulator page"""
    # Implementation

# API Endpoints
@app.route('/api/risk_mitigation/what_if_simulator/<project_id>', methods=['GET'])
def get_what_if_simulator_data(project_id):
    """Get What If Simulator data (bottlenecks + graph)"""
    # Implementation

@app.route('/api/risk_mitigation/mitigation/<project_id>/<bottleneck_id>', methods=['POST'])
def get_mitigation_suggestions(project_id, bottleneck_id):
    """Get mitigation suggestions for a bottleneck"""
    # Implementation

@app.route('/api/risk_mitigation/consequences/<project_id>/<bottleneck_id>', methods=['POST'])
def get_consequences(project_id, bottleneck_id):
    """Get consequences for a bottleneck"""
    # Implementation
```

---

## Phase 6: LLM-Powered Functions

### 6.1 Bottleneck Ordering Function

**Implementation:**
```python
def order_bottlenecks_by_priority(bottlenecks: List[Dict], llm_manager) -> List[Dict]:
    """
    Order bottlenecks by which will occur first using LLM.
    
    Args:
        bottlenecks: List of bottleneck dicts with 'id' and 'bottleneck' (title)
        llm_manager: LLM manager instance
        
    Returns:
        List of bottlenecks with 'order_priority' field added (1 = first, 2 = second, etc.)
    """
    # Extract only IDs and titles for LLM (to save context window)
    bottleneck_summary = [
        {'id': b['id'], 'title': b['bottleneck']}
        for b in bottlenecks
    ]
    
    # Create prompt
    prompt = f"""Analyze the following project bottlenecks and order them by which will occur first in the project timeline.

Bottlenecks:
{json.dumps(bottleneck_summary, indent=2)}

Return a JSON array with the bottleneck IDs in order (first to occur = first in array).
Format: {{"ordered_ids": ["id1", "id2", "id3", ...]}}
"""
    
    # Call LLM
    response = llm_manager.generate_response(prompt)
    
    # Parse JSON response
    result = json.loads(response)
    ordered_ids = result.get('ordered_ids', [])
    
    # Add order_priority to bottlenecks
    for i, bottleneck in enumerate(bottlenecks):
        if bottleneck['id'] in ordered_ids:
            bottleneck['order_priority'] = ordered_ids.index(bottleneck['id']) + 1
        else:
            bottleneck['order_priority'] = len(bottlenecks) + 1  # Put unlisted ones at end
    
    # Sort by order_priority
    return sorted(bottlenecks, key=lambda x: x.get('order_priority', 999))
```

### 6.2 Mitigation Suggestions Function

**Implementation:**
```python
def generate_mitigation_suggestions(bottleneck_id: str, bottleneck_title: str, 
                                   all_bottleneck_titles: List[str], llm_manager) -> Dict:
    """
    Generate AI-powered mitigation suggestions for a bottleneck.
    
    Args:
        bottleneck_id: ID of the bottleneck
        bottleneck_title: Title of the bottleneck
        all_bottleneck_titles: List of all bottleneck titles in project (for context)
        llm_manager: LLM manager instance
        
    Returns:
        Dict with 'mitigation_points' list
    """
    # Create prompt
    prompt = f"""You are a project risk management expert. Analyze the following bottleneck and provide mitigation strategies.

Current Bottleneck: {bottleneck_title}

Other Bottlenecks in Project (for context):
{chr(10).join(f"- {title}" for title in all_bottleneck_titles)}

Provide 3-5 specific, actionable mitigation strategies for this bottleneck.
Return JSON format:
{{
    "mitigation_points": [
        "Strategy 1",
        "Strategy 2",
        "Strategy 3"
    ]
}}
"""
    
    # Call LLM
    response = llm_manager.generate_response(prompt)
    
    # Parse JSON response
    result = json.loads(response)
    mitigation_points = result.get('mitigation_points', [])
    
    return {
        'bottleneck_id': bottleneck_id,
        'bottleneck_title': bottleneck_title,
        'mitigation_points': mitigation_points,
        'generated_at': datetime.now().isoformat()
    }
```

### 6.3 Consequence Analysis Function

**Implementation:**
```python
def analyze_consequences(bottleneck_id: str, bottleneck_title: str,
                        all_bottleneck_titles: List[str], llm_manager) -> Dict:
    """
    Analyze consequences of a bottleneck.
    
    Args:
        bottleneck_id: ID of the bottleneck
        bottleneck_title: Title of the bottleneck
        all_bottleneck_titles: List of all bottleneck titles in project (for context)
        llm_manager: LLM manager instance
        
    Returns:
        Dict with 'consequence_points' list
    """
    # Create prompt
    prompt = f"""You are a project risk management expert. Analyze the consequences if the following bottleneck is not addressed.

Bottleneck: {bottleneck_title}

Other Bottlenecks in Project (for context):
{chr(10).join(f"- {title}" for title in all_bottleneck_titles)}

Provide 3-5 specific consequences that could occur if this bottleneck is not mitigated.
Return JSON format:
{{
    "consequence_points": [
        "Consequence 1",
        "Consequence 2",
        "Consequence 3"
    ]
}}
"""
    
    # Call LLM
    response = llm_manager.generate_response(prompt)
    
    # Parse JSON response
    result = json.loads(response)
    consequence_points = result.get('consequence_points', [])
    
    return {
        'bottleneck_id': bottleneck_id,
        'bottleneck_title': bottleneck_title,
        'consequence_points': consequence_points,
        'generated_at': datetime.now().isoformat()
    }
```

---

## Phase 7: Graph Visualization

### 7.1 Graph Data Structure

**Format:**
```json
{
    "nodes": [
        {
            "id": "bottleneck_1",
            "label": "Resource allocation delays",
            "order_priority": 1,
            "category": "resource",
            "severity": "high",
            "impact": "schedule_delay"
        },
        ...
    ],
    "edges": []  // Can be empty or show dependencies if needed
}
```

### 7.2 Graph Library Selection

**Recommended:** Use **vis-network** or **Cytoscape.js** for interactive graphs.

**vis-network Example:**
- Easy to use
- Good documentation
- Supports node click events
- Beautiful styling options

**Implementation:**
```javascript
// Initialize graph
const nodes = new vis.DataSet(graphData.nodes);
const edges = new vis.DataSet(graphData.edges);
const data = { nodes, edges };
const options = {
    nodes: {
        shape: 'box',
        font: { size: 14 },
        borderWidth: 2,
        color: {
            border: '#2B7CE9',
            background: '#D2E5FF',
            highlight: { border: '#2B7CE9', background: '#D2E5FF' }
        }
    },
    layout: {
        hierarchical: {
            enabled: true,
            direction: 'LR',  // Left to Right
            sortMethod: 'directed'
        }
    }
};
const network = new vis.Network(container, data, options);

// Handle node click
network.on('click', function(params) {
    if (params.nodes.length > 0) {
        const nodeId = params.nodes[0];
        showBottleneckCard(nodeId);
    }
});
```

---

## Phase 8: Testing

### 8.1 Test File

**File: `proj/tests/test_risk_mitigation_agent.py`**

**Test Cases:**
1. Test bottleneck fetching from Performance Agent
2. Test bottleneck ordering (LLM call)
3. Test graph data generation
4. Test mitigation suggestions generation (LLM call)
5. Test consequence analysis (LLM call)
6. Test A2A protocol integration
7. Test fallback to monolith mode
8. Test service endpoints

---

## Phase 9: Docker Integration

### 9.1 Update docker-entrypoint.sh

Add risk-mitigation-service to entrypoint:
```bash
risk-mitigation-service)
    exec python services/risk-mitigation-service/main.py
    ;;
```

### 9.2 Update docker-compose.yml

Add risk-mitigation-service:
```yaml
risk-mitigation-service:
  build:
    context: .
    dockerfile: Dockerfile
  command: ["risk-mitigation-service"]
  container_name: risk-mitigation-service
  ports:
    - "8006:8006"
  environment:
    - A2A_ROUTER_URL=http://a2a-router-service:8004
  volumes:
    - ./chroma_db:/app/chroma_db
    - ./data:/app/data
  depends_on:
    - a2a-router-service
    - performance-service
  healthcheck:
    test: ["CMD", "python", "-c", "import requests; requests.get('http://localhost:8006/health', timeout=5)"]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 40s
  restart: unless-stopped
  networks:
    - microservices-network
```

### 9.3 Update API Gateway

Add risk-mitigation-service to API gateway routing.

---

## Implementation Checklist

### Backend
- [ ] Create `risk_mitigation_agent` directory structure
- [ ] Implement `RiskChromaManager`
- [ ] Implement `RiskMitigationAgent` (main coordinator)
- [ ] Implement `WhatIfSimulatorAgent` (worker agent)
- [ ] Create LangGraph workflow (`what_if_simulator_graph.py`)
- [ ] Implement graph nodes
- [ ] Create Flask service (`risk-mitigation-service/main.py`)
- [ ] Add A2A protocol support
- [ ] Add routes to `app.py`
- [ ] Implement bottleneck ordering function (LLM)
- [ ] Implement mitigation suggestions function (LLM)
- [ ] Implement consequence analysis function (LLM)

### Frontend
- [ ] Add Risk Mitigation card to `project_details.html`
- [ ] Create `risk_mitigation_dashboard.html`
- [ ] Create `what_if_simulator.html`
- [ ] Implement interactive graph visualization
- [ ] Implement node click handler
- [ ] Implement mitigation suggestions card
- [ ] Implement consequences card
- [ ] Add beautiful styling and animations
- [ ] Add JavaScript for API calls

### Integration
- [ ] Update `docker-entrypoint.sh`
- [ ] Update `docker-compose.yml`
- [ ] Update API gateway
- [ ] Register with A2A router
- [ ] Test A2A communication with Performance Service

### Testing
- [ ] Create test file
- [ ] Test individual components
- [ ] Test end-to-end workflow
- [ ] Test UI interactions
- [ ] Test A2A protocol
- [ ] Test fallback to monolith

---

## Database Collections Summary

### ChromaDB Collections

1. **`project_risk_bottlenecks`**
   - Cached bottleneck data from Performance Agent
   - Metadata: project_id, bottleneck_id, bottleneck_title, category, severity, impact, order_priority

2. **`project_risk_mitigation_suggestions`**
   - AI-generated mitigation strategies
   - Metadata: project_id, bottleneck_id, mitigation_points, generated_at

3. **`project_risk_consequences`**
   - Consequence analysis results
   - Metadata: project_id, bottleneck_id, consequence_points, generated_at

4. **`project_risk_ordering`**
   - Bottleneck ordering results
   - Metadata: project_id, ordered_bottleneck_ids, generated_at

---

## API Endpoints Summary

### Service Endpoints (Port 8006)

- `GET /health` - Health check
- `POST /what_if_simulator/<project_id>` - Get What If Simulator data
- `POST /mitigation/<project_id>/<bottleneck_id>` - Get mitigation suggestions
- `POST /consequences/<project_id>/<bottleneck_id>` - Get consequences
- `POST /a2a/message` - Handle A2A messages

### Main App Endpoints (Port 5001)

- `GET /risk_mitigation/dashboard/<project_id>` - Risk mitigation dashboard
- `GET /risk_mitigation/what_if_simulator/<project_id>` - What If Simulator page
- `GET /api/risk_mitigation/what_if_simulator/<project_id>` - Get simulator data
- `POST /api/risk_mitigation/mitigation/<project_id>/<bottleneck_id>` - Get mitigation
- `POST /api/risk_mitigation/consequences/<project_id>/<bottleneck_id>` - Get consequences

---

## Notes

1. **Bottleneck Data Source**: Bottlenecks are fetched from Performance Agent's `project_bottlenecks` collection. We cache them in our own collection for faster access.

2. **LLM Context Window**: When calling LLM for ordering, suggestions, or consequences, we only send bottleneck titles (not full details) to save context window space.

3. **Graph Ordering**: Bottlenecks are ordered by LLM to determine which will occur first. This order is used to position nodes in the graph.

4. **Lazy Loading**: Mitigation suggestions and consequences are only generated when the user clicks on a node/button, not pre-computed.

5. **Beautiful UI**: All UI components should follow the existing design system with gradients, shadows, animations, and modern styling.

6. **Docker Image**: Uses the existing shared Docker image (no new image needed).

7. **A2A Protocol**: Supports both microservice mode (A2A) and monolith mode (direct calls).

---

## Next Steps

1. Review and approve this plan
2. Start with Phase 1 (Core Infrastructure)
3. Implement backend components
4. Implement frontend components
5. Test integration
6. Deploy and verify

---

**End of Implementation Plan**

