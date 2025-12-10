# Risk Mitigation Agent - Calculations & Logic Explanation

## Overview

The Risk Mitigation Agent reads bottlenecks from the Performance Agent and provides risk analysis, prediction, and mitigation strategies. It does NOT extract data itself - it relies on Performance Agent having already extracted bottlenecks.

---

## 1. Risk Score Calculation

### Formula
```
Risk Score = (Critical×4 + High×3 + Medium×2 + Low×1) / (Total × 4) × 100
```

### Explanation
- **Critical Severity**: Weight = 4
- **High Severity**: Weight = 3
- **Medium Severity**: Weight = 2
- **Low Severity**: Weight = 1

### Examples

**Example 1:**
- 3 Critical, 10 High, 10 Medium, 4 Low (Total: 27)
- Score = (3×4 + 10×3 + 10×2 + 4×1) / (27×4) × 100
- Score = (12 + 30 + 20 + 4) / 108 × 100
- Score = 66 / 108 × 100 = **61.11%**

**Example 2:**
- All High severity (10 bottlenecks)
- Score = (10×3) / (10×4) × 100 = 30/40 × 100 = **75%**

**Example 3:**
- All Critical severity (10 bottlenecks)
- Score = (10×4) / (10×4) × 100 = 40/40 × 100 = **100%**

**Example 4:**
- All Medium severity (10 bottlenecks)
- Score = (10×2) / (10×4) × 100 = 20/40 × 100 = **50%**

**Example 5:**
- All Low severity (10 bottlenecks)
- Score = (10×1) / (10×4) × 100 = 10/40 × 100 = **25%**

### Range
- **Minimum**: 25% (if all bottlenecks are Low severity)
- **Maximum**: 100% (if all bottlenecks are Critical severity)

---

## 2. High Severity / Critical Risks Count

### Logic
```python
high_severity = sum(1 for b in bottlenecks if b.get('severity') in ['High', 'Critical'])
```

### Explanation
- Counts bottlenecks where `severity == 'High'` OR `severity == 'Critical'`
- Both are considered "critical risks" for the dashboard
- This is a simple count, not weighted

### Example
- 3 bottlenecks with severity = "High"
- 0 bottlenecks with severity = "Critical"
- **High Severity Count = 3**

---

## 3. Impact Determination

### Automatic Enhancement
When bottlenecks are fetched, the system automatically:

1. **Checks for Unknown Impacts**: Identifies bottlenecks with:
   - `impact == "Unknown impact"`
   - `impact == "Unknown"`
   - `impact == ""` (empty)

2. **LLM Analysis**: For each bottleneck with unknown impact:
   - Sends bottleneck description, category, and severity to LLM
   - LLM analyzes and determines specific impact
   - Considers: schedule, budget, quality, resources, stakeholders

3. **Batch Processing**: Processes in batches of 5 to avoid overwhelming LLM

4. **Updates**: Replaces "Unknown impact" with specific impact description

### Impact Categories Considered
- Schedule/timeline impacts
- Budget/cost impacts
- Quality/technical impacts
- Resource/team impacts
- Stakeholder/communication impacts

---

## 4. First Time Generation Routine

### Important Note
**Risk Mitigation Agent does NOT have a traditional "first time generation"** because it doesn't extract data from documents. It reads bottlenecks that were already extracted by the Performance Agent.

### Initialization Routine

However, we have an **`initialize_risk_analysis()`** method that:

1. **Fetches Bottlenecks** from Performance Agent
   - Uses A2A protocol (microservice mode) or direct access (monolith mode)
   - Automatically enhances impacts for bottlenecks with "Unknown impact"

2. **Orders Bottlenecks** by Priority
   - Uses LLM to determine which bottlenecks will occur first
   - Considers: dependencies, timeline, critical path, resource constraints

3. **Stores Ordering Data**
   - Saves the ordered bottleneck IDs in ChromaDB
   - Used for graph visualization

### When It's Called
- **Automatically**: When accessing Risk Mitigation Dashboard for the first time
- **On-Demand**: Can be called via API endpoint (if we add one)
- **Lazy Loading**: Data is generated when needed, not pre-computed

### Workflow
```
User opens Risk Mitigation Dashboard
    ↓
initialize_risk_analysis() is called (implicitly via get_what_if_simulator_data)
    ↓
1. Fetch bottlenecks from Performance Agent
    ↓
2. Enhance impacts (if unknown) using LLM
    ↓
3. Order bottlenecks by priority using LLM
    ↓
4. Generate graph data
    ↓
5. Display in dashboard
```

---

## 5. Bottleneck Ordering Logic

### How It Works
1. **Extract IDs and Titles**: Only sends bottleneck IDs and titles to LLM (to save context window)
2. **LLM Analysis**: LLM analyzes and orders by:
   - Dependencies between bottlenecks
   - Project timeline and phases
   - Critical path impacts
   - Resource availability constraints
3. **Returns Ordered IDs**: LLM returns JSON with ordered bottleneck IDs
4. **Assign Priority**: Each bottleneck gets an `order_priority` field (1 = first, 2 = second, etc.)

### Example
```
Input Bottlenecks:
- ID: "b1", Title: "Resource allocation delays"
- ID: "b2", Title: "Environmental approval pending"
- ID: "b3", Title: "Vendor material supply issues"

LLM Analysis:
- "b2" will occur first (environmental approval is prerequisite)
- "b1" will occur second (resource allocation depends on approval)
- "b3" will occur third (material supply comes later)

Output:
- b2: order_priority = 1
- b1: order_priority = 2
- b3: order_priority = 3
```

---

## 6. Data Flow

### Reading Bottlenecks
```
Risk Mitigation Agent
    ↓
WhatIfSimulatorAgent.fetch_project_bottlenecks()
    ↓
[Try A2A Protocol] → Performance Service → Performance Agent → ChromaDB
    ↓ (if fails)
[Try Direct Access] → Performance Agent → ChromaDB
    ↓ (if fails)
[Try Direct ChromaDB] → PerformanceChromaManager → ChromaDB
```

### Impact Enhancement
```
Bottlenecks with "Unknown impact"
    ↓
Batch into groups of 5
    ↓
Send to LLM with prompt
    ↓
LLM returns JSON: {"bottleneck text": "specific impact"}
    ↓
Update bottleneck['impact'] with enhanced value
```

### Ordering
```
All Bottlenecks (IDs + Titles only)
    ↓
Send to LLM with ordering prompt
    ↓
LLM returns: {"ordered_ids": ["id1", "id2", "id3", ...]}
    ↓
Assign order_priority to each bottleneck
    ↓
Sort by order_priority
```

---

## Summary

1. **Risk Score**: Weighted average (Critical×4, High×3, Medium×2, Low×1) normalized to 0-100%
2. **High Severity Count**: Simple count of bottlenecks with severity = "High" or "Critical"
3. **Impact Enhancement**: Automatic LLM analysis for bottlenecks with unknown impacts
4. **First Time Generation**: No traditional first-time generation - data is generated on-demand when dashboard is accessed
5. **Ordering**: LLM-powered ordering based on timeline, dependencies, and critical path

---

**Last Updated**: Implementation Date
**Version**: 1.0

