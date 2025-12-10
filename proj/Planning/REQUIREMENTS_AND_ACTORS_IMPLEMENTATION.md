# Requirements and Actors Implementation Plan

## Overview
Add two new features to Performance Agent:
1. Requirements Agent - extracts project requirements (4th vertical card)
2. Actors Agent - extracts actors/entities/organizations/people who do requirements (horizontal card)

Both follow the same pattern as existing Milestones, Tasks, and Bottlenecks agents.

## Phase 1: ChromaDB Collections Setup

### Step 1.1: Update PerformanceChromaManager
- Add new collections to self.collections dictionary:
  - 'requirements': 'project_requirements'
  - 'requirements_details': 'project_requirements_details'
  - 'actors': 'project_actors'
  - 'actors_details': 'project_actors_details'
- Update _initialize_performance_collections() to create these collections
- Ensure embedding_function is used for all new collections

## Phase 2: Requirements Agent Implementation

### Step 2.1: Create RequirementsAgent Class
- File: backend/performance_agent/agents/requirements_agent.py
- Follow same structure as MilestoneAgent, TaskAgent, BottleneckAgent
- Methods to implement:
  - __init__(chroma_manager=None)
  - extract_requirements_from_document(project_id, document_id, llm_manager, similarity_threshold=0.20)
  - _get_document_embeddings(project_id, document_id)
  - _find_relevant_context(document_embeddings, query_embedding, similarity_threshold)
  - _prepare_context_for_llm(relevant_context)
  - _create_requirements_prompt(context_text, project_id, document_id)
  - _parse_requirements_from_response(response)
  - _store_requirements(project_id, document_id, requirements)
  - _extract_requirements_with_regex(response) - fallback parser

### Step 2.2: Requirements Extraction Prompt
- Query: "requirements specifications needs deliverables features functionality scope"
- LLM prompt should extract:
  - Requirement ID
  - Requirement description
  - Priority/importance
  - Category/type
  - Related documents/sections
  - Dependencies

### Step 2.3: Requirements Storage Format
- Store in project_requirements collection
- Metadata includes: project_id, document_id, requirement_id, priority, category, created_at
- Details stored in project_requirements_details collection (for large text)

## Phase 3: Actors Agent Implementation

### Step 3.1: Create ActorsAgent Class
- File: backend/performance_agent/agents/actors_agent.py
- Follow same structure as other agents
- Methods to implement:
  - __init__(chroma_manager=None)
  - extract_actors_from_document(project_id, document_id, llm_manager, similarity_threshold=0.20)
  - _get_document_embeddings(project_id, document_id)
  - _find_relevant_context(document_embeddings, query_embedding, similarity_threshold)
  - _prepare_context_for_llm(relevant_context)
  - _create_actors_prompt(context_text, project_id, document_id)
  - _parse_actors_from_response(response)
  - _store_actors(project_id, document_id, actors)
  - _extract_actors_with_regex(response) - fallback parser
  - link_actors_to_requirements(project_id) - link actors to requirements they handle

### Step 3.2: Actors Extraction Prompt
- Query: "actors entities organizations people stakeholders responsible parties roles"
- LLM prompt should extract:
  - Actor name/identifier
  - Actor type (person, organization, entity, role)
  - Responsibilities/requirements they handle
  - Contact information if available
  - Role description

### Step 3.3: Actors Storage Format
- Store in project_actors collection
- Metadata includes: project_id, document_id, actor_id, actor_type, role, created_at
- Link to requirements via requirement_ids list in metadata
- Details stored in project_actors_details collection

## Phase 4: Integration with PerformanceAgent

### Step 4.1: Update PerformanceAgent Class
- Import RequirementsAgent and ActorsAgent
- Initialize in __init__:
  - self.requirements_agent = RequirementsAgent(self.chroma_manager)
  - self.actors_agent = ActorsAgent(self.chroma_manager)

### Step 4.2: Update first_time_generation() Method
- Add requirements extraction step (after bottlenecks, before details)
- Add actors extraction step (after requirements)
- Update results dictionary to include:
  - 'requirements': {'success': False, 'count': 0, 'details_count': 0, 'suggestions_count': 0}
  - 'actors': {'success': False, 'count': 0, 'details_count': 0, 'linked_requirements_count': 0}
- Update overall_success logic

### Step 4.3: Update refresh_performance_data() Method
- Add requirements refresh extraction
- Add actors refresh extraction
- Update refresh_result dictionary

## Phase 5: LangGraph Integration

### Step 5.1: Create Extraction Nodes
- File: backend/performance_agent/nodes/extraction_nodes.py
- Add extract_requirements_node(state) function
- Add extract_actors_node(state) function
- Follow same pattern as extract_milestones_node, extract_tasks_node, extract_bottlenecks_node

### Step 5.2: Update First Time Generation Graph
- File: backend/performance_agent/graphs/first_time_generation_graph.py
- Import extract_requirements_node and extract_actors_node
- Add to PerformanceGenerationState:
  - requirements_result: dict
  - actors_result: dict
