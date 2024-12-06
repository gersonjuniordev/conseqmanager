from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.x509.oid import NameOID
from datetime import datetime, timedelta
import hashlib
import json
import base64

class SignatureManager:
    def __init__(self):
        self.private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        
    def generate_certificate(self, signer_data):
        """Gera certificado auto-assinado"""
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, signer_data['name']),
            x509.NameAttribute(NameOID.EMAIL_ADDRESS, signer_data['email']),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Sistema de Assinatura Digital")
        ])

        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            issuer
        ).public_key(
            self.private_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.utcnow()
        ).not_valid_after(
            datetime.utcnow() + timedelta(days=365)
        ).sign(self.private_key, hashes.SHA256())

        return cert

    def sign_document(self, pdf_content, signer_data):
        """Assina o documento e gera evidências"""
        # Gera hash do documento
        doc_hash = hashlib.sha256(pdf_content).hexdigest()
        
        # Gera assinatura digital
        signature = self.private_key.sign(
            pdf_content,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        
        # Gera certificado
        certificate = self.generate_certificate(signer_data)
        
        return {
            'hash': doc_hash,
            'signature': base64.b64encode(signature).decode('utf-8'),
            'certificate': base64.b64encode(
                certificate.public_bytes(serialization.Encoding.PEM)
            ).decode('utf-8')
        } 