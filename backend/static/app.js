let appointments = [];
let callInProgress = {};
let selectedIds = new Set();
let batchStatusTimer = null;

// Call window display removed

async function loadAppointments() {
    try {
        const response = await fetch('/api/appointments');
        appointments = await response.json();
        
        // Debug: Log first appointment to see if date is present
        if (appointments.length > 0) {
            console.log('First appointment data:', appointments[0]);
        }
        
        renderAppointments();
        updateCount();
    } catch (error) {
        console.error('Error loading appointments:', error);
    }
}

function updateCount() {
    const count = appointments.length;
    document.getElementById('appointmentCount').textContent = 
        `${count} appointment${count !== 1 ? 's' : ''}`;
}

function renderAppointments() {
    const container = document.getElementById('appointmentsTable');
    
    if (appointments.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                </svg>
                <h3>No Unconfirmed Appointments</h3>
                <p>Upload a Practice Fusion PDF to get started</p>
            </div>
        `;
        return;
    }
    
    const table = `
        <table>
            <thead>
                <tr>
                    <th><input type="checkbox" id="selectAll" /></th>
                    <th>Patient</th>
                    <th>Phone</th>
                    <th>Date</th>
                    <th>Time</th>
                    <th>Provider</th>
                    <th>Type</th>
                    <th>Status</th>
                    <th>Outcome</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                ${appointments.map(apt => `
                    <tr>
                        <td><input type="checkbox" class="rowSelect" data-id="${apt.id}" ${selectedIds.has(apt.id) ? 'checked' : ''} /></td>
                        <td>${escapeHtml(apt.patient_name)}</td>
                        <td>${apt.phone}</td>
                        <td>${apt.appointment_date || 'Not set'}</td>
                        <td>${apt.appointment_time}</td>
                        <td>${apt.provider}</td>
                        <td>${apt.appointment_type}</td>
                        <td>
                            <span class="status-badge status-${apt.status.toLowerCase().replace(/\s+/g, '-')}">
                                ${apt.status}
                            </span>
                        </td>
                        <td>
                            ${renderOutcome(apt)}
                        </td>
                        <td>
                            ${renderActions(apt)}
                        </td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
        <div style="margin-top:12px; display:flex; gap:10px; align-items:center;">
            <button id="callSelectedBtn" ${selectedIds.size === 0 ? 'disabled' : ''}>Call Selected</button>
            <button id="cancelBatchBtn">Cancel Batch</button>
            <span id="batchStatus" style="font-size:12px;color:#555;"></span>
        </div>
    `;
    
    container.innerHTML = table;

    // Wire selection events
    const selectAll = document.getElementById('selectAll');
    if (selectAll) {
        selectAll.addEventListener('change', (e) => {
            if (e.target.checked) {
                appointments.forEach(a => selectedIds.add(a.id));
            } else {
                selectedIds.clear();
            }
            renderAppointments();
        });
    }
    document.querySelectorAll('.rowSelect').forEach(cb => {
        cb.addEventListener('change', (e) => {
            const id = e.target.getAttribute('data-id');
            if (e.target.checked) selectedIds.add(id); else selectedIds.delete(id);
            // Update button state without full re-render
            const btn = document.getElementById('callSelectedBtn');
            if (btn) btn.disabled = selectedIds.size === 0;
        });
    });

    const callBtn = document.getElementById('callSelectedBtn');
    if (callBtn) callBtn.addEventListener('click', startBatchCall);
    const cancelBtn = document.getElementById('cancelBatchBtn');
    if (cancelBtn) cancelBtn.addEventListener('click', cancelBatchCall);
}

function renderActions(apt) {
    const canCall = !['Confirmed', 'Cancelled', 'Do Not Call'].includes(apt.status);
    const isCallInProgress = callInProgress[apt.id];
    
    if (!canCall) {
        return '<span style="color: #999;">—</span>';
    }
    
    if (isCallInProgress) {
        return '<span class="loader"></span>';
    }
    
    return `
        <button class="call-button" onclick="initiateCall('${apt.id}')" 
                ${apt.status === 'Calling' ? 'disabled' : ''}>
            ${apt.status === 'Calling' ? 'Calling...' : 'Call Now'}
        </button>
    `;
}
async function startBatchCall() {
    if (selectedIds.size === 0) return;
    const override = false;
    const ids = Array.from(selectedIds);
    try {
        const res = await fetch('/api/calls/batch', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ appointment_ids: ids, override_window: override })
        });
        if (!res.ok) throw new Error('Batch start failed');
        showMessage('callMessage', 'success', 'Batch calling started.');
        pollBatchStatus();
    } catch (e) {
        showMessage('callMessage', 'error', 'Failed to start batch calling.');
    }
}

