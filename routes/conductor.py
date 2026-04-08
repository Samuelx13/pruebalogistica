from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from models import db
from models.driver import Driver
from models.order import Order
from models.route import Route
from models.incident import Incident
from functools import wraps
from datetime import datetime

conductor_bp = Blueprint('conductor', __name__, url_prefix='/conductor')


def conductor_required(f):
    """Decorador para restringir acceso solo a conductores."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'conductor':
            flash('Acceso denegado. Se requiere rol de conductor.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


@conductor_bp.route('/dashboard')
@login_required
@conductor_required
def dashboard():
    driver = Driver.query.filter_by(user_id=current_user.id).first()

    if not driver:
        flash('No se encontró perfil de conductor. Contacte al administrador.', 'warning')
        return render_template('conductor/dashboard.html', driver=None, route=None, orders=[])

    # Obtener ruta activa del conductor
    active_route = Route.query.filter(
        Route.driver_id == driver.id,
        Route.status.in_(['planificada', 'en_progreso'])
    ).first()

    orders = []
    if active_route:
        orders = Order.query.filter_by(route_id=active_route.id).order_by(Order.sequence_order).all()

    # Estadísticas del día
    today_delivered = Order.query.join(Route).filter(
        Route.driver_id == driver.id,
        Order.status == 'entregado',
        Order.delivered_at >= datetime.utcnow().replace(hour=0, minute=0, second=0)
    ).count()

    total_assigned = len(orders)
    pending = len([o for o in orders if o.status in ['asignado', 'en_transito']])
    delivered = len([o for o in orders if o.status == 'entregado'])

    return render_template('conductor/dashboard.html',
                           driver=driver,
                           route=active_route,
                           orders=orders,
                           today_delivered=today_delivered,
                           total_assigned=total_assigned,
                           pending=pending,
                           delivered=delivered,
                           google_maps_key=current_app.config['GOOGLE_MAPS_API_KEY'])


@conductor_bp.route('/delivery/<int:order_id>')
@login_required
@conductor_required
def delivery_detail(order_id):
    driver = Driver.query.filter_by(user_id=current_user.id).first()
    if not driver:
        flash('No se encontró perfil de conductor.', 'warning')
        return redirect(url_for('conductor.dashboard'))

    order = Order.query.get_or_404(order_id)

    # Verificar que el pedido pertenece a una ruta del conductor
    if not order.route or order.route.driver_id != driver.id:
        flash('No tiene acceso a este pedido.', 'danger')
        return redirect(url_for('conductor.dashboard'))

    # Obtener pedido anterior y siguiente en la secuencia
    prev_order = None
    next_order = None
    if order.route_id and order.sequence_order:
        prev_order = Order.query.filter(
            Order.route_id == order.route_id,
            Order.sequence_order == order.sequence_order - 1
        ).first()
        next_order = Order.query.filter(
            Order.route_id == order.route_id,
            Order.sequence_order == order.sequence_order + 1
        ).first()

    return render_template('conductor/delivery.html',
                           order=order,
                           prev_order=prev_order,
                           next_order=next_order,
                           driver=driver,
                           google_maps_key=current_app.config['GOOGLE_MAPS_API_KEY'])


@conductor_bp.route('/delivery/<int:order_id>/update_status', methods=['POST'])
@login_required
@conductor_required
def update_delivery_status(order_id):
    driver = Driver.query.filter_by(user_id=current_user.id).first()
    if not driver:
        return jsonify({'success': False, 'message': 'Perfil de conductor no encontrado.'}), 403

    order = Order.query.get_or_404(order_id)

    if not order.route or order.route.driver_id != driver.id:
        return jsonify({'success': False, 'message': 'No tiene acceso a este pedido.'}), 403

    new_status = request.form.get('status', '')
    valid_statuses = ['en_transito', 'entregado', 'cliente_ausente', 'devolucion']

    if new_status not in valid_statuses:
        flash('Estado no válido.', 'danger')
        return redirect(url_for('conductor.dashboard'))

    order.status = new_status

    if new_status == 'entregado':
        order.delivered_at = datetime.utcnow()

    # Verificar si todos los pedidos de la ruta están completados
    route = order.route
    if route:
        all_orders = Order.query.filter_by(route_id=route.id).all()
        completed_statuses = ['entregado', 'cliente_ausente', 'devolucion']
        all_completed = all(o.status in completed_statuses for o in all_orders)

        if all_completed:
            route.status = 'completada'
            driver.status = 'disponible'
            if route.vehicle:
                route.vehicle.status = 'disponible'

        # Actualizar ruta a en_progreso si estaba planificada
        elif route.status == 'planificada':
            route.status = 'en_progreso'

    db.session.commit()

    status_display = {
        'en_transito': 'En Tránsito',
        'entregado': 'Entregado',
        'cliente_ausente': 'Cliente Ausente',
        'devolucion': 'Devolución'
    }

    flash(f'Pedido {order.tracking_number} actualizado a: {status_display.get(new_status, new_status)}', 'success')
    return redirect(url_for('conductor.dashboard'))


@conductor_bp.route('/report', methods=['GET', 'POST'])
@login_required
@conductor_required
def report_incident():
    driver = Driver.query.filter_by(user_id=current_user.id).first()
    if not driver:
        flash('No se encontró perfil de conductor.', 'warning')
        return redirect(url_for('conductor.dashboard'))

    if request.method == 'POST':
        incident_type = request.form.get('incident_type', '').strip()
        description = request.form.get('description', '').strip()
        order_id = request.form.get('order_id', type=int)
        duration_minutes = request.form.get('duration_minutes', 0, type=int)

        if not incident_type or not description:
            flash('Tipo de incidencia y descripción son obligatorios.', 'danger')
            return redirect(url_for('conductor.report_incident'))

        # Obtener ruta activa
        active_route = Route.query.filter(
            Route.driver_id == driver.id,
            Route.status.in_(['planificada', 'en_progreso'])
        ).first()

        incident = Incident(
            driver_id=driver.id,
            order_id=order_id if order_id else None,
            route_id=active_route.id if active_route else None,
            incident_type=incident_type,
            description=description,
            duration_minutes=duration_minutes,
            status='reportado'
        )
        db.session.add(incident)
        db.session.commit()

        flash('Novedad reportada exitosamente.', 'success')
        return redirect(url_for('conductor.dashboard'))

    # Obtener pedidos de la ruta activa para el formulario
    active_route = Route.query.filter(
        Route.driver_id == driver.id,
        Route.status.in_(['planificada', 'en_progreso'])
    ).first()

    orders = []
    if active_route:
        orders = Order.query.filter_by(route_id=active_route.id).order_by(Order.sequence_order).all()

    return render_template('conductor/report.html', driver=driver, orders=orders)
