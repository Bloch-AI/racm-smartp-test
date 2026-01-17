/**
 * SmartPapers Flowchart Editor
 * Drawflow-based process flow diagram editor
 */

// Global editor reference
let editor = null;

// Node templates - clean Miro style with editable headers
const nodeTemplates = {
    start: `
        <div class="node-header"><input type="text" class="header-input" value="Start" df-name></div>
        <div class="node-body">
            <textarea class="node-textarea" placeholder="Description..." df-description></textarea>
        </div>`,
    process: `
        <div class="node-header"><input type="text" class="header-input" value="Process" df-name></div>
        <div class="node-body">
            <textarea class="node-textarea" placeholder="Description..." df-description></textarea>
        </div>`,
    decision: `
        <div class="node-header"><input type="text" class="header-input" value="Decision" df-name></div>
        <div class="node-body">
            <textarea class="node-textarea" placeholder="Criteria..." df-description></textarea>
        </div>`,
    end: `
        <div class="node-header"><input type="text" class="header-input" value="End" df-name></div>
        <div class="node-body">
            <textarea class="node-textarea" placeholder="Description..." df-description></textarea>
        </div>`,
    control: `
        <div class="node-header"><input type="text" class="header-input" value="Control" df-name></div>
        <div class="node-body">
            <textarea class="node-textarea" placeholder="Control description..." df-description></textarea>
            <select class="node-select" df-status>
                <option value="effective">Effective</option>
                <option value="needs-improvement">Needs Improvement</option>
                <option value="ineffective">Ineffective</option>
                <option value="not-tested">Not Tested</option>
            </select>
        </div>`,
    risk: `
        <div class="node-header"><input type="text" class="header-input" value="Risk" df-name></div>
        <div class="node-body">
            <textarea class="node-textarea" placeholder="Risk description..." df-description></textarea>
            <select class="node-select" df-rating>
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
            </select>
        </div>`,
    document: `
        <div class="node-header"><input type="text" class="header-input" value="Document" df-name></div>
        <div class="node-body">
            <textarea class="node-textarea" placeholder="Reference..." df-description></textarea>
        </div>`,
    system: `
        <div class="node-header"><input type="text" class="header-input" value="System" df-name></div>
        <div class="node-body"></div>`,
    note: `
        <div class="node-header"><input type="text" class="header-input" value="Note" df-name></div>
        <div class="node-body">
            <textarea class="node-textarea" placeholder="Notes..." df-note></textarea>
        </div>`,
};

const nodeConfig = {
    start: { inputs: 0, outputs: 1 },
    process: { inputs: 1, outputs: 1 },
    decision: { inputs: 1, outputs: 2 },
    end: { inputs: 1, outputs: 0 },
    control: { inputs: 1, outputs: 1 },
    risk: { inputs: 0, outputs: 0 },      // No connectors - standalone risk indicator
    document: { inputs: 1, outputs: 1 },
    system: { inputs: 0, outputs: 0 },    // No connectors - container box
    note: { inputs: 0, outputs: 0 },
};

/**
 * Initialize the Drawflow editor
 * @param {string} containerId - DOM element ID for the canvas
 * @param {Object} options - Configuration options
 */
function initFlowchartEditor(containerId, options = {}) {
    const container = document.getElementById(containerId);
    if (!container) {
        console.error('Flowchart container not found:', containerId);
        return null;
    }

    editor = new Drawflow(container);
    editor.reroute = true;
    editor.reroute_fix_curvature = true;
    editor.force_first_input = false;
    editor.start();

    // Apply admin restrictions if specified
    if (options.isAdmin) {
        editor.editor_mode = 'view';

        const sidebar = document.getElementById('flowchartSidebar');
        const saveBtn = document.getElementById('saveBtn');
        const clearBtn = document.getElementById('clearBtn');

        if (sidebar) sidebar.style.display = 'none';
        if (saveBtn) saveBtn.style.display = 'none';
        if (clearBtn) clearBtn.style.display = 'none';

        // Add view-only indicator
        const nav = document.querySelector('nav .flex.items-center.gap-2');
        if (nav) {
            const badge = document.createElement('span');
            badge.className = 'ml-2 px-2 py-1 text-xs font-medium bg-amber-100 text-amber-700 rounded';
            badge.textContent = 'Admin View Only';
            nav.appendChild(badge);
        }

        // Disable all inputs/textareas in flowchart after load
        editor.on('import', function() {
            setTimeout(() => {
                document.querySelectorAll('#drawflow input, #drawflow textarea, #drawflow select').forEach(el => {
                    el.disabled = true;
                    el.style.pointerEvents = 'none';
                });
            }, 100);
        });
    }

    return editor;
}