- Add nodes to workflow:
  - workflow.add_node("extract_requirements", extract_requirements_node)
  - workflow.add_node("extract_actors", extract_actors_node)
- Update edges:
  - workflow.add_edge("extract_bottlenecks", "extract_requirements")
  - workflow.add_edge("extract_requirements", "extract_actors")
  - workflow.add_edge("extract_actors", "extract_details")

### Step 5.3: Update Refresh Graph
- File: backend/performance_agent/graphs/refresh_graph.py
- Update extract_from_new_docs_node to include requirements and actors extraction
- Update update_existing_entities_node to handle requirements and actors updates

### Step 5.4: Update Nodes __init__
- File: backend/performance_agent/nodes/__init__.py
- Export extract_requirements_node and extract_actors_node

## Phase 6: API Endpoints

### Step 6.1: Add Requirements Endpoints
- File: proj/app.py
- Add route: POST /performance_agent/extract_requirements
- Add route: GET /performance_agent/requirements/<project_id>
- Add route: GET /performance_agent/requirement_details/<project_id>/<requirement_id>
- Follow same pattern as extract_milestones, extract_tasks, extract_bottlenecks

### Step 6.2: Add Actors Endpoints
- File: proj/app.py
- Add route: POST /performance_agent/extract_actors
- Add route: GET /performance_agent/actors/<project_id>
- Add route: GET /performance_agent/actor_details/<project_id>/<actor_id>
- Add route: POST /performance_agent/link_actors_to_requirements/<project_id>

### Step 6.3: Update Gateway Integration
- Ensure all new endpoints work through API Gateway
- Add fallback functions for direct agent calls

## Phase 7: UI Implementation

### Step 7.1: Update Performance Dashboard Template
- File: proj/templates/performance_dashboard.html
- Add Requirements Card (4th vertical card) in performance-cards-grid
- Structure same as Milestones, Tasks, Bottlenecks cards
- Add Actors Card (horizontal card below the 4 vertical cards)
- Update CSS classes for new cards

### Step 7.2: Add Requirements Card HTML
- Card structure:
  - Header with icon (fas fa-clipboard-list), title "Requirements", subtitle "Project Specifications"
  - Count badge showing requirements count
  - Body with requirements list/details
- Use same styling pattern as other cards

### Step 7.3: Add Actors Card HTML
- Horizontal card layout (full width)
- Header with icon (fas fa-users), title "Actors & Stakeholders"
- Grid layout showing actors with their roles and linked requirements
- Show actor type badges (Person, Organization, Entity, Role)

### Step 7.4: Update JavaScript
- File: proj/static/js/performance-agent.js
- Add loadRequirementsData() function
- Add loadActorsData() function
- Add renderRequirementsCard() function
- Add renderActorsCard() function
- Update refreshPerformanceData() to include requirements and actors
- Update generatePerformanceAnalysis() to trigger requirements and actors extraction

### Step 7.5: Update CSS
- File: proj/static/css/performance-agent.css
- Add styles for requirements-card
- Add styles for actors-card
- Add horizontal card layout styles
- Ensure responsive design

## Phase 8: Data Interface Updates

### Step 8.1: Update PerformanceDataInterface
- File: backend/performance_agent/data_interface.py
- Add methods:
  - get_requirements(project_id)
  - get_requirement_details(project_id, requirement_id)
  - get_actors(project_id)
  - get_actor_details(project_id, actor_id)
  - get_actors_by_requirement(project_id, requirement_id)
  - get_requirements_by_actor(project_id, actor_id)

## Phase 9: Service Layer Updates

### Step 9.1: Update Performance Service
- File: proj/services/performance-service/main.py
- Ensure all new endpoints are accessible through microservice
- Test gateway routing

## Phase 10: Testing and Validation

### Step 10.1: Unit Tests
- Test RequirementsAgent extraction
- Test ActorsAgent extraction
- Test ChromaDB storage and retrieval
- Test linking actors to requirements

### Step 10.2: Integration Tests
- Test first_time_generation with requirements and actors
- Test refresh with requirements and actors
- Test UI rendering
- Test API endpoints

### Step 10.3: End-to-End Tests
- Upload document
- Generate performance analysis
- Verify requirements and actors appear in UI
- Test refresh functionality

## Implementation Order

1. Phase 1: ChromaDB Collections Setup
2. Phase 2: Requirements Agent Implementation
3. Phase 3: Actors Agent Implementation
4. Phase 4: Integration with PerformanceAgent
5. Phase 5: LangGraph Integration
6. Phase 6: API Endpoints
7. Phase 7: UI Implementation
8. Phase 8: Data Interface Updates
9. Phase 9: Service Layer Updates
10. Phase 10: Testing and Validation

## Key Design Decisions

- Requirements follow same extraction pattern as milestones/tasks/bottlenecks
- Actors extraction happens after requirements to enable linking
- Both use same ChromaDB structure with main collection and details collection
- UI maintains consistency with existing 3-card layout, adding 4th card and horizontal actors card
- All refresh routines updated to include new entities
- LangGraph workflows updated to include new extraction nodes
