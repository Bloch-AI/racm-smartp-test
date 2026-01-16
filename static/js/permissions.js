/**
 * Permissions and Workflow State Management for SmartPapers
 *
 * This module provides:
 * - Status badge rendering
 * - Permission checking for UI elements
 * - Workflow action modals
 * - API calls for state transitions
 */

// Status badge configuration
const STATUS_BADGES = {
    'draft': {
        icon: '<svg class="w-3 h-3" fill="currentColor" viewBox="0 0 20 20"><path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z"/></svg>',
        text: 'Draft',
        class: 'bg-blue-100 text-blue-700'
    },
    'in_review': {
        icon: '<svg class="w-3 h-3" fill="currentColor" viewBox="0 0 20 20"><path d="M9 2a1 1 0 000 2h2a1 1 0 100-2H9z"/><path fill-rule="evenodd" d="M4 5a2 2 0 012-2 3 3 0 003 3h2a3 3 0 003-3 2 2 0 012 2v11a2 2 0 01-2 2H6a2 2 0 01-2-2V5zm3 4a1 1 0 000 2h.01a1 1 0 100-2H7zm3 0a1 1 0 000 2h3a1 1 0 100-2h-3zm-3 4a1 1 0 100 2h.01a1 1 0 100-2H7zm3 0a1 1 0 100 2h3a1 1 0 100-2h-3z" clip-rule="evenodd"/></svg>',
        text: 'In Review',
        class: 'bg-amber-100 text-amber-700'
    },
    'admin_hold': {
        icon: '<svg class="w-3 h-3" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zM7 8a1 1 0 012 0v4a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v4a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd"/></svg>',
        text: 'Admin Hold',
        class: 'bg-red-100 text-red-700'
    },
    'signed_off': {
        icon: '<svg class="w-3 h-3" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/></svg>',
        text: 'Signed Off',
        class: 'bg-green-100 text-green-700'
    }
};

/**
 * Render a status badge for a record
 * @param {string} status - The record status (draft, in_review, admin_hold, signed_off)
 * @returns {string} HTML for the status badge
 */
function renderStatusBadge(status) {
    const badge = STATUS_BADGES[status] || STATUS_BADGES['draft'];
    return `<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${badge.class}">
        ${badge.icon}
        ${badge.text}
    </span>`;
}

/**
 * Render workflow action buttons based on permissions
 * @param {Object} metadata - Record metadata including permissions
 * @param {string} recordType - 'risk' or 'issue'
 * @returns {string} HTML for action buttons
 */
function renderWorkflowActions(metadata, recordType) {
    const permissions = metadata.permissions || {};
    const buttons = [];

    if (permissions.canSubmitForReview) {
        buttons.push(`
            <button onclick="showSubmitForReviewModal('${recordType}', ${metadata.id})"
                    class="text-xs px-2 py-1 bg-blue-500 text-white rounded hover:bg-blue-600 transition-colors">
                Submit for Review
            </button>
        `);
    }

    if (permissions.canReturnToAuditor) {
        buttons.push(`
            <button onclick="showReturnToAuditorModal('${recordType}', ${metadata.id})"
                    class="text-xs px-2 py-1 bg-amber-500 text-white rounded hover:bg-amber-600 transition-colors">
                Return to Auditor
            </button>
        `);
    }

    if (permissions.canSignOff) {
        buttons.push(`
            <button onclick="showSignOffModal('${recordType}', ${metadata.id})"
                    class="text-xs px-2 py-1 bg-green-500 text-white rounded hover:bg-green-600 transition-colors">
                Sign Off
            </button>
        `);
    }

    if (permissions.canAdminLock) {
        buttons.push(`
            <button onclick="showAdminLockModal('${recordType}', ${metadata.id})"
                    class="text-xs px-2 py-1 bg-red-500 text-white rounded hover:bg-red-600 transition-colors">
                Lock
            </button>
        `);
    }

    if (permissions.canAdminUnlock) {
        buttons.push(`
            <button onclick="showAdminUnlockModal('${recordType}', ${metadata.id})"
                    class="text-xs px-2 py-1 bg-slate-500 text-white rounded hover:bg-slate-600 transition-colors">
                Unlock
            </button>
        `);
    }

    if (permissions.canAdminUnlockSignoff) {
        buttons.push(`
            <button onclick="showAdminUnlockSignoffModal('${recordType}', ${metadata.id})"
                    class="text-xs px-2 py-1 bg-red-600 text-white rounded hover:bg-red-700 transition-colors">
                Unlock Sign-off
            </button>
        `);
    }

    return buttons.length > 0 ? `<div class="flex gap-1 flex-wrap">${buttons.join('')}</div>` : '';
}

