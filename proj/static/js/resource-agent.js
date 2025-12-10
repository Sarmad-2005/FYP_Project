// Resource Agent JavaScript Functions

// Global variables
let currentProjectId = null;
let currentDocumentId = null;
let dependenciesNetwork = null;
let criticalPathNetwork = null;
let taskAnalysisData = [];
let dependenciesData = [];
let criticalPathData = null;

// Initialize Resource Dashboard
function loadResourceDashboard(projectId) {
    currentProjectId = projectId;
    
    // Load all data
    loadTaskAnalysis();
    loadDependencies();
    loadCriticalPath();
    loadWorkTeam();
    loadFinancialSummary();
}

// Load Task Analysis
async function loadTaskAnalysis() {
    try {
        const response = await fetch(`/resource_agent/tasks/${currentProjectId}`);
        const data = await response.json();
        
        if (data.tasks && data.tasks.length > 0) {
            taskAnalysisData = data.tasks;
            renderTaskAnalysis(data.tasks);
            document.getElementById('task-analysis-count').textContent = `${data.tasks.length} tasks analyzed`;
        } else {
            document.getElementById('task-analysis-container').innerHTML = 
                '<div class="text-center p-8 text-gray-500 col-span-full">No task analysis available. Run first generation first.</div>';
        }
    } catch (error) {
        console.error('Error loading task analysis:', error);
        document.getElementById('task-analysis-tbody').innerHTML = 
            '<tr><td colspan="4" class="text-center text-red-500">Error loading task analysis</td></tr>';
    }
}

// Render Task Analysis Cards
function renderTaskAnalysis(tasks) {
    const container = document.getElementById('task-analysis-container');
    container.innerHTML = '';
    
    tasks.forEach(task => {
        const taskName = task.task_name || task.metadata?.task_name || 'Unknown Task';
        const priority = task.priority || task.metadata?.priority || 'Medium';
        const complexity = task.complexity || task.metadata?.complexity || 'Moderate';
        const estimatedTime = task.estimated_time_hours || task.metadata?.estimated_time_hours || 0;
        
        const card = document.createElement('div');
        card.className = 'task-analysis-card';
        
        // Priority color
        let priorityColor = '#3b82f6'; // Medium - blue
        if (priority === 'High') priorityColor = '#ef4444'; // red
        if (priority === 'Low') priorityColor = '#10b981'; // green
        
        // Complexity icon
        let complexityIcon = 'fa-cog';
        if (complexity === 'Simple') complexityIcon = 'fa-circle';
        if (complexity === 'Very Complex') complexityIcon = 'fa-exclamation-triangle';
        
        card.innerHTML = `
            <div class="task-card-header" style="border-left: 4px solid ${priorityColor};">
                <div class="task-card-title">${escapeHtml(taskName)}</div>
                <span class="priority-badge ${priority}">${priority}</span>
            </div>
            <div class="task-card-body">
                <div class="task-card-metric">
                    <i class="fas ${complexityIcon} text-purple-500"></i>
                    <div>
                        <span class="task-card-label">Complexity</span>
                        <span class="task-card-value complexity-badge ${complexity.replace(/\s+/g, '\\ ')}">${complexity}</span>
                    </div>
                </div>
                <div class="task-card-metric">
                    <i class="fas fa-clock text-blue-500"></i>
                    <div>
                        <span class="task-card-label">Estimated Time</span>
                        <span class="task-card-value">${estimatedTime.toFixed(1)}h (${(estimatedTime / 8).toFixed(1)} days)</span>
                    </div>
                </div>
            </div>
        `;
        
        container.appendChild(card);
    });
}

// Load Dependencies
async function loadDependencies() {
    try {
        const response = await fetch(`/resource_agent/dependencies/${currentProjectId}`);
        const data = await response.json();
        
        if (data.dependencies && data.dependencies.length > 0) {
            dependenciesData = data.dependencies;
            renderDependenciesGraph(data.dependencies);
            document.getElementById('dependencies-count').textContent = `${data.dependencies.length} dependencies`;
        } else {
            document.getElementById('dependencies-graph-container').innerHTML = 
                '<div class="text-center p-8 text-gray-500">No dependencies found. Create dependencies first.</div>';
        }
    } catch (error) {
        console.error('Error loading dependencies:', error);
        document.getElementById('dependencies-graph-container').innerHTML = 
            '<div class="text-center p-8 text-red-500">Error loading dependencies</div>';
    }
}

