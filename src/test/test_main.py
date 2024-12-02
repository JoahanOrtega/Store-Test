import pytest
from flask import Flask
from api.extensions import db
from api.models import UserModel, CategoryModel, ProductModel
from api.controllers import Users, Categories, Products
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
    api.add_resource(Users, '/api/users', '/api/users/<int:user_id>')
    api.add_resource(Categories, '/api/categories', '/api/categories/<int:category_id>')
    api.add_resource(Products, '/api/products', '/api/products/<int:product_id>')
    
    return app

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def init_database(app):
    with app.app_context():
        db.create_all()
        
        # Helper function to create a test user
        def create_test_user(username, email, password):
            user = UserModel(
                username=username,
                email=email
            )
            user.set_password(password)
            db.session.add(user)
        
        # Helper function to create a test category
        def create_test_category(name, description):
            category = CategoryModel(
                name=name,
                description=description
            )
            db.session.add(category)

        # Helper function to create a test Product
        def create_test_product(name, price, description, stock, category_id):
            product = ProductModel(
                name=name,
                price=price,
                description=description,
                stock=stock,
                category_id = category_id
            )
            db.session.add(product)
        
        # Add initial data
        create_test_user("testuser1", "test1@example.com", "password123")
        create_test_category("Electronics", "Electronic devices and accessories")
        create_test_category("Sports", "Sports equipment and accessories")
        create_test_product("Smartphone", 699.99, "Latest model smartphone", 50, 1)
        create_test_product("Laptop", 1499.99, "Latest model laptop", 25, 1)
        
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

def test_create_category_success_with_description(client, init_database):
    """Test creating category with name and description"""
    response = client.post('/api/categories', json={
        'name': 'Books',
        'description': 'Books and magazines'
    })
    
    assert response.status_code == 201
    data = json.loads(response.data)
    assert data == {
        'message': 'Category created successfully',
        'category': {
            'id': 3,
            'name': 'Books'
        }
    }

def test_create_category_success_without_description(client, init_database):
    """Test creating category with only name"""
    response = client.post('/api/categories', json={
        'name': 'Games'
    })
    
    assert response.status_code == 201
    data = json.loads(response.data)
    assert data == {
        'message': 'Category created successfully',
        'category': {
            'id': 3,
            'name': 'Games'
        }
    }

def test_create_category_duplicate_name(client, init_database):
    """Test creating category with duplicate name"""
    response = client.post('/api/categories', json={
        'name': 'Electronics',
        'description': 'Another description'
    })
    
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data == {
        'message': 'Category with this name already exists'
    }

def test_create_category_missing_name(client, init_database):
    """Test creating category without name"""
    response = client.post('/api/categories', json={
        'description': 'Test Description'
    })
    
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data == {
        'message': {
            'name': 'Category name cannot be blank'
        }
    }

def test_get_all_categories(client, init_database):
    """Test getting all categories"""
    response = client.get('/api/categories')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'categories' in data
    categories = data['categories']
    assert len(categories) == 2
    assert categories[0] == {
        'id': 1,
        'name': 'Electronics',
        'description': 'Electronic devices and accessories',
        'product_count': 2
    }

def test_get_single_category(client, init_database):
    """Test getting a single category"""
    response = client.get('/api/categories/1')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data == {
        'id': 1,
        'name': 'Electronics',
        'description': 'Electronic devices and accessories',
        'products': [
            {
                'id': 1,
                'name': 'Smartphone',
                'price': 699.99,
            },
            {
                'id': 2,
                'name': 'Laptop',
                'price': 1499.99,
            },
        ],
    }

def test_get_nonexistent_category(client, init_database):
    """Test getting a category that doesn't exist"""
    response = client.get('/api/categories/999')
    
    assert response.status_code == 404
    data = json.loads(response.data)
    assert data == {
        'message': 'CategoryModel with id 999 not found'
    }

