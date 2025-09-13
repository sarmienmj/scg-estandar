from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.db.models import Q, F, Sum
from pos.models import Cliente, Credito, CreditoAbono
import json
import os
from datetime import datetime
from decimal import Decimal


class Command(BaseCommand):
    help = 'Script completo para limpiar deudas de clientes y restablecer créditos'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--modo',
            type=str,
            choices=['todo', 'cliente', 'reporte', 'verificar'],
            default='todo',
            help='Modo de operación: todo, cliente específico, reporte o verificar'
        )
        parser.add_argument(
            '--cliente-id',
            type=int,
            help='ID del cliente específico a limpiar (solo para modo=cliente)'
        )
        parser.add_argument(
            '--confirmar',
            action='store_true',
            help='Confirma que deseas ejecutar la operación'
        )
        parser.add_argument(
            '--backup-path',
            type=str,
            help='Ruta personalizada para el backup',
            default=None
        )
        parser.add_argument(
            '--sin-backup',
            action='store_true',
            help='Omite crear backup (NO RECOMENDADO para --modo=todo)'
        )
        parser.add_argument(
            '--forzar',
            action='store_true',
            help='Omite confirmaciones interactivas (usar con precaución)'
        )
    
    def handle(self, *args, **options):
        """Punto de entrada principal del comando"""
        
        # Mostrar banner
        self.mostrar_banner()
        
        # Validar argumentos
        if not self.validar_argumentos(options):
            return
        
        # Ejecutar según el modo
        modo = options['modo']
        
        if modo == 'reporte':
            self.generar_reporte()
        elif modo == 'verificar':
            self.verificar_integridad()
        elif modo == 'cliente':
            self.limpiar_cliente_especifico(options)
        elif modo == 'todo':
            self.limpiar_todas_las_deudas(options)
    
    def mostrar_banner(self):
        """Muestra el banner del script"""
        banner = """
╔══════════════════════════════════════════════════════════════╗
║                    🧹 LIMPIEZA DE DEUDAS                     ║
║              Sistema POS - Gestión de Créditos              ║
╚══════════════════════════════════════════════════════════════╝
        """
        self.stdout.write(self.style.HTTP_INFO(banner))
    
    def validar_argumentos(self, options):
        """Valida los argumentos del comando"""
        
        if options['modo'] == 'cliente' and not options['cliente_id']:
            self.stdout.write(
                self.style.ERROR(
                    "❌ Error: Para modo 'cliente' debes especificar --cliente-id"
                )
            )
            return False
        
        if options['modo'] == 'todo' and not options['sin_backup'] and not options['confirmar']:
            self.stdout.write(
                self.style.WARNING(
                    "⚠️  Para limpiar TODAS las deudas necesitas usar --confirmar"
                )
            )
            return False
        
        return True
    
    def generar_reporte(self):
        """Genera un reporte completo del estado de créditos"""
        
        self.stdout.write(self.style.HTTP_INFO("\n📊 REPORTE COMPLETO DE CRÉDITOS"))
        self.stdout.write("=" * 60)
        
        # Estadísticas generales
        total_clientes = Cliente.objects.count()
        total_creditos = Credito.objects.count()
        total_abonos = CreditoAbono.objects.count()
        
        # Créditos por estado
        creditos_pendientes = Credito.objects.filter(estado='Pendiente').count()
        creditos_pagados = Credito.objects.filter(estado='Pagado').count()
        creditos_vencidos = Credito.objects.filter(estado='Vencido').count()
        
        # Montos totales
        deuda_total = Credito.objects.filter(estado='Pendiente').aggregate(
            total=Sum('monto_credito'))['total'] or 0
        abonos_total = CreditoAbono.objects.aggregate(
            total=Sum('monto'))['total'] or 0
        
        self.stdout.write(f"\n🏢 ESTADÍSTICAS GENERALES:")
        self.stdout.write(f"   • Total de clientes: {total_clientes}")
        self.stdout.write(f"   • Total de créditos: {total_creditos}")
        self.stdout.write(f"   • Total de abonos: {total_abonos}")
        
        self.stdout.write(f"\n💳 CRÉDITOS POR ESTADO:")
        self.stdout.write(f"   • Pendientes: {creditos_pendientes}")
        self.stdout.write(f"   • Pagados: {creditos_pagados}")
        self.stdout.write(f"   • Vencidos: {creditos_vencidos}")
        
        self.stdout.write(f"\n💰 MONTOS:")
        self.stdout.write(f"   • Deuda total pendiente: ${deuda_total:.2f}")
        self.stdout.write(f"   • Total abonado: ${abonos_total:.2f}")
        
        # Clientes con mayor deuda
        self.stdout.write(f"\n👥 TOP 10 CLIENTES CON MAYOR DEUDA:")
        clientes_con_deuda = []
        
        for cliente in Cliente.objects.all():
            creditos = Credito.objects.filter(cliente_id=cliente.cedula, estado='Pendiente')
            deuda_cliente = sum(credito.monto_credito - credito.abonado for credito in creditos)
            if deuda_cliente > 0:
                clientes_con_deuda.append((cliente, deuda_cliente))
        
        clientes_con_deuda.sort(key=lambda x: x[1], reverse=True)
        
        for i, (cliente, deuda) in enumerate(clientes_con_deuda[:10]):
            self.stdout.write(f"   {i+1:2d}. {cliente.nombre} (#{cliente.cedula}) - ${deuda:.2f}")
        
        # Análisis de créditos máximos vs disponibles
        self.stdout.write(f"\n🔍 ANÁLISIS DE CRÉDITOS:")
        clientes_credito_maximo = Cliente.objects.filter(credito=F('credito_maximo')).count()
        clientes_sin_credito = Cliente.objects.filter(credito=0).count()
        
        self.stdout.write(f"   • Clientes con crédito máximo: {clientes_credito_maximo}")
        self.stdout.write(f"   • Clientes sin crédito disponible: {clientes_sin_credito}")
        
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("✅ Reporte completado"))
    
    def verificar_integridad(self):
        """Verifica la integridad de los datos de créditos"""
        
        self.stdout.write(self.style.HTTP_INFO("\n🔍 VERIFICACIÓN DE INTEGRIDAD"))
        self.stdout.write("=" * 50)
        
        errores = []
        
        # 1. Verificar créditos huérfanos (sin cliente)
        creditos_huerfanos = Credito.objects.filter(
            Q(cliente_id__isnull=True) | Q(cliente_id='')
        ).count()
        if creditos_huerfanos > 0:
            errores.append(f"❌ {creditos_huerfanos} créditos sin cliente asociado")
        
        # 2. Verificar abonos huérfanos (sin crédito)
        abonos_huerfanos = CreditoAbono.objects.filter(
            credito_id__isnull=True
        ).count()
        if abonos_huerfanos > 0:
            errores.append(f"❌ {abonos_huerfanos} abonos sin crédito asociado")
        
        # 3. Verificar créditos con montos negativos
        creditos_negativos = Credito.objects.filter(
            monto_credito__lt=0
        ).count()
        if creditos_negativos > 0:
            errores.append(f"❌ {creditos_negativos} créditos con monto negativo")
        
        # 4. Verificar clientes con crédito mayor al máximo
        clientes_exceso = Cliente.objects.filter(
            credito__gt=F('credito_maximo')
        ).count()
        if clientes_exceso > 0:
            errores.append(f"❌ {clientes_exceso} clientes con crédito mayor al máximo")
        
        # 5. Verificar abonos mayores al crédito
        for credito in Credito.objects.all():
            if credito.abonado and credito.abonado > credito.monto_credito:
                errores.append(f"❌ Crédito #{credito.id}: abonado (${credito.abonado}) > crédito (${credito.monto_credito})")
        
        # Mostrar resultados
        if errores:
            self.stdout.write(f"\n⚠️  PROBLEMAS ENCONTRADOS ({len(errores)}):")
            for error in errores:
                self.stdout.write(f"   {error}")
        else:
            self.stdout.write(self.style.SUCCESS("\n✅ No se encontraron problemas de integridad"))
        
        self.stdout.write("\n" + "=" * 50)
    
    def limpiar_cliente_especifico(self, options):
        """Limpia las deudas de un cliente específico"""
        
        cliente_id = options['cliente_id']
        
        try:
            cliente = Cliente.objects.get(id=cliente_id)
        except Cliente.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f"❌ Cliente con ID {cliente_id} no encontrado")
            )
            return
        
        self.stdout.write(self.style.HTTP_INFO(f"\n👤 LIMPIAR CLIENTE: {cliente.nombre}"))
        self.stdout.write("=" * 50)
        
        # Mostrar estado actual
        creditos = Credito.objects.filter(cliente_id=cliente.cedula)
        abonos = CreditoAbono.objects.filter(credito_id__in=creditos.values_list('id', flat=True))
        deuda_total = sum(credito.monto_credito - credito.abonado for credito in creditos if credito.estado == 'Pendiente')
        
        self.stdout.write(f"\n📊 ESTADO ACTUAL:")
        self.stdout.write(f"   • Nombre: {cliente.nombre}")
        self.stdout.write(f"   • Cédula: {cliente.cedula}")
        self.stdout.write(f"   • Crédito actual: ${cliente.credito}")
        self.stdout.write(f"   • Crédito máximo: ${cliente.credito_maximo}")
        self.stdout.write(f"   • Deuda total: ${deuda_total:.2f}")
        self.stdout.write(f"   • Créditos registrados: {creditos.count()}")
        self.stdout.write(f"   • Abonos registrados: {abonos.count()}")
        
        # Confirmación
        if not options['forzar']:
            confirm = input(f"\n¿Limpiar TODAS las deudas de {cliente.nombre}? (s/N): ")
            if confirm.lower() != 's':
                self.stdout.write(self.style.WARNING("❌ Operación cancelada"))
                return
        
        # Ejecutar limpieza
        try:
            with transaction.atomic():
                # Eliminar abonos
                abonos_eliminados = abonos.delete()[0]
                
                # Eliminar créditos
                creditos_eliminados = creditos.delete()[0]
                
                # Restablecer crédito
                cliente.credito = cliente.credito_maximo
                cliente.save()
                
                self.stdout.write(f"\n✅ LIMPIEZA COMPLETADA:")
                self.stdout.write(f"   • Eliminados {creditos_eliminados} créditos")
                self.stdout.write(f"   • Eliminados {abonos_eliminados} abonos")
                self.stdout.write(f"   • Crédito restablecido a ${cliente.credito_maximo}")
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error durante la limpieza: {str(e)}"))
            raise
    
    def limpiar_todas_las_deudas(self, options):
        """Limpia TODAS las deudas del sistema"""
        
        if not options['confirmar']:
            self.stdout.write(
                self.style.WARNING(
                    "\n⚠️  OPERACIÓN CRÍTICA: Esta acción eliminará TODAS las deudas del sistema.\n"
                    "Para continuar, usa: --confirmar\n"
                    "Ejemplo: python manage.py limpiar_deudas_completo --modo=todo --confirmar"
                )
            )
            return
        
        self.stdout.write(self.style.ERROR("\n🚨 LIMPIEZA TOTAL DEL SISTEMA"))
        self.stdout.write("=" * 60)
        
        # Estadísticas iniciales
        clientes_count = Cliente.objects.count()
        creditos_count = Credito.objects.count()
        abonos_count = CreditoAbono.objects.count()
        deuda_total = Credito.objects.filter(estado='Pendiente').aggregate(
            total=Sum('monto_credito'))['total'] or 0
        
        self.stdout.write(f"\n📊 ESTADO ACTUAL:")
        self.stdout.write(f"   • Clientes: {clientes_count}")
        self.stdout.write(f"   • Créditos: {creditos_count}")
        self.stdout.write(f"   • Abonos: {abonos_count}")
        self.stdout.write(f"   • Deuda total: ${deuda_total:.2f}")
        
        # Crear backup automático
        if not options['sin_backup']:
            backup_path = options['backup_path'] or f"backup_deudas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            self.stdout.write(f"\n💾 Creando backup en: {backup_path}")
            self.crear_backup_completo(backup_path)
        
        # Confirmación final
        if not options['forzar']:
            self.stdout.write(self.style.ERROR(
                f"\n🚨 ÚLTIMA ADVERTENCIA:\n"
                f"   • Se eliminarán {creditos_count} créditos\n"
                f"   • Se eliminarán {abonos_count} abonos\n"
                f"   • Se perderán ${deuda_total:.2f} en deudas registradas\n"
                f"   • Se restablecerán {clientes_count} clientes a su crédito máximo"
            ))
            
            confirm = input("\n¿CONFIRMAS que quieres ELIMINAR TODAS LAS DEUDAS? Escribe 'ELIMINAR TODO': ")
            if confirm != 'ELIMINAR TODO':
                self.stdout.write(self.style.WARNING("❌ Operación cancelada por seguridad"))
                return
        
        # Ejecutar limpieza total
        self.stdout.write(self.style.HTTP_INFO("\n🧹 INICIANDO LIMPIEZA TOTAL..."))
        
        try:
            with transaction.atomic():
                # 1. Eliminar todos los abonos
                abonos_eliminados = CreditoAbono.objects.all().delete()[0]
                self.stdout.write(f"   ✅ Eliminados {abonos_eliminados} abonos")
                
                # 2. Eliminar todos los créditos
                creditos_eliminados = Credito.objects.all().delete()[0]
                self.stdout.write(f"   ✅ Eliminados {creditos_eliminados} créditos")
                
                # 3. Restablecer todos los clientes
                clientes_actualizados = 0
                for cliente in Cliente.objects.all():
                    if cliente.credito != cliente.credito_maximo:
                        cliente.credito = cliente.credito_maximo
                        cliente.save()
                        clientes_actualizados += 1
                
                self.stdout.write(f"   ✅ Restablecidos {clientes_actualizados} clientes")
                
                # 4. Verificación final
                self.stdout.write(f"\n📊 VERIFICACIÓN FINAL:")
                self.stdout.write(f"   • Créditos restantes: {Credito.objects.count()}")
                self.stdout.write(f"   • Abonos restantes: {CreditoAbono.objects.count()}")
                
                clientes_incorrectos = Cliente.objects.exclude(credito=F('credito_maximo')).count()
                if clientes_incorrectos == 0:
                    self.stdout.write(f"   ✅ Todos los clientes tienen su crédito máximo")
                else:
                    self.stdout.write(f"   ⚠️  {clientes_incorrectos} clientes con crédito incorrecto")
                
                self.stdout.write(self.style.SUCCESS("\n🎉 LIMPIEZA TOTAL COMPLETADA EXITOSAMENTE"))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error durante la limpieza: {str(e)}"))
            self.stdout.write("🔄 La transacción fue revertida automáticamente")
            raise
    
    def crear_backup_completo(self, backup_path):
        """Crea un backup completo con metadatos adicionales"""
        
        try:
            backup_data = {
                'metadata': {
                    'timestamp': timezone.now().isoformat(),
                    'created_by': 'limpiar_deudas_completo',
                    'version': '2.0',
                    'description': 'Backup completo antes de limpieza de deudas'
                },
                'estadisticas': {
                    'clientes': Cliente.objects.count(),
                    'creditos': Credito.objects.count(),
                    'abonos': CreditoAbono.objects.count(),
                    'deuda_total': float(Credito.objects.filter(estado='Pendiente').aggregate(
                        total=Sum('monto_credito'))['total'] or 0)
                },
                'clientes': [],
                'creditos': [],
                'abonos': []
            }
            
            # Backup de clientes
            for cliente in Cliente.objects.all():
                backup_data['clientes'].append({
                    'id': cliente.id,
                    'cedula': cliente.cedula,
                    'nombre': cliente.nombre,
                    'telefono': cliente.telefono,
                    'zona_vive': cliente.zona_vive,
                    'credito': float(cliente.credito),
                    'credito_maximo': float(cliente.credito_maximo),
                    'credito_plazo': cliente.credito_plazo
                })
            
            # Backup de créditos
            for credito in Credito.objects.all():
                backup_data['creditos'].append({
                    'id': credito.id,
                    'pedido_id': credito.pedido_id,
                    'monto_credito': float(credito.monto_credito) if credito.monto_credito else None,
                    'estado': credito.estado,
                    'plazo_credito': credito.plazo_credito,
                    'fecha': credito.fecha.isoformat() if credito.fecha else None,
                    'fecha_vencimiento': credito.fecha_vencimiento.isoformat() if credito.fecha_vencimiento else None,
                    'cliente': credito.cliente,
                    'abonado': float(credito.abonado) if credito.abonado else None,
                    'cliente_id': credito.cliente_id
                })
            
            # Backup de abonos
            for abono in CreditoAbono.objects.all():
                backup_data['abonos'].append({
                    'id': abono.id,
                    'credito_id': abono.credito_id,
                    'monto': float(abono.monto) if abono.monto else None,
                    'fecha': abono.fecha.isoformat() if abono.fecha else None,
                    'metodo_pago': abono.metodo_pago,
                    'monto_neto': float(abono.monto_neto) if abono.monto_neto else None,
                    'denominaciones': abono.denominaciones,
                    'vuelto': abono.vuelto,
                    'cierre_caja_id': abono.cierre_caja.id if abono.cierre_caja else None
                })
            
            # Guardar backup
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False)
            
            # Verificar que el archivo se creó correctamente
            if os.path.exists(backup_path):
                file_size = os.path.getsize(backup_path)
                self.stdout.write(
                    f"✅ Backup creado: {backup_path} ({file_size} bytes)\n"
                    f"   📁 Contiene: {len(backup_data['clientes'])} clientes, "
                    f"{len(backup_data['creditos'])} créditos, {len(backup_data['abonos'])} abonos"
                )
            else:
                raise Exception("El archivo de backup no se creó correctamente")
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error creando backup: {str(e)}"))
            raise 