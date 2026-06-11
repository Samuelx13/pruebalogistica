import pytest
from models.user import User
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import create_app
from models import db

@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    with app.app_context():
        db.create_all()
        user = User(username='test', email='test@example.com', role='admin', first_name='Test', last_name='Admin', cedula='V-00000001')
        user.set_password('testpass')
        db.session.add(user)
        db.session.commit()
        yield app.test_client()
        db.session.rollback()
        db.drop_all()

def test_login_view(client):
    # GET login page
    rv = client.get('/login')
    assert b'LogiTrack' in rv.data
    assert b'username' in rv.data
    assert b'password' in rv.data

    # POST login success
    rv = client.post('/login', data=dict(
        username='test',
        password='testpass'
    ), follow_redirects=True)
    assert b'dashboard' in rv.data

    # Wrong login
    rv = client.post('/login', data=dict(
        username='test',
        password='wrong'
    ), follow_redirects=True)
    assert b'login' in rv.data

def test_register_view(client):
    rv = client.get('/register')
    assert b'register' in rv.data or b'registro' in rv.data

    # Test register with principal address/map data
    rv = client.post('/register', data=dict(
        username='newuser',
        email='new@example.com',
        first_name='New',
        last_name='User',
        phone='0412-0000000',
        cedula='V-99999999',
        principal_address='Test Principal Address',
        principal_lat='8.37',
        principal_lng='-62.67',
        password='newpass',
        confirm_password='newpass'
    ), follow_redirects=True)
    assert b'login' in rv.data
    
    # Verify principal data saved
    user = User.query.filter_by(username='newuser').first()
    assert user.principal_address == 'Test Principal Address'
    assert user.principal_lat == 8.37
    assert user.principal_lng == -62.67

def test_admin_order_lookup(client):
    # Login as admin
    client.post('/login', data=dict(username='test', password='testpass'))
    
    # Test cedula lookup (assumes service works)
    rv = client.get('/admin/api/user-by-cedula?cedula=V-12345678')
    data = rv.get_json()
    assert 'full_name' in data

def test_protected_route(client):
    rv = client.get('/admin/dashboard')
    assert b'login' in rv.data  # redirect to login

def test_api_stats(client):
    rv = client.get('/admin/api/stats')
    assert rv.status_code == 302  # login required
