from flask_restful import Resource, reqparse, abort
from api.models import ProductModel, CategoryModel, OrderModel, UserModel, OrderItemModel, CartModel
from api.extensions import db
from datetime import datetime
import re
from werkzeug.security import generate_password_hash, check_password_hash


# Helper function for validation
def abort_if_not_found(model, item_id):
    # Using Session.get() instead of Query.get()
    item = db.session.get(model, item_id)
    if not item:
        abort(404, message=f"{model.__name__} with id {item_id} not found")
    return item


class Users(Resource):
    def __init__(self):
        self.parser = reqparse.RequestParser()
        self.parser.add_argument('username', 
            type=str,
            required=True,
            help='Username is required'
        )
        self.parser.add_argument('email',
            type=str,
            required=True,
            help='Email is required'
        )
        self.parser.add_argument('password',
            type=str,
            required=True,
            help='Password is required'
        )

        # Parser for updates (password optional)
        self.update_parser = reqparse.RequestParser()
        self.update_parser.add_argument('username', required=False)
        self.update_parser.add_argument('email', required=False)
        self.update_parser.add_argument('password', required=False)


    def validate_email(self, email):
        # Basic email regex pattern
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        if not email or not isinstance(email, str):
            return False
        
        # Check email length
        if len(email) > 254:
            return False
        
        # Split email into local and domain parts
        try:
            local_part, domain = email.rsplit('@', 1)
        except ValueError:
            return False
        
        # Check local part and domain lengths
        if len(local_part) > 64 or len(domain) > 255:
            return False
        
        # Check for consecutive dots
        if '..' in email:
            return False
        
        # Check for leading/trailing dots in local part
        if local_part.startswith('.') or local_part.endswith('.'):
            return False
        
        # Check domain format
        if domain.startswith('-') or domain.endswith('-'):
            return False
        
        if not re.match(email_pattern, email):
            return False
            
        return True

    def get(self, user_id=None):
        if user_id:
            # Using Session.get() instead of Query.get()
            user = db.session.get(UserModel, user_id)
            if not user:
                abort(404, message=f"User {user_id} not found")
            return {
                'id': user.id,
                'username': user.username,
                'email': user.email
            }
        users = UserModel.query.all()
        return {'users': [{'id': u.id, 'username': u.username, 'email': u.email} for u in users]}

    def post(self):
        data = self.parser.parse_args()
        
        # Validate username
        if not data['username'] or not data['username'].strip():
            return {'message': 'Username is required'}, 400
        
        if len(data['username']) < 3:
            return {'message': 'Username must be at least 3 characters long'}, 400
        
        # Check if username already exists
        if UserModel.query.filter_by(username=data['username']).first():
            return {'message': 'Username already exists'}, 400

        # Email validation
        if not self.validate_email(data['email']):
            return {'message': 'Invalid email format'}, 400

        # Check if email already exists
        if UserModel.query.filter_by(email=data['email']).first():
            return {'message': 'Email already exists'}, 400

        # Validate password
        if len(data['password']) < 6:
            return {'message': 'Password must be at least 6 characters long'}, 400

        try:
            new_user = UserModel(
                username=data['username'],
                email=data['email']
            )
            new_user.set_password(data['password'])
            
            db.session.add(new_user)
            db.session.commit()

            return {
                'message': 'User created successfully',
                'user': {
                    'id': new_user.id,
                    'username': new_user.username,
                    'email': new_user.email
                }
            }, 201

        except Exception as e:
            db.session.rollback()
            return {'message': 'An error occurred while creating the user'}, 500

    def put(self, user_id):
        user = abort_if_not_found(UserModel, user_id)
        args = self.update_parser.parse_args()

        try:
            if args.get('username'):
                if len(args['username'].strip()) < 2:
                    abort(400, message="Username must be at least 2 characters long")
                
                # Check if username is taken by another user
                existing_user = UserModel.query.filter_by(username=args['username']).first()
                if existing_user and existing_user.id != user_id:
                    abort(400, message="Username already taken")
                
                user.username = args['username']

            if args.get('email'):
                email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
                if not re.match(email_pattern, args['email']):
                    abort(400, message="Invalid email format")
                
                # Check if email is taken by another user
                existing_user = UserModel.query.filter_by(email=args['email']).first()
                if existing_user and existing_user.id != user_id:
                    abort(400, message="Email already registered")
                
                user.email = args['email']

            if args.get('password'):
                if len(args['password']) < 6:
                    abort(400, message="Password must be at least 6 characters long")
                user.set_password(args['password'])

            db.session.commit()
            return {
                'message': 'User updated successfully',
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email
                }
            }

        except Exception as e:
            db.session.rollback()
            abort(500, message=f"An error occurred while updating user: {str(e)}")

    def delete(self, user_id):
        user = abort_if_not_found(UserModel, user_id)

        try:
            # Check if user has any orders before deletion
            if hasattr(user, 'orders') and user.orders:
                abort(400, message="Cannot delete user with existing orders")

            db.session.delete(user)
            db.session.commit()
            return {'message': 'User deleted successfully'}
        
        except Exception as e:
            db.session.rollback()
            abort(500, message=f"An error occurred while deleting user: {str(e)}")


