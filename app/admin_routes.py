from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from app import db
from app.models import User, Company, CompanyUser
from functools import wraps
from flask import session
import os
import sqlite3
import re
from datetime import datetime

admin = Blueprint('admin', __name__)

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('main.login'))
        
        user = User.query.get(session['user_id'])
        if not user or not user.is_admin:
            flash('Acesso não autorizado', 'error')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

@admin.route('/admin/companies')
@admin_required
def list_companies():
    companies = Company.query.all()
    return render_template('admin/companies.html', companies=companies)

@admin.route('/admin/companies/new', methods=['GET', 'POST'])
@admin_required
def new_company():
    if request.method == 'POST':
        name = request.form['name']
        cnpj = request.form['cnpj']
        
        try:
            # Validar CNPJ
            if not Company.validate_cnpj(cnpj):
                flash('CNPJ inválido', 'error')
                return render_template('admin/company_form.html')

            # Criar nome único para o banco de dados
            database_name = f"company_{re.sub(r'[^0-9]', '', cnpj)}"
            
            company = Company(
                name=name,
                cnpj=cnpj,
                database_name=database_name
            )
            
            db.session.add(company)
            db.session.commit()
            flash('Empresa criada com sucesso!', 'success')
            return redirect(url_for('admin.list_companies'))
            
        except ValueError as e:
            flash(str(e), 'error')
        except Exception as e:
            db.session.rollback()
            flash('Erro ao criar empresa. Verifique se o CNPJ já está cadastrado.', 'error')
    
    return render_template('admin/company_form.html')

@admin.route('/admin/companies/<int:id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_company(id):
    company = Company.query.get_or_404(id)
    
    if request.method == 'POST':
        company.name = request.form['name']
        company.active = 'active' in request.form
        
        try:
            db.session.commit()
            flash('Empresa atualizada com sucesso!', 'success')
            return redirect(url_for('admin.list_companies'))
        except:
            db.session.rollback()
            flash('Erro ao atualizar empresa', 'error')
    
    return render_template('admin/company_form.html', company=company)

@admin.route('/admin/companies/<int:id>/delete', methods=['POST'])
@admin_required
def delete_company(id):
    company = Company.query.get_or_404(id)
    
    try:
        # Desativar a empresa ao invés de deletar
        company.active = False
        db.session.commit()
        flash('Empresa desativada com sucesso!', 'success')
    except:
        db.session.rollback()
        flash('Erro ao desativar empresa', 'error')
    
    return redirect(url_for('admin.list_companies'))

@admin.route('/admin/companies/<int:company_id>/users')
@admin_required
def list_company_users(company_id):
    company = Company.query.get_or_404(company_id)
    users = CompanyUser.query.filter_by(company_id=company_id).all()
    return render_template('admin/company_users.html', company=company, users=users)

@admin.route('/admin/companies/<int:company_id>/users/new', methods=['GET', 'POST'])
@admin_required
def new_company_user(company_id):
    company = Company.query.get_or_404(company_id)
    
    if request.method == 'POST':
        try:
            user = CompanyUser(
                username=request.form['username'],
                email=request.form['email'],
                company_id=company_id
            )
            
            # Validar senha
            if not CompanyUser.validate_password(request.form['password']):
                flash('A senha deve ter pelo menos 8 caracteres, uma letra maiúscula, uma minúscula e um número', 'error')
                return render_template('admin/company_user_form.html', company=company)
                
            user.set_password(request.form['password'])
            
            db.session.add(user)
            db.session.commit()
            flash('Usuário criado com sucesso!', 'success')
            return redirect(url_for('admin.list_company_users', company_id=company_id))
            
        except ValueError as e:
            flash(str(e), 'error')
        except Exception as e:
            db.session.rollback()
            flash('Erro ao criar usuário', 'error')
    
    return render_template('admin/company_user_form.html', company=company)

@admin.route('/admin/companies/<int:company_id>/users/<int:id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_company_user(company_id, id):
    company = Company.query.get_or_404(company_id)
    user = CompanyUser.query.get_or_404(id)
    
    if request.method == 'POST':
        user.username = request.form['username']
        user.email = request.form['email']
        user.active = 'active' in request.form
        
        if request.form.get('password'):
            user.set_password(request.form['password'])
        
        try:
            db.session.commit()
            flash('Usuário atualizado com sucesso!', 'success')
            return redirect(url_for('admin.list_company_users', company_id=company_id))
        except:
            db.session.rollback()
            flash('Erro ao atualizar usuário', 'error')
    
    return render_template('admin/company_user_form.html', company=company, user=user)

@admin.route('/admin/companies/<int:company_id>/users/<int:id>/delete', methods=['POST'])
@admin_required
def delete_company_user(company_id, id):
    try:
        user = CompanyUser.query.get_or_404(id)
        
        if user.company_id != company_id:
            flash('Usuário não pertence a esta empresa', 'error')
            return redirect(url_for('admin.list_company_users', company_id=company_id))
        
        # Não permitir remover o último usuário ativo
        active_users = CompanyUser.query.filter_by(company_id=company_id, active=True).count()
        if active_users <= 1 and user.active:
            flash('Não é possível remover o último usuário ativo da empresa', 'error')
            return redirect(url_for('admin.list_company_users', company_id=company_id))
        
        # Ao invés de deletar, apenas desativa o usuário
        user.active = False
        db.session.commit()
        
        flash('Usuário desativado com sucesso', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao remover usuário: {str(e)}', 'error')
        
    return redirect(url_for('admin.list_company_users', company_id=company_id))

@admin.route('/admin/companies/<int:company_id>/users/<int:id>/password', methods=['POST'])
@admin_required
def reset_company_user_password(company_id, id):
    user = CompanyUser.query.get_or_404(id)
    
    if user.company_id != company_id:
        flash('Usuário não pertence a esta empresa', 'error')
        return redirect(url_for('admin.list_company_users', company_id=company_id))
        
    try:
        new_password = request.form['new_password']
        if CompanyUser.validate_password(new_password):
            user.set_password(new_password)
            user.last_password_change = datetime.utcnow()
            db.session.commit()
            flash('Senha alterada com sucesso!', 'success')
        else:
            flash('A senha não atende aos requisitos mínimos', 'error')
    except Exception as e:
        db.session.rollback()
        flash('Erro ao alterar senha', 'error')
        
    return redirect(url_for('admin.edit_company_user', company_id=company_id, id=id)) 