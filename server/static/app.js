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
    loadDeletedClients();
    
    // Set up keyboard shortcuts
    document.addEventListener('keydown', handleKeyboard);
    
    // Start frame update loop
    startFrameUpdate();
});

function setupEventListeners() {
    document.getElementById('refreshBtn').addEventListener('click', () => {
        loadClients();
        loadDeletedClients();
    });
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
        
        // Check if this client has control active (from local state, not server state)
        const isControlActive = (controlActive && controlClientId === client.id);
        
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
                <button class="btn-control ${isControlActive ? 'active' : ''}" 
                        onclick="toggleControl('${client.id}')"
                        ${buttonsDisabled}
                        style="${buttonOpacity}">
                    ${isControlActive ? 'Stop Control' : 'Control'}
                </button>
                <button class="btn-delete" 
                        onclick="deleteClient('${client.id}', '${client.name}')"
                        style="background: #f44336; color: white; padding: 8px 16px; border: none; border-radius: 4px; cursor: pointer; font-size: 14px; margin-right: 8px;">
                    Delete
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
                // Restart frame update with correct interval for webcam state
                if (currentClientId === clientId) {
                    startFrameUpdate();
                }
            }, 150);
        }
    })
    .catch(err => {
        console.error('Error toggling webcam:', err);
        showAlert('No Service: Webcam not available');
        loadClients();
    });
}

function deleteClient(clientId, clientName) {
    if (!confirm(`Delete client "${clientName}"?\n\nDeleted clients will be hidden from the list until restored.`)) {
        return;
    }
    
    fetch(`/api/client/${clientId}/delete`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'}
    })
    .then(res => res.json())
    .then(data => {
        if (data.error) {
            alert('Delete failed: ' + data.error);
        } else {
            // If current client was deleted, clear the display
            if (currentClientId === clientId) {
                document.getElementById('screenDisplay').style.display = 'none';
                document.getElementById('noClients').style.display = 'block';
                updateStatus('Client deleted');
                currentClientId = null;
                currentClientIndex = -1;
            }
            // Reload clients
            loadClients();
            loadDeletedClients();
        }
    })
    .catch(err => {
        console.error('Error deleting client:', err);
        alert('Error deleting client');
    });
}

function restoreClient(clientId, clientName) {
    fetch(`/api/client/${clientId}/restore`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'}
    })
    .then(res => res.json())
    .then(data => {
        if (data.error) {
            alert('Restore failed: ' + data.error);
        } else {
            // Reload both lists
            loadClients();
            loadDeletedClients();
        }
    })
    .catch(err => {
        console.error('Error restoring client:', err);
        alert('Error restoring client');
    });
}