class Categories(Resource):
    def __init__(self):
        self.parser = reqparse.RequestParser()
        self.parser.add_argument('name', required=True, help="Category name cannot be blank")
        self.parser.add_argument('description')

    def get(self, category_id=None):
        if category_id:
            category = abort_if_not_found(CategoryModel, category_id)
            return {
                'id': category.id,
                'name': category.name,
                'description': category.description,
                'products': [{
                    'id': product.id,
                    'name': product.name,
                    'price': product.price
                } for product in category.products]
            }
        
        categories = CategoryModel.query.all()
        return {
            'categories': [{
                'id': c.id,
                'name': c.name,
                'description': c.description,
                'product_count': len(c.products)
            } for c in categories]
        }

    def post(self):
        args = self.parser.parse_args()
        
        if len(args['name'].strip()) < 3:
            abort(400, message="Category name must be at least 3 characters long")
        
        if CategoryModel.query.filter_by(name=args['name']).first():
            abort(400, message="Category with this name already exists")

        try:
            category = CategoryModel(
                name=args['name'],
                description=args.get('description', '')
            )
            db.session.add(category)
            db.session.commit()
            return {
                'message': 'Category created successfully',
                'category': {
                    'id': category.id,
                    'name': category.name
                }
            }, 201
        except Exception as e:
            db.session.rollback()
            abort(500, message=f"An error occurred while creating category: {str(e)}")

    def put(self, category_id):
        category = abort_if_not_found(CategoryModel, category_id)
        args = self.parser.parse_args()
        
        if len(args['name'].strip()) < 3:
            abort(400, message="Category name must be at least 3 characters long")
        
        existing_category = CategoryModel.query.filter_by(name=args['name']).first()
        if existing_category and existing_category.id != category_id:
            abort(400, message="Category with this name already exists")

        try:
            category.name = args['name']
            if 'description' in args:
                category.description = args['description']
            
            db.session.commit()
            return {'message': 'Category updated successfully'}
        except Exception as e:
            db.session.rollback()
            abort(500, message=f"An error occurred while updating category: {str(e)}")

    def delete(self, category_id):
        category = abort_if_not_found(CategoryModel, category_id)
        
        if category.products:
            abort(400, message="Cannot delete category with associated products")

        try:
            db.session.delete(category)
            db.session.commit()
            return {'message': 'Category deleted successfully'}
        except Exception as e:
            db.session.rollback()
            abort(500, message=f"An error occurred while deleting category: {str(e)}")

