# API RESTful Documentation

Este proyecto proporciona una API RESTful desarrollada con Flask para gestionar usuarios, categorías, productos, carritos y pedidos. A continuación, se describen las rutas disponibles y los detalles para utilizarlas.

## Índice
1. [Usuarios](#usuarios)
2. [Categorías](#categorías)
3. [Productos](#productos)
4. [Carrito](#carrito)
5. [Pedidos](#pedidos)

---

## Usuarios

### Crear un usuario
**URL:** `POST /api/users`  
**Descripción:** Crea un nuevo usuario en el sistema.  

**Cuerpo de la solicitud (JSON):**
```json
{
    "username": "john_doe",
    "email": "john@example.com",
    "password": "secure123"
}
Respuesta esperada:

    Código 201: Usuario creado exitosamente.
    Código 400: Error en los datos proporcionados.

Categorías
Crear una categoría

URL: POST /api/categories
Descripción: Agrega una nueva categoría de productos.

Cuerpo de la solicitud (JSON):

{
    "name": "Electronics",
    "description": "Electronic devices and accessories"
}

Respuesta esperada:

    Código 201: Categoría creada exitosamente.
    Código 400: Error en los datos proporcionados.

Productos
Crear un producto

URL: POST /api/products
Descripción: Agrega un nuevo producto a una categoría existente.

Cuerpo de la solicitud (JSON):

{
    "name": "Smartphone",
    "description": "Latest model smartphone",
    "price": 699.99,
    "stock": 50,
    "category_id": 1
}

Respuesta esperada:

    Código 201: Producto creado exitosamente.
    Código 400: Error en los datos proporcionados.

Carrito
Agregar productos al carrito

URL: POST /api/cart/<user_id>
Descripción: Agrega productos al carrito de un usuario especificado por user_id.

Cuerpo de la solicitud (JSON):

{
    "product_id": 1,
    "quantity": 2
}

Respuesta esperada:

    Código 200: Producto agregado al carrito.
    Código 404: Usuario o producto no encontrado.

Pedidos
Crear un pedido

URL: POST /api/orders
Descripción: Genera un pedido basado en los productos seleccionados por el usuario.

Cuerpo de la solicitud (JSON):

{
    "user_id": 1,
    "items": [
        {
            "product_id": 1,
            "quantity": 2
        }
    ]
}

Respuesta esperada:

    Código 201: Pedido creado exitosamente.
    Código 400: Error en los datos proporcionados.