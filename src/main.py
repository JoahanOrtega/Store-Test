from typing import List
from api.models import ProductModel
from flask import abort

class ShoppingCart:
    def __init__(self):
        # Lista para almacenar los productos del carrito
        self.items: List[ProductModel] = []

    def add_item(self, product_id: int):
        # Buscar el producto en la base de datos por ID
        product = ProductModel.query.filter_by(id=product_id).first()
        if not product:
            abort(404, description="Product not found")
        
        # Validar si hay stock disponible
        if product.stock <= 0:
            abort(400, description="Product is out of stock")
        
        # Agregar el producto al carrito y reducir el stock
        self.items.append(product)
        product.stock -= 1
        return f"Added {product.name} to the cart."

    def size(self) -> int:
        # Retorna el número de productos en el carrito
        return len(self.items)

    def get_items(self) -> List[ProductModel]:
        # Retorna la lista de productos en el carrito
        return self.items

    def calculate_total(self) -> float:
        # Calcula el costo total de los productos en el carrito
        return sum(product.price for product in self.items)

    def remove_item(self, product_id: int):
        # Elimina un producto específico del carrito
        product_to_remove = None
        for product in self.items:
            if product.id == product_id:
                product_to_remove = product
                break

        if not product_to_remove:
            abort(404, description="Product not found in cart")

        # Restaurar el stock y eliminar el producto del carrito
        product_to_remove.stock += 1
        self.items.remove(product_to_remove)
        return f"Removed {product_to_remove.name} from the cart."
