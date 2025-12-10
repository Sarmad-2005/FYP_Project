// CSV Analysis - Excel-like Interface JavaScript

console.log('🚀 CSV Analysis JavaScript LOADED!');

// Global Variables
// projectId, currentSessionId, csvTable, selectedCells (declared in HTML)

// ==== Initialization ====
document.addEventListener('DOMContentLoaded', function() {
    console.log('📄 DOM Content Loaded');
    initializeUpload();
    initializeAIPanel();
});

// ==== File Upload ====
function initializeUpload() {
    const fileUpload = document.getElementById('fileUpload');
    const dropZone = document.getElementById('dropZone');
    
    // File input change
    fileUpload.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFileUpload(e.target.files[0]);
        }
    });
    
    // Drag and drop
    if (dropZone) {
        dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropZone.classList.add('drag-over');
        });
        
        dropZone.addEventListener('dragleave', () => {
            dropZone.classList.remove('drag-over');
        });
        
        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropZone.classList.remove('drag-over');
            
            const files = e.dataTransfer.files;
            if (files.length > 0 && files[0].name.endsWith('.csv')) {
                handleFileUpload(files[0]);
            } else {
                showToast('Please drop a CSV file', 'error');
            }
        });
        
        dropZone.addEventListener('click', () => {
            fileUpload.click();
        });
    }
}

