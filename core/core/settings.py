import json
from pathlib import Path
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "django-insecure-yv8w$9u_%i!h7r!1jb45(anmbmlfg80=z*c$mt_&#-2e@i08lp"

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ["*"]


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "pos",
    "bootstrap5",
    # "django_extensions"  # Comentado temporalmente - no está instalado
]

LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/" 

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "pos.middleware.CorsMiddleware",  # CORS para API React Native
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    #"django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "core.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, 'templates')],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "pos.context_processors.sucursal_processor",
            ],
        },
    },
]

WSGI_APPLICATION = "core.wsgi.application"
ASGI_APPLICATION = "core.asgi.application"


# Database
# https://docs.djangoproject.com/en/4.1/ref/settings/#databases

# Configuración PostgreSQL (comentada temporalmente - para reactivar cuando instales PostgreSQL)
# Configuración PostgreSQL (comentada temporalmente - para reactivar cuando instales PostgreSQL)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'scgdb',
        'USER': 'scg',
        'PASSWORD': 'django',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}



# Password validation
# https://docs.djangoproject.com/en/4.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [

]
INTERNAL_IPS = [
    # ...
    "127.0.0.1",
    # ...
]

# Internationalization
# https://docs.djangoproject.com/en/4.1/topics/i18n/

LANGUAGE_CODE = "es-es"

TIME_ZONE = "America/Caracas"
DATE_FORMAT = 'd/m/Y'
DATETIME_FORMAT = 'd/m/Y h:i:s A'
SHORT_DATE_FORMAT = 'd/m/Y'
SHORT_DATETIME_FORMAT = 'd/m/Y h:i A'

USE_I18N = True
USE_L10N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.1/howto/static-files/


STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]

MEDIA_ROOT= os.path.join(BASE_DIR, "media")
MEDIA_URL= "/media/"

# Default primary key field type
# https://docs.djangoproject.com/en/4.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# Configuración HTTPS
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# Configuración adicional para SSL/HTTPS con uvicorn
SECURE_SSL_REDIRECT = False  # No redirigir HTTP a HTTPS automáticamente
SECURE_HSTS_SECONDS = 0  # Desactivar HSTS para desarrollo
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False

# Configuración de cookies para HTTPS
SESSION_COOKIE_SECURE = False  # Para desarrollo local
CSRF_COOKIE_SECURE = False  # Para desarrollo local
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True

# Configuración de CORS y Host seguro
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
SECURE_CROSS_ORIGIN_OPENER_POLICY = 'same-origin'

# Configuración de Logging - Bloquear todos los logs GET (Django + Werkzeug)
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'filters': {
        'block_http_requests': {
            '()': 'django.utils.log.CallbackFilter',
            'callback': lambda record: not (
                # Bloquear logs que contengan direcciones IP y métodos HTTP
                any(method in str(record.getMessage()) for method in ['GET /', 'POST /', 'PUT /', 'DELETE /']) or
                # Bloquear logs de Werkzeug con formato IP - - [fecha] "método..."
                '] "GET /' in str(record.getMessage()) or
                '] "POST /' in str(record.getMessage()) or
                # Bloquear logs específicos de archivos estáticos y media
                any(path in str(record.getMessage()) for path in ['/static/', '/media/']) or
                # Bloquear logs de Not Found
                'Not Found:' in str(record.getMessage()) or
                # Bloquear logs con códigos de respuesta HTTP
                any(code in str(record.getMessage()) for code in [' 200 -', ' 404 -', ' 301 -', ' 302 -']) or
                # Bloquear por formato de IP
                any(ip_pattern in str(record.getMessage()) for ip_pattern in ['192.168.', '127.0.0.1', '0.0.0.0'])
            )
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
            'filters': ['block_http_requests'],
        },
        'file': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': 'django_errors.log',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'filters': ['block_http_requests'],
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
            'filters': ['block_http_requests'],
        },
        'django.server': {
            'handlers': [],
            'level': 'ERROR',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['file'],
            'level': 'ERROR',
            'propagate': False,
        },
        'werkzeug': {
            'handlers': [],  # Bloquear completamente logs de Werkzeug
            'level': 'ERROR',
            'propagate': False,
        },
    },
}

# Configuración adicional para Werkzeug/runserver_plus
import logging
import sys

# Silenciar completamente Werkzeug
werkzeug_logger = logging.getLogger('werkzeug')
werkzeug_logger.setLevel(logging.ERROR)
werkzeug_logger.disabled = True

# También silenciar el logger root de Werkzeug que puede aparecer
class WerkzeugFilter(logging.Filter):
    def filter(self, record):
        # Bloquear cualquier log que contenga patrones de Werkzeug
        message = str(record.getMessage())
        return not (
            '192.168.' in message or
            '127.0.0.1' in message or
            '] "GET /' in message or
            '] "POST /' in message or
            ' 200 -' in message or
            ' 404 -' in message or
            '/static/' in message or
            '/media/' in message
        )

# Aplicar filtro a todos los handlers de logging
for handler in logging.root.handlers:
    handler.addFilter(WerkzeugFilter())

# =============================================================================
# CONFIGURACIÓN DEL NEGOCIO
# =============================================================================

# Nombre de la sucursal/negocio (configurable)
SUCURSAL = "LOS CHAMITOS"

# URL base para la API (usado por serializers para generar URLs de imágenes)
API_BASE_URL = "http://192.168.1.107:8004"

# =============================================================================
# CONFIGURACIÓN DE CORS PARA API REACT NATIVE
# =============================================================================

# Permitir CORS para aplicación React Native
CORS_ALLOW_ALL_ORIGINS = True  # En producción, usar CORS_ALLOWED_ORIGINS

# Headers permitidos para CORS
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

# Métodos HTTP permitidos
CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]

# Permitir credenciales
CORS_ALLOW_CREDENTIALS = True

# =============================================================================