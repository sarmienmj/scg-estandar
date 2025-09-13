from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from pos.models import Cliente, Credito, CreditoAbono
import json
from datetime import datetime


class Command(BaseCommand):
    help = 'Script simple para resetear créditos de todos los clientes a su máximo'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--ejecutar',
            action='store_true',
            help='Ejecuta la operación de limpieza',
        )
        parser.add_argument(
            '--backup',
            action='store_true',
            help='Crear backup antes de ejecutar',
        )
        parser.add_argument(
            '--silencioso',
            action='store_true',
            help='Ejecutar sin confirmaciones (usar solo en scripts automáticos)',
        )
    
    def handle(self, *args, **options):
        """Resetea los créditos de todos los clientes"""
        
        # Banner informativo
        self.stdout.write("\n" + "="*60)
        self.stdout.write("🔄 SCRIPT DE RESETEO DE CRÉDITOS")
        self.stdout.write("="*60)
        
        # Mostrar estadísticas actuales
        self.mostrar_estadisticas()
        
        # Si no se especifica --ejecutar, solo mostrar información
        if not options['ejecutar']:
            self.stdout.write(
                self.style.WARNING(
                    "\n⚠️  MODO INFORMACIÓN - No se ejecutará ningún cambio\n"
                    "Para ejecutar la limpieza use: --ejecutar\n"
                    "Para crear backup use: --backup\n"
                    "Ejemplo: python manage.py resetear_creditos --ejecutar --backup"
                )
            )
            return
        
        # Crear backup si se solicita
        if options['backup']:
            self.crear_backup()
        
        # Confirmación de seguridad
        if not options['silencioso']:
            self.stdout.write(
                self.style.ERROR(
                    "\n🚨 ATENCIÓN: Esta operación:\n"
                    "   • Eliminará TODOS los créditos/deudas\n"
                    "   • Eliminará TODOS los abonos\n"
                    "   • Restablecerá TODOS los clientes a su crédito máximo\n"
                )
            )
            
            respuesta = input("¿Desea continuar? Escriba 'SI' para confirmar: ")
            if respuesta != 'SI':
                self.stdout.write(self.style.WARNING("❌ Operación cancelada"))
                return
        
        # Ejecutar la limpieza
        self.ejecutar_reseteo()
    
    def mostrar_estadisticas(self):
        """Muestra estadísticas del estado actual"""
        
        total_clientes = Cliente.objects.count()
        total_creditos = Credito.objects.count()
        total_abonos = CreditoAbono.objects.count()
        
        # Calcular deuda total
        deuda_total = 0
        clientes_con_deuda = 0
        
        for cliente in Cliente.objects.all():
            creditos = Credito.objects.filter(cliente_id=cliente.cedula, estado='Pendiente')
            deuda_cliente = sum(credito.monto_credito - credito.abonado for credito in creditos)
            if deuda_cliente > 0:
                deuda_total += deuda_cliente
                clientes_con_deuda += 1
        
        # Clientes con crédito disponible
        clientes_credito_maximo = Cliente.objects.filter(credito__gte=100).count()
        clientes_sin_credito = Cliente.objects.filter(credito=0).count()
        
        self.stdout.write(f"\n📊 ESTADO ACTUAL DEL SISTEMA:")
        self.stdout.write(f"   💳 Total de clientes: {total_clientes}")
        self.stdout.write(f"   📄 Total de créditos: {total_creditos}")
        self.stdout.write(f"   💰 Total de abonos: {total_abonos}")
        self.stdout.write(f"   🔴 Clientes con deuda: {clientes_con_deuda}")
        self.stdout.write(f"   💸 Deuda total: ${deuda_total:.2f}")
        self.stdout.write(f"   ✅ Clientes con crédito disponible: {clientes_credito_maximo}")
        self.stdout.write(f"   ❌ Clientes sin crédito: {clientes_sin_credito}")
    
    def crear_backup(self):
        """Crea un backup rápido de los datos"""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f"backup_reseteo_{timestamp}.json"
        
        self.stdout.write(f"\n💾 Creando backup: {backup_file}")
        
        try:
            backup_data = {
                'timestamp': timezone.now().isoformat(),
                'total_clientes': Cliente.objects.count(),
                'total_creditos': Credito.objects.count(),
                'total_abonos': CreditoAbono.objects.count(),
                'clientes': [
                    {
                        'id': c.id,
                        'cedula': c.cedula,
                        'nombre': c.nombre,
                        'credito_actual': c.credito,
                        'credito_maximo': c.credito_maximo
                    } for c in Cliente.objects.all()
                ],
                'creditos': [
                    {
                        'id': cr.id,
                        'cliente_id': cr.cliente_id,
                        'monto': cr.monto_credito,
                        'abonado': cr.abonado,
                        'estado': cr.estado
                    } for cr in Credito.objects.all()
                ]
            }
            
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False)
            
            self.stdout.write(f"   ✅ Backup creado exitosamente")
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"   ❌ Error creando backup: {e}"))
    
    def ejecutar_reseteo(self):
        """Ejecuta el reseteo completo"""
        
        self.stdout.write(f"\n🔄 INICIANDO RESETEO...")
        
        try:
            with transaction.atomic():
                
                # 1. Eliminar todos los abonos
                self.stdout.write("   🗑️  Eliminando abonos...")
                abonos_eliminados, _ = CreditoAbono.objects.all().delete()
                self.stdout.write(f"      ✅ {abonos_eliminados} abonos eliminados")
                
                # 2. Eliminar todos los créditos
                self.stdout.write("   🗑️  Eliminando créditos...")
                creditos_eliminados, _ = Credito.objects.all().delete()
                self.stdout.write(f"      ✅ {creditos_eliminados} créditos eliminados")
                
                # 3. Resetear créditos de clientes
                self.stdout.write("   🔄 Reseteando créditos de clientes...")
                clientes_actualizados = 0
                
                for cliente in Cliente.objects.all():
                    if cliente.credito != cliente.credito_maximo:
                        cliente.credito = cliente.credito_maximo
                        cliente.save()
                        clientes_actualizados += 1
                
                self.stdout.write(f"      ✅ {clientes_actualizados} clientes actualizados")
                
                # 4. Verificación final
                self.stdout.write(f"\n✅ RESETEO COMPLETADO EXITOSAMENTE")
                self.mostrar_resultado_final()
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error durante el reseteo: {e}"))
            self.stdout.write("🔄 Los cambios fueron revertidos automáticamente")
            raise
    
    def mostrar_resultado_final(self):
        """Muestra el resultado final del reseteo"""
        
        total_clientes = Cliente.objects.count()
        creditos_restantes = Credito.objects.count()
        abonos_restantes = CreditoAbono.objects.count()
        
        # Verificar que todos los clientes tienen su crédito máximo
        clientes_correctos = 0
        credito_total_disponible = 0
        
        for cliente in Cliente.objects.all():
            if cliente.credito == cliente.credito_maximo:
                clientes_correctos += 1
            credito_total_disponible += cliente.credito
        
        self.stdout.write(f"\n📊 RESULTADO FINAL:")
        self.stdout.write(f"   👥 Total de clientes: {total_clientes}")
        self.stdout.write(f"   ✅ Clientes con crédito máximo: {clientes_correctos}")
        self.stdout.write(f"   💳 Crédito total disponible: ${credito_total_disponible}")
        self.stdout.write(f"   📄 Créditos restantes: {creditos_restantes} (debe ser 0)")
        self.stdout.write(f"   💰 Abonos restantes: {abonos_restantes} (debe ser 0)")
        
        if creditos_restantes == 0 and abonos_restantes == 0 and clientes_correctos == total_clientes:
            self.stdout.write(self.style.SUCCESS(f"\n🎉 ÉXITO TOTAL: Todos los créditos han sido reseteados"))
        else:
            self.stdout.write(self.style.WARNING(f"\n⚠️  Verificar: Algunos elementos pueden no haberse procesado correctamente"))
        
        self.stdout.write("\n" + "="*60)
        self.stdout.write("✨ Los clientes ahora tienen su crédito máximo disponible")
        self.stdout.write("✨ Todas las deudas han sido eliminadas")
        self.stdout.write("="*60) 