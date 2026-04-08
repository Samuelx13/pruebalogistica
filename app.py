from flask import Flask, redirect, url_for
from flask_login import LoginManager, current_user
from config import Config
from models import db
from models.user import User
import os


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Crear carpeta de uploads si no existe
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Inicializar extensiones
    db.init_app(app)

    # Configurar Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Por favor inicie sesión para acceder a esta página.'
    login_manager.login_message_category = 'warning'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Registrar Blueprints
    from routes.auth import auth_bp
    from routes.admin import admin_bp
    from routes.conductor import conductor_bp
    from routes.cliente import cliente_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(conductor_bp)
    app.register_blueprint(cliente_bp)

    # Ruta raíz
    @app.route('/')
    def index():
        if current_user.is_authenticated:
            if current_user.role == 'admin':
                return redirect(url_for('admin.dashboard'))
            elif current_user.role == 'conductor':
                return redirect(url_for('conductor.dashboard'))
            elif current_user.role == 'cliente':
                return redirect(url_for('cliente.tracking'))
        return redirect(url_for('auth.login'))

    # Crear tablas de la base de datos
    with app.app_context():
        db.create_all()

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)
