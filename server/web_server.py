"""
Web-based server interface using Flask and SocketIO
"""
import asyncio
import json
import logging
import threading
import struct
import base64
from pathlib import Path
import sys
from io import BytesIO

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from flask import Flask, render_template, jsonify, send_from_directory, request
    from flask_socketio import SocketIO, emit
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False

from common.protocol import MessageType, ProtocolHandler

logger = logging.getLogger(__name__)

app = Flask(__name__, template_folder='templates', static_folder='static')
app.config['SECRET_KEY'] = 'remote-desktop-viewer-secret-key'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# Global reference to the async server
async_server = None
async_loop = None  # Store reference to the async event loop

# Client state
client_states = {}  # {client_id: {'disabled': bool, 'webcam_active': bool, 'control_active': bool}}


def init_web_server(server_instance, event_loop=None):
    """Initialize web server with async server instance"""
    global async_server, async_loop
    async_server = server_instance
    async_loop = event_loop
    
    # Set up webcam error callback
    def webcam_error_handler(client_id, error_msg):
        """Handle webcam errors from clients"""
        try:
            # Reset webcam state for this client
            if client_id in client_states:
                client_states[client_id]['webcam_active'] = False
                logger.info(f"Reset webcam state for {client_id} due to error")
            
            # Emit error to web clients
            socketio.emit('webcam_error', {
                'client_id': client_id,
                'message': error_msg
            }, namespace='/')
            logger.info(f"Emitted webcam error to web clients: {client_id} - {error_msg}")
        except Exception as e:
            logger.error(f"Error emitting webcam error: {e}")
    
    async_server.webcam_error_callback = webcam_error_handler


@app.route('/')
def index():
    """Serve main page"""
    return render_template('index.html')


@app.route('/api/clients')
def get_clients():
    """Get list of connected clients"""
    if not async_server:
        return jsonify([])
    
    clients = []
    for client_id, client_info in async_server.clients.items():
        # Ensure client has state entry (initialize if missing)
        if client_id not in client_states:
            client_states[client_id] = {'disabled': False, 'webcam_active': False, 'control_active': False}
        
        state = client_states[client_id]
        clients.append({
            'id': client_id,
            'name': client_info.get('pc_name', client_id),
            'disabled': state.get('disabled', False),
            'webcam_active': state.get('webcam_active', False),
            'control_active': state.get('control_active', False),
            'display_count': client_info.get('display_count', 1)
        })
    return jsonify(clients)


@app.route('/api/client/<client_id>/disable', methods=['POST'])
def toggle_disable(client_id):
    """Toggle disable state for a client"""
    if client_id not in client_states:
        client_states[client_id] = {'disabled': False, 'webcam_active': False, 'control_active': False}
    
    client_states[client_id]['disabled'] = not client_states[client_id].get('disabled', False)
    return jsonify({'disabled': client_states[client_id]['disabled']})


