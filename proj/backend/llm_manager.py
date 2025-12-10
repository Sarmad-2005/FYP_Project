"""
LLM Manager for handling different language models (Mistral B via Ollama, Gemini, and Hugging Face)
"""

import requests
import json
from typing import List, Dict, Any, Optional
import os
import time
from google.generativeai import GenerativeModel
import google.generativeai as genai

class LLMManager:
    """Manager for different LLM providers"""
    
    def __init__(self):
        self.ollama_base_url = "http://localhost:11434"
        self.llm_config_file = "data/llm_config.json"
        #self.gemini_api_key = "AIzaSyCss7j_1JB0TNlzJxvD_j7_YbmMtKI2Evw"
        #self.gemini_api_key = "AIzaSyDyUz_qjmgWOLoFRif5bBNPHSfrg0kQ4ms"
        self.gemini_api_key = "AIzaSyALhWTAX8FY82_-UZTaFk_vC-enRClpO5M"

        self.gemini_model = None
        self.last_gemini_call_time = 0  # Track last Gemini API call time for rate limiting
        
        # Hugging Face Inference API - router chat model (available)
        # Use a widely available router model for reliability
        self.huggingface_model = "meta-llama/Meta-Llama-3-8B-Instruct"  # Router-compatible chat model
        self.huggingface_api_url = "https://router.huggingface.co/v1/chat/completions"
        self.huggingface_api_key = os.getenv("HUGGINGFACE_API_KEY", "")  # Use environment variable
        self.last_huggingface_call_time = 0  # Track last Hugging Face API call time for rate limiting

        # Initialize Gemini
        try:
            genai.configure(api_key=self.gemini_api_key)
            self.gemini_model = GenerativeModel('gemini-2.5-flash-lite')
            print("  ✅ Gemini initialized (using gemini-2.5-flash-lite)")
        except Exception as e:
            print(f"  ⚠️ Failed to initialize Gemini: {e}")
            self.gemini_model = None

        # Load saved LLM selection or choose best available
        self.current_llm = self._load_llm_selection()
    
    def _default_llm(self) -> Optional[str]:
        """Pick the best available LLM based on availability."""
        if self._check_ollama_status() == "available":
            return "mistral"
        if self._gemini_available():
            return "gemini"
        if self._huggingface_available():
            return "huggingface"
        return None

    def _gemini_available(self) -> bool:
        """Return True if Gemini can be used."""
        return self.gemini_model is not None
    
    def _huggingface_available(self) -> bool:
        """Return True if Hugging Face Inference API can be used."""
        # Hugging Face router API requires API key
        return self.huggingface_api_key is not None and len(self.huggingface_api_key) > 0

    def _load_llm_selection(self) -> Optional[str]:
        """Load saved LLM selection from config file, fallback to available."""
        try:
            if os.path.exists(self.llm_config_file):
                with open(self.llm_config_file, 'r') as f:
                    config = json.load(f)
                    selected_llm = config.get('current_llm')
                    if selected_llm:
                        # Validate availability
                        if selected_llm == "gemini" and not self._gemini_available():
                            print("  ⚠️ Saved LLM is Gemini but GEMINI_API_KEY is missing/invalid; falling back")
                            return self._default_llm()
                        if selected_llm == "mistral" and self._check_ollama_status() != "available":
                            print("  ⚠️ Saved LLM is Mistral but Ollama is unavailable; falling back")
                            return self._default_llm()
                        if selected_llm == "huggingface" and not self._huggingface_available():
                            print("  ⚠️ Saved LLM is Hugging Face but API is unavailable; falling back")
                            return self._default_llm()
                        print(f"  ℹ️ Loaded LLM selection: {selected_llm}")
                        return selected_llm
            # No config file or no valid selection; pick best available
            fallback = self._default_llm()
            if fallback:
                print(f"  ℹ️ No LLM config found; defaulting to {fallback}")
            else:
                print("  ❌ No LLM available. Configure GEMINI_API_KEY, start Ollama with Mistral, or set HUGGINGFACE_API_KEY.")
            return fallback
        except Exception as e:
            print(f"  ⚠️ Error loading LLM config: {e}")
            return self._default_llm()
    
    def _save_llm_selection(self, llm_name: str) -> bool:
        """Save LLM selection to config file"""
        try:
            # Ensure data directory exists
            os.makedirs(os.path.dirname(self.llm_config_file), exist_ok=True)
            
            with open(self.llm_config_file, 'w') as f:
                json.dump({'current_llm': llm_name}, f, indent=2)
            return True
        except Exception as e:
            print(f"  ⚠️ Error saving LLM config: {e}")
            return False
    
    def set_llm(self, llm_name: str) -> bool:
        """Set the current LLM provider - can only be called from dashboard"""
        print(f"  🔄 set_llm called with: {llm_name}")
        if llm_name == "mistral":
            if self._check_ollama_status() != "available":
                print("  ❌ Mistral not available (Ollama not running/model missing)")
                return False
        elif llm_name == "gemini":
            if not self._gemini_available():
                print("  ❌ Gemini not available (missing or invalid GEMINI_API_KEY)")
                return False
        elif llm_name == "huggingface":
            if not self._huggingface_available():
                print("  ❌ Hugging Face not available")
                return False
        else:
            print(f"  ❌ Invalid LLM name: {llm_name}")
            return False

        self.current_llm = llm_name
        print(f"     → LLM updated in memory: {self.current_llm}")
        save_success = self._save_llm_selection(llm_name)  # Persist selection
        if save_success:
            print(f"     ✅ LLM saved to config file: {llm_name}")
        else:
            print(f"     ⚠️ LLM set in memory but save failed: {llm_name}")
        return True
    
    def get_current_llm(self) -> str:
        """Get the current LLM provider"""
        return self.current_llm
    
    def is_llm_set(self) -> bool:
        """Check if LLM has been set and is available"""
        if self.current_llm == "gemini":
            return self._gemini_available()
        if self.current_llm == "mistral":
            return self._check_ollama_status() == "available"
        if self.current_llm == "huggingface":
            return self._huggingface_available()
        return False
    
    def get_available_llms(self) -> List[Dict[str, str]]:
        """Get list of available LLM providers"""
        return [
            {
                "name": "mistral",
                "display_name": "Mistral B (Ollama)",
                "description": "Local Mistral B model via Ollama",
                "status": self._check_ollama_status()
            },
            {
                "name": "gemini",
                "display_name": "Google Gemini Flash Lite",
                "description": "Google's cost-efficient Gemini 2.5 Flash-Lite model",
                "status": "available" if self._gemini_available() else "api_key_missing"
            },
            {
                "name": "huggingface",
                "display_name": "Hugging Face Llama-3-8B",
                "description": "Meta-Llama-3-8B-Instruct via Hugging Face Router API",
                "status": "available" if self._huggingface_available() else "api_key_missing"
            }
        ]
    
    def _check_ollama_status(self) -> str:
        """Check if Ollama is running and Mistral model is available"""
        try:
            response = requests.get(f"{self.ollama_base_url}/api/tags", timeout=30)
            if response.status_code == 200:
                models = response.json().get("models", [])
                mistral_models = [m for m in models if "mistral" in m.get("name", "").lower()]
                return "available" if mistral_models else "model_not_found"
            return "unavailable"
        except:
            return "unavailable"
    
    def chat_with_context(self, query: str, context_chunks: List[Dict], project_id: str, document_id: str) -> Dict[str, Any]:
        """Chat with LLM using context from document chunks"""
        try:
            # Check if LLM is set
            if not self.is_llm_set():
                fallback = self._default_llm()
                if fallback:
                    self.current_llm = fallback
                    print(f"  ℹ️ Auto-selected LLM: {fallback}")
                else:
                    return {"error": "No LLM available. Set GEMINI_API_KEY, run Ollama with Mistral, or set HUGGINGFACE_API_KEY for Hugging Face."}
            
            # Prepare context
            context_text = self._prepare_context(context_chunks)
            
            # Create prompt
            prompt = self._create_prompt(query, context_text, project_id, document_id)
            
            if self.current_llm == "mistral":
                return self._chat_with_mistral(prompt)
            elif self.current_llm == "gemini":
                return self._chat_with_gemini(prompt)
            elif self.current_llm == "huggingface":
                return self._chat_with_huggingface(prompt)
            else:
                return {"error": "Invalid LLM selected"}
                
        except Exception as e:
            return {"error": f"Error in chat: {str(e)}"}
    
    def _prepare_context(self, context_chunks: List[Dict]) -> str:
        """Prepare context from document chunks"""
        context_parts = []
        
        for i, chunk in enumerate(context_chunks):
            chunk_type = chunk.get('metadata', {}).get('type', 'unknown')
            content = chunk.get('content', '')
            
            if chunk_type == 'table':
                context_parts.append(f"[Table {i+1}]\n{content}")
            else:
                context_parts.append(f"[Text {i+1}]\n{content}")
        
        return "\n\n".join(context_parts)
    
    def _create_prompt(self, query: str, context: str, project_id: str, document_id: str) -> str:
        """Create a comprehensive prompt for the LLM"""
        return f"""You are an AI assistant helping with document analysis and question answering. 
You have access to the following context from a document in project '{project_id}', document '{document_id}':

CONTEXT:
{context}

USER QUESTION: {query}

Please provide a helpful, accurate response based on the context provided. If the context doesn't contain enough information to answer the question, please say so clearly.

Response:"""
    
    def _chat_with_mistral(self, prompt: str) -> Dict[str, Any]:
        """Chat with Mistral B via Ollama"""
        try:
            payload = {
                "model": "mistral:7b-instruct-q4_0",
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "max_tokens": 20000  # Increased to 20k for comprehensive extraction
                }
            }
            
            response = requests.post(
                f"{self.ollama_base_url}/api/generate",
                json=payload
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    "response": result.get("response", ""),
                    "model": "mistral:7b-instruct-q4_0",
                    "success": True
                }
            else:
                return {
                    "error": f"Ollama API error: {response.status_code}",
                    "success": False
                }
                
        except requests.exceptions.ConnectionError:
            return {
                "error": "Cannot connect to Ollama. Please ensure Ollama is running.",
                "success": False
            }
        except Exception as e:
            return {
                "error": f"Mistral API error: {str(e)}",
                "success": False
            }
    
    def _chat_with_gemini(self, prompt: str) -> Dict[str, Any]:
        """Chat with Google Gemini Flash"""
        try:
            if not self._gemini_available():
                return {
                    "error": "Gemini unavailable. Set GEMINI_API_KEY and restart.",
                    "success": False
                }
            
            # Rate limiting: 15 second delay between Gemini API calls
            current_time = time.time()
            time_since_last_call = current_time - self.last_gemini_call_time
            if time_since_last_call < 15:
                delay_needed = 15 - time_since_last_call
                print(f"  ⏳ Rate limiting: waiting {delay_needed:.1f} seconds before Gemini API call...")
                time.sleep(delay_needed)
            
            self.last_gemini_call_time = time.time()
            
            # Configure generation parameters for better performance
            generation_config = {
                "temperature": 0.7,
                "top_p": 0.9,
                "top_k": 40,
                "max_output_tokens": 20000,  # Increased to 20k for comprehensive extraction
            }
            
            response = self.gemini_model.generate_content(
                prompt,
                generation_config=generation_config
            )
            
            if response.text:
                return {
                    "response": response.text,
                    "model": "gemini-2.5-flash-lite",
                    "success": True
                }
            else:
                return {
                    "error": "Empty response from Gemini",
                    "success": False
                }
            
        except Exception as e:
            error_msg = str(e)
            error_type = type(e).__name__
            
            # Log full error for debugging
            print(f"   ❌ Gemini API Exception: {error_type}: {error_msg}")
            
            if "quota" in error_msg.lower() or "429" in error_msg or "rate limit" in error_msg.lower() or "ResourceExhausted" in error_type:
                # Try to extract retry delay from error message
                retry_delay = None
                if "retry in" in error_msg.lower() or "retry_delay" in error_msg.lower():
                    import re
                    # Look for "retry in X.XXs" or "seconds: XX"
                    delay_match = re.search(r'retry in ([\d.]+)s', error_msg.lower())
                    if not delay_match:
                        delay_match = re.search(r'seconds:\s*(\d+)', error_msg.lower())
                    if delay_match:
                        retry_delay = float(delay_match.group(1))
                        print(f"   ⏳ Gemini suggests retrying in {retry_delay:.1f} seconds")
                
                return {
                    "error": f"Gemini API quota/rate limit exceeded. {'Retry suggested in ' + str(int(retry_delay)) + ' seconds. ' if retry_delay else ''}Full error: {error_msg[:200]}. Try again later or use Mistral/Ollama.",
                    "success": False,
                    "retry_delay": retry_delay
                }
            elif "api_key" in error_msg.lower() or "403" in error_msg:
                return {
                    "error": f"Invalid Gemini API key or access denied. Full error: {error_msg}",
                    "success": False
                }
            else:
                return {
                    "error": f"Gemini API error ({error_type}): {error_msg}",
                    "success": False
                }
    
    def _chat_with_huggingface(self, prompt: str) -> Dict[str, Any]:
        """Chat with Mistral-7B via Hugging Face Router API (OpenAI-compatible)"""
        try:
            if not self._huggingface_available():
                return {
                    "error": "Hugging Face API key required. Set HUGGINGFACE_API_KEY or HF_TOKEN environment variable.",
                    "success": False
                }
            
            # Rate limiting: 2 second delay between Hugging Face API calls
            current_time = time.time()
            time_since_last_call = current_time - self.last_huggingface_call_time
            if time_since_last_call < 2:
                delay_needed = 2 - time_since_last_call
                print(f"  ⏳ Rate limiting: waiting {delay_needed:.1f} seconds before Hugging Face API call...")
                time.sleep(delay_needed)
            
            self.last_huggingface_call_time = time.time()
            
            # Prepare headers with required API key
            headers = {
                "Authorization": f"Bearer {self.huggingface_api_key}",
                "Content-Type": "application/json"
            }
            
            # OpenAI-compatible payload format for router API
            payload = {
                "model": self.huggingface_model,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.7,
                # Router limit is <=8192; keep headroom for prompt tokens (~1k); use 4000
                "max_tokens": 4000
            }
            
            response = requests.post(
                self.huggingface_api_url,
                headers=headers,
                json=payload,
                timeout=120  # 2 minute timeout for large responses
            )
            
            if response.status_code == 200:
                result = response.json()
                # OpenAI-compatible format: {"choices": [{"message": {"content": "..."}}]}
                if "choices" in result and len(result["choices"]) > 0:
                    generated_text = result["choices"][0].get("message", {}).get("content", "")
                    if generated_text:
                        return {
                            "response": generated_text,
                            "model": self.huggingface_model,
                            "success": True
                        }
                
                return {
                    "error": f"Unexpected response format from Hugging Face: {result}",
                    "success": False
                }
            elif response.status_code == 401:
                return {
                    "error": "Hugging Face API authentication failed. Please check your HUGGINGFACE_API_KEY or HF_TOKEN.",
                    "success": False
                }
            elif response.status_code == 503:
                # Model is loading, wait and retry
                error_msg = response.json().get("error", "Model is loading")
                estimated_time = response.json().get("estimated_time", 10)
                print(f"  ⏳ Hugging Face model loading, estimated wait: {estimated_time}s")
                return {
                    "error": f"Hugging Face model is loading. Please retry in {estimated_time} seconds.",
                    "success": False,
                    "retry_delay": estimated_time
                }
            else:
                error_msg = response.text
                try:
                    error_json = response.json()
                    error_msg = error_json.get("error", error_json.get("message", error_msg))
                except:
                    pass
                return {
                    "error": f"Hugging Face API error ({response.status_code}): {error_msg}",
                    "success": False
                }
                
        except requests.exceptions.Timeout:
            return {
                "error": "Hugging Face API request timed out. The model may be processing a large request.",
                "success": False
            }
        except requests.exceptions.ConnectionError:
            return {
                "error": "Cannot connect to Hugging Face API. Please check your internet connection.",
                "success": False
            }
        except Exception as e:
            return {
                "error": f"Hugging Face API error: {str(e)}",
                "success": False
            }
    
    def simple_chat(self, query: str) -> Dict[str, Any]:
        """Simple chat without context (for testing)"""
        try:
            # Check if LLM is set
            if not self.is_llm_set():
                return {"error": "No LLM selected. Please select an AI model from the dashboard first."}
            
            if self.current_llm == "mistral":
                return self._chat_with_mistral(query)
            elif self.current_llm == "gemini":
                return self._chat_with_gemini(query)
            elif self.current_llm == "huggingface":
                return self._chat_with_huggingface(query)
            else:
                return {"error": "Invalid LLM selected"}
                
        except Exception as e:
            return {"error": f"Error in simple chat: {str(e)}"}
