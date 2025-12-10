# Risk Mitigation Agent: Data Storage & What If Scenario Simulator

## 📦 ChromaDB Collections

The Risk Mitigation Agent creates **4 new ChromaDB collections** to store its data:

### 1. `project_risk_bottlenecks`
- **Purpose**: Stores project bottlenecks fetched from Performance Agent
- **Data**: Bottleneck details (title, category, severity, impact)
- **Usage**: Currently used for caching, but bottlenecks are primarily fetched on-demand from Performance Agent

### 2. `project_risk_mitigation_suggestions`
- **Purpose**: Stores LLM-generated mitigation suggestions for bottlenecks
- **Data Structure**:
  ```json
  {
    "id": "mitigation_{bottleneck_id}_{timestamp}",
    "text": "JSON array of mitigation points",
    "metadata": {
      "bottleneck_id": "...",
      "bottleneck_title": "...",
      "project_id": "..."
    }
  }
  ```
- **Generated**: On-demand when user clicks a bottleneck node in the What If Simulator
- **Content**: 3-5 specific, actionable mitigation strategies per bottleneck

### 3. `project_risk_consequences`
- **Purpose**: Stores LLM-generated consequence analysis for bottlenecks
- **Data Structure**:
  ```json
  {
    "id": "consequence_{bottleneck_id}_{timestamp}",
    "text": "JSON array of consequence points",
    "metadata": {
      "bottleneck_id": "...",
      "bottleneck_title": "...",
      "project_id": "..."
    }
  }
  ```
- **Generated**: On-demand when user clicks "Consequences" button in the simulator
- **Content**: 3-5 specific consequences if the bottleneck is not addressed

### 4. `project_risk_ordering`
- **Purpose**: Stores the ordered sequence of bottlenecks (which will occur first)
- **Data Structure**:
  ```json
  {
    "id": "ordering_{project_id}",
    "text": "JSON array of bottleneck IDs in order",
    "metadata": {
      "project_id": "...",
      "ordered_count": 27
    }
  }
  ```
- **Generated**: During first-time initialization or when accessing What If Simulator
- **Content**: Array of bottleneck IDs ordered by priority (first to occur = first in array)

---

## 🔮 What If Scenario Simulator: How It Works

### Overview
The What If Scenario Simulator is a **worker agent** (`WhatIfSimulatorAgent`) that:
1. Fetches bottlenecks from Performance Agent
2. Enhances impacts for bottlenecks with "Unknown impact"
3. Orders bottlenecks by priority (which will occur first)
4. Generates interactive graph data
5. Provides on-demand mitigation suggestions and consequences

### First-Time Generation Routine

**Important**: The What If Simulator does NOT have a traditional "first-time generation" like document extraction agents. Instead, it operates **on-demand** when you access the simulator page.

#### When You First Access the What If Simulator:

**Step 1: Fetch Bottlenecks** (`fetch_project_bottlenecks`)
- **Source**: Performance Agent (via A2A protocol, direct access, or ChromaDB)
- **Fallback Chain**:
  1. Try A2A protocol (microservice mode) → `orchestrator.route_data_request()`
  2. Fallback to direct access (monolith mode) → `performance_agent.bottleneck_agent.get_project_bottlenecks()`
  3. Last resort: Direct ChromaDB access → `performance_chroma_manager.get_performance_data('bottlenecks')`
- **Enhancement**: Automatically enhances impacts for bottlenecks with "Unknown impact" using LLM
  - Processes in batches of 5
  - Uses LLM to determine specific impacts (schedule, budget, quality, resources, stakeholders)
  - Updates bottleneck data with enhanced impacts

**Step 2: Order Bottlenecks by Priority** (`order_bottlenecks_by_priority`)
- **Method**: LLM-powered analysis
- **Input**: List of bottleneck IDs and titles only (to save context window)
- **LLM Prompt**: Analyzes dependencies, timeline, critical path, resource constraints
- **Output**: Ordered list of bottleneck IDs (first to occur = first in array)
- **Storage**: Stored in `project_risk_ordering` collection

**Step 3: Generate Graph Data** (`generate_graph_data`)
- **Input**: Ordered bottlenecks with all details
- **Output**: Graph structure with:
  - **Nodes**: Each bottleneck as a node with:
    - ID, label (title), order_priority
    - Category, severity, impact
    - Color coding based on severity (High=red, Medium=orange, Low=yellow)
  - **Edges**: Currently empty (can be added later for dependencies)

**Step 4: Display Interactive Graph**
- Frontend renders graph using `vis-network`
- Nodes are clickable
- Clicking a node opens a modal with bottleneck details

### On-Demand Features

#### Mitigation Suggestions (`generate_mitigation_suggestions`)
- **Trigger**: User clicks a bottleneck node in the graph
- **LLM Call**: Made ONLY when user clicks (not pre-generated)
- **Context**: 
  - Current bottleneck title
  - All other bottleneck titles in project (for context)
- **Output**: 3-5 specific, actionable mitigation strategies
- **Storage**: Saved to `project_risk_mitigation_suggestions` collection
- **Format**: JSON array of mitigation points