// Render Dependencies Graph
function renderDependenciesGraph(dependencies) {
    const container = document.getElementById('dependencies-graph-container');
    container.innerHTML = '';
    
    // Create a map of task_id to task_name from task analysis data
    const taskNameMap = new Map();
    if (taskAnalysisData && taskAnalysisData.length > 0) {
        taskAnalysisData.forEach(task => {
            const taskId = task.task_id || task.metadata?.task_id;
            const taskName = task.task_name || task.metadata?.task_name;
            if (taskId && taskName) {
                taskNameMap.set(taskId, taskName);
            }
        });
    }
    
    // Helper function to get task name or create a short label
    function getTaskLabel(taskId) {
        if (taskNameMap.has(taskId)) {
            const fullName = taskNameMap.get(taskId);
            // Truncate long names intelligently
            if (fullName.length > 40) {
                return fullName.substring(0, 37) + '...';
            }
            return fullName;
        }
        // If no name found, try to extract from task_id format
        if (taskId && taskId.includes('_')) {
            const parts = taskId.split('_');
            if (parts.length > 1) {
                return `Task ${parts[parts.length - 1].substring(0, 8)}`;
            }
        }
        return taskId ? taskId.substring(0, 20) : 'Unknown';
    }
    
    // Prepare nodes and edges
    const nodes = new vis.DataSet([]);
    const edges = new vis.DataSet([]);
    const nodeMap = new Map();
    
    // Add nodes for all tasks mentioned in dependencies
    dependencies.forEach((dep, index) => {
        const taskId = dep.task_id || dep.metadata?.task_id || `task_${index}`;
        const taskName = getTaskLabel(taskId);
        
        if (!nodeMap.has(taskId)) {
            nodes.add({
                id: taskId,
                label: taskName,
                title: taskNameMap.get(taskId) || taskId,
                color: {
                    background: '#e0e7ff',
                    border: '#6366f1',
                    highlight: { background: '#c7d2fe', border: '#4f46e5' }
                },
                font: { size: 13, face: 'Arial' }
            });
            nodeMap.set(taskId, true);
        }
        
        // Add edges for dependencies
        const dependsOn = dep.depends_on || dep.metadata?.depends_on || [];
        let dependsOnArray = dependsOn;
        
        if (typeof dependsOn === 'string') {
            try {
                dependsOnArray = JSON.parse(dependsOn);
            } catch (e) {
                dependsOnArray = [];
            }
        }
        
        dependsOnArray.forEach(depTaskId => {
            // Ensure dependency node exists
            if (!nodeMap.has(depTaskId)) {
                const depTaskName = getTaskLabel(depTaskId);
                nodes.add({
                    id: depTaskId,
                    label: depTaskName,
                    title: taskNameMap.get(depTaskId) || depTaskId,
                    color: {
                        background: '#e0e7ff',
                        border: '#6366f1',
                        highlight: { background: '#c7d2fe', border: '#4f46e5' }
                    },
                    font: { size: 13, face: 'Arial' }
                });
                nodeMap.set(depTaskId, true);
            }
            
            edges.add({
                from: depTaskId,
                to: taskId,
                arrows: 'to',
                color: { color: '#6366f1', width: 2 },
                smooth: { type: 'continuous', roundness: 0.5 }
            });
        });
    });
    
    // Create network
    const data = { nodes: nodes, edges: edges };
    const options = {
        nodes: {
            shape: 'box',
            font: { 
                size: 14, 
                face: 'Arial', 
                color: '#1f2937',
                bold: true
            },
            margin: 15,
            widthConstraint: { maximum: 220, minimum: 100 },
            heightConstraint: { minimum: 40 },
            borderWidth: 3,
            borderWidthSelected: 4,
            shadow: {
                enabled: true,
                color: 'rgba(99, 102, 241, 0.3)',
                size: 10,
                x: 3,
                y: 3
            },
            color: {
                background: '#e0e7ff',
                border: '#6366f1',
                highlight: {
                    background: '#c7d2fe',
                    border: '#4f46e5'
                },
                hover: {
                    background: '#e0e7ff',
                    border: '#4f46e5'
                }
            },
            chosen: {
                node: function(values, id, selected, hovering) {
                    if (hovering || selected) {
                        values.borderWidth = 4;
                        values.shadow = {
                            enabled: true,
                            color: 'rgba(99, 102, 241, 0.5)',
                            size: 15,
                            x: 4,
                            y: 4
                        };
                    }
                }
            }
        },
        edges: {
            smooth: { 
                type: 'continuous', 
                roundness: 0.6,
                forceDirection: 'vertical'
            },
            font: { 
                size: 12, 
                align: 'middle', 
                color: '#6366f1',
                bold: true,
                strokeWidth: 2,
                strokeColor: '#ffffff'
            },
            width: 3,
            color: {
                color: '#6366f1',
                highlight: '#4f46e5',
                hover: '#818cf8'
            },
            arrows: {
                to: {
                    enabled: true,
                    scaleFactor: 1.3,
                    type: 'arrow',
                    length: 15
                }
            },
            shadow: {
                enabled: true,
                color: 'rgba(99, 102, 241, 0.2)',
                size: 5
            }
        },
        layout: {
            hierarchical: {
                enabled: true,
                direction: 'UD',
                sortMethod: 'directed',
                levelSeparation: 180,
                nodeSpacing: 150,
                treeSpacing: 250,
                blockShifting: true,
                edgeMinimization: true,
                parentCentralization: true
            }
        },
        physics: {
            enabled: false  // Disable physics for hierarchical layout
        },
        interaction: {
            hover: true,
            tooltipDelay: 150,
            zoomView: true,
            dragView: true,
            selectConnectedEdges: true
        },
        configure: {
            enabled: false
        }
    };
    
    dependenciesNetwork = new vis.Network(container, data, options);
    
    // Add event listeners for better UX
    dependenciesNetwork.on("hoverNode", function(params) {
        container.style.cursor = 'pointer';
    });
    dependenciesNetwork.on("blurNode", function(params) {
        container.style.cursor = 'default';
    });
    
    // Add click handler to show node details in inline card
    dependenciesNetwork.on("click", function(params) {
        if (params.nodes.length > 0) {
            const nodeId = params.nodes[0];
            console.log('Dependencies graph node clicked:', nodeId);
            showTaskDetailsCard(nodeId, nodes, taskAnalysisData, dependencies, 'task-details-card', 'task-details-card-content');
        }
    });
}

