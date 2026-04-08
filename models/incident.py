from models import db
from datetime import datetime


class Incident(db.Model):
    __tablename__ = 'incidents'

    id = db.Column(db.Integer, primary_key=True)
    driver_id = db.Column(db.Integer, db.ForeignKey('drivers.id'), nullable=False)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=True)
    route_id = db.Column(db.Integer, db.ForeignKey('routes.id'), nullable=True)

    # Tipo de incidencia
    incident_type = db.Column(db.String(50), nullable=False)
    # Tipos: trafico, accidente, demora_descarga, vehiculo_averiado, cliente_ausente, otro

    description = db.Column(db.Text, nullable=False)
    duration_minutes = db.Column(db.Integer, nullable=True, default=0)

    # Ubicación del incidente
    lat = db.Column(db.Float, nullable=True)
    lng = db.Column(db.Float, nullable=True)

    reported_at = db.Column(db.DateTime, default=datetime.utcnow)
    resolved_at = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), nullable=False, default='reportado')  # reportado, resuelto

    # Relación con ruta
    route = db.relationship('Route', backref='incidents', lazy=True)

    def get_type_display(self):
        type_map = {
            'trafico': 'Tráfico Pesado',
            'accidente': 'Accidente Vial',
            'demora_descarga': 'Demora en Descarga',
            'vehiculo_averiado': 'Vehículo Averiado',
            'cliente_ausente': 'Cliente Ausente',
            'otro': 'Otro'
        }
        return type_map.get(self.incident_type, self.incident_type)

    def get_type_icon(self):
        icon_map = {
            'trafico': 'fa-car',
            'accidente': 'fa-car-crash',
            'demora_descarga': 'fa-clock',
            'vehiculo_averiado': 'fa-tools',
            'cliente_ausente': 'fa-user-slash',
            'otro': 'fa-exclamation-circle'
        }
        return icon_map.get(self.incident_type, 'fa-exclamation-circle')

    def __repr__(self):
        return f'<Incident {self.incident_type} - {self.status}>'
