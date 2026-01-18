// Remote Desktop Viewer Web Client
const socket = io();
let clients = [];
let currentClientIndex = -1;
let currentClientId = null;
let frameUpdateInterval = null;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    setupEventListeners();
    loadClients();
    
    // Set up keyboard shortcuts
    document.addEventListener('keydown', handleKeyboard);
    
    // Start frame update loop
    startFrameUpdate();
});

function setupEventListeners() {
    document.getElementById('refreshBtn').addEventListener('click', loadClients);
    document.getElementById('displaySelect').addEventListener('change', handleDisplayChange);
}

function loadClients() {
    fetch('/api/clients')
        .then(res => res.json())
        .then(data => {
            clients = data;
            renderClientList();
            if (clients.length > 0 && currentClientIndex === -1) {
                selectClient(0);
            }
        })
        .catch(err => {
            console.error('Error loading clients:', err);
            showAlert('Error loading clients');
        });
}

function renderClientList() {
    const container = document.getElementById('clientList');
    container.innerHTML = '';
    
    if (clients.length === 0) {
        container.innerHTML = '<p style="color: #888; text-align: center; padding: 20px;">No clients connected</p>';
        return;
    }
    
    clients.forEach((client, index) => {
        const item = document.createElement('div');
        item.className = 'client-item' + (client.disabled ? ' disabled' : '');
        item.dataset.clientId = client.id;
        
        // Disable buttons if client is disabled
        const buttonsDisabled = client.disabled ? 'disabled' : '';
        const buttonOpacity = client.disabled ? 'opacity: 0.5; cursor: not-allowed;' : '';
        
        item.innerHTML = `
            <div class="client-header">
                <label style="display: flex; align-items: center; cursor: pointer;">
                    <input type="checkbox" class="client-checkbox" ${client.disabled ? 'checked' : ''} 
                           onchange="toggleDisable('${client.id}', this.checked)">
                    <span style="margin-left: 5px; font-size: 12px; color: #aaa;">Disable</span>
                </label>
                <span class="client-name">${client.name}</span>
            </div>
            <div class="client-actions">
                <button class="btn-webcam ${client.webcam_active ? 'active' : ''}" 
                        onclick="toggleWebcam('${client.id}')"
                        ${buttonsDisabled}
                        style="${buttonOpacity}">
                    ${client.webcam_active ? 'Stop Webcam' : 'Webcam'}
                </button>
                <button class="btn-control ${client.control_active ? 'active' : ''}" 
                        onclick="toggleControl('${client.id}')"
                        ${buttonsDisabled}
                        style="${buttonOpacity}">
                    ${client.control_active ? 'Stop Control' : 'Control'}
                </button>
            </div>
        `;
        
        item.addEventListener('click', (e) => {
            if (e.target.type !== 'checkbox' && e.target.tagName !== 'BUTTON' && e.target.tagName !== 'LABEL') {
                selectClient(index);
            }
        });
        
        container.appendChild(item);
    });
}

function toggleDisable(clientId, isDisabled) {
    fetch(`/api/client/${clientId}/disable`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'}
    })
    .then(res => res.json())
    .then(data => {
        loadClients();
        // If current client was disabled, stop showing its display
        if (isDisabled && currentClientId === clientId) {
            document.getElementById('screenDisplay').style.display = 'none';
            document.getElementById('noClients').style.display = 'block';
            updateStatus('Client disabled - select another client');
        }
    })
    .catch(err => {
        console.error('Error toggling disable:', err);
        showAlert('Error toggling disable');
    });
}

function toggleWebcam(clientId) {
    console.log('toggleWebcam called for client:', clientId);
    
    // Check if client is disabled
    const client = clients.find(c => c.id === clientId);
    if (client && client.disabled) {
        showAlert('Client is disabled. Uncheck "Disable" first.');
        return;
    }
    
    // Send request to server
    fetch(`/api/client/${clientId}/webcam`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'}
    })
    .then(res => {
        console.log('Webcam toggle response status:', res.status);
        return res.json();
    })
    .then(data => {
        console.log('Webcam toggle response data:', data);
        if (data.error) {
            showAlert('No Service: ' + data.error);
            loadClients();
        } else {
            // Wait a bit for potential error from client before updating UI
            // If webcam fails, error handler will reset state within ~100ms
            setTimeout(() => {
                loadClients();
            }, 150);
        }
    })
    .catch(err => {
        console.error('Error toggling webcam:', err);
        showAlert('No Service: Webcam not available');
        loadClients();
    });
}

function toggleControl(clientId) {
    // Check if client is disabled
    const client = clients.find(c => c.id === clientId);
    if (client && client.disabled) {
        showAlert('Client is disabled. Uncheck "Disable" first.');
        return;
    }
    
    fetch(`/api/client/${clientId}/control`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'}
    })
    .then(res => res.json())
    .then(data => {
        loadClients();
        if (data.control_active) {
            // Enter control mode - focus on screen for input
            document.getElementById('screenDisplay').focus();
        }
    })
    .catch(err => {
        console.error('Error toggling control:', err);
        showAlert('Error toggling control');
    });
}

