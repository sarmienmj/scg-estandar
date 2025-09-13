from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from pos.models import Cliente, Credito, CreditoAbono, estadoCaja
import json
from datetime import datetime


class Command(BaseCommand):
    help = 'Restaura créditos y abonos desde un archivo de backup JSON'
    
    def add_arguments(self, parser):
        parser.add_argument(
            'backup_file',
            type=str,
            help='Ruta del archivo de backup JSON a restaurar'
        )
        parser.add_argument(
            '--confirmar',
            action='store_true',
            help='Confirma que deseas ejecutar la restauración (requerido)'
        )
    
    def handle(self, *args, **options):
        if not options['confirmar']:
            self.stdout.write(
                self.style.WARNING(
                    '⚠️  OPERACIÓN DE RESTAURACIÓN\n'
                    'Para continuar, usa: --confirmar\n'
                    'Ejemplo: python manage.py restaurar_creditos backup_creditos.json --confirmar'
                )
            )
            return
        
        backup_file = options['backup_file']
        
        try:
            with open(backup_file, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
            
            self.stdout.write(f"📁 Cargando backup desde: {backup_file}")
            self.stdout.write(f"📅 Fecha backup: {backup_data.get('timestamp', 'No disponible')}")
            self.stdout.write(f"📊 Datos a restaurar:")
            self.stdout.write(f"   • Clientes: {len(backup_data.get('clientes', []))}")
            self.stdout.write(f"   • Créditos: {len(backup_data.get('creditos', []))}")
            self.stdout.write(f"   • Abonos: {len(backup_data.get('abonos', []))}")
            
            # Confirmación final
            confirm = input("\n🚨 ¿CONTINUAR CON LA RESTAURACIÓN? Escribe 'CONFIRMAR': ")
            if confirm != 'CONFIRMAR':
                self.stdout.write(self.style.ERROR("❌ Restauración cancelada"))
                return
            
            # Ejecutar restauración
            with transaction.atomic():
                self.restaurar_creditos(backup_data)
                self.stdout.write(self.style.SUCCESS("✅ Restauración completada exitosamente"))
                
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f"❌ Archivo no encontrado: {backup_file}"))
        except json.JSONDecodeError:
            self.stdout.write(self.style.ERROR(f"❌ Error leyendo JSON: {backup_file}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error durante la restauración: {str(e)}"))
            raise
    
    def restaurar_creditos(self, backup_data):
        """Ejecuta la restauración completa de créditos"""
        
        self.stdout.write("🔄 Iniciando restauración...")
        
        # 1. Restaurar datos de clientes (solo créditos)
        clientes_actualizados = 0
        for cliente_data in backup_data.get('clientes', []):
            try:
                cliente = Cliente.objects.get(id=cliente_data['id'])
                cliente.credito = cliente_data['credito']
                cliente.credito_maximo = cliente_data['credito_maximo']
                cliente.credito_plazo = cliente_data['credito_plazo']
                cliente.save()
                clientes_actualizados += 1
            except Cliente.DoesNotExist:
                self.stdout.write(f"⚠️  Cliente ID {cliente_data['id']} no encontrado, saltando...")
        
        self.stdout.write(f"   ✅ Actualizados {clientes_actualizados} clientes")
        
        # 2. Restaurar créditos
        creditos_creados = 0
        for credito_data in backup_data.get('creditos', []):
            Credito.objects.create(
                pedido_id=credito_data.get('pedido_id'),
                monto_credito=credito_data.get('monto_credito'),
                estado=credito_data.get('estado'),
                plazo_credito=credito_data.get('plazo_credito'),
                fecha=datetime.fromisoformat(credito_data['fecha']) if credito_data.get('fecha') else timezone.now(),
                fecha_vencimiento=datetime.fromisoformat(credito_data['fecha_vencimiento']) if credito_data.get('fecha_vencimiento') else None,
                cliente=credito_data.get('cliente'),
                abonado=credito_data.get('abonado', 0),
                cliente_id=credito_data.get('cliente_id')
            )
            creditos_creados += 1
        
        self.stdout.write(f"   ✅ Creados {creditos_creados} créditos")
        
        # 3. Restaurar abonos
        abonos_creados = 0
        for abono_data in backup_data.get('abonos', []):
            # Buscar cierre de caja si existe
            cierre_caja = None
            if abono_data.get('cierre_caja_id'):
                try:
                    cierre_caja = estadoCaja.objects.get(id=abono_data['cierre_caja_id'])
                except estadoCaja.DoesNotExist:
                    pass  # Continuar sin cierre de caja
            
            CreditoAbono.objects.create(
                credito_id=abono_data.get('credito_id'),
                monto=abono_data.get('monto'),
                fecha=datetime.fromisoformat(abono_data['fecha']) if abono_data.get('fecha') else timezone.now(),
                metodo_pago=abono_data.get('metodo_pago'),
                monto_neto=abono_data.get('monto_neto'),
                denominaciones=abono_data.get('denominaciones'),
                vuelto=abono_data.get('vuelto'),
                cierre_caja=cierre_caja
            )
            abonos_creados += 1
        
        self.stdout.write(f"   ✅ Creados {abonos_creados} abonos")
        
        # 4. Estadísticas finales
        self.stdout.write(f"\n📊 ESTADÍSTICAS FINALES:")
        self.stdout.write(f"   • Clientes: {Cliente.objects.count()}")
        self.stdout.write(f"   • Créditos: {Credito.objects.count()}")
        self.stdout.write(f"   • Abonos: {CreditoAbono.objects.count()}") 