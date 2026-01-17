/**
 * SmartPapers Kanban Board
 * jKanban-based task management board
 */

let kanban = null;
let boardData = null;
let itemIdCounter = 100;

/**
 * Initialize the kanban board
 * @param {string} boardId - The board ID to load
 */
async function initKanbanBoard(boardId) {
    const response = await fetch(`/api/kanban/${boardId}`);
    boardData = await response.json();

    if (!boardData) {
        boardData = {
            name: 'Audit Plan',
            columns: [
                { id: 'planning', title: 'Planning', items: [] },
                { id: 'fieldwork', title: 'Fieldwork', items: [] },
                { id: 'testing', title: 'Testing', items: [] },
                { id: 'review', title: 'Review', items: [] },
                { id: 'complete', title: 'Complete', items: [] }
            ]
        };
    }

    renderBoard(boardId);
}

/**
 * Render the kanban board
 */
function renderBoard(boardId) {
    document.getElementById('kanban-board').innerHTML = '';

    const boards = boardData.columns.map(col => ({
        id: col.id,
        title: `${col.title} <span class="ml-2 inline-flex items-center rounded-full bg-slate-200 px-2 py-0.5 text-xs font-medium text-slate-700">${col.items.length}</span>`,
        item: col.items.map(item => ({
            id: item.id,
            title: buildItemHTML(item),
            priority: item.priority || 'low'
        }))
    }));

    kanban = new jKanban({
        element: '#kanban-board',
        boards: boards,
        dragItems: true,
        dragBoards: false,
        itemHandleOptions: { enabled: false },
        click: function(el) {
            const itemId = el.getAttribute('data-eid');
            openEditModal(itemId);
        },
        dropEl: function(el, target, source, sibling) {
            updateBoardData();
            saveBoard(boardId);
        }
    });

    // Add "Add task" buttons
    document.querySelectorAll('.kanban-board').forEach(board => {
        const colId = board.getAttribute('data-id');
        const addBtn = document.createElement('button');
        addBtn.className = 'w-full mt-2 px-4 py-2 text-sm text-slate-500 hover:text-slate-700 hover:bg-slate-50 rounded-full transition-colors flex items-center justify-center gap-2';
        addBtn.innerHTML = '<svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" /></svg> Add task';
        addBtn.onclick = () => openAddModal(colId);
        board.querySelector('.kanban-drag').after(addBtn);
    });
}

/**
 * Build HTML for a kanban item
 */
function buildItemHTML(item) {
    const priorityColors = {
        high: 'bg-red-100 text-red-700',
        medium: 'bg-amber-100 text-amber-700',
        low: 'bg-emerald-100 text-emerald-700'
    };
    const priorityColor = priorityColors[item.priority] || priorityColors.low;

    let html = `<div class="font-medium text-sm text-slate-900">${escapeHtml(item.title)}</div>`;
    if (item.description) {
        html += `<div class="mt-1 text-xs text-slate-500 line-clamp-2">${escapeHtml(item.description)}</div>`;
    }
    html += `<div class="mt-2 flex items-center gap-1 flex-wrap">`;
    html += `<span class="inline-block px-2 py-0.5 rounded-full text-xs font-medium ${priorityColor}">${item.priority || 'low'}</span>`;
    if (item.assignee) html += `<span class="inline-block px-2 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-600">${escapeHtml(item.assignee)}</span>`;
    if (item.dueDate) html += `<span class="inline-block px-2 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-600">${item.dueDate}</span>`;
    html += `</div>`;
    return html;
}

/**
 * Update board data from DOM
 */
function updateBoardData() {
    boardData.columns = boardData.columns.map(col => {
        const boardEl = document.querySelector(`.kanban-board[data-id="${col.id}"]`);
        if (boardEl) {
            const items = [];
            boardEl.querySelectorAll('.kanban-item').forEach(itemEl => {
                const itemId = itemEl.getAttribute('data-eid');
                let originalItem = null;
                boardData.columns.forEach(c => {
                    const found = c.items.find(i => i.id === itemId);
                    if (found) originalItem = found;
                });
                if (originalItem) items.push(originalItem);
            });
            col.items = items;
        }
        return col;
    });
}

