# Phase 8 Migration Guide

## Overview

Phase 8 migrates `app.py` routes to use the API Gateway instead of direct agent calls, while maintaining backward compatibility.

## Migration Pattern

### Before (Direct Agent Call)
```python
@app.route('/financial_agent/status/<project_id>')
def get_financial_status(project_id):
    result = financial_agent.get_financial_status(project_id)
    return jsonify(result)
```

### After (Gateway with Fallback)
```python
@app.route('/financial_agent/status/<project_id>')
def get_financial_status(project_id):
    def fallback():
        # Direct agent call (old way) - used if gateway unavailable
        return financial_agent.get_financial_status(project_id)
    
    # Try gateway first, fallback to direct call
    response, status = gateway_client.request(
        f'/financial_agent/status/{project_id}',
        method='GET',
        fallback_func=fallback
    )
    
    return jsonify(response), status
```

## Routes to Update

### Financial Agent Routes
- `/financial_agent/dashboard/<project_id>` → `/financial_agent/dashboard/<project_id>`
- `/financial_agent/first_generation` (POST) → `/financial_agent/first_generation`
- `/financial_agent/status/<project_id>` → `/financial_agent/status/<project_id>`
- `/financial_agent/quick_status/<project_id>` → `/financial_agent/quick_status/<project_id>`
- `/financial_agent/transactions/<project_id>` → `/financial_agent/transactions/<project_id>`
- `/financial_agent/expenses/<project_id>` → `/financial_agent/expenses/<project_id>`
- `/financial_agent/revenue/<project_id>` → `/financial_agent/revenue/<project_id>`
- `/financial_agent/anomalies/<project_id>` → `/financial_agent/anomalies/<project_id>`
- `/financial_agent/export/<project_id>` → `/financial_agent/export/<project_id>`

### Performance Agent Routes
- `/performance_agent/first_generation` (POST) → `/performance_agent/first_generation`
- `/performance_agent/status/<project_id>` → `/performance_agent/status/<project_id>`
- `/performance_agent/quick_status/<project_id>` → `/performance_agent/quick_status/<project_id>`
- `/performance_agent/dashboard/<project_id>` → `/performance_agent/dashboard/<project_id>`
- `/performance_agent/suggestions/<project_id>` → `/performance_agent/suggestions/<project_id>`
- `/performance_agent/export/<project_id>` → `/performance_agent/export/<project_id>`

### CSV Analysis Routes
- `/csv_analysis/<project_id>` → `/csv_analysis/<project_id>`
- `/csv_analysis/upload/<project_id>` (POST) → `/csv_analysis/upload`
- `/csv_analysis/data/<project_id>/<session_id>` → `/csv_analysis/data`
- `/csv_analysis/ask/<project_id>/<session_id>` (POST) → `/csv_analysis/ask`
- `/csv_analysis/export/<project_id>/<session_id>` → `/csv_analysis/export`

## POST Request Example

```python
@app.route('/financial_agent/first_generation', methods=['POST'])
def financial_first_generation():
    def fallback():
        data = request.get_json()
        return financial_agent.first_time_generation(
            data.get('project_id'),
            data.get('document_id')
        )
    
    response, status = gateway_client.request(
        '/financial_agent/first_generation',
        method='POST',
        data=request.get_json(),
        fallback_func=fallback
    )
    
    return jsonify(response), status
```

## File Upload Example

```python
@app.route('/csv_analysis/upload/<project_id>', methods=['POST'])
def csv_upload(project_id):
    def fallback():
        if 'file' not in request.files:
            return {'error': 'No file provided'}, 400
        file = request.files['file']
        return csv_analysis_agent.upload_csv(project_id, file)
    
    response, status = gateway_client.request(
        f'/csv_analysis/upload?project_id={project_id}',
        method='POST',
        files={'file': request.files.get('file')},
        data={'project_id': project_id},
        fallback_func=fallback
    )
    
    return jsonify(response), status
```

## Environment Variables

Set these to control gateway behavior:

```bash
# Enable/disable gateway (default: true)
USE_GATEWAY=true

# Gateway URL (default: http://localhost:5000)
GATEWAY_URL=http://localhost:5000
```

## Testing

1. **With Gateway Running:**
   ```bash
   export USE_GATEWAY=true
   export GATEWAY_URL=http://localhost:5000
   python app.py
   ```

2. **Without Gateway (Fallback Mode):**
   ```bash
   export USE_GATEWAY=false
   python app.py
   ```

## Benefits

- ✅ Automatic fallback if gateway unavailable
- ✅ No breaking changes - old code still works
- ✅ Gradual migration - update routes one at a time
- ✅ Easy testing - toggle gateway on/off
