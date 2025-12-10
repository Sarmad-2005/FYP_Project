# Performance Agent Functionality Report

## Overview
This report details the two main functionalities of the Performance Agent system:
1. **First-Time Generation** - Initial analysis when a project's first document is uploaded
2. **12-Hour Schedule** - Automated updates and maintenance

---

## 🚀 First-Time Generation

### **When It Triggers**
- ✅ When the **first document** of a project is uploaded
- ✅ User clicks "Generate Performance Analysis" button
- ✅ Called via `/performance_agent/first_generation` API endpoint

### **What It Does (Step-by-Step)**

#### **1. Extract Milestones** 📋
- **Input**: Document content + project context
- **Process**: 
  - Query ChromaDB for relevant document chunks (similarity > 0.20)
  - Send context to LLM with prompt: "Extract project milestones in bullet points"
  - Parse LLM response into structured milestone data
- **Output**: List of milestones with metadata
- **Storage**: ChromaDB collection `project_milestones`

#### **2. Extract Tasks** ✅
- **Input**: Document content + project context  
- **Process**:
  - Query ChromaDB for relevant document chunks (similarity > 0.20)
  - Send context to LLM with prompt: "Extract project tasks in bullet points"
  - Parse LLM response into structured task data
- **Output**: List of tasks with metadata
- **Storage**: ChromaDB collection `project_tasks`

#### **3. Extract Bottlenecks** ⚠️
- **Input**: Document content + project context
- **Process**:
  - Query ChromaDB for relevant document chunks (similarity > 0.20)
  - Send context to LLM with prompt: "Extract project bottlenecks in bullet points"
  - Parse LLM response into structured bottleneck data
- **Output**: List of bottlenecks with metadata
- **Storage**: ChromaDB collection `project_bottlenecks`

#### **4. Extract Milestone Details** 🔍
- **For Each Milestone**:
  - Query ChromaDB for similar milestones across all project documents
  - Send context to LLM with prompt: "Provide detailed information about this milestone"
  - Parse detailed response
  - **Storage**: Append details to milestone metadata in ChromaDB

#### **5. Extract Task Details & Completion Analysis** 📊
- **For Each Task**:
  - Query ChromaDB for similar tasks across all project documents
  - Send context to LLM with prompt: "Provide detailed information about this task"
  - **Completion Status**: Analyze task completion against each document
  - **Storage**: Append details and completion status to task metadata

#### **6. Extract Bottleneck Details** 🔍
- **For Each Bottleneck**:
  - Query ChromaDB for similar bottlenecks across all project documents
  - Send context to LLM with prompt: "Provide detailed information about this bottleneck"
  - Parse detailed response
  - **Storage**: Append details to bottleneck metadata in ChromaDB

#### **7. Generate Suggestions** 💡
- **Milestone Suggestions**: AI-generated recommendations for milestone optimization
- **Task Suggestions**: AI-generated recommendations for task management
- **Bottleneck Suggestions**: AI-generated recommendations for bottleneck resolution
- **Storage**: ChromaDB collection `project_suggestions`

#### **8. Calculate Completion Score** 📈
- **Formula**: `(Completed Tasks / Total Tasks) * 100`
- **Purpose**: Overall project progress indicator
- **Storage**: Included in results JSON

#### **9. Save Results** 💾
- **ChromaDB**: All extracted data, details, and suggestions
- **JSON File**: Summary statistics and metrics
- **Location**: `data/performance/{project_id}_results.json`

### **First-Time Generation Output**
```json
{
  "project_id": "proj_123",
  "document_id": "doc_456", 
  "timestamp": "2024-01-15T10:30:00",
  "milestones": {
    "success": true,
    "count": 5,
    "details_count": 5,
    "suggestions_count": 3
  },
  "tasks": {
    "success": true,
    "count": 12,
    "details_count": 12,
    "suggestions_count": 8,
    "completion_analysis": true
  },
  "bottlenecks": {
    "success": true,
    "count": 3,
    "details_count": 3,
    "suggestions_count": 3
  },
  "completion_score": 75.0,
  "overall_success": true
}
```

---

## ⏰ 12-Hour Schedule Functionality

### **When It Runs**
- ✅ **Every 12 hours** automatically
- ✅ **Manual trigger** via `/performance_agent/schedule_updates` endpoint
- ✅ **Background process** using Python threading

### **What It Does (Step-by-Step)**

#### **1. Check for New Documents** 📄
- **Process**: Scan all projects for newly uploaded documents
- **Detection**: Compare document timestamps with last update time
- **Action**: Identify projects with new documents since last run

#### **2. Update Milestones** 📋
- **For Projects with New Documents**:
  - **Extract New Milestones**: Run milestone extraction on new documents
  - **Update Existing Milestones**: Append details from new documents to existing milestones
  - **Cross-Document Analysis**: Ensure all milestone details span across all project documents
  - **Storage**: Update ChromaDB with new milestone data