class Products(Resource):
    def __init__(self):
        self.parser = reqparse.RequestParser()
        self.parser.add_argument('name', required=True, help="Name cannot be blank")
        self.parser.add_argument('price', type=float, required=True, help="Price must be provided")
        self.parser.add_argument('description')
        self.parser.add_argument('stock', type=int, required=True, help="Stock quantity must be provided")
        self.parser.add_argument('category_id', type=int, required=True, help="Category ID must be provided")

    def get(self, product_id=None):
        if product_id:
            product = abort_if_not_found(ProductModel, product_id)
            return {
                'id': product.id,
                'name': product.name,
                'price': product.price,
                'description': product.description,
                'stock': product.stock,
                'category_id': product.category_id
            }
        
        products = ProductModel.query.all()
        return {'products': [{
            'id': p.id, 
            'name': p.name, 
            'price': p.price, 
            'description': p.description, 
            'stock': p.stock
        } for p in products]}

    def post(self):
        args = self.parser.parse_args()
        
        # Validate category exists
        abort_if_not_found(CategoryModel, args['category_id'])
        
        if args['price'] <= 0:
            abort(400, message="Price must be greater than 0")
        
        if args['stock'] < 0:
            abort(400, message="Stock cannot be negative")

        product = ProductModel(**args)
        try:
            db.session.add(product)
            db.session.commit()
            return {'message': 'Product created successfully', 'id': product.id}, 201
        except Exception as e:
            db.session.rollback()
            abort(500, message=f"An error occurred while creating product: {str(e)}")

    def put(self, product_id):
        product = abort_if_not_found(ProductModel, product_id)
        args = self.parser.parse_args()
        
        for key, value in args.items():
            setattr(product, key, value)

        try:
            db.session.commit()
            return {'message': 'Product updated successfully'}
        except Exception as e:
            db.session.rollback()
            abort(500, message=f"An error occurred while updating product: {str(e)}")

    def delete(self, product_id):
        product = abort_if_not_found(ProductModel, product_id)
        try:
            db.session.delete(product)
            db.session.commit()
            return {'message': 'Product deleted successfully'}
        except Exception as e:
            db.session.rollback()
            abort(500, message=f"An error occurred while deleting product: {str(e)}")

class Orders(Resource):
    def __init__(self):
        self.parser = reqparse.RequestParser()
        self.parser.add_argument('user_id', type=int, required=True)
        self.parser.add_argument('items', type=list, required=True, location='json')

    def get(self, order_id=None):
        if order_id:
            order = OrderModel.query.get_or_404(order_id)
            return {
                'id': order.id,
                'user_id': order.user_id,
                'total_amount': order.total_amount,
                'status': order.status,
                'created_at': str(order.created_at),
                'items': [{
                    'product_id': item.product_id,
                    'quantity': item.quantity,
                    'price': item.price_at_time
                } for item in order.items]
            }
        
        orders = OrderModel.query.all()
        return {'orders': [{
            'id': o.id,
            'user_id': o.user_id,
            'total_amount': o.total_amount,
            'status': o.status,
            'created_at': str(o.created_at)
        } for o in orders]}

    def post(self):
        args = self.parser.parse_args()
        
        if not args['items']:
            abort(400, message="Order must contain at least one item")
            
        # Validate user exists
        user = UserModel.query.get(args['user_id'])
        if not user:
            abort(404, message=f"User {args['user_id']} not found")
            
        # Create order
        order = OrderModel(user_id=args['user_id'])
        db.session.add(order)
        db.session.flush()
        
        # Add order items
        for item in args['items']:
            product = ProductModel.query.get(item['product_id'])
            if not product:
                db.session.rollback()
                abort(404, message=f"Product {item['product_id']} not found")
                
            if item['quantity'] <= 0:
                db.session.rollback()
                abort(400, message="Quantity must be positive")
                
            if product.stock < item['quantity']:
                db.session.rollback()
                abort(400, message=f"Insufficient stock for product {product.id}")
                
            order_item = OrderItemModel(
                order_id=order.id,
                product_id=product.id,
                quantity=item['quantity']
            )
            db.session.add(order_item)
            
            # Update stock
            product.stock -= item['quantity']
            
        try:
            db.session.commit()
            return {'message': 'Order created successfully', 'id': order.id}, 201
        except Exception as e:
            db.session.rollback()
            abort(500, message=str(e))  