// Load Critical Path
async function loadCriticalPath() {
    try {
        const response = await fetch(`/resource_agent/critical_path/${currentProjectId}`);
        const data = await response.json();
        
        if (data.critical_path && data.critical_path.path_tasks) {
            criticalPathData = data.critical_path;
            renderCriticalPathGraph(data.critical_path);
            
            const pathTasks = data.critical_path.path_tasks || [];
            const duration = data.critical_path.total_duration_hours || 0;
            
            document.getElementById('critical-path-length').textContent = `${pathTasks.length} tasks`;
            document.getElementById('critical-path-duration').textContent = `${duration.toFixed(1)} hours (${(duration / 8).toFixed(1)} days)`;
        } else {
            document.getElementById('critical-path-graph-container').innerHTML = 
                '<div class="text-center p-8 text-gray-500">No critical path found. Calculate critical path first.</div>';
        }
    } catch (error) {
        console.error('Error loading critical path:', error);
        document.getElementById('critical-path-graph-container').innerHTML = 
            '<div class="text-center p-8 text-red-500">Error loading critical path</div>';
    }
}

// Render Critical Path Graph
function renderCriticalPathGraph(criticalPath) {
    const container = document.getElementById('critical-path-graph-container');
    container.innerHTML = '';
    
    const pathTasks = criticalPath.path_tasks || criticalPath.metadata?.path_tasks || [];
    const taskSchedule = criticalPath.task_schedule || criticalPath.metadata?.task_schedule || {};
    
    // Create task name map from task analysis
    const taskNameMap = new Map();
    if (taskAnalysisData && taskAnalysisData.length > 0) {
        taskAnalysisData.forEach(task => {
            const taskId = task.task_id || task.metadata?.task_id;
            const taskName = task.task_name || task.metadata?.task_name;
            const estimatedTime = task.estimated_time_hours || task.metadata?.estimated_time_hours || 0;
            if (taskId) {
                taskNameMap.set(taskId, { name: taskName, time: estimatedTime });
            }
        });
    }
    
    if (pathTasks.length === 0) {
        container.innerHTML = '<div class="text-center p-8 text-gray-500">No critical path tasks found</div>';
        return;
    }
    
    // Prepare nodes and edges
    const nodes = new vis.DataSet([]);
    const edges = new vis.DataSet([]);
    
    // Add nodes (critical path tasks in red)
    pathTasks.forEach((taskId, index) => {
        let schedule = taskSchedule[taskId] || {};
        
        // If schedule doesn't have task_name, try to get from task analysis
        if (!schedule.task_name && taskNameMap.has(taskId)) {
            const taskInfo = taskNameMap.get(taskId);
            schedule.task_name = taskInfo.name;
            if (!schedule.duration || schedule.duration === 0) {
                schedule.duration = taskInfo.time;
            }
        }
        
        const taskName = schedule.task_name || taskId;
        const duration = schedule.duration || (taskNameMap.has(taskId) ? taskNameMap.get(taskId).time : 0);
        
        // Truncate task name for display
        let displayName = taskName;
        if (displayName.length > 35) {
            displayName = displayName.substring(0, 32) + '...';
        }
        
        nodes.add({
            id: taskId,
            label: `${displayName}\n⏱️ ${duration.toFixed(1)}h (${(duration / 8).toFixed(1)}d)`,
            title: `${taskName}\nDuration: ${duration.toFixed(1)} hours (${(duration / 8).toFixed(1)} days)\nEarliest Start: ${schedule.earliest_start?.toFixed(1) || 0}h\nEarliest Finish: ${schedule.earliest_finish?.toFixed(1) || duration.toFixed(1)}h`,
            color: {
                background: '#fee2e2',
                border: '#dc2626',
                highlight: { background: '#fecaca', border: '#b91c1c' }
            },
            font: { size: 13, face: 'Arial', color: '#991b1b', bold: true },
            shape: 'box',
            margin: 15
        });
        
        // Add edge to next task
        if (index < pathTasks.length - 1) {
            const nextSchedule = taskSchedule[pathTasks[index + 1]] || {};
            const nextDuration = nextSchedule.duration || (taskNameMap.has(pathTasks[index + 1]) ? taskNameMap.get(pathTasks[index + 1]).time : 0);
            
            edges.add({
                from: taskId,
                to: pathTasks[index + 1],
                arrows: 'to',
                color: { color: '#dc2626', width: 4 },
                label: `${duration.toFixed(1)}h`,
                font: { size: 12, color: '#dc2626', bold: true, align: 'middle' },
                smooth: { type: 'continuous', roundness: 0.5 }
            });
        }
    });
    
    // Create network
    const data = { nodes: nodes, edges: edges };
    const options = {
        nodes: {
            shape: 'box',
            font: { 
                size: 14, 
                face: 'Arial', 
                color: '#991b1b', 
                bold: true 
            },
            margin: 18,
            widthConstraint: { maximum: 280, minimum: 120 },
            heightConstraint: { minimum: 60 },
            borderWidth: 4,
            borderWidthSelected: 5,
            shadow: { 
                enabled: true, 
                color: 'rgba(220, 38, 38, 0.4)', 
                size: 12, 
                x: 4, 
                y: 4 
            },
            color: {
                background: '#fee2e2',
                border: '#dc2626',
                highlight: {
                    background: '#fecaca',
                    border: '#b91c1c'
                },
                hover: {
                    background: '#fee2e2',
                    border: '#b91c1c'
                }
            },
            chosen: {
                node: function(values, id, selected, hovering) {
                    if (hovering || selected) {
                        values.borderWidth = 5;
                        values.shadow = {
                            enabled: true,
                            color: 'rgba(220, 38, 38, 0.6)',
                            size: 18,
                            x: 5,
                            y: 5
                        };
                    }
                }
            }
        },
        edges: {
            smooth: { 
                type: 'continuous', 
                roundness: 0.7,
                forceDirection: 'horizontal'
            },
            font: { 
                size: 13, 
                color: '#dc2626', 
                bold: true, 
                align: 'middle',
                strokeWidth: 3,
                strokeColor: '#ffffff'
            },
            width: 5,
            color: {
                color: '#dc2626',
                highlight: '#b91c1c',
                hover: '#ef4444'
            },
            arrows: {
                to: {
                    enabled: true,
                    scaleFactor: 1.6,
                    type: 'arrow',
                    length: 20
                }
            },
            shadow: {
                enabled: true,
                color: 'rgba(220, 38, 38, 0.3)',
                size: 8
            }
        },
        layout: {
            hierarchical: {
                enabled: true,
                direction: 'LR',
                sortMethod: 'directed',
                levelSeparation: 250,
                nodeSpacing: 180,
                treeSpacing: 300,
                blockShifting: true,
                edgeMinimization: true,
                parentCentralization: true
            }
        },
        physics: {
            enabled: false  // Disable physics for hierarchical layout
        },
        interaction: {
            hover: true,
            tooltipDelay: 150,
            zoomView: true,
            dragView: true,
            selectConnectedEdges: true
        },
        configure: {
            enabled: false
        }
    };
    
    criticalPathNetwork = new vis.Network(container, data, options);
    
    // Add event listeners
    criticalPathNetwork.on("hoverNode", function(params) {
        container.style.cursor = 'pointer';
    });
    criticalPathNetwork.on("blurNode", function(params) {
        container.style.cursor = 'default';
    });
    
    // Add click handler to show task details in inline card
    criticalPathNetwork.on("click", function(params) {
        if (params.nodes.length > 0) {
            const nodeId = params.nodes[0];
            showTaskDetailsCard(nodeId, nodes, taskAnalysisData, dependenciesData, 'task-details-card-cp', 'task-details-card-content-cp');
        }
    });
}

