from django.http import JsonResponse
from django.conf import settings
from urllib.parse import quote
from .models import CategoriasProductos, Producto


class CategoriaSerializer:
    """
    Serializer para categorías que mapea campos Django a interfaz React Native
    
    Mapeo:
    - id → id (convertir a string)
    - nombre → title
    - imagen → image (manejar valores nulos con URL por defecto)
    """
    
    @staticmethod
    def serialize(categoria):
        # Generar URL de imagen
        if categoria.imagen and categoria.imagen.strip():
            # Si tiene imagen específica, usarla
            image_url = categoria.imagen
            # Si no es una URL completa, construir la URL del servidor
            if not image_url.startswith(('http://', 'https://')):
                # Obtener la URL base del servidor
                base_url = getattr(settings, 'API_BASE_URL', 'http://192.168.1.107:8004')
                # Si la imagen ya empieza con "/" es una ruta absoluta del servidor
                if image_url.startswith('/'):
                    image_url = f"{base_url}{image_url}"
                else:
                    # Si no, es relativa al directorio media
                    image_url = f"{base_url}/media/{image_url}"
        else:
            # URL de imagen por defecto usando el nombre de la categoría
            encoded_name = quote(categoria.nombre)
            base_url = getattr(settings, 'API_BASE_URL', 'http://192.168.1.107:8004')
            image_url = f"{base_url}/media/{encoded_name}.png"
        
        return {
            "id": str(categoria.id),
            "title": categoria.nombre,
            "image": image_url
        }
    
    @staticmethod
    def serialize_list(categorias):
        """Serializa una lista de categorías ordenadas por campo orden"""
        return [CategoriaSerializer.serialize(categoria) for categoria in categorias]


class ProductoSerializer:
    """
    Serializer para productos que mapea campos Django a interfaz React Native
    
    Mapeo:
    - id → id (convertir a string)
    - nombre → title
    - precio_detal → price
    - imagen → image (manejar valores nulos con URL por defecto)
    - moneda → currency
    - unidad → unit (convertir 'K' a 'KG')
    - categoria → categoryId (tomar la primera categoría)
    """
    
    @staticmethod
    def serialize(producto):
        # Generar URL de imagen
        if producto.imagen and producto.imagen.strip():
            # Si tiene imagen específica, usarla
            image_url = producto.imagen
            # Si no es una URL completa, construir la URL del servidor
            if not image_url.startswith(('http://', 'https://')):
                # Obtener la URL base del servidor
                base_url = getattr(settings, 'API_BASE_URL', 'http://192.168.1.107:8004')
                
                # Si la imagen ya empieza con "/" es una ruta absoluta del servidor
                if image_url.startswith('/'):
                    image_url = f"{base_url}{image_url}"
                else:
                    # Si no, es relativa al directorio media
                    # Si la imagen no tiene extensión, agregar .png
                    if not image_url.endswith(('.png', '.jpg', '.jpeg', '.webp', '.gif')):
                        image_url = f"{image_url}.png"
                    image_url = f"{base_url}/media/{image_url}"
        else:
            # URL de imagen por defecto usando el nombre del producto
            encoded_name = quote(producto.nombre)
            base_url = getattr(settings, 'API_BASE_URL', 'http://192.168.1.107:8004')
            image_url = f"{base_url}/media/{encoded_name}.png"
        
        # Convertir unidad 'K' a 'KG' para React Native
        unit = "KG" if producto.unidad == "K" else producto.unidad
        
        # Tomar la primera categoría como categoryId principal
        categorias = producto.categoria.all()
        category_id = str(categorias.first().id) if categorias.exists() else "1"
        
        return {
            "id": str(producto.id),
            "title": producto.nombre,
            "price": float(producto.precio_detal),
            "image": image_url,
            "currency": producto.moneda,
            "unit": unit,
            "categoryId": category_id
        }
    
    @staticmethod
    def serialize_list(productos):
        """Serializa una lista de productos ordenados alfabéticamente por nombre"""
        return [ProductoSerializer.serialize(producto) for producto in productos] 