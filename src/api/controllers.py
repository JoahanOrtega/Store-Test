from flask_restful import Resource, reqparse, abort
from api.models import ProductModel, CategoryModel, OrderModel, UserModel, OrderItemModel, CartModel
from api.extensions import db
from datetime import datetime
import re
from werkzeug.security import generate_password_hash, check_password_hash


# Helper function for validation
def abort_if_not_found(model, item_id):
    item = model.query.get(item_id)
    if not item:
        abort(404, message=f"{model.__name__} with id {item_id} not found")
    return item


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

class Users(Resource):
    def __init__(self):
        self.parser = reqparse.RequestParser()
        self.parser.add_argument('username', required=True, help="Username cannot be blank")
        self.parser.add_argument('email', required=True, help="Email cannot be blank")
        self.parser.add_argument('password', required=True, help="Password cannot be blank")
        
        # Parser for updates (password optional)
        self.update_parser = reqparse.RequestParser()
        self.update_parser.add_argument('username', required=False)
        self.update_parser.add_argument('email', required=False)
        self.update_parser.add_argument('password', required=False)

    def get(self, user_id=None):
        if user_id:
            user = abort_if_not_found(UserModel, user_id)
            return {
                'id': user.id,
                'username': user.username,
                'email': user.email
            }
        
        users = UserModel.query.all()
        return {
            'users': [{
                'id': u.id,
                'username': u.username,
                'email': u.email
            } for u in users]
        }

    def post(self):
        args = self.parser.parse_args()
        
        # Validate username
        if len(args['username'].strip()) < 2:
            abort(400, message="Username must be at least 2 characters long")
        
        # Validate email format
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, args['email']):
            abort(400, message="Invalid email format")
        
        # Check if email already exists
        if UserModel.query.filter_by(email=args['email']).first():
            abort(400, message="Email already registered")
        
        # Check if username already exists
        if UserModel.query.filter_by(username=args['username']).first():
            abort(400, message="Username already taken")
        
        # Validate password
        if len(args['password']) < 6:
            abort(400, message="Password must be at least 6 characters long")

        try:
            # Create new user
            new_user = UserModel(
                username=args['username'],
                email=args['email']
            )
            new_user.set_password(args['password'])
            
            # Save to database
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
            abort(500, message=f"An error occurred while creating user: {str(e)}")

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
        
        # Calculate total amount and create order
        total_amount = 0
        order = OrderModel(
            user_id=args['user_id'],
            total_amount=0
        )
        db.session.add(order)
        db.session.flush()  # This gets us the order.id
        
        # Add order items
        for item in args['items']:
            product = ProductModel.query.get_or_404(item['product_id'])
            if product.stock < item['quantity']:
                db.session.rollback()
                abort(400, message=f"Insufficient stock for product {product.name}")
            
            order_item = OrderItemModel(
                order_id=order.id,
                product_id=product.id,
                quantity=item['quantity'],
                price_at_time=product.price  # Use price_at_time instead of price
            )
            total_amount += product.price * item['quantity']
            product.stock -= item['quantity']
            db.session.add(order_item)
        
        order.total_amount = total_amount
        
        try:
            db.session.commit()
            
            # Clear user's cart
            CartModel.query.filter_by(user_id=args['user_id']).delete()
            db.session.commit()
            
            return {
                'message': 'Order created successfully',
                'order': {
                    'id': order.id,
                    'total_amount': order.total_amount,
                    'status': order.status
                }
            }, 201
            
        except Exception as e:
            db.session.rollback()
            abort(500, message=str(e))          

class Cart(Resource):
    def __init__(self):
        self.parser = reqparse.RequestParser()
        self.parser.add_argument('product_id', type=int, required=True, help="Product ID is required")
        self.parser.add_argument('quantity', type=int, required=True, help="Quantity is required")

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
        
        # Validate user and product exist
        abort_if_not_found(UserModel, user_id)
        product = abort_if_not_found(ProductModel, args['product_id'])
        
        if args['quantity'] <= 0:
            abort(400, message="Quantity must be greater than 0")
        
        if product.stock < args['quantity']:
            abort(400, message="Insufficient stock")

        try:
            # Check if item already in cart
            cart_item = CartModel.query.filter_by(
                user_id=user_id,
                product_id=args['product_id']
            ).first()

            if cart_item:
                cart_item.quantity += args['quantity']
            else:
                cart_item = CartModel(
                    user_id=user_id,
                    product_id=args['product_id'],
                    quantity=args['quantity']
                )
                db.session.add(cart_item)

            db.session.commit()
            return {'message': 'Item added to cart successfully'}
        except Exception as e:
            db.session.rollback()
            abort(500, message=f"An error occurred while adding to cart: {str(e)}")

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
