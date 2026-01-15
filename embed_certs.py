#!/usr/bin/env python3
"""
Script to embed certificates into client and server files
"""
import base64
from pathlib import Path

def read_and_encode_cert(cert_path):
    """Read certificate file and return base64 encoded string"""
    with open(cert_path, 'rb') as f:
        return base64.b64encode(f.read()).decode('ascii')

def main():
    # Read all certificates
    certs = {
        'CA_CERT': read_and_encode_cert('certs/ca.crt'),
        'SERVER_CERT': read_and_encode_cert('certs/server.crt'),
        'SERVER_KEY': read_and_encode_cert('certs/server.key'),
        'CLIENT_CERT': read_and_encode_cert('certs/client.crt'),
        'CLIENT_KEY': read_and_encode_cert('certs/client.key'),
    }
    
    # Create embedded certificates module
    embedded_certs_code = '''"""
Embedded SSL/TLS Certificates
Auto-generated - do not edit manually
"""
import base64
import ssl
import tempfile
from pathlib import Path

# Embedded certificates (base64 encoded)
_CA_CERT_B64 = """{}"""

_SERVER_CERT_B64 = """{}"""

_SERVER_KEY_B64 = """{}"""

_CLIENT_CERT_B64 = """{}"""

_CLIENT_KEY_B64 = """{}"""

def _decode_cert(b64_data):
    """Decode base64 certificate data"""
    return base64.b64decode(b64_data)

def get_ca_cert():
    """Get CA certificate bytes"""
    return _decode_cert(_CA_CERT_B64)

def get_server_cert():
    """Get server certificate bytes"""
    return _decode_cert(_SERVER_CERT_B64)

def get_server_key():
    """Get server private key bytes"""
    return _decode_cert(_SERVER_KEY_B64)

def get_client_cert():
    """Get client certificate bytes"""
    return _decode_cert(_CLIENT_CERT_B64)

def get_client_key():
    """Get client private key bytes"""
    return _decode_cert(_CLIENT_KEY_B64)

def create_temp_cert_file(cert_data, suffix='.pem'):
    """Create a temporary file with certificate data"""
    temp_file = tempfile.NamedTemporaryFile(mode='wb', suffix=suffix, delete=False)
    temp_file.write(cert_data)
    temp_file.close()
    return temp_file.name

def create_ssl_context_server():
    """Create SSL context for server using embedded certificates"""
    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    
    # Create temporary files for certificates
    server_cert_file = create_temp_cert_file(get_server_cert(), '.crt')
    server_key_file = create_temp_cert_file(get_server_key(), '.key')
    ca_cert_file = create_temp_cert_file(get_ca_cert(), '.crt')
    
    try:
        context.load_cert_chain(server_cert_file, server_key_file)
        context.load_verify_locations(ca_cert_file)
        context.verify_mode = ssl.CERT_OPTIONAL
    finally:
        # Clean up temp files
        Path(server_cert_file).unlink(missing_ok=True)
        Path(server_key_file).unlink(missing_ok=True)
        Path(ca_cert_file).unlink(missing_ok=True)
    
    return context

def create_ssl_context_client():
    """Create SSL context for client using embedded certificates"""
    context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    
    # Create temporary files for certificates
    client_cert_file = create_temp_cert_file(get_client_cert(), '.crt')
    client_key_file = create_temp_cert_file(get_client_key(), '.key')
    ca_cert_file = create_temp_cert_file(get_ca_cert(), '.crt')
    
    try:
        context.load_cert_chain(client_cert_file, client_key_file)
        context.load_verify_locations(ca_cert_file)
    finally:
        # Clean up temp files
        Path(client_cert_file).unlink(missing_ok=True)
        Path(client_key_file).unlink(missing_ok=True)
        Path(ca_cert_file).unlink(missing_ok=True)
    
    return context
'''.format(
        certs['CA_CERT'],
        certs['SERVER_CERT'],
        certs['SERVER_KEY'],
        certs['CLIENT_CERT'],
        certs['CLIENT_KEY']
    )
    
    # Write embedded certificates module
    with open('common/embedded_certs.py', 'w') as f:
        f.write(embedded_certs_code)
    
    print("✓ Created common/embedded_certs.py with embedded certificates")
    print("\nNext steps:")
    print("1. Update client/client.py to use embedded certificates")
    print("2. Update server/server.py to use embedded certificates")

if __name__ == '__main__':
    main()
