"""
API Gateway Client
Helper module for proxying requests through API Gateway with fallback to direct calls.
"""

import os
import requests
from typing import Dict, Any, Optional, Tuple


class GatewayClient:
    """Client for making requests through API Gateway with fallback support."""
    
    def __init__(self, gateway_url: str = None, use_gateway: bool = True):
        """
        Initialize Gateway Client.
        
        Args:
            gateway_url: API Gateway URL (defaults to env var or localhost:5000)
            use_gateway: Whether to use gateway (defaults to env var or True)
        """
        self.gateway_url = gateway_url or os.getenv('GATEWAY_URL', 'http://localhost:5000')
        self.use_gateway = use_gateway if isinstance(use_gateway, bool) else os.getenv('USE_GATEWAY', 'true').lower() == 'true'
        self._available = None
    
    def is_available(self) -> bool:
        """Check if API Gateway is available."""
        if not self.use_gateway:
            return False
        
        if self._available is None:
            try:
                response = requests.get(f"{self.gateway_url}/health", timeout=2)
                self._available = response.status_code == 200
            except:
                self._available = False
        
        return self._available
    
    def request(self, path: str, method: str = 'GET', data: Any = None, 
                files: Dict = None, params: Dict = None, 
                fallback_func: callable = None) -> Tuple[Dict, int]:
        """
        Make request through API Gateway or use fallback.
        
        Args:
            path: API path (e.g., '/financial_agent/status/project123')
            method: HTTP method
            data: Request data (dict for JSON, or form data)
            files: Files for multipart/form-data
            params: Query parameters
            fallback_func: Function to call if gateway unavailable
        
        Returns:
            Tuple of (response_data, status_code)
        """
        # Try gateway if enabled and available
        if self.use_gateway and self.is_available():
            try:
                url = f"{self.gateway_url}{path}"
                
                if method == 'GET':
                    response = requests.get(url, params=params, timeout=30)
                elif method == 'POST':
                    if files:
                        response = requests.post(url, data=data, files=files, timeout=30)
                    else:
                        response = requests.post(url, json=data, timeout=30)
                elif method == 'PUT':
                    response = requests.put(url, json=data, timeout=30)
                elif method == 'DELETE':
                    response = requests.delete(url, timeout=30)
                else:
                    return {'error': f'Unsupported method: {method}'}, 405
                
                try:
                    return response.json(), response.status_code
                except:
                    return {'error': 'Invalid JSON response'}, 500
                    
            except requests.exceptions.ConnectionError:
                # Gateway unavailable, use fallback
                pass
            except Exception as e:
                # Other error, use fallback
                print(f"⚠️ Gateway request failed: {e}, using fallback")
        
        # Use fallback function if provided
        if fallback_func:
            try:
                result = fallback_func()
                if isinstance(result, tuple):
                    return result
                else:
                    return result, 200
            except Exception as e:
                return {'error': f'Fallback failed: {str(e)}'}, 500
        
        # No fallback, return error
        return {'error': 'API Gateway unavailable and no fallback provided'}, 503


# Global instance
_gateway_client = None

def get_gateway_client() -> GatewayClient:
    """Get or create global gateway client instance."""
    global _gateway_client
    if _gateway_client is None:
        _gateway_client = GatewayClient()
    return _gateway_client
