from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from pos.models import Cliente, Credito, CreditoAbono
import json
from datetime import datetime


class Command(BaseCommand):
    help = 'Limpia todos los créditos y abonos, restablece créditos de clientes a su máximo'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--confirmar',
            action='store_true',
            help='Confirma que deseas ejecutar la limpieza (requerido)'
        )
        parser.add_argument(
            '--backup-path',
            type=str,
            help='Ruta donde guardar el backup de datos antes de limpiar',
            default='backup_creditos.json'
        )
        parser.add_argument(
            '--sin-backup',
            action='store_true',
            help='Omite crear backup (NO RECOMENDADO)'
        )
    
    def handle(self, *args, **options):
        if not options['confirmar']:
            self.stdout.write(
                self.style.WARNING(
                    '⚠️  OPERACIÓN PELIGROSA: Esta acción eliminará TODOS los créditos y abonos.\n'
                    'Para continuar, usa: --confirmar\n'
                    'Ejemplo: python manage.py limpiar_creditos --confirmar'
                )
            )
            return
        
        # Estadísticas iniciales
        clientes_count = Cliente.objects.count()
        creditos_count = Credito.objects.count()
        abonos_count = CreditoAbono.objects.count()
        
        self.stdout.write(f"📊 ESTADÍSTICAS INICIALES:")
        self.stdout.write(f"   • Clientes: {clientes_count}")
        self.stdout.write(f"   • Créditos: {creditos_count}")
        self.stdout.write(f"   • Abonos: {abonos_count}")
        
        # Crear backup si no se omite
        if not options['sin_backup']:
            self.stdout.write(f"💾 Creando backup en: {options['backup_path']}")
            self.crear_backup(options['backup_path'])
        
        # Confirmación final
        confirm = input("\n🚨 ¿ESTÁS SEGURO? Esta acción NO SE PUEDE DESHACER. Escribe 'CONFIRMAR': ")
        if confirm != 'CONFIRMAR':
            self.stdout.write(self.style.ERROR("❌ Operación cancelada"))
            return
        
        # Ejecutar limpieza
        try:
            with transaction.atomic():
                self.limpiar_creditos()
                self.stdout.write(self.style.SUCCESS("✅ Limpieza completada exitosamente"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error durante la limpieza: {str(e)}"))
            raise
    
    def crear_backup(self, backup_path):
        """Crea un backup JSON con todos los datos de créditos"""
        try:
            backup_data = {
                'timestamp': timezone.now().isoformat(),
                'clientes': [],
                'creditos': [],
                'abonos': []
            }
            
            # Backup de clientes (solo campos relacionados con crédito)
            for cliente in Cliente.objects.all():
                backup_data['clientes'].append({
                    'id': cliente.id,
                    'cedula': cliente.cedula,
                    'nombre': cliente.nombre,
                    'credito': cliente.credito,
                    'credito_maximo': cliente.credito_maximo,
                    'credito_plazo': cliente.credito_plazo
                })
            
            # Backup de créditos
            for credito in Credito.objects.all():
                backup_data['creditos'].append({
                    'id': credito.id,
                    'pedido_id': credito.pedido_id,
                    'monto_credito': credito.monto_credito,
                    'estado': credito.estado,
                    'plazo_credito': credito.plazo_credito,
                    'fecha': credito.fecha.isoformat() if credito.fecha else None,
                    'fecha_vencimiento': credito.fecha_vencimiento.isoformat() if credito.fecha_vencimiento else None,
                    'cliente': credito.cliente,
                    'abonado': credito.abonado,
                    'cliente_id': credito.cliente_id
                })
            
            # Backup de abonos
            for abono in CreditoAbono.objects.all():
                backup_data['abonos'].append({
                    'id': abono.id,
                    'credito_id': abono.credito_id,
                    'monto': abono.monto,
                    'fecha': abono.fecha.isoformat() if abono.fecha else None,
                    'metodo_pago': abono.metodo_pago,
                    'monto_neto': abono.monto_neto,
                    'denominaciones': abono.denominaciones,
                    'vuelto': abono.vuelto,
                    'cierre_caja_id': abono.cierre_caja.id if abono.cierre_caja else None
                })
            
            # Guardar backup
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False)
            
            self.stdout.write(f"✅ Backup guardado: {len(backup_data['clientes'])} clientes, {len(backup_data['creditos'])} créditos, {len(backup_data['abonos'])} abonos")
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error creando backup: {str(e)}"))
            raise
    
    def limpiar_creditos(self):
        """Ejecuta la limpieza completa de créditos"""
        
        self.stdout.write("🧹 Iniciando limpieza...")
        
        # 1. Eliminar todos los abonos de crédito
        abonos_eliminados = CreditoAbono.objects.all().delete()[0]
        self.stdout.write(f"   ✅ Eliminados {abonos_eliminados} abonos de crédito")
        
        # 2. Eliminar todos los créditos
        creditos_eliminados = Credito.objects.all().delete()[0]
        self.stdout.write(f"   ✅ Eliminados {creditos_eliminados} créditos")
        
        # 3. Restablecer crédito de clientes a su máximo
        clientes_actualizados = 0
        for cliente in Cliente.objects.all():
            if cliente.credito != cliente.credito_maximo:
                cliente.credito = cliente.credito_maximo
                cliente.save()
                clientes_actualizados += 1
        
        self.stdout.write(f"   ✅ Restablecidos {clientes_actualizados} clientes a su crédito máximo")
        
        # 4. Estadísticas finales
        self.stdout.write(f"\n📊 ESTADÍSTICAS FINALES:")
        self.stdout.write(f"   • Clientes: {Cliente.objects.count()}")
        self.stdout.write(f"   • Créditos: {Credito.objects.count()} (debería ser 0)")
        self.stdout.write(f"   • Abonos: {CreditoAbono.objects.count()} (debería ser 0)")
        
        # 5. Verificar que todos los clientes tienen su crédito máximo
        from django.db import models
        clientes_con_credito_incorrecto = Cliente.objects.exclude(credito=models.F('credito_maximo')).count()
        if clientes_con_credito_incorrecto == 0:
            self.stdout.write("   ✅ Todos los clientes tienen su crédito máximo")
        else:
            self.stdout.write(f"   ⚠️  {clientes_con_credito_incorrecto} clientes no tienen su crédito máximo") 