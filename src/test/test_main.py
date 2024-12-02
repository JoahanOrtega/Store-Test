import pytest
from flask import Flask
from api.extensions import db
from api.models import UserModel
from flask_restful import Api
import json

@pytest.fixture
def app():
    app = Flask(__name__)
    app.config.update({
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
        'TESTING': True
    })
    
    api = Api(app)
    db.init_app(app)
    
    # Register resources
    from api.controllers import Users
    api.add_resource(Users, '/api/users', '/api/users/<int:user_id>')
    
    return app

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def init_database(app):
    with app.app_context():
        db.create_all()
        
        # Create test user
        test_user = UserModel(
            username="testuser1",
            email="test1@example.com"
        )
        test_user.set_password("password123")
        db.session.add(test_user)
        db.session.commit()
        
        yield db
        
        db.session.remove()
        db.drop_all()

def test_create_user_success(client, init_database):
    with client.application.app_context():
        response = client.post('/api/users', json={
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'password789'
        })
        
        assert response.status_code == 201
        data = json.loads(response.data)
        assert 'user' in data
        assert data['user']['username'] == 'newuser'
        assert data['user']['email'] == 'newuser@example.com'

def test_get_user(client, init_database):
    with client.application.app_context():
        # First get the test user we created in init_database
        response = client.get('/api/users/1')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['username'] == 'testuser1'
        assert data['email'] == 'test1@example.com'

def test_create_user_missing_email(client, init_database):
    with client.application.app_context():
        response = client.post('/api/users', json={
            'username': 'testuser',
            'password': 'password123'
        })
        assert response.status_code == 400
        data = json.loads(response.data)
        
        # Ensure 'message' is a dictionary
        assert 'message' in data
        assert isinstance(data['message'], dict)
        
        # Check if 'email' has the correct error message
        assert 'email' in data['message']
        assert data['message']['email'].lower() == "email is required"

def test_create_user_duplicate_email(client, init_database):
    with client.application.app_context():
        response = client.post('/api/users', json={
            'username': 'differentuser',
            'email': 'test1@example.com',  # This email already exists
            'password': 'password123'
        })
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'email already exists' in data['message'].lower()

def test_create_user_invalid_email_format(client, init_database):
    invalid_email_cases = [
        'plainaddress',           # Missing @ and domain
        '@missinglocal.com',     # Missing local part
        'missing@domain',         # Incomplete domain
        'missing.domain.com',     # Missing @
        'multiple@@@domain.com',  # Multiple @
        'invalid@domain@com',     # Multiple @
        'invalid@.com',          # Missing domain name
        'invalid@com.',          # Trailing dot in domain
        '.invalid@domain.com',   # Leading dot in local part
        'invalid..email@domain.com',  # Consecutive dots
        'email@domain..com',     # Consecutive dots in domain
        'email@-domain.com',     # Domain starting with hyphen
        'email@[123.123.123.123]', # IP address format not supported
        'email@domain.com.',     # Trailing dot
    ]
    
    with client.application.app_context():
        for i, invalid_email in enumerate(invalid_email_cases):
            unique_username = f'invalid_test_user_{i}'  # Make sure username is unique
            response = client.post('/api/users', json={
                'username': unique_username,
                'email': invalid_email,
                'password': 'password123'
            })
            assert response.status_code == 400, f"Failed for email: {invalid_email}"
            data = json.loads(response.data)
            assert 'message' in data
            assert 'Invalid email format' in data['message'], f"Expected 'Invalid email format' but got '{data['message']}' for email: {invalid_email}"

