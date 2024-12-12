from flask import Blueprint, render_template, request, jsonify, send_file, url_for, current_app, redirect, flash, session, make_response, abort
from werkzeug.utils import secure_filename
from app.models import Document, User, CompanyUser, Company
from app import db
from app.utils import generate_qr_code, save_signature_on_pdf
import os
from datetime import datetime
from functools import wraps
from app.signature_manager import SignatureManager
import json
from app.signature_validator import SignatureValidator

main = Blueprint('main', __name__)

ALLOWED_EXTENSIONS = {'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or 'user_type' not in session:
            return redirect(url_for('main.login'))
            
        if session['user_type'] == 'admin':
            user = User.query.get(session['user_id'])
        else:
            user = CompanyUser.query.get(session['user_id'])
            
        if not user or (session['user_type'] == 'company' and not user.active):
            session.clear()
            return redirect(url_for('main.login'))
            
        return f(*args, **kwargs)
    return decorated_function

@main.route('/')
def index():
    return render_template('index.html')

@main.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Primeiro tenta login como admin
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['user_type'] = 'admin'
            return redirect(url_for('main.upload'))
            
        # Se não for admin, tenta como usuário de empresa
        company_user = CompanyUser.query.filter_by(username=username).first()
        if company_user and company_user.check_password(password):
            if not company_user.active:
                flash('Usuário inativo', 'error')
                return render_template('login.html')
                
            company = Company.query.get(company_user.company_id)
            if not company or not company.active:
                flash('Empresa inativa', 'error')
                return render_template('login.html')
                
            session['user_id'] = company_user.id
            session['user_type'] = 'company'
            session['company_id'] = company.id
            return redirect(url_for('main.upload'))
            
        flash('Usuário ou senha inválidos')
    return render_template('login.html')

@main.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('main.index'))

@main.route('/upload')
@login_required
def upload():
    if session['user_type'] == 'company':
        documents = Document.query.filter_by(company_id=session['company_id']).order_by(Document.created_at.desc()).all()
    else:
        documents = Document.query.order_by(Document.created_at.desc()).all()
    return render_template('upload.html', documents=documents)

@main.route('/upload', methods=['POST'])
@login_required
def upload_file():
    if 'pdf' not in request.files:
        return jsonify({'error': 'Nenhum arquivo enviado'}), 400
        
    file = request.files['pdf']
    if file.filename == '':
        return jsonify({'error': 'Nenhum arquivo selecionado'}), 400
        
    if not allowed_file(file.filename):
        return jsonify({'error': 'Tipo de arquivo não permitido'}), 400
        
    try:
        filename = secure_filename(file.filename)
        unique_filename = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{filename}"
        
        # Definir company_id e pasta de upload baseado no tipo de usuário
        if session['user_type'] == 'admin':
            company_id = None
            upload_folder = current_app.config['ADMIN_UPLOADS']
        else:
            company_id = session['company_id']
            upload_folder = os.path.join(current_app.config['COMPANY_UPLOADS'], 
                                       str(company_id))
            
        # Criar pasta se não existir
        os.makedirs(upload_folder, exist_ok=True)
        
        # Salvar arquivo
        file_path = os.path.join(upload_folder, unique_filename)
        file.save(file_path)
        
        document = Document(
            filename=unique_filename,
            original_filename=filename,
            company_id=company_id
        )
        
        db.session.add(document)
        db.session.commit()

        # Gerar QR code e URL de assinatura
        sign_url = url_for('main.sign_document', doc_id=document.id, _external=True)
        qr_code = generate_qr_code(sign_url)
        
        return jsonify({
            'success': True,
            'message': 'Arquivo enviado com sucesso',
            'qr_code': qr_code,
            'sign_url': sign_url,
            'document': document.to_dict()
        })
        
    except Exception as e:
        print(f"Erro no upload: {str(e)}")
        if os.path.exists(file_path):
            os.remove(file_path)
        db.session.rollback()
        return jsonify({'error': 'Erro ao processar arquivo'}), 500

@main.route('/verify/<doc_id>')
def verify_document(doc_id):
    doc = Document.query.get_or_404(doc_id)
    validator = SignatureValidator(doc)
    result = validator.validate_signature()
    
    if request.headers.get('Accept') == 'application/json':
        return jsonify(result)
        
    return render_template('verify.html', document=doc, validation=result)

@main.route('/history')
@login_required
def document_history():
    if session['user_type'] == 'admin':
        # Admin vê todos os documentos
        documents = Document.query.order_by(Document.created_at.desc()).all()
    else:
        # Usuário da empresa vê apenas seus documentos
        documents = Document.query.filter_by(
            company_id=session['company_id']
        ).order_by(Document.created_at.desc()).all()
    return render_template('history.html', documents=documents)

