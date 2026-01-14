"""
Generate self-signed certificates for TLS communication
"""
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from datetime import datetime, timedelta
import sys
import ipaddress
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import CERTS_DIR, SERVER_CERT, SERVER_KEY, CLIENT_CERT, CLIENT_KEY, CA_CERT

def generate_certificates():
    """Generate CA, server, and client certificates"""
    
    # Generate private keys
    ca_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    server_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    client_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    
    # CA Certificate
    ca_subject = ca_issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "State"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, "City"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Remote Desktop Viewer"),
        x509.NameAttribute(NameOID.COMMON_NAME, "Remote Desktop Viewer CA"),
    ])
    
    ca_cert = x509.CertificateBuilder().subject_name(
        ca_subject
    ).issuer_name(
        ca_issuer
    ).public_key(
        ca_key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.utcnow()
    ).not_valid_after(
        datetime.utcnow() + timedelta(days=365)
    ).add_extension(
        x509.BasicConstraints(ca=True, path_length=None), critical=True
    ).sign(ca_key, hashes.SHA256())
    
    # Server Certificate
    server_subject = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "State"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, "City"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Remote Desktop Viewer"),
        x509.NameAttribute(NameOID.COMMON_NAME, "Remote Desktop Viewer Server"),
    ])
    
    server_cert = x509.CertificateBuilder().subject_name(
        server_subject
    ).issuer_name(
        ca_issuer
    ).public_key(
        server_key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.utcnow()
    ).not_valid_after(
        datetime.utcnow() + timedelta(days=365)
    ).add_extension(
        x509.SubjectAlternativeName([
            x509.DNSName("localhost"),
            x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
        ]),
        critical=False,
    ).sign(ca_key, hashes.SHA256())
    
    # Client Certificate
    client_subject = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "State"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, "City"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Remote Desktop Viewer"),
        x509.NameAttribute(NameOID.COMMON_NAME, "Remote Desktop Viewer Client"),
    ])
    
    client_cert = x509.CertificateBuilder().subject_name(
        client_subject
    ).issuer_name(
        ca_issuer
    ).public_key(
        client_key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.utcnow()
    ).not_valid_after(
        datetime.utcnow() + timedelta(days=365)
    ).sign(ca_key, hashes.SHA256())
    
    # Write CA certificate
    with open(CA_CERT, "wb") as f:
        f.write(ca_cert.public_bytes(serialization.Encoding.PEM))
    
    # Write server certificate and key
    with open(SERVER_CERT, "wb") as f:
        f.write(server_cert.public_bytes(serialization.Encoding.PEM))
    
    with open(SERVER_KEY, "wb") as f:
        f.write(server_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ))
    
    # Write client certificate and key
    with open(CLIENT_CERT, "wb") as f:
        f.write(client_cert.public_bytes(serialization.Encoding.PEM))
    
    with open(CLIENT_KEY, "wb") as f:
        f.write(client_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ))
    
    print("Certificates generated successfully!")
    print(f"CA Certificate: {CA_CERT}")
    print(f"Server Certificate: {SERVER_CERT}")
    print(f"Client Certificate: {CLIENT_CERT}")

if __name__ == "__main__":
    generate_certificates()