def test_create_user_valid_email_format(client, init_database):
    valid_email_cases = [
        'simple@example.com',
        'very.common@example.com',
        'disposable.style.email.with+symbol@example.com',
        'other.email-with-hyphen@example.com',
        'fully-qualified-domain@example.com',
        'user.name+tag+sorting@example.com',
        'x@example.com',
        'example-indeed@strange-example.com',
        'test.email+bob@example.com',
        '123@example.com',
        'test-email@example.co.uk'
    ]
    
    with client.application.app_context():
        for i, valid_email in enumerate(valid_email_cases):
            unique_username = f'valid_test_user_{i}'  # Make sure username is unique
            response = client.post('/api/users', json={
                'username': unique_username,
                'email': valid_email,
                'password': 'password123'
            })
            assert response.status_code == 201, f"Failed for email: {valid_email}"
            data = json.loads(response.data)
            assert 'message' in data
            assert 'User created successfully' in data['message']

def test_create_user_missing_username(client, init_database):
    with client.application.app_context():
        response = client.post('/api/users', json={
            'email': 'test@example.com',
            'password': 'password123'
        })
        assert response.status_code == 400
        data = json.loads(response.data)
        
        # Check if 'message' exists and is a dictionary
        assert 'message' in data
        assert isinstance(data['message'], dict)
        
        # Check if the 'username' field has the correct error message
        assert 'username' in data['message']
        assert data['message']['username'].lower() == "username is required"

def test_create_user_empty_username(client, init_database):
    with client.application.app_context():
        response = client.post('/api/users', json={
            'username': '',  # Empty username
            'email': 'test@example.com',
            'password': 'password123'
        })
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'message' in data
        assert isinstance(data['message'], str), "Message should be a string"
        assert 'username is required' in data['message'].lower()

def test_create_user_whitespace_username(client, init_database):
    with client.application.app_context():
        response = client.post('/api/users', json={
            'username': '   ',  # Whitespace username
            'email': 'test@example.com',
            'password': 'password123'
        })
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'message' in data
        assert isinstance(data['message'], str), "Message should be a string"
        assert 'username is required' in data['message'].lower()

def test_get_nonexistent_user(client, init_database):
    with client.application.app_context():
        response = client.get('/api/users/999')
        assert response.status_code == 404

    with client.application.app_context():
        response = client.post('/api/users', json={
            'username': 'testuser1',  # This username already exists
            'email': 'different@example.com',
            'password': 'password789'
        })
        assert response.status_code == 400

def test_create_user_short_password(client, init_database):
    with client.application.app_context():
        response = client.post('/api/users', json={
            'username': 'testuser',
            'email': 'test@example.com',
            'password': '12345'  # Less than 6 characters
        })
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'password must be at least 6 characters' in data['message'].lower()

def test_create_user_missing_password(client, init_database):
    with client.application.app_context():
        response = client.post('/api/users', json={
            'username': 'testuser',
            'email': 'test@example.com'
        })
        assert response.status_code == 400
        data = json.loads(response.data)
        
        # Ensure 'message' is a dictionary
        assert 'message' in data
        assert isinstance(data['message'], dict)
        
        # Check if 'password' has the correct error message
        assert 'password' in data['message']
        assert data['message']['password'].lower() == "password is required"

def test_update_user_success(client, init_database):
    with client.application.app_context():
        response = client.put('/api/users/1', json={
            'username': 'updateduser',
            'email': 'updated@example.com',
            'password': 'newpassword123'
        })
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        # Check if the response contains the expected message
        assert 'message' in data
        assert data['message'] == 'User updated successfully'
        
        # Check the nested user object
        assert 'user' in data
        assert data['user']['username'] == 'updateduser'
        assert data['user']['email'] == 'updated@example.com'
        assert data['user']['id'] == 1

def test_delete_user_success(client, init_database):
    with client.application.app_context():
        # First verify the user exists
        response = client.get('/api/users/1')
        assert response.status_code == 200
        
        # Delete the user
        response = client.delete('/api/users/1')
        assert response.status_code == 200
        
        # Verify the user no longer exists
        response = client.get('/api/users/1')
        assert response.status_code == 404

def test_delete_nonexistent_user(client, init_database):
    with client.application.app_context():
        response = client.delete('/api/users/999')
        assert response.status_code == 404