@main.route('/export/<doc_id>')
@login_required
def export_signature_info(doc_id):
    doc = Document.query.get_or_404(doc_id)
    
    # Verificar se o usuário tem acesso ao documento
    if session['user_type'] == 'company' and doc.company_id != session['company_id']:
        flash('Acesso não autorizado', 'error')
        return redirect(url_for('main.document_history'))
    
    validator = SignatureValidator(doc)
    validation = validator.validate_signature()
    
    if not validation['valid']:
        flash('Documento não possui assinatura válida', 'error')
        return redirect(url_for('main.document_history'))
    
    # Criar arquivo JSON com informações da assinatura
    signature_info = {
        'documento': {
            'nome': doc.original_filename,
            'hash': doc.signature_hash,
            'data_criacao': doc.created_at.isoformat(),
            'data_assinatura': doc.signed_at.isoformat()
        },
        'assinante': validation['data']['assinante'],
        'dispositivo': validation['data']['dispositivo'],
        'timestamp': validation['data']['timestamp'],
        'ip': validation['data']['ip']
    }
    
    response = make_response(json.dumps(signature_info, indent=2, ensure_ascii=False))
    response.headers['Content-Type'] = 'application/json'
    response.headers['Content-Disposition'] = f'attachment; filename=assinatura_{doc.id}.json'
    
    return response

@main.route('/sign/<doc_id>', methods=['GET'])
def sign_document(doc_id):
    document = Document.query.get_or_404(doc_id)
    
    # Detectar se é dispositivo móvel
    user_agent = request.headers.get('User-Agent', '').lower()
    is_mobile = 'mobile' in user_agent or 'android' in user_agent or 'iphone' in user_agent
    
    if is_mobile:
        return render_template('sign_mobile.html', document=document)
    else:
        return render_template('sign.html', document=document)

@main.route('/download/<doc_id>')
@login_required
def download_document(doc_id):
    try:
        document = Document.query.get_or_404(doc_id)
        current_app.logger.info(f"Baixando documento {doc_id}")
        
        # Verificar permissão
        if session['user_type'] != 'admin' and document.company_id != session.get('company_id'):
            current_app.logger.error("Acesso não autorizado")
            abort(403)  # Forbidden
        
        # Determinar caminho do arquivo
        if document.company_id:
            base_folder = os.path.join(current_app.config['COMPANY_UPLOADS'], 
                                     str(document.company_id))
        else:
            base_folder = current_app.config['ADMIN_UPLOADS']
            
        current_app.logger.info(f"Base folder: {base_folder}")
        
        # Se o documento estiver assinado, retorna a versão assinada
        if document.status == 'signed':
            filename = document.filename.replace('.pdf', '_signed.pdf')
        else:
            filename = document.filename
            
        file_path = os.path.join(base_folder, filename)
        current_app.logger.info(f"File path: {file_path}")
        
        if not os.path.exists(file_path):
            current_app.logger.error(f"Arquivo não encontrado: {file_path}")
            abort(404)
            
        return send_file(
            file_path,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=document.original_filename
        )
        
    except Exception as e:
        current_app.logger.error(f"Erro ao baixar documento: {str(e)}")
        abort(500)

@main.route('/view/<doc_id>')
def view_document(doc_id):
    try:
        document = Document.query.get_or_404(doc_id)
        current_app.logger.info(f"Visualizando documento {doc_id}")
        
        # Determinar caminho do arquivo
        if document.company_id:
            base_folder = os.path.join(current_app.config['COMPANY_UPLOADS'], 
                                     str(document.company_id))
        else:
            base_folder = current_app.config['ADMIN_UPLOADS']
            
        current_app.logger.info(f"Base folder: {base_folder}")
        
        # Se o documento estiver assinado, retorna a versão assinada
        if document.status == 'signed':
            filename = document.filename.replace('.pdf', '_signed.pdf')
        else:
            filename = document.filename
            
        file_path = os.path.join(base_folder, filename)
        current_app.logger.info(f"File path: {file_path}")
        
        if not os.path.exists(file_path):
            current_app.logger.error(f"Arquivo não encontrado: {file_path}")
            abort(404)
            
        return send_file(
            file_path,
            mimetype='application/pdf',
            as_attachment=False,
            download_name=document.original_filename
        )
        
    except Exception as e:
        current_app.logger.error(f"Erro ao visualizar documento: {str(e)}")
        abort(500)

@main.route('/remove/<doc_id>', methods=['DELETE'])
@login_required
def remove_document(doc_id):
    try:
        document = Document.query.get_or_404(doc_id)
        
        # Verificar se o usuário tem acesso ao documento
        if session['user_type'] == 'company' and document.company_id != session['company_id']:
            return jsonify({'error': 'Acesso não autorizado'}), 403
            
        # Remover arquivo físico
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], document.filename)
        if os.path.exists(file_path):
            os.remove(file_path)
            
        # Se existir versão assinada, remover também
        signed_path = file_path.replace('.pdf', '_signed.pdf')
        if os.path.exists(signed_path):
            os.remove(signed_path)
            
        # Remover do banco de dados
        db.session.delete(document)
        db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        print(f"Erro ao remover documento: {str(e)}")
        return jsonify({'error': 'Erro ao remover documento'}), 500