class Cart(Resource):
    def __init__(self):
        self.parser = reqparse.RequestParser()
        self.parser.add_argument('product_id', type=int, required=True, help='Product ID is required')
        self.parser.add_argument('quantity', type=int, required=True, help='Quantity is required')

    def get(self, user_id):
        cart_items = CartModel.query.filter_by(user_id=user_id).all()
        total = 0
        items = []
        
        for item in cart_items:
            product = ProductModel.query.get(item.product_id)
            subtotal = product.price * item.quantity
            total += subtotal
            items.append({
                'product_id': item.product_id,
                'product_name': product.name,
                'quantity': item.quantity,
                'price': product.price,
                'subtotal': subtotal
            })
        
        return {
            'user_id': user_id,
            'items': items,
            'total': total
        }

    def post(self, user_id):
        args = self.parser.parse_args()
        
        try:
            # Validate user exists
            user = db.session.execute(
                select(UserModel).filter_by(id=user_id)
            ).scalar_one_or_none()
            
            if not user:
                return {'message': f'User with ID {user_id} not found'}, 404

            # Validate product exists and has sufficient stock
            product = db.session.execute(
                select(ProductModel).filter_by(id=args['product_id'])
            ).scalar_one_or_none()
            
            if not product:
                return {
                    'message': f'Product with ID {args["product_id"]} not found'
                }, 404

            # Validate quantity
            if args['quantity'] <= 0:
                return {'message': 'Quantity must be greater than 0'}, 400

            if product.stock < args['quantity']:
                return {
                    'message': f'Insufficient stock. Available: {product.stock}'
                }, 400

            # Check if item already in cart
            cart_item = db.session.execute(
                select(CartModel).filter_by(
                    user_id=user_id,
                    product_id=args['product_id']
                )
            ).scalar_one_or_none()

            if cart_item:
                # Update existing cart item
                new_quantity = cart_item.quantity + args['quantity']
                if new_quantity > product.stock:
                    return {
                        'message': (
                            f'Cannot add {args["quantity"]} items. '
                            f'Cart already has {cart_item.quantity} items. '
                            f'Stock available: {product.stock}'
                        )
                    }, 400
                
                cart_item.quantity = new_quantity
                message = 'Cart item quantity updated successfully'
            else:
                # Create new cart item
                cart_item = CartModel(
                    user_id=user_id,
                    product_id=args['product_id'],
                    quantity=args['quantity']
                )
                db.session.add(cart_item)
                message = 'Item added to cart successfully'

            db.session.commit()
            
            # Return response with cart item details
            return {
                'message': message,
                'cart_item': {
                    'id': cart_item.id,
                    'user_id': cart_item.user_id,
                    'product_id': cart_item.product_id,
                    'quantity': cart_item.quantity,
                    'product_name': product.name,
                    'unit_price': product.price,
                    'total_price': product.price * cart_item.quantity
                }
            }, 200 if cart_item else 201

        except ValueError as e:
            db.session.rollback()
            return {'message': str(e)}, 400
        
        except Exception as e:
            db.session.rollback()
            return {
                'message': 'An error occurred while processing your request',
                'error': str(e)
            }, 500

    def delete(self, user_id):
        parser = reqparse.RequestParser()
        parser.add_argument('product_id', type=int, required=True, help="Product ID is required")
        args = parser.parse_args()

        try:
            cart_item = CartModel.query.filter_by(
                user_id=user_id,
                product_id=args['product_id']
            ).first()

            if cart_item:
                db.session.delete(cart_item)
                db.session.commit()
                return {'message': 'Item removed from cart successfully'}
            else:
                abort(404, message="Item not found in cart")
        except Exception as e:
            db.session.rollback()
            abort(500, message=f"An error occurred while removing from cart: {str(e)}")