function selectClient(index) {
    if (index < 0 || index >= clients.length) return;
    
    const client = clients[index];
    
    // If client is disabled, don't show display
    if (client.disabled) {
        showAlert('This client is disabled. Uncheck "Disable" to view.');
        return;
    }
    
    currentClientIndex = index;
    currentClientId = client.id;
    
    // Update UI
    document.querySelectorAll('.client-item').forEach((item, i) => {
        if (i === index) {
            item.style.border = '2px solid #4CAF50';
        } else {
            item.style.border = '1px solid #444';
        }
    });
    
    updateStatus(`Viewing: ${client.name}`);
    loadFrame();
}

function findNextEnabledClient() {
    const enabledClients = clients.filter(c => !c.disabled);
    if (enabledClients.length === 0) {
        currentClientIndex = -1;
        currentClientId = null;
        document.getElementById('screenDisplay').style.display = 'none';
        document.getElementById('noClients').style.display = 'block';
        updateStatus('No enabled clients');
        return;
    }
    
    const currentIndex = enabledClients.findIndex(c => c.id === currentClientId);
    const nextIndex = currentIndex >= 0 ? (currentIndex + 1) % enabledClients.length : 0;
    const nextClient = enabledClients[nextIndex];
    const actualIndex = clients.findIndex(c => c.id === nextClient.id);
    selectClient(actualIndex);
}

function findPreviousEnabledClient() {
    const enabledClients = clients.filter(c => !c.disabled);
    if (enabledClients.length === 0) {
        currentClientIndex = -1;
        currentClientId = null;
        document.getElementById('screenDisplay').style.display = 'none';
        document.getElementById('noClients').style.display = 'block';
        updateStatus('No enabled clients');
        return;
    }
    
    const currentIndex = enabledClients.findIndex(c => c.id === currentClientId);
    const prevIndex = currentIndex > 0 ? currentIndex - 1 : enabledClients.length - 1;
    const prevClient = enabledClients[prevIndex];
    const actualIndex = clients.findIndex(c => c.id === prevClient.id);
    selectClient(actualIndex);
}

function handleKeyboard(e) {
    // Page Up - next client
    if (e.key === 'PageUp') {
        e.preventDefault();
        findNextEnabledClient();
    }
    // Page Down - previous client
    else if (e.key === 'PageDown') {
        e.preventDefault();
        findPreviousEnabledClient();
    }
}

function handleDisplayChange() {
    const displayIndex = document.getElementById('displaySelect').value;
    if (currentClientId) {
        // Send display selection to server
        fetch(`/api/client/${currentClientId}/display`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({display: parseInt(displayIndex)})
        })
        .catch(err => console.error('Error changing display:', err));
    }
}

function loadFrame() {
    if (!currentClientId) return;
    
    // Check if current client is disabled
    const currentClient = clients.find(c => c.id === currentClientId);
    if (currentClient && currentClient.disabled) {
        document.getElementById('screenDisplay').style.display = 'none';
        document.getElementById('noClients').style.display = 'block';
        updateStatus('Client disabled');
        return;
    }
    
    // Request frame from server via WebSocket or polling
    // For now, we'll use polling
    const img = document.getElementById('screenDisplay');
    img.src = `/api/client/${currentClientId}/frame?t=${Date.now()}`;
    img.style.display = 'block';
    document.getElementById('noClients').style.display = 'none';
}

function startFrameUpdate() {
    // Update frame every 50ms (20 FPS)
    frameUpdateInterval = setInterval(() => {
        if (currentClientId) {
            loadFrame();
        }
    }, 50);
}

function updateStatus(text) {
    document.getElementById('statusText').textContent = text;
}

function showAlert(message) {
    console.log('ALERT:', message); // Debug log
    
    // Use browser native alert for now (more visible)
    alert(message);
    
    // Also show custom alert
    const alertDiv = document.getElementById('alert');
    if (alertDiv) {
        alertDiv.textContent = message;
        alertDiv.classList.add('show');
        
        // Hide after 5 seconds
        setTimeout(() => {
            alertDiv.classList.remove('show');
        }, 5000);
    }
}

// Socket.IO event handlers
socket.on('connect', () => {
    console.log('Connected to server');
    socket.emit('get_clients');
});

socket.on('clients_list', (data) => {
    clients = data.clients;
    renderClientList();
});

socket.on('frame_update', (data) => {
    if (data.client_id === currentClientId) {
        const img = document.getElementById('screenDisplay');
        img.src = 'data:image/jpeg;base64,' + data.frame;
    }
});

socket.on('webcam_error', (data) => {
    console.log('=== WEBCAM ERROR EVENT RECEIVED ===');
    console.log('Received webcam_error event:', data);
    console.log('Message:', data.message);
    console.log('Client ID:', data.client_id);
    
    const alertMessage = 'No Service: ' + data.message;
    console.log('Showing alert:', alertMessage);
    showAlert(alertMessage);
    
    // Reset webcam button state - reload clients to update UI
    console.log('Reloading clients...');
    loadClients();
});
