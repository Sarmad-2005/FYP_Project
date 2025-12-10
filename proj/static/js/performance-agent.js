// Performance Agent JavaScript Functions

// Global variables
let currentProjectId = null;
let currentDocumentId = null;
let isPerformanceLoading = false;

// Initialize Performance Agent
function initPerformanceAgent() {
    // Get current project ID from the page
    // Check if it's already set by the page-specific script first
    if (!currentProjectId || !window.currentProjectId) {
        currentProjectId = getCurrentProjectId();
    } else {
        currentProjectId = window.currentProjectId;
    }
    
    // Only load if we have a project ID
    if (currentProjectId) {
        // Load initial performance data
        loadPerformanceData();
        
        // Set up auto-refresh every 30 seconds
        setInterval(loadPerformanceData, 30000);
    }
}

// Get current project ID
function getCurrentProjectId() {
    // First check if already set globally
    if (window.currentProjectId) {
        return window.currentProjectId;
    }
    
    // Try to get from URL - handles both /project/<id> and /performance_agent/dashboard/<id>
    const pathParts = window.location.pathname.split('/');
    if (pathParts.includes('project') && pathParts.length > 2) {
        return pathParts[pathParts.indexOf('project') + 1];
    }
    if (pathParts.includes('dashboard') && pathParts.length > 3) {
        return pathParts[pathParts.indexOf('dashboard') + 1];
    }
    
    // Try to get from hidden input
    const projectInput = document.querySelector('input[name="project_id"]');
    if (projectInput) {
        return projectInput.value;
    }
    
    // Try to get from data attribute
    const projectElement = document.querySelector('[data-project-id]');
    if (projectElement) {
        return projectElement.getAttribute('data-project-id');
    }
    
    return null;
}

// Get current document ID (if available)
function getCurrentDocumentId() {
    // Try to get document ID from hidden input first (if exists)
    const documentInput = document.querySelector('input[name="document_id"]');
    if (documentInput && documentInput.value) {
        return documentInput.value;
    }
    // Try first-doc-id injected in template
    const firstDocInput = document.getElementById('first-doc-id');
    if (firstDocInput && firstDocInput.value) {
        console.log('📄 Using first-doc-id from template:', firstDocInput.value);
        return firstDocInput.value;
    }
    
    // Otherwise, extract from first document's "View Embeddings" button
    const viewEmbeddingsBtn = document.querySelector('button[onclick^="viewEmbeddings"]');
    if (viewEmbeddingsBtn) {
        const onclickAttr = viewEmbeddingsBtn.getAttribute('onclick');
        // Extract ID from: viewEmbeddings('some-uuid-here')
        const match = onclickAttr.match(/viewEmbeddings\('([^']+)'\)/);
        if (match && match[1]) {
            console.log('📄 Found document ID from page:', match[1]);
            return match[1];
        }
    }
    
    console.warn('⚠️ No document ID found on page');
    return null;
}

// Load performance data (READ-ONLY for auto-refresh)
async function loadPerformanceData() {
    // Always check for current project ID (might be set by page-specific script)
    if (!currentProjectId && window.currentProjectId) {
        currentProjectId = window.currentProjectId;
    }
    
    if (!currentProjectId) {
        console.warn('No project ID available for performance data');
        return;
    }
    
    try {
        console.log('📊 [Global] Fetching quick status for project:', currentProjectId);
        // Use quick_status for auto-refresh (no processing, just reads current data)
        const response = await fetch(`/performance_agent/quick_status/${currentProjectId}`);
        const data = await response.json();
        
        console.log('📊 [Global] Received data:', data);
        
        if (data.success) {
            updatePerformanceMetrics(data);
        } else {
            console.warn('Failed to load performance data:', data.error);
        }
    } catch (error) {
        console.error('Error loading performance data:', error);
    }
}

// Helper function to escape HTML
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = String(text);
    return div.innerHTML;
}

