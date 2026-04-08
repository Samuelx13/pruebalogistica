from models import db
from datetime import datetime
import uuid


def generate_tracking_number():
    """Genera un número de guía único."""
    return 'ENV-' + uuid.uuid4().hex[:8].upper()


class Order(db.Model):
    __tablename__ = 'orders'

    id = db.Column(db.Integer, primary_key=True)
    tracking_number = db.Column(db.String(20), unique=True, nullable=False, default=generate_tracking_number)
    client_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    client_name = db.Column(db.String(120), nullable=False)
    client_phone = db.Column(db.String(20), nullable=True)
    client_email = db.Column(db.String(120), nullable=True)

    # Dirección de entrega
    address = db.Column(db.String(300), nullable=False)
    city = db.Column(db.String(100), nullable=True)
    state = db.Column(db.String(100), nullable=True)
    zip_code = db.Column(db.String(10), nullable=True)
    lat = db.Column(db.Float, nullable=True)
    lng = db.Column(db.Float, nullable=True)

    # Detalles del paquete
    weight_kg = db.Column(db.Float, nullable=False, default=1.0)
    volume_m3 = db.Column(db.Float, nullable=False, default=0.01)
    description = db.Column(db.String(300), nullable=True)
    special_instructions = db.Column(db.Text, nullable=True)

    # Estado y asignación
    status = db.Column(db.String(30), nullable=False, default='en_almacen')
    # Estados: en_almacen, asignado, en_transito, entregado, cliente_ausente, devolucion
    route_id = db.Column(db.Integer, db.ForeignKey('routes.id'), nullable=True)
    sequence_order = db.Column(db.Integer, nullable=True)

    # Tiempos
    eta = db.Column(db.DateTime, nullable=True)
    delivered_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relaciones
    incidents = db.relationship('Incident', backref='order', lazy=True)

    def get_status_display(self):
        status_map = {
            'en_almacen': 'En Almacén',
            'asignado': 'Asignado a Ruta',
            'en_transito': 'En Tránsito',
            'entregado': 'Entregado',
            'cliente_ausente': 'Cliente Ausente',
            'devolucion': 'Devolución'
        }
        return status_map.get(self.status, self.status)

    def get_status_color(self):
        color_map = {
            'en_almacen': 'secondary',
            'asignado': 'info',
            'en_transito': 'primary',
            'entregado': 'success',
            'cliente_ausente': 'warning',
            'devolucion': 'danger'
        }
        return color_map.get(self.status, 'secondary')

    def __repr__(self):
        return f'<Order {self.tracking_number} - {self.status}>'
