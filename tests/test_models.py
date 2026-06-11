import pytest
from models.user import User
from models.order import Order
from models.vehicle import Vehicle
from models.driver import Driver
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import create_app
from models import db

@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()

def test_user_password_hashing(app):
    with app.app_context():
        user = User(username='test', email='test@example.com', role='cliente', first_name='Test', last_name='User', cedula='V-00000000')
        user.set_password('testpass')
        assert user.check_password('testpass') is True
        assert user.check_password('wrong') is False

def test_order_validation(app):
    with app.app_context():
        order = Order(
            tracking_number='TEST-001',
            client_name='Test Client',
            address='Test Address',
            lat=8.37,
            lng=-62.67,
            weight_kg=10.0,
            volume_m3=0.5,
            status='en_almacen'
        )
        db.session.add(order)
        db.session.commit()
        assert order.id is not None

def test_vehicle_status(app):
    with app.app_context():
        vehicle = Vehicle(
            plate_number='TEST-001',
            brand='Test',
            model='Model',
            year=2024,
            max_weight_kg=1000,
            max_volume_m3=10,
            status='disponible'
        )
        db.session.add(vehicle)
        db.session.commit()
        saved_vehicle = Vehicle.query.get(vehicle.id)
        assert saved_vehicle.status == 'disponible'

def test_driver_relationship(app):
    from models.user import User
    with app.app_context():
        user = User(username='driver_test', email='driver@test.com', role='conductor', first_name='Driver', last_name='Test', cedula='V-11111111')
        user.set_password('pass')
        db.session.add(user)
        db.session.flush()
        vehicle = Vehicle(plate_number='D-TEST', brand='Test', model='Model', year=2024, max_weight_kg=1000, max_volume_m3=10, status='disponible')
        db.session.add(vehicle)
        db.session.flush()
        driver = Driver(user_id=user.id, vehicle_id=vehicle.id, license_number='LIC-TEST', status='disponible')
        db.session.add(driver)
        db.session.commit()
        saved_driver = Driver.query.first()
        assert saved_driver.user.username == 'driver_test'

def test_user_cedula_unique(app):
    with app.app_context():
        user1 = User(username='test1', email='test1@test.com', cedula='V-12345678', first_name='Test', last_name='User', role='cliente')
        user1.set_password('pass')
        db.session.add(user1)
        db.session.flush()
        
# Duplicate cedula should fail
        user2 = User(username='test2', email='test2@test.com', cedula='V-12345678', first_name='Test2', last_name='User2', role='cliente')
        user2.set_password('pass')
        db.session.add(user2)
        
        with pytest.raises(Exception):
            db.session.commit()
        
        db.session.rollback()
        
        # Principal fields
        user3 = User(username='test3', email='test3@test.com', cedula='V-87654321', first_name='Test3', last_name='User3', 
                     principal_address='Test Addr', principal_lat=8.37, principal_lng=-62.67, role='cliente')
        user3.set_password('pass')
        db.session.add(user3)
        db.session.commit()
        assert user3.principal_address == 'Test Addr'
        assert user3.principal_lat == 8.37
        assert user3.principal_lng == -62.67