// Drag and drop handlers
function allowDrop(ev) { ev.preventDefault(); }

function drag(ev) {
    ev.dataTransfer.setData("node", ev.target.closest('[data-node]').getAttribute('data-node'));
}

function drop(ev) {
    ev.preventDefault();
    const nodeType = ev.dataTransfer.getData("node");
    const container = document.getElementById('drawflow');
    addNode(nodeType, ev.clientX, ev.clientY, container);
}

function addNode(type, posX, posY, container) {
    if (!editor) return;
    const rect = container.getBoundingClientRect();
    const x = (posX - rect.left) / editor.zoom - editor.precanvas.getBoundingClientRect().left / editor.zoom;
    const y = (posY - rect.top) / editor.zoom - editor.precanvas.getBoundingClientRect().top / editor.zoom;
    const config = nodeConfig[type];
    editor.addNode(type, config.inputs, config.outputs, x, y, type, { name: '', description: '', status: '', rating: '', note: '' }, nodeTemplates[type]);
}

// Zoom controls
function zoomIn() { if (editor) editor.zoom_in(); }
function zoomOut() { if (editor) editor.zoom_out(); }
function zoomReset() { if (editor) editor.zoom_reset(); }

/**
 * Load flowcharts list into a dropdown
 */
async function loadFlowchartList(selectId, initialFlowchartId) {
    try {
        const response = await fetch('/api/flowcharts');
        const flowcharts = await response.json();
        const select = document.getElementById(selectId);
        if (!select) return;

        select.innerHTML = '<option value="">-- Select Flowchart --</option>';
        flowcharts.forEach(name => {
            const option = document.createElement('option');
            option.value = name;
            option.textContent = name.replace(/-/g, ' ').replace(/\d+$/, '').trim();
            if (name === initialFlowchartId) option.selected = true;
            select.appendChild(option);
        });
    } catch (e) {
        console.error('Failed to load flowchart list:', e);
    }
}

/**
 * Select flowchart from dropdown
 */
function selectFlowchart() {
    const select = document.getElementById('flowchartSelect');
    const name = select.value;
    if (name) {
        document.getElementById('flowchartName').value = name;
        loadFlowchart();
    }
}

/**
 * Save the current flowchart
 */
