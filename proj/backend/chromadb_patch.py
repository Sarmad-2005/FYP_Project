"""
Patch chromadb to use sentence-transformers instead of onnxruntime
This MUST be imported before any chromadb imports
"""
import os
os.environ['CHROMA_DISABLE_ONNXRUNTIME'] = '1'

# Patch DefaultEmbeddingFunction BEFORE chromadb.api.models.Collection is imported
# The Collection class evaluates DefaultEmbeddingFunction() at class definition time
import chromadb.utils.embedding_functions as ef_module

_original_default = ef_module.DefaultEmbeddingFunction

def _patched_default_embedding():
    """Use sentence-transformers instead of onnxruntime"""
    from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
    return SentenceTransformerEmbeddingFunction(model_name='all-MiniLM-L6-v2')

# Replace the function
ef_module.DefaultEmbeddingFunction = _patched_default_embedding

# Now we can safely import chromadb
import chromadb