// Load Work Team
async function loadWorkTeam() {
    try {
        const response = await fetch(`/resource_agent/work_team/${currentProjectId}`);
        const data = await response.json();
        
        if (data.work_team && data.work_team.length > 0) {
            renderWorkTeam(data.work_team);
        } else {
            document.getElementById('work-team-container').innerHTML = 
                '<div class="text-center p-8 text-gray-500 col-span-full">No work team members. Add members to get started.</div>';
        }
    } catch (error) {
        console.error('Error loading work team:', error);
        document.getElementById('work-team-container').innerHTML = 
            '<div class="text-center p-8 text-red-500 col-span-full">Error loading work team</div>';
    }
}

// Render Work Team
function renderWorkTeam(team) {
    const container = document.getElementById('work-team-container');
    container.innerHTML = '';
    
    team.forEach(member => {
        const card = document.createElement('div');
        card.className = 'work-team-card';
        
        const typeClass = member.type === 'organization' ? 'organization' : 'person';
        const typeLabel = member.type === 'organization' ? 'Organization' : 'Person';
        
        const resources = member.assigned_resources || 0;
        const hasResources = resources > 0;
        
        card.innerHTML = `
            <div class="work-team-card-header">
                <div class="work-team-card-title">${escapeHtml(member.name)}</div>
                <span class="work-team-card-type ${typeClass}">${typeLabel}</span>
            </div>
            <div class="work-team-card-resources ${hasResources ? '' : 'no-resources'}">
                ${hasResources ? `PKR ${formatNumber(resources)}` : '<span style="opacity: 0.6;">No resources assigned</span>'}
            </div>
            <div class="work-team-card-actions">
                <button onclick="editResourceAssignment('${member.id}', ${resources})" class="btn btn-primary btn-sm">
                    <i class="fas fa-edit"></i> Edit
                </button>
                <button onclick="deleteTeamMember('${member.id}')" class="btn btn-danger btn-sm">
                    <i class="fas fa-trash"></i> Delete
                </button>
            </div>
        `;
        
        container.appendChild(card);
    });
}

