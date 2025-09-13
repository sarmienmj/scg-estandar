from django.utils.deprecation import MiddlewareMixin
from django.http import HttpResponse


class CorsMiddleware(MiddlewareMixin):
    """
    Middleware personalizado para manejar CORS para la API React Native
    """
    
    def process_request(self, request):
        """
        Procesar petición OPTIONS para CORS preflight
        """
        if request.method == 'OPTIONS':
            response = HttpResponse()
            return self.add_cors_headers(response, request)
        return None
    
    def process_response(self, request, response):
        """
        Agregar headers CORS a todas las respuestas
        """
        return self.add_cors_headers(response, request)
    
    def add_cors_headers(self, response, request):
        """
        Agregar headers CORS necesarios
        """
        # Permitir todos los orígenes (para desarrollo)
        response['Access-Control-Allow-Origin'] = '*'
        
        # Headers permitidos
        response['Access-Control-Allow-Headers'] = (
            'accept, accept-encoding, authorization, content-type, dnt, '
            'origin, user-agent, x-csrftoken, x-requested-with'
        )
        
        # Métodos HTTP permitidos
        response['Access-Control-Allow-Methods'] = (
            'DELETE, GET, OPTIONS, PATCH, POST, PUT'
        )
        
        # Permitir credenciales
        response['Access-Control-Allow-Credentials'] = 'true'
        
        # Tiempo de cache para preflight
        response['Access-Control-Max-Age'] = '3600'
        
        return response 