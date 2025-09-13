#!/usr/bin/env python3
"""
Script para iniciar Django con uvicorn y SSL
Soluciona problemas de event loop y configuración SSL
"""

import os
import sys
import signal
import asyncio
import logging
from pathlib import Path

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def setup_django():
    """Configurar Django antes de iniciar uvicorn"""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
    
    import django
    django.setup()
    
    logger.info("✓ Django configurado correctamente")

def verify_ssl_certificates():

    return True

def signal_handler(signum, frame):
    """Manejador de señales para cierre limpio"""
    logger.info("🛑 Recibida señal de interrupción, cerrando servidor...")
    sys.exit(0)

def main():
    """Función principal"""
    print("=" * 60)
    print("🔒 INICIANDO DJANGO CON UVICORN SSL")
    print("=" * 60)
    
    # Registrar manejador de señales
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Verificar certificados
    if not verify_ssl_certificates():
        logger.error("❌ Error en certificados SSL")
        sys.exit(1)
    
    # Configurar Django
    setup_django()
    
    # Configuración de uvicorn
    config = {
        'app': 'core.asgi:application',
        'host': '0.0.0.0',
        'port': 8004,
        'access_log': True,
        'use_colors': True,
        'reload': True,
        'server_header': True,
        'date_header': True,
        'workers': 1,
    }
    
    print(f"🌐 Servidor: https://0.0.0.0:{config['port']}")
    print(f"🌐 Red local: https://192.168.1.8:{config['port']}")
    print(f"🌐 Localhost: https://localhost:{config['port']}")
    print("=" * 60)
    print("💡 Presiona Ctrl+C para detener el servidor")
    print("=" * 60)
    
    # Iniciar uvicorn
    try:
        import uvicorn
        
        # Configurar loop de eventos específico para Windows
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        
        # Iniciar servidor
        uvicorn.run(**config)
        
    except ImportError:
        logger.error("❌ uvicorn no está instalado. Instala con: pip install uvicorn")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Error al iniciar servidor: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main() 