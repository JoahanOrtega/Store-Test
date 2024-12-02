from pytest import approx
import pytest
from flask import Flask
from api.extensions import db
from api.models import UserModel, CategoryModel, ProductModel, CartModel, OrderModel, OrderItemModel
from api.controllers import Users, Categories, Products, Cart, Orders
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
    api.add_resource(Cart, '/api/cart', '/api/cart/<int:user_id>', '/api/cart/<int:user_id>/<int:product_id>')
    api.add_resource(Orders, '/api/orders', '/api/orders/<int:order_id>')

    
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
        
        # Helper function to create a test Cart
        def create_test_cart(user_id, product_id, quantity):
            cart = CartModel(
                user_id=user_id,
                product_id=product_id,
                quantity=quantity
            )
            db.session.add(cart)

        # Add initial data
        create_test_user("testuser1", "test1@example.com", "password123")
        create_test_user("john_doe", "john@example.com", "secure123")
        
        create_test_category("Electronics", "Electronic devices and accessories")
        create_test_category("Sports", "Sports equipment and accessories")
        
        create_test_product("Smartphone", 699.99, "Latest model smartphone", 50, 1)
        create_test_product("Laptop", 1499.99, "Latest model laptop", 25, 1)
        create_test_product("Headphones", 1499.99, "Wireless headphones", 5, 1)

        create_test_cart(2, 1, 2)
        create_test_cart(2, 2, 1)

        
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
        'product_count': 3
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
            {
                'id': 3,
                'name': 'Headphones',
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
            {
                "id": 3,
                "name": "Headphones",
                "price": 1499.99,
                "description": "Wireless headphones",
                "stock": 5
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
    response = client.delete('/api/products/3')
    
    assert response.status_code == 200
    assert response.json == {"message": "Product deleted successfully"}

# CART Test
def test_get_empty_cart(client, init_database):
    """Test getting an empty cart"""
    response = client.get('/api/cart/1')
    
    assert response.status_code == 200
    data = response.json
    assert data['user_id'] == 1
    assert data['items'] == []
    assert data['total'] == 0
    assert data['item_count'] == 0
    assert 'updated_at' in data

def test_get_nonexistent_user_cart(client, init_database):
    """Test getting cart for non-existent user"""
    response = client.get('/api/cart/999')
    
    assert response.status_code == 404
    assert 'User with id 999 not found' in response.json['message']

def test_add_item_to_cart(client, init_database):
    """Test adding an item to cart"""
    response = client.post('/api/cart/1', json={
        'product_id': 1,
        'quantity': 2
    })
    
    assert response.status_code == 201
    data = response.json
    assert data['message'] == 'Item added to cart successfully'
    assert data['cart_item']['product_id'] == 1
    assert data['cart_item']['quantity'] == 2
    assert data['cart_item']['product_name'] == 'Smartphone'
    assert 'subtotal' in data['cart_item']
    assert 'added_at' in data['cart_item']

def test_add_out_of_stock_item(client, init_database):
    """Test adding out of stock item"""
    response = client.post('/api/cart/1', json={
        'product_id': 3,  # Smarwatch (stock: 5)
        'quantity': 6
    })
    assert response.status_code == 400

def test_add_nonexistent_product(client, init_database):
    """Test adding non-existent product"""
    response = client.post('/api/cart/1', json={
        'product_id': 999,
        'quantity': 1
    })
    
    assert response.status_code == 404
    assert 'Product with id 999 not found' in response.json['message']

def test_add_negative_quantity(client, init_database):
    """Test adding negative quantity to cart"""
    response = client.post('/api/cart/1', json={
        'product_id': 1,
        'quantity': -1
    })
    
    assert response.status_code == 400
    assert 'quantity' in response.json['message'].lower()

def test_add_zero_quantity(client, init_database):
    """Test adding zero quantity to cart"""
    response = client.post('/api/cart/1', json={
        'product_id': 1,
        'quantity': 0
    })
    
    assert response.status_code == 400
    assert 'quantity' in response.json['message'].lower()

def test_update_cart_quantity(client, init_database):
    """Test updating item quantity in cart"""
    # First add item to cart
    client.post('/api/cart/1', json={
        'product_id': 1,
        'quantity': 1
    })
    
    # Then update quantity
    response = client.post('/api/cart/1', json={
        'product_id': 1,
        'quantity': 2,
        'replace': True
    })
    
    assert response.status_code == 200
    data = response.json
    assert data['cart_item']['quantity'] == 2

def test_exceed_stock_quantity(client, init_database):
    """Test adding more items than available stock"""
    response = client.post('/api/cart/1', json={
        'product_id': 3,  # Laptop (stock: 5)
        'quantity': 6
    })
    
    assert response.status_code == 400
    assert 'stock' in response.json['message'].lower()

def test_delete_cart_item(client, init_database):
    """Test deleting an item from cart"""
    # Add item to cart
    client.post('/api/cart/1', json={
        'product_id': 3,
        'quantity': 1
    })
    
    # Get the cart to find the cart_item_id
    cart_response = client.get('/api/cart/1')
    cart_item_id = cart_response.json['items'][0]['id']

    # Delete item using cart_item_id
    response = client.delete(f'/api/cart/1/{cart_item_id}')
    print(response.json)
    assert response.status_code == 200
    assert 'removed' in response.json['message'].lower()
    
    # Verify item was deleted
    response = client.get('/api/cart/1')
    assert len(response.json['items']) == 0

def test_clear_cart(client, init_database):
    """Test clearing entire cart"""
    # Add multiple items to cart
    client.post('/api/cart/1', json={'product_id': 1, 'quantity': 1})
    client.post('/api/cart/1', json={'product_id': 2, 'quantity': 1})
    
    # Clear cart
    response = client.delete('/api/cart/1')
    
    assert response.status_code == 200
    assert 'cleared' in response.json['message'].lower()
    
    # Verify cart is empty
    response = client.get('/api/cart/1')
    assert len(response.json['items']) == 0

def test_get_cart_with_multiple_items(client, init_database):
    """Test getting cart with multiple items"""
    # Add multiple items
    client.post('/api/cart/1', json={'product_id': 1, 'quantity': 2})
    client.post('/api/cart/1', json={'product_id': 2, 'quantity': 1})
    
    response = client.get('/api/cart/1')
    total = (699.99 * 2 + 1499.99)

    assert response.status_code == 200
    data = response.json
    assert len(data['items']) == 2
    assert data['total'] == approx(total)
    assert data['item_count'] == 2

def test_delete_nonexistent_cart_item(client, init_database):
    """Test deleting a non-existent cart item"""
    # First ensure user exists
    response = client.delete('/api/cart/1/999')
    
    assert response.status_code == 404
    assert response.json['message'] == "Item not found in cart"

def test_delete_cart_item_wrong_user(client, init_database):
    """Test deleting a cart item from wrong user"""
    # Add item to cart for user 1
    add_response = client.post('/api/cart/1', json={
        'product_id': 1,
        'quantity': 1
    })
    assert add_response.status_code == 201
    
    # Get the cart_item_id
    cart_response = client.get('/api/cart/1')
    assert cart_response.status_code == 200
    cart_item_id = cart_response.json['items'][0]['id']
    
    # Try to delete item using wrong user_id
    response = client.delete(f'/api/cart/999/{cart_item_id}')
    
    assert response.status_code == 404
    assert response.json['message'] == "User with id 999 not found"

def test_delete_cart_item_wrong_user_and_item(client, init_database):
    """Test deleting with both wrong user and item"""
    response = client.delete('/api/cart/999/999')
    
    assert response.status_code == 404
    assert response.json['message'] == "User with id 999 not found"

def test_clear_empty_cart(client, init_database):
    """Test clearing an already empty cart"""
    response = client.delete('/api/cart/1')
    
    assert response.status_code == 200
    assert response.json['message'] == "Cart is already empty"

def test_clear_cart_with_items(client, init_database):
    """Test clearing a cart with items"""
    # Add items to cart
    client.post('/api/cart/1', json={'product_id': 1, 'quantity': 1})
    client.post('/api/cart/1', json={'product_id': 2, 'quantity': 1})
    
    # Verify items were added
    cart_response = client.get('/api/cart/1')
    assert len(cart_response.json['items']) == 2
    
    # Clear cart
    response = client.delete('/api/cart/1')
    
    assert response.status_code == 200
    assert response.json['message'] == "Cleared"
    
    # Verify cart is empty
    verify_response = client.get('/api/cart/1')
    assert len(verify_response.json['items']) == 0

def test_delete_cart_item_invalid_ids(client, init_database):
    """Test deleting with invalid ID formats"""
    response = client.delete('/api/cart/abc/def')
    
    assert response.status_code == 404  # or whatever your app returns for invalid URLs

def test_get_all_orders(client, init_database):
    """Test getting all orders"""
    # Create multiple orders
    order_data1 = {
        'user_id': 1,
        'items': [{'product_id': 1, 'quantity': 1}]
    }
    order_data2 = {
        'user_id': 1,
        'items': [{'product_id': 2, 'quantity': 1}]
    }
    
    response1 = client.post('/api/orders', json=order_data1)
    response2 = client.post('/api/orders', json=order_data2)
    
    assert response1.status_code == 201
    assert response2.status_code == 201
    
    # Get all orders
    response = client.get('/api/orders')
    
    assert response.status_code == 200
    assert 'orders' in response.json
    orders = response.json['orders']
    assert len(orders) >= 2
    
    # Verify order structure
    for order in orders:
        assert 'id' in order
        assert 'user_id' in order
        assert 'total_amount' in order
        assert 'status' in order
        assert 'created_at' in order

def test_get_order_with_multiple_items(client, init_database):
    """Test getting an order with multiple items"""
    # Create an order with multiple items
    order_data = {
        'user_id': 1,
        'items': [
            {'product_id': 1, 'quantity': 2},
            {'product_id': 2, 'quantity': 1}
        ]
    }
    
    create_response = client.post('/api/orders', json=order_data)
    assert create_response.status_code == 201
    order_id = create_response.json['order']['id']
    
    # Get the order
    response = client.get(f'/api/orders/{order_id}')
    
    assert response.status_code == 200
    assert response.json['id'] == order_id
    assert len(response.json['items']) == 2
    
    # Verify items
    items = response.json['items']
    assert items[0]['product_id'] == 1
    assert items[0]['quantity'] == 2
    assert items[1]['product_id'] == 2
    assert items[1]['quantity'] == 1
    
    # Verify total amount
    expected_total = (2 * 699.99) + (1 * 1499.99)
    assert response.json['total_amount'] == pytest.approx(expected_total, 0.01)

def test_get_nonexistent_order(client, init_database):
    """Test getting a non-existent order"""
    response = client.get('/api/orders/999')
    
    assert response.status_code == 404

def test_get_order_by_id(client, init_database):
    """Test getting a specific order"""
    # First create an order
    order_data = {
        'user_id': 1,
        'items': [{'product_id': 1, 'quantity': 1}]
    }
    create_response = client.post('/api/orders', json=order_data)
    assert create_response.status_code == 201
    order_id = create_response.json['order']['id']
    
    # Get the order
    response = client.get(f'/api/orders/{order_id}')
    
    assert response.status_code == 200
    assert response.json['id'] == order_id
    assert response.json['user_id'] == 1
    assert len(response.json['items']) == 1
    assert 'total_amount' in response.json
    assert 'status' in response.json
    assert 'created_at' in response.json

    # Verify order details
    assert response.json['status'] == 'pending'
    assert isinstance(response.json['total_amount'], (int, float))
    
    # Verify items
    items = response.json['items']
    assert len(items) == 1
    assert items[0]['product_id'] == 1
    assert items[0]['quantity'] == 1
    assert 'price' in items[0]

def test_create_order_success(client, init_database):
    """Test creating a valid order"""
    # Verify initial stock
    with client.application.app_context():
        product1 = db.session.get(ProductModel, 1)
        product2 = db.session.get(ProductModel, 2)
        assert product1.stock == 50, "Initial stock for product 1 should be 10"
        assert product2.stock == 25, "Initial stock for product 2 should be 5"

    order_data = {
        'user_id': 1,
        'items': [
            {'product_id': 1, 'quantity': 2},
            {'product_id': 2, 'quantity': 1}
        ]
    }

    response = client.post('/api/orders', json=order_data)

    assert response.status_code == 201
    assert 'Order created successfully' in response.json['message']
    assert 'order' in response.json
    assert 'id' in response.json['order']
    
    # Verify order details
    order = response.json['order']
    assert order['user_id'] == 1
    assert order['status'] == 'pending'
    assert len(order['items']) == 2

    # Verify items details
    items = order['items']
    assert items[0]['product_id'] == 1
    assert items[0]['quantity'] == 2
    assert items[0]['price'] == 699.99
    assert items[1]['product_id'] == 2
    assert items[1]['quantity'] == 1
    assert items[1]['price'] == 1499.99

    # Verify stock was updated
    with client.application.app_context():
        db.session.expire_all()  # Refresh session to get latest data
        product1 = db.session.get(ProductModel, 1)
        product2 = db.session.get(ProductModel, 2)
        assert product1.stock == 48, f"Expected stock 8, got {product1.stock}"  # 50 - 2
        assert product2.stock == 24, f"Expected stock 4, got {product2.stock}"  # 25 - 1

    # Verify total amount
    expected_total = (2 * 699.99) + (1 * 1499.99)
    assert order['total_amount'] == pytest.approx(expected_total, 0.01)

def test_create_order_empty_items(client, init_database):
    """Test creating order with no items"""
    order_data = {
        'user_id': 1,
        'items': []
    }
    
    response = client.post('/api/orders', json=order_data)
    
    assert response.status_code == 400
    assert 'must contain at least one item' in response.json['message']

def test_create_order_nonexistent_user(client, init_database):
    """Test creating order for non-existent user"""
    order_data = {
        'user_id': 999,
        'items': [{'product_id': 1, 'quantity': 1}]
    }
    
    response = client.post('/api/orders', json=order_data)
    
    assert response.status_code == 404
    assert 'User 999 not found' in response.json['message']

def test_create_order_nonexistent_product(client, init_database):
    """Test creating order with non-existent product"""
    order_data = {
        'user_id': 1,
        'items': [{'product_id': 999, 'quantity': 1}]
    }
    
    response = client.post('/api/orders', json=order_data)
    
    assert response.status_code == 404
    assert 'Product 999 not found' in response.json['message']

def test_create_order_insufficient_stock(client, init_database):
    """Test creating order with insufficient stock"""
    order_data = {
        'user_id': 1,
        'items': [{'product_id': 1, 'quantity': 51}]  # Stock is 50
    }
    
    response = client.post('/api/orders', json=order_data)
    
    assert response.status_code == 400
    assert 'Insufficient stock' in response.json['message']

def test_create_order_zero_quantity(client, init_database):
    """Test creating order with zero quantity"""
    order_data = {
        'user_id': 1,
        'items': [{'product_id': 1, 'quantity': 0}]
    }
    
    response = client.post('/api/orders', json=order_data)
    
    assert response.status_code == 400
    assert 'Quantity must be positive' in response.json['message']

def test_create_order_negative_quantity(client, init_database):
    """Test creating order with negative quantity"""
    order_data = {
        'user_id': 1,
        'items': [{'product_id': 1, 'quantity': -1}]
    }
    
    response = client.post('/api/orders', json=order_data)
    
    assert response.status_code == 400
    assert 'Quantity must be positive' in response.json['message']

def test_create_order_multiple_items_same_product(client, init_database):
    """Test creating order with multiple items of same product"""
    order_data = {
        'user_id': 1,
        'items': [
            {'product_id': 1, 'quantity': 2},
            {'product_id': 1, 'quantity': 3}
        ]
    }
    
    response = client.post('/api/orders', json=order_data)
    
    assert response.status_code == 201
    assert 'Order created successfully' in response.json['message']
    
    # Verify stock was updated correctly
    with client.application.app_context():
        product = db.session.get(ProductModel, 1)  # New syntax
        assert product.stock == 45  # 50 - (2 + 3)