// ==================== Modal Functions ====================

/**
 * Show the submit for review modal with reviewer selection
 */
function showSubmitForReviewModal(recordType, recordId) {
    // Get reviewers from audit team (set by index.html from API response)
    const reviewers = (typeof auditTeam !== 'undefined' && auditTeam.reviewers) ? auditTeam.reviewers : [];

    // Build reviewer options
    let reviewerOptions = '';
    if (reviewers.length === 0) {
        reviewerOptions = '<option value="">No reviewers assigned</option>';
    } else {
        reviewerOptions = '<option value="">Select a reviewer...</option>' +
            reviewers.map(r => `<option value="${r.user_id}">${escapeHtml(r.user_name)}</option>`).join('');
    }

    const modalHtml = `
        <div id="workflow-modal" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div class="bg-white rounded-lg shadow-xl max-w-md w-full mx-4 p-6">
                <h3 class="text-lg font-semibold text-slate-900 mb-4">Submit for Review</h3>
                <p class="text-sm text-slate-600 mb-4">
                    Once submitted, you will no longer be able to edit this record until it is returned.
                </p>
                <div class="mb-4">
                    <label class="block text-sm font-medium text-slate-700 mb-1">
                        Select Reviewer <span class="text-red-500">*</span>
                    </label>
                    <select id="modal-reviewer" required
                        class="w-full px-3 py-2 border border-slate-300 rounded-md text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
                        ${reviewerOptions}
                    </select>
                    ${reviewers.length === 0 ? '<p class="text-xs text-red-500 mt-1">No reviewers are assigned to this audit. Please ask an admin to assign reviewers.</p>' : ''}
                </div>
                <div class="mb-4">
                    <label class="block text-sm font-medium text-slate-700 mb-1">Notes (optional)</label>
                    <textarea id="modal-notes" rows="3"
                        class="w-full px-3 py-2 border border-slate-300 rounded-md text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                        placeholder="Add any notes for the reviewer..."></textarea>
                </div>
                <div class="flex justify-end gap-3">
                    <button onclick="closeWorkflowModal()"
                        class="px-4 py-2 text-sm text-slate-700 hover:bg-slate-100 rounded-md transition-colors">
                        Cancel
                    </button>
                    <button onclick="submitForReview('${recordType}', ${recordId})"
                        class="px-4 py-2 text-sm bg-blue-500 text-white rounded-md hover:bg-blue-600 transition-colors"
                        ${reviewers.length === 0 ? 'disabled' : ''}>
                        Submit for Review
                    </button>
                </div>
            </div>
        </div>
    `;
    document.body.insertAdjacentHTML('beforeend', modalHtml);
}

/**
 * Show the return to auditor modal
 */
function showReturnToAuditorModal(recordType, recordId) {
    const modalHtml = `
        <div id="workflow-modal" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div class="bg-white rounded-lg shadow-xl max-w-md w-full mx-4 p-6">
                <h3 class="text-lg font-semibold text-slate-900 mb-4">Return to Auditor</h3>
                <p class="text-sm text-slate-600 mb-4">
                    Please provide feedback explaining why the record is being returned.
                </p>
                <div class="mb-4">
                    <label class="block text-sm font-medium text-slate-700 mb-1">Feedback Notes <span class="text-red-500">*</span></label>
                    <textarea id="modal-notes" rows="3" required
                        class="w-full px-3 py-2 border border-slate-300 rounded-md text-sm focus:ring-2 focus:ring-amber-500 focus:border-amber-500"
                        placeholder="Explain why this record is being returned..."></textarea>
                </div>
                <div class="flex justify-end gap-3">
                    <button onclick="closeWorkflowModal()"
                        class="px-4 py-2 text-sm text-slate-700 hover:bg-slate-100 rounded-md transition-colors">
                        Cancel
                    </button>
                    <button onclick="returnToAuditor('${recordType}', ${recordId})"
                        class="px-4 py-2 text-sm bg-amber-500 text-white rounded-md hover:bg-amber-600 transition-colors">
                        Return to Auditor
                    </button>
                </div>
            </div>
        </div>
    `;
    document.body.insertAdjacentHTML('beforeend', modalHtml);
}

/**
 * Show the sign off modal
 */
