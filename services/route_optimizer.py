import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from models import db
from models.order import Order
from models.route import Route
from models.vehicle import Vehicle
from models.driver import Driver
from services.geocoding import get_directions
from config import Config
import json


def calculate_distance(lat1, lng1, lat2, lng2):
    """
    Calcula la distancia aproximada entre dos puntos usando la fórmula de Haversine.
    Retorna la distancia en kilómetros.
    """
    R = 6371  # Radio de la Tierra en km
    
    lat1_rad = np.radians(lat1)
    lat2_rad = np.radians(lat2)
    dlat = np.radians(lat2 - lat1)
    dlng = np.radians(lng2 - lng1)
    
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(dlng / 2) ** 2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    
    return R * c


def nearest_neighbor_sort(orders_df, origin_lat, origin_lng):
    """
    Algoritmo del vecino más cercano para ordenar las entregas.
    Comienza desde el almacén y va seleccionando el punto más cercano no visitado.
    
    Retorna el DataFrame ordenado con la secuencia óptima.
    """
    if orders_df.empty:
        return orders_df
    
    df = orders_df.copy()
    df = df.dropna(subset=['lat', 'lng'])
    
    if df.empty:
        return orders_df
    
    visited = []
    unvisited = list(df.index)
    current_lat = origin_lat
    current_lng = origin_lng
    sequence = 1
    
    while unvisited:
        min_dist = float('inf')
        nearest_idx = None
        
        for idx in unvisited:
            dist = calculate_distance(
                current_lat, current_lng,
                df.loc[idx, 'lat'], df.loc[idx, 'lng']
            )
            if dist < min_dist:
                min_dist = dist
                nearest_idx = idx
        
        if nearest_idx is not None:
            df.loc[nearest_idx, 'sequence_order'] = sequence
            df.loc[nearest_idx, 'distance_from_prev'] = round(min_dist, 2)
            visited.append(nearest_idx)
            unvisited.remove(nearest_idx)
            current_lat = df.loc[nearest_idx, 'lat']
            current_lng = df.loc[nearest_idx, 'lng']
            sequence += 1
    
    df = df.loc[visited]
    return df


def assign_orders_to_vehicles(orders_df, vehicles):
    """
    Asigna pedidos a vehículos respetando las capacidades de carga (peso y volumen).
    Usa un algoritmo de bin-packing simplificado (First Fit Decreasing).
    
    orders_df: DataFrame con los pedidos ordenados
    vehicles: lista de diccionarios con datos de vehículos disponibles
    
    Retorna un diccionario con las asignaciones {vehicle_id: [order_ids]}
    """
    if orders_df.empty or not vehicles:
        return {}
    
    # Ordenar pedidos por peso descendente (First Fit Decreasing)
    df = orders_df.sort_values('weight_kg', ascending=False).copy()
    
    assignments = {}
    vehicle_remaining = {}
    
    for v in vehicles:
        assignments[v['id']] = []
        vehicle_remaining[v['id']] = {
            'weight': v['max_weight_kg'],
            'volume': v['max_volume_m3']
        }
    
    for idx, order in df.iterrows():
        assigned = False
        for v in vehicles:
            vid = v['id']
            if (vehicle_remaining[vid]['weight'] >= order['weight_kg'] and
                    vehicle_remaining[vid]['volume'] >= order['volume_m3']):
                assignments[vid].append(order['id'])
                vehicle_remaining[vid]['weight'] -= order['weight_kg']
                vehicle_remaining[vid]['volume'] -= order['volume_m3']
                assigned = True
                break
        
        if not assigned:
            # Si no cabe en ningún vehículo, asignar al que tenga más capacidad restante
            best_vehicle = max(vehicle_remaining.keys(),
                               key=lambda vid: vehicle_remaining[vid]['weight'])
            assignments[best_vehicle].append(order['id'])
            vehicle_remaining[best_vehicle]['weight'] -= order['weight_kg']
            vehicle_remaining[best_vehicle]['volume'] -= order['volume_m3']
    
    # Eliminar vehículos sin asignaciones
    assignments = {k: v for k, v in assignments.items() if v}
    
    return assignments