function loadDeletedClients() {
    console.log('Loading deleted clients...');
    fetch('/api/client/deleted')
    .then(res => {
        console.log('Deleted clients response status:', res.status);
        if (!res.ok) {
            throw new Error(`HTTP error! status: ${res.status}`);
        }
        return res.json();
    })
    .then(deletedClients => {
        console.log('Deleted clients received:', deletedClients);
        const container = document.getElementById('deletedClientsList');
        if (!container) {
            console.error('deletedClientsList container not found!');
            return;
        }
        
        container.innerHTML = '';
        
        if (!deletedClients || deletedClients.length === 0) {
            container.innerHTML = '<div style="padding: 10px; color: #888; text-align: center;">No deleted clients</div>';
            return;
        }
        
        deletedClients.forEach(client => {
            const item = document.createElement('div');
            item.className = 'client-item';
            item.style.cssText = 'padding: 10px; border-bottom: 1px solid #444; cursor: pointer;';
            
            item.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span class="client-name" style="color: #888;">${client.name}</span>
                    <button class="btn-restore" 
                            onclick="restoreClient('${client.id}', '${client.name}'); event.stopPropagation();"
                            style="background: #4CAF50; color: white; padding: 6px 12px; border: none; border-radius: 4px; cursor: pointer; font-size: 12px;">
                        Restore
                    </button>
                </div>
            `;
            
            container.appendChild(item);
        });
        console.log(`Loaded ${deletedClients.length} deleted clients`);
    })
    .catch(err => {
        console.error('Error loading deleted clients:', err);
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
        if (data.control_active) {
            // Control mode activated - enable input capture
            enableControlMode(clientId);
        } else {
            // Control mode deactivated - disable input capture
            disableControlMode();
        }
        // Reload clients to update button state (but control mode will persist)
        loadClients();
    })
    .catch(err => {
        console.error('Error toggling control:', err);
        showAlert('Error toggling control');
    });
}

let controlActive = false;
let controlClientId = null;
let lastMousePosition = {x: 0, y: 0};
let controlEventListenersAttached = false;

function enableControlMode(clientId) {
    console.log('=== ENABLING CONTROL MODE ===');
    console.log('Client ID:', clientId);
    
    controlActive = true;
    controlClientId = clientId;
    
    const screenDisplay = document.getElementById('screenDisplay');
    
    // Remove any existing listeners first to avoid duplicates
    if (controlEventListenersAttached) {
        console.log('Removing existing listeners before re-attaching');
        disableControlModeListeners();
    }
    
    // Add event listeners for mouse and keyboard
    console.log('Attaching event listeners...');
    screenDisplay.addEventListener('mousemove', handleMouseMove, true);
    screenDisplay.addEventListener('mousedown', handleMouseDown, true);
    screenDisplay.addEventListener('mouseup', handleMouseUp, true);
    screenDisplay.addEventListener('click', handleMouseClick, true);
    screenDisplay.addEventListener('contextmenu', handleContextMenu, true);
    screenDisplay.addEventListener('wheel', handleMouseWheel, true);
    
    // Focus on screen to capture keyboard
    screenDisplay.tabIndex = 0;
    screenDisplay.focus();
    screenDisplay.addEventListener('keydown', handleKeyDown, true);
    screenDisplay.addEventListener('keyup', handleKeyUp, true);
    
    controlEventListenersAttached = true;
    
    // Change cursor to indicate control mode
    screenDisplay.style.cursor = 'crosshair';
    
    console.log('Control mode enabled successfully');
    console.log('Event listeners attached:', controlEventListenersAttached);
    updateStatus('Control mode active - Click on screen to control');
    
    // Periodically check if listeners are still attached (every 1 second)
    if (window.controlModeCheckInterval) {
        clearInterval(window.controlModeCheckInterval);
    }
    window.controlModeCheckInterval = setInterval(() => {
        if (controlActive && !controlEventListenersAttached) {
            console.warn('Event listeners were removed! Re-attaching...');
            enableControlMode(controlClientId);
        }
    }, 1000);
}

function disableControlModeListeners() {
    console.log('Removing event listeners...');
    const screenDisplay = document.getElementById('screenDisplay');
    
    // Remove event listeners
    screenDisplay.removeEventListener('mousemove', handleMouseMove, true);
    screenDisplay.removeEventListener('mousedown', handleMouseDown, true);
    screenDisplay.removeEventListener('mouseup', handleMouseUp, true);
    screenDisplay.removeEventListener('click', handleMouseClick, true);
    screenDisplay.removeEventListener('contextmenu', handleContextMenu, true);
    screenDisplay.removeEventListener('wheel', handleMouseWheel, true);
    screenDisplay.removeEventListener('keydown', handleKeyDown, true);
    screenDisplay.removeEventListener('keyup', handleKeyUp, true);
    
    controlEventListenersAttached = false;
}

function disableControlMode() {
    console.log('=== DISABLING CONTROL MODE ===');
    
    controlActive = false;
    const wasControlling = controlClientId;
    controlClientId = null;
    
    // Stop the check interval
    if (window.controlModeCheckInterval) {
        clearInterval(window.controlModeCheckInterval);
        window.controlModeCheckInterval = null;
    }
    
    disableControlModeListeners();
    
    const screenDisplay = document.getElementById('screenDisplay');
    
    // Reset cursor
    screenDisplay.style.cursor = 'default';
    
    console.log('Control mode disabled');
    if (wasControlling) {
        updateStatus('Control mode deactivated');
    }
}

function getScaledCoordinates(event) {
    const img = document.getElementById('screenDisplay');
    const rect = img.getBoundingClientRect();
    
    // Get click position relative to image
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;
    
    // Check if mouse is outside image bounds - return null to skip
    if (x < 0 || y < 0 || x > rect.width || y > rect.height) {
        console.debug('Mouse outside image bounds, skipping');
        return null;
    }
    
    // Validate image dimensions
    if (!img.naturalWidth || !img.naturalHeight || !rect.width || !rect.height) {
        console.warn('Image dimensions not available, skipping');
        return null;
    }
    
    // Scale to actual image dimensions
    const scaleX = img.naturalWidth / rect.width;
    const scaleY = img.naturalHeight / rect.height;
    
    // Validate scaling factors
    if (!isFinite(scaleX) || !isFinite(scaleY) || scaleX <= 0 || scaleY <= 0) {
        console.warn('Invalid scaling factors, skipping');
        return null;
    }
    
    const scaledX = Math.round(x * scaleX);
    const scaledY = Math.round(y * scaleY);
    
    // Final validation - ensure coordinates are valid
    if (scaledX < 0 || scaledY < 0 || !isFinite(scaledX) || !isFinite(scaledY)) {
        console.warn('Invalid scaled coordinates, skipping');
        return null;
    }
    
    // Clamp to valid range
    return {
        x: Math.max(0, Math.min(scaledX, img.naturalWidth - 1)),
        y: Math.max(0, Math.min(scaledY, img.naturalHeight - 1))
    };
}

function sendControlInput(inputData) {
    if (!controlActive || !controlClientId) return;
    
    socket.emit('control_input', {
        client_id: controlClientId,
        input: inputData
    });
}

function handleMouseMove(event) {
    if (!controlActive) {
        console.warn('handleMouseMove called but controlActive is false!');
        return;
    }
    
    const coords = getScaledCoordinates(event);
    
    // Skip if coordinates are invalid (null or negative)
    if (!coords || coords.x < 0 || coords.y < 0) {
        return;
    }
    
    // Only send if mouse moved significantly (reduce network traffic)
    if (Math.abs(coords.x - lastMousePosition.x) > 2 || 
        Math.abs(coords.y - lastMousePosition.y) > 2) {
        lastMousePosition = coords;
        
        sendControlInput({
            type: 'mouse',
            action: 'move',
            x: coords.x,
            y: coords.y
        });
    }
}

function handleMouseDown(event) {
    if (!controlActive) {
        console.warn('handleMouseDown called but controlActive is false!');
        return;
    }
    event.preventDefault();
    event.stopPropagation();
    
    console.log('Mouse down:', event.button);
    
    const coords = getScaledCoordinates(event);
    if (!coords) return;  // Skip if invalid
    
    sendControlInput({
        type: 'mouse',
        action: 'press',
        x: coords.x,
        y: coords.y,
        button: event.button + 1  // Convert to 1-based (1=left, 2=middle, 3=right)
    });
}

function handleMouseUp(event) {
    if (!controlActive) {
        console.warn('handleMouseUp called but controlActive is false!');
        return;
    }
    event.preventDefault();
    event.stopPropagation();
    
    console.log('Mouse up:', event.button);
    
    const coords = getScaledCoordinates(event);
    if (!coords) return;  // Skip if invalid
    
    sendControlInput({
        type: 'mouse',
        action: 'release',
        x: coords.x,
        y: coords.y,
        button: event.button + 1
    });
}

function handleMouseClick(event) {
    if (!controlActive) {
        console.warn('handleMouseClick called but controlActive is false!');
        return;
    }
    event.preventDefault();
    event.stopPropagation();
    
    console.log('Mouse click:', event.button);
    
    const coords = getScaledCoordinates(event);
    if (!coords) return;  // Skip if invalid
    
    sendControlInput({
        type: 'mouse',
        action: 'click',
        x: coords.x,
        y: coords.y,
        button: event.button + 1
    });
}

function handleContextMenu(event) {
    if (!controlActive) return;
    event.preventDefault();  // Prevent browser context menu
    event.stopPropagation();
    return false;
}

function handleMouseWheel(event) {
    if (!controlActive) {
        console.warn('handleMouseWheel called but controlActive is false!');
        return;
    }
    event.preventDefault();
    event.stopPropagation();
    
    console.log('Mouse wheel:', event.deltaY);
    
    sendControlInput({
        type: 'mouse',
        action: 'scroll',
        scroll: event.deltaY > 0 ? -1 : 1  // Normalize scroll direction
    });
}

function handleKeyDown(event) {
    if (!controlActive) {
        console.warn('handleKeyDown called but controlActive is false!');
        return;
    }
    event.preventDefault();
    event.stopPropagation();
    
    console.log('Key down:', event.key, event.code);
    
    const key = event.key;
    const keyCode = event.code.toLowerCase().replace('key', '').replace('digit', '');
    
    sendControlInput({
        type: 'key',
        action: 'press',
        key: key,
        key_code: keyCode
    });
}

function handleKeyUp(event) {
    if (!controlActive) {
        console.warn('handleKeyUp called but controlActive is false!');
        return;
    }
    event.preventDefault();
    event.stopPropagation();
    
    console.log('Key up:', event.key, event.code);
    
    const key = event.key;
    const keyCode = event.code.toLowerCase().replace('key', '').replace('digit', '');
    
    sendControlInput({
        type: 'key',
        action: 'release',
        key: key,
        key_code: keyCode
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
    
    // Update display selector based on client's display count
    updateDisplaySelector(client.display_count || 1);
    
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

function updateDisplaySelector(displayCount) {
    const selector = document.getElementById('displaySelect');
    selector.innerHTML = '';
    
    // Add "All Displays" option if multiple displays
    if (displayCount > 1) {
        const allOption = document.createElement('option');
        allOption.value = '0';
        allOption.textContent = `All Displays (${displayCount})`;
        selector.appendChild(allOption);
    }
    
    // Add individual display options
    for (let i = 1; i <= displayCount; i++) {
        const option = document.createElement('option');
        option.value = i.toString();
        option.textContent = `Display ${i}`;
        selector.appendChild(option);
    }
    
    // Set default selection
    if (displayCount > 1) {
        selector.value = '0';  // Default to "All Displays"
    } else {
        selector.value = '1';  // Single display
    }
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
    
    const img = document.getElementById('screenDisplay');
    
    // Check if webcam is active for this client
    if (currentClient && currentClient.webcam_active) {
        // Load webcam frame (webcam is lower FPS, so we poll less frequently)
        img.src = `/api/client/${currentClientId}/webcam_frame?t=${Date.now()}`;
        updateStatus(`Viewing: ${currentClient.name} (Webcam)`);
    } else {
        // Load screen frame
        img.src = `/api/client/${currentClientId}/frame?t=${Date.now()}`;
        updateStatus(`Viewing: ${currentClient ? currentClient.name : 'Unknown'}`);
    }
    
    img.style.display = 'block';
    document.getElementById('noClients').style.display = 'none';
}

function startFrameUpdate() {
    // Clear any existing interval first
    if (frameUpdateInterval) {
        clearTimeout(frameUpdateInterval);
        frameUpdateInterval = null;
    }
    
    // Use adaptive polling based on what's being displayed
    // Screen: 100ms (10 FPS) - reduced from 50ms for lower load
    // Webcam: 125ms (8 FPS) - matches webcam capture rate
    function updateLoop() {
        if (currentClientId) {
            const currentClient = clients.find(c => c.id === currentClientId);
            const isWebcam = currentClient && currentClient.webcam_active;
            const interval = isWebcam ? 125 : 100; // Webcam is slower, screen is faster
            
            loadFrame();
            
            // Schedule next update with appropriate interval
            frameUpdateInterval = setTimeout(updateLoop, interval);
        } else {
            // No client selected, check again in 500ms
            frameUpdateInterval = setTimeout(updateLoop, 500);
        }
    }
    
    updateLoop();
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

socket.on('clients_updated', () => {
    // Reload clients when updated
    loadClients();
    loadDeletedClients();
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
    loadDeletedClients();
});

