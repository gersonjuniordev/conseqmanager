from app import db
from datetime import datetime
import uuid
from werkzeug.security import generate_password_hash, check_password_hash
import os
import re
from validate_docbr import CNPJ
from email_validator import validate_email, EmailNotValidError

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    is_admin = db.Column(db.Boolean, default=False)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Company(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    cnpj = db.Column(db.String(14), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    active = db.Column(db.Boolean, default=True)
    database_name = db.Column(db.String(100), unique=True, nullable=False)
    
    users = db.relationship('CompanyUser', backref='company', lazy=True)
    documents = db.relationship('Document', backref='company', lazy=True)

    @staticmethod
    def validate_cnpj(cnpj):
        """Valida o CNPJ usando a biblioteca validate_docbr"""
        validator = CNPJ()
        # Remove caracteres não numéricos
        cnpj = re.sub(r'[^0-9]', '', cnpj)
        return validator.validate(cnpj)

    @staticmethod
    def format_cnpj(cnpj):
        """Formata o CNPJ para XX.XXX.XXX/XXXX-XX"""
        cnpj = re.sub(r'[^0-9]', '', cnpj)
        return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}"

    def __init__(self, **kwargs):
        if 'cnpj' in kwargs:
            if not self.validate_cnpj(kwargs['cnpj']):
                raise ValueError('CNPJ inválido')
            kwargs['cnpj'] = re.sub(r'[^0-9]', '', kwargs['cnpj'])
        super(Company, self).__init__(**kwargs)

class CompanyUser(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False)
    password_hash = db.Column(db.String(128))
    email = db.Column(db.String(120), nullable=False)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Novos campos para perfil
    full_name = db.Column(db.String(100))
    profile_image = db.Column(db.String(255))  # Caminho da imagem
    phone = db.Column(db.String(20))
    position = db.Column(db.String(50))  # Cargo
    department = db.Column(db.String(50))  # Departamento
    bio = db.Column(db.Text)
    last_password_change = db.Column(db.DateTime, default=datetime.utcnow)
    
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    
    @staticmethod
    def validate_email(email):
        """Valida o email usando email-validator"""
        try:
            validate_email(email)
            return True
        except EmailNotValidError:
            return False

    @staticmethod
    def validate_username(username):
        """Valida o nome de usuário"""
        # Apenas letras, números e underscore, 3-30 caracteres
        return bool(re.match(r'^[a-zA-Z0-9_]{3,30}$', username))

    @staticmethod
    def validate_password(password):
        """Valida a senha"""
        # Pelo menos 8 caracteres, uma letra maiúscula, uma minúscula e um número
        if len(password) < 8:
            return False
        if not re.search(r'[A-Z]', password):
            return False
        if not re.search(r'[a-z]', password):
            return False
        if not re.search(r'[0-9]', password):
            return False
        return True

    def __init__(self, **kwargs):
        if 'email' in kwargs:
            if not self.validate_email(kwargs['email']):
                raise ValueError('Email inválido')
        if 'username' in kwargs:
            if not self.validate_username(kwargs['username']):
                raise ValueError('Nome de usuário inválido')
        super(CompanyUser, self).__init__(**kwargs)

    def set_password(self, password):
        if not self.validate_password(password):
            raise ValueError('Senha não atende aos requisitos mínimos')
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Document(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(50), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    signed_at = db.Column(db.DateTime)
    signature_hash = db.Column(db.Text)
    signature_certificate = db.Column(db.Text)
    signature_timestamp = db.Column(db.DateTime)
    signer_ip = db.Column(db.String(50))
    signer_device_info = db.Column(db.Text)
    signer_cpf = db.Column(db.String(14))
    signer_phone = db.Column(db.String(20))
    signature_position_x = db.Column(db.Float)
    signature_position_y = db.Column(db.Float)
    signer_name = db.Column(db.String(255))
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=True)
    
    def get_upload_path(self):
        """Retorna o caminho do arquivo baseado na empresa"""
        return os.path.join('companies', str(self.company_id), self.filename)
    
    def get_signed_path(self):
        """Retorna o caminho do arquivo assinado"""
        return os.path.join('companies', str(self.company_id), 
                          self.filename.replace('.pdf', '_signed.pdf'))
    
    def to_dict(self):
        return {
            'id': self.id,
            'filename': self.filename,
            'original_filename': self.original_filename,
            'signer_phone': self.signer_phone,
            'status': self.status,
            'created_at': self.created_at.isoformat(),
            'signed_at': self.signed_at.isoformat() if self.signed_at else None
        }