async function handleFileUpload(file) {
    console.log('📤 handleFileUpload called with:', file.name);
    
    if (!file.name.endsWith('.csv')) {
        showToast('Please upload a CSV file', 'error');
        return;
    }
    
    showLoading('Uploading and processing CSV...');
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        console.log('📡 Sending upload request...');
        const response = await fetch(`/csv_analysis/upload/${projectId}`, {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        console.log('📦 Upload result:', result);
        
        hideLoading();
        
        if (result.success) {
            currentSessionId = result.session_id;
            console.log('✅ Upload successful, loading table...');
            showToast(`✓ CSV uploaded: ${result.rows} rows, ${result.columns} columns`, 'success');
            loadCSVTable(result.preview, result.headers);
            showTableSection();
            updateHeaderStats(result.rows, result.columns);
        } else {
            console.log('❌ Upload failed:', result.error);
            showToast(`Upload failed: ${result.error}`, 'error');
        }
        
    } catch (error) {
        console.log('❌ Upload error:', error);
        hideLoading();
        showToast(`Upload error: ${error.message}`, 'error');
    }
}

// ==== Excel-like Table Configuration ====
function loadCSVTable(data, headers) {
    console.log('📊 loadCSVTable called');
    console.log('   Data rows:', data.length);
    console.log('   Headers:', headers);
    
    // Add row numbers to data
    const dataWithRowNumbers = data.map((row, index) => ({
        __rowNum: index + 1,
        ...row
    }));
    
    console.log('   Data with row numbers:', dataWithRowNumbers.length);
    
    // Create row number column
    const rowNumColumn = {
        title: "#",
        field: "__rowNum",
        width: 60,
        frozen: true,
        headerSort: false,
        cssClass: "row-number-cell",
        hozAlign: "center",
        formatter: function(cell) {
            return cell.getValue();
        }
    };
    
    // Create data columns - Excel-like
    const columns = headers.map(header => ({
        title: header,
        field: header,
        editor: "input",
        headerFilter: "input",
        headerFilterPlaceholder: `Search ${header}...`,
        minWidth: 120,
        widthGrow: 1,
        tooltip: true,
        formatter: function(cell) {
            const value = cell.getValue();
            if (value === null || value === undefined || value === '') {
                return '<span style="color: #9ca3af; font-style: italic;">empty</span>';
            }
            return value;
        }
    }));
    
    // Add row number column at the start
    columns.unshift(rowNumColumn);
    
    // Initialize Tabulator with Excel-like configuration
    csvTable = new Tabulator("#csvTable", {
        data: dataWithRowNumbers,
        columns: columns,
        height: "100%",
        layout: "fitColumns",  // Show all columns
        layoutColumnsOnNewData: true,
        
        // Excel-like row height
        rowHeight: 38,
        
        // Row selection configuration - DIRECT CLICK
        selectable: true,  // Enable row selection
        selectableRollingSelection: true,  // Click toggles selection
        selectablePersistence: false,  // Don't persist
        
        // Make entire row clickable for selection
        reactiveData: false,  // Disable reactive data for performance
        
        // Visual feedback - make rows look clickable
        rowFormatter: function(row) {
            row.getElement().style.cursor = "pointer";
        },
        
        // Editing
        cellEdited: function(cell) {
            showToast('Cell updated', 'success');
        },
        
        // Pagination
        pagination: false,
        
        // Appearance
        headerSort: true,
        headerSortTristate: true,
        resizableColumnFit: true,
        
        // Clipboard
        clipboard: true,
        clipboardCopyStyled: false,
        clipboardPasteAction: "update",
        
        // Responsiveness
        responsiveLayout: "hide",
        
        // Row click handler - with error catching
        rowClick: function(e, row) {
            try {
                console.log('====================================');
                console.log('🖱️ ROW CLICK EVENT FIRED!!!');
                console.log('Row #:', row.getData().__rowNum);
                console.log('====================================');
                
                setTimeout(() => {
                    try {
                        const selectedRows = csvTable.getSelectedRows();
                        console.log('⏱️ Selected count:', selectedRows.length);
                        updateRowSelection(selectedRows);
                    } catch (error) {
                        console.error('❌ Error in setTimeout:', error);
                    }
                }, 50);
            } catch (error) {
                console.error('❌ Error in rowClick:', error);
            }
        },
        
        // Row selection callback - with error catching
        rowSelectionChanged: function(data, rows) {
            try {
                console.log('====================================');
                console.log('🔵 ROW SELECTION CHANGED FIRED!!!');
                console.log('Count:', rows.length);
                console.log('====================================');
                updateRowSelection(rows);
            } catch (error) {
                console.error('❌ Error in rowSelectionChanged:', error);
            }
        }
    });
    
    console.log('✅ Tabulator initialized successfully');
    console.log('📊 Selectable mode:', csvTable.options.selectable);
    console.log('📊 Data count:', dataWithRowNumbers.length);
    
    // BACKUP: Manual click listener on table element
    console.log('🔧 Installing manual click listener on table...');
    const tableElement = document.getElementById('csvTable');
    if (tableElement) {
        tableElement.addEventListener('click', function(e) {
            console.log('🎯 MANUAL CLICK DETECTED on table!');
            // Check selection after a short delay
            setTimeout(() => {
                if (csvTable) {
                    const selected = csvTable.getSelectedRows();
                    console.log('🔍 Manual check: Selected count =', selected.length);
                    if (selected.length > 0) {
                        console.log('📋 Updating selection via manual listener...');
                        updateRowSelection(selected);
                    }
                }
            }, 100);
        });
        console.log('✅ Manual listener installed');
    }
    
    // Enable toolbar buttons
    enableToolbarButtons();
    
    // Initial selection state
    updateSelectedCount(0);
    
    // Selection is now handled by rowClick handler above
}

function updateRowSelection(rows) {
    console.log('🔄 updateRowSelection called with', rows.length, 'rows');
    console.log('📋 Rows array:', rows);
    
    if (!csvTable) {
        console.error('❌ csvTable is not defined!');
        return;
    }
    
    // Convert to cell data format (remove row numbers)
    selectedCells = rows.map(row => {
        const data = row.getData();
        const {__rowNum, ...cellData} = data;
        return cellData;
    });
    
    console.log('✅ Selected cells data:', selectedCells.length, 'cells');
    
    // Update selected count
    updateSelectedCount(rows.length);
    console.log('📊 Updated count display');
    
    // Enable/disable buttons based on selection
    const deleteBtn = document.getElementById('deleteRowBtn');
    const clearBtn = document.getElementById('clearSelectionBtn');
    const askBtn = document.getElementById('askBtn');
    
    console.log('🔘 Button states before update:', {
        deleteBtn: deleteBtn ? !deleteBtn.disabled : 'not found',
        clearBtn: clearBtn ? !clearBtn.disabled : 'not found',
        askBtn: askBtn ? !askBtn.disabled : 'not found'
    });
    
    if (deleteBtn) {
        deleteBtn.disabled = rows.length === 0;
        console.log('🔘 Delete button:', deleteBtn.disabled ? 'DISABLED' : 'ENABLED');
    }
    if (clearBtn) {
        clearBtn.disabled = rows.length === 0;
        console.log('🔘 Clear button:', clearBtn.disabled ? 'DISABLED' : 'ENABLED');
    }
    if (askBtn) {
        askBtn.disabled = false;  // Can always ask questions
        console.log('🔘 Ask button: ENABLED');
    }
    
    // Update empty state in AI panel
    const emptyState = document.getElementById('aiEmptyState');
    if (emptyState && rows.length > 0) {
        emptyState.style.display = 'none';
    }
    
    console.log('✅ updateRowSelection complete');
}

function showTableSection() {
    document.getElementById('uploadPlaceholder').style.display = 'none';
    document.getElementById('tableWrapper').style.display = 'flex';
}

function updateHeaderStats(rows, columns) {
    const headerStats = document.getElementById('headerStats');
    const rowCount = document.getElementById('rowCount');
    const colCount = document.getElementById('colCount');
    
    if (headerStats) {
        headerStats.style.display = 'flex';
        rowCount.textContent = rows;
        colCount.textContent = columns;
    }
}

function updateSelectedCount(count) {
    console.log('🔢 updateSelectedCount called with:', count);
    const selectedCount = document.getElementById('selectedCount');
    console.log('📍 selectedCount element:', selectedCount);
    if (selectedCount) {
        selectedCount.textContent = count;
        console.log('✅ Updated selectedCount to:', count);
    } else {
        console.error('❌ selectedCount element not found in DOM!');
    }
}

function enableToolbarButtons() {
    console.log('🔓 Enabling toolbar buttons');
    document.getElementById('downloadBtn').disabled = false;
    document.getElementById('exportBtn').disabled = false;
    document.getElementById('addRowBtn').disabled = false;
    document.getElementById('refreshBtn').disabled = false;
    document.getElementById('askBtn').disabled = false;  // Enable Ask button
    console.log('✅ All buttons enabled');
}

// ==== Toolbar Actions ====
function addRow() {
    if (!csvTable) return;
    
    const columns = csvTable.getColumns();
    const newRow = {__rowNum: csvTable.getDataCount() + 1};
    
    columns.forEach(col => {
        const field = col.getField();
        if (field !== '__rowNum') {
            newRow[field] = '';
        }
    });
    
    csvTable.addRow(newRow);
    showToast('Row added', 'success');
}

function deleteSelectedRows() {
    if (!csvTable) return;
    
    const selectedRows = csvTable.getSelectedRows();
    if (selectedRows.length === 0) {
        showToast('No rows selected', 'warning');
        return;
    }
    
    if (confirm(`Delete ${selectedRows.length} selected row(s)?`)) {
        selectedRows.forEach(row => row.delete());
        showToast(`${selectedRows.length} row(s) deleted`, 'success');
        
        // Renumber rows
        renumberRows();
        
        // Clear selection
        selectedCells = [];
        updateSelectedCount(0);
    }
}

function renumberRows() {
    if (!csvTable) return;
    
    const data = csvTable.getData();
    data.forEach((row, index) => {
        row.__rowNum = index + 1;
    });
    csvTable.setData(data);
}

function clearSelection() {
    console.log('🧹 clearSelection called');
    if (!csvTable) {
        console.error('❌ csvTable not defined');
        return;
    }
    csvTable.deselectRow();
    console.log('✅ All rows deselected');
    selectedCells = [];
    updateSelectedCount(0);
    showToast('Selection cleared', 'success');
}

// DEBUG FUNCTION - Type testSelection() in browser console to test
window.testSelection = function() {
    console.log('🧪 ========== TESTING SELECTION ==========');
    console.log('📊 csvTable exists:', !!csvTable);
    
    if (!csvTable) {
        console.error('❌ csvTable is not defined!');
        return;
    }
    
    const allRows = csvTable.getRows();
    console.log('📊 Total rows available:', allRows.length);
    console.log('📊 Selectable config:', csvTable.options.selectable);
    console.log('📊 Rolling selection:', csvTable.options.selectableRollingSelection);
    
    if (allRows.length === 0) {
        console.error('❌ No rows in table!');
        return;
    }
    
    console.log('🎯 Attempting to select first 3 rows programmatically...');
    
    try {
        allRows[0].select();
        console.log('   ✅ Row 1 selected');
        
        if (allRows.length > 1) {
            allRows[1].select();
            console.log('   ✅ Row 2 selected');
        }
        
        if (allRows.length > 2) {
            allRows[2].select();
            console.log('   ✅ Row 3 selected');
        }
        
        setTimeout(() => {
            const selected = csvTable.getSelectedRows();
            console.log('📊 RESULT: Selected count =', selected.length);
            if (selected.length > 0) {
                console.log('📋 Selected row numbers:', selected.map(r => r.getData().__rowNum));
                console.log('🔄 Calling updateRowSelection...');
                updateRowSelection(selected);
            } else {
                console.error('❌ NO ROWS SELECTED! Selection failed!');
            }
        }, 100);
    } catch (error) {
        console.error('❌ Error during selection:', error);
    }
    
    console.log('🧪 ========== TEST COMPLETE ==========');
};

function refreshTable() {
    if (!csvTable || !currentSessionId) return;
    
    showLoading('Refreshing data...');
    
    fetch(`/csv_analysis/data/${projectId}/${currentSessionId}`)
        .then(res => res.json())
        .then(result => {
            hideLoading();
            if (result.success) {
                loadCSVTable(result.data, result.headers);
                showToast('Table refreshed', 'success');
            } else {
                showToast('Refresh failed', 'error');
            }
        })
        .catch(error => {
            hideLoading();
            showToast('Refresh error', 'error');
        });
}

function downloadCSV() {
    if (!csvTable || !currentSessionId) return;
    window.location.href = `/csv_analysis/export/${projectId}/${currentSessionId}`;
}

function exportModifiedCSV() {
    if (!csvTable || !currentSessionId) return;
    
    showLoading('Exporting modified CSV...');
    
    const data = csvTable.getData();
    // Remove row numbers
    const cleanData = data.map(row => {
        const {__rowNum, ...cleanRow} = row;
        return cleanRow;
    });
    
    fetch(`/csv_analysis/update/${projectId}/${currentSessionId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            data: cleanData,
            operation: 'update_all'
        })
    })
    .then(res => res.json())
    .then(result => {
        hideLoading();
        if (result.success) {
            window.location.href = `/csv_analysis/export/${projectId}/${currentSessionId}`;
            showToast('Exporting modified data', 'success');
        } else {
            showToast('Export failed', 'error');
        }
    })
    .catch(error => {
        hideLoading();
        showToast('Export error', 'error');
    });
}

// ==== AI Assistant ====
function initializeAIPanel() {
    const emptyState = document.getElementById('aiEmptyState');
    if (emptyState) {
        emptyState.style.display = 'flex';
    }
}

function toggleAIPanel() {
    const panel = document.querySelector('.ai-panel');
    const btn = document.querySelector('.toggle-panel-btn i');
    
    panel.classList.toggle('collapsed');
    
    if (panel.classList.contains('collapsed')) {
        btn.className = 'fas fa-chevron-left';
    } else {
        btn.className = 'fas fa-chevron-right';
    }
}

async function askQuestion() {
    const question = document.getElementById('questionInput').value.trim();
    
    if (!question) {
        showToast('Please enter a question', 'warning');
        return;
    }
    
    if (!currentSessionId) {
        showToast('Please upload a CSV file first', 'warning');
        return;
    }
    
    // Check if rows are selected
    if (!selectedCells || selectedCells.length === 0) {
        showToast('⚠️ Please select rows from the table first! Click rows to select them.', 'warning');
        console.log('❌ No rows selected. User must select rows before asking questions.');
        return;
    }
    
    console.log(`✅ Asking question with ${selectedCells.length} selected rows`);
    console.log('📋 Selected cells:', selectedCells);
    
    const askBtn = document.getElementById('askBtn');
    const askSpinner = document.getElementById('askSpinner');
    
    askBtn.disabled = true;
    askSpinner.style.display = 'inline-block';
    
    const includeContext = document.getElementById('includeProjectContext').checked;
    
    try {
        const response = await fetch(`/csv_analysis/ask/${projectId}/${currentSessionId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                question: question,
                selected_cells: selectedCells,
                // Backend expects context_type == 'with_project_data' to include financial context
                context_type: includeContext ? 'with_project_data' : 'selection'
            })
        });
        
        const result = await response.json();
        
        askBtn.disabled = false;
        askSpinner.style.display = 'none';
        
        if (result.success) {
            displayAnswer(result);
        } else {
            showToast(`Error: ${result.error}`, 'error');
        }
        
    } catch (error) {
        askBtn.disabled = false;
        askSpinner.style.display = 'none';
        showToast(`Q&A error: ${error.message}`, 'error');
    }
}

