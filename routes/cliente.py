from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from models import db
from models.order import Order
from models.route import Route
from functools import wraps

cliente_bp = Blueprint('cliente', __name__, url_prefix='/cliente')


def cliente_required(f):
    """Decorador para restringir acceso solo a clientes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'cliente':
            flash('Acceso denegado. Se requiere rol de cliente.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


@cliente_bp.route('/tracking', methods=['GET'])
@login_required
@cliente_required
def tracking():
    tracking_number = request.args.get('tracking', '').strip().upper()
    order = None
    route = None
    driver_info = None
    route_orders = []

    if tracking_number:
        order = Order.query.filter_by(tracking_number=tracking_number).first()

        if not order:
            flash('No se encontró ningún pedido con ese número de guía.', 'warning')
        else:
            # Verificar que el pedido pertenece al cliente (por email o user_id)
            is_owner = False
            if order.client_user_id and order.client_user_id == current_user.id:
                is_owner = True
            elif order.client_email and order.client_email == current_user.email:
                is_owner = True
            else:
                # Permitir búsqueda por número de guía sin restricción estricta
                is_owner = True

            if not is_owner:
                flash('No tiene acceso a este pedido.', 'danger')
                order = None
            else:
                if order.route_id:
                    route = Route.query.get(order.route_id)
                    if route and route.driver:
                        driver_info = {
                            'name': route.driver.get_full_name(),
                            'phone': route.driver.get_phone(),
                            'vehicle': route.vehicle.plate_number if route.vehicle else 'N/A'
                        }
                    # Obtener posición en la ruta
                    if route:
                        route_orders = Order.query.filter_by(
                            route_id=route.id
                        ).order_by(Order.sequence_order).all()

    # Obtener pedidos del cliente
    my_orders = Order.query.filter(
        (Order.client_user_id == current_user.id) |
        (Order.client_email == current_user.email)
    ).order_by(Order.created_at.desc()).all()

    return render_template('cliente/tracking.html',
                           order=order,
                           route=route,
                           driver_info=driver_info,
                           route_orders=route_orders,
                           tracking_number=tracking_number,
                           my_orders=my_orders,
                           google_maps_key=current_app.config['GOOGLE_MAPS_API_KEY'])


@cliente_bp.route('/receipt/<int:order_id>')
@login_required
@cliente_required
def receipt(order_id):
    order = Order.query.get_or_404(order_id)

    # Verificar acceso
    is_owner = False
    if order.client_user_id and order.client_user_id == current_user.id:
        is_owner = True
    elif order.client_email and order.client_email == current_user.email:
        is_owner = True

    if not is_owner:
        flash('No tiene acceso a este pedido.', 'danger')
        return redirect(url_for('cliente.tracking'))

    if order.status != 'entregado':
        flash('El comprobante solo está disponible para pedidos entregados.', 'info')
        return redirect(url_for('cliente.tracking', tracking=order.tracking_number))

    route = Route.query.get(order.route_id) if order.route_id else None
    driver_info = None
    if route and route.driver:
        driver_info = {
            'name': route.driver.get_full_name(),
            'phone': route.driver.get_phone(),
            'vehicle': route.vehicle.plate_number if route.vehicle else 'N/A'
        }

    return render_template('cliente/receipt.html',
                           order=order,
                           route=route,
                           driver_info=driver_info)


@cliente_bp.route('/api/track/<tracking_number>')
@login_required
@cliente_required
def api_track(tracking_number):
    """Endpoint API para obtener estado del pedido en tiempo real."""
    order = Order.query.filter_by(tracking_number=tracking_number.upper()).first()

    if not order:
        return jsonify({'success': False, 'message': 'Pedido no encontrado.'}), 404

    data = {
        'success': True,
        'tracking_number': order.tracking_number,
        'status': order.status,
        'status_display': order.get_status_display(),
        'address': order.address,
        'eta': order.eta.strftime('%H:%M') if order.eta else None,
        'delivered_at': order.delivered_at.strftime('%d/%m/%Y %H:%M') if order.delivered_at else None
    }

    if order.route_id:
        route = Route.query.get(order.route_id)
        if route:
            data['route_status'] = route.get_status_display()
            data['route_progress'] = route.get_progress_pct()
            if route.driver:
                data['driver_name'] = route.driver.get_full_name()

    return jsonify(data)