/**
 * Open modal to add a new task
 */
function openAddModal(columnId) {
    document.getElementById('modalTitle').textContent = 'Add Task';
    document.getElementById('editItemId').value = '';
    document.getElementById('editColumnId').value = columnId;
    document.getElementById('editTitle').value = '';
    document.getElementById('editDescription').value = '';
    document.getElementById('editPriority').value = 'medium';
    document.getElementById('editAssignee').value = '';
    document.getElementById('editDueDate').value = '';
    document.getElementById('deleteBtn').style.display = 'none';
    document.getElementById('editModal').classList.remove('translate-x-full');
    document.getElementById('editModalBackdrop').classList.remove('hidden');
}

/**
 * Open modal to edit an existing task
 */
function openEditModal(itemId) {
    let item = null;
    let columnId = null;
    boardData.columns.forEach(col => {
        const found = col.items.find(i => i.id === itemId);
        if (found) { item = found; columnId = col.id; }
    });
    if (!item) return;

    document.getElementById('modalTitle').textContent = 'Edit Task';
    document.getElementById('editItemId').value = itemId;
    document.getElementById('editColumnId').value = columnId;
    document.getElementById('editTitle').value = item.title || '';
    document.getElementById('editDescription').value = item.description || '';
    document.getElementById('editPriority').value = item.priority || 'medium';
    document.getElementById('editAssignee').value = item.assignee || '';
    document.getElementById('editDueDate').value = item.dueDate || '';
    document.getElementById('deleteBtn').style.display = 'block';
    document.getElementById('editModal').classList.remove('translate-x-full');
    document.getElementById('editModalBackdrop').classList.remove('hidden');
}

/**
 * Close the edit modal
 */
function closeModal() {
    document.getElementById('editModal').classList.add('translate-x-full');
    document.getElementById('editModalBackdrop').classList.add('hidden');
}

/**
 * Save a task (create or update)
 */
function saveCard(boardId) {
    const itemId = document.getElementById('editItemId').value;
    const columnId = document.getElementById('editColumnId').value;
    const title = document.getElementById('editTitle').value.trim();
    const description = document.getElementById('editDescription').value.trim();
    const priority = document.getElementById('editPriority').value;
    const assignee = document.getElementById('editAssignee').value.trim();
    const dueDate = document.getElementById('editDueDate').value;

    if (!title) {
        showToast('Please enter a title', 'warning');
        return;
    }

    if (itemId) {
        boardData.columns.forEach(col => {
            const item = col.items.find(i => i.id === itemId);
            if (item) {
                item.title = title;
                item.description = description;
                item.priority = priority;
                item.assignee = assignee;
                item.dueDate = dueDate;
            }
        });
    } else {
        const newItem = {
            id: 'item-' + (++itemIdCounter),
            title, description, priority, assignee, dueDate
        };
        const col = boardData.columns.find(c => c.id === columnId);
        if (col) col.items.push(newItem);
    }

    closeModal();
    renderBoard(boardId);
    saveBoard(boardId);
}

/**
 * Delete a task
 */
function deleteCard(boardId) {
    const itemId = document.getElementById('editItemId').value;
    if (!itemId) return;
    if (confirm('Delete this task?')) {
        boardData.columns.forEach(col => {
            col.items = col.items.filter(i => i.id !== itemId);
        });
        closeModal();
        renderBoard(boardId);
        saveBoard(boardId);
    }
}

/**
 * Add a new column
 */
function addColumn(boardId) {
    const title = prompt('Enter column title:');
    if (title && title.trim()) {
        const id = title.toLowerCase().replace(/\s+/g, '-') + '-' + Date.now();
        boardData.columns.push({ id, title: title.trim(), items: [] });
        renderBoard(boardId);
        saveBoard(boardId);
    }
}

/**
 * Save the board to the server
 */
async function saveBoard(boardId) {
    updateBoardData();
    await fetch(`/api/kanban/${boardId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(boardData)
    });
    showToast('Board saved!', 'success');
}

// Close panel on Escape key
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') closeModal();
});
