from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.x509 import load_pem_x509_certificate
import base64
import json
from datetime import datetime
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from cryptography.x509 import load_pem_x509_certificate

class SignatureValidator:
    def __init__(self, document):
        self.document = document
        
    def validate_signature(self) -> dict:
        try:
            if not self.document.signature_certificate:
                return {
                    "valid": False,
                    "reason": "Documento não possui certificado digital"
                }
                
            if not self.document.signed_at:
                return {
                    "valid": False,
                    "reason": "Documento não possui data de assinatura"
                }
                
            # Carregar certificado
            cert_data = base64.b64decode(self.document.signature_certificate)
            if not cert_data:
                return {
                    "valid": False,
                    "reason": "Certificado digital inválido"
                }
                
            certificate = load_pem_x509_certificate(cert_data)
            
            # Validar período do certificado
            now = datetime.utcnow()
            if now < certificate.not_valid_before or now > certificate.not_valid_after:
                return {
                    "valid": False,
                    "reason": "Certificado expirado ou ainda não válido"
                }
            
            # Verificar dados do assinante
            subject = certificate.subject
            validation_data = {
                "assinante": {
                    "nome": subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value,
                    "email": subject.get_attributes_for_oid(NameOID.EMAIL_ADDRESS)[0].value,
                    "cpf": self.document.signer_cpf
                },
                "timestamp": self.document.signed_at.isoformat() if self.document.signed_at else None,
                "ip": self.document.signer_ip,
                "dispositivo": json.loads(self.document.signer_device_info) if self.document.signer_device_info else {}
            }
            
            return {
                "valid": True,
                "data": validation_data
            }
            
        except Exception as e:
            print("Erro na validação:", str(e))  # Debug
            return {
                "valid": False,
                "reason": f"Erro na validação: {str(e)}"
            } 