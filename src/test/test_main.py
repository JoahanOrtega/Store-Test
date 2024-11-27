from api.models import ProductModel, db
from src.main import ShoppingCart
from flask import Flask
import pytest

@pytest.fixture
def app():
    # Configurar la aplicación Flask para pruebas
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'  # Base de datos en memoria
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)

    with app.app_context():
        db.create_all()
        # Crear productos de prueba
        db.session.add(ProductModel(name="Apple", description="Fresh Apple", price=1.0, stock=10))
        db.session.add(ProductModel(name="Banana", description="Ripe Banana", price=0.5, stock=15))
        db.session.add(ProductModel(name="Orange", description="Juicy Orange", price=0.8, stock=20))
        db.session.commit()

        yield app

        db.session.remove()
        db.drop_all()

@pytest.fixture
def cart():
    # Crear una instancia del carrito
    return ShoppingCart()

def test_add_single_item(app, cart):
    with app.app_context():
        cart.add_item(1)  # ID del producto "Apple"
        items = cart.get_items()
        assert len(items) == 1
        assert items[0].name == "Apple"

def test_add_multiple_items(app, cart):
    with app.app_context():
        cart.add_item(1)  # Apple
        cart.add_item(2)  # Banana
        cart.add_item(3)  # Orange
        items = cart.get_items()
        assert len(items) == 3
        assert items[0].name == "Apple"
        assert items[1].name == "Banana"
        assert items[2].name == "Orange"

def test_calculate_total(app, cart):
    with app.app_context():
        cart.add_item(1)  # Apple
        cart.add_item(2)  # Banana
        total = cart.calculate_total()
        assert total == 1.5  # Apple: 1.0 + Banana: 0.5

def test_remove_item(app, cart):
    with app.app_context():
        cart.add_item(1)  # Apple
        cart.add_item(2)  # Banana
        cart.remove_item(1)  # Remove Apple
        items = cart.get_items()
        assert len(items) == 1
        assert items[0].name == "Banana"

def test_out_of_stock(app, cart):
    with app.app_context():
        cart.add_item(1)  # Apple
        for _ in range(9):  # Agregar Apple hasta que se acabe el stock
            cart.add_item(1)
        with pytest.raises(Exception):
            cart.add_item(1)  # Intentar agregar cuando ya no hay stock
