#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para gestionar la configuración de impresoras y balanzas del sistema POS SCG
Uso independiente sin necesidad de Django

Ejemplos de uso:
  python config_cli.py list
  python config_cli.py add impresora --nombre "Caja1" --ip "192.168.1.200"
  python config_cli.py add balanza --nombre "ICM3" --ip "192.168.1.50"
  python config_cli.py remove impresora --nombre "Caja1"
  python config_cli.py update balanza --nombre "ICM1" --ip "192.168.1.105"
"""

import json
import os
import sys
import argparse
from pathlib import Path


class ConfigManager:
    def __init__(self):
        # Ruta al archivo de configuración
        self.script_dir = Path(__file__).parent
        self.config_path = self.script_dir / 'core' / 'core' / 'config.txt'
        
        if not self.config_path.exists():
            print(f"❌ Error: Archivo de configuración no encontrado en {self.config_path}")
            sys.exit(1)
    
    def load_config(self):
        """Carga la configuración desde el archivo JSON"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as file:
                return json.load(file)
        except json.JSONDecodeError as e:
            print(f"❌ Error: Formato JSON inválido en {self.config_path}")
            print(f"   Detalle: {str(e)}")
            sys.exit(1)
        except Exception as e:
            print(f"❌ Error al leer configuración: {str(e)}")
            sys.exit(1)
    
    def save_config(self, config):
        """Guarda la configuración en el archivo JSON"""
        try:
            # Crear backup antes de guardar
            backup_path = self.config_path.with_suffix('.txt.backup')
            if self.config_path.exists():
                import shutil
                shutil.copy2(self.config_path, backup_path)
            
            with open(self.config_path, 'w', encoding='utf-8') as file:
                json.dump(config, file, indent=3, ensure_ascii=False)
            
            print("✅ Configuración guardada exitosamente")
            
        except Exception as e:
            print(f"❌ Error al guardar configuración: {str(e)}")
            sys.exit(1)
    
    def list_devices(self, device_type=None):
        """Lista todos los dispositivos o de un tipo específico"""
        config = self.load_config()
        
        if device_type == 'impresora':
            print("\n🖨️  === IMPRESORAS ===")
            impresoras = config.get('IMPRESORAS', {})
            if not impresoras:
                print("   No hay impresoras configuradas")
            else:
                for nombre, ip in impresoras.items():
                    print(f"   📍 {nombre}: {ip}")
        
        elif device_type == 'balanza':
            print("\n⚖️  === BALANZAS ===")
            balanzas = config.get('BALANZAS', {})
            if not balanzas:
                print("   No hay balanzas configuradas")
            else:
                for nombre, ip in balanzas.items():
                    print(f"   📍 {nombre}: {ip}")
        
        else:
            # Listar todo
            print("\n🔧 === CONFIGURACIÓN COMPLETA ===")
            print(f"🌐 HOST: {config.get('HOST', 'N/A')}")
            print(f"🔌 PORT: {config.get('PORT', 'N/A')}")
            
            print("\n🖨️  === IMPRESORAS ===")
            impresoras = config.get('IMPRESORAS', {})
            if not impresoras:
                print("   No hay impresoras configuradas")
            else:
                for nombre, ip in impresoras.items():
                    print(f"   📍 {nombre}: {ip}")
            
            print("\n⚖️  === BALANZAS ===")
            balanzas = config.get('BALANZAS', {})
            if not balanzas:
                print("   No hay balanzas configuradas")
            else:
                for nombre, ip in balanzas.items():
                    print(f"   📍 {nombre}: {ip}")
        
        print()  # Línea en blanco al final
    
    def add_device(self, device_type, nombre, ip):
        """Agrega un nuevo dispositivo"""
        config = self.load_config()
        section = 'IMPRESORAS' if device_type == 'impresora' else 'BALANZAS'
        
        # Validar IP básica
        if not self._validate_ip(ip):
            print(f"❌ Error: IP inválida '{ip}'. Debe tener formato xxx.xxx.xxx.xxx")
            sys.exit(1)
        
        # Verificar si ya existe
        if section in config and nombre in config[section]:
            print(f"❌ Error: El dispositivo '{nombre}' ya existe en {section}")
            print(f"   IP actual: {config[section][nombre]}")
            print(f"   Use 'update' para cambiar la IP")
            sys.exit(1)
        
        # Inicializar sección si no existe
        if section not in config:
            config[section] = {}
        
        # Agregar dispositivo
        config[section][nombre] = ip
        self.save_config(config)
        
        emoji = "🖨️" if device_type == 'impresora' else "⚖️"
        print(f"✅ {emoji} {device_type.capitalize()} '{nombre}' agregada con IP {ip}")
    
    def remove_device(self, device_type, nombre):
        """Elimina un dispositivo existente"""
        config = self.load_config()
        section = 'IMPRESORAS' if device_type == 'impresora' else 'BALANZAS'
        
        if section not in config or nombre not in config[section]:
            print(f"❌ Error: El dispositivo '{nombre}' no existe en {section}")
            self._show_available_devices(config, section)
            sys.exit(1)
        
        # Confirmar eliminación
        ip = config[section][nombre]
        respuesta = input(f"⚠️  ¿Está seguro de eliminar '{nombre}' ({ip})? [s/N]: ")
        if respuesta.lower() not in ['s', 'si', 'sí', 'y', 'yes']:
            print("❌ Operación cancelada")
            return
        
        # Eliminar dispositivo
        del config[section][nombre]
        self.save_config(config)
        
        emoji = "🖨️" if device_type == 'impresora' else "⚖️"
        print(f"✅ {emoji} {device_type.capitalize()} '{nombre}' eliminada exitosamente")
    
    def update_device(self, device_type, nombre, ip):
        """Actualiza la IP de un dispositivo existente"""
        config = self.load_config()
        section = 'IMPRESORAS' if device_type == 'impresora' else 'BALANZAS'
        
        # Validar IP básica
        if not self._validate_ip(ip):
            print(f"❌ Error: IP inválida '{ip}'. Debe tener formato xxx.xxx.xxx.xxx")
            sys.exit(1)
        
        if section not in config or nombre not in config[section]:
            print(f"❌ Error: El dispositivo '{nombre}' no existe en {section}")
            self._show_available_devices(config, section)
            sys.exit(1)
        
        old_ip = config[section][nombre]
        if old_ip == ip:
            print(f"⚠️  La IP '{ip}' ya está asignada al dispositivo '{nombre}'")
            return
        
        # Actualizar IP
        config[section][nombre] = ip
        self.save_config(config)
        
        emoji = "🖨️" if device_type == 'impresora' else "⚖️"
        print(f"✅ {emoji} {device_type.capitalize()} '{nombre}' actualizada: {old_ip} -> {ip}")
    
    def _validate_ip(self, ip):
        """Validación básica de formato IP"""
        try:
            parts = ip.split('.')
            if len(parts) != 4:
                return False
            for part in parts:
                if not (0 <= int(part) <= 255):
                    return False
            return True
        except ValueError:
            return False
    
    def _show_available_devices(self, config, section):
        """Muestra los dispositivos disponibles en una sección"""
        devices = config.get(section, {})
        if devices:
            print(f"\n📋 Dispositivos disponibles en {section}:")
            for nombre, ip in devices.items():
                print(f"   📍 {nombre}: {ip}")
        else:
            print(f"\n📋 No hay dispositivos configurados en {section}")


