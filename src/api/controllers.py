from flask_restful import Resource, reqparse, abort
from api.models import ProductModel, CategoryModel, OrderModel, UserModel, OrderItemModel, CartModel
from api.extensions import db
import re
from werkzeug.security import generate_password_hash, check_password_hash
# cart imports
from decimal import Decimal
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime


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
        
        # Name validations
        if len(args['name'].strip()) < 3:
            abort(400, message="Product name must be at least 3 characters long")
        if len(args['name']) > 100:
            abort(400, message="Product name cannot exceed 100 characters")
        
        # Price validations
        if args['price'] <= 0:
            abort(400, message="Price must be greater than 0")
        if args['price'] > 1000000:  # 1 million limit
            abort(400, message="Price cannot exceed 1,000,000")
        
        # Stock validations
        if args['stock'] < 0:
            abort(400, message="Stock cannot be negative")
        if args['stock'] > 10000:  # Reasonable stock limit
            abort(400, message="Stock cannot exceed 10,000 units")
        
        # Description validation (if provided)
        if args['description'] and len(args['description']) > 1000:
            abort(400, message="Description cannot exceed 1000 characters")
            
        # Validate category exists
        category = db.session.get(CategoryModel, args['category_id'])
        if not category:
            abort(404, message=f"CategoryModel with id {args['category_id']} not found")
        
        # Check for duplicate product names in the same category
        existing_product = ProductModel.query.filter_by(
            name=args['name'],
            category_id=args['category_id']
        ).first()
        if existing_product:
            abort(400, message="A product with this name already exists in this category")

        try:
            product = ProductModel(**args)
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

