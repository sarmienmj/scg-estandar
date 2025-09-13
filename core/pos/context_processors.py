from django.conf import settings

def sucursal_processor(request):
    """
    Context processor para hacer disponible la variable SUCURSAL en todos los templates
    """
    return {
        'SUCURSAL': getattr(settings, 'SUCURSAL', 'LOCAL')
    } 