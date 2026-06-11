import os

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'clave-secreta-tesis-2026-logistica'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'logistica.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(basedir, 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max upload
    GOOGLE_MAPS_API_KEY = 'AIzaSyC16HuEheZSOlKb2sy4cqIjcXAhXfRdrk8'

    # Coordenadas del almacén/centro de distribución (por defecto)
    WAREHOUSE_LAT = 8.3700  # Puerto Ordaz, Ciudad Guayana
    WAREHOUSE_LNG = -62.6700  # Puerto Ordaz, Ciudad Guayana
    WAREHOUSE_ADDRESS = 'Centro de Distribución Ciudad Guayana, Puerto Ordaz, Bolívar, Venezuela'