function showSignOffModal(recordType, recordId) {
    const modalHtml = `
        <div id="workflow-modal" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div class="bg-white rounded-lg shadow-xl max-w-md w-full mx-4 p-6">
                <h3 class="text-lg font-semibold text-slate-900 mb-4">Sign Off Record</h3>
                <div class="bg-amber-50 border border-amber-200 rounded-md p-3 mb-4">
                    <p class="text-sm text-amber-800 font-medium">Warning</p>
                    <p class="text-sm text-amber-700">
                        Signing off a record is a final action. Only an admin can unlock a signed-off record.
                    </p>
                </div>
                <div class="mb-4">
                    <label class="block text-sm font-medium text-slate-700 mb-1">
                        Type "SIGN OFF" to confirm <span class="text-red-500">*</span>
                    </label>
                    <input type="text" id="modal-confirmation"
                        class="w-full px-3 py-2 border border-slate-300 rounded-md text-sm focus:ring-2 focus:ring-green-500 focus:border-green-500"
                        placeholder="SIGN OFF">
                </div>
                <div class="flex justify-end gap-3">
                    <button onclick="closeWorkflowModal()"
                        class="px-4 py-2 text-sm text-slate-700 hover:bg-slate-100 rounded-md transition-colors">
                        Cancel
                    </button>
                    <button onclick="signOffRecord('${recordType}', ${recordId})"
                        class="px-4 py-2 text-sm bg-green-500 text-white rounded-md hover:bg-green-600 transition-colors">
                        Sign Off
                    </button>
                </div>
            </div>
        </div>
    `;
    document.body.insertAdjacentHTML('beforeend', modalHtml);
}

/**
 * Show the admin lock modal
 */
function showAdminLockModal(recordType, recordId) {
    const modalHtml = `
        <div id="workflow-modal" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div class="bg-white rounded-lg shadow-xl max-w-md w-full mx-4 p-6">
                <h3 class="text-lg font-semibold text-slate-900 mb-4">Admin Lock Record</h3>
                <p class="text-sm text-slate-600 mb-4">
                    This will place the record on hold, preventing any edits until unlocked.
                </p>
                <div class="mb-4">
                    <label class="block text-sm font-medium text-slate-700 mb-1">Reason <span class="text-red-500">*</span></label>
                    <textarea id="modal-reason" rows="3" required
                        class="w-full px-3 py-2 border border-slate-300 rounded-md text-sm focus:ring-2 focus:ring-red-500 focus:border-red-500"
                        placeholder="Explain why this record is being locked..."></textarea>
                </div>
                <div class="flex justify-end gap-3">
                    <button onclick="closeWorkflowModal()"
                        class="px-4 py-2 text-sm text-slate-700 hover:bg-slate-100 rounded-md transition-colors">
                        Cancel
                    </button>
                    <button onclick="adminLockRecord('${recordType}', ${recordId})"
                        class="px-4 py-2 text-sm bg-red-500 text-white rounded-md hover:bg-red-600 transition-colors">
                        Lock Record
                    </button>
                </div>
            </div>
        </div>
    `;
    document.body.insertAdjacentHTML('beforeend', modalHtml);
}

/**
 * Show the admin unlock modal
 */
function showAdminUnlockModal(recordType, recordId) {
    const modalHtml = `
        <div id="workflow-modal" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div class="bg-white rounded-lg shadow-xl max-w-md w-full mx-4 p-6">
                <h3 class="text-lg font-semibold text-slate-900 mb-4">Unlock Record</h3>
                <p class="text-sm text-slate-600 mb-4">
                    Choose where to return this record after unlocking.
                </p>
                <div class="mb-4">
                    <label class="block text-sm font-medium text-slate-700 mb-1">Reason <span class="text-red-500">*</span></label>
                    <textarea id="modal-reason" rows="3" required
                        class="w-full px-3 py-2 border border-slate-300 rounded-md text-sm focus:ring-2 focus:ring-slate-500 focus:border-slate-500"
                        placeholder="Explain why this record is being unlocked..."></textarea>
                </div>
                <div class="mb-4">
                    <label class="block text-sm font-medium text-slate-700 mb-2">Return to</label>
                    <div class="flex gap-4">
                        <label class="flex items-center">
                            <input type="radio" name="return_to" value="draft" checked class="mr-2">
                            <span class="text-sm text-slate-700">Draft (Auditor)</span>
                        </label>
                        <label class="flex items-center">
                            <input type="radio" name="return_to" value="in_review" class="mr-2">
                            <span class="text-sm text-slate-700">In Review (Reviewer)</span>
                        </label>
                    </div>
                </div>
                <div class="flex justify-end gap-3">
                    <button onclick="closeWorkflowModal()"
                        class="px-4 py-2 text-sm text-slate-700 hover:bg-slate-100 rounded-md transition-colors">
                        Cancel
                    </button>
                    <button onclick="adminUnlockRecord('${recordType}', ${recordId})"
                        class="px-4 py-2 text-sm bg-slate-500 text-white rounded-md hover:bg-slate-600 transition-colors">
                        Unlock Record
                    </button>
                </div>
            </div>
        </div>
    `;
    document.body.insertAdjacentHTML('beforeend', modalHtml);
}