#### **3. Update Tasks** ✅
- **For Projects with New Documents**:
  - **Extract New Tasks**: Run task extraction on new documents
  - **Update Existing Tasks**: Append details from new documents to existing tasks
  - **Cross-Document Analysis**: Ensure all task details span across all project documents
  - **Storage**: Update ChromaDB with new task data

#### **4. Update Bottlenecks** ⚠️
- **For Projects with New Documents**:
  - **Extract New Bottlenecks**: Run bottleneck extraction on new documents
  - **Update Existing Bottlenecks**: Append details from new documents to existing bottlenecks
  - **Cross-Document Analysis**: Ensure all bottleneck details span across all project documents
  - **Storage**: Update ChromaDB with new bottleneck data

#### **5. Recalculate Task Completion Status** 📊
- **For All Projects**:
  - **Per-Document Analysis**: Determine completion status for each task against each document
  - **Final Verdict**: Calculate overall completion status (completed if >50% documents show completion)
  - **Update Status**: Store final completion verdict in ChromaDB
  - **Formula**: `Final Status = (Completed Documents / Total Documents) > 0.5`

#### **6. Generate Updated Suggestions** 💡
- **For Projects with New Documents**:
  - **Milestone Suggestions**: Generate new suggestions based on updated milestone data
  - **Task Suggestions**: Generate new suggestions based on updated task data
  - **Bottleneck Suggestions**: Generate new suggestions based on updated bottleneck data
  - **Storage**: Update ChromaDB with new suggestions

#### **7. Update Completion Scores** 📈
- **For All Projects**:
  - **Recalculate**: Update completion scores based on latest task statuses
  - **Formula**: `(Completed Tasks / Total Tasks) * 100`
  - **Storage**: Update results JSON with new scores

#### **8. Log Schedule Results** 📝
- **Success Tracking**: Log which projects were updated successfully
- **Error Handling**: Log any failures or issues during updates
- **Performance Metrics**: Track processing time and resource usage

### **12-Hour Schedule Logic Flow**
```
Every 12 Hours:
├── Check All Projects
│   ├── Identify New Documents
│   └── For Each Project with New Documents:
│       ├── Extract New Milestones + Details
│       ├── Extract New Tasks + Details  
│       ├── Extract New Bottlenecks + Details
│       └── Update Existing Items with New Details
├── For All Projects:
│   ├── Recalculate Task Completion Status
│   ├── Generate Updated Suggestions
│   └── Update Completion Scores
└── Log Results
```

### **Key Features of 12-Hour Schedule**

#### **Incremental Updates** 🔄
- Only processes projects with new documents
- Appends new details to existing items
- Maintains historical data integrity

#### **Cross-Document Analysis** 🔍
- Ensures all details span across all project documents
- Maintains comprehensive context for each item
- Updates existing items with new document insights

#### **Completion Status Tracking** ✅
- Tracks completion status per document per task
- Calculates final verdict based on majority completion
- Updates completion scores automatically

#### **Error Handling** 🛡️
- Graceful handling of LLM failures
- Retry mechanisms for failed operations
- Comprehensive logging of issues

---

## 🔧 Technical Implementation

### **ChromaDB Collections Used**
- `project_milestones` - Milestone data and details
- `project_tasks` - Task data, details, and completion status
- `project_bottlenecks` - Bottleneck data and details
- `project_suggestions` - AI-generated suggestions

### **API Endpoints**
- `POST /performance_agent/first_generation` - Trigger first-time generation
- `POST /performance_agent/schedule_updates` - Manual schedule trigger
- `GET /performance_agent/status/{project_id}` - Get project status
- `GET /performance_agent/suggestions/{project_id}` - Get suggestions

### **Data Flow**
```
Document Upload → First-Time Generation → ChromaDB Storage → JSON Summary
                ↓
            12-Hour Schedule → Incremental Updates → ChromaDB Updates → JSON Updates
```

---

## 📊 Benefits

### **First-Time Generation Benefits**
- ✅ **Comprehensive Analysis**: Complete project overview from single document
- ✅ **AI-Powered Insights**: LLM-generated details and suggestions
- ✅ **Structured Data**: Organized storage for easy retrieval
- ✅ **Progress Tracking**: Initial completion score calculation

### **12-Hour Schedule Benefits**
- ✅ **Automatic Updates**: No manual intervention required
- ✅ **Incremental Learning**: System improves with each new document
- ✅ **Cross-Document Intelligence**: Details span across all project documents
- ✅ **Real-Time Progress**: Updated completion scores and statuses
- ✅ **Continuous Optimization**: Regular suggestion updates

---

## 🎯 Summary

The Performance Agent system provides:
1. **Initial Analysis** - Comprehensive first-time generation when projects start
2. **Continuous Learning** - Automated 12-hour updates as projects evolve
3. **Cross-Document Intelligence** - Details and insights span across all project documents
4. **AI-Powered Insights** - LLM-generated suggestions and analysis
5. **Progress Tracking** - Real-time completion scores and status updates

This creates a **self-improving system** that gets smarter with each new document and provides ongoing project intelligence without manual intervention.
