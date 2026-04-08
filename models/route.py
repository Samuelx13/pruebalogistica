from models import db
from datetime import datetime


class Route(db.Model):
    __tablename__ = 'routes'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    driver_id = db.Column(db.Integer, db.ForeignKey('drivers.id'), nullable=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicles.id'), nullable=True)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow)

    # Métricas de la ruta
    total_distance_km = db.Column(db.Float, nullable=True, default=0.0)
    total_duration_min = db.Column(db.Float, nullable=True, default=0.0)
    total_orders = db.Column(db.Integer, nullable=True, default=0)

    # Capacidad utilizada
    total_weight_kg = db.Column(db.Float, nullable=True, default=0.0)
    total_volume_m3 = db.Column(db.Float, nullable=True, default=0.0)
    capacity_used_weight_pct = db.Column(db.Float, nullable=True, default=0.0)
    capacity_used_volume_pct = db.Column(db.Float, nullable=True, default=0.0)

    # Estado
    status = db.Column(db.String(20), nullable=False, default='planificada')
    # Estados: planificada, en_progreso, completada, cancelada

    # Coordenadas de origen (almacén)
    origin_lat = db.Column(db.Float, nullable=True)
    origin_lng = db.Column(db.Float, nullable=True)
    origin_address = db.Column(db.String(300), nullable=True)

    # Datos de ruta de Google Maps (JSON encoded)
    route_polyline = db.Column(db.Text, nullable=True)
    waypoints_order = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relaciones
    orders = db.relationship('Order', backref='route', lazy=True, order_by='Order.sequence_order')

    def get_status_display(self):
        status_map = {
            'planificada': 'Planificada',
            'en_progreso': 'En Progreso',
            'completada': 'Completada',
            'cancelada': 'Cancelada'
        }
        return status_map.get(self.status, self.status)

    def get_status_color(self):
        color_map = {
            'planificada': 'info',
            'en_progreso': 'primary',
            'completada': 'success',
            'cancelada': 'danger'
        }
        return color_map.get(self.status, 'secondary')

    def get_delivered_count(self):
        return len([o for o in self.orders if o.status == 'entregado'])

    def get_progress_pct(self):
        if self.total_orders and self.total_orders > 0:
            return round((self.get_delivered_count() / self.total_orders) * 100, 1)
        return 0.0

    def __repr__(self):
        return f'<Route {self.name} - {self.status}>'
