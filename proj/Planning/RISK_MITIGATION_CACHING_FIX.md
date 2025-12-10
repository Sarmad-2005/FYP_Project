# Risk Mitigation Agent - Caching Fix

## Problem
The Risk Mitigation Agent was making LLM calls every time the dashboard or What If Simulator page was opened, causing:
1. Repeated impact enhancement calls
2. Unnecessary bottleneck ordering
3. Slow page loads
4. Wasted API credits

## Solution
Implemented a **strict caching strategy** where:
1. **First-Time Generation ONLY** triggers LLM calls (manual button click)
2. **All subsequent views** retrieve data from ChromaDB cache
3. **No automatic generation** - user must explicitly click "First-Time Generation"

## Changes Made

### 1. Added `enhanced_bottlenecks` Collection
**File**: `proj/backend/risk_mitigation_agent/chroma_manager.py`

```python
self.collections = {
    'risk_bottlenecks': 'project_risk_bottlenecks',
    'mitigation_suggestions': 'project_risk_mitigation_suggestions',
    'consequences': 'project_risk_consequences',
    'ordering': 'project_risk_ordering',
    'enhanced_bottlenecks': 'project_risk_enhanced_bottlenecks'  # NEW
}
```

- Stores bottlenecks after impact enhancement
- Prevents repeated LLM calls for impact generation

### 2. Added `check_generation_status()` Method
**File**: `proj/backend/risk_mitigation_agent/risk_mitigation_agent.py`

```python
def check_generation_status(self, project_id: str) -> Dict[str, Any]:
    """Check if first-time generation has been run"""
    ordering_data = self.chroma_manager.get_risk_data('ordering', project_id)
    cached_bottlenecks = self.what_if_simulator._get_cached_bottlenecks(project_id)
    
    has_data = bool(ordering_data and cached_bottlenecks)
    
    return {'success': True, 'has_data': has_data, 'project_id': project_id}
```

- Checks if data exists before attempting to display
- Returns `has_data: false` if first-time generation hasn't been run

### 3. Modified `get_what_if_simulator_data()` - RETRIEVAL ONLY
**File**: `proj/backend/risk_mitigation_agent/risk_mitigation_agent.py`

**BEFORE**:
```python
# Fetched bottlenecks from Performance Agent every time
bottlenecks = self.what_if_simulator.fetch_project_bottlenecks(...)
```

**AFTER**:
```python
# Retrieves from cache ONLY
cached_bottlenecks = self.what_if_simulator._get_cached_bottlenecks(project_id)

if not cached_bottlenecks:
    return {'success': False, 'error': 'No data. Run first-time generation.'}

bottlenecks = cached_bottlenecks
```

- **No LLM calls** when viewing the simulator
- Returns error if data not cached
- User must click "First-Time Generation" button

### 4. Modified `get_risk_summary()` - RETRIEVAL ONLY
**File**: `proj/backend/risk_mitigation_agent/risk_mitigation_agent.py`

**BEFORE**:
```python
bottlenecks = self.what_if_simulator.fetch_project_bottlenecks(...)
```

**AFTER**:
```python
cached_bottlenecks = self.what_if_simulator._get_cached_bottlenecks(project_id)

if not cached_bottlenecks:
    return {'success': False, 'error': 'No data. Run first-time generation.', ...}

bottlenecks = cached_bottlenecks
```

- **No LLM calls** when loading dashboard
- Returns error if data not cached

### 5. Updated Dashboard UI
**File**: `proj/templates/risk_mitigation_dashboard.html`

**Added**:
- `check_generation_status` API call before loading data
- Beautiful "No Data" placeholder with "Run First-Time Generation" button
- `runFirstGeneration()` function to trigger first-time analysis

**Flow**:
1. Page loads → checks if data exists
2. If no data → shows placeholder with button
3. User clicks button → runs first-time generation
4. After generation → reloads dashboard with data

### 6. Added API Endpoint
**File**: `proj/app.py`

