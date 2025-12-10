"""
LangChain LLM Wrapper
Wraps LLMManager to be compatible with LangChain's BaseLLM interface
"""

from typing import Any, List, Mapping, Optional
from langchain.llms.base import LLM
from langchain.callbacks.manager import CallbackManagerForLLMRun


class LLMManagerWrapper(LLM):
    """
    Wrapper to make LLMManager compatible with LangChain
    Translates LangChain calls to LLMManager.simple_chat() calls
    """
    
    llm_manager: Any
    
    def __init__(self, llm_manager):
        """
        Initialize wrapper with LLMManager instance
        
        Args:
            llm_manager: Your existing LLMManager instance
        """
        super().__init__()
        self.llm_manager = llm_manager
    
    @property
    def _llm_type(self) -> str:
        """Return identifier for the LLM type"""
        return "custom_llm_manager"
    
    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        """
        Call the LLM with a prompt
        
        Args:
            prompt: The prompt to send to the LLM
            stop: Optional stop sequences
            run_manager: Optional callback manager
            **kwargs: Additional arguments
            
        Returns:
            The LLM's response as a string
        """
        # Call your existing LLMManager
        try:
            result = self.llm_manager.simple_chat(prompt)
            
            # Handle success/error
            if result.get('success', True):  # Default True for backwards compatibility
                response = result.get('response', '')
                
                # Call callbacks if provided
                if run_manager:
                    run_manager.on_llm_new_token(response)
                
                return response
            else:
                # Handle error from LLMManager
                error_msg = result.get('error', 'Unknown LLM error')
                
                # Check for rate limit errors
                if '429' in error_msg or 'rate limit' in error_msg.lower() or 'quota' in error_msg.lower():
                    raise ValueError("⚠️ API rate limit reached. Please wait a moment and try again with a simpler question.")
                
                return f"Error: {error_msg}"
                
        except Exception as e:
            error_str = str(e)
            # Provide user-friendly messages for common errors
            if '429' in error_str or 'rate limit' in error_str.lower():
                raise ValueError("⚠️ API rate limit reached. Please wait a moment and try again.")
            raise
    
    @property
    def _identifying_params(self) -> Mapping[str, Any]:
        """Get identifying parameters"""
        return {
            "llm_type": self._llm_type,
            "current_llm": self.llm_manager.get_current_llm() if hasattr(self.llm_manager, 'get_current_llm') else 'unknown'
        }

