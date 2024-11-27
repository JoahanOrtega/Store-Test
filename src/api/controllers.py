#Aquí se colocan los metodos para agregar POST, Editar PUT, Obtener GET y eliminar DELETE

from flask import Response
from flask_restful import Api, Resource, reqparse, abort, fields, marshal_with
from api.models import ProductModel, db
import json

# Argumentos para las solicitudes
product_args = reqparse.RequestParser()
product_args.add_argument("name", type=str, help="Product name is required", required=True)
product_args.add_argument("description", type=str, help="Product description")
product_args.add_argument("price", type=float, help="Product price is required", required=True)
product_args.add_argument("stock", type=int, help="Product stock is required", required=True)
product_args.add_argument("category", type=str, help="Product category")

# Esquema de los campos para la serialización
productFields = {
    "id": fields.Integer,
    "name": fields.String,
    "description": fields.String,
    "price": fields.Float,
    "stock": fields.Integer,
    "category": fields.String,
    "created_at": fields.String
}

# Controlador para la colección de productos
class Products(Resource):
    @marshal_with(productFields)
    def post(self):
        args = product_args.parse_args()

        # Validar el nombre del producto
        if not args['name'] or args['name'].isspace():
            response = Response(json.dumps({'error': 'Product name cannot be empty'}),
                                status=400,
                                mimetype='application/json')
            return abort(response)

        # Validar el precio y el stock
        if args['price'] <= 0:
            response = Response(json.dumps({'error': 'Price must be greater than zero'}),
                                status=400,
                                mimetype='application/json')
            return abort(response)
        if args['stock'] < 0:
            response = Response(json.dumps({'error': 'Stock cannot be negative'}),
                                status=400,
                                mimetype='application/json')
            return abort(response)

        # Crear el producto
        product = ProductModel(
            name=args['name'].strip(),
            description=args['description'],
            price=args['price'],
            stock=args['stock'],
            category=args['category']
        )
        db.session.add(product)
        db.session.commit()
        return product, 201

    @marshal_with(productFields)
    def get(self):
        products = ProductModel.query.all()
        return products


# Controlador para un producto específico
class Product(Resource):
    @marshal_with(productFields)
    def get(self, product_id):
        product = ProductModel.query.filter_by(id=product_id).first()
        if not product:
            abort(404, message="Product not found")
        return product

    @marshal_with(productFields)
    def put(self, product_id):
        args = product_args.parse_args()
        product = ProductModel.query.get(product_id)
        if not product:
            abort(404, message="Product not found")

        # Actualizar los campos
        product.name = args['name']
        product.description = args['description']
        product.price = args['price']
        product.stock = args['stock']
        product.category = args['category']
        db.session.commit()
        return product, 200

    def delete(self, product_id):
        product = ProductModel.query.get(product_id)
        if not product:
            abort(404, message="Product not found")

        db.session.delete(product)
        db.session.commit()
        return '', 204