```python
@app.route('/api/risk_mitigation/check_generation_status/<project_id>', methods=['GET'])
def api_risk_mitigation_check_status(project_id):
    """Check if first-time generation has been run"""
    result = risk_mitigation_agent.check_generation_status(project_id)
    return jsonify(result)
```

## Data Flow

### First-Time Generation (Manual - Button Click)
```
User clicks "First-Time Generation"
    ↓
fetch_project_bottlenecks(use_cache=False)
    ↓
Fetch from Performance Agent
    ↓
Enhance impacts with LLM (18 bottlenecks)
    ↓
Cache enhanced bottlenecks → enhanced_bottlenecks collection
    ↓
Order bottlenecks with LLM
    ↓
Store ordering → ordering collection
    ↓
Generate ALL mitigation suggestions (LLM)
    ↓
Store suggestions → mitigation_suggestions collection
    ↓
Generate ALL consequences (LLM)
    ↓
Store consequences → consequences collection
    ↓
DONE ✅
```

### Subsequent Views (Automatic - No LLM Calls)
```
User opens Dashboard/Simulator
    ↓
check_generation_status()
    ↓
If has_data = false:
    Show "No Data" placeholder
    ↓
If has_data = true:
    Retrieve from enhanced_bottlenecks collection
    ↓
    Retrieve from ordering collection
    ↓
    Generate graph (formatting only, no LLM)
    ↓
    Display ✅
```

### Mitigation/Consequence Views (On-Demand)
```
User clicks node in graph
    ↓
Check mitigation_suggestions collection
    ↓
If found: Display from cache
    ↓
If not found: Should not happen (generated in first-time)
    ↓
Same for consequences
```

## Collections Summary

| Collection | Purpose | Generated When | Retrieved When |
|------------|---------|----------------|----------------|
| `enhanced_bottlenecks` | Bottlenecks with LLM-enhanced impacts | First-time generation | Every dashboard/simulator view |
| `ordering` | Ordered bottleneck IDs | First-time generation | Every simulator view |
| `mitigation_suggestions` | LLM-generated mitigation strategies | First-time generation | On node click |
| `consequences` | LLM-generated consequences | First-time generation | On "Consequences" button click |

## Benefits

1. **No Repeated LLM Calls**: Impact enhancement, ordering, suggestions, and consequences are generated once and cached
2. **Fast Page Loads**: Dashboard and simulator load instantly from cache
3. **Cost Efficient**: Minimal API usage
4. **User Control**: User decides when to generate/refresh data
5. **Clear UX**: Shows placeholder when no data exists

## Testing

To verify the fix:

1. **Open Dashboard** → Should show "No Data" placeholder
2. **Click "First-Time Generation"** → Terminal shows LLM calls (impact enhancement, ordering, suggestions, consequences)
3. **Refresh Dashboard** → Loads instantly from cache, **NO LLM calls in terminal**
4. **Open What If Simulator** → Loads graph from cache, **NO LLM calls**
5. **Click node** → Shows suggestions from cache, **NO LLM calls**
6. **Click "Consequences"** → Shows consequences from cache, **NO LLM calls**

## Terminal Output Comparison

### BEFORE (Every Page Load):
```
🔍 Enhancing impact for 18 bottlenecks with unknown impact...
   ✅ Enhanced impact for: Prioritize architectural design...
   ✅ Enhanced impact for: Regularly review and update...
   [18 LLM calls]
```

### AFTER (First-Time Only):
```
First page load:
📍 Checking for stored ordering...
   ⚠️ No data found. User must run first-time generation.

After button click:
🔍 Enhancing impact for 18 bottlenecks with unknown impact...
   ✅ Enhanced impact for: Prioritize architectural design...
   [18 LLM calls]
✅ Cached 27 enhanced bottlenecks

Subsequent page loads:
📍 Retrieving enhanced bottlenecks from cache...
   ✅ Retrieved 27 cached bottlenecks
   [NO LLM CALLS]
```

## Date
December 10, 2025

