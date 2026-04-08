from models import db
from datetime import datetime


class Driver(db.Model):
    __tablename__ = 'drivers'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicles.id'), nullable=True)
    license_number = db.Column(db.String(30), nullable=False)
    license_expiry = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(20), nullable=False, default='disponible')  # disponible, en_ruta, ausente, inactivo
    current_lat = db.Column(db.Float, nullable=True)
    current_lng = db.Column(db.Float, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relaciones
    routes = db.relationship('Route', backref='driver', lazy=True)
    incidents = db.relationship('Incident', backref='driver', lazy=True)

    def get_full_name(self):
        return self.user.get_full_name() if self.user else 'Sin asignar'

    def get_phone(self):
        return self.user.phone if self.user else ''

    def __repr__(self):
        return f'<Driver {self.get_full_name()} - Licencia: {self.license_number}>'
