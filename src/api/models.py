from api.extensions import db
from api.extensions import db
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from sqlalchemy.orm import validates
from decimal import Decimal

class UserModel(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False)

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)
    
    # Relationships
    # Define relationship to cart items
    cart_items = db.relationship(
        'CartModel',
        back_populates='user',
        cascade='all, delete-orphan',
        lazy=True
    )
    orders = db.relationship('OrderModel', backref='user', lazy=True)

    def __repr__(self):
        return f'<User {self.username}>'

class CategoryModel(db.Model):
    __tablename__ = 'categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(200))
    
    # Relationships
    products = db.relationship('ProductModel', backref='category', lazy=True)

    def __repr__(self):
        return f'<Category {self.name}>'

class ProductModel(db.Model):
    __tablename__ = 'products'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, nullable=False, default=0)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    # Define relationship to cart items
    cart_items = db.relationship(
        'CartModel',
        back_populates='product',
        cascade='all, delete-orphan',
        lazy=True
    )
    order_items = db.relationship('OrderItemModel', backref='product', lazy=True)

    def __repr__(self):
        return f'<Product {self.name}>'


class CartModel(db.Model):
    __tablename__ = 'cart_items'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id', ondelete='CASCADE'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Define relationships without backrefs
    user = db.relationship('UserModel', back_populates='cart_items')
    product = db.relationship('ProductModel', back_populates='cart_items')

    # Constants
    MAX_QUANTITY = 99
    MIN_QUANTITY = 1

    @validates('quantity')
    def validate_quantity(self, key, quantity):
        """Validate quantity is within acceptable range"""
        if not isinstance(quantity, int):
            raise ValueError("Quantity must be an integer")
        if quantity < self.MIN_QUANTITY:
            raise ValueError("Quantity must be greater than 0")
        if quantity > self.MAX_QUANTITY:
            raise ValueError(f"Quantity cannot exceed {self.MAX_QUANTITY}")
        return quantity
    
    @property
    def subtotal(self):
        """Calculate subtotal for cart item"""
        if self.product:
            return Decimal(str(self.product.price)) * Decimal(str(self.quantity))
        return Decimal('0')
    
    @property
    def is_valid(self):
        """Check if cart item is still valid"""
        if not self.product:
            return False
        if self.product.stock < self.quantity:
            return False
        return True
    
    def adjust_quantity(self, available_stock):
        """Adjust quantity based on available stock"""
        if available_stock < self.quantity:
            self.quantity = available_stock
            return True
        return False
    
    def __init__(self, user_id, product_id, quantity=1):
        self.user_id = user_id
        self.product_id = product_id
        self.quantity = quantity

    def __repr__(self):
        return f'<CartItem user_id={self.user_id} product_id={self.product_id} quantity={self.quantity}>'

    @classmethod
    def get_user_cart(cls, user_id):
        """Get all cart items for a user"""
        return cls.query.filter_by(user_id=user_id).all()

    @classmethod
    def get_cart_total(cls, user_id):
        """Calculate total for user's cart"""
        cart_items = cls.get_user_cart(user_id)
        return sum(item.subtotal for item in cart_items)

    @classmethod
    def clear_cart(cls, user_id):
        """Remove all items from user's cart"""
        return cls.query.filter_by(user_id=user_id).delete()

class OrderModel(db.Model):
    __tablename__ = 'orders'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, completed, cancelled
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    items = db.relationship('OrderItemModel', backref='order', lazy=True)

class OrderItemModel(db.Model):
    __tablename__ = 'order_items'
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price_at_time = db.Column(db.Float, nullable=False)  # Store the price at the time of order