function displayAnswer(result) {
    const answerSection = document.getElementById('answerSection');
    const answerContent = document.getElementById('answerContent');
    const sourcesContent = document.getElementById('sourcesContent');
    const agentChainContent = document.getElementById('agentChainContent');
    const executionTime = document.getElementById('executionTime');
    const emptyState = document.getElementById('aiEmptyState');
    
    // Hide empty state
    if (emptyState) emptyState.style.display = 'none';
    
    // Display answer
    answerContent.innerHTML = `<p>${escapeHtml(result.answer)}</p>`;
    
    // Display sources with icons
    if (result.sources && result.sources.length > 0) {
        sourcesContent.innerHTML = result.sources.map((source, index) => `
            <div class="source-item">
                <span class="source-icon">${source.icon || '📌'}</span>
                <div class="source-details">
                    <strong>${escapeHtml(source.type || `Source ${index + 1}`)}</strong>
                    <p>${escapeHtml(source.description || '')}</p>
                </div>
            </div>
        `).join('');
    } else {
        sourcesContent.innerHTML = '<p style="color: #9ca3af; font-style: italic;">No sources available</p>';
    }
    
    // Display agent thinking process (beautiful timeline)
    if (result.agent_chain && result.agent_chain.length > 0) {
        agentChainContent.innerHTML = `
            <div class="thinking-timeline">
                ${result.agent_chain.map((step, index) => {
                    // Determine step type from emoji or content
                    let stepClass = 'thinking-step';
                    if (step.includes('💭') || step.includes('Thought')) {
                        stepClass += ' thought-step';
                    } else if (step.includes('🔧') || step.includes('Action') || step.includes('Used')) {
                        stepClass += ' action-step';
                    } else if (step.includes('📊') || step.includes('Result') || step.includes('Observation')) {
                        stepClass += ' result-step';
                    }
                    
                    return `
                        <div class="${stepClass}">
                            <div class="step-marker"></div>
                            <div class="step-content">
                                ${escapeHtml(step)}
                            </div>
                        </div>
                    `;
                }).join('')}
            </div>
        `;
    } else {
        agentChainContent.innerHTML = '<p style="color: #9ca3af; font-style: italic;">Direct answer provided</p>';
    }
    
    // Display execution time
    if (result.execution_time) {
        executionTime.textContent = `⏱️ ${result.execution_time.toFixed(2)}s`;
    }
    
    // Show answer section
    answerSection.style.display = 'block';
    answerSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

// ==== Utility Functions ====
function showLoading(message) {
    const overlay = document.getElementById('loadingOverlay');
    const text = document.getElementById('loadingText');
    if (overlay) {
        overlay.style.display = 'flex';
        if (text) text.textContent = message;
    }
}

function hideLoading() {
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) overlay.style.display = 'none';
}

function showToast(message, type = 'success') {
    const container = document.getElementById('toastContainer');
    if (!container) return;
    
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    const icon = type === 'success' ? 'fa-check-circle' : 
                 type === 'error' ? 'fa-exclamation-circle' : 
                 'fa-exclamation-triangle';
    
    toast.innerHTML = `
        <i class="fas ${icon}"></i>
        <span>${message}</span>
    `;
    
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = 'toastOut 0.3s ease-out';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
