from models.user import User

def lookup_user_by_cedula(cedula):
    """Busca usuario por cédula de identidad."""
    if not cedula:
        return None
    
    user = User.query.filter_by(cedula=cedula.strip().upper()).first()
    if user:
        return {
            'id': user.id,
            'username': user.username,
            'full_name': user.get_full_name(),
            'email': user.email,
            'phone': user.phone,
            'address': user.principal_address,
            'lat': user.principal_lat,
            'lng': user.principal_lng
        }
    return None