// Load Financial Summary
async function loadFinancialSummary() {
    try {
        const response = await fetch(`/resource_agent/financial_summary/${currentProjectId}`);
        const data = await response.json();
        
        if (data.success) {
            document.getElementById('resource-budget').textContent = `PKR ${formatNumber(data.budget || 0)}`;
            document.getElementById('resource-expenses').textContent = `PKR ${formatNumber(data.expenses || 0)}`;
            document.getElementById('resource-revenue').textContent = `PKR ${formatNumber(data.revenue || 0)}`;
            document.getElementById('resource-available').textContent = `PKR ${formatNumber(data.available || 0)}`;
        }
    } catch (error) {
        console.error('Error loading financial summary:', error);
    }
}

// Add Team Member - Inline Card
function showAddMemberCard() {
    const card = document.getElementById('add-member-card');
    if (card) {
        card.classList.remove('hidden');
        // Scroll to card
        card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
}

function closeAddMemberCard() {
    const card = document.getElementById('add-member-card');
    if (card) {
        card.classList.add('hidden');
    }
    const form = document.getElementById('add-team-member-form');
    if (form) {
        form.reset();
    }
}

document.getElementById('add-team-member-form')?.addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const name = document.getElementById('team-member-name').value.trim();
    const type = document.getElementById('team-member-type').value;
    
    if (!name) {
        alert('Please enter a name for the team member');
        return;
    }
    
    try {
        console.log('Adding team member:', { name, type, projectId: currentProjectId });
        const response = await fetch(`/resource_agent/work_team/${currentProjectId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, type })
        });
        
        const data = await response.json();
        console.log('Add team member response:', data);
        
        if (data.success || response.ok) {
            closeAddMemberCard();
            loadWorkTeam();
            // Show success message
            const successMsg = document.createElement('div');
            successMsg.className = 'alert alert-success';
            successMsg.style.marginTop = '1rem';
            successMsg.innerHTML = '<i class="fas fa-check-circle"></i> Team member added successfully!';
            const workTeamSection = document.querySelector('.work-team-section');
            if (workTeamSection) {
                workTeamSection.insertBefore(successMsg, document.getElementById('work-team-container'));
                setTimeout(() => successMsg.remove(), 3000);
            }
        } else {
            const errorMsg = data.error || data.message || 'Failed to add team member';
            console.error('Error response:', errorMsg);
            alert('Error: ' + errorMsg);
        }
    } catch (error) {
        console.error('Error adding team member:', error);
        alert('Error adding team member: ' + error.message);
    }
});

// Edit Resource Assignment
function editResourceAssignment(teamMemberId, currentAmount) {
    const card = document.getElementById('edit-resource-card');
    if (card) {
        document.getElementById('edit-team-member-id').value = teamMemberId;
        document.getElementById('edit-resource-amount').value = currentAmount;
        card.classList.remove('hidden');
        // Scroll to card
        card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
}

function closeEditResourceCard() {
    const card = document.getElementById('edit-resource-card');
    if (card) {
        card.classList.add('hidden');
    }
    const form = document.getElementById('edit-resource-form');
    if (form) {
        form.reset();
    }
}

document.getElementById('edit-resource-form')?.addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const teamMemberId = document.getElementById('edit-team-member-id').value;
    const amount = parseFloat(document.getElementById('edit-resource-amount').value);
    
    try {
        const response = await fetch(`/resource_agent/resource_assignment/${teamMemberId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ amount })
        });
        
        const data = await response.json();
        
        if (data.success || response.ok) {
            closeEditResourceCard();
            loadWorkTeam();
            // Show success message
            const successMsg = document.createElement('div');
            successMsg.className = 'alert alert-success';
            successMsg.style.marginTop = '1rem';
            successMsg.innerHTML = '<i class="fas fa-check-circle"></i> Resource assignment updated successfully!';
            const workTeamSection = document.querySelector('.work-team-section');
            if (workTeamSection) {
                workTeamSection.insertBefore(successMsg, document.getElementById('work-team-container'));
                setTimeout(() => successMsg.remove(), 3000);
            }
        } else {
            const errorMsg = data.error || data.message || 'Failed to update resource assignment';
            alert('Error: ' + errorMsg);
        }
    } catch (error) {
        console.error('Error updating resource assignment:', error);
        alert('Error updating resource assignment');
    }
});

