from django.core.management.base import BaseCommand
from django.db.models import Q
from pos.models import ProductosPedido, Producto

class Command(BaseCommand):
    help = 'Verifica y reporta productos huérfanos en pedidos existentes'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fix',
            action='store_true',
            help='Corregir automáticamente los productos huérfanos eliminándolos',
        )

    def handle(self, *args, **options):
        self.stdout.write("🔍 Verificando productos huérfanos en pedidos...")
        
        # Obtener todos los ProductosPedido con IDs de productos que no existen
        productos_pedido = ProductosPedido.objects.all()
        huerfanos = []
        
        for producto_pedido in productos_pedido:
            if producto_pedido.producto:
                try:
                    Producto.objects.get(id=producto_pedido.producto)
                except Producto.DoesNotExist:
                    huerfanos.append(producto_pedido)
        
        if not huerfanos:
            self.stdout.write(self.style.SUCCESS("✅ No se encontraron productos huérfanos"))
            return
        
        self.stdout.write(f"⚠️  Se encontraron {len(huerfanos)} productos huérfanos:")
        
        for producto_pedido in huerfanos:
            self.stdout.write(f"  - ProductosPedido ID: {producto_pedido.id}")
            self.stdout.write(f"    Producto ID: {producto_pedido.producto}")
            self.stdout.write(f"    Nombre: {producto_pedido.producto_nombre}")
            self.stdout.write(f"    Cantidad: {producto_pedido.cantidad}")
            self.stdout.write(f"    Precio: {producto_pedido.precio}")
            
            # Verificar si el ProductosPedido está asociado a algún pedido
            pedidos_relacionados = producto_pedido.pedido_set.all()
            if pedidos_relacionados:
                self.stdout.write(f"    Pedidos relacionados: {[p.id for p in pedidos_relacionados]}")
            else:
                self.stdout.write(f"    No está asociado a ningún pedido")
            self.stdout.write("")
        
        if options['fix']:
            self.stdout.write("🔧 Corrigiendo productos huérfanos...")
            eliminados = 0
            for producto_pedido in huerfanos:
                producto_pedido.delete()
                eliminados += 1
            
            self.stdout.write(self.style.SUCCESS(f"✅ Eliminados {eliminados} productos huérfanos"))
        else:
            self.stdout.write(self.style.WARNING("Para corregir automáticamente, ejecute el comando con --fix"))
            self.stdout.write("⚠️  ADVERTENCIA: Esto eliminará los productos huérfanos permanentemente") 