async function cancelBatchCall() {
    try {
        await fetch('/api/calls/batch-cancel', { method: 'POST' });
        showMessage('callMessage', 'success', 'Batch cancelled.');
        stopBatchPolling();
        await loadAppointments();
    } catch (e) {}
}

async function pollBatchStatus() {
    stopBatchPolling();
    batchStatusTimer = setInterval(async () => {
        try {
            const res = await fetch('/api/calls/batch-status');
            const data = await res.json();
            const el = document.getElementById('batchStatus');
            if (el) {
                el.textContent = data.active
                    ? `Active — queued: ${data.queued_count}, done: ${data.done_count}, errors: ${data.error_count}`
                    : 'Idle';
            }
            if (!data.active) {
                stopBatchPolling();
                // refresh table at the end
                await loadAppointments();
            }
        } catch {}
    }, 2000);
}

function stopBatchPolling() {
    if (batchStatusTimer) {
        clearInterval(batchStatusTimer);
        batchStatusTimer = null;
    }
}

function renderOutcome(apt) {
    let outcome = '';
    if (apt.last_answered_by) {
        if (apt.last_answered_by.startsWith('machine')) outcome = 'Voicemail detected';
        else if (apt.last_answered_by === 'human') outcome = 'Human answered';
        else outcome = 'Unknown';
    } else if (apt.status === 'Calling') {
        outcome = 'In progress';
    } else if (apt.status === 'Voicemail/No Answer') {
        outcome = 'Voicemail/No Answer';
    } else if (apt.status === 'Not Confirmed' && apt.notes && apt.notes.toLowerCase().includes('no response')) {
        outcome = 'Completed - no response';
    } else if (apt.notes) {
        outcome = escapeHtml(apt.notes);
    }

    const callbackBadge = apt.needs_callback ? '<span class="status-badge status-callback">Consider callback</span>' : '';
    return `${escapeHtml(outcome)} ${callbackBadge}`;
}

async function initiateCall(appointmentId) {
    callInProgress[appointmentId] = true;
    renderAppointments();
    
    const override = false;
    
    console.log('Override checkbox checked:', override);  // Debug log
    
    try {
        const response = await fetch(`/api/call/${appointmentId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                override_window: override
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showMessage('callMessage', 'success', 'Call initiated successfully. Monitor the status in the table.');
            setTimeout(() => loadAppointments(), 2000);
        } else {
            showMessage('callMessage', 'error', data.detail || 'Failed to initiate call');
        }
    } catch (error) {
        showMessage('callMessage', 'error', 'Network error. Please try again.');
    } finally {
        delete callInProgress[appointmentId];
        loadAppointments();
    }
}

function showMessage(elementId, type, text) {
    const messageEl = document.getElementById(elementId);
    messageEl.className = `message ${type} show`;
    messageEl.textContent = text;
    
    setTimeout(() => {
        messageEl.classList.remove('show');
    }, 5000);
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

document.getElementById('uploadForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const fileInput = document.getElementById('pdfFile');
    const file = fileInput.files[0];
    
    if (!file) {
        showMessage('uploadMessage', 'error', 'Please select a PDF file');
        return;
    }
    
    const formData = new FormData();
    formData.append('file', file);
    
    const submitButton = e.target.querySelector('button[type="submit"]');
    submitButton.disabled = true;
    submitButton.innerHTML = 'Uploading<span class="loader"></span>';
    
    try {
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showMessage('uploadMessage', 'success', data.message);
            fileInput.value = '';
            await loadAppointments();
        } else {
            showMessage('uploadMessage', 'error', data.detail || 'Failed to upload PDF');
        }
    } catch (error) {
        showMessage('uploadMessage', 'error', 'Network error. Please try again.');
    } finally {
        submitButton.disabled = false;
        submitButton.innerHTML = 'Upload & Parse PDF';
    }
});

loadAppointments();

setInterval(loadAppointments, 3000);  // Refresh every 3 seconds to see status updates