@app.route('/api/client/<client_id>/webcam', methods=['POST'])
def toggle_webcam(client_id):
    """Start/stop webcam for a client"""
    logger.info(f"Webcam toggle requested for client: {client_id}")
    
    if not async_server or client_id not in async_server.clients:
        logger.warning(f"Client {client_id} not found in async_server.clients")
        return jsonify({'error': 'Client not found'}), 404
    
    state = client_states.get(client_id, {'disabled': False, 'webcam_active': False, 'control_active': False})
    logger.info(f"Current webcam state for {client_id}: {state.get('webcam_active', False)}")
    
    # Send webcam start/stop signal
    try:
        client_info = async_server.clients[client_id]
        writer = client_info.get('writer')
        
        if not writer:
            logger.error(f"No writer found for client {client_id}")
            return jsonify({'error': 'No writer available'}), 500
            
        if writer.is_closing():
            logger.error(f"Writer is closing for client {client_id}")
            return jsonify({'error': 'Connection closing'}), 500
        
        if not state.get('webcam_active', False):
            # Start webcam
            msg_type = int(MessageType.WEBCAM_START)
            msg_bytes = "START".encode('utf-8')
            msg = struct.pack('!BI', msg_type, len(msg_bytes)) + msg_bytes
            action = "start"
        else:
            # Stop webcam
            msg_type = int(MessageType.WEBCAM_STOP)
            msg_bytes = "STOP".encode('utf-8')
            msg = struct.pack('!BI', msg_type, len(msg_bytes)) + msg_bytes
            action = "stop"
        
        logger.info(f"Sending webcam {action} message to {client_id}, msg_type={msg_type}, length={len(msg)}")
        
        # Send message using asyncio.run_coroutine_threadsafe
        async def send_message_async():
            try:
                length_bytes = len(msg).to_bytes(4, 'big')
                writer.write(length_bytes + msg)
                await writer.drain()  # Actually flush the data
                logger.info(f"Webcam {action} message sent and flushed for {client_id}")
                return True
            except Exception as e:
                logger.error(f"Error sending webcam message: {e}")
                import traceback
                logger.error(traceback.format_exc())
                return False
        
        # Schedule the coroutine in the async event loop
        if async_loop and async_loop.is_running():
            future = asyncio.run_coroutine_threadsafe(send_message_async(), async_loop)
            # Wait for result with timeout
            try:
                result = future.result(timeout=2.0)
                if not result:
                    return jsonify({'error': 'Failed to send message'}), 500
            except Exception as e:
                logger.error(f"Error waiting for message send: {e}")
                return jsonify({'error': f'Send timeout: {str(e)}'}), 500
        else:
            logger.error("Async event loop not available or not running")
            return jsonify({'error': 'Server not ready'}), 500
        
        # For STOP action, immediately update state
        if action == "stop":
            state['webcam_active'] = False
            client_states[client_id] = state
            logger.info(f"Updated webcam state for {client_id}: False")
        else:
            # For START action, set to true but it will be reset by error handler if fails
            # The error handler will reset this within ~50ms if webcam is not available
            state['webcam_active'] = True
            client_states[client_id] = state
            logger.info(f"Set webcam state for {client_id}: True (pending confirmation)")
        
    except Exception as e:
        logger.error(f"Error toggling webcam: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500
    
    return jsonify({'webcam_active': state.get('webcam_active', False)})


@app.route('/api/client/<client_id>/control', methods=['POST'])
def toggle_control(client_id):
    """Start/stop control mode for a client"""
    logger.info(f"Control toggle requested for client: {client_id}")
    
    if not async_server or client_id not in async_server.clients:
        logger.warning(f"Client {client_id} not found in async_server.clients")
        return jsonify({'error': 'Client not found'}), 404
    
    # Ensure client has state entry (initialize if missing)
    if client_id not in client_states:
        client_states[client_id] = {'disabled': False, 'webcam_active': False, 'control_active': False}
    
    state = client_states[client_id]
    logger.info(f"Current control state for {client_id}: {state.get('control_active', False)}")
    
    # Send control start/stop signal
    try:
        client_info = async_server.clients[client_id]
        writer = client_info.get('writer')
        
        if not writer:
            logger.error(f"No writer found for client {client_id}")
            return jsonify({'error': 'No writer available'}), 500
            
        if writer.is_closing():
            logger.error(f"Writer is closing for client {client_id}")
            return jsonify({'error': 'Connection closing'}), 500
        
        if not state.get('control_active', False):
            # Start control
            msg = ProtocolHandler.create_control_signal("START")
            action = "start"
        else:
            # Stop control
            msg = ProtocolHandler.create_control_signal("STOP")
            action = "stop"
        
        logger.info(f"Sending control {action} message to {client_id}, length={len(msg)}")
        
        # Send message using asyncio.run_coroutine_threadsafe
        async def send_message_async():
            try:
                length_bytes = len(msg).to_bytes(4, 'big')
                writer.write(length_bytes + msg)
                await writer.drain()
                logger.info(f"Control {action} message sent and flushed for {client_id}")
                return True
            except Exception as e:
                logger.error(f"Error sending control message: {e}")
                import traceback
                logger.error(traceback.format_exc())
                return False
        
        # Schedule the coroutine in the async event loop
        if async_loop and async_loop.is_running():
            future = asyncio.run_coroutine_threadsafe(send_message_async(), async_loop)
            try:
                result = future.result(timeout=2.0)
                if not result:
                    return jsonify({'error': 'Failed to send message'}), 500
            except Exception as e:
                logger.error(f"Error waiting for message send: {e}")
                return jsonify({'error': f'Send timeout: {str(e)}'}), 500
        else:
            logger.error("Async event loop not available or not running")
            return jsonify({'error': 'Server not ready'}), 500
        
        # Toggle the state
        state['control_active'] = not state.get('control_active', False)
        # State is already in client_states dict, so changes are persisted
        logger.info(f"Updated control state for {client_id}: {state['control_active']}")
        
    except Exception as e:
        logger.error(f"Error toggling control: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500
    
    return jsonify({'control_active': state.get('control_active', False)})


@app.route('/api/client/<client_id>/frame')
def get_frame(client_id):
    """Get latest frame from client"""
    if not async_server or client_id not in async_server.frame_buffer:
        from flask import Response
        return Response('', status=404)
    
    frame_info = async_server.frame_buffer.get(client_id)
    if not frame_info:
        from flask import Response
        return Response('', status=404)
    
    frame_data = frame_info.get('frame_data')
    if not frame_data:
        from flask import Response
        return Response('', status=404)
    
    # Return frame as JPEG
    from flask import Response
    return Response(frame_data, mimetype='image/jpeg')


@app.route('/api/client/<client_id>/display', methods=['POST'])
def set_display(client_id):
    """Set display selection for a client"""
    if not async_server or client_id not in async_server.clients:
        return jsonify({'error': 'Client not found'}), 404
    
    try:
        data = json.loads(request.data)
        display_index = data.get('display', 0)
        
        # Send display selection to client
        client_info = async_server.clients[client_id]
        writer = client_info.get('writer')
        
        if writer and not writer.is_closing():
            msg_data = json.dumps({'display': display_index}).encode('utf-8')
            msg = struct.pack('!BI', int(MessageType.DISPLAY_SELECT), len(msg_data)) + msg_data
            
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(_send_to_client(writer, msg))
            else:
                loop.run_until_complete(_send_to_client(writer, msg))
        
        return jsonify({'display': display_index})
    except Exception as e:
        logger.error(f"Error setting display: {e}")
        return jsonify({'error': str(e)}), 500


async def _send_to_client(writer, msg):
    """Helper to send message to client"""
    try:
        length_bytes = len(msg).to_bytes(4, 'big')
        writer.write(length_bytes + msg)
        await writer.drain()
    except Exception as e:
        logger.error(f"Error sending to client: {e}")


@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    logger.info("Web client connected")
    emit('connected', {'status': 'ok'})


@socketio.on('get_clients')
def handle_get_clients():
    """Handle get clients request"""
    clients = []
    if async_server:
        for client_id, client_info in async_server.clients.items():
            state = client_states.get(client_id, {'disabled': False, 'webcam_active': False, 'control_active': False})
            # Include all clients, let frontend filter disabled ones
            clients.append({
                'id': client_id,
                'name': client_info.get('pc_name', client_id),
                'disabled': state.get('disabled', False)
            })
    emit('clients_list', {'clients': clients})


@socketio.on('control_input')
def handle_control_input(data):
    """Handle control input from web client (mouse/keyboard)"""
    try:
        client_id = data.get('client_id')
        input_data = data.get('input')
        
        if not client_id or not input_data:
            logger.warning("Invalid control input data")
            return
        
        if not async_server or client_id not in async_server.clients:
            logger.warning(f"Client {client_id} not found for control input")
            return
        
        # Check if control is active for this client
        state = client_states.get(client_id, {})
        if not state.get('control_active', False):
            logger.warning(f"Control not active for client {client_id}")
            return
        
        # Forward control input to client
        client_info = async_server.clients[client_id]
        writer = client_info.get('writer')
        
        if not writer or writer.is_closing():
            logger.warning(f"No writer available for client {client_id}")
            return
        
        # Create control input message
        import json
        msg_data = json.dumps(input_data).encode('utf-8')
        msg = struct.pack('!BI', int(MessageType.CONTROL_INPUT), len(msg_data)) + msg_data
        
        # Send message using asyncio.run_coroutine_threadsafe
        async def send_control_input():
            try:
                length_bytes = len(msg).to_bytes(4, 'big')
                writer.write(length_bytes + msg)
                await writer.drain()
                return True
            except Exception as e:
                logger.error(f"Error sending control input: {e}")
                return False
        
        # Schedule in async event loop
        if async_loop and async_loop.is_running():
            future = asyncio.run_coroutine_threadsafe(send_control_input(), async_loop)
            try:
                result = future.result(timeout=0.5)
                if not result:
                    logger.error(f"Failed to send control input to {client_id}")
            except Exception as e:
                logger.error(f"Error waiting for control input send: {e}")
        else:
            logger.error("Async event loop not available")
            
    except Exception as e:
        logger.error(f"Error handling control input: {e}")
        import traceback
        logger.error(traceback.format_exc())


def run_web_server(host='0.0.0.0', port=5000):
    """Run the web server"""
    if not FLASK_AVAILABLE:
        logger.error("Flask not available. Install: pip install Flask flask-socketio eventlet")
        return
    
    logger.info(f"Starting web server on {host}:{port}")
    socketio.run(app, host=host, port=port, debug=False)
