from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from models import db
from models.user import User
from models.vehicle import Vehicle
from models.driver import Driver
from models.order import Order
from models.route import Route
from models.incident import Incident
from services.route_optimizer import optimize_routes, get_route_analytics
from services.order_processor import process_orders_file
from services.geocoding import geocode_address
from functools import wraps
from datetime import datetime
import os
import json

# Blueprint para API públicas (geocodificación)
api_bp = Blueprint('api', __name__)


@api_bp.route('/api/geocode')
def api_geocode():
    """Endpoint público para geocodificar direcciones."""
    address = request.args.get('address', '')
    if not address:
        return jsonify({'success': False, 'error': 'Dirección requerida'})
    
    result = geocode_address(address)
    return jsonify(result)


@api_bp.route('/api/reverse-geocode')
def api_reverse_geocode():
    """Endpoint público para reverse geocodificación."""
    lat = request.args.get('lat', type=float)
    lng = request.args.get('lng', type=float)
    
    if not lat or not lng:
        return jsonify({'success': False, 'error': 'Coordenadas requeridas'})
    
    # Usar Nominatim para reverse geocoding
    try:
        import requests as req
        url = f"https://nominatim.openstreetmap.org/reverse"
        params = {'lat': lat, 'lng': lng, 'format': 'json'}
        resp = req.get(url, params=params, timeout=5)
        data = resp.json()
        return jsonify({
            'success': True,
            'formatted_address': data.get('display_name', '')
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def admin_required(f):
    """Decorador para restringir acceso solo a administradores."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Acceso denegado. Se requieren permisos de administrador.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


# ==================== DASHBOARD ====================

@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    # Estadísticas generales
    total_orders = Order.query.count()
    orders_pending = Order.query.filter_by(status='en_almacen').count()
    orders_in_transit = Order.query.filter(Order.status.in_(['asignado', 'en_transito'])).count()
    orders_delivered = Order.query.filter_by(status='entregado').count()

    total_vehicles = Vehicle.query.count()
    vehicles_available = Vehicle.query.filter_by(status='disponible').count()
    vehicles_in_route = Vehicle.query.filter_by(status='en_ruta').count()

    total_drivers = Driver.query.count()
    drivers_available = Driver.query.filter_by(status='disponible').count()
    drivers_in_route = Driver.query.filter_by(status='en_ruta').count()

    total_routes = Route.query.count()
    routes_active = Route.query.filter(Route.status.in_(['planificada', 'en_progreso'])).count()
    routes_completed = Route.query.filter_by(status='completada').count()

    total_incidents = Incident.query.filter_by(status='reportado').count()

    # Rutas activas para el mapa
    active_routes = Route.query.filter(
        Route.status.in_(['planificada', 'en_progreso'])
    ).all()

    routes_data = []
    for route in active_routes:
        route_orders = Order.query.filter_by(route_id=route.id).order_by(Order.sequence_order).all()
        orders_list = [{
            'id': o.id,
            'tracking_number': o.tracking_number,
            'client_name': o.client_name,
            'address': o.address,
            'lat': o.lat,
            'lng': o.lng,
            'status': o.status,
            'sequence_order': o.sequence_order,
            'weight_kg': o.weight_kg,
            'volume_m3': o.volume_m3
        } for o in route_orders]

        routes_data.append({
            'id': route.id,
            'name': route.name,
            'driver': route.driver.get_full_name() if route.driver else 'Sin asignar',
            'vehicle': route.vehicle.plate_number if route.vehicle else 'Sin asignar',
            'status': route.status,
            'total_orders': route.total_orders,
            'delivered': route.get_delivered_count(),
            'progress': route.get_progress_pct(),
            'weight_pct': route.capacity_used_weight_pct,
            'volume_pct': route.capacity_used_volume_pct,
            'polyline': route.route_polyline,
            'orders': orders_list,
            'origin_lat': route.origin_lat,
            'origin_lng': route.origin_lng
        })

    # Analíticas
    analytics = get_route_analytics()

    return render_template('admin/dashboard.html',
                           total_orders=total_orders,
                           orders_pending=orders_pending,
                           orders_in_transit=orders_in_transit,
                           orders_delivered=orders_delivered,
                           total_vehicles=total_vehicles,
                           vehicles_available=vehicles_available,
                           vehicles_in_route=vehicles_in_route,
                           total_drivers=total_drivers,
                           drivers_available=drivers_available,
                           drivers_in_route=drivers_in_route,
                           total_routes=total_routes,
                           routes_active=routes_active,
                           routes_completed=routes_completed,
                           total_incidents=total_incidents,
                           routes_data=json.dumps(routes_data),
                           analytics=analytics,
                           google_maps_key=current_app.config['GOOGLE_MAPS_API_KEY'])


# ==================== GESTIÓN DE FLOTA ====================

@admin_bp.route('/fleet')
@login_required
@admin_required
def fleet():
    vehicles = Vehicle.query.order_by(Vehicle.created_at.desc()).all()
    return render_template('admin/fleet.html', vehicles=vehicles)


@admin_bp.route('/fleet/add', methods=['POST'])
@login_required
@admin_required
def fleet_add():
    plate_number = request.form.get('plate_number', '').strip().upper()
    brand = request.form.get('brand', '').strip()
    model = request.form.get('model', '').strip()
    year = request.form.get('year', type=int)
    max_weight_kg = request.form.get('max_weight_kg', 1000, type=float)
    max_volume_m3 = request.form.get('max_volume_m3', 10, type=float)
    fuel_type = request.form.get('fuel_type', 'Gasolina').strip()

    if not plate_number or not brand or not model:
        flash('Placa, marca y modelo son obligatorios.', 'danger')
        return redirect(url_for('admin.fleet'))

    if Vehicle.query.filter_by(plate_number=plate_number).first():
        flash('Ya existe un vehículo con esa placa.', 'warning')
        return redirect(url_for('admin.fleet'))

    vehicle = Vehicle(
        plate_number=plate_number,
        brand=brand,
        model=model,
        year=year,
        max_weight_kg=max_weight_kg,
        max_volume_m3=max_volume_m3,
        fuel_type=fuel_type,
        status='disponible'
    )
    db.session.add(vehicle)
    db.session.commit()

    flash(f'Vehículo {plate_number} agregado exitosamente.', 'success')
    return redirect(url_for('admin.fleet'))


@admin_bp.route('/fleet/edit/<int:vehicle_id>', methods=['POST'])
@login_required
@admin_required
def fleet_edit(vehicle_id):
    vehicle = Vehicle.query.get_or_404(vehicle_id)

    vehicle.plate_number = request.form.get('plate_number', vehicle.plate_number).strip().upper()
    vehicle.brand = request.form.get('brand', vehicle.brand).strip()
    vehicle.model = request.form.get('model', vehicle.model).strip()
    vehicle.year = request.form.get('year', vehicle.year, type=int)
    vehicle.max_weight_kg = request.form.get('max_weight_kg', vehicle.max_weight_kg, type=float)
    vehicle.max_volume_m3 = request.form.get('max_volume_m3', vehicle.max_volume_m3, type=float)
    vehicle.fuel_type = request.form.get('fuel_type', vehicle.fuel_type).strip()
    vehicle.status = request.form.get('status', vehicle.status).strip()

    db.session.commit()
    flash(f'Vehículo {vehicle.plate_number} actualizado.', 'success')
    return redirect(url_for('admin.fleet'))


@admin_bp.route('/fleet/delete/<int:vehicle_id>', methods=['POST'])
@login_required
@admin_required
def fleet_delete(vehicle_id):
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    db.session.delete(vehicle)
    db.session.commit()
    flash(f'Vehículo {vehicle.plate_number} eliminado.', 'success')
    return redirect(url_for('admin.fleet'))


# ==================== GESTIÓN DE CONDUCTORES ====================

@admin_bp.route('/drivers')
@login_required
@admin_required
def drivers():
    drivers_list = Driver.query.all()
    vehicles = Vehicle.query.filter_by(status='disponible').all()
    # Usuarios con rol conductor que no tienen perfil de conductor
    conductor_users = User.query.filter_by(role='conductor').all()
    existing_driver_user_ids = [d.user_id for d in drivers_list]
    available_users = [u for u in conductor_users if u.id not in existing_driver_user_ids]
    return render_template('admin/drivers.html',
                           drivers=drivers_list,
                           vehicles=vehicles,
                           available_users=available_users)


@admin_bp.route('/drivers/add', methods=['POST'])
@login_required
@admin_required
def drivers_add():
    user_id = request.form.get('user_id', type=int)
    vehicle_id = request.form.get('vehicle_id', type=int)
    license_number = request.form.get('license_number', '').strip()

    # Si no hay usuario existente, crear uno nuevo
    if not user_id:
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '123456')

        if not first_name or not last_name or not username or not email:
            flash('Nombre, apellido, usuario y email son obligatorios.', 'danger')
            return redirect(url_for('admin.drivers'))

        if User.query.filter_by(username=username).first():
            flash('El nombre de usuario ya existe.', 'warning')
            return redirect(url_for('admin.drivers'))

        user = User(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            role='conductor'
        )
        user.set_password(password)
        db.session.add(user)
        db.session.flush()
        user_id = user.id

    if not license_number:
        flash('El número de licencia es obligatorio.', 'danger')
        return redirect(url_for('admin.drivers'))

    driver = Driver(
        user_id=user_id,
        vehicle_id=vehicle_id if vehicle_id else None,
        license_number=license_number,
        status='disponible'
    )
    db.session.add(driver)
    db.session.commit()

    flash('Conductor agregado exitosamente.', 'success')
    return redirect(url_for('admin.drivers'))


@admin_bp.route('/drivers/edit/<int:driver_id>', methods=['POST'])
@login_required
@admin_required
def drivers_edit(driver_id):
    driver = Driver.query.get_or_404(driver_id)

    driver.license_number = request.form.get('license_number', driver.license_number).strip()
    driver.vehicle_id = request.form.get('vehicle_id', driver.vehicle_id, type=int) or None
    driver.status = request.form.get('status', driver.status).strip()

    if driver.user:
        driver.user.phone = request.form.get('phone', driver.user.phone).strip()

    db.session.commit()
    flash('Conductor actualizado.', 'success')
    return redirect(url_for('admin.drivers'))


@admin_bp.route('/drivers/delete/<int:driver_id>', methods=['POST'])
@login_required
@admin_required
def drivers_delete(driver_id):
    driver = Driver.query.get_or_404(driver_id)
    db.session.delete(driver)
    db.session.commit()
    flash('Conductor eliminado.', 'success')
    return redirect(url_for('admin.drivers'))


# ==================== GESTIÓN DE PEDIDOS ====================

@admin_bp.route('/orders')
@login_required
@admin_required
def orders():
    status_filter = request.args.get('status', '')
    query = Order.query

    if status_filter:
        query = query.filter_by(status=status_filter)

    orders_list = query.order_by(Order.created_at.desc()).all()
    return render_template('admin/orders.html', orders=orders_list, status_filter=status_filter)


from services.user_service import lookup_user_by_cedula

@admin_bp.route('/api/user-by-cedula')
@login_required
@admin_required
def api_user_by_cedula():
    cedula = request.args.get('cedula', '').strip().upper()
    user_data = lookup_user_by_cedula(cedula)
    return jsonify(user_data or {})

@admin_bp.route('/orders/add', methods=['POST'])
@login_required
@admin_required
def orders_add():
    cedula = request.form.get('cedula', '').strip().upper()
    client_name = request.form.get('client_name', '').strip()
    address = request.form.get('address', '').strip()
    weight_kg = request.form.get('weight_kg', 1.0, type=float)
    volume_m3 = request.form.get('volume_m3', 0.01, type=float)
    client_phone = request.form.get('client_phone', '').strip()
    client_email = request.form.get('client_email', '').strip()
    client_user_id = request.form.get('client_user_id', type=int)
    description = request.form.get('description', '').strip()
    special_instructions = request.form.get('special_instructions', '').strip()

    if not client_name or not address:
        flash('Nombre del cliente y dirección son obligatorios.', 'danger')
        return redirect(url_for('admin.orders'))

    # Geocodificar dirección
    # Si hay cédula registrada, usar datos del cliente
    if cedula:
        user_data = lookup_user_by_cedula(cedula)
        if user_data:
            client_user_id = user_data['id']
            client_name = client_name or user_data['full_name']
            client_phone = client_phone or user_data['phone']
            client_email = client_email or user_data['email']
            if not address and user_data['address']:
                address = user_data['address']
                flash('Datos del cliente cargados desde cédula. Dirección principal utilizada.', 'info')

    geo = geocode_address(address)

    order = Order(
        client_user_id=client_user_id,
        client_name=client_name,
        client_phone=client_phone if client_phone else None,
        client_email=client_email if client_email else None,
        address=address,
    lat=request.form.get('lat', type=float) or geo.get('lat'),
    lng=request.form.get('lng', type=float) or geo.get('lng'),
        weight_kg=weight_kg,
        volume_m3=volume_m3,
        description=description if description else None,
        special_instructions=special_instructions if special_instructions else None,
        status='en_almacen'
    )
    db.session.add(order)
    db.session.commit()

    if geo.get('success'):
        flash(f'Pedido {order.tracking_number} creado y geocodificado exitosamente.', 'success')
    else:
        flash(f'Pedido {order.tracking_number} creado, pero no se pudo geocodificar la dirección.', 'warning')

    return redirect(url_for('admin.orders'))


@admin_bp.route('/orders/upload', methods=['POST'])
@login_required
@admin_required
def orders_upload():
    if 'file' not in request.files:
        flash('No se seleccionó ningún archivo.', 'danger')
        return redirect(url_for('admin.orders'))

    file = request.files['file']
    if file.filename == '':
        flash('No se seleccionó ningún archivo.', 'danger')
        return redirect(url_for('admin.orders'))

    allowed_extensions = {'.csv', '.xlsx', '.xls'}
    file_ext = os.path.splitext(file.filename)[1].lower()

    if file_ext not in allowed_extensions:
        flash('Formato no soportado. Use CSV o Excel (.xlsx/.xls).', 'danger')
        return redirect(url_for('admin.orders'))

    # Guardar archivo
    upload_folder = current_app.config['UPLOAD_FOLDER']
    os.makedirs(upload_folder, exist_ok=True)
    filepath = os.path.join(upload_folder, f"upload_{datetime.now().strftime('%Y%m%d_%H%M%S')}{file_ext}")
    file.save(filepath)

    # Procesar archivo
    result = process_orders_file(filepath)

    if result['success']:
        flash(f"Archivo procesado: {result['orders_created']} pedidos creados, "
              f"{result['orders_failed']} fallidos.", 'success')
        if result.get('stats'):
            stats = result['stats']
            flash(f"Estadísticas: Peso total {stats['total_weight_kg']} kg, "
                  f"Volumen total {stats['total_volume_m3']} m³", 'info')
    else:
        flash(f"Error al procesar archivo: {result.get('error', 'Error desconocido')}", 'danger')

    return redirect(url_for('admin.orders'))


@admin_bp.route('/orders/delete/<int:order_id>', methods=['POST'])
@login_required
@admin_required
def orders_delete(order_id):
    order = Order.query.get_or_404(order_id)
    db.session.delete(order)
    db.session.commit()
    flash(f'Pedido {order.tracking_number} eliminado.', 'success')
    return redirect(url_for('admin.orders'))


# ==================== RUTAS ====================

@admin_bp.route('/routes')
@login_required
@admin_required
def routes_view():
    routes_list = Route.query.order_by(Route.created_at.desc()).all()
    return render_template('admin/routes.html',
    routes=routes_list,
    google_maps_key=current_app.config['GOOGLE_MAPS_API_KEY'])


@admin_bp.route('/routes/optimize', methods=['POST'])
@login_required
@admin_required
def routes_optimize():
    use_google = request.form.get('use_google_maps', 'true') == 'true'
    result = optimize_routes(use_google_maps=use_google)

    if result['success']:
        flash(result['message'], 'success')
    else:
        flash(result['message'], 'warning')

    return redirect(url_for('admin.routes_view'))


@admin_bp.route('/routes/<int:route_id>/start', methods=['POST'])
@login_required
@admin_required
def route_start(route_id):
    route = Route.query.get_or_404(route_id)
    route.status = 'en_progreso'
    
    for order in route.orders:
        if order.status == 'asignado':
            order.status = 'en_transito'
    
    db.session.commit()
    flash(f'Ruta {route.name} iniciada.', 'success')
    return redirect(url_for('admin.routes_view'))


@admin_bp.route('/routes/<int:route_id>/cancel', methods=['POST'])
@login_required
@admin_required
def route_cancel(route_id):
    route = Route.query.get_or_404(route_id)
    route.status = 'cancelada'

    # Liberar pedidos
    for order in route.orders:
        order.route_id = None
        order.sequence_order = None
        order.status = 'en_almacen'

    # Liberar conductor y vehículo
    if route.driver:
        route.driver.status = 'disponible'
    if route.vehicle:
        route.vehicle.status = 'disponible'

    db.session.commit()
    flash(f'Ruta {route.name} cancelada. Pedidos liberados.', 'info')
    return redirect(url_for('admin.routes_view'))


# ==================== EXCEPCIONES ====================

@admin_bp.route('/exceptions')
@login_required
@admin_required
def exceptions():
    incidents = Incident.query.order_by(Incident.reported_at.desc()).all()
    routes_list = Route.query.filter(Route.status.in_(['planificada', 'en_progreso'])).all()
    drivers_list = Driver.query.filter_by(status='disponible').all()
    return render_template('admin/exceptions.html',
                           incidents=incidents,
                           routes=routes_list,
                           drivers=drivers_list)


@admin_bp.route('/exceptions/reassign', methods=['POST'])
@login_required
@admin_required
def reassign_order():
    order_id = request.form.get('order_id', type=int)
    new_route_id = request.form.get('new_route_id', type=int)

    order = Order.query.get_or_404(order_id)

    if new_route_id:
        new_route = Route.query.get_or_404(new_route_id)
        # Obtener la última secuencia de la nueva ruta
        max_seq = db.session.query(db.func.max(Order.sequence_order)).filter_by(route_id=new_route_id).scalar() or 0
        
        order.route_id = new_route_id
        order.sequence_order = max_seq + 1
        order.status = 'asignado'
        
        new_route.total_orders = (new_route.total_orders or 0) + 1
        new_route.total_weight_kg = (new_route.total_weight_kg or 0) + order.weight_kg
        new_route.total_volume_m3 = (new_route.total_volume_m3 or 0) + order.volume_m3
    else:
        order.route_id = None
        order.sequence_order = None
        order.status = 'en_almacen'

    db.session.commit()
    flash(f'Pedido {order.tracking_number} reasignado exitosamente.', 'success')
    return redirect(url_for('admin.exceptions'))


# ==================== API ENDPOINTS ====================

@admin_bp.route('/api/stats')
@login_required
@admin_required
def api_stats():
    """Endpoint API para obtener estadísticas en tiempo real."""
    analytics = get_route_analytics()
    
    orders_by_status = {
        'en_almacen': Order.query.filter_by(status='en_almacen').count(),
        'asignado': Order.query.filter_by(status='asignado').count(),
        'en_transito': Order.query.filter_by(status='en_transito').count(),
        'entregado': Order.query.filter_by(status='entregado').count(),
        'cliente_ausente': Order.query.filter_by(status='cliente_ausente').count(),
        'devolucion': Order.query.filter_by(status='devolucion').count()
    }
    
    return jsonify({
        'analytics': analytics,
        'orders_by_status': orders_by_status
    })


@admin_bp.route('/api/routes')
@login_required
@admin_required
def api_routes():
    """Endpoint API para obtener datos de rutas activas."""
    active_routes = Route.query.filter(
        Route.status.in_(['planificada', 'en_progreso'])
    ).all()

    routes_data = []
    for route in active_routes:
        route_orders = Order.query.filter_by(route_id=route.id).order_by(Order.sequence_order).all()
        orders_list = [{
            'id': o.id,
            'tracking_number': o.tracking_number,
            'client_name': o.client_name,
            'address': o.address,
            'lat': o.lat,
            'lng': o.lng,
            'status': o.status,
            'sequence_order': o.sequence_order
        } for o in route_orders]

        routes_data.append({
            'id': route.id,
            'name': route.name,
            'driver': route.driver.get_full_name() if route.driver else 'Sin asignar',
            'vehicle': route.vehicle.plate_number if route.vehicle else 'Sin asignar',
            'status': route.status,
            'progress': route.get_progress_pct(),
            'polyline': route.route_polyline,
            'orders': orders_list,
            'origin_lat': route.origin_lat,
            'origin_lng': route.origin_lng
        })

    return jsonify(routes_data)
