from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from models import db
from models.user import User

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect_by_role(current_user.role)

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not username or not password:
            flash('Por favor ingrese usuario y contraseña.', 'warning')
            return render_template('login.html')

        user = User.query.filter(
            (User.username == username) | (User.email == username)
        ).first()

        if user and user.check_password(password):
            if not user.is_active_user:
                flash('Su cuenta está desactivada. Contacte al administrador.', 'danger')
                return render_template('login.html')

            login_user(user)
            flash(f'Bienvenido, {user.get_full_name()}!', 'success')
            
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect_by_role(user.role)
        else:
            flash('Usuario o contraseña incorrectos.', 'danger')

    return render_template('login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect_by_role(current_user.role)

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        phone = request.form.get('phone', '').strip()
        cedula = request.form.get('cedula', '').strip().upper()

        import re

        # Validaciones
        errors = []
        if not username or len(username) < 3:
            errors.append('El nombre de usuario debe tener al menos 3 caracteres.')
        if not email or '@' not in email:
            errors.append('Ingrese un correo electrónico válido.')
        if not password or len(password) < 6:
            errors.append('La contraseña debe tener al menos 6 caracteres.')
        if password != confirm_password:
            errors.append('Las contraseñas no coinciden.')
        if not first_name:
            errors.append('El nombre es obligatorio.')
        if not last_name:
            errors.append('El apellido es obligatorio.')
        if not cedula or not re.match(r'^[V|E]G?-\d{7,8}$', cedula):
            errors.append('Cédula inválida. Formato: V-12345678 o E-1234567.')
        if User.query.filter_by(cedula=cedula).first():
            errors.append('Esta cédula ya está registrada.')
        
        # Validar dirección principal
        principal_address = request.form.get('principal_address', '').strip()
        principal_lat = request.form.get('principal_lat', type=float)
        principal_lng = request.form.get('principal_lng', type=float)
        if not principal_address or not principal_lat or not principal_lng:
            errors.append('Debe seleccionar su ubicación exacta en el mapa.')

        if User.query.filter_by(username=username).first():
            errors.append('El nombre de usuario ya está en uso.')
        if User.query.filter_by(email=email).first():
            errors.append('El correo electrónico ya está registrado.')

        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('register.html')

        # Crear usuario (por defecto como cliente)
        user = User(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            cedula=cedula,
            principal_address=request.form.get('principal_address', '').strip(),
            principal_lat=request.form.get('principal_lat', type=float),
            principal_lng=request.form.get('principal_lng', type=float),
            role='cliente'
        )
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        flash('Registro exitoso. Ahora puede iniciar sesión.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('register.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Sesión cerrada exitosamente.', 'info')
    return redirect(url_for('auth.login'))


def redirect_by_role(role):
    """Redirige al usuario según su rol."""
    if role == 'admin':
        return redirect(url_for('admin.dashboard'))
    elif role == 'conductor':
        return redirect(url_for('conductor.dashboard'))
    elif role == 'cliente':
        return redirect(url_for('cliente.tracking'))
    else:
        return redirect(url_for('auth.login'))