#### Consequences Analysis (`analyze_consequences`)
- **Trigger**: User clicks "Consequences" button in the bottleneck modal
- **LLM Call**: Made ONLY when user clicks (not pre-generated)
- **Context**:
  - Current bottleneck title
  - All other bottleneck titles in project (for context)
- **Output**: 3-5 specific consequences if bottleneck is not addressed
- **Storage**: Saved to `project_risk_consequences` collection
- **Format**: JSON array of consequence points

---

## 🔄 Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Performance Agent                        │
│  (Source of Truth for Bottlenecks)                          │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ A2A / Direct Access / ChromaDB
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              What If Simulator Agent                         │
│                                                              │
│  1. fetch_project_bottlenecks()                             │
│     ├─ Fetch from Performance Agent                        │
│     └─ Enhance impacts (LLM) for "Unknown impact"           │
│                                                              │
│  2. order_bottlenecks_by_priority()                         │
│     └─ LLM determines order (first to occur)               │
│                                                              │
│  3. generate_graph_data()                                   │
│     └─ Create nodes/edges for vis-network                   │
│                                                              │
│  4. generate_mitigation_suggestions() [ON-DEMAND]           │
│     └─ LLM generates when user clicks node                  │
│                                                              │
│  5. analyze_consequences() [ON-DEMAND]                       │
│     └─ LLM generates when user clicks "Consequences"        │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ Store Results
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              Risk Mitigation ChromaDB Collections          │
│                                                              │
│  • project_risk_ordering (bottleneck order)                 │
│  • project_risk_mitigation_suggestions (on-demand)          │
│  • project_risk_consequences (on-demand)                    │
│  • project_risk_bottlenecks (caching, optional)             │
└─────────────────────────────────────────────────────────────┘
```

---

## 📋 Key Design Decisions

### 1. **No Pre-Generation of Suggestions/Consequences**
- **Why**: Saves LLM API calls and storage
- **How**: Generated only when user explicitly requests them
- **Benefit**: Faster initial load, lower costs

### 2. **On-Demand Impact Enhancement**
- **Why**: Many bottlenecks have "Unknown impact"
- **How**: Automatically enhanced during bottleneck fetch
- **Benefit**: Better data quality without manual intervention

### 3. **Ordering Stored for Reuse**
- **Why**: Ordering is expensive (LLM call)
- **How**: Stored in `project_risk_ordering` collection
- **Benefit**: Can be reused until bottlenecks change

### 4. **Multi-Mode Access (A2A + Direct + ChromaDB)**
- **Why**: Supports both microservice and monolith modes
- **How**: Fallback chain ensures data access
- **Benefit**: Works in any deployment configuration

---

## 🚀 Usage Flow

### First Time Accessing What If Simulator:

1. User navigates to `/risk_mitigation/what_if_simulator/<project_id>`
2. Frontend calls `/api/risk_mitigation/what_if_simulator/<project_id>`
3. Backend:
   - Fetches bottlenecks (enhances impacts)
   - Orders bottlenecks (LLM call)
   - Generates graph data
   - Returns to frontend
4. Frontend renders interactive graph
5. User clicks a node → Modal opens
6. User clicks "Mitigations" → LLM call → Suggestions displayed
7. User clicks "Consequences" → LLM call → Consequences displayed

### Subsequent Accesses:

- If bottlenecks haven't changed, ordering can be retrieved from ChromaDB
- Mitigation suggestions and consequences are cached after first generation
- Graph is regenerated each time (to reflect any changes)

---

## 📊 Collection Statistics

Each collection stores:
- **Embeddings**: Vector embeddings for semantic search (using `all-MiniLM-L6-v2`)
- **Documents**: Text content (JSON strings for structured data)
- **Metadata**: Project ID, timestamps, bottleneck IDs, etc.
- **IDs**: Unique identifiers for each entry

---

## 🔍 Example Data Structures

### Ordering Collection Entry:
```json
{
  "id": "ordering_project_123",
  "content": "[\"bottleneck_1\", \"bottleneck_5\", \"bottleneck_3\", ...]",
  "metadata": {
    "project_id": "project_123",
    "ordered_count": 27,
    "created_at": "2024-01-15T10:30:00"
  }
}
```

### Mitigation Suggestions Entry:
```json
{
  "id": "mitigation_bottleneck_1_20240115_103000",
  "content": "[\"Strategy 1: ...\", \"Strategy 2: ...\", ...]",
  "metadata": {
    "bottleneck_id": "bottleneck_1",
    "bottleneck_title": "Inadequate project planning",
    "project_id": "project_123",
    "created_at": "2024-01-15T10:30:00"
  }
}
```

---

## ✅ Summary

- **4 New Collections**: `project_risk_bottlenecks`, `project_risk_mitigation_suggestions`, `project_risk_consequences`, `project_risk_ordering`
- **On-Demand Generation**: No pre-generation; data created when needed
- **LLM-Powered**: Uses LLM for ordering, impact enhancement, suggestions, and consequences
- **Multi-Mode Support**: Works with A2A, direct access, and ChromaDB
- **Efficient**: Caches expensive operations (ordering) and generates lightweight operations (suggestions) on-demand