def optimize_routes(use_google_maps=True):
    """
    Función principal que ejecuta el algoritmo completo de optimización de rutas.
    
    1. Obtiene pedidos sin asignar (en_almacen)
    2. Los geocodifica si es necesario
    3. Obtiene vehículos y conductores disponibles
    4. Asigna pedidos a vehículos por capacidad
    5. Ordena las entregas por proximidad geográfica (vecino más cercano)
    6. Opcionalmente optimiza con Google Maps Directions API
    7. Crea las rutas en la base de datos
    
    Retorna un resumen de las rutas creadas.
    """
    # 1. Obtener pedidos sin asignar con coordenadas
    unassigned_orders = Order.query.filter(
        Order.status == 'en_almacen',
        Order.route_id.is_(None),
        Order.lat.isnot(None),
        Order.lng.isnot(None)
    ).all()
    
    if not unassigned_orders:
        return {
            'success': False,
            'message': 'No hay pedidos sin asignar con coordenadas válidas.',
            'routes_created': 0
        }
    
    # Crear DataFrame con Pandas
    orders_data = []
    for order in unassigned_orders:
        orders_data.append({
            'id': order.id,
            'tracking_number': order.tracking_number,
            'client_name': order.client_name,
            'address': order.address,
            'lat': order.lat,
            'lng': order.lng,
            'weight_kg': order.weight_kg,
            'volume_m3': order.volume_m3
        })
    
    orders_df = pd.DataFrame(orders_data)
    
    # 2. Obtener vehículos disponibles
    available_vehicles = Vehicle.query.filter(
        Vehicle.status == 'disponible'
    ).all()
    
    if not available_vehicles:
        return {
            'success': False,
            'message': 'No hay vehículos disponibles.',
            'routes_created': 0
        }
    
    vehicles_list = [{
        'id': v.id,
        'plate_number': v.plate_number,
        'max_weight_kg': v.max_weight_kg,
        'max_volume_m3': v.max_volume_m3
    } for v in available_vehicles]
    
    # 3. Obtener conductores disponibles
    available_drivers = Driver.query.filter(
        Driver.status == 'disponible'
    ).all()
    
    if not available_drivers:
        return {
            'success': False,
            'message': 'No hay conductores disponibles.',
            'routes_created': 0
        }
    
    # 4. Asignar pedidos a vehículos
    assignments = assign_orders_to_vehicles(orders_df, vehicles_list)
    
    if not assignments:
        return {
            'success': False,
            'message': 'No se pudieron asignar pedidos a vehículos.',
            'routes_created': 0
        }
    
    # 5. Crear rutas
    routes_created = []
    driver_index = 0
    origin_lat = Config.WAREHOUSE_LAT
    origin_lng = Config.WAREHOUSE_LNG
    
    for vehicle_id, order_ids in assignments.items():
        if driver_index >= len(available_drivers):
            break
        
        driver = available_drivers[driver_index]
        vehicle = Vehicle.query.get(vehicle_id)
        
        # Filtrar pedidos de este vehículo
        vehicle_orders_df = orders_df[orders_df['id'].isin(order_ids)].copy()
        
        # Ordenar por vecino más cercano
        sorted_orders_df = nearest_neighbor_sort(vehicle_orders_df, origin_lat, origin_lng)
        
        # Calcular capacidad utilizada
        total_weight = sorted_orders_df['weight_kg'].sum()
        total_volume = sorted_orders_df['volume_m3'].sum()
        weight_pct = round((total_weight / vehicle.max_weight_kg) * 100, 1) if vehicle.max_weight_kg > 0 else 0
        volume_pct = round((total_volume / vehicle.max_volume_m3) * 100, 1) if vehicle.max_volume_m3 > 0 else 0
        
        # Crear ruta
        route = Route(
            name=f"Ruta {datetime.now().strftime('%Y%m%d')}-{vehicle.plate_number}",
            driver_id=driver.id,
            vehicle_id=vehicle_id,
            date=datetime.utcnow().date(),
            total_orders=len(order_ids),
            total_weight_kg=round(total_weight, 2),
            total_volume_m3=round(total_volume, 4),
            capacity_used_weight_pct=weight_pct,
            capacity_used_volume_pct=volume_pct,
            origin_lat=origin_lat,
            origin_lng=origin_lng,
            origin_address=Config.WAREHOUSE_ADDRESS,
            status='planificada'
        )
        
        db.session.add(route)
        db.session.flush()  # Para obtener el ID de la ruta
        
        # Intentar optimizar con Google Maps
        total_distance = 0
        total_duration = 0
        
        if use_google_maps and len(sorted_orders_df) > 0:
            try:
                waypoints = list(zip(
                    sorted_orders_df['lat'].tolist(),
                    sorted_orders_df['lng'].tolist()
                ))
                
                origin = (origin_lat, origin_lng)
                destination = waypoints[-1] if waypoints else origin
                intermediate = waypoints[:-1] if len(waypoints) > 1 else []
                
                directions = get_directions(origin, destination, intermediate)
                
                if directions['success']:
                    total_distance = directions['total_distance_km']
                    total_duration = directions['total_duration_min']
                    route.route_polyline = directions['polyline']
                    route.waypoints_order = json.dumps(directions['waypoint_order'])
                    
                    # Reordenar según Google Maps si proporcionó un orden optimizado
                    if directions['waypoint_order'] and len(directions['waypoint_order']) > 0:
                        wp_order = directions['waypoint_order']
                        order_ids_list = sorted_orders_df['id'].tolist()
                        
                        if len(wp_order) == len(order_ids_list) - 1:
                            # Google Maps optimiza waypoints intermedios
                            reordered = [order_ids_list[i] for i in wp_order]
                            reordered.append(order_ids_list[-1])  # Destino final
                            order_ids = reordered
                    
                    # Calcular ETAs basados en los legs
                    current_time = datetime.utcnow().replace(hour=8, minute=0, second=0)
                    for i, leg in enumerate(directions['legs']):
                        duration_sec = leg['duration']['value']
                        current_time += timedelta(seconds=duration_sec)
                        # Agregar 10 minutos por descarga
                        current_time += timedelta(minutes=10)
                        
                        if i < len(order_ids):
                            order_obj = Order.query.get(order_ids[i] if isinstance(order_ids, list) else sorted_orders_df.iloc[i]['id'])
                            if order_obj:
                                order_obj.eta = current_time
                                
            except Exception as e:
                # Si falla Google Maps, usar distancia Haversine estimada
                total_distance = sorted_orders_df.get('distance_from_prev', pd.Series([0])).sum()
                total_duration = total_distance * 3  # Estimación: 3 min/km en ciudad
        else:
            total_distance = sorted_orders_df.get('distance_from_prev', pd.Series([0])).sum()
            total_duration = total_distance * 3
        
        route.total_distance_km = round(total_distance, 2)
        route.total_duration_min = round(total_duration, 2)
        
        # Asignar pedidos a la ruta
        for seq, order_id in enumerate(sorted_orders_df['id'].tolist(), 1):
            order_obj = Order.query.get(order_id)
            if order_obj:
                order_obj.route_id = route.id
                order_obj.sequence_order = seq
                order_obj.status = 'asignado'
        
        # Actualizar estado del conductor y vehículo
        driver.status = 'en_ruta'
        driver.vehicle_id = vehicle_id
        vehicle.status = 'en_ruta'
        
        driver_index += 1
        
        routes_created.append({
            'route_id': route.id,
            'route_name': route.name,
            'driver': driver.get_full_name(),
            'vehicle': vehicle.plate_number,
            'orders_count': len(order_ids),
            'total_weight_kg': round(total_weight, 2),
            'total_volume_m3': round(total_volume, 4),
            'weight_pct': weight_pct,
            'volume_pct': volume_pct,
            'distance_km': round(total_distance, 2),
            'duration_min': round(total_duration, 2)
        })
    
    db.session.commit()
    
    return {
        'success': True,
        'message': f'Se crearon {len(routes_created)} rutas exitosamente.',
        'routes_created': len(routes_created),
        'routes': routes_created
    }


