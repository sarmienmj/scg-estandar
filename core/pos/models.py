from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User

# modelos para cada tabla de la base de datos

class Cliente(models.Model):

    nombre = models.CharField(max_length=50)
    cedula = models.CharField(max_length=50)
    telefono = models.CharField(max_length=20)
    zona_vive = models.CharField(max_length=50)
    credito = models.IntegerField(default=0)
    credito_maximo = models.IntegerField(default=0)
    credito_plazo = models.IntegerField(default=0)
    
#clase de categorias de productos
# relacionada ManytoMany a Producto en campo Producto.categoria
class CategoriasProductos(models.Model):
    nombre = models.CharField(max_length=50)
    imagen = models.ImageField(upload_to='categorias/', blank=True, null=True)
    orden = models.IntegerField()

    def __str__(self):
        return self.nombre

#clase de productos
class Producto(models.Model):
    UNIDAD_OPCIONES = [
            ('U', 'U'),
            ('K', 'K'),
        ]
    MONEDA_OPCIONES = [
            ('USD', 'USD'),
            ('BS', 'BS'),
        ]

    nombre = models.CharField(max_length=50)
    cantidad = models.FloatField( blank=True,null=True,default="")
    unidad = models.CharField(max_length=20, choices=UNIDAD_OPCIONES)
    moneda = models.CharField(max_length=20, choices=MONEDA_OPCIONES)
    imagen = models.ImageField(upload_to='productos/', blank=True, null=True)
    barcode = models.CharField(max_length=200, blank=True,null=True)
    costo = models.FloatField(blank=True,null=True)
    precio_detal = models.FloatField()
    precio_mayor = models.FloatField(blank=True,null=True)
    precio_especial = models.FloatField(blank=True,null=True)
    categoria = models.ManyToManyField(CategoriasProductos)
    subproducto = models.CharField(max_length=50,blank=True,null=True,default="")
    relacion_subproducto = models.IntegerField(blank=True,null=True, default=0)
    
    def __str__(self):
        return self.nombre
    

#clase de relacion entre pedidos y sus productos con sus cantidades y precio a considerar
class ProductosPedido(models.Model):
    producto_nombre = models.CharField(max_length=50,blank=True,null=True)
    unidad = models.CharField(max_length=20,blank=True,null=True)
    producto = models.IntegerField(blank=True,null=True)
    cantidad = models.FloatField(blank=True,null=True)
    precio = models.FloatField(blank=True,null=True)
    moneda = models.CharField(max_length=20, blank=True, null=True)
    
    def clean(self):
        """Validar que el producto existe si se proporciona un ID"""
        from django.core.exceptions import ValidationError
        if self.producto:
            try:
                Producto.objects.get(id=self.producto)
            except Producto.DoesNotExist:
                raise ValidationError(f'El producto con ID {self.producto} no existe')
    
    def save(self, *args, **kwargs):
        """Validar antes de guardar"""
        self.clean()
        super().save(*args, **kwargs)

class CierresDiarios(models.Model):
    total = models.FloatField(blank=True,null=True)
    fecha = models.DateTimeField(auto_now_add=True)
    usuario = models.CharField(max_length=50,blank=True,null=True)
    
#clase de pedidos
class Pedido(models.Model):
    productos = models.ManyToManyField(ProductosPedido)
    status = models.CharField(max_length=50,blank=True,null=True)
    precio_total = models.FloatField(blank=True,null=True)
    fecha = models.DateTimeField(auto_now_add=True,blank=True,null=True)
    pagado_fecha = models.DateTimeField(null=True, blank=True)
    despachado_fecha = models.DateTimeField(null=True, blank=True)
    cliente = models.IntegerField(default=0)
    dolar_al_pagar = models.FloatField(null=True, blank=True)
    notas = models.CharField(max_length=400,blank=True,null=True)
    usuario = models.CharField(max_length=50,blank=True,null=True)
    pesador = models.CharField(max_length=50,blank=True,null=True)
    numero_pedido_balanza = models.IntegerField(null=True, blank=True)
        
    def get_productos(self):
        productos = self.productos.all()
        return productos

class ValorDolar(models.Model):
    valor = models.FloatField()

class BalanzasImpresoras(models.Model):
    balanza_id = models.CharField(max_length=50, null=True, blank=True)
    impresora_ip = models.CharField(max_length=50, null=True, blank=True)

class ProductosBalanzas(models.Model):
    numero = models.IntegerField(blank=True,null=True)
    producto = models.IntegerField(blank=True,null=True)

class Credito(models.Model):
    pedido_id = models.IntegerField(blank=True,null=True)
    monto_credito = models.FloatField(blank=True,null=True)
    estado = models.CharField(max_length=50,blank=True,null=True)
    plazo_credito = models.IntegerField(blank=True,null=True)
    fecha = models.DateTimeField(auto_now_add=True)
    fecha_vencimiento = models.DateTimeField(null=True, blank=True)
    cliente = models.CharField(max_length=50,blank=True,null=True)
    abonado = models.FloatField(blank=True,null=True)
    cliente_id = models.CharField(max_length=50,blank=True,null=True)

    def verificar_vencimiento(self):
        if self.estado == 'Pendiente' and self.fecha_vencimiento < timezone.now():
            self.estado = 'Vencido'
            self.save()

class CreditoAbono(models.Model):
    credito_id = models.IntegerField(blank=True, null=True)
    monto = models.FloatField(blank=True, null=True)
    fecha = models.DateTimeField(auto_now_add=True)
    metodo_pago = models.CharField(max_length=50, blank=True, null=True)
    monto_neto = models.FloatField(blank=True, null=True)
    denominaciones = models.JSONField(blank=True, null=True)
    vuelto = models.JSONField(blank=True, null=True)
    cierre_caja = models.ForeignKey('estadoCaja', on_delete=models.CASCADE, related_name='abonos_creditos', null=True, blank=True)

class estadoCaja(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cajas_abiertas')
    fechaInicio = models.DateTimeField(null=True,blank=True)
    fechaFin = models.DateTimeField(null=True,blank=True)
    dineroInicio = models.JSONField(blank=True,null=True)
    dineroFinal = models.JSONField(blank=True,null=True)
    dineroEsperado = models.JSONField(blank=True,null=True)
    pedidos_pendientes = models.JSONField(blank=True, null=True, help_text="Pedidos en estado 'Por Pagar' al momento del cierre")

class PagoMovil(models.Model):
    referencia = models.CharField(max_length=10)
    monto = models.FloatField()
    fecha = models.DateTimeField(auto_now_add=True)
    telefono = models.CharField(max_length=20)
    cliente = models.CharField(max_length=100, blank=True, null=True)
    cliente_id = models.CharField(max_length=50, blank=True, null=True)
    cajero = models.CharField(max_length=100)
    pedido_id = models.IntegerField()
    verificado = models.BooleanField(default=False)

    def __str__(self):
        return f"Pago móvil {self.referencia} - {self.monto} Bs."