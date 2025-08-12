let appointments = [];
let callInProgress = {};

async function checkCallWindow() {
    try {
        const response = await fetch('/healthz');
        const data = await response.json();
        const statusEl = document.getElementById('callWindowStatus');
        
        if (data.call_window_active) {
            statusEl.className = 'call-window-info active';
            statusEl.innerHTML = `✓ Call Window Active: ${data.settings.call_window}`;
        } else {
            statusEl.className = 'call-window-info inactive';
            statusEl.innerHTML = `✗ Outside Call Window: ${data.settings.call_window}`;
        }
    } catch (error) {
        console.error('Error checking call window:', error);
    }
}

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
    `;
    
    container.innerHTML = table;
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
    
    const overrideCheckbox = document.getElementById('overrideCallWindow');
    const override = overrideCheckbox ? overrideCheckbox.checked : false;
    
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

checkCallWindow();
loadAppointments();

setInterval(checkCallWindow, 60000);
setInterval(loadAppointments, 3000);  // Refresh every 3 seconds to see status updates