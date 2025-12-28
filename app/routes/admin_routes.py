from flask import Blueprint, request, redirect, url_for, flash, render_template_string
from flask_login import login_user, logout_user, login_required, current_user
from app.extensions import db, bcrypt
from app.models.user import User

admin_bp = Blueprint('admin_bp', __name__, url_prefix='/admin')

@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        users_ref = db.collection('users').where('email', '==', email).limit(1).stream()
        user_doc = next(users_ref, None)

        if user_doc:
            data = user_doc.to_dict()
            if bcrypt.check_password_hash(data['password_hash'], password):
                user_obj = User(user_doc.id, data['email'], data['full_name'], data['role'])
                login_user(user_obj)
                return redirect(url_for('admin_bp.dashboard'))
        flash("Email atau Password salah!")
    
    return '''
        <form method="post" style="text-align:center; margin-top:100px;">
            <h2>Login Admin MyHeadStyle</h2>
            <input type="email" name="email" placeholder="Email" required><br><br>
            <input type="password" name="password" placeholder="Password" required><br><br>
            <button type="submit">Masuk ke Panel</button>
        </form>
    '''

@admin_bp.route('/dashboard')
@login_required
def dashboard():
    return f"<h1>Halo {current_user.full_name}, Anda masuk sebagai {current_user.role}</h1>" \
           f"<a href='/admin/logout'>Logout</a>"

@admin_bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('admin_bp.login'))