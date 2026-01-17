/**
 * SmartPapers Navigation Dropdowns
 * Handles audit selector and user menu dropdowns
 */

function toggleAuditDropdown() {
    const menu = document.getElementById('audit-dropdown-menu');
    const arrow = document.getElementById('audit-dropdown-arrow');
    // Close user dropdown if open
    closeUserDropdown();
    if (menu) {
        menu.classList.toggle('hidden');
        if (arrow) {
            arrow.classList.toggle('rotate-180');
        }
    }
}

function toggleUserDropdown() {
    const menu = document.getElementById('user-dropdown-menu');
    const arrow = document.getElementById('user-dropdown-arrow');
    // Close audit dropdown if open
    closeAuditDropdown();
    if (menu) {
        menu.classList.toggle('hidden');
        if (arrow) {
            arrow.classList.toggle('rotate-180');
        }
    }
}

function closeAuditDropdown() {
    const menu = document.getElementById('audit-dropdown-menu');
    const arrow = document.getElementById('audit-dropdown-arrow');
    if (menu) menu.classList.add('hidden');
    if (arrow) arrow.classList.remove('rotate-180');
}

function closeUserDropdown() {
    const menu = document.getElementById('user-dropdown-menu');
    const arrow = document.getElementById('user-dropdown-arrow');
    if (menu) menu.classList.add('hidden');
    if (arrow) arrow.classList.remove('rotate-180');
}

function switchAudit(auditId) {
    fetch('/api/auth/set-audit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'same-origin',
        body: JSON.stringify({ audit_id: parseInt(auditId) })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'ok') {
            // Reload the page to refresh data for the new audit
            window.location.href = '/';
        } else {
            alert('Failed to switch audit: ' + (data.error || 'Unknown error'));
        }
    })
    .catch(error => {
        console.error('Error switching audit:', error);
        alert('Failed to switch audit');
    });
}

// Close dropdowns when clicking outside
document.addEventListener('click', function(event) {
    const auditContainer = document.getElementById('audit-dropdown-container');
    const userContainer = document.getElementById('user-dropdown-container');

    if (auditContainer && !auditContainer.contains(event.target)) {
        closeAuditDropdown();
    }
    if (userContainer && !userContainer.contains(event.target)) {
        closeUserDropdown();
    }
});