def get_route_analytics():
    """
    Genera analíticas de las rutas usando Pandas para el dashboard del administrador.
    """
    routes = Route.query.all()
    
    if not routes:
        return {
            'total_routes': 0,
            'routes_by_status': {},
            'avg_capacity_weight': 0,
            'avg_capacity_volume': 0,
            'total_distance': 0,
            'total_duration': 0,
            'avg_orders_per_route': 0
        }
    
    data = []
    for route in routes:
        data.append({
            'id': route.id,
            'name': route.name,
            'status': route.status,
            'total_orders': route.total_orders or 0,
            'total_distance_km': route.total_distance_km or 0,
            'total_duration_min': route.total_duration_min or 0,
            'capacity_used_weight_pct': route.capacity_used_weight_pct or 0,
            'capacity_used_volume_pct': route.capacity_used_volume_pct or 0,
            'total_weight_kg': route.total_weight_kg or 0,
            'total_volume_m3': route.total_volume_m3 or 0,
            'date': route.date
        })
    
    df = pd.DataFrame(data)
    
    routes_by_status = df['status'].value_counts().to_dict()
    
    return {
        'total_routes': len(df),
        'routes_by_status': routes_by_status,
        'avg_capacity_weight': round(df['capacity_used_weight_pct'].mean(), 1),
        'avg_capacity_volume': round(df['capacity_used_volume_pct'].mean(), 1),
        'total_distance': round(df['total_distance_km'].sum(), 2),
        'total_duration': round(df['total_duration_min'].sum(), 2),
        'avg_orders_per_route': round(df['total_orders'].mean(), 1),
        'total_orders': int(df['total_orders'].sum()),
        'avg_distance_per_route': round(df['total_distance_km'].mean(), 2),
        'avg_duration_per_route': round(df['total_duration_min'].mean(), 2)
    }