def test_update_category_success(client, init_database):
    """Test successful category update"""
    response = client.put('/api/categories/1', json={
        'name': 'Updated Electronics',
        'description': 'Updated Description'
    })
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data == {
        'message': 'Category updated successfully'
    }

def test_update_nonexistent_category(client, init_database):
    """Test updating a nonexistent category"""
    response = client.put('/api/categories/999', json={
        'name': 'Updated Category',
        'description': 'Updated Description'
    })
    
    assert response.status_code == 404
    data = json.loads(response.data)
    assert data == {
        'message': 'CategoryModel with id 999 not found'
    }

def test_delete_category_success(client, init_database):
    """Test successful category deletion"""
    response = client.delete('/api/categories/2')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data == {
        'message': 'Category deleted successfully'
    }

def test_delete_nonexistent_category(client, init_database):
    """Test deleting a nonexistent category"""
    response = client.delete('/api/categories/999')
    
    assert response.status_code == 404
    data = json.loads(response.data)
    assert data == {
        'message': 'CategoryModel with id 999 not found'
    }

# def test_delete_category_with_products(client, init_database):
#     """Test deleting a category that has associated products"""
#     with client.application.app_context():
#         # Create a product associated with the category
#         product = ProductModel(
#             name="Test Product",
#             price=99.99,
#             category_id=1
#         )
#         db.session.add(product)
#         db.session.commit()

#         response = client.delete('/api/categories/1')
#         assert response.status_code == 400
#         data = json.loads(response.data)
#         assert data == {
#             'message': 'Cannot delete category with associated products'
#         }

# GET Test
def test_get_all_products(client, init_database):
    """Test getting all products"""
    response = client.get('/api/products')
    
    assert response.status_code == 200
    expected_data = {
        "products": [
            {
                "id": 1,
                "name": "Smartphone",
                "price": 699.99,
                "description": "Latest model smartphone",
                "stock": 50
            },
            {
                "id": 2,
                "name": "Laptop",
                "price": 1499.99,
                "description": "Latest model laptop",
                "stock": 25
            },
        ]
    }
    assert response.json == expected_data

def test_get_single_product(client, init_database):
    """Test getting a single product"""
    response = client.get('/api/products/1')
    
    assert response.status_code == 200
    data = response.json
    # print("Actual response:", data)
    expected_data = {
        "id": 1,
        "name": "Smartphone",
        "price": 699.99,
        "description": "Latest model smartphone",
        "stock": 50,
        "category_id": 1
    }
    assert data == expected_data

def test_get_nonexistent_product(client, init_database):
    """Test getting a nonexistent product"""
    response = client.get('/api/products/999')
    assert response.status_code == 404
    assert response.json == {"message": "ProductModel with id 999 not found"}

# POST Tests
def test_create_product_success(client, init_database):
    """Test successful product creation"""
    response = client.post('/api/products', json={
        'name': 'New Product',
        'price': 199.99,
        'description': 'New Description',
        'stock': 20,
        'category_id': 1
    })
    
    assert response.status_code == 201
    assert 'message' in response.json
    assert 'id' in response.json
    assert response.json['message'] == 'Product created successfully'
    assert isinstance(response.json['id'], int)

def test_create_product_missing_name(client, init_database):
    """Test creating product without name"""
    response = client.post('/api/products', json={
        'price': 199.99,
        'description': 'New Description',
        'stock': 20,
        'category_id': 1
    })
    
    assert response.status_code == 400
    assert response.json == {"message": {"name": "Name cannot be blank"}}

def test_create_product_missing_price(client, init_database):
    """Test creating product without price"""
    response = client.post('/api/products', json={
        'name': 'New Product',
        'description': 'New Description',
        'stock': 20,
        'category_id': 1
    })
    
    assert response.status_code == 400
    assert response.json == {"message": {"price": "Price must be provided"}}

