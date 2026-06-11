"""
Script de inicialización de la base de datos con datos de prueba.
Ejecutar: python init_db.py
"""

from app import create_app
from models import db
from models.user import User
from models.vehicle import Vehicle
from models.driver import Driver
from models.order import Order, generate_tracking_number
from datetime import datetime


def init_database():
    app = create_app()

    with app.app_context():
        # Crear todas las tablas
        db.create_all()
        print("✅ Tablas creadas exitosamente.")

        # Verificar si ya hay datos
        if User.query.first():
            print("⚠️  La base de datos ya contiene datos. Omitiendo inserción de datos de prueba.")
            return

        # ==================== USUARIOS ====================
        print("📝 Creando usuarios de prueba...")

        # Administrador
        admin = User(
            username='admin',
            email='admin@logitrack.com',
            first_name='Carlos',
            last_name='Mendoza',
            phone='0412-1234567',
            role='admin'
        )
        admin.set_password('admin123')
        db.session.add(admin)

        # Conductores
        conductor1_user = User(
            username='conductor1',
            email='conductor1@logitrack.com',
            first_name='José',
            last_name='Rodríguez',
            phone='0414-7654321',
            role='conductor'
        )
        conductor1_user.set_password('conductor123')
        db.session.add(conductor1_user)

        conductor2_user = User(
            username='conductor2',
            email='conductor2@logitrack.com',
            first_name='María',
            last_name='González',
            phone='0416-9876543',
            role='conductor'
        )
        conductor2_user.set_password('conductor123')
        db.session.add(conductor2_user)

        conductor3_user = User(
            username='conductor3',
            email='conductor3@logitrack.com',
            first_name='Pedro',
            last_name='Martínez',
            phone='0424-1112233',
            role='conductor'
        )
        conductor3_user.set_password('conductor123')
        db.session.add(conductor3_user)

