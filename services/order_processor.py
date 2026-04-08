import pandas as pd
from models import db
from models.order import Order, generate_tracking_number
from services.geocoding import geocode_address


def process_orders_file(filepath):
    """
    Procesa un archivo CSV o Excel con datos de pedidos usando Pandas.
    
    Columnas esperadas:
    - cliente_nombre (obligatorio)
    - direccion (obligatorio)
    - peso_kg (obligatorio)
    - volumen_m3 (opcional, default 0.01)
    - telefono (opcional)
    - email (opcional)
    - ciudad (opcional)
    - estado (opcional)
    - codigo_postal (opcional)
    - descripcion (opcional)
    - instrucciones_especiales (opcional)
    
    Retorna un diccionario con resultados del procesamiento.
    """
    try:
        # Leer archivo según extensión
        if filepath.endswith('.csv'):
            df = pd.read_csv(filepath, encoding='utf-8')
        elif filepath.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(filepath)
        else:
            return {
                'success': False,
                'error': 'Formato de archivo no soportado. Use CSV o Excel (.xlsx/.xls).',
                'orders_created': 0,
                'orders_failed': 0,
                'details': []
            }

        # Limpiar nombres de columnas
        df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')

        # Verificar columnas obligatorias
        required_columns = ['cliente_nombre', 'direccion', 'peso_kg']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            return {
                'success': False,
                'error': f'Columnas obligatorias faltantes: {", ".join(missing_columns)}',
                'orders_created': 0,
                'orders_failed': 0,
                'details': []
            }

        # Limpiar datos
        df = df.dropna(subset=['cliente_nombre', 'direccion', 'peso_kg'])
        df['cliente_nombre'] = df['cliente_nombre'].astype(str).str.strip()
        df['direccion'] = df['direccion'].astype(str).str.strip()
        df['peso_kg'] = pd.to_numeric(df['peso_kg'], errors='coerce').fillna(1.0)
        
        if 'volumen_m3' in df.columns:
            df['volumen_m3'] = pd.to_numeric(df['volumen_m3'], errors='coerce').fillna(0.01)
        else:
            df['volumen_m3'] = 0.01

        orders_created = 0
        orders_failed = 0
        details = []

        for index, row in df.iterrows():
            try:
                # Geocodificar dirección
                geo_result = geocode_address(row['direccion'])
                
                order = Order(
                    tracking_number=generate_tracking_number(),
                    client_name=row['cliente_nombre'],
                    client_phone=str(row.get('telefono', '')).strip() if pd.notna(row.get('telefono')) else None,
                    client_email=str(row.get('email', '')).strip() if pd.notna(row.get('email')) else None,
                    address=row['direccion'],
                    city=str(row.get('ciudad', '')).strip() if pd.notna(row.get('ciudad')) else None,
                    state=str(row.get('estado', '')).strip() if pd.notna(row.get('estado')) else None,
                    zip_code=str(row.get('codigo_postal', '')).strip() if pd.notna(row.get('codigo_postal')) else None,
                    lat=geo_result.get('lat'),
                    lng=geo_result.get('lng'),
                    weight_kg=float(row['peso_kg']),
                    volume_m3=float(row['volumen_m3']),
                    description=str(row.get('descripcion', '')).strip() if pd.notna(row.get('descripcion')) else None,
                    special_instructions=str(row.get('instrucciones_especiales', '')).strip() if pd.notna(row.get('instrucciones_especiales')) else None,
                    status='en_almacen'
                )
                
                db.session.add(order)
                orders_created += 1
                details.append({
                    'row': index + 2,  # +2 por header y 0-index
                    'client': row['cliente_nombre'],
                    'address': row['direccion'],
                    'geocoded': geo_result.get('success', False),
                    'status': 'creado'
                })
                
            except Exception as e:
                orders_failed += 1
                details.append({
                    'row': index + 2,
                    'client': row.get('cliente_nombre', 'Desconocido'),
                    'address': row.get('direccion', 'Desconocida'),
                    'geocoded': False,
                    'status': f'error: {str(e)}'
                })

        db.session.commit()

        # Estadísticas con Pandas
        stats = {
            'total_weight_kg': round(df['peso_kg'].sum(), 2),
            'total_volume_m3': round(df['volumen_m3'].sum(), 4),
            'avg_weight_kg': round(df['peso_kg'].mean(), 2),
            'max_weight_kg': round(df['peso_kg'].max(), 2),
            'min_weight_kg': round(df['peso_kg'].min(), 2),
            'total_rows': len(df)
        }

        return {
            'success': True,
            'orders_created': orders_created,
            'orders_failed': orders_failed,
            'details': details,
            'stats': stats
        }

    except Exception as e:
        db.session.rollback()
        return {
            'success': False,
            'error': str(e),
            'orders_created': 0,
            'orders_failed': 0,
            'details': []
        }


def get_orders_dataframe(filters=None):
    """
    Obtiene un DataFrame de Pandas con los pedidos filtrados.
    Útil para análisis y generación de reportes.
    """
    query = Order.query
    
    if filters:
        if filters.get('status'):
            query = query.filter(Order.status == filters['status'])
        if filters.get('date_from'):
            query = query.filter(Order.created_at >= filters['date_from'])
        if filters.get('date_to'):
            query = query.filter(Order.created_at <= filters['date_to'])
        if filters.get('route_id'):
            query = query.filter(Order.route_id == filters['route_id'])
        if filters.get('unassigned'):
            query = query.filter(Order.route_id.is_(None))
    
    orders = query.all()
    
    if not orders:
        return pd.DataFrame()
    
    data = []
    for order in orders:
        data.append({
            'id': order.id,
            'tracking_number': order.tracking_number,
            'client_name': order.client_name,
            'address': order.address,
            'lat': order.lat,
            'lng': order.lng,
            'weight_kg': order.weight_kg,
            'volume_m3': order.volume_m3,
            'status': order.status,
            'route_id': order.route_id,
            'sequence_order': order.sequence_order,
            'created_at': order.created_at
        })
    
    return pd.DataFrame(data)
