from models import db
from datetime import datetime


class Vehicle(db.Model):
    __tablename__ = 'vehicles'

    id = db.Column(db.Integer, primary_key=True)
    plate_number = db.Column(db.String(20), unique=True, nullable=False)
    brand = db.Column(db.String(50), nullable=False)
    model = db.Column(db.String(50), nullable=False)
    year = db.Column(db.Integer, nullable=True)
    max_weight_kg = db.Column(db.Float, nullable=False, default=1000.0)
    max_volume_m3 = db.Column(db.Float, nullable=False, default=10.0)
    fuel_type = db.Column(db.String(20), nullable=True, default='Gasolina')
    status = db.Column(db.String(20), nullable=False, default='disponible')  # disponible, en_ruta, mantenimiento, inactivo
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relaciones
    drivers = db.relationship('Driver', backref='vehicle', lazy=True)
    routes = db.relationship('Route', backref='vehicle', lazy=True)

    def __repr__(self):
        return f'<Vehicle {self.plate_number} - {self.brand} {self.model}>'