# Clientes con cédula y dirección principal
        cliente1 = User(
            username='cliente1',
            email='cliente1@email.com',
            first_name='Ana',
            last_name='López',
            cedula='V-12345678',
            phone='0412-5551234',
            principal_address='C.C. Orinoco Mall, Puerto Ordaz, Ciudad Guayana, Bolívar, Venezuela',
            principal_lat=8.3200,
            principal_lng=-62.6800,
            role='cliente'
        )
        cliente1.set_password('cliente123')
        db.session.add(cliente1)

        cliente2 = User(
            username='cliente2',
            email='cliente2@email.com',
            first_name='Luis',
            last_name='Hernández',
            cedula='E-87654321',
            phone='0414-5555678',
            principal_address='Av. Guayana 123, Puerto Ordaz, Ciudad Guayana, Bolívar',
            principal_lat=8.3500,
            principal_lng=-62.6500,
            role='cliente'
        )
        cliente2.set_password('cliente123')
        db.session.add(cliente2)

        cliente3 = User(
            username='cliente3',
            email='cliente3@email.com',
            first_name='María',
            last_name='García',
            cedula='V-11223344',
            phone='0416-7778899',
            principal_address='Zona Industrial Mata Oral, Puerto Ordaz, Ciudad Guayana',
            principal_lat=8.3600,
            principal_lng=-62.6400,
            role='cliente'
        )
        cliente3.set_password('cliente123')
        db.session.add(cliente3)

        db.session.flush()
        print(f"   ✅ {User.query.count()} usuarios creados.")

        # ==================== VEHÍCULOS ====================
        print("🚛 Creando vehículos de prueba...")

        vehicles_data = [
            {
                'plate_number': 'ABC-123',
                'brand': 'Toyota',
                'model': 'Hilux',
                'year': 2022,
                'max_weight_kg': 1200.0,
                'max_volume_m3': 8.0,
                'fuel_type': 'Gasolina',
                'status': 'disponible'
            },
            {
                'plate_number': 'DEF-456',
                'brand': 'Ford',
                'model': 'F-150',
                'year': 2021,
                'max_weight_kg': 1500.0,
                'max_volume_m3': 12.0,
                'fuel_type': 'Diésel',
                'status': 'disponible'
            },
            {
                'plate_number': 'GHI-789',
                'brand': 'Chevrolet',
                'model': 'NPR',
                'year': 2023,
                'max_weight_kg': 3000.0,
                'max_volume_m3': 20.0,
                'fuel_type': 'Diésel',
                'status': 'disponible'
            },
            {
                'plate_number': 'JKL-012',
                'brand': 'Hyundai',
                'model': 'HD65',
                'year': 2020,
                'max_weight_kg': 2500.0,
                'max_volume_m3': 15.0,
                'fuel_type': 'Diésel',
                'status': 'mantenimiento'
            }
        ]

        for v_data in vehicles_data:
            vehicle = Vehicle(**v_data)
            db.session.add(vehicle)

        db.session.flush()
        print(f"   ✅ {Vehicle.query.count()} vehículos creados.")

        # ==================== CONDUCTORES ====================
        print("👤 Creando perfiles de conductores...")

        vehicles = Vehicle.query.filter_by(status='disponible').all()

        driver1 = Driver(
            user_id=conductor1_user.id,
            vehicle_id=vehicles[0].id if len(vehicles) > 0 else None,
            license_number='LIC-001-2022',
            status='disponible'
        )
        db.session.add(driver1)

        driver2 = Driver(
            user_id=conductor2_user.id,
            vehicle_id=vehicles[1].id if len(vehicles) > 1 else None,
            license_number='LIC-002-2021',
            status='disponible'
        )
        db.session.add(driver2)

        driver3 = Driver(
            user_id=conductor3_user.id,
            vehicle_id=vehicles[2].id if len(vehicles) > 2 else None,
            license_number='LIC-003-2023',
            status='disponible'
        )
        db.session.add(driver3)

        db.session.flush()
        print(f"   ✅ {Driver.query.count()} conductores creados.")

        # ==================== PEDIDOS ====================
        print("📦 Creando pedidos de prueba...")

        orders_data = [
            {
                'client_name': 'Ana López',
                'client_phone': '0412-5551234',
                'client_email': 'cliente1@email.com',
                'client_user_id': cliente1.id,
'address': 'C.C. Orinoco Mall, Puerto Ordaz, Ciudad Guayana, Bolívar, Venezuela',  # Local Guayana'
'lat': 8.3200,  # Orinoco Mall Puerto Ordaz'
'lng': -62.6800,  # Orinoco Mall Puerto Ordaz'
                'weight_kg': 5.0,
                'volume_m3': 0.03,
                'description': 'Caja de electrónicos',
                'special_instructions': 'Frágil - Manejar con cuidado',
                'status': 'en_almacen'
            },
            {
                'client_name': 'Luis Hernández',
                'client_phone': '0414-5555678',
                'client_email': 'cliente2@email.com',
                'client_user_id': cliente2.id,
'address': 'Av. Guayana, Puerto Ordaz, Ciudad Guayana, Bolívar',  # Local Guayana'
'lat': 8.3500,  # Av. Guayana Puerto Ordaz'
'lng': -62.6500,  # Av. Guayana Puerto Ordaz'
                'weight_kg': 12.0,
                'volume_m3': 0.08,
                'description': 'Paquete de ropa',
                'status': 'en_almacen'
            },
            {
                'client_name': 'Roberto Díaz',
                'client_phone': '0416-3334455',
                'address': 'Calle Los Palos Grandes, Caracas, Venezuela',
'lat': 8.3400,  # C.C. Cachamay Puerto Ordaz'
'lng': -62.6600,  # C.C. Cachamay Puerto Ordaz'
                'weight_kg': 3.5,
                'volume_m3': 0.02,
                'description': 'Documentos importantes',
                'special_instructions': 'Entregar solo al titular',
                'status': 'en_almacen'
            },
            {
                'client_name': 'Carmen Suárez',
                'client_phone': '0424-6667788',
'address': 'Zona Industrial Mata Oral, Puerto Ordaz, Ciudad Guayana, Bolívar',  # Local Guayana'
'lat': 8.3600,  # Mata Oral Puerto Ordaz'
'lng': -62.6400,  # Mata Oral Puerto Ordaz'
                'weight_kg': 25.0,
                'volume_m3': 0.15,
                'description': 'Cajas de suministros de oficina',
                'status': 'en_almacen'
            },
            {
                'client_name': 'Miguel Torres',
                'client_phone': '0412-9990011',
'address': 'Mercado de San Félix, San Félix, Ciudad Guayana, Bolívar',  # Local Guayana'
'lat': 8.3000,  # Mercado San Félix'
'lng': -62.6600,  # Mercado San Félix'
                'weight_kg': 8.0,
                'volume_m3': 0.05,
                'description': 'Repuestos automotrices',
                'status': 'en_almacen'
            },
            {
                'client_name': 'Patricia Morales',
                'client_phone': '0414-2223344',
'address': 'Universidad de Oriente - Núcleo Bolívar, Puerto Ordaz',  # Local Guayana'
'lat': 8.3300,  # UDO Núcleo Bolívar'
'lng': -62.6700,  # UDO Núcleo Bolívar'
                'weight_kg': 15.0,
                'volume_m3': 0.10,
                'description': 'Equipos de computación',
                'special_instructions': 'Llamar antes de llegar',
                'status': 'en_almacen'
            },
            {
                'client_name': 'Fernando Rivas',
                'client_phone': '0416-7778899',
'address': 'Av. Principal de Upata, Upata, Bolívar',  # Local Guayana'
                'lat': 10.4940,
                'lng': -66.8830,
                'weight_kg': 2.0,
                'volume_m3': 0.01,
                'description': 'Sobre con documentos',
                'status': 'en_almacen'
            },
            {
                'client_name': 'Gabriela Pérez',
                'client_phone': '0424-1114455',
                'address': 'Av. Principal de Las Mercedes, Caracas, Venezuela',
                'lat': 10.4830,
                'lng': -66.8600,
                'weight_kg': 20.0,
                'volume_m3': 0.12,
                'description': 'Muebles pequeños',
                'special_instructions': 'Subir al piso 3',
                'status': 'en_almacen'
            },
            {
                'client_name': 'Andrés Vargas',
                'client_phone': '0412-3336677',
                'address': 'Av. Río de Janeiro, Las Mercedes, Caracas, Venezuela',
                'lat': 10.4810,
                'lng': -66.8580,
                'weight_kg': 7.5,
                'volume_m3': 0.04,
                'description': 'Productos alimenticios',
                'special_instructions': 'Mantener refrigerado',
                'status': 'en_almacen'
            },
            {
                'client_name': 'Sofía Ramírez',
                'client_phone': '0414-8889900',
                'address': 'Av. Principal de Chuao, Caracas, Venezuela',
                'lat': 10.4870,
                'lng': -66.8520,
                'weight_kg': 10.0,
                'volume_m3': 0.06,
                'description': 'Material de construcción',
                'status': 'en_almacen'
            },
            {
                'client_name': 'Diego Castillo',
                'client_phone': '0416-4445566',
                'address': 'Av. La Estancia, Chuao, Caracas, Venezuela',
                'lat': 10.4890,
                'lng': -66.8500,
                'weight_kg': 30.0,
                'volume_m3': 0.20,
                'description': 'Electrodomésticos',
                'special_instructions': 'Requiere dos personas para descarga',
                'status': 'en_almacen'
            },
            {
                'client_name': 'Valentina Flores',
                'client_phone': '0424-5556677',
                'address': 'Av. Andrés Bello, Los Palos Grandes, Caracas, Venezuela',
                'lat': 10.4990,
                'lng': -66.8460,
                'weight_kg': 4.0,
                'volume_m3': 0.02,
                'description': 'Paquete de cosméticos',
                'status': 'en_almacen'
            }
        ]

        for o_data in orders_data:
            order = Order(
                tracking_number=generate_tracking_number(),
                **o_data
            )
            db.session.add(order)

        db.session.commit()
        print(f"   ✅ {Order.query.count()} pedidos creados.")

        # ==================== RESUMEN ====================
        print("\n" + "=" * 50)
        print("🎉 Base de datos inicializada exitosamente!")
        print("=" * 50)
        print(f"\n📊 Resumen:")
        print(f"   👥 Usuarios: {User.query.count()}")
        print(f"   🚛 Vehículos: {Vehicle.query.count()}")
        print(f"   👤 Conductores: {Driver.query.count()}")
        print(f"   📦 Pedidos: {Order.query.count()}")
        print(f"\n🔑 Credenciales de acceso:")
        print(f"   Admin:     admin / admin123")
        print(f"   Conductor: conductor1 / conductor123")
        print(f"   Conductor: conductor2 / conductor123")
        print(f"   Conductor: conductor3 / conductor123")
        print(f"   Cliente:   cliente1 / cliente123")
        print(f"   Cliente:   cliente2 / cliente123")
        print(f"\n🌐 Ejecute: python app.py")
        print(f"   Abra: http://localhost:5000")


if __name__ == '__main__':
    init_database()