async function saveFlowchart() {
    if (!editor) return;

    const name = document.getElementById('flowchartName').value.trim();
    if (!name) {
        showFlowchartToast('Please enter a flowchart name', 'warning');
        return;
    }

    const data = editor.export();
    await fetch(`/api/flowchart/${encodeURIComponent(name)}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });

    showFlowchartToast('Flowchart saved!', 'success');
    window.history.pushState({}, '', `/flowchart/${encodeURIComponent(name)}`);
}

/**
 * Load a flowchart by name
 */
async function loadFlowchart() {
    if (!editor) return;

    const name = document.getElementById('flowchartName').value.trim();
    if (!name) {
        showFlowchartToast('Please enter a flowchart name', 'warning');
        return;
    }

    const response = await fetch(`/api/flowchart/${encodeURIComponent(name)}`);
    const result = await response.json();

    // Handle new response format: {data: {...}, permissions: {...}}
    const data = result?.data || result;
    const permissions = result?.permissions || {};

    if (data && data.drawflow) {
        // Rebuild HTML from templates for each node before importing
        const homeData = data.drawflow.Home?.data || {};
        for (const nodeId in homeData) {
            const node = homeData[nodeId];
            const nodeType = node.name || 'process';
            if (nodeTemplates[nodeType]) {
                node.html = nodeTemplates[nodeType];
            }
        }
        editor.import(data);

        // Apply permissions from server
        applyFlowchartPermissions(permissions);

        showFlowchartToast('Flowchart loaded!', 'success');
        window.history.pushState({}, '', `/flowchart/${encodeURIComponent(name)}`);
    } else {
        showFlowchartToast('Flowchart not found', 'error');
    }
}

/**
 * Apply permissions to flowchart editor controls
 */
function applyFlowchartPermissions(permissions) {
    const canEdit = permissions?.canEdit === true;

    if (!canEdit) {
        editor.editor_mode = 'view';

        const sidebar = document.getElementById('flowchartSidebar');
        const saveBtn = document.getElementById('saveBtn');
        const clearBtn = document.getElementById('clearBtn');

        if (sidebar) sidebar.style.display = 'none';
        if (saveBtn) saveBtn.style.display = 'none';
        if (clearBtn) clearBtn.style.display = 'none';

        // Add view-only indicator if not already present
        const nav = document.querySelector('nav .flex.items-center.gap-2');
        if (nav && !document.getElementById('viewOnlyBadge')) {
            const badge = document.createElement('span');
            badge.id = 'viewOnlyBadge';
            badge.className = 'px-2 py-1 text-xs font-medium bg-amber-100 text-amber-700 rounded';
            badge.textContent = 'View Only';
            nav.appendChild(badge);
        }

        // Disable inputs in nodes
        document.querySelectorAll('#drawflow input, #drawflow textarea').forEach(el => {
            el.disabled = true;
            el.style.pointerEvents = 'none';
        });
    } else {
        editor.editor_mode = 'edit';

        const sidebar = document.getElementById('flowchartSidebar');
        const saveBtn = document.getElementById('saveBtn');
        const clearBtn = document.getElementById('clearBtn');

        if (sidebar) sidebar.style.display = '';
        if (saveBtn) saveBtn.style.display = '';
        if (clearBtn) clearBtn.style.display = '';

        // Remove view-only badge if present
        const badge = document.getElementById('viewOnlyBadge');
        if (badge) badge.remove();
    }
}

/**
 * Export flowchart data as JSON file
 */
function exportData() {
    if (!editor) return;

    const data = editor.export();
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const name = document.getElementById('flowchartName').value.trim() || 'flowchart';
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${name}.json`;
    a.click();
    URL.revokeObjectURL(url);
    showFlowchartToast('Exported!', 'success');
}

/**
 * Clear the canvas
 */
function clearCanvas() {
    if (!editor) return;

    if (confirm('Clear the entire flowchart?')) {
        editor.clear();
        showFlowchartToast('Canvas cleared', 'info');
    }
}

/**
 * Show toast notification
 */
function showFlowchartToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `flowchart-toast rounded-lg shadow-lg px-4 py-3 flex items-center gap-2 ${
        type === 'success' ? 'bg-emerald-600 text-white' :
        type === 'error' ? 'bg-red-600 text-white' :
        type === 'warning' ? 'bg-amber-500 text-white' :
        'bg-slate-700 text-white'
    }`;
    toast.innerHTML = `<p class="text-sm font-medium">${message}</p>`;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(10px)';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// Keyboard shortcuts
document.addEventListener('keydown', function(e) {
    if (!editor) return;

    if (e.key === 'Delete' || e.key === 'Backspace') {
        if (editor.node_selected) {
            if (document.activeElement.tagName === 'INPUT' || document.activeElement.tagName === 'TEXTAREA') return;
            editor.removeNodeId('node-' + editor.node_selected);
        }
    }
    if (e.key === 's' && (e.ctrlKey || e.metaKey)) {
        e.preventDefault();
        saveFlowchart();
    }
});
