from django import template
import locale

register = template.Library()

@register.filter
def format_number(value):
    """Formatea un número con separadores de miles (formato latino)"""
    try:
        # Convertir a float para mantener decimales
        num = float(value)
        # Formatear con separadores de miles (puntos) y decimales (comas)
        return "{:,.2f}".format(num).replace(",", "X").replace(".", ",").replace("X", ".")
    except (ValueError, TypeError):
        return value

@register.filter
def format_currency(value):
    """Formatea un número como moneda con separadores de miles (formato latino)"""
    try:
        # Convertir a float para mantener decimales
        num = float(value)
        # Formatear con separadores de miles (puntos) y decimales (comas)
        formatted = "{:,.2f}".format(num).replace(",", "X").replace(".", ",").replace("X", ".")
        return f"${formatted}"
    except (ValueError, TypeError):
        return value

@register.filter
def subtract(value, arg):
    """Resta dos valores"""
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        return 0 