class Cart(Resource):
    def __init__(self):
        self.parser = reqparse.RequestParser()
        self.parser.add_argument('product_id', type=int, required=True, help='Product ID is required')
        self.parser.add_argument('quantity', type=int, required=True, help='Quantity is required')
        self.parser.add_argument('replace', type=bool, default=False, help='Replace existing quantity instead of adding')
        self.MAX_CART_ITEMS = 20

    def get(self, user_id):
        """
        Get cart contents for a user
        """
        try:
            # Verify user exists
            user = db.session.get(UserModel, user_id)
            if not user:
                abort(404, message=f"User with id {user_id} not found")

            cart_items = CartModel.get_user_cart(user_id)
            items = []
            removed_items = []
            total = Decimal('0')

            for item in cart_items:
                if not item.is_valid:
                    removed_items.append(item)
                    continue

                # Adjust quantity if needed
                if item.product and item.product.stock < item.quantity:
                    item.adjust_quantity(item.product.stock)
                    db.session.add(item)

                items.append({
                    'id': item.id,
                    'product_id': item.product_id,
                    'product_name': item.product.name,
                    'quantity': item.quantity,
                    'price': float(item.product.price),
                    'subtotal': float(item.subtotal),
                    'stock_available': item.product.stock,
                    'added_at': item.added_at.isoformat(),
                    'updated_at': item.updated_at.isoformat()
                })
                total += item.subtotal

            # Remove invalid items
            for item in removed_items:
                db.session.delete(item)

            if removed_items or any(hasattr(item, '_modified') for item in cart_items):
                db.session.commit()

            return {
                'user_id': user_id,
                'items': items,
                'total': float(total),
                'item_count': len(items),
                'updated_at': datetime.utcnow().isoformat(),
                'messages': [
                    "Some items were removed from your cart because they are no longer available"
                    if removed_items else None,
                    "Some item quantities were adjusted due to stock limitations"
                    if any(hasattr(item, '_modified') for item in cart_items)
                    else None
                ]
            }

        except Exception as e:
            db.session.rollback()
            abort(500, message=f"An error occurred while retrieving cart: {str(e)}")

    def post(self, user_id):
        """
        Add item to cart or update quantity
        """
        args = self.parser.parse_args()
        
        try:
            # Verify user exists
            user = db.session.get(UserModel, user_id)
            if not user:
                abort(404, message=f"User with id {user_id} not found")

            # Verify product exists and has stock
            product = db.session.get(ProductModel, args['product_id'])
            if not product:
                abort(404, message=f"Product with id {args['product_id']} not found")

            if product.stock <= 0:
                abort(400, message="Product is out of stock")

            # Check cart item limit
            current_items = CartModel.query.filter_by(user_id=user_id).count()
            cart_item = CartModel.query.filter_by(
                user_id=user_id,
                product_id=args['product_id']
            ).first()

            if current_items >= self.MAX_CART_ITEMS and not cart_item:
                abort(400, message=f"Cart cannot contain more than {self.MAX_CART_ITEMS} different items")

            try:
                if cart_item:
                    # Update existing cart item
                    new_quantity = args['quantity'] if args['replace'] else cart_item.quantity + args['quantity']
                    cart_item.quantity = new_quantity  # This will trigger quantity validation
                    message = "Cart item quantity updated successfully"
                    status_code = 200
                else:
                    # Create new cart item
                    cart_item = CartModel(
                        user_id=user_id,
                        product_id=args['product_id'],
                        quantity=args['quantity']
                    )
                    db.session.add(cart_item)
                    message = "Item added to cart successfully"
                    status_code = 201

                db.session.commit()

                return {
                    'message': message,
                    'cart_item': {
                        'id': cart_item.id,
                        'product_id': cart_item.product_id,
                        'product_name': cart_item.product.name,
                        'quantity': cart_item.quantity,
                        'price': float(cart_item.product.price),
                        'subtotal': float(cart_item.subtotal),
                        'stock_available': cart_item.product.stock,
                        'added_at': cart_item.added_at.isoformat(),
                        'updated_at': cart_item.updated_at.isoformat()
                    }
                }, status_code

            except ValueError as ve:
                abort(400, message=str(ve))

        except SQLAlchemyError as e:
            db.session.rollback()
            abort(500, message=f"Database error occurred: {str(e)}")
        except Exception as e:
            db.session.rollback()
            abort(500, message=f"An error occurred: {str(e)}")

    def put(self, user_id, product_id):
        """
        Update cart item quantity
        """
        args = self.parser.parse_args()
        
        try:
            # Verify user exists
            user = db.session.get(UserModel, user_id)
            if not user:
                abort(404, message=f"User with id {user_id} not found")

            # Get cart item
            cart_item = CartModel.query.filter_by(
                user_id=user_id,
                product_id=product_id
            ).first()

            if not cart_item:
                abort(404, message="Item not found in cart")

            try:
                cart_item.quantity = args['quantity']  # This will trigger quantity validation
                db.session.commit()

                return {
                    'message': 'Cart item updated successfully',
                    'cart_item': {
                        'id': cart_item.id,
                        'product_id': cart_item.product_id,
                        'product_name': cart_item.product.name,
                        'quantity': cart_item.quantity,
                        'price': float(cart_item.product.price),
                        'subtotal': float(cart_item.subtotal),
                        'stock_available': cart_item.product.stock,
                        'updated_at': cart_item.updated_at.isoformat()
                    }
                }

            except ValueError as ve:
                abort(400, message=str(ve))

        except Exception as e:
            db.session.rollback()
            abort(500, message=f"An error occurred while updating cart: {str(e)}")

    def delete(self, user_id, product_id=None):
        """
        Remove item(s) from cart
        """
        try:
            # Verify user exists
            user = db.session.get(UserModel, user_id)
            if not user:
                abort(404, message=f"User with id {user_id} not found")

            if product_id:
                # Delete specific item
                cart_item = CartModel.query.filter_by(
                    user_id=user_id,
                    product_id=product_id
                ).first()

                if not cart_item:
                    abort(404, message="Item not found in cart")

                db.session.delete(cart_item)
                message = "Item removed from cart successfully"
            else:
                # Clear entire cart
                deleted = CartModel.clear_cart(user_id)
                if not deleted:
                    return {'message': 'Cart is already empty'}, 200
                message = "All items removed from cart successfully"

            db.session.commit()
            return {'message': message}

        except Exception as e:
            db.session.rollback()
            abort(500, message=f"An error occurred while removing from cart: {str(e)}")

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

