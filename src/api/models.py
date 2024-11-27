from .extensions import db

class ProductModel(db.Model):
    id = db.Column(db.Integer, primary_key=True)  # Identificador único del producto
    name = db.Column(db.String(100), unique=True, nullable=False)  # Nombre del producto
    description = db.Column(db.String(255), nullable=True)  # Descripción del producto
    price = db.Column(db.Float, nullable=False)  # Precio del producto
    stock = db.Column(db.Integer, nullable=False, default=0)  # Cantidad en inventario
    category = db.Column(db.String(50), nullable=True)  # Categoría del producto
    created_at = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())  # Fecha de creación

    def __repr__(self):
        return f'<Product {self.name}>'
