"""
Shared Resources Package
Common utilities shared across all microservices.
"""

# Re-export common modules for easy importing
from backend.llm_manager import LLMManager
from backend.embeddings import EmbeddingsManager
from backend.database import DatabaseManager

__all__ = ['LLMManager', 'EmbeddingsManager', 'DatabaseManager']
