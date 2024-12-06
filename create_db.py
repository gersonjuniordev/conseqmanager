from app import create_app, db
import os

def recreate_database():
    app = create_app()
    
    # Criar pasta instance se não existir
    instance_path = os.path.join(os.path.dirname(__file__), 'instance')
    if not os.path.exists(instance_path):
        os.makedirs(instance_path)
    
    # Criar pasta uploads com permissões corretas
    uploads_path = os.path.join(instance_path, 'uploads')
    if not os.path.exists(uploads_path):
        os.makedirs(uploads_path, mode=0o777)
        
    # Criar pasta para documentos de empresas
    companies_path = os.path.join(uploads_path, 'companies')
    if not os.path.exists(companies_path):
        os.makedirs(companies_path)
    
    # Criar pasta para documentos do admin
    admin_path = os.path.join(uploads_path, 'admin')
    if not os.path.exists(admin_path):
        os.makedirs(admin_path)
    
    # Criar pasta para fotos de perfil
    profile_path = os.path.join(uploads_path, 'profiles')
    if not os.path.exists(profile_path):
        os.makedirs(profile_path)
    
    # Criar banco de dados
    with app.app_context():
        db.create_all()
        
    print("Estrutura de pastas e banco de dados criados com sucesso!")

if __name__ == '__main__':
    recreate_database() 