// Delete Team Member
async function deleteTeamMember(teamMemberId) {
    if (!confirm('Are you sure you want to delete this team member?')) {
        return;
    }
    
    try {
        const response = await fetch(`/resource_agent/work_team/${teamMemberId}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (data.success) {
            loadWorkTeam();
        } else {
            alert('Error: ' + (data.error || 'Failed to delete team member'));
        }
    } catch (error) {
        console.error('Error deleting team member:', error);
        alert('Error deleting team member');
    }
}

// Assign Resources AI
async function assignResourcesAI() {
    const btn = document.getElementById('assign-resources-btn');
    const originalText = btn.innerHTML;
    
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Assigning...';
    
    try {
        const response = await fetch(`/resource_agent/assign_resources/${currentProjectId}`, {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (data.success) {
            document.getElementById('assignment-results').classList.remove('hidden');
            loadWorkTeam();
            loadFinancialSummary();
            
            setTimeout(() => {
                document.getElementById('assignment-results').classList.add('hidden');
            }, 5000);
        } else {
            alert('Error: ' + (data.error || 'Failed to assign resources'));
        }
    } catch (error) {
        console.error('Error assigning resources:', error);
        alert('Error assigning resources');
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalText;
    }
}

// Run First Generation
async function runFirstGeneration() {
    // Get document ID from hidden input (set by template)
    if (!currentDocumentId) {
        const firstDocInput = document.getElementById('first-doc-id');
        if (firstDocInput && firstDocInput.value) {
            currentDocumentId = firstDocInput.value;
            console.log('📄 Using first-doc-id from template:', currentDocumentId);
        } else {
            alert('No document found in project. Please upload at least one document first.');
            window.location.href = `/project/${currentProjectId}`;
            return;
        }
    }
    
    const btn = document.getElementById('first-generation-btn');
    const originalText = btn.innerHTML;
    
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Running First Generation...';
    
    try {
        const response = await fetch('/resource_agent/first_generation', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                project_id: currentProjectId,
                document_id: currentDocumentId
            })
        });
        
        const data = await response.json();
        
        if (data.success || data.overall_success) {
            alert('First generation completed successfully!');
            // Reload all data
            loadResourceDashboard(currentProjectId);
        } else {
            alert('Error: ' + (data.error || 'First generation failed. Check console for details.'));
            console.error('First generation error:', data);
        }
    } catch (error) {
        console.error('Error running first generation:', error);
        alert('Error running first generation: ' + error.message);
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalText;
    }
}

// Refresh Resource Data
async function refreshResourceData() {
    try {
        const response = await fetch(`/resource_agent/refresh/${currentProjectId}`, {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (data.success) {
            // Reload all data
            loadResourceDashboard(currentProjectId);
            alert('Resource data refreshed successfully!');
        } else {
            alert('Error: ' + (data.error || 'Failed to refresh resource data'));
        }
    } catch (error) {
        console.error('Error refreshing resource data:', error);
        alert('Error refreshing resource data');
    }
}

// Utility Functions
function formatNumber(num) {
    return new Intl.NumberFormat('en-PK').format(num);
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Show Task Details Card (Inline)
function showTaskDetailsCard(taskId, nodes, taskAnalysisData, dependencies, cardId, contentId) {
    const node = nodes.get(taskId);
    if (!node) return;
    
    // Find task details from task analysis data
    let taskDetails = null;
    if (taskAnalysisData && taskAnalysisData.length > 0) {
        taskDetails = taskAnalysisData.find(t => {
            const tid = t.task_id || t.metadata?.task_id;
            return tid === taskId;
        });
    }
    
    // Find dependencies for this task
    let taskDependencies = [];
    if (dependencies && dependencies.length > 0) {
        const taskDep = dependencies.find(d => {
            const tid = d.task_id || d.metadata?.task_id;
            return tid === taskId;
        });
        if (taskDep) {
            const dependsOn = taskDep.depends_on || taskDep.metadata?.depends_on || [];
            let dependsOnArray = dependsOn;
            if (typeof dependsOn === 'string') {
                try {
                    dependsOnArray = JSON.parse(dependsOn);
                } catch (e) {
                    dependsOnArray = [];
                }
            }
            taskDependencies = dependsOnArray;
        }
    }
    
    // Get task name
    const taskName = taskDetails?.task_name || taskDetails?.metadata?.task_name || node.title || taskId;
    const priority = taskDetails?.priority || taskDetails?.metadata?.priority || 'Medium';
    const complexity = taskDetails?.complexity || taskDetails?.metadata?.complexity || 'Moderate';
    const estimatedTime = taskDetails?.estimated_time_hours || taskDetails?.metadata?.estimated_time_hours || 0;
    
    // Build card content
    const content = document.getElementById(contentId);
    content.innerHTML = `
        <div class="task-details-header">
            <div class="task-details-title">${escapeHtml(taskName)}</div>
            <div class="task-details-badges">
                <span class="priority-badge ${priority}">${priority}</span>
                <span class="complexity-badge ${complexity.replace(/\s+/g, '\\ ')}">${complexity}</span>
            </div>
        </div>
        
        <div class="task-details-section">
            <div class="task-details-section-title">
                <i class="fas fa-info-circle"></i>
                Task Information
            </div>
            <div class="task-details-content">
                <div class="task-details-metric">
                    <span class="task-details-metric-label">Task ID</span>
                    <span class="task-details-metric-value">${escapeHtml(taskId)}</span>
                </div>
                <div class="task-details-metric">
                    <span class="task-details-metric-label">Priority</span>
                    <span class="task-details-metric-value">
                        <span class="priority-badge ${priority}">${priority}</span>
                    </span>
                </div>
                <div class="task-details-metric">
                    <span class="task-details-metric-label">Complexity</span>
                    <span class="task-details-metric-value">
                        <span class="complexity-badge ${complexity.replace(/\s+/g, '\\ ')}">${complexity}</span>
                    </span>
                </div>
                <div class="task-details-metric">
                    <span class="task-details-metric-label">Estimated Time</span>
                    <span class="task-details-metric-value">${estimatedTime.toFixed(1)} hours (${(estimatedTime / 8).toFixed(1)} days)</span>
                </div>
            </div>
        </div>
        
        <div class="task-details-section">
            <div class="task-details-section-title">
                <i class="fas fa-project-diagram"></i>
                Dependencies
            </div>
            <div class="task-details-content">
                ${taskDependencies.length > 0 ? `
                    <p style="margin-bottom: 0.75rem; color: #6b7280; font-size: 0.9rem;">
                        This task depends on the following tasks:
                    </p>
                    <ul class="task-dependencies-list">
                        ${taskDependencies.map(depId => {
                            // Find dependency task name
                            let depName = depId;
                            if (taskAnalysisData && taskAnalysisData.length > 0) {
                                const depTask = taskAnalysisData.find(t => {
                                    const tid = t.task_id || t.metadata?.task_id;
                                    return tid === depId;
                                });
                                if (depTask) {
                                    depName = depTask.task_name || depTask.metadata?.task_name || depId;
                                }
                            }
                            return `<li>${escapeHtml(depName)}</li>`;
                        }).join('')}
                    </ul>
                ` : `
                    <div class="no-dependencies">
                        <i class="fas fa-info-circle"></i> This task has no dependencies
                    </div>
                `}
            </div>
        </div>
    `;
    
    // Show card
    const card = document.getElementById(cardId);
    if (card && content) {
        console.log('Showing task details card:', cardId, 'Content:', contentId);
        card.classList.remove('hidden');
        card.style.display = 'flex';
        // Scroll content to top
        const cardBody = card.querySelector('.task-details-card-body');
        if (cardBody) {
            cardBody.scrollTop = 0;
        }
    } else {
        console.error('Task details card or content not found!', 'Card ID:', cardId, 'Content ID:', contentId);
        if (!card) console.error('Card element not found:', cardId);
        if (!content) console.error('Content element not found:', contentId);
    }
}

// Close Task Details Card
function closeTaskDetailsCard() {
    const card = document.getElementById('task-details-card');
    if (card) {
        card.classList.add('hidden');
    }
}

function closeTaskDetailsCardCP() {
    const card = document.getElementById('task-details-card-cp');
    if (card) {
        card.classList.add('hidden');
    }
}

// Close task details cards on Escape key
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        closeTaskDetailsCard();
        closeTaskDetailsCardCP();
    }
});

