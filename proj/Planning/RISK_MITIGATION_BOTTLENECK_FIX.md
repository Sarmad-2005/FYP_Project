# Risk Mitigation Agent - Bottleneck Fetching Fix

## Problem
The Risk Mitigation Agent was fetching the wrong data:
- Expected: **9 bottlenecks** (e.g., "Environmental approval necessary")
- Got: **27 items** that looked like tasks, not bottlenecks

## Root Cause
The A2A routing query was too generic:
```python
query="Get all project bottlenecks with their details, categories, severities, and impacts"
```

This semantic query was matching:
- ❌ Tasks
- ❌ Bottleneck suggestions
- ✅ Actual bottlenecks (only 9)

## Solution

### 1. Updated A2A Query
**File**: `proj/backend/risk_mitigation_agent/agents/what_if_simulator_agent.py`

**BEFORE**:
```python
query="Get all project bottlenecks with their details, categories, severities, and impacts"
```

**AFTER**:
```python
query="performance_agent.get_bottlenecks"  # Direct method call
```

### 2. Enhanced Direct Access Path
The direct access (monolith mode) now explicitly calls:
```python
bottlenecks = performance_agent.bottleneck_agent.get_project_bottlenecks(project_id)
```

This method (`get_project_bottlenecks`) already:
- ✅ Filters out suggestions (`type == 'bottleneck_suggestion'`)
- ✅ Returns only actual bottlenecks
- ✅ Includes all required fields: `id`, `bottleneck`, `category`, `severity`, `impact`, `created_at`, `source_document`

### 3. Added Debug Logging
Added detailed logging to show:
- Which path is being used (A2A vs Direct vs ChromaDB)
- How many items are retrieved
- Sample bottleneck data
- What items are being skipped (suggestions, tasks, etc.)

## Data Structure

### Actual Bottlenecks (What We Want)
Stored in `project_bottlenecks` collection:
```python
{
    'id': 'bottleneck_project_doc_0_20251210_123456',
    'bottleneck': 'Environmental approval necessary',
    'category': 'Process',
    'severity': 'High',
    'impact': 'Delays project timeline by 2-3 months',
    'created_at': '2025-12-10T12:34:56',
    'source_document': 'doc_id_123',
    # NO 'type' field for actual bottlenecks
}
```

### Bottleneck Suggestions (What We Don't Want)
Also stored in `project_bottlenecks` collection but with `type` field:
```python
{
    'text': 'Consider hiring additional resources',
    'metadata': {
        'type': 'bottleneck_suggestion',  # <-- This is how we filter them out
        'priority': 'Medium',
        'category': 'General'
    }
}
```

## Verification

The correct method to get bottlenecks is:
```python
# From performance_agent/agents/bottleneck_agent.py
def get_project_bottlenecks(self, project_id: str) -> List[Dict]:
    """Get all bottlenecks for a project (excludes suggestions)"""
    results = self.bottlenecks_collection.query(
        query_embeddings=[[0.0] * 384],
        where={"project_id": project_id},
        n_results=1000
    )
    
    bottlenecks = []
    for i, (bottleneck_text, metadata) in enumerate(zip(results['documents'][0], results['metadatas'][0])):
        # Skip suggestions (only include actual bottlenecks)
        if metadata.get('type') == 'bottleneck_suggestion':
            continue
        
        bottlenecks.append({
            'id': results['ids'][0][i],
            'bottleneck': bottleneck_text,
            'category': metadata.get('category', 'General'),
            'severity': metadata.get('severity', 'Medium'),
            'impact': metadata.get('impact', 'Unknown impact'),
            'created_at': metadata.get('created_at', ''),
            'source_document': metadata.get('source_document', '')
        })
    
    return bottlenecks
```

## Expected Terminal Output

### Before Fix:
```
✅ Fetched 27 bottlenecks via A2A
🔍 Enhancing impact for 18 bottlenecks with unknown impact...
```
(Many items were tasks, not bottlenecks)

### After Fix:
```
🔍 Fetching bottlenecks for project a33a827e...
   Orchestrator available: True
   Performance Agent available: True
   Performance ChromaDB available: True
✅ Fetched 9 bottlenecks via direct access (bottleneck_agent)
   Sample bottleneck: {'id': 'bottleneck_...', 'bottleneck': 'Environmental approval necessary', ...}
🔍 Enhancing impact for X bottlenecks with unknown impact...
```
(Only actual bottlenecks, matching Performance Agent count)

## Testing

1. **Check Performance Agent**:
   - Go to Performance Agent dashboard
   - Note the bottleneck count (e.g., 9)

2. **Run First-Time Generation**:
   - Click "First-Time Generation" on Risk Mitigation Dashboard
   - Check terminal output
   - Should show: `✅ Fetched 9 bottlenecks via direct access`

3. **Verify Dashboard**:
   - Bottleneck count should match Performance Agent (9)
   - Bottlenecks should be actual issues, not tasks
   - Examples: "Environmental approval necessary", "Land acquisition delays", etc.

## Date
December 10, 2025

