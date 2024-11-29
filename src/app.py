from flask import Flask
from flask_restful import Api
from api.extensions import db
from api.controllers import Products, Categories, Orders, Users, Cart

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///store.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
api = Api(app)

with app.app_context():
    db.init_app(app)
    db.create_all()

# Store API Routes
api.add_resource(Products, '/api/products', '/api/products/<int:product_id>')   # CRUD for products
api.add_resource(Categories, '/api/categories', '/api/categories/<int:category_id>')    # CRUD for product categories
api.add_resource(Orders, '/api/orders', '/api/orders/<int:order_id>')   # CRUD for customer orders
api.add_resource(Users, '/api/users', '/api/users/<int:user_id>')   # CRUD for customers
# Shopping cart operations
api.add_resource(Cart, '/api/cart', '/api/cart/<int:user_id>', '/api/cart/<int:user_id>/<int:product_id>')

if __name__ == '__main__':
    app.run(debug=True)