@main.route('/sign/<doc_id>', methods=['POST'])
def sign_document_post(doc_id):
    try:
        document = Document.query.get_or_404(doc_id)
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Dados inválidos'}), 400
            
        # Definir a data de assinatura
        document.signed_at = datetime.utcnow()
            
        # Salvar informações do assinante
        document.signer_name = data.get('name')
        document.signer_email = data.get('email')
        document.signer_cpf = data.get('cpf')
        document.signer_phone = data.get('phone')
        document.signature_position_x = data.get('position_x', 0)
        document.signature_position_y = data.get('position_y', 0)
        
        # Informações do dispositivo
        document.signer_device_info = json.dumps({
            'userAgent': request.headers.get('User-Agent'),
            'platform': request.headers.get('Sec-Ch-Ua-Platform'),
            'browser': request.headers.get('Sec-Ch-Ua')
        })
        document.signer_ip = request.remote_addr
        
        # Processar assinatura
        signature_manager = SignatureManager()
        
        # Obter caminho do arquivo baseado na empresa
        if document.company_id:
            file_path = os.path.join(current_app.config['COMPANY_UPLOADS'], 
                                   str(document.company_id), 
                                   document.filename)
        else:
            file_path = os.path.join(current_app.config['ADMIN_UPLOADS'], 
                                   document.filename)
        
        # Verificar se o arquivo existe
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")
        
        # Processar assinatura
        signature_data = signature_manager.sign_document(
            open(file_path, 'rb').read(),
            {
                'name': document.signer_name,
                'email': data.get('email')
            }
        )
        
        # Salvar assinatura no PDF
        output_path = save_signature_on_pdf(
            file_path,
            data.get('signature'),
            data.get('position_x', 0),
            data.get('position_y', 0),
            data.get('scale', 1.0)
        )
        
        # Atualizar documento
        document.status = 'signed'
        document.signature_hash = signature_data['hash']
        document.signature_certificate = signature_data['certificate']
        
        db.session.commit()
        
        return jsonify({'success': True})
        
    except Exception as e:
        print(f"Erro na assinatura: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Erro ao processar assinatura'}), 500

@main.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if session['user_type'] == 'company':
        user = CompanyUser.query.get(session['user_id'])
    else:
        user = User.query.get(session['user_id'])
        
    if request.method == 'POST':
        try:
            # Atualizar informações básicas
            if 'update_info' in request.form:
                user.full_name = request.form['full_name']
                user.phone = request.form['phone']
                user.position = request.form['position']
                user.department = request.form['department']
                user.bio = request.form['bio']
                
                # Processar foto de perfil
                if 'profile_image' in request.files:
                    file = request.files['profile_image']
                    if file and allowed_image_file(file.filename):
                        filename = secure_filename(file.filename)
                        unique_filename = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{filename}"
                        file_path = os.path.join(current_app.config['PROFILE_UPLOADS'], unique_filename)
                        file.save(file_path)
                        
                        # Remover foto antiga se existir
                        if user.profile_image:
                            old_path = os.path.join(current_app.config['PROFILE_UPLOADS'], user.profile_image)
                            if os.path.exists(old_path):
                                os.remove(old_path)
                        
                        user.profile_image = unique_filename
                
                db.session.commit()
                flash('Perfil atualizado com sucesso!', 'success')
                
            # Atualizar email
            elif 'update_email' in request.form:
                new_email = request.form['email']
                if CompanyUser.validate_email(new_email):
                    user.email = new_email
                    db.session.commit()
                    flash('Email atualizado com sucesso!', 'success')
                else:
                    flash('Email inválido!', 'error')
                    
            # Atualizar senha
            elif 'update_password' in request.form:
                if user.check_password(request.form['current_password']):
                    if CompanyUser.validate_password(request.form['new_password']):
                        user.set_password(request.form['new_password'])
                        user.last_password_change = datetime.utcnow()
                        db.session.commit()
                        flash('Senha atualizada com sucesso!', 'success')
                    else:
                        flash('A nova senha não atende aos requisitos mínimos', 'error')
                else:
                    flash('Senha atual incorreta', 'error')
                    
        except Exception as e:
            db.session.rollback()
            flash('Erro ao atualizar perfil', 'error')
            
    return render_template('profile.html', user=user)

@main.errorhandler(404)
def not_found_error(error):
    if request.headers.get('Accept') == 'application/json':
        return jsonify({'error': 'Arquivo não encontrado'}), 404
    flash('Arquivo não encontrado', 'error')
    return redirect(url_for('main.document_history'))

@main.errorhandler(500)
def internal_error(error):
    if request.headers.get('Accept') == 'application/json':
        return jsonify({'error': 'Erro interno do servidor'}), 500
    flash('Erro ao processar sua requisição', 'error')
    return redirect(url_for('main.document_history'))