// Update performance metrics display
function updatePerformanceMetrics(data) {
    // Update milestone count
    const milestonesCount = document.getElementById('milestones-count');
    if (milestonesCount) {
        milestonesCount.textContent = data.milestones?.count || 0;
    }
    
    // Update task count
    const tasksCount = document.getElementById('tasks-count');
    if (tasksCount) {
        tasksCount.textContent = data.tasks?.count || 0;
    }
    
    // Update bottleneck count
    const bottlenecksCount = document.getElementById('bottlenecks-count');
    if (bottlenecksCount) {
        bottlenecksCount.textContent = data.bottlenecks?.count || 0;
    }

    // Helper function to strip markdown formatting
    function stripMarkdown(text) {
        if (!text) return '';
        return String(text)
            .replace(/\*\*([^*]+)\*\*/g, '$1')  // Remove **bold**
            .replace(/\*([^*]+)\*/g, '$1')      // Remove *italic*
            .replace(/__([^_]+)__/g, '$1')       // Remove __bold__
            .replace(/_([^_]+)_/g, '$1')        // Remove _italic_
            .replace(/`([^`]+)`/g, '$1')        // Remove `code`
            .replace(/\[([^\]]+)\]\([^\)]+\)/g, '$1')  // Remove [link](url)
            .trim();
    }

    // Update requirements count/details
    const requirementsCount = document.getElementById('requirements-count');
    if (requirementsCount) {
        requirementsCount.textContent = data.requirements?.count || 0;
    }
    const requirementsDetails = document.getElementById('requirements-details');
    const reqList = data.requirements?.requirements || data.requirements?.items || [];
    console.log('📋 [Global] Requirements data:', reqList);
    if (requirementsDetails && Array.isArray(reqList) && reqList.length > 0) {
        requirementsDetails.innerHTML = reqList.map(req => {
            // Data structure: {id, content, metadata: {priority, category, ...}}
            let reqText = req.content || req.text || req.requirement || 'Requirement';
            reqText = stripMarkdown(reqText);
            const priority = req.metadata?.priority || req.priority || 'Medium';
            const category = req.metadata?.category || req.category || 'General';
            
            // Determine priority badge color
            let priorityClass = 'priority-medium';
            if (priority.toLowerCase() === 'high') priorityClass = 'priority-high';
            else if (priority.toLowerCase() === 'low') priorityClass = 'priority-low';
            
            return `
                <div class="req-item-card">
                    <div class="req-item-header">
                        <span class="req-category-badge">${escapeHtml(category)}</span>
                        <span class="req-priority-badge ${priorityClass}">${escapeHtml(priority)}</span>
                    </div>
                    <div class="req-item-content">${escapeHtml(reqText)}</div>
                </div>
            `;
        }).join('') || '<p class="text-gray-600">No requirements identified yet.</p>';
    } else if (requirementsDetails && (!reqList || reqList.length === 0)) {
        requirementsDetails.innerHTML = '<p class="text-gray-600">No requirements identified yet.</p>';
    }

    // Update actors count/details
    const actorsCount = document.getElementById('actors-count');
    if (actorsCount) {
        actorsCount.textContent = data.actors?.count || 0;
    }
    const actorsDetails = document.getElementById('actors-details');
    const actorList = data.actors?.actors || data.actors?.items || [];
    console.log('👥 [Global] Actors data:', actorList);
    if (actorsDetails && Array.isArray(actorList) && actorList.length > 0) {
        actorsDetails.innerHTML = actorList.map(actor => {
            // Data structure: {id, content, metadata: {actor_type, role, ...}}
            let actorName = actor.content || actor.text || actor.name || 'Actor';
            actorName = stripMarkdown(actorName);
            const role = actor.metadata?.role || actor.role || '';
            const type = actor.metadata?.actor_type || actor.actor_type || 'Person';
            
            // Determine type badge color
            let typeClass = 'actor-type-person';
            if (type.toLowerCase().includes('organization')) typeClass = 'actor-type-org';
            else if (type.toLowerCase().includes('team')) typeClass = 'actor-type-team';
            else if (type.toLowerCase().includes('vendor')) typeClass = 'actor-type-vendor';
            else if (type.toLowerCase().includes('client')) typeClass = 'actor-type-client';
            
            return `
                <div class="actor-item-card">
                    <div class="actor-item-header">
                        <span class="actor-type-badge ${typeClass}">${escapeHtml(type)}</span>
                    </div>
                    <div class="actor-item-name">${escapeHtml(actorName)}</div>
                    ${role ? `<div class="actor-item-role">${escapeHtml(role)}</div>` : ''}
                </div>
            `;
        }).join('') || '<p class="text-gray-600">No actors identified yet.</p>';
    } else if (actorsDetails && (!actorList || actorList.length === 0)) {
        actorsDetails.innerHTML = '<p class="text-gray-600">No actors identified yet.</p>';
    }
    
    // Update completion score
    const completionScore = data.completion_score || 0;
    updateCompletionScore(completionScore);
    
    // Update last analysis timestamp if available
    if (data.last_analysis) {
        updateLastAnalysisTimestamp(data.last_analysis);
    }
}

// Update completion score display
function updateCompletionScore(score) {
    const percentageElement = document.getElementById('completion-percentage');
    const progressElement = document.getElementById('completion-progress');
    const badgeElement = document.getElementById('completion-badge');
    
    if (percentageElement) {
        percentageElement.textContent = Math.round(score) + '%';
    }
    
    if (progressElement) {
        progressElement.style.width = score + '%';
    }
    
    if (badgeElement) {
        badgeElement.textContent = getCompletionStatus(score);
        badgeElement.className = 'score-badge ' + getCompletionBadgeClass(score);
    }
}

// Get completion status text
function getCompletionStatus(score) {
    if (score >= 80) return 'Excellent';
    if (score >= 60) return 'Good';
    if (score >= 40) return 'Fair';
    if (score >= 20) return 'Needs Improvement';
    return 'Not Started';
}

// Get completion badge class
function getCompletionBadgeClass(score) {
    if (score >= 80) return 'badge-success';
    if (score >= 60) return 'badge-warning';
    if (score >= 40) return 'badge-info';
    return 'badge-danger';
}

// Update last analysis timestamp
function updateLastAnalysisTimestamp(timestamp) {
    const timestampElement = document.getElementById('last-analysis-timestamp');
    if (timestampElement) {
        const date = new Date(timestamp);
        timestampElement.textContent = 'Last updated: ' + date.toLocaleString();
    }
}

// Generate Performance Analysis
window.generatePerformanceAnalysis = async function() {
    if (isPerformanceLoading) {
        return;
    }
    
    if (!currentProjectId) {
        showAlert('No project selected', 'error');
        return;
    }
    
    // Get the first document ID if available
    const documentId = getCurrentDocumentId();
    if (!documentId) {
        showAlert('Please upload a document first', 'error');
        return;
    }
    
    showPerformanceLoading();
    
    console.log('🚀 Starting AI Analysis...');
    console.log('📁 Project ID:', currentProjectId);
    console.log('📄 Document ID:', documentId);
    
    showAlert('🤖 Analyzing document with AI... This may take 1-2 minutes', 'info');
    
    try {
        console.log('📡 Sending request to backend...');
        console.time('⏱️ Analysis Duration');
        
        const response = await fetch('/performance_agent/first_generation', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                project_id: currentProjectId,
                document_id: documentId
            })
        });
        
        console.log('📨 Response received! Status:', response.status);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        console.timeEnd('⏱️ Analysis Duration');
        
        console.log('📊 Full Analysis Results:', data);
        
        // Log detailed results
        if (data.milestones) {
            console.log(`  ✅ Milestones: ${data.milestones.count || 0} found, ${data.milestones.details_count || 0} detailed`);
        }
        if (data.tasks) {
            console.log(`  ✅ Tasks: ${data.tasks.count || 0} found, ${data.tasks.details_count || 0} detailed`);
        }
        if (data.bottlenecks) {
            console.log(`  ✅ Bottlenecks: ${data.bottlenecks.count || 0} found, ${data.bottlenecks.details_count || 0} detailed`);
        }
        if (data.completion_score !== undefined) {
            console.log(`  🎯 Completion Score: ${data.completion_score}%`);
        }
        
        if (data.success || data.overall_success) {
            updatePerformanceMetrics(data);
            showAlert('✅ AI analysis completed successfully!', 'success');
            console.log('✅ Analysis SUCCESS - Metrics updated!');
        } else {
            showAlert('⚠️ Analysis completed with issues: ' + (data.error || 'Check console'), 'warning');
            console.warn('⚠️ Analysis had issues:', data);
        }
    } catch (error) {
        console.error('❌ ERROR during analysis:', error);
        console.error('Error stack:', error.stack);
        showAlert('❌ Error: ' + error.message, 'error');
    } finally {
        hidePerformanceLoading();
        console.log('🏁 Analysis process complete');
    }
};

// View Performance Dashboard
window.viewPerformanceDashboard = function() {
    if (!currentProjectId) {
        showAlert('No project selected', 'error');
        return;
    }
    
    window.open(`/performance_agent/dashboard/${currentProjectId}`, '_blank');
};

// Refresh Performance Data (MANUAL - Full Processing)
// Processes new documents and updates all performance metrics immediately
window.refreshPerformanceData = async function() {
    if (isPerformanceLoading) {
        return;
    }
    
    if (!currentProjectId) {
        showAlert('No project selected', 'error');
        return;
    }
    
    showPerformanceLoading();
    
    try {
        console.log('🔄 Starting FULL performance update with AI processing...');
        
        // Show initial alert that this may take time
        showAlert('🔄 Processing new documents with AI... This may take 1-2 minutes for new documents.', 'info');
        
        // Use the FULL processing endpoint (not quick_status)
        const response = await fetch(`/performance_agent/status/${currentProjectId}`);
        const data = await response.json();
        
        if (data.success) {
            updatePerformanceMetrics(data);
            
            // Show detailed success message
            if (data.new_documents_processed > 0) {
                showAlert(`✅ Processed ${data.new_documents_processed} new document(s) successfully!`, 'success');
            } else {
                showAlert('✅ No new documents to process - data is up to date!', 'success');
            }
            console.log('✅ Full refresh complete:', data);
        } else {
            showAlert(`❌ Error: ${data.error}`, 'error');
        }
    } catch (error) {
        console.error('❌ Error refreshing performance data:', error);
        showAlert('❌ Error updating metrics: ' + error.message, 'error');
    } finally {
        hidePerformanceLoading();
    }
}

// Export Performance Report
async function exportPerformanceReport() {
    if (!currentProjectId) {
        showAlert('No project selected', 'error');
        return;
    }
    
    try {
        const response = await fetch(`/performance_agent/export/${currentProjectId}`);
        
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `performance-report-${currentProjectId}.json`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            showAlert('Report exported successfully!', 'success');
        } else {
            showAlert('Failed to export report', 'error');
        }
    } catch (error) {
        console.error('Error exporting report:', error);
        showAlert('Error exporting report: ' + error.message, 'error');
    }
}

// Show Performance Loading State
function showPerformanceLoading() {
    isPerformanceLoading = true;
    const container = document.querySelector('.performance-agent-container');
    if (container) {
        container.classList.add('performance-loading');
    }
    
    // Disable action buttons
    const buttons = document.querySelectorAll('.performance-actions .btn');
    buttons.forEach(btn => {
        btn.disabled = true;
        btn.classList.add('loading');
    });
}

// Hide Performance Loading State
function hidePerformanceLoading() {
    isPerformanceLoading = false;
    const container = document.querySelector('.performance-agent-container');
    if (container) {
        container.classList.remove('performance-loading');
    }
    
    // Enable action buttons
    const buttons = document.querySelectorAll('.performance-actions .btn');
    buttons.forEach(btn => {
        btn.disabled = false;
        btn.classList.remove('loading');
    });
};

// Toggle Performance Details
window.togglePerformanceDetails = function() {
    const container = document.querySelector('.performance-agent-container');
    if (container) {
        container.classList.toggle('expanded');
    }
};

// Update Metric Cards with Animation
function updateMetricCards(data) {
    const cards = document.querySelectorAll('.metric-card');
    cards.forEach((card, index) => {
        card.style.animation = 'none';
        setTimeout(() => {
            card.style.animation = 'slideInUp 0.6s ease-out';
        }, index * 100);
    });
}

// Show Alert Function (if not already defined in base.html)
if (typeof window.showAlert !== 'function') {
    window.showAlert = function(message, type = 'info') {
        // Fallback alert implementation
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type}`;
        alertDiv.textContent = message;
        alertDiv.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 1000;
            padding: 12px 20px;
            border-radius: 8px;
            color: white;
            font-weight: 500;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            animation: slideInRight 0.3s ease-out;
        `;
        
        if (type === 'success') {
            alertDiv.style.background = 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)';
        } else if (type === 'error') {
            alertDiv.style.background = 'linear-gradient(135deg, #fa709a 0%, #fee140 100%)';
        } else {
            alertDiv.style.background = 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)';
        }
        
        document.body.appendChild(alertDiv);
        
        setTimeout(() => {
            alertDiv.style.animation = 'slideOutRight 0.3s ease-out';
            setTimeout(() => {
                document.body.removeChild(alertDiv);
            }, 300);
        }, 3000);
    };
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initPerformanceAgent();
});

// Add CSS for animations if not already present
if (!document.querySelector('#performance-agent-animations')) {
    const style = document.createElement('style');
    style.id = 'performance-agent-animations';
    style.textContent = `
        @keyframes slideInRight {
            from { transform: translateX(100%); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
        @keyframes slideOutRight {
            from { transform: translateX(0); opacity: 1; }
            to { transform: translateX(100%); opacity: 0; }
        }
        .performance-loading .btn {
            position: relative;
        }
        .performance-loading .btn::after {
            content: '';
            position: absolute;
            top: 50%;
            left: 50%;
            width: 16px;
            height: 16px;
            margin: -8px 0 0 -8px;
            border: 2px solid transparent;
            border-top: 2px solid currentColor;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    `;
    document.head.appendChild(style);
}
