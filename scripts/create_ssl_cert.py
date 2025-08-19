#!/usr/bin/env python3
"""
Create a self-signed SSL certificate for local HTTPS testing.
This enables camera access on mobile browsers.
"""

import os
import ssl
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
import datetime
import ipaddress

def create_self_signed_cert(cert_dir="certs"):
    """Create self-signed SSL certificate for local development."""
    
    # Create certs directory
    os.makedirs(cert_dir, exist_ok=True)
    
    # Generate private key
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    
    # Get local IP
    import socket
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    
    # Create certificate
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, u"US"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, u"CA"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, u"Local"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"WebRTC Demo"),
        x509.NameAttribute(NameOID.COMMON_NAME, local_ip),
    ])
    
    cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        issuer
    ).public_key(
        private_key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.datetime.utcnow()
    ).not_valid_after(
        datetime.datetime.utcnow() + datetime.timedelta(days=365)
    ).add_extension(
        x509.SubjectAlternativeName([
            x509.DNSName(u"localhost"),
            x509.DNSName(hostname),
            x509.IPAddress(ipaddress.ip_address(local_ip)),
            x509.IPAddress(ipaddress.ip_address("127.0.0.1")),
        ]),
        critical=False,
    ).sign(private_key, hashes.SHA256())
    
    # Write private key
    key_path = os.path.join(cert_dir, "key.pem")
    with open(key_path, "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ))
    
    # Write certificate
    cert_path = os.path.join(cert_dir, "cert.pem")
    with open(cert_path, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))
    
    print(f"✅ SSL certificate created!")
    print(f"📁 Certificate: {cert_path}")
    print(f"🔑 Private key: {key_path}")
    print(f"🌐 Server IP: {local_ip}")
    print(f"🔒 HTTPS URL: https://{local_ip}:8443")
    print(f"⚠️  You'll need to accept the security warning in your browser")
    
    return cert_path, key_path, local_ip

if __name__ == "__main__":
    create_self_signed_cert()
