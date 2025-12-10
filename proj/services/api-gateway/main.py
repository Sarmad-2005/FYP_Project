"""
API Gateway Service
Flask service that routes requests to appropriate microservices.
"""

import sys
import os
from flask import Flask, request, jsonify, Response
import requests
import logging

# Try to import CORS, make it optional
try:
    from flask_cors import CORS
    CORS_AVAILABLE = True
except ImportError:
    CORS_AVAILABLE = False
    logging.warning("flask-cors not available, CORS disabled")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
if CORS_AVAILABLE:
    CORS(app)  # Enable CORS for all routes

# Service URLs configuration
SERVICE_URLS = {
    'financial': os.getenv('FINANCIAL_SERVICE_URL', 'http://localhost:8001'),
    'performance': os.getenv('PERFORMANCE_SERVICE_URL', 'http://localhost:8002'),
    'csv_analysis': os.getenv('CSV_ANALYSIS_SERVICE_URL', 'http://localhost:8003'),
    'a2a_router': os.getenv('A2A_ROUTER_SERVICE_URL', 'http://localhost:8004'),
    'scheduler': os.getenv('SCHEDULER_SERVICE_URL', 'http://localhost:8005')
}

# Route mappings: gateway path prefix -> (service_name, service_path_prefix)
ROUTE_MAPPINGS = {
    '/financial_agent': ('financial', ''),
    '/performance_agent': ('performance', ''),
    '/csv_analysis': ('csv_analysis', ''),
    '/a2a_router': ('a2a_router', ''),
    '/scheduler': ('scheduler', '')
}


def forward_request(service_name: str, path: str, method: str, headers: dict, data=None, params=None, files=None):
    """
    Forward a request to a backend service.
    
    Args:
        service_name: Name of the service (key in SERVICE_URLS)
        path: Path to append to service URL
        method: HTTP method
        headers: Request headers (excluding host)
        data: Request body data
        params: Query parameters
        files: Files for multipart/form-data
    
    Returns:
        Response tuple (status_code, headers, content) or None if service unavailable
    """
    if service_name not in SERVICE_URLS:
        return None
    
    service_url = SERVICE_URLS[service_name]
    target_url = f"{service_url}{path}"
    
    # Filter out headers that shouldn't be forwarded
    forward_headers = {k: v for k, v in headers.items() 
                      if k.lower() not in ['host', 'content-length', 'connection']}
    
    try:
        if files:
            # Handle multipart/form-data
            response = requests.request(
                method=method,
                url=target_url,
                headers=forward_headers,
                params=params,
                files=files,
                data=data,
                timeout=30
            )
        else:
            # Handle JSON or other data
            response = requests.request(
                method=method,
                url=target_url,
                headers=forward_headers,
                params=params,
                json=data if data and method in ['POST', 'PUT', 'PATCH'] else None,
                data=data if method not in ['POST', 'PUT', 'PATCH'] else None,
                timeout=30
            )
        
        # Get response headers (excluding some that shouldn't be forwarded)
        response_headers = {k: v for k, v in response.headers.items() 
                          if k.lower() not in ['content-encoding', 'transfer-encoding', 'connection']}
        
        return (response.status_code, response_headers, response.content)
    
    except requests.exceptions.ConnectionError:
        logger.error(f"Service {service_name} at {target_url} is not available")
        return None
    except requests.exceptions.Timeout:
        logger.error(f"Request to {service_name} at {target_url} timed out")
        return None
    except Exception as e:
        logger.error(f"Error forwarding request to {service_name}: {e}")
        return None


def create_route_handler(route_prefix: str, service_name: str, service_path_prefix: str):
    """
    Create a route handler function for a specific route prefix.
    
    Args:
        route_prefix: The prefix to match (e.g., '/financial_agent')
        service_name: Name of the service to forward to
        service_path_prefix: Prefix to add to service path (usually '')
    
    Returns:
        Route handler function
    """
    def route_handler(path=''):
        # Get the remaining path after the route prefix
        remaining_path = request.path[len(route_prefix):]
        if not remaining_path:
            remaining_path = '/'
        
        # Add service path prefix if needed
        target_path = f"{service_path_prefix}{remaining_path}"
        
        # Get query parameters
        params = request.args.to_dict()
        
        # Get request data
        data = None
        files = None
        
        if request.method in ['POST', 'PUT', 'PATCH']:
            if request.is_json:
                data = request.get_json()
            elif request.files:
                files = request.files.to_dict()
                data = request.form.to_dict()
            elif request.form:
                data = request.form.to_dict()
            else:
                data = request.get_data()
        
        # Forward request
        result = forward_request(
            service_name=service_name,
            path=target_path,
            method=request.method,
            headers=dict(request.headers),
            data=data,
            params=params,
            files=files
        )
        
        if result is None:
            return jsonify({
                "error": f"Service {service_name} is not available",
                "service": service_name,
                "path": target_path
            }), 503
        
        status_code, response_headers, content = result
        
        # Create Flask response
        response = Response(
            content,
            status=status_code,
            headers=response_headers
        )
        
        return response
    
    return route_handler


