from typing import List
from datetime import datetime
from flask import app
from api.models import UserModel, ProductModel, CartModel, OrderModel, db

class StoreManagementSystem:
    def __init__(self):
        self.context_initialized = False

    def initialize_context(self):
        if not self.context_initialized:
            with app.app_context():
                db.create_all()
            self.context_initialized = True

    def add_user(self, username: str, email: str):
        username = username.strip()
        email = email.strip()
        print(f"Intentando registrar cliente: {username}, {email}")
        with app.app_context():
            if UserModel.query.filter_by(username=username).first():
                print(f"El cliente '{username}' ya existe.")
                return
            if UserModel.query.filter_by(email=email).first():
                print(f"El email '{email}' ya está registrado.")
                return
            user = UserModel(username=username, email=email)
            db.session.add(user)
            db.session.commit()
            print(f"Cliente registrado: {username}")

    def add_product(self, name: str, description: str, price: float, stock: int):
        name = name.strip()
        print(f"Intentando agregar producto: {name}, precio: ${price}, stock: {stock}")
        with app.app_context():
            product = ProductModel(
                name=name,
                description=description,
                price=price,
                stock=stock
            )
            db.session.add(product)
            db.session.commit()
            print(f"Producto agregado: {name}")

    def add_to_cart(self, user_id: int, product_id: int, quantity: int):
        print(f"Agregando al carrito: usuario_id={user_id}, producto_id={product_id}, cantidad={quantity}")
        with app.app_context():
            product = ProductModel.query.get(product_id)
            if not product:
                print("El producto no existe.")
                return
            if product.stock < quantity:
                print("No hay suficiente stock disponible.")
                return
            
            cart_item = CartModel.query.filter_by(
                user_id=user_id, 
                product_id=product_id
            ).first()
            
            if cart_item:
                cart_item.quantity += quantity
            else:
                cart_item = CartModel(
                    user_id=user_id,
                    product_id=product_id,
                    quantity=quantity
                )
                db.session.add(cart_item)
            
            product.stock -= quantity
            db.session.commit()
            print("Producto agregado al carrito con éxito.")

    def create_order(self, user_id: int, shipping_address: str):
        print(f"Creando orden para usuario_id={user_id}")
        with app.app_context():
            cart_items = CartModel.query.filter_by(user_id=user_id).all()
            if not cart_items:
                print("El carrito está vacío.")
                return

            total_amount = 0
            for item in cart_items:
                product = ProductModel.query.get(item.product_id)
                total_amount += product.price * item.quantity

            order = OrderModel(
                user_id=user_id,
                order_date=datetime.now(),
                total_amount=total_amount,
                shipping_address=shipping_address,
                status="pending"
            )
            db.session.add(order)
            
            # Clear cart after order creation
            for item in cart_items:
                db.session.delete(item)
                
            db.session.commit()
            print(f"Orden creada con éxito. Total: ${total_amount:.2f}")

    def list_products(self):
        with app.app_context():
            products = ProductModel.query.all()
            print("Productos disponibles:")
            for product in products:
                print(f"- {product.id}: {product.name} (Precio: ${product.price:.2f}, Stock: {product.stock})")

    def list_cart(self, user_id: int):
        with app.app_context():
            cart_items = CartModel.query.filter_by(user_id=user_id).all()
            print(f"Carrito del usuario {user_id}:")
            total = 0
            for item in cart_items:
                product = ProductModel.query.get(item.product_id)
                subtotal = product.price * item.quantity
                total += subtotal
                print(f"- {product.name}: {item.quantity} x ${product.price:.2f} = ${subtotal:.2f}")
            print(f"Total: ${total:.2f}")

    def list_orders(self, user_id: int):
        with app.app_context():
            orders = OrderModel.query.filter_by(user_id=user_id).all()
            print(f"Órdenes del usuario {user_id}:")
            for order in orders:
                print(f"- Orden #{order.id}: ${order.total_amount:.2f} ({order.status})")
                print(f"  Fecha: {order.order_date}")
                print(f"  Dirección de envío: {order.shipping_address}")

if __name__ == "__main__":
    system = StoreManagementSystem()
    system.initialize_context()

    # Agregar usuarios
    system.add_user("cliente1", "cliente1@example.com")
    system.add_user("cliente2", "cliente2@example.com")

    # Agregar productos
    system.add_product("Laptop", "Laptop gaming de última generación", 1299.99, 10)
    system.add_product("Mouse", "Mouse inalámbrico ergonómico", 49.99, 50)

    # Listar productos
    system.list_products()

    # Agregar productos al carrito
    system.add_to_cart(1, 1, 1)  # Usuario 1 compra 1 laptop
    system.add_to_cart(1, 2, 2)  # Usuario 1 compra 2 mouse

    # Ver carrito
    system.list_cart(1)

    # Crear orden
    system.create_order(1, "Calle Principal 123, Ciudad")

    # Ver órdenes
    system.list_orders(1)