def main():
    parser = argparse.ArgumentParser(
        description='Gestor de configuración para impresoras y balanzas del sistema POS SCG',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  %(prog)s list
  %(prog)s list impresora
  %(prog)s add impresora --nombre "Caja1" --ip "192.168.1.200"
  %(prog)s add balanza --nombre "ICM3" --ip "192.168.1.50"
  %(prog)s remove impresora --nombre "Caja1"
  %(prog)s update balanza --nombre "ICM1" --ip "192.168.1.105"
        """
    )
    
    parser.add_argument(
        'action',
        choices=['add', 'remove', 'list', 'update'],
        help='Acción a realizar'
    )
    
    parser.add_argument(
        'device_type',
        nargs='?',
        choices=['impresora', 'balanza'],
        help='Tipo de dispositivo (requerido para add, remove, update)'
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
    
    args = parser.parse_args()
    
    # Crear instancia del gestor
    manager = ConfigManager()
    
    try:
        if args.action == 'list':
            manager.list_devices(args.device_type)
        
        elif args.action == 'add':
            if not args.device_type:
                print("❌ Error: Debe especificar el tipo de dispositivo (impresora o balanza)")
                sys.exit(1)
            if not args.nombre or not args.ip:
                print("❌ Error: Para agregar un dispositivo debe especificar --nombre e --ip")
                sys.exit(1)
            manager.add_device(args.device_type, args.nombre, args.ip)
        
        elif args.action == 'remove':
            if not args.device_type:
                print("❌ Error: Debe especificar el tipo de dispositivo (impresora o balanza)")
                sys.exit(1)
            if not args.nombre:
                print("❌ Error: Para eliminar un dispositivo debe especificar --nombre")
                sys.exit(1)
            manager.remove_device(args.device_type, args.nombre)
        
        elif args.action == 'update':
            if not args.device_type:
                print("❌ Error: Debe especificar el tipo de dispositivo (impresora o balanza)")
                sys.exit(1)
            if not args.nombre or not args.ip:
                print("❌ Error: Para actualizar un dispositivo debe especificar --nombre e --ip")
                sys.exit(1)
            manager.update_device(args.device_type, args.nombre, args.ip)
    
    except KeyboardInterrupt:
        print("\n❌ Operación cancelada por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error inesperado: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()