# Register routes
for route_prefix, (service_name, service_path_prefix) in ROUTE_MAPPINGS.items():
    # Create route with catch-all path
    app.add_url_rule(
        f'{route_prefix}/<path:path>',
        f'route_{service_name}',
        create_route_handler(route_prefix, service_name, service_path_prefix),
        methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS']
    )
    
    # Also handle root path for the route prefix
    app.add_url_rule(
        route_prefix,
        f'route_{service_name}_root',
        create_route_handler(route_prefix, service_name, service_path_prefix),
        methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS']
    )
    
    # Handle trailing slash
    app.add_url_rule(
        f'{route_prefix}/',
        f'route_{service_name}_trailing',
        create_route_handler(route_prefix, service_name, service_path_prefix),
        methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS']
    )


@app.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint that checks all backend services.
    Uses shorter timeouts to prevent gateway health check from hanging.
    """
    import threading
    from queue import Queue
    
    service_status = {}
    all_healthy = True
    
    def check_service(service_name, service_url, result_queue):
        """Check a single service and put result in queue."""
        try:
            # Use tuple timeout: (connect_timeout, read_timeout)
            # Very short timeouts to prevent hanging
            response = requests.get(
                f"{service_url}/health", 
                timeout=(0.5, 0.5)  # 0.5s connect, 0.5s read
            )
            result_queue.put({
                'service': service_name,
                'status': 'healthy' if response.status_code == 200 else 'unhealthy',
                'url': service_url,
                'status_code': response.status_code,
                'error': None
            })
        except requests.exceptions.ConnectionError:
            result_queue.put({
                'service': service_name,
                'status': 'unavailable',
                'url': service_url,
                'error': 'Connection refused'
            })
        except (requests.exceptions.Timeout, requests.exceptions.ReadTimeout, requests.exceptions.ConnectTimeout):
            result_queue.put({
                'service': service_name,
                'status': 'timeout',
                'url': service_url,
                'error': 'Request timed out'
            })
        except Exception as e:
            result_queue.put({
                'service': service_name,
                'status': 'error',
                'url': service_url,
                'error': str(e)[:100]
            })
    
    # Check all services in parallel with threading
    result_queue = Queue()
    threads = []
    
    for service_name, service_url in SERVICE_URLS.items():
        thread = threading.Thread(
            target=check_service,
            args=(service_name, service_url, result_queue),
            daemon=True
        )
        thread.start()
        threads.append(thread)
    
    # Wait for all threads with a maximum timeout
    max_wait = 2.0  # Maximum 2 seconds total
    for thread in threads:
        thread.join(timeout=max_wait)
    
    # Collect results
    while not result_queue.empty():
        result = result_queue.get()
        service_name = result['service']
        service_status[service_name] = {
            'status': result['status'],
            'url': result['url']
        }
        if 'status_code' in result:
            service_status[service_name]['status_code'] = result['status_code']
        if result.get('error'):
            service_status[service_name]['error'] = result['error']
        
        if result['status'] != 'healthy':
            all_healthy = False
    
    # Handle any services that didn't respond (threads timed out)
    for service_name, service_url in SERVICE_URLS.items():
        if service_name not in service_status:
            service_status[service_name] = {
                'status': 'timeout',
                'url': service_url,
                'error': 'Health check timed out'
            }
            all_healthy = False
    
    gateway_status = {
        "status": "healthy" if all_healthy else "degraded",
        "service": "api-gateway",
        "port": 5000,
        "services": service_status
    }
    
    # Always return 200 for gateway health - degraded status is in the response
    # This allows the gateway to report its own health even if backend services are down
    return jsonify(gateway_status), 200


@app.route('/', methods=['GET'])
def root():
    """Root endpoint with API information."""
    return jsonify({
        "service": "api-gateway",
        "version": "1.0",
        "port": 5000,
        "routes": {
            "/financial_agent/*": "Financial Service (port 8001)",
            "/performance_agent/*": "Performance Service (port 8002)",
            "/csv_analysis/*": "CSV Analysis Service (port 8003)",
            "/a2a_router/*": "A2A Router Service (port 8004)",
            "/scheduler/*": "Scheduler Service (port 8005)",
            "/health": "Health check for all services"
        }
    }), 200


if __name__ == '__main__':
    logger.info("Starting API Gateway on port 5000")
    logger.info(f"Service URLs: {SERVICE_URLS}")
    # Disable debug mode when running in subprocess (test environment)
    # Use environment variable to control debug mode
    debug_mode = os.getenv('GATEWAY_DEBUG', 'False').lower() == 'true'
    app.run(host='0.0.0.0', port=5000, debug=debug_mode, use_reloader=False)