/**
 * Show the admin unlock signoff modal
 */
function showAdminUnlockSignoffModal(recordType, recordId) {
    const modalHtml = `
        <div id="workflow-modal" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div class="bg-white rounded-lg shadow-xl max-w-md w-full mx-4 p-6">
                <h3 class="text-lg font-semibold text-slate-900 mb-4">Unlock Signed-Off Record</h3>
                <div class="bg-red-50 border border-red-200 rounded-md p-3 mb-4">
                    <p class="text-sm text-red-800 font-medium">Caution: Audit Trail Impact</p>
                    <p class="text-sm text-red-700">
                        Unlocking a signed-off record will be logged in the audit trail. Use only when necessary.
                    </p>
                </div>
                <div class="mb-4">
                    <label class="block text-sm font-medium text-slate-700 mb-1">Reason <span class="text-red-500">*</span></label>
                    <textarea id="modal-reason" rows="3" required
                        class="w-full px-3 py-2 border border-slate-300 rounded-md text-sm focus:ring-2 focus:ring-red-500 focus:border-red-500"
                        placeholder="Explain why this signed-off record needs to be unlocked..."></textarea>
                </div>
                <div class="mb-4">
                    <label class="block text-sm font-medium text-slate-700 mb-2">Return to</label>
                    <div class="flex gap-4">
                        <label class="flex items-center">
                            <input type="radio" name="return_to" value="draft" checked class="mr-2">
                            <span class="text-sm text-slate-700">Draft (Auditor)</span>
                        </label>
                        <label class="flex items-center">
                            <input type="radio" name="return_to" value="in_review" class="mr-2">
                            <span class="text-sm text-slate-700">In Review (Reviewer)</span>
                        </label>
                    </div>
                </div>
                <div class="mb-4">
                    <label class="block text-sm font-medium text-slate-700 mb-1">
                        Type "UNLOCK SIGNED OFF" to confirm <span class="text-red-500">*</span>
                    </label>
                    <input type="text" id="modal-confirmation"
                        class="w-full px-3 py-2 border border-slate-300 rounded-md text-sm focus:ring-2 focus:ring-red-500 focus:border-red-500"
                        placeholder="UNLOCK SIGNED OFF">
                </div>
                <div class="flex justify-end gap-3">
                    <button onclick="closeWorkflowModal()"
                        class="px-4 py-2 text-sm text-slate-700 hover:bg-slate-100 rounded-md transition-colors">
                        Cancel
                    </button>
                    <button onclick="adminUnlockSignoff('${recordType}', ${recordId})"
                        class="px-4 py-2 text-sm bg-red-600 text-white rounded-md hover:bg-red-700 transition-colors">
                        Unlock Record
                    </button>
                </div>
            </div>
        </div>
    `;
    document.body.insertAdjacentHTML('beforeend', modalHtml);
}

/**
 * Close the workflow modal
 */
function closeWorkflowModal() {
    const modal = document.getElementById('workflow-modal');
    if (modal) modal.remove();
}

// ==================== API Call Functions ====================

async function submitForReview(recordType, recordId) {
    const notes = document.getElementById('modal-notes')?.value || '';
    const reviewerId = document.getElementById('modal-reviewer')?.value;

    // Validate reviewer selection
    if (!reviewerId) {
        showToast('Please select a reviewer', 'error');
        return;
    }

    try {
        const response = await fetch(`/api/records/${recordType}/${recordId}/submit-for-review`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'same-origin',
            body: JSON.stringify({ notes, reviewer_id: parseInt(reviewerId) })
        });

        const data = await response.json();
        if (response.ok) {
            closeWorkflowModal();
            showToast('Record submitted for review', 'success');
            if (typeof loadData === 'function') loadData();
        } else {
            showToast(data.error || 'Failed to submit for review', 'error');
        }
    } catch (err) {
        showToast('Network error', 'error');
    }
}

