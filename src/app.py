from flask import Flask
from api.controllers import Product, Products  # Importar los controladores de productos
from api.extensions import db  # Extensión para la base de datos
from flask_restful import Api

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'  # Base de datos SQLite
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # Desactivar advertencias innecesarias
db.init_app(app)  # Inicializar la base de datos
api = Api(app)

# Crear la base de datos y las tablas
with app.app_context():
    db.create_all()

# Registrar las rutas para los recursos
api.add_resource(Products, "/api/products")  # Ruta para la colección de productos
api.add_resource(Product, "/api/product/<int:product_id>")  # Ruta para un producto específico

@app.route("/")
def hello_world():
    return "<p>Welcome to the Product Inventory API!</p>"

if __name__ == "__main__":
    app.run(debug=True)
