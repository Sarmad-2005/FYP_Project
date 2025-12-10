"""
Function descriptions and parameters for Performance Agent system
"""

# Milestone Extraction Agent
MILESTONE_EXTRACTION_DESCRIPTION = """
Milestone Extraction Agent

Purpose:
Extracts project milestones from a specific document using AI-powered analysis.
Uses ChromaDB embeddings to find relevant content and LLM to identify milestones.

Parameters:
- project_id (str): Unique identifier for the project
- document_id (str): Unique identifier for the document to analyze
- llm_manager: LLM manager instance for AI processing
- similarity_threshold (float): Minimum similarity score for context retrieval (default: 0.20)

Process:
1. Query ChromaDB for embeddings above similarity threshold
2. Send context to LLM with milestone extraction prompt
3. Parse LLM response to extract structured milestones
4. Store milestones in dedicated ChromaDB collection
5. Maintain document source tracking

Returns:
- dict: Success status and extracted milestones count
"""

# Milestone Details Agent
MILESTONE_DETAILS_DESCRIPTION = """
Milestone Details Agent

Purpose:
Extracts detailed information for a specific milestone across all project documents.
Analyzes milestone context and provides comprehensive details.

Parameters:
- project_id (str): Unique identifier for the project
- milestone_text (str): The specific milestone to analyze
- llm_manager: LLM manager instance for AI processing
- similarity_threshold (float): Minimum similarity score for context retrieval (default: 0.20)

Process:
1. Use milestone text as query embedding
2. Search ChromaDB for relevant context above threshold
3. Send context to LLM for detailed analysis
4. Parse structured details from LLM response
5. Store details in ChromaDB with document source tracking

Returns:
- dict: Success status and milestone details
"""

# Task Extraction Agent
TASK_EXTRACTION_DESCRIPTION = """
Task Extraction Agent

Purpose:
Extracts project tasks from documents using AI analysis.
Identifies actionable items and deliverables from project content.

Parameters:
- project_id (str): Unique identifier for the project
- document_id (str): Unique identifier for the document to analyze
- llm_manager: LLM manager instance for AI processing
- similarity_threshold (float): Minimum similarity score for context retrieval (default: 0.20)

Process:
1. Query ChromaDB for task-related embeddings
2. Send context to LLM with task extraction prompt
3. Parse structured tasks from LLM response
4. Store tasks in dedicated ChromaDB collection
5. Maintain document source tracking

Returns:
- dict: Success status and extracted tasks count
"""

# Bottleneck Analysis Agent
BOTTLENECK_ANALYSIS_DESCRIPTION = """
Bottleneck Analysis Agent

Purpose:
Identifies project bottlenecks and constraints from document analysis.
Uses AI to analyze potential issues and risks.

Parameters:
- project_id (str): Unique identifier for the project
- document_id (str): Unique identifier for the document to analyze
- llm_manager: LLM manager instance for AI processing
- similarity_threshold (float): Minimum similarity score for context retrieval (default: 0.20)

Process:
1. Query ChromaDB for bottleneck-related embeddings
2. Send context to LLM with bottleneck analysis prompt
3. Parse structured bottlenecks from LLM response
4. Store bottlenecks in dedicated ChromaDB collection
5. Maintain document source tracking

Returns:
- dict: Success status and extracted bottlenecks count
"""

# Task Completion Status Agent
TASK_COMPLETION_STATUS_DESCRIPTION = """
Task Completion Status Agent

Purpose:
Determines completion status of tasks against specific documents.
Analyzes task progress and completion indicators.

Parameters:
- project_id (str): Unique identifier for the project
- document_id (str): Unique identifier for the document to analyze
- task_text (str): The specific task to analyze
- llm_manager: LLM manager instance for AI processing
- similarity_threshold (float): Minimum similarity score for context retrieval (default: 0.20)

Process:
1. Use task text as query embedding
2. Search ChromaDB for relevant context
3. Send context to LLM for completion analysis
4. Parse completion status (1 for completed, 0 for not completed)
5. Store status in ChromaDB with document source

Returns:
- dict: Success status and completion status (0 or 1)
"""