async function returnToAuditor(recordType, recordId) {
    const notes = document.getElementById('modal-notes')?.value || '';

    if (!notes.trim()) {
        showToast('Feedback notes are required', 'error');
        return;
    }

    try {
        const response = await fetch(`/api/records/${recordType}/${recordId}/return-to-auditor`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'same-origin',
            body: JSON.stringify({ notes })
        });

        const data = await response.json();
        if (response.ok) {
            closeWorkflowModal();
            showToast('Record returned to auditor', 'success');
            if (typeof loadData === 'function') loadData();
        } else {
            showToast(data.error || 'Failed to return record', 'error');
        }
    } catch (err) {
        showToast('Network error', 'error');
    }
}

async function signOffRecord(recordType, recordId) {
    const confirmation = document.getElementById('modal-confirmation')?.value || '';

    if (confirmation !== 'SIGN OFF') {
        showToast('Please type "SIGN OFF" to confirm', 'error');
        return;
    }

    try {
        const response = await fetch(`/api/records/${recordType}/${recordId}/sign-off`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'same-origin',
            body: JSON.stringify({ confirmation })
        });

        const data = await response.json();
        if (response.ok) {
            closeWorkflowModal();
            showToast('Record signed off', 'success');
            if (typeof loadData === 'function') loadData();
        } else {
            showToast(data.error || 'Failed to sign off', 'error');
        }
    } catch (err) {
        showToast('Network error', 'error');
    }
}

async function adminLockRecord(recordType, recordId) {
    const reason = document.getElementById('modal-reason')?.value || '';

    if (!reason.trim()) {
        showToast('Reason is required', 'error');
        return;
    }

    try {
        const response = await fetch(`/api/admin/records/${recordType}/${recordId}/lock`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'same-origin',
            body: JSON.stringify({ reason })
        });

        const data = await response.json();
        if (response.ok) {
            closeWorkflowModal();
            showToast('Record locked', 'success');
            if (typeof loadData === 'function') loadData();
        } else {
            showToast(data.error || 'Failed to lock record', 'error');
        }
    } catch (err) {
        showToast('Network error', 'error');
    }
}

async function adminUnlockRecord(recordType, recordId) {
    const reason = document.getElementById('modal-reason')?.value || '';
    const return_to = document.querySelector('input[name="return_to"]:checked')?.value || 'draft';

    if (!reason.trim()) {
        showToast('Reason is required', 'error');
        return;
    }

    try {
        const response = await fetch(`/api/admin/records/${recordType}/${recordId}/unlock`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'same-origin',
            body: JSON.stringify({ reason, return_to })
        });

        const data = await response.json();
        if (response.ok) {
            closeWorkflowModal();
            showToast('Record unlocked', 'success');
            if (typeof loadData === 'function') loadData();
        } else {
            showToast(data.error || 'Failed to unlock record', 'error');
        }
    } catch (err) {
        showToast('Network error', 'error');
    }
}

async function adminUnlockSignoff(recordType, recordId) {
    const reason = document.getElementById('modal-reason')?.value || '';
    const return_to = document.querySelector('input[name="return_to"]:checked')?.value || 'draft';
    const confirmation = document.getElementById('modal-confirmation')?.value || '';

    if (!reason.trim()) {
        showToast('Reason is required', 'error');
        return;
    }

    if (confirmation !== 'UNLOCK SIGNED OFF') {
        showToast('Please type "UNLOCK SIGNED OFF" to confirm', 'error');
        return;
    }

    try {
        const response = await fetch(`/api/admin/records/${recordType}/${recordId}/unlock-signoff`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'same-origin',
            body: JSON.stringify({ reason, return_to, confirmation })
        });

        const data = await response.json();
        if (response.ok) {
            closeWorkflowModal();
            showToast('Signed-off record unlocked', 'success');
            if (typeof loadData === 'function') loadData();
        } else {
            showToast(data.error || 'Failed to unlock record', 'error');
        }
    } catch (err) {
        showToast('Network error', 'error');
    }
}

/**
 * Check if a row should be editable based on permissions
 * @param {Object} metadata - Row metadata including permissions
 * @returns {boolean}
 */
function isRowEditable(metadata) {
    return metadata?.permissions?.canEdit || false;
}

/**
 * Get the CSS class for a row based on its status
 * @param {string} status - Record status
 * @returns {string} CSS class name
 */
function getRowStatusClass(status) {
    const classes = {
        'draft': '',
        'in_review': 'bg-amber-50',
        'admin_hold': 'bg-red-50',
        'signed_off': 'bg-green-50'
    };
    return classes[status] || '';
}
