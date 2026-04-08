import requests
from config import Config


def geocode_address(address):
    """
    Geocodifica una dirección usando la API de Google Maps.
    Retorna un diccionario con lat, lng y dirección formateada.
    """
    try:
        url = 'https://maps.googleapis.com/maps/api/geocode/json'
        params = {
            'address': address,
            'key': Config.GOOGLE_MAPS_API_KEY,
            'language': 'es'
        }
        response = requests.get(url, params=params, timeout=10)
        data = response.json()

        if data['status'] == 'OK' and len(data['results']) > 0:
            result = data['results'][0]
            location = result['geometry']['location']
            return {
                'lat': location['lat'],
                'lng': location['lng'],
                'formatted_address': result['formatted_address'],
                'success': True
            }
        else:
            return {
                'lat': None,
                'lng': None,
                'formatted_address': address,
                'success': False,
                'error': data.get('status', 'UNKNOWN_ERROR')
            }
    except Exception as e:
        return {
            'lat': None,
            'lng': None,
            'formatted_address': address,
            'success': False,
            'error': str(e)
        }


def get_distance_matrix(origins, destinations):
    """
    Obtiene la matriz de distancias y tiempos entre orígenes y destinos
    usando la API de Google Maps Distance Matrix.
    
    origins: lista de tuplas (lat, lng)
    destinations: lista de tuplas (lat, lng)
    """
    try:
        url = 'https://maps.googleapis.com/maps/api/distancematrix/json'
        
        origins_str = '|'.join([f"{lat},{lng}" for lat, lng in origins])
        destinations_str = '|'.join([f"{lat},{lng}" for lat, lng in destinations])
        
        params = {
            'origins': origins_str,
            'destinations': destinations_str,
            'key': Config.GOOGLE_MAPS_API_KEY,
            'language': 'es',
            'units': 'metric'
        }
        
        response = requests.get(url, params=params, timeout=15)
        data = response.json()

        if data['status'] == 'OK':
            return {
                'rows': data['rows'],
                'success': True
            }
        else:
            return {
                'rows': [],
                'success': False,
                'error': data.get('status', 'UNKNOWN_ERROR')
            }
    except Exception as e:
        return {
            'rows': [],
            'success': False,
            'error': str(e)
        }


def get_directions(origin, destination, waypoints=None):
    """
    Obtiene las direcciones de ruta entre origen y destino con paradas intermedias.
    
    origin: tupla (lat, lng)
    destination: tupla (lat, lng)
    waypoints: lista de tuplas (lat, lng) - paradas intermedias
    """
    try:
        url = 'https://maps.googleapis.com/maps/api/directions/json'
        
        params = {
            'origin': f"{origin[0]},{origin[1]}",
            'destination': f"{destination[0]},{destination[1]}",
            'key': Config.GOOGLE_MAPS_API_KEY,
            'language': 'es',
            'units': 'metric',
            'optimize': 'true'
        }
        
        if waypoints and len(waypoints) > 0:
            waypoints_str = '|'.join([f"{lat},{lng}" for lat, lng in waypoints])
            params['waypoints'] = f"optimize:true|{waypoints_str}"
        
        response = requests.get(url, params=params, timeout=15)
        data = response.json()

        if data['status'] == 'OK' and len(data['routes']) > 0:
            route = data['routes'][0]
            legs = route['legs']
            
            total_distance = sum(leg['distance']['value'] for leg in legs) / 1000  # km
            total_duration = sum(leg['duration']['value'] for leg in legs) / 60  # minutos
            
            waypoint_order = route.get('waypoint_order', [])
            
            return {
                'legs': legs,
                'total_distance_km': round(total_distance, 2),
                'total_duration_min': round(total_duration, 2),
                'polyline': route['overview_polyline']['points'],
                'waypoint_order': waypoint_order,
                'success': True
            }
        else:
            return {
                'legs': [],
                'total_distance_km': 0,
                'total_duration_min': 0,
                'polyline': '',
                'waypoint_order': [],
                'success': False,
                'error': data.get('status', 'UNKNOWN_ERROR')
            }
    except Exception as e:
        return {
            'legs': [],
            'total_distance_km': 0,
            'total_duration_min': 0,
            'polyline': '',
            'waypoint_order': [],
            'success': False,
            'error': str(e)
        }
