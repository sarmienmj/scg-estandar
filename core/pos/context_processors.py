from django.conf import settings
from constance import config

def sucursal_processor(request):
    """
    Context processor para hacer disponible la configuración en todos los templates
    """
    return {
        'SUCURSAL': config.BUSINESS_NAME,
        'BUSINESS_NAME': config.BUSINESS_NAME,
        'BUSINESS_LOGO': config.BUSINESS_LOGO,
    } 