def test_create_product_short_name(client, init_database):
    """Test creating product with too short name"""
    response = client.post('/api/products', json={
        'name': 'ab',  # Less than 3 characters
        'price': 199.99,
        'description': 'New Description',
        'stock': 20,
        'category_id': 1
    })
    
    assert response.status_code == 400
    assert response.json == {"message": "Product name must be at least 3 characters long"}

def test_create_product_long_name(client, init_database):
    """Test creating product with too long name"""
    response = client.post('/api/products', json={
        'name': 'a' * 101,  # More than 100 characters
        'price': 199.99,
        'description': 'New Description',
        'stock': 20,
        'category_id': 1
    })
    
    assert response.status_code == 400
    assert response.json == {"message": "Product name cannot exceed 100 characters"}

def test_create_product_invalid_price(client, init_database):
    """Test creating product with invalid price"""
    response = client.post('/api/products', json={
        'name': 'New Product',
        'price': 0,
        'description': 'New Description',
        'stock': 20,
        'category_id': 1
    })
    
    assert response.status_code == 400
    assert response.json == {"message": "Price must be greater than 0"}

def test_create_product_excessive_price(client, init_database):
    """Test creating product with excessive price"""
    response = client.post('/api/products', json={
        'name': 'New Product',
        'price': 1000001,
        'description': 'New Description',
        'stock': 20,
        'category_id': 1
    })
    
    assert response.status_code == 400
    assert response.json == {"message": "Price cannot exceed 1,000,000"}

def test_create_product_negative_stock(client, init_database):
    """Test creating product with negative stock"""
    response = client.post('/api/products', json={
        'name': 'New Product',
        'price': 199.99,
        'description': 'New Description',
        'stock': -1,
        'category_id': 1
    })
    
    assert response.status_code == 400
    assert response.json == {"message": "Stock cannot be negative"}

def test_create_product_excessive_stock(client, init_database):
    """Test creating product with excessive stock"""
    response = client.post('/api/products', json={
        'name': 'New Product',
        'price': 199.99,
        'description': 'New Description',
        'stock': 10001,
        'category_id': 1
    })
    
    assert response.status_code == 400
    assert response.json == {"message": "Stock cannot exceed 10,000 units"}

def test_create_product_long_description(client, init_database):
    """Test creating product with too long description"""
    response = client.post('/api/products', json={
        'name': 'New Product',
        'price': 199.99,
        'description': 'a' * 1001,  # More than 1000 characters
        'stock': 20,
        'category_id': 1
    })
    
    assert response.status_code == 400
    assert response.json == {"message": "Description cannot exceed 1000 characters"}

def test_create_product_invalid_category(client, init_database):
    """Test creating product with invalid category"""
    response = client.post('/api/products', json={
        'name': 'New Product',
        'price': 199.99,
        'description': 'New Description',
        'stock': 20,
        'category_id': 999
    })
    
    assert response.status_code == 404
    assert response.json == {"message": "CategoryModel with id 999 not found"}

def test_create_duplicate_product_name(client, init_database):
    """Test creating product with duplicate name in same category"""
    response = client.post('/api/products', json={
        'name': 'Smartphone',  # Already exists in category 1
        'price': 199.99,
        'description': 'New Description',
        'stock': 20,
        'category_id': 1
    })
    
    assert response.status_code == 400
    assert response.json == {"message": "A product with this name already exists in this category"}

# PUT Tests
def test_update_product_success(client, init_database):
    """Test successful product update"""
    response = client.put('/api/products/1', json={
        'name': 'Updated Smartphone',
        'price': 799.99,
        'description': 'Updated Description',
        'stock': 60,
        'category_id': 1
    })
    
    assert response.status_code == 200
    assert response.json == {"message": "Product updated successfully"}

# DELETE Tests
def test_delete_product_success(client, init_database):
    """Test successful product deletion"""
    response = client.delete('/api/products/1')
    
    assert response.status_code == 200
    assert response.json == {"message": "Product deleted successfully"}
