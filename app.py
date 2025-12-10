from flask import Flask, render_template, request, jsonify, redirect, url_for, make_response
import uuid
import os
import json
import numpy as np
from datetime import datetime
from threading import Thread, Lock
from backend.database import DatabaseManager
from backend.enhanced_pdf_processor import EnhancedPDFProcessor
from backend.embeddings import EmbeddingsManager
from backend.llm_manager import LLMManager
from backend.performance_agent import PerformanceAgent
from backend.performance_agent.data_interface import PerformanceDataInterface
from backend.financial_agent.financial_agent import FinancialAgent
from backend.financial_agent.data_interface import FinancialDataInterface
from backend.document_agent.document_agent import DocumentAgent
from backend.document_agent.intelligent_doc_agent import IntelligentDocAgent
from backend.csv_analysis_agent.csv_analysis_agent import CSVAnalysisAgent
from backend.orchestrator.orchestrator_agent import OrchestratorAgent
from backend.orchestrator.agent_registry import AgentRegistry
from backend.gateway_client import get_gateway_client

# ===== SSL CERTIFICATE FIX =====
# Fix SSL certificate trust issues for API calls
import ssl
try:
    import certifi
    os.environ['SSL_CERT_FILE'] = certifi.where()
    os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()
    print("✅ SSL certificates configured using certifi")
except ImportError:
    print("⚠️ certifi not found. Run: pip install certifi")
# ================================

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

# Configure Flask to handle NaN/Infinity in JSON
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True
from flask.json.provider import DefaultJSONProvider

class CustomJSONProvider(DefaultJSONProvider):
    """Custom JSON provider that converts NaN to null"""
    def default(self, obj):
        if isinstance(obj, float):
            if np.isnan(obj) or np.isinf(obj):
                return None
        return super().default(obj)

app.json = CustomJSONProvider(app)

# Global processing jobs tracker (for async background processing)
processing_jobs = {}
jobs_lock = Lock()

# Initialize managers
db_manager = DatabaseManager()
pdf_processor = EnhancedPDFProcessor()
embeddings_manager = EmbeddingsManager()
llm_manager = LLMManager()
print(f"🤖 LLM Manager initialized with: {llm_manager.get_current_llm().upper() if llm_manager.get_current_llm() else 'NONE'}")

# Initialize registry first
print("\n🔧 Initializing Orchestrator Agent System...")
agent_registry = AgentRegistry()

# Initialize Performance Agent (without orchestrator dependency)
performance_agent = PerformanceAgent(llm_manager, embeddings_manager, db_manager)

# Register Performance Agent FIRST
perf_interface = PerformanceDataInterface(performance_agent)
agent_registry.register_agent("performance_agent", perf_interface)

# NOW create orchestrator with registered agents
print("🔧 Creating Orchestrator Agent...")
orchestrator = OrchestratorAgent(embeddings_manager, agent_registry)

# Initialize Financial Agent with orchestrator
financial_agent = FinancialAgent(llm_manager, embeddings_manager, db_manager, orchestrator)

# Register Financial Agent
fin_interface = FinancialDataInterface(financial_agent)
agent_registry.register_agent("financial_agent", fin_interface)

# Initialize Resource Agent
from backend.resource_agent.resource_agent import ResourceAgent
resource_agent = ResourceAgent(llm_manager, embeddings_manager, db_manager, orchestrator)

# Initialize Risk Mitigation Agent
from backend.risk_mitigation_agent.risk_mitigation_agent import RiskMitigationAgent
from backend.performance_agent.chroma_manager import PerformanceChromaManager
performance_chroma_manager = PerformanceChromaManager()
risk_mitigation_agent = RiskMitigationAgent(
    llm_manager,
    embeddings_manager,
    db_manager,
    orchestrator=orchestrator,
    performance_agent=performance_agent,
    performance_chroma_manager=performance_chroma_manager
)

# Initialize Document Agents (reuse existing managers; no new Docker image)
doc_agent = DocumentAgent(llm_manager, performance_agent, financial_agent, orchestrator=orchestrator)
intelligent_doc_agent = IntelligentDocAgent(llm_manager, performance_agent, financial_agent, doc_agent.chroma_manager, orchestrator=orchestrator)

# Initialize CSV Analysis Agent
print("🔧 Initializing CSV Analysis Agent...")
csv_analysis_agent = CSVAnalysisAgent(
    llm_manager, 
    fin_interface, 
    financial_agent.anomaly_agent
)
print("✅ CSV Analysis Agent initialized!\n")

# Re-initialize orchestrator embeddings now that all agents are registered
print("🔧 Re-initializing function embeddings with all agents...")
orchestrator._initialize_function_embeddings()

print("✅ Orchestrator Agent System initialized successfully!\n")

# Initialize Gateway Client for API Gateway integration
gateway_client = get_gateway_client()
if gateway_client.is_available():
    print(f"✅ API Gateway client ready at {gateway_client.gateway_url}")
    print("   Routes will use API Gateway with automatic fallback")
else:
    print(f"⚠️ API Gateway not available at {gateway_client.gateway_url}")
    print("   Routes will use direct agent calls (fallback mode)")

# Utility function to sanitize data for JSON serialization
def sanitize_for_json(obj):
    """Recursively sanitize data to be JSON-safe (convert NaN to None)"""
    if isinstance(obj, dict):
        return {key: sanitize_for_json(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_for_json(item) for item in obj]
    elif isinstance(obj, float):
        if np.isnan(obj) or np.isinf(obj):
            return None
        return obj
    elif hasattr(obj, 'item'):  # numpy types
        val = obj.item()
        if isinstance(val, float) and (np.isnan(val) or np.isinf(val)):
            return None
        return val
    else:
        return obj

@app.route('/')
def dashboard():
    """Main dashboard page"""
    projects = db_manager.get_all_projects()
    return render_template('dashboard.html', projects=projects)

@app.route('/create_project', methods=['POST'])
def create_project():
    """Create a new project"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid JSON data'}), 400
            
        project_name = data.get('name')
        description = data.get('description', '')
        
        if not project_name or not project_name.strip():
            return jsonify({'error': 'Project name is required'}), 400
            
        if len(project_name) > 100:
            return jsonify({'error': 'Project name is too long (max 100 characters)'}), 400
        
        project_id = str(uuid.uuid4())
        project_data = {
            'id': project_id,
            'name': project_name.strip(),
            'description': description.strip() if description else '',
            'created_at': datetime.now().isoformat()
        }
        
        success = db_manager.create_project(project_data)
        if success:
            return jsonify({'success': True, 'project_id': project_id, 'message': 'Project created successfully'})
        else:
            return jsonify({'error': 'Failed to create project in database'}), 500
            
    except Exception as e:
        print(f"Error in create_project: {e}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/search_project', methods=['POST'])
def search_project():
    """Search for a project by name or UUID"""
    data = request.get_json()
    query = data.get('query', '').strip()
    
    if not query:
        return jsonify({'error': 'Search query is required'}), 400
    
    projects = db_manager.search_projects(query)
    return jsonify({'projects': projects})

@app.route('/project/<project_id>')
def project_details(project_id):
    """Project details page"""
    project = db_manager.get_project(project_id)
    if not project:
        return "Project not found", 404
    
    documents = db_manager.get_project_documents(project_id)
    return render_template('project_details.html', project=project, documents=documents)

@app.route('/upload_document', methods=['POST'])
def upload_document():
    """Upload and process a PDF document"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    project_id = request.form.get('project_id')
    
    if not project_id:
        return jsonify({'error': 'Project ID is required'}), 400
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not file.filename.lower().endswith('.pdf'):
        return jsonify({'error': 'Only PDF files are allowed'}), 400
    
    try:
        # Save file temporarily
        filename = f"{uuid.uuid4()}.pdf"
        filepath = os.path.join('uploads', filename)
        os.makedirs('uploads', exist_ok=True)
        file.save(filepath)
        
        # Process PDF
        sentences, tables = pdf_processor.process_pdf(filepath)
        
        # Create document record
        document_id = str(uuid.uuid4())
        document_data = {
            'id': document_id,
            'project_id': project_id,
            'filename': file.filename,
            'created_at': datetime.now().isoformat(),
            'sentences_count': len(sentences),
            'tables_count': len(tables)
        }
        
        # Store document in database
        db_manager.create_document(document_data)
        
        # Create embeddings
        embeddings_manager.create_embeddings(project_id, document_id, sentences, tables)
        
        # Clean up temporary file
        os.remove(filepath)
        
        return jsonify({
            'success': True,
            'document_id': document_id,
            'sentences_count': len(sentences),
            'tables_count': len(tables)
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to process document: {str(e)}'}), 500

@app.route('/get_embeddings/<project_id>/<document_id>')
def get_embeddings(project_id, document_id):
    """Get embeddings for a specific document"""
    try:
        embeddings = embeddings_manager.get_document_embeddings(project_id, document_id)
        return jsonify({'embeddings': embeddings})
    except Exception as e:
        return jsonify({'error': f'Failed to retrieve embeddings: {str(e)}'}), 500

@app.route('/set_llm', methods=['POST'])
def set_llm():
    """Set the current LLM provider"""
    try:
        data = request.get_json()
        llm_name = data.get('llm')
        
        if not llm_name:
            return jsonify({'error': 'LLM name is required'}), 400
        
        success = llm_manager.set_llm(llm_name)
        
        if success:
            return jsonify({'success': True, 'message': f'LLM switched to {llm_name}'})
        else:
            return jsonify({'error': 'Invalid LLM selected'}), 400
            
    except Exception as e:
        return jsonify({'error': f'Failed to set LLM: {str(e)}'}), 500

@app.route('/get_llm_status', methods=['GET'])
def get_llm_status():
    """Get the current LLM status"""
    try:
        current_llm = llm_manager.get_current_llm()
        is_set = llm_manager.is_llm_set()
        
        # Find display name from available LLMs
        display_name = 'Not selected'
        if current_llm:
            available_llms = llm_manager.get_available_llms()
            for llm in available_llms:
                if llm['name'] == current_llm:
                    display_name = llm['display_name']
                    break
        
        return jsonify({
            'current_llm': current_llm,
            'is_set': is_set,
            'display_name': display_name
        })
    except Exception as e:
        return jsonify({'error': f'Failed to get LLM status: {str(e)}'}), 500

@app.route('/test_llm', methods=['POST'])
def test_llm():
    """Test the current LLM with a simple query"""
    try:
        data = request.get_json()
        llm_name = data.get('llm')
        query = data.get('query', 'Hello! Can you tell me what you are?')
        
        if llm_name:
            llm_manager.set_llm(llm_name)
        
        result = llm_manager.simple_chat(query)
        
        if result.get('success'):
            return jsonify({
                'success': True,
                'response': result.get('response', ''),
                'model': result.get('model', 'unknown')
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Unknown error')
            }), 500
            
    except Exception as e:
        return jsonify({'error': f'Failed to test LLM: {str(e)}'}), 500

@app.route('/chat_with_document', methods=['POST'])
def chat_with_document():
    """Chat with LLM using document context"""
    try:
        data = request.get_json()
        project_id = data.get('project_id')
        document_id = data.get('document_id')
        query = data.get('query')
        llm_name = data.get('llm')
        
        if not all([project_id, document_id, query]):
            return jsonify({'error': 'project_id, document_id, and query are required'}), 400
        
        # Set LLM if specified
        if llm_name:
            llm_manager.set_llm(llm_name)
        
        # Get relevant context from embeddings
        context_chunks = embeddings_manager.search_embeddings(project_id, document_id, query, n_results=5)
        
        if not context_chunks:
            return jsonify({'error': 'No relevant context found in document'}), 404
        
        # Chat with context
        result = llm_manager.chat_with_context(query, context_chunks, project_id, document_id)
        
        if result.get('success'):
            return jsonify({
                'success': True,
                'response': result.get('response', ''),
                'model': result.get('model', 'unknown'),
                'context_used': len(context_chunks)
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Unknown error')
            }), 500
            
    except Exception as e:
        return jsonify({'error': f'Failed to chat with document: {str(e)}'}), 500

@app.route('/get_available_llms')
def get_available_llms():
    """Get list of available LLM providers"""
    try:
        llms = llm_manager.get_available_llms()
        return jsonify({'llms': llms})
    except Exception as e:
        return jsonify({'error': f'Failed to get available LLMs: {str(e)}'}), 500

# Performance Agent Endpoints
@app.route('/performance_agent/first_generation', methods=['POST'])
def performance_first_generation():
    """First time generation of performance metrics"""
    def fallback():
        data = request.get_json()
        project_id = data.get('project_id')
        document_id = data.get('document_id')
        
        if not all([project_id, document_id]):
            return {'error': 'project_id and document_id are required'}, 400
        
        result = performance_agent.first_time_generation(project_id, document_id)
        return result
    
    try:
        response, status = gateway_client.request(
            '/performance_agent/first_generation',
            method='POST',
            data=request.get_json(),
            fallback_func=fallback
        )
        return jsonify(response), status
    except Exception as e:
        return jsonify({'error': f'Failed to generate performance metrics: {str(e)}'}), 500

@app.route('/performance_agent/extract_milestones', methods=['POST'])
def extract_milestones():
    """Extract milestones from a document"""
    def fallback():
        data = request.get_json()
        project_id = data.get('project_id')
        document_id = data.get('document_id')
        
        if not all([project_id, document_id]):
            return {'error': 'project_id and document_id are required'}, 400
        
        result = performance_agent.milestone_agent.extract_milestones_from_document(
            project_id, document_id, llm_manager
        )
        return result
    
    try:
        response, status = gateway_client.request(
            '/performance_agent/extract_milestones',
            method='POST',
            data=request.get_json(),
            fallback_func=fallback
        )
        return jsonify(response), status
    except Exception as e:
        return jsonify({'error': f'Failed to extract milestones: {str(e)}'}), 500

@app.route('/performance_agent/project_summary/<project_id>')
def get_performance_summary(project_id):
    """Get performance summary for a project"""
    def fallback():
        print(f"\n📋 PROJECT SUMMARY REQUEST - Project: {project_id}")
        summary = performance_agent.get_project_performance_summary(project_id)
        
        print(f"📋 Summary data:")
        print(f"   Milestones: {len(summary.get('milestones', []))}")
        print(f"   Tasks: {len(summary.get('tasks', []))}")
        print(f"   Bottlenecks: {len(summary.get('bottlenecks', []))}")
        
        return summary
    
    try:
        response, status = gateway_client.request(
            f'/performance_agent/project_summary/{project_id}',
            method='GET',
            fallback_func=fallback
        )
        return jsonify(response), status
    except Exception as e:
        print(f"❌ Error in project_summary: {str(e)}")
        return jsonify({'error': f'Failed to get performance summary: {str(e)}'}), 500

@app.route('/performance_agent/extract_tasks', methods=['POST'])
def extract_tasks():
    """Extract tasks from a document"""
    def fallback():
        data = request.get_json()
        project_id = data.get('project_id')
        document_id = data.get('document_id')
        
        if not all([project_id, document_id]):
            return {'error': 'project_id and document_id are required'}, 400
        
        result = performance_agent.task_agent.extract_tasks_from_document(
            project_id, document_id, llm_manager
        )
        return result
    
    try:
        response, status = gateway_client.request(
            '/performance_agent/extract_tasks',
            method='POST',
            data=request.get_json(),
            fallback_func=fallback
        )
        return jsonify(response), status
    except Exception as e:
        return jsonify({'error': f'Failed to extract tasks: {str(e)}'}), 500

@app.route('/performance_agent/extract_bottlenecks', methods=['POST'])
def extract_bottlenecks():
    """Extract bottlenecks from a document"""
    def fallback():
        data = request.get_json()
        project_id = data.get('project_id')
        document_id = data.get('document_id')
        
        if not all([project_id, document_id]):
            return {'error': 'project_id and document_id are required'}, 400
        
        result = performance_agent.bottleneck_agent.extract_bottlenecks_from_document(
            project_id, document_id, llm_manager
        )
        return result
    
    try:
        response, status = gateway_client.request(
            '/performance_agent/extract_bottlenecks',
            method='POST',
            data=request.get_json(),
            fallback_func=fallback
        )
        return jsonify(response), status
    except Exception as e:
        return jsonify({'error': f'Failed to extract bottlenecks: {str(e)}'}), 500

@app.route('/performance_agent/extract_requirements', methods=['POST'])
def extract_requirements():
    """Extract requirements from a document"""
    def fallback():
        data = request.get_json()
        project_id = data.get('project_id')
        document_id = data.get('document_id')
        if not all([project_id, document_id]):
            return {'error': 'project_id and document_id are required'}, 400
        result = performance_agent.requirements_agent.extract_requirements_from_document(
            project_id, document_id, llm_manager
        )
        return result
    try:
        response, status = gateway_client.request(
            '/performance_agent/extract_requirements',
            method='POST',
            data=request.get_json(),
            fallback_func=fallback
        )
        return jsonify(response), status
    except Exception as e:
        return jsonify({'error': f'Failed to extract requirements: {str(e)}'}), 500

@app.route('/performance_agent/extract_actors', methods=['POST'])
def extract_actors():
    """Extract actors/stakeholders from a document"""
    def fallback():
        data = request.get_json()
        project_id = data.get('project_id')
        document_id = data.get('document_id')
        if not all([project_id, document_id]):
            return {'error': 'project_id and document_id are required'}, 400
        result = performance_agent.actors_agent.extract_actors_from_document(
            project_id, document_id, llm_manager
        )
        return result
    try:
        response, status = gateway_client.request(
            '/performance_agent/extract_actors',
            method='POST',
            data=request.get_json(),
            fallback_func=fallback
        )
        return jsonify(response), status
    except Exception as e:
        return jsonify({'error': f'Failed to extract actors: {str(e)}'}), 500

@app.route('/performance_agent/extract_requirements_actors', methods=['POST'])
def extract_requirements_actors():
    """Extract requirements and actors from all project documents"""
    def fallback():
        data = request.get_json()
        project_id = data.get('project_id')
        if not project_id:
            return {'error': 'project_id is required'}, 400
        result = performance_agent.extract_requirements_and_actors_for_project(project_id)
        return result
    try:
        response, status = gateway_client.request(
            '/performance_agent/extract_requirements_actors',
            method='POST',
            data=request.get_json(),
            fallback_func=fallback
        )
        return jsonify(response), status
    except Exception as e:
        return jsonify({'error': f'Failed to extract requirements and actors: {str(e)}'}), 500

@app.route('/performance_agent/requirements/<project_id>', methods=['GET'])
def get_requirements(project_id: str):
    """Get requirements for a project"""
    try:
        data = performance_agent.chroma_manager.get_performance_data('requirements', project_id)
        return jsonify({'requirements': data}), 200
    except Exception as e:
        return jsonify({'error': f'Failed to fetch requirements: {str(e)}'}), 500

@app.route('/performance_agent/actors/<project_id>', methods=['GET'])
def get_actors(project_id: str):
    """Get actors/stakeholders for a project"""
    try:
        data = performance_agent.chroma_manager.get_performance_data('actors', project_id)
        return jsonify({'actors': data}), 200
    except Exception as e:
        return jsonify({'error': f'Failed to fetch actors: {str(e)}'}), 500

@app.route('/performance_agent/update_metrics', methods=['POST'])
def update_performance_metrics():
    """Update performance metrics for new document"""
    def fallback():
        data = request.get_json()
        project_id = data.get('project_id')
        document_id = data.get('document_id')
        
        if not all([project_id, document_id]):
            return {'error': 'project_id and document_id are required'}, 400
        
        result = performance_agent.update_performance_metrics_for_new_document(project_id, document_id)
        return result
    
    try:
        response, status = gateway_client.request(
            '/performance_agent/update_metrics',
            method='POST',
            data=request.get_json(),
            fallback_func=fallback
        )
        return jsonify(response), status
    except Exception as e:
        return jsonify({'error': f'Failed to update performance metrics: {str(e)}'}), 500

@app.route('/performance_agent/schedule_update', methods=['POST'])
def schedule_performance_update():
    """Manually trigger scheduled performance update"""
    def fallback():
        performance_agent.schedule_performance_updates()
        return {'success': True, 'message': 'Performance update scheduled successfully'}
    
    try:
        response, status = gateway_client.request(
            '/performance_agent/schedule_update',
            method='POST',
            fallback_func=fallback
        )
        return jsonify(response), status
    except Exception as e:
        return jsonify({'error': f'Failed to schedule performance update: {str(e)}'}), 500

# Performance Agent Dashboard
@app.route('/performance_agent/dashboard/<project_id>')
def performance_dashboard(project_id):
    """Render Performance Agent Dashboard page"""
    try:
        project = db_manager.get_project(project_id)
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        documents = db_manager.get_project_documents(project_id)
        first_doc_id = documents[0]['id'] if documents else ''
        return render_template('performance_dashboard.html', project=project, first_doc_id=first_doc_id)
        
    except Exception as e:
        return jsonify({'error': f'Failed to load performance dashboard: {str(e)}'}), 500

# Performance Quick Status (Read-Only)
@app.route('/performance_agent/quick_status/<project_id>')
def get_quick_performance_status(project_id):
    """Get current performance metrics - READ ONLY (no processing, for auto-refresh)"""
    def fallback():
        print(f"\n{'='*80}")
        print(f"📊 QUICK STATUS REQUEST - Project: {project_id}")
        print(f"{'='*80}")
        
        # Get basic project info
        project = db_manager.get_project(project_id)
        if not project:
            print(f"❌ Project not found: {project_id}")
            return {'error': 'Project not found'}, 404
        
        print(f"✅ Project found: {project.get('name', 'Unknown')}")
        
        # Just read current data without processing
        response = performance_agent._get_current_performance_data(project_id)
        
        print(f"📊 Response data:")
        print(f"   Milestones: {response.get('milestones', {}).get('count', 0)}")
        print(f"   Tasks: {response.get('tasks', {}).get('count', 0)}")
        print(f"   Bottlenecks: {response.get('bottlenecks', {}).get('count', 0)}")
        print(f"   Completion: {response.get('completion_score', 0)}%")
        print(f"{'='*80}\n")
        
        return response
    
    try:
        response, status = gateway_client.request(
            f'/performance_agent/quick_status/{project_id}',
            method='GET',
            fallback_func=fallback
        )
        return jsonify(response), status
    except Exception as e:
        print(f"❌ Error in quick_status: {str(e)}")
        return jsonify({'error': f'Failed to get quick status: {str(e)}'}), 500

# Performance Status (Full Processing)
@app.route('/performance_agent/status/<project_id>')
def get_performance_status(project_id):
    """Get current performance metrics - FULL PROCESSING (processes new documents in background)"""
    try:
        # Get basic project info
        project = db_manager.get_project(project_id)
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        
        # Check if already processing
        with jobs_lock:
            if project_id in processing_jobs:
                job_status = processing_jobs[project_id].get('status')
                job_agent = processing_jobs[project_id].get('agent')
                
                # Only prevent duplicate if actively processing
                if job_status == 'processing' and job_agent == 'performance':
                    return jsonify({
                        'success': True,
                        'processing': True,
                        'message': 'Performance data processing already in progress...',
                        'job_id': processing_jobs[project_id]['job_id'],
                        'started_at': processing_jobs[project_id]['started_at']
                    })
                
                # If completed or failed, allow new refresh (user explicitly requested it)
                # Just clear the old job and start a new one
                if job_status in ['completed', 'failed'] and job_agent == 'performance':
                    print(f"   🔄 Clearing previous job (status: {job_status}) and starting new refresh")
                    del processing_jobs[project_id]
        
        # Start background processing
        job_id = str(uuid.uuid4())
        
        with jobs_lock:
            processing_jobs[project_id] = {
                'job_id': job_id,
                'status': 'processing',
                'started_at': datetime.now().isoformat(),
                'agent': 'performance'
            }
        
        # Try gateway first, if available use it for processing
        if gateway_client.is_available():
            # Use gateway for processing
            def gateway_refresh():
                response, status = gateway_client.request(
                    f'/performance_agent/refresh/{project_id}',
                    method='POST',
                    fallback_func=None
                )
                return response if status == 200 else None
            
            # Run gateway request in background
            thread = Thread(target=run_performance_refresh_background_gateway, args=(project_id, job_id, gateway_refresh))
        else:
            # Use direct agent call
            thread = Thread(target=run_performance_refresh_background, args=(project_id, job_id))
        
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'processing': True,
            'message': 'Performance data processing started in background',
            'job_id': job_id,
            'started_at': processing_jobs[project_id]['started_at']
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to start performance processing: {str(e)}'}), 500

def run_performance_refresh_background(project_id, job_id):
    """Background worker function for performance agent refresh (direct call)"""
    try:
        print(f"\n🔄 [Background Job {job_id[:8]}] Starting performance refresh for project {project_id[:8]}...")
        result = performance_agent.refresh_performance_data(project_id)
        
        with jobs_lock:
            processing_jobs[project_id] = {
                'job_id': job_id,
                'status': 'completed',
                'completed_at': datetime.now().isoformat(),
                'agent': 'performance',
                'result': result
            }
        print(f"✅ [Background Job {job_id[:8]}] Performance refresh completed successfully!")
        
    except Exception as e:
        print(f"❌ [Background Job {job_id[:8]}] Performance refresh failed: {str(e)}")
        with jobs_lock:
            processing_jobs[project_id] = {
                'job_id': job_id,
                'status': 'failed',
                'failed_at': datetime.now().isoformat(),
                'agent': 'performance',
                'error': str(e),
                'result': {'success': False, 'error': str(e)}
            }

def run_performance_refresh_background_gateway(project_id, job_id, gateway_func):
    """Background worker function for performance agent refresh (via gateway)"""
    try:
        print(f"\n🔄 [Background Job {job_id[:8]}] Starting performance refresh via gateway for project {project_id[:8]}...")
        result = gateway_func()
        
        with jobs_lock:
            processing_jobs[project_id] = {
                'job_id': job_id,
                'status': 'completed',
                'completed_at': datetime.now().isoformat(),
                'agent': 'performance',
                'result': result or {'success': True}
            }
        print(f"✅ [Background Job {job_id[:8]}] Performance refresh completed successfully!")
        
    except Exception as e:
        print(f"❌ [Background Job {job_id[:8]}] Performance refresh failed: {str(e)}")
        with jobs_lock:
            processing_jobs[project_id] = {
                'job_id': job_id,
                'status': 'failed',
                'failed_at': datetime.now().isoformat(),
                'agent': 'performance',
                'error': str(e),
                'result': {'success': False, 'error': str(e)}
            }

@app.route('/performance_agent/processing_status/<project_id>')
def get_performance_processing_status(project_id):
    """Check the status of background performance processing"""
    try:
        with jobs_lock:
            if project_id in processing_jobs:
                job_info = processing_jobs[project_id].copy()
                if job_info.get('agent') == 'performance':
                    return jsonify({
                        'success': True,
                        'found': True,
                        **job_info
                    })
        
        return jsonify({
            'success': True,
            'found': False,
            'status': 'not_found',
            'message': 'No processing job found for this project'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Performance Suggestions
@app.route('/performance_agent/suggestions/<project_id>')
def get_performance_suggestions(project_id):
    """Get AI-generated suggestions"""
    def fallback():
        suggestions = performance_agent.get_suggestions(project_id)
        
        return {
            'success': True,
            'project_id': project_id,
            'suggestions': suggestions
        }
    
    try:
        response, status = gateway_client.request(
            f'/performance_agent/suggestions/{project_id}',
            method='GET',
            fallback_func=fallback
        )
        return jsonify(response), status
    except Exception as e:
        return jsonify({'error': f'Failed to get performance suggestions: {str(e)}'}), 500

# Get Item Details
@app.route('/performance_agent/item_details/<project_id>/<detail_type>/<item_id>')
def get_item_details(project_id, detail_type, item_id):
    """Get details for a specific milestone/task/bottleneck"""
    def fallback():
        print(f"\n📋 ITEM DETAILS REQUEST - Type: {detail_type}, Item: {item_id}")
        
        # Get details from ChromaDB
        details = performance_agent.chroma_manager.get_details_by_parent(detail_type, item_id)
        
        print(f"📋 Found {len(details)} details for {item_id}")
        
        return {
            'success': True,
            'item_id': item_id,
            'details': details
        }
    
    try:
        response, status = gateway_client.request(
            f'/performance_agent/item_details/{project_id}/{detail_type}/{item_id}',
            method='GET',
            fallback_func=fallback
        )
        return jsonify(response), status
    except Exception as e:
        print(f"❌ Error getting item details: {str(e)}")
        return jsonify({'error': f'Failed to get item details: {str(e)}'}), 500

# Export Performance Report
@app.route('/performance_agent/export/<project_id>')
def export_performance_report(project_id):
    """Export performance data as JSON"""
    def fallback():
        # Get refreshed performance data
        performance_data = performance_agent.refresh_performance_data(project_id)
        
        # Get suggestions
        suggestions = performance_agent.get_suggestions(project_id)
        
        # Create export data
        export_data = {
            'project_id': project_id,
            'export_timestamp': datetime.now().isoformat(),
            'performance_data': performance_data,
            'suggestions': suggestions
        }
        
        # Create response
        response = make_response(jsonify(export_data))
        response.headers['Content-Disposition'] = f'attachment; filename=performance-report-{project_id}.json'
        response.headers['Content-Type'] = 'application/json'
        
        return response
    
    try:
        response, status = gateway_client.request(
            f'/performance_agent/export/{project_id}',
            method='GET',
            fallback_func=fallback
        )
        if isinstance(response, dict):
            # Gateway returned JSON, create download response
            export_response = make_response(jsonify(response))
            export_response.headers['Content-Disposition'] = f'attachment; filename=performance-report-{project_id}.json'
            export_response.headers['Content-Type'] = 'application/json'
            return export_response
        else:
            return jsonify(response), status
    except Exception as e:
        return jsonify({'error': f'Failed to export performance report: {str(e)}'}), 500

# ============================================================================
# FINANCIAL AGENT ENDPOINTS
# ============================================================================

@app.route('/financial_agent/dashboard/<project_id>')
def financial_dashboard(project_id):
    """Render Financial Agent Dashboard page"""
    try:
        project = db_manager.get_project(project_id)
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        
        return render_template('financial_dashboard.html', project=project, project_id=project_id)
        
    except Exception as e:
        return jsonify({'error': f'Failed to load financial dashboard: {str(e)}'}), 500

@app.route('/financial_agent/first_generation', methods=['POST'])
def financial_first_generation():
    """First time generation of financial metrics"""
    def fallback():
        data = request.get_json()
        project_id = data.get('project_id')
        document_id = data.get('document_id')
        
        # If no document_id provided, process all documents
        if not document_id:
            if not project_id:
                return {'error': 'project_id required'}, 400
            
            # Get all project documents
            documents = db_manager.get_project_documents(project_id)
            if not documents:
                return {'error': 'No documents found in project'}, 400
            
            # Process all documents
            all_results = []
            for document in documents:
                result = financial_agent.first_time_generation(project_id, document['id'])
                all_results.append(result)
            
            # Aggregate results
            aggregated = {
                'success': all([r.get('overall_success', False) for r in all_results]),
                'project_id': project_id,
                'documents_processed': len(all_results),
                'financial_details': {'count': sum(r.get('financial_details', {}).get('count', 0) for r in all_results)},
                'transactions': {'count': sum(r.get('transactions', {}).get('count', 0) for r in all_results)},
                'expenses': {'total': sum(r.get('expenses', {}).get('total', 0) for r in all_results)},
                'revenue': {'total': sum(r.get('revenue', {}).get('total', 0) for r in all_results)},
                'financial_health': sum(r.get('financial_health', 0) for r in all_results) / len(all_results) if all_results else 0
            }
            return aggregated
        else:
            if not project_id:
                return {'error': 'project_id required'}, 400
            
            result = financial_agent.first_time_generation(project_id, document_id)
            return result
    
    try:
        response, status = gateway_client.request(
            '/financial_agent/first_generation',
            method='POST',
            data=request.get_json(),
            fallback_func=fallback
        )
        return jsonify(response), status
    except Exception as e:
        return jsonify({'error': f'Failed to generate financial metrics: {str(e)}'}), 500

@app.route('/financial_agent/status/<project_id>')
def get_financial_status(project_id):
    """Get current financial metrics - FULL PROCESSING (processes new documents in background)"""
    try:
        # Check if already processing
        with jobs_lock:
            if project_id in processing_jobs:
                job_status = processing_jobs[project_id].get('status')
                job_agent = processing_jobs[project_id].get('agent')
                
                # Only prevent duplicate if actively processing
                if job_status == 'processing' and job_agent == 'financial':
                    return jsonify({
                        'success': True,
                        'processing': True,
                        'message': 'Financial data processing already in progress...',
                        'job_id': processing_jobs[project_id]['job_id'],
                        'started_at': processing_jobs[project_id]['started_at']
                    })
                
                # If completed or failed, allow new refresh (user explicitly requested it)
                # Just clear the old job and start a new one
                if job_status in ['completed', 'failed'] and job_agent == 'financial':
                    print(f"   🔄 Clearing previous job (status: {job_status}) and starting new refresh")
                    del processing_jobs[project_id]
        
        # Start background processing
        job_id = str(uuid.uuid4())
        
        with jobs_lock:
            processing_jobs[project_id] = {
                'job_id': job_id,
                'status': 'processing',
                'started_at': datetime.now().isoformat(),
                'agent': 'financial'
            }
        
        # Try gateway first, if available use it for processing
        if gateway_client.is_available():
            # Use gateway for processing
            def gateway_refresh():
                response, status = gateway_client.request(
                    f'/financial_agent/refresh/{project_id}',
                    method='POST',
                    fallback_func=None
                )
                return response if status == 200 else None
            
            # Run gateway request in background
            thread = Thread(target=run_financial_refresh_background_gateway, args=(project_id, job_id, gateway_refresh))
        else:
            # Use direct agent call
            thread = Thread(target=run_financial_refresh_background, args=(project_id, job_id))
        
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'processing': True,
            'message': 'Financial data processing started in background',
            'job_id': job_id,
            'started_at': processing_jobs[project_id]['started_at']
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to start financial processing: {str(e)}'}), 500

def run_financial_refresh_background(project_id, job_id):
    """Background worker function for financial agent refresh (direct call)"""
    try:
        print(f"\n🔄 [Background Job {job_id[:8]}] Starting financial refresh for project {project_id[:8]}...")
        result = financial_agent.refresh_financial_data(project_id)
        
        with jobs_lock:
            processing_jobs[project_id] = {
                'job_id': job_id,
                'status': 'completed',
                'completed_at': datetime.now().isoformat(),
                'agent': 'financial',
                'result': result
            }
        print(f"✅ [Background Job {job_id[:8]}] Financial refresh completed successfully!")
        
    except Exception as e:
        print(f"❌ [Background Job {job_id[:8]}] Financial refresh failed: {str(e)}")
        with jobs_lock:
            processing_jobs[project_id] = {
                'job_id': job_id,
                'status': 'failed',
                'failed_at': datetime.now().isoformat(),
                'agent': 'financial',
                'error': str(e),
                'result': {'success': False, 'error': str(e)}
            }

def run_financial_refresh_background_gateway(project_id, job_id, gateway_func):
    """Background worker function for financial agent refresh (via gateway)"""
    try:
        print(f"\n🔄 [Background Job {job_id[:8]}] Starting financial refresh via gateway for project {project_id[:8]}...")
        result = gateway_func()
        
        with jobs_lock:
            processing_jobs[project_id] = {
                'job_id': job_id,
                'status': 'completed',
                'completed_at': datetime.now().isoformat(),
                'agent': 'financial',
                'result': result or {'success': True}
            }
        print(f"✅ [Background Job {job_id[:8]}] Financial refresh completed successfully!")
        
    except Exception as e:
        print(f"❌ [Background Job {job_id[:8]}] Financial refresh failed: {str(e)}")
        with jobs_lock:
            processing_jobs[project_id] = {
                'job_id': job_id,
                'status': 'failed',
                'failed_at': datetime.now().isoformat(),
                'agent': 'financial',
                'error': str(e),
                'result': {'success': False, 'error': str(e)}
            }

@app.route('/financial_agent/processing_status/<project_id>')
def get_financial_processing_status(project_id):
    """Check the status of background financial processing"""
    try:
        with jobs_lock:
            if project_id in processing_jobs:
                job_info = processing_jobs[project_id].copy()
                # Only return if it's a financial agent job
                if job_info.get('agent') == 'financial':
                    return jsonify({
                        'success': True,
                        'found': True,
                        **job_info
                    })
        
        return jsonify({
            'success': True,
            'found': False,
            'status': 'not_found',
            'message': 'No financial processing job found for this project'
        })
        
    except Exception as e:
        print(f"  ❌ Error in get_financial_processing_status: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/financial_agent/quick_status/<project_id>')
def get_quick_financial_status(project_id):
    """Get current financial metrics - READ ONLY (no processing, for auto-refresh)"""
    def fallback():
        # Get current data without processing
        data = financial_agent._get_current_financial_data(project_id)
        
        # Get transactions for display
        transactions = financial_agent.chroma_manager.get_financial_data('transactions', project_id)
        data['transactions'] = transactions[:20]  # Limit to 20 most recent
        
        # Get financial details for display
        financial_details = financial_agent.chroma_manager.get_financial_data('financial_details', project_id)
        data['financial_details'] = financial_details[:10]  # Limit to 10
        
        # Get expense analysis
        expense_analysis = financial_agent.expense_agent.get_expense_analysis(project_id)
        data['expense_analysis'] = expense_analysis

        # Actor → transaction mappings (for card visibility)
        mappings = financial_agent.get_actor_transaction_mappings(project_id)
        data['actor_transaction_mappings'] = {
            'count': len(mappings),
            'items': mappings[:10]  # limit for quick payload
        }
        
        return data
    
    try:
        response, status = gateway_client.request(
            f'/financial_agent/quick_status/{project_id}',
            method='GET',
            fallback_func=fallback
        )
        return jsonify(response), status
    except Exception as e:
        return jsonify({'error': f'Failed to get quick financial status: {str(e)}'}), 500

@app.route('/financial_agent/transactions/<project_id>')
def get_financial_transactions(project_id):
    """Get all transactions"""
    def fallback():
        # Get filter parameters
        txn_type = request.args.get('type')  # expense, revenue, etc.
        
        filters = {}
        if txn_type:
            filters['transaction_type'] = txn_type
        
        transactions = financial_agent.chroma_manager.get_financial_data(
            'transactions', project_id, filters
        )
        
        return {
            'success': True,
            'transactions': transactions,
            'count': len(transactions)
        }
    
    try:
        response, status = gateway_client.request(
            f'/financial_agent/transactions/{project_id}',
            method='GET',
            params=request.args.to_dict(),
            fallback_func=fallback
        )
        return jsonify(response), status
    except Exception as e:
        return jsonify({'error': f'Failed to get transactions: {str(e)}'}), 500

@app.route('/financial_agent/expenses/<project_id>')
def get_expenses(project_id):
    """Get expense analysis"""
    def fallback():
        transactions = financial_agent.chroma_manager.get_financial_data('transactions', project_id)
        expense_analysis = financial_agent.expense_agent.analyze_expenses(project_id, transactions)
        
        return {
            'success': True,
            'expense_analysis': expense_analysis
        }
    
    try:
        response, status = gateway_client.request(
            f'/financial_agent/expenses/{project_id}',
            method='GET',
            fallback_func=fallback
        )
        return jsonify(response), status
    except Exception as e:
        return jsonify({'error': f'Failed to get expenses: {str(e)}'}), 500

@app.route('/financial_agent/revenue/<project_id>')
def get_revenue(project_id):
    """Get revenue analysis"""
    def fallback():
        transactions = financial_agent.chroma_manager.get_financial_data('transactions', project_id)
        revenue_analysis = financial_agent.revenue_agent.analyze_revenue(project_id, transactions)
        
        return {
            'success': True,
            'revenue_analysis': revenue_analysis
        }
    
    try:
        response, status = gateway_client.request(
            f'/financial_agent/revenue/{project_id}',
            method='GET',
            fallback_func=fallback
        )
        return jsonify(response), status
    except Exception as e:
        return jsonify({'error': f'Failed to get revenue: {str(e)}'}), 500

@app.route('/financial_agent/map_actor_transactions', methods=['POST'])
def map_actor_transactions():
    """Map actors (from Performance) to financial transactions"""
    def fallback():
        data = request.get_json() or {}
        project_id = data.get('project_id')
        if not project_id:
            return {'error': 'project_id required'}, 400
        actors = []
        # Try to fetch actors via gateway (A2A router) first
        try:
            resp, _ = gateway_client.request(
                f'/performance_agent/actors/{project_id}',
                method='GET',
                fallback_func=lambda: {'actors': []}
            )
            if isinstance(resp, dict):
                actors = resp.get('actors', resp.get('data', [])) or []
            elif isinstance(resp, list):
                actors = resp
            print(f"📥 Fetched {len(actors)} actors via gateway")
        except Exception as e:
            print(f"⚠️  Error fetching actors via gateway: {e}")
        
        # If no actors from gateway, try direct access to performance agent ChromaDB
        if not actors:
            try:
                actors = performance_agent.chroma_manager.get_performance_data('actors', project_id)
                print(f"📥 Fetched {len(actors)} actors directly from performance agent ChromaDB")
                if actors:
                    print(f"   Sample actor: {actors[0] if actors else 'None'}")
            except Exception as e:
                print(f"❌ Error fetching actors directly: {e}")
                import traceback
                traceback.print_exc()
        
        if not actors:
            return {'error': 'No actors found. Run Performance agent first to extract actors.'}, 400
        
        return financial_agent.map_actor_transactions(project_id, actors=actors)

    try:
        response, status = gateway_client.request(
            '/financial_agent/map_actor_transactions',
            method='POST',
            data=request.get_json(),
            fallback_func=fallback
        )
        return jsonify(response), status
    except Exception as e:
        return jsonify({'error': f'Failed to map actors to transactions: {str(e)}'}), 500

@app.route('/financial_agent/actor_transaction_mappings/<project_id>')
def get_actor_transaction_mappings(project_id):
    """Get stored actor -> transaction mappings"""
    def fallback():
        data = financial_agent.get_actor_transaction_mappings(project_id)
        return {'success': True, 'mappings': data}

    try:
        response, status = gateway_client.request(
            f'/financial_agent/actor_transaction_mappings/{project_id}',
            method='GET',
            fallback_func=fallback
        )
        return jsonify(response), status
    except Exception as e:
        return jsonify({'error': f'Failed to get actor transaction mappings: {str(e)}'}), 500

# ============================================================================
# DOCUMENT AGENT ENDPOINTS
# ============================================================================

@app.route('/document_agent/dashboard/<project_id>')
def document_agent_dashboard(project_id):
    try:
        project = db_manager.get_project(project_id)
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        return render_template('document_dashboard.html', project=project, project_id=project_id)
    except Exception as e:
        return jsonify({'error': f'Failed to load document dashboard: {str(e)}'}), 500

@app.route('/document_agent/psdp_summary', methods=['POST'])
def generate_psdp_summary():
    def fallback():
        data = request.get_json() or {}
        project_id = data.get('project_id')
        if not project_id:
            return {'error': 'project_id required'}, 400
        return doc_agent.generate_psdp_summary(project_id)
    try:
        response, status = gateway_client.request(
            '/document_agent/psdp_summary',
            method='POST',
            data=request.get_json(),
            fallback_func=fallback
        )
        return jsonify(response), status
    except Exception as e:
        return jsonify({'error': f'Failed to generate PSDP summary: {str(e)}'}), 500

@app.route('/document_agent/financial_brief', methods=['POST'])
def generate_financial_brief():
    def fallback():
        data = request.get_json() or {}
        project_id = data.get('project_id')
        if not project_id:
            return {'error': 'project_id required'}, 400
        return doc_agent.generate_financial_brief(project_id)
    try:
        response, status = gateway_client.request(
            '/document_agent/financial_brief',
            method='POST',
            data=request.get_json(),
            fallback_func=fallback
        )
        return jsonify(response), status
    except Exception as e:
        return jsonify({'error': f'Failed to generate Financial Brief: {str(e)}'}), 500

@app.route('/document_agent/documents/<project_id>')
def list_doc_agent_documents(project_id):
    try:
        docs = doc_agent.chroma_manager.list_documents(
            project_id,
            doc_agent.chroma_manager.collections["doc_agent_documents"]
        )
        return jsonify({'success': True, 'documents': docs}), 200
    except Exception as e:
        return jsonify({'error': f'Failed to list documents: {str(e)}'}), 500

@app.route('/document_agent/document/<doc_id>')
def get_doc_agent_document(doc_id):
    try:
        doc = doc_agent.chroma_manager.get_document(
            doc_id,
            doc_agent.chroma_manager.collections["doc_agent_documents"]
        )
        if not doc:
            return jsonify({'error': 'Document not found'}), 404
        return jsonify({'success': True, 'document': doc}), 200
    except Exception as e:
        return jsonify({'error': f'Failed to get document: {str(e)}'}), 500

@app.route('/document_agent/document/<doc_id>/download')
def download_doc_agent_document(doc_id):
    try:
        doc = doc_agent.chroma_manager.get_document(
            doc_id,
            doc_agent.chroma_manager.collections["doc_agent_documents"]
        )
        if not doc:
            return jsonify({'error': 'Document not found'}), 404
        content = doc.get('content', '')
        response = make_response(content)
        response.headers['Content-Disposition'] = f'attachment; filename=\"{doc_id}.html\"'
        response.headers['Content-Type'] = 'text/html'
        return response
    except Exception as e:
        return jsonify({'error': f'Failed to download document: {str(e)}'}), 500

# ============================================================================
# INTELLIGENT DOCUMENT GENERATOR ENDPOINTS
# ============================================================================

@app.route('/doc_gen/create', methods=['POST'])
def create_intelligent_document():
    def fallback():
        data = request.get_json() or {}
        project_id = data.get('project_id')
        title = data.get('title') or 'Custom Document'
        instructions = data.get('instructions') or ''
        if not project_id:
            return {'error': 'project_id required'}, 400
        return intelligent_doc_agent.create_document(project_id, title, instructions)
    try:
        response, status = gateway_client.request(
            '/doc_gen/create',
            method='POST',
            data=request.get_json(),
            fallback_func=fallback
        )
        return jsonify(response), status
    except Exception as e:
        return jsonify({'error': f'Failed to create intelligent document: {str(e)}'}), 500

@app.route('/doc_gen/documents/<project_id>')
def list_doc_gen_documents(project_id):
    try:
        docs = intelligent_doc_agent.chroma_manager.list_documents(
            project_id,
            intelligent_doc_agent.chroma_manager.collections["doc_gen_documents"]
        )
        return jsonify({'success': True, 'documents': docs}), 200
    except Exception as e:
        return jsonify({'error': f'Failed to list intelligent documents: {str(e)}'}), 500

@app.route('/doc_gen/document/<doc_id>')
def get_doc_gen_document(doc_id):
    try:
        doc = intelligent_doc_agent.chroma_manager.get_document(
            doc_id,
            intelligent_doc_agent.chroma_manager.collections["doc_gen_documents"]
        )
        if not doc:
            return jsonify({'error': 'Document not found'}), 404
        return jsonify({'success': True, 'document': doc}), 200
    except Exception as e:
        return jsonify({'error': f'Failed to get intelligent document: {str(e)}'}), 500

@app.route('/doc_gen/document/<doc_id>/download')
def download_doc_gen_document(doc_id):
    try:
        doc = intelligent_doc_agent.chroma_manager.get_document(
            doc_id,
            intelligent_doc_agent.chroma_manager.collections["doc_gen_documents"]
        )
        if not doc:
            return jsonify({'error': 'Document not found'}), 404
        content = doc.get('content', '')
        response = make_response(content)
        response.headers['Content-Disposition'] = f'attachment; filename=\"{doc_id}.html\"'
        response.headers['Content-Type'] = 'text/html'
        return response
    except Exception as e:
        return jsonify({'error': f'Failed to download intelligent document: {str(e)}'}), 500

@app.route('/financial_agent/anomalies/<project_id>')
def get_anomalies(project_id):
    """Get detected anomalies for a project"""
    def fallback():
        # Get filter parameters
        severity_level = request.args.get('severity')  # critical, high, medium, low
        status = request.args.get('status')  # unreviewed, reviewed, dismissed
        
        filters = {}
        if severity_level:
            filters['severity_level'] = severity_level
        if status:
            filters['status'] = status
        
        anomalies = financial_agent.anomaly_agent.get_anomalies(project_id, filters)
        
        # Get summary statistics
        total_anomalies = len(anomalies)
        severity_counts = {
            'critical': sum(1 for a in anomalies if a.get('metadata', {}).get('severity_level') == 'critical'),
            'high': sum(1 for a in anomalies if a.get('metadata', {}).get('severity_level') == 'high'),
            'medium': sum(1 for a in anomalies if a.get('metadata', {}).get('severity_level') == 'medium'),
            'low': sum(1 for a in anomalies if a.get('metadata', {}).get('severity_level') == 'low')
        }
        
        return {
            'success': True,
            'anomalies': anomalies,
            'total_count': total_anomalies,
            'severity_counts': severity_counts
        }
    
    try:
        response, status = gateway_client.request(
            f'/financial_agent/anomalies/{project_id}',
            method='GET',
            params=request.args.to_dict(),
            fallback_func=fallback
        )
        return jsonify(response), status
    except Exception as e:
        return jsonify({'error': f'Failed to get anomalies: {str(e)}'}), 500

@app.route('/financial_agent/anomalies/update', methods=['POST'])
def update_anomaly_status():
    """Update anomaly review status"""
    def fallback():
        data = request.get_json()
        anomaly_id = data.get('anomaly_id')
        status = data.get('status')  # reviewed, dismissed
        notes = data.get('notes', '')
        
        if not anomaly_id or not status:
            return {'error': 'Missing required fields'}, 400
        
        success = financial_agent.anomaly_agent.update_anomaly_status(
            anomaly_id, status, notes
        )
        
        if success:
            return {'success': True, 'message': 'Anomaly status updated'}
        else:
            return {'error': 'Failed to update anomaly status'}, 500
    
    try:
        response, status = gateway_client.request(
            '/financial_agent/anomalies/update',
            method='POST',
            data=request.get_json(),
            fallback_func=fallback
        )
        return jsonify(response), status
    except Exception as e:
        return jsonify({'error': f'Failed to update anomaly: {str(e)}'}), 500

@app.route('/financial_agent/anomalies/reviewed/<project_id>')
def get_reviewed_anomalies(project_id):
    """Get reviewed anomalies history for a project"""
    def fallback():
        reviewed_anomalies = financial_agent.anomaly_agent.get_reviewed_anomalies(project_id)
        
        return {
            'success': True,
            'reviewed_anomalies': reviewed_anomalies,
            'count': len(reviewed_anomalies)
        }
    
    try:
        response, status = gateway_client.request(
            f'/financial_agent/anomalies/reviewed/{project_id}',
            method='GET',
            fallback_func=fallback
        )
        return jsonify(response), status
    except Exception as e:
        return jsonify({'error': f'Failed to get reviewed anomalies: {str(e)}'}), 500

@app.route('/financial_agent/export/<project_id>')
def export_financial_report(project_id):
    """Export financial data as JSON"""
    def fallback():
        # Get refreshed financial data
        financial_data = financial_agent.refresh_financial_data(project_id)
        
        # Get all transactions
        transactions = financial_agent.chroma_manager.get_financial_data('transactions', project_id)
        
        # Get expense and revenue analysis
        expense_analysis = financial_agent.expense_agent.analyze_expenses(project_id, transactions)
        revenue_analysis = financial_agent.revenue_agent.analyze_revenue(project_id, transactions)
        
        export_data = {
            'project_id': project_id,
            'exported_at': datetime.now().isoformat(),
            'summary': financial_data,
            'transactions': transactions,
            'expense_analysis': expense_analysis,
            'revenue_analysis': revenue_analysis
        }
        
        response = make_response(jsonify(export_data))
        response.headers['Content-Disposition'] = f'attachment; filename=financial_report_{project_id[:8]}.json'
        response.headers['Content-Type'] = 'application/json'
        
        return response
    
    try:
        response, status = gateway_client.request(
            f'/financial_agent/export/{project_id}',
            method='GET',
            fallback_func=fallback
        )
        if isinstance(response, dict):
            # Gateway returned JSON, create download response
            export_response = make_response(jsonify(response))
            export_response.headers['Content-Disposition'] = f'attachment; filename=financial_report_{project_id[:8]}.json'
            export_response.headers['Content-Type'] = 'application/json'
            return export_response
        else:
            return jsonify(response), status
    except Exception as e:
        return jsonify({'error': f'Failed to export financial report: {str(e)}'}), 500

# ============================================================================
# Resource Agent Routes
# ============================================================================

@app.route('/resource_agent/dashboard/<project_id>')
def resource_dashboard(project_id):
    """Render Resource Agent Dashboard page"""
    try:
        project = db_manager.get_project(project_id)
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        
        # Get first document ID for first generation
        documents = db_manager.get_project_documents(project_id)
        first_doc_id = documents[0]['id'] if documents else None
        
        return render_template('resource_dashboard.html', 
                             project=project, 
                             project_id=project_id,
                             first_doc_id=first_doc_id)
        
    except Exception as e:
        return jsonify({'error': f'Failed to load resource dashboard: {str(e)}'}), 500

@app.route('/resource_agent/first_generation', methods=['POST'])
def resource_first_generation():
    """First time generation of resource metrics"""
    def fallback():
        data = request.get_json()
        project_id = data.get('project_id')
        document_id = data.get('document_id')
        
        if not project_id or not document_id:
            return {'error': 'project_id and document_id are required'}, 400
        
        result = resource_agent.first_time_generation(project_id, document_id)
        return result
    
    try:
        response, status = gateway_client.request(
            '/resource_agent/first_generation',
            method='POST',
            data=request.get_json(),
            fallback_func=fallback
        )
        return jsonify(response), status
    except Exception as e:
        return jsonify({'error': f'Failed to generate resource metrics: {str(e)}'}), 500

@app.route('/resource_agent/status/<project_id>')
def get_resource_status(project_id):
    """Get current resource data status"""
    def fallback():
        return resource_agent._get_current_resource_data(project_id)
    
    try:
        response, status = gateway_client.request(
            f'/resource_agent/status/{project_id}',
            method='GET',
            fallback_func=fallback
        )
        return jsonify(response), status
    except Exception as e:
        return jsonify({'error': f'Failed to get resource status: {str(e)}'}), 500

@app.route('/resource_agent/tasks/<project_id>')
def get_resource_tasks(project_id):
    """Get task analysis for a project"""
    def fallback():
        return {'tasks': resource_agent.get_task_analysis(project_id)}
    
    try:
        response, status = gateway_client.request(
            f'/resource_agent/tasks/{project_id}',
            method='GET',
            fallback_func=fallback
        )
        return jsonify(response), status
    except Exception as e:
        return jsonify({'error': f'Failed to get task analysis: {str(e)}'}), 500

@app.route('/resource_agent/dependencies/<project_id>')
def get_resource_dependencies(project_id):
    """Get task dependencies for a project"""
    def fallback():
        return {'dependencies': resource_agent.get_task_dependencies(project_id)}
    
    try:
        response, status = gateway_client.request(
            f'/resource_agent/dependencies/{project_id}',
            method='GET',
            fallback_func=fallback
        )
        return jsonify(response), status
    except Exception as e:
        return jsonify({'error': f'Failed to get dependencies: {str(e)}'}), 500

@app.route('/resource_agent/critical_path/<project_id>')
def get_resource_critical_path(project_id):
    """Get critical path for a project"""
    def fallback():
        return {'critical_path': resource_agent.get_critical_path(project_id)}
    
    try:
        response, status = gateway_client.request(
            f'/resource_agent/critical_path/{project_id}',
            method='GET',
            fallback_func=fallback
        )
        return jsonify(response), status
    except Exception as e:
        return jsonify({'error': f'Failed to get critical path: {str(e)}'}), 500

@app.route('/resource_agent/work_team/<project_id>', methods=['GET'])
def get_work_team(project_id):
    """Get work team for a project"""
    def fallback():
        return {'work_team': resource_agent.get_work_team(project_id)}
    
    try:
        response, status = gateway_client.request(
            f'/resource_agent/work_team/{project_id}',
            method='GET',
            fallback_func=fallback
        )
        return jsonify(response), status
    except Exception as e:
        return jsonify({'error': f'Failed to get work team: {str(e)}'}), 500

@app.route('/resource_agent/work_team/<project_id>', methods=['POST'])
def add_work_team_member(project_id):
    """Add a work team member"""
    def fallback():
        data = request.get_json()
        if not data or 'name' not in data:
            return {'error': 'name is required'}, 400
        
        result = resource_agent.resource_optimization_agent.add_work_team_member(
            project_id,
            data['name'],
            data.get('type', 'person')
        )
        return result
    
    try:
        response, status = gateway_client.request(
            f'/resource_agent/work_team/{project_id}',
            method='POST',
            data=request.get_json(),
            fallback_func=fallback
        )
        return jsonify(response), status
    except Exception as e:
        return jsonify({'error': f'Failed to add work team member: {str(e)}'}), 500

@app.route('/resource_agent/work_team/<team_member_id>', methods=['PUT'])
def update_work_team_member(team_member_id):
    """Update a work team member"""
    def fallback():
        data = request.get_json()
        if not data:
            return {'error': 'Request body is required'}, 400
        
        success = resource_agent.resource_optimization_agent.update_work_team_member(
            team_member_id,
            data
        )
        return {'success': success}
    
    try:
        response, status = gateway_client.request(
            f'/resource_agent/work_team/{team_member_id}',
            method='PUT',
            data=request.get_json(),
            fallback_func=fallback
        )
        return jsonify(response), status
    except Exception as e:
        return jsonify({'error': f'Failed to update work team member: {str(e)}'}), 500

@app.route('/resource_agent/work_team/<team_member_id>', methods=['DELETE'])
def delete_work_team_member(team_member_id):
    """Delete a work team member"""
    def fallback():
        success = resource_agent.resource_optimization_agent.delete_work_team_member(team_member_id)
        return {'success': success}
    
    try:
        response, status = gateway_client.request(
            f'/resource_agent/work_team/{team_member_id}',
            method='DELETE',
            fallback_func=fallback
        )
        return jsonify(response), status
    except Exception as e:
        return jsonify({'error': f'Failed to delete work team member: {str(e)}'}), 500

@app.route('/resource_agent/financial_summary/<project_id>')
def get_resource_financial_summary(project_id):
    """Get financial summary for resource allocation"""
    def fallback():
        return resource_agent.get_financial_summary(project_id)
    
    try:
        response, status = gateway_client.request(
            f'/resource_agent/financial_summary/{project_id}',
            method='GET',
            fallback_func=fallback
        )
        return jsonify(response), status
    except Exception as e:
        return jsonify({'error': f'Failed to get financial summary: {str(e)}'}), 500

@app.route('/resource_agent/assign_resources/<project_id>', methods=['POST'])
def assign_resources(project_id):
    """AI-based resource assignment"""
    def fallback():
        result = resource_agent.resource_optimization_agent.assign_resources_ai(
            project_id,
            llm_manager
        )
        return result
    
    try:
        response, status = gateway_client.request(
            f'/resource_agent/assign_resources/{project_id}',
            method='POST',
            fallback_func=fallback
        )
        return jsonify(response), status
    except Exception as e:
        return jsonify({'error': f'Failed to assign resources: {str(e)}'}), 500

@app.route('/resource_agent/resource_assignment/<team_member_id>', methods=['PUT'])
def update_resource_assignment(team_member_id):
    """Manually update resource assignment"""
    def fallback():
        data = request.get_json()
        if not data or 'amount' not in data:
            return {'error': 'amount is required'}, 400
        
        success = resource_agent.resource_optimization_agent.update_resource_assignment(
            team_member_id,
            float(data['amount'])
        )
        return {'success': success}
    
    try:
        response, status = gateway_client.request(
            f'/resource_agent/resource_assignment/{team_member_id}',
            method='PUT',
            data=request.get_json(),
            fallback_func=fallback
        )
        return jsonify(response), status
    except Exception as e:
        return jsonify({'error': f'Failed to update resource assignment: {str(e)}'}), 500

@app.route('/resource_agent/refresh/<project_id>', methods=['POST'])
def refresh_resource_data(project_id):
    """Refresh resource data for a project"""
    def fallback():
        return resource_agent.refresh_resource_data(project_id)
    
    try:
        response, status = gateway_client.request(
            f'/resource_agent/refresh/{project_id}',
            method='POST',
            fallback_func=fallback
        )
        return jsonify(response), status
    except Exception as e:
        return jsonify({'error': f'Failed to refresh resource data: {str(e)}'}), 500

# ===== Risk Mitigation Agent Routes =====

@app.route('/risk_mitigation/dashboard/<project_id>')
def risk_mitigation_dashboard(project_id):
    """Render risk mitigation dashboard"""
    def fallback():
        return render_template('risk_mitigation_dashboard.html', project_id=project_id)
    
    try:
        response, status = gateway_client.request(
            f'/risk_mitigation/dashboard/{project_id}',
            method='GET',
            fallback_func=fallback
        )
        if status == 200 and isinstance(response, str):
            return response
        return render_template('risk_mitigation_dashboard.html', project_id=project_id)
    except Exception as e:
        return render_template('risk_mitigation_dashboard.html', project_id=project_id)

@app.route('/risk_mitigation/what_if_simulator/<project_id>')
def what_if_simulator(project_id):
    """Render What If Scenario Simulator page"""
    def fallback():
        return render_template('what_if_simulator.html', project_id=project_id)
    
    try:
        response, status = gateway_client.request(
            f'/risk_mitigation/what_if_simulator/{project_id}',
            method='GET',
            fallback_func=fallback
        )
        if status == 200 and isinstance(response, str):
            return response
        return render_template('what_if_simulator.html', project_id=project_id)
    except Exception as e:
        return render_template('what_if_simulator.html', project_id=project_id)

@app.route('/api/risk_mitigation/what_if_simulator/<project_id>', methods=['GET'])
def get_what_if_simulator_data(project_id):
    """Get What If Simulator data (bottlenecks + graph)"""
    def fallback():
        result = risk_mitigation_agent.get_what_if_simulator_data(project_id)
        return result
    
    try:
        response, status = gateway_client.request(
            f'/api/risk_mitigation/what_if_simulator/{project_id}',
            method='GET',
            fallback_func=fallback
        )
        return jsonify(response), status
    except Exception as e:
        return jsonify({'error': f'Failed to get What If Simulator data: {str(e)}'}), 500

@app.route('/api/risk_mitigation/mitigation/<project_id>/<bottleneck_id>', methods=['POST'])
def get_mitigation_suggestions(project_id, bottleneck_id):
    """Get mitigation suggestions for a bottleneck"""
    def fallback():
        result = risk_mitigation_agent.get_mitigation_suggestions(project_id, bottleneck_id)
        return result
    
    try:
        response, status = gateway_client.request(
            f'/api/risk_mitigation/mitigation/{project_id}/{bottleneck_id}',
            method='POST',
            data=request.get_json(),
            fallback_func=fallback
        )
        return jsonify(response), status
    except Exception as e:
        return jsonify({'error': f'Failed to get mitigation suggestions: {str(e)}'}), 500

@app.route('/api/risk_mitigation/consequences/<project_id>/<bottleneck_id>', methods=['POST'])
def get_consequences(project_id, bottleneck_id):
    """Get consequences for a bottleneck"""
    def fallback():
        result = risk_mitigation_agent.get_consequences(project_id, bottleneck_id)
        return result
    
    try:
        response, status = gateway_client.request(
            f'/api/risk_mitigation/consequences/{project_id}/{bottleneck_id}',
            method='POST',
            data=request.get_json(),
            fallback_func=fallback
        )
        return jsonify(response), status
    except Exception as e:
        return jsonify({'error': f'Failed to get consequences: {str(e)}'}), 500

@app.route('/api/risk_mitigation/check_generation_status/<project_id>', methods=['GET'])
def api_risk_mitigation_check_status(project_id):
    """API endpoint to check if first-time generation has been run"""
    def fallback():
        result = risk_mitigation_agent.check_generation_status(project_id)
        return jsonify(result)
    
    try:
        response, status = gateway_client.request(
            f'/api/risk_mitigation/check_generation_status/{project_id}',
            method='GET',
            fallback_func=fallback
        )
        return jsonify(response), status
    except Exception as e:
        return fallback()

@app.route('/api/risk_mitigation/first_generation', methods=['POST'])
def risk_mitigation_first_generation():
    """First-time generation of risk mitigation data for a project"""
    def fallback():
        data = request.get_json()
        if not data or 'project_id' not in data:
            return {'error': 'project_id is required'}, 400
        result = risk_mitigation_agent.initialize_risk_analysis(data['project_id'])
        return result
    
    try:
        response, status = gateway_client.request(
            '/api/risk_mitigation/first_generation',
            method='POST',
            data=request.get_json(),
            fallback_func=fallback
        )
        return jsonify(response), status
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/risk_mitigation/risk_summary/<project_id>', methods=['GET'])
def get_risk_summary(project_id):
    """Get risk summary for a project"""
    def fallback():
        result = risk_mitigation_agent.get_risk_summary(project_id)
        return result
    
    try:
        response, status = gateway_client.request(
            f'/api/risk_mitigation/risk_summary/{project_id}',
            method='GET',
            fallback_func=fallback
        )
        return jsonify(response), status
    except Exception as e:
        return jsonify({'error': f'Failed to get risk summary: {str(e)}'}), 500

# ========== CSV Analysis Agent Routes ==========

@app.route('/csv_analysis/<project_id>')
def csv_analysis_page(project_id):
    """CSV Analysis main page"""
    try:
        project = db_manager.get_project(project_id)
        if not project:
            return "Project not found", 404
        
        return render_template('csv_analysis.html', project=project, project_id=project_id)
        
    except Exception as e:
        return f"Error loading CSV analysis: {str(e)}", 500

@app.route('/csv_analysis/upload/<project_id>', methods=['POST'])
def upload_csv(project_id):
    """Upload CSV file for analysis"""
    def fallback():
        if 'file' not in request.files:
            return {'success': False, 'error': 'No file provided'}, 400
        
        file = request.files['file']
        
        if file.filename == '':
            return {'success': False, 'error': 'No file selected'}, 400
        
        if not file.filename.endswith('.csv'):
            return {'success': False, 'error': 'File must be a CSV'}, 400
        
        # Save uploaded file temporarily
        upload_dir = 'data/csv_sessions/uploads'
        os.makedirs(upload_dir, exist_ok=True)
        
        temp_filename = f"{uuid.uuid4().hex[:8]}_{file.filename}"
        temp_path = os.path.join(upload_dir, temp_filename)
        file.save(temp_path)
        
        # Process with CSV Analysis Agent
        result = csv_analysis_agent.upload_csv(project_id, temp_path)
        
        # Clean up temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)
        
        result = sanitize_for_json(result)
        return result
    
    try:
        # Handle file upload through gateway
        if 'file' in request.files:
            file = request.files['file']
            response, status = gateway_client.request(
                f'/csv_analysis/upload?project_id={project_id}',
                method='POST',
                files={'file': file},
                data={'project_id': project_id},
                fallback_func=fallback
            )
        else:
            # No file, use fallback
            response, status = fallback()
        
        return jsonify(response), status
    except Exception as e:
        return jsonify({'success': False, 'error': f'Upload error: {str(e)}'}), 500

@app.route('/csv_analysis/data/<project_id>/<session_id>')
def get_csv_data(project_id, session_id):
    """Get CSV data for a session"""
    try:
        result = csv_analysis_agent.get_csv_data(project_id, session_id)
        
        # Sanitize result to handle NaN values
        result = sanitize_for_json(result)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 404
            
    except Exception as e:
        return jsonify({'success': False, 'error': f'Data retrieval error: {str(e)}'}), 500

@app.route('/csv_analysis/update/<project_id>/<session_id>', methods=['POST'])
def update_csv_data(project_id, session_id):
    """Update CSV data in session"""
    def fallback():
        data = request.get_json()
        
        if not data or 'data' not in data:
            return {'success': False, 'error': 'No data provided'}, 400
        
        updated_data = data['data']
        operation = data.get('operation', 'edit')
        
        result = csv_analysis_agent.update_csv_data(
            project_id,
            session_id,
            updated_data,
            operation
        )
        
        return result
    
    try:
        request_data = request.get_json()
        request_data['project_id'] = project_id
        request_data['session_id'] = session_id
        
        response, status = gateway_client.request(
            f'/csv_analysis/update?project_id={project_id}&session_id={session_id}',
            method='POST',
            data=request_data,
            fallback_func=fallback
        )
        return jsonify(response), status
    except Exception as e:
        return jsonify({'success': False, 'error': f'Update error: {str(e)}'}), 500

@app.route('/csv_analysis/ask/<project_id>/<session_id>', methods=['POST'])
def ask_csv_question(project_id, session_id):
    """Ask question about CSV data"""
    def fallback():
        data = request.get_json()
        
        if not data or 'question' not in data:
            return {'success': False, 'error': 'No question provided'}, 400
        
        question = data['question']
        selected_cells = data.get('selected_cells', [])
        include_project_context = data.get('context_type') == 'with_project_data'
        
        result = csv_analysis_agent.ask_question(
            project_id,
            session_id,
            question,
            selected_cells,
            include_project_context
        )
        
        result = sanitize_for_json(result)
        return result
    
    try:
        request_data = request.get_json()
        request_data['project_id'] = project_id
        request_data['session_id'] = session_id
        
        response, status = gateway_client.request(
            f'/csv_analysis/ask?project_id={project_id}&session_id={session_id}',
            method='POST',
            data=request_data,
            fallback_func=fallback
        )
        return jsonify(response), status
    except Exception as e:
        return jsonify({'success': False, 'error': f'Q&A error: {str(e)}'}), 500

@app.route('/csv_analysis/export/<project_id>/<session_id>')
def export_csv_data(project_id, session_id):
    """Export CSV data"""
    def fallback():
        export_format = request.args.get('format', 'csv')
        filename = request.args.get('filename', None)
        
        result = csv_analysis_agent.export_csv(
            project_id,
            session_id,
            export_format,
            filename
        )
        
        if result['success']:
            # Send file for download
            file_path = result['file_path']
            filename = result['filename']
            
            with open(file_path, 'rb') as f:
                file_data = f.read()
            
            response = make_response(file_data)
            response.headers['Content-Disposition'] = f'attachment; filename={filename}'
            response.headers['Content-Type'] = 'text/csv'
            
            return response
        else:
            return result, 400
    
    try:
        response, status = gateway_client.request(
            f'/csv_analysis/export?project_id={project_id}&session_id={session_id}',
            method='GET',
            params=request.args.to_dict(),
            fallback_func=fallback
        )
        if isinstance(response, bytes) or (isinstance(response, dict) and 'file_data' in response):
            # Handle file download response
            if isinstance(response, dict):
                file_data = response['file_data']
                filename = response.get('filename', 'export.csv')
            else:
                file_data = response
                filename = request.args.get('filename', 'export.csv')
            
            export_response = make_response(file_data)
            export_response.headers['Content-Disposition'] = f'attachment; filename={filename}'
            export_response.headers['Content-Type'] = 'text/csv'
            return export_response
        else:
            return jsonify(response), status
    except Exception as e:
        return jsonify({'success': False, 'error': f'Export error: {str(e)}'}), 500

@app.route('/csv_analysis/financial_context/<project_id>')
def get_csv_financial_context(project_id):
    """Get financial context for CSV analysis"""
    def fallback():
        result = csv_analysis_agent.get_financial_context(project_id)
        return result
    
    try:
        response, status = gateway_client.request(
            f'/csv_analysis/financial_context/{project_id}',
            method='GET',
            fallback_func=fallback
        )
        return jsonify(response), status
    except Exception as e:
        return jsonify({'success': False, 'error': f'Context error: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)  # Changed to port 5001 to avoid conflict with API Gateway






