import json
import os
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings


class Command(BaseCommand):
    help = 'Gestiona la configuración de impresoras y balanzas en config.txt'
    
    def __init__(self):
        super().__init__()
        self.config_path = os.path.join(settings.BASE_DIR, 'core', 'config.txt')
    
    def add_arguments(self, parser):
        parser.add_argument(
            'action',
            choices=['add', 'remove', 'list', 'update'],
            help='Acción a realizar: add, remove, list, update'
        )
        parser.add_argument(
            'device_type',
            nargs='?',
            choices=['impresora', 'balanza'],
            help='Tipo de dispositivo: impresora o balanza'
        )
        parser.add_argument(
            '--nombre',
            type=str,
            help='Nombre del dispositivo'
        )
        parser.add_argument(
            '--ip',
            type=str,
            help='Dirección IP del dispositivo'
        )
    
    def load_config(self):
        """Carga la configuración desde el archivo JSON"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as file:
                return json.load(file)
        except FileNotFoundError:
            raise CommandError(f'Archivo de configuración no encontrado: {self.config_path}')
        except json.JSONDecodeError:
            raise CommandError('Error al leer el archivo de configuración. Formato JSON inválido.')
    
    def save_config(self, config):
        """Guarda la configuración en el archivo JSON"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as file:
                json.dump(config, file, indent=3, ensure_ascii=False)
            self.stdout.write(
                self.style.SUCCESS('Configuración guardada exitosamente.')
            )
        except Exception as e:
            raise CommandError(f'Error al guardar la configuración: {str(e)}')
    
    def list_devices(self, config, device_type=None):
        """Lista todos los dispositivos o de un tipo específico"""
        if device_type == 'impresora':
            self.stdout.write(self.style.HTTP_INFO('\n=== IMPRESORAS ==>'))
            for nombre, ip in config.get('IMPRESORAS', {}).items():
                self.stdout.write(f'  {nombre}: {ip}')
        elif device_type == 'balanza':
            self.stdout.write(self.style.HTTP_INFO('\n=== BALANZAS ==>'))
            for nombre, ip in config.get('BALANZAS', {}).items():
                self.stdout.write(f'  {nombre}: {ip}')
        else:
            # Listar todos
            self.stdout.write(self.style.HTTP_INFO('\n=== CONFIGURACIÓN COMPLETA ==>'))
            self.stdout.write(f'HOST: {config.get("HOST", "N/A")}')
            self.stdout.write(f'PORT: {config.get("PORT", "N/A")}')
            
            self.stdout.write(self.style.HTTP_INFO('\n=== IMPRESORAS ==>'))
            for nombre, ip in config.get('IMPRESORAS', {}).items():
                self.stdout.write(f'  {nombre}: {ip}')
            
            self.stdout.write(self.style.HTTP_INFO('\n=== BALANZAS ==>'))
            for nombre, ip in config.get('BALANZAS', {}).items():
                self.stdout.write(f'  {nombre}: {ip}')
    
    def add_device(self, config, device_type, nombre, ip):
        """Agrega un nuevo dispositivo"""
        section = 'IMPRESORAS' if device_type == 'impresora' else 'BALANZAS'
        
        # Verificar si ya existe
        if nombre in config.get(section, {}):
            raise CommandError(f'El dispositivo "{nombre}" ya existe en {section}.')
        
        # Inicializar sección si no existe
        if section not in config:
            config[section] = {}
        
        # Agregar dispositivo
        config[section][nombre] = ip
        
        self.stdout.write(
            self.style.SUCCESS(
                f'{device_type.capitalize()} "{nombre}" agregada con IP {ip}'
            )
        )
    
    def remove_device(self, config, device_type, nombre):
        """Elimina un dispositivo existente"""
        section = 'IMPRESORAS' if device_type == 'impresora' else 'BALANZAS'
        
        if section not in config or nombre not in config[section]:
            raise CommandError(f'El dispositivo "{nombre}" no existe en {section}.')
        
        # Eliminar dispositivo
        del config[section][nombre]
        
        self.stdout.write(
            self.style.SUCCESS(
                f'{device_type.capitalize()} "{nombre}" eliminada exitosamente'
            )
        )
    
    def update_device(self, config, device_type, nombre, ip):
        """Actualiza la IP de un dispositivo existente"""
        section = 'IMPRESORAS' if device_type == 'impresora' else 'BALANZAS'
        
        if section not in config or nombre not in config[section]:
            raise CommandError(f'El dispositivo "{nombre}" no existe en {section}.')
        
        old_ip = config[section][nombre]
        config[section][nombre] = ip
        
        self.stdout.write(
            self.style.SUCCESS(
                f'{device_type.capitalize()} "{nombre}" actualizada: {old_ip} -> {ip}'
            )
        )
    
    def handle(self, *args, **options):
        action = options['action']
        device_type = options['device_type']
        nombre = options['nombre']
        ip = options['ip']
        
        # Cargar configuración actual
        config = self.load_config()
        
        if action == 'list':
            self.list_devices(config, device_type)
            return
        
        # Validaciones para acciones que requieren device_type
        if not device_type:
            raise CommandError('Debe especificar el tipo de dispositivo (impresora o balanza)')
        
        if action == 'add':
            if not nombre or not ip:
                raise CommandError('Para agregar un dispositivo debe especificar --nombre e --ip')
            self.add_device(config, device_type, nombre, ip)
            self.save_config(config)
        
        elif action == 'remove':
            if not nombre:
                raise CommandError('Para eliminar un dispositivo debe especificar --nombre')
            self.remove_device(config, device_type, nombre)
            self.save_config(config)
        
        elif action == 'update':
            if not nombre or not ip:
                raise CommandError('Para actualizar un dispositivo debe especificar --nombre e --ip')
            self.update_device(config, device_type, nombre, ip)
            self.save_config(config)