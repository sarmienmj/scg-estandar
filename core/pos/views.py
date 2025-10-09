import json
import uuid
import asyncio
from asgiref.sync import sync_to_async
from django.forms.models import BaseModelForm
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.contrib.auth.hashers import check_password
import threading
from django.conf import settings
from constance import config

from django.contrib.auth.models import *
from django.db.models import Sum
from django.db.models.functions import TruncDate
from django.views.generic.edit import FormView
from django.views.generic import View, ListView, CreateView,UpdateView
# TSPL helpers removed
from django.http import JsonResponse
from django.contrib.auth.views import PasswordChangeView
from django.contrib.auth.forms import SetPasswordForm
from django.utils import timezone
from django.db.models.functions import Lower
from datetime import datetime, timedelta
from django.template.loader import render_to_string
from .models import  *
from .forms import ProductoForm, CustomUserCreationForm, ModificarUsuarioForm, ValorDolarForm, CategoriaForm
import socket
import csv
from django import forms
from django.contrib import messages
from django.db.models import Q
import os

# Función para leer configuración
def leer_configuracion():
    config_path = "./core/config.txt"
    with open(config_path, "r") as f:
        config = f.read()
    return json.loads(config)

# Función para escribir configuración
def escribir_configuracion(config_data):
    config_path = "./core/config.txt"
    with open(config_path, "w") as f:
        json.dump(config_data, f, indent=3)

# Cargar configuración inicial
config_json = leer_configuracion()
IMPRESORAS = config_json["IMPRESORAS"]
IMPRESORAS_ETIQUETAS = config_json.get("IMPRESORAS_ETIQUETAS", {})
BALANZAS = config_json["BALANZAS"]

# Función helper para manejar conexiones socket de forma robusta
def conectar_socket_seguro(ip, puerto, datos, timeout=2, es_balanza=False):
    """
    Función helper para manejar conexiones socket de forma segura.
    
    Args:
        ip (str): Dirección IP del dispositivo
        puerto (int): Puerto de conexión
        datos (str): Datos a enviar
        timeout (int): Timeout en segundos (default: 5)
        es_balanza (bool): Si es True, espera respuesta. Si es False, solo envía.
    
    Returns:
        tuple: (success: bool, result: str, error_msg: str)
    """
    cliente_socket = None
    try:
        # Crear socket con configuración optimizada
        cliente_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        # Configurar timeouts más agresivos
        cliente_socket.settimeout(2)
        
        # Intentar conexión
        cliente_socket.connect((ip, puerto))
        
        # Enviar datos
        if isinstance(datos, str):
            datos_bytes = datos.encode('utf-8')
        else:
            datos_bytes = datos
            
        cliente_socket.sendall(datos_bytes)
        
        # Si es balanza, esperar respuesta
        if es_balanza:
            # Usar recv con timeout más corto para balanzas
            cliente_socket.settimeout(2)  # Timeout más corto para recv
            respuesta = cliente_socket.recv(2048)
            
            # Intentar decodificar la respuesta
            try:
                respuesta_str = respuesta.decode('utf-8')
            except UnicodeDecodeError:
                # Si no se puede decodificar como UTF-8, tratar como bytes raw
                respuesta_str = str(respuesta)
            
            return True, respuesta_str, ""
        else:
            # Para impresoras, solo confirmar envío exitoso
            return True, "SUCCESS", ""
            
    except socket.timeout:
        error_msg = f"Timeout conectando a {ip}:{puerto} - Sin respuesta en {timeout} segundos"
        print(f"ERROR: {error_msg}")
        return False, "", error_msg
        
    except socket.gaierror as e:
        error_msg = f"Error de resolución DNS para {ip}: {e}"
        print(f"ERROR: {error_msg}")
        return False, "", error_msg
        
    except ConnectionRefusedError:
        error_msg = f"Conexión rechazada por {ip}:{puerto}"
        print(f"ERROR: {error_msg}")
        return False, "", error_msg
        
    except OSError as e:
        error_msg = f"Error de red conectando a {ip}: {e}"
        print(f"ERROR: {error_msg}")
        return False, "", error_msg
        
    except Exception as e:
        error_msg = f"Error inesperado conectando a {ip}: {e}"
        print(f"ERROR: {error_msg}")
        return False, "", error_msg
        
    finally:
        # Limpieza segura del socket
        if cliente_socket:
            try:
                cliente_socket.close()
            except:
                pass  # Ignorar errores en close
                print("Error al cerrar el socket")

# Función helper asíncrona para manejar conexiones socket
async def conectar_socket_async(ip, puerto, datos, timeout=2, es_balanza=False):
    """
    Función helper asíncrona para manejar conexiones socket de forma segura.
    
    Args:
        ip (str): Dirección IP del dispositivo
        puerto (int): Puerto de conexión
        datos (str): Datos a enviar
        timeout (int): Timeout en segundos (default: 2)
        es_balanza (bool): Si es True, espera respuesta. Si es False, solo envía.
    
    Returns:
        tuple: (success: bool, result: str, error_msg: str)
    """
    reader = None
    writer = None
    
    try:
        print(f"🔌 Conectando async a {ip}:{puerto}")
        
        # Crear conexión asíncrona con timeout
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(ip, puerto),
            timeout=timeout
        )
        
        print(f"✅ Conexión establecida a {ip}:{puerto}")
        
        # Preparar datos para envío
        if isinstance(datos, str):
            datos_bytes = datos.encode('utf-8')
        else:
            datos_bytes = datos
        
        # Enviar datos de forma asíncrona
        writer.write(datos_bytes)
        await writer.drain()  # Asegurar que se envíen los datos
        
        print(f"📤 Datos enviados a {ip}:{puerto}: {datos}")
        
        # Si es balanza, esperar respuesta
        if es_balanza:
            # Leer respuesta con timeout
            respuesta_bytes = await asyncio.wait_for(
                reader.read(2048),
                timeout=timeout
            )
            
            # Decodificar respuesta
            try:
                respuesta_str = respuesta_bytes.decode('utf-8')
            except UnicodeDecodeError:
                respuesta_str = str(respuesta_bytes)
            
            print(f"📥 Respuesta recibida de {ip}:{puerto}: {respuesta_str}")
            return True, respuesta_str, ""
        else:
            # Para impresoras, solo confirmar envío exitoso
            print(f"🖨️ Datos enviados exitosamente a impresora {ip}")
            return True, "SUCCESS", ""
            
    except asyncio.TimeoutError:
        error_msg = f"⏱️ Timeout conectando a {ip}:{puerto} - Sin respuesta en {timeout} segundos"
        print(f"ERROR: {error_msg}")
        return False, "", error_msg
        
    except OSError as e:
        error_msg = f"🔌 Error de red conectando a {ip}: {e}"
        print(f"ERROR: {error_msg}")
        return False, "", error_msg
        
    except Exception as e:
        error_msg = f"💥 Error inesperado conectando a {ip}: {e}"
        print(f"ERROR: {error_msg}")
        return False, "", error_msg
        
    finally:
        # Limpieza segura de conexión
        if writer:
            try:
                writer.close()
                await writer.wait_closed()
                print(f"🔒 Conexión cerrada para {ip}:{puerto}")
            except Exception as e:
                print(f"⚠️ Error cerrando conexión: {e}")

class ADMIN_SUPERVISOR_AUTH(UserPassesTestMixin):
    
    def test_func(self):
        allowed_groups = ['ADMINISTRADOR', 'SUPERVISOR']
        user_groups = self.request.user.groups.values_list('name', flat=True)
        return any(group in allowed_groups for group in user_groups)
    
    def handle_no_permission(self):
        return redirect("/pos/home/")

class ADMIN_AUTH(UserPassesTestMixin):
    
    def test_func(self):
        return self.request.user.groups.filter(name='ADMINISTRADOR').exists()
    
    def handle_no_permission(self):
        return redirect("/pos/menu/")


###Vista principal del sistema POS
class PosView(LoginRequiredMixin,View):
    
     
    ###Request Get Busca todos los productos y categorias y las envia al Front
    def get(self, request, *args, **kwargs):
        dolar = ValorDolar.objects.get(pk=1)
        productos = Producto.objects.all().order_by('nombre')
        for x in productos:
            x.precio_display = "{:.2f}".format(x.precio_detal)
        
        categorias = CategoriasProductos.objects.all().order_by('orden')
        if len(kwargs) != 0:
            pedido_id=kwargs['pedido']
            pedido = Pedido.objects.filter(pk=pedido_id)

            if len(pedido) == 0:
                context={
                            "productos":productos,
                            "categorias":categorias,
                            "dolar": dolar.valor
                        }
                return render(request, 'pos.html', context)

            if pedido[0].cliente != 0:
                cliente_nombre = Cliente.objects.get(id=pedido[0].cliente).nombre

            else:
                cliente_nombre = "Cliente"

            # Determinar la tasa de dólar a usar y flags especiales
            # Si está pagado Y tiene tasa guardada, usar esa tasa. Si no, usar la actual.
            if pedido[0].status in ['Pagado', 'Pagado con Crédito']:
                if pedido[0].dolar_al_pagar:
                    dolar_para_calculo = pedido[0].dolar_al_pagar
                    pedido_pagado_flag = True
                else:
                    dolar_para_calculo = dolar.valor
                    pedido_pagado_flag = True
                pedido_devolucion_flag = False
                pedido_cancelado_flag = False
                pedido_injustificado_flag = False
            elif pedido[0].status == 'Devolución':
                dolar_para_calculo = dolar.valor
                pedido_pagado_flag = False
                pedido_devolucion_flag = True
                pedido_cancelado_flag = False
                pedido_injustificado_flag = False
            elif pedido[0].status == 'Cancelado':
                dolar_para_calculo = dolar.valor
                pedido_pagado_flag = False
                pedido_devolucion_flag = False
                pedido_cancelado_flag = True
                pedido_injustificado_flag = False
            elif pedido[0].status == 'Injustificado':
                dolar_para_calculo = dolar.valor
                pedido_pagado_flag = False
                pedido_devolucion_flag = False
                pedido_cancelado_flag = False
                pedido_injustificado_flag = True
            else:
                dolar_para_calculo = dolar.valor
                pedido_pagado_flag = False
                pedido_devolucion_flag = False
                pedido_cancelado_flag = False
                pedido_injustificado_flag = False

            productos_pedido = pedido[0].get_productos()

            # Calcular precios de productos con la tasa correcta
            for x in productos_pedido:
                precio_usd = 0
                precio_bs = 0
                cantidad = float(x.cantidad)
                precio = float(x.precio)
                moneda = x.moneda

                if moneda == "USD":
                    precio_usd = precio * cantidad
                    precio_bs = precio_usd * dolar_para_calculo
                elif moneda == "BS":
                    precio_bs = precio * cantidad
                    precio_usd = precio_bs / dolar_para_calculo

                x.precio_total_usd_display = "{:.2f}".format(precio_usd)
                x.precio_total_bs_display = "{:.2f}".format(precio_bs)
                x.precio_unitario_display = "{:.2f}".format(precio)
                x.uniqueId = uuid.uuid4().hex

            precio_total = pedido[0].precio_total
            precio_total_bs_display = "{:.2f}".format(precio_total * dolar_para_calculo)

            context={
            "productos":productos,
            "categorias":categorias,
            "status":pedido[0].status,
            "cliente_id":pedido[0].cliente,
            "cliente_nombre":cliente_nombre,
            "productos_pedido":productos_pedido,
            "pedido_id":pedido_id,
            "dolar": dolar_para_calculo, # Usar la tasa correcta
            "pedido_pagado": pedido_pagado_flag, # Pasar la bandera
            "pedido_devolucion": pedido_devolucion_flag, # Pasar la bandera de devolución
            "pedido_cancelado": pedido_cancelado_flag, # Pasar la bandera de cancelado
            "pedido_injustificado": pedido_injustificado_flag, # Pasar la bandera de injustificado
            "pedido": pedido[0], # Pasar el objeto Pedido completo
            "precio_total":precio_total,
            "precio_total_bs_display": precio_total_bs_display
            }
            return render(request, 'pos.html', context)
        context={
            "productos":productos,
            "categorias":categorias,
            "dolar": dolar.valor
        }
        return render(request, 'pos.html', context)

### Vista para filtrar por los productos por categorias
### Desde el front se hace una peticion POST a la url 'pos/filtrar-categorias/'
### El front envia un numero en la peticion POST que es igual al numero de categoria que se quiere filtrar

class FiltrarCategorias(View):

    ### peticion POST
    def post(self,request,*args, **kwargs):
        # Numero de categoria recibida en la peticion
        categoria_id = (request.POST['categoria'])

        # Si categoria_id es 0 buscar todos los productos
        # Se usa para reiniciar los filtros
        if categoria_id == "0":
            # Query de todos los productos
            #Devuelve QuerySet
            qs = Producto.objects.filter().order_by('nombre')

        # Si no es 0 busca filtra los productos por el ID que envia el FRONT 
        else:
            # Query de buscar todos los productos que tengan esta categoria 'categoria_id'
            #devuelve QuerySet
            qs = Producto.objects.filter(categoria=categoria_id).order_by('nombre')

        #iniciar lista que se enviara al front con los productos filtrados
        productos=[]

        # Ciclo for usado para llevar los datos de un QuerySet qs a un dict llamado Productos
        # No se puede enviar un queryset como en formato Json por eso aca se lleva a Dict
        for producto in qs:
            #por cada producto en el queryset separarlos y hacerles append() a el dict Productos
            p = {
                'id':producto.pk,
                'nombre':producto.nombre,
                'precio':producto.precio_detal,
                'imagen':producto.imagen,
                'unidad':producto.unidad,
                'moneda':producto.moneda
            }
            productos.append(p)

        # enviar el dict en formato Json para el front
        
        return JsonResponse(productos,safe=False)

### Vista que guarda los pedidos recibidos desde el front en peticion POST
### El front envia un array de productos y el precio total del pedido en USD$ a la url 'pos/guardar-pedido/'

class GuardarPedidoPost(View):                 
    # definir la peticion POST
    def post(self,request,*args, **kwargs):
        #Recibir el pedido desde la peticion
        #se recibe un dato de tipo QueryDict que es inmutable
        pedido = request.POST
        
        pedido = pedido.copy()

        pedido_json = json.loads(pedido['pedidoJSON'])

        pedido_id = pedido['pedido_id']

        if pedido_id != 'nuevo': pedido_existe = Pedido.objects.filter(pk=pedido_id).exists()
        else: pedido_existe = False
        

        #En el pedido el precio total se ingresa de ultimo en el Dict, para obtenerlo usamos popitem() que saca el ultimo elemento del Dict
        precio_total = pedido['precioT']
        # Extraemos el valor del precio total del dict que creamos con .popitem()

        cliente = pedido['cliente']
        usuario = pedido['usuario']
        impresora = pedido['impresora']
        
        # 🚀 OPTIMIZACIÓN: Pre-cargar todos los productos en una sola query
        # Extraer todos los IDs de productos del pedido_json
        producto_ids = [x['id'] for x in pedido_json]
        
        # Hacer un solo query para obtener todos los productos necesarios
        productos_data = {}
        if producto_ids:
            productos_queryset = Producto.objects.filter(id__in=producto_ids).only('id', 'nombre', 'unidad', 'moneda')
            productos_data = {producto.id: producto for producto in productos_queryset}
        
        #modificar pedido existente
        if pedido_existe == True:
            pedidoExistente = Pedido.objects.filter(pk=pedido_id)
            pedidoExistente = pedidoExistente[0]
            productos_borrar = pedidoExistente.get_productos()

            productos_borrar.delete()
            pedidoExistente.precio_total = precio_total
            
            # 🚀 OPTIMIZACIÓN: Preparar lista para bulk_create
            productos_pedido_list = []
            
            #Ciclo for para recorrer cada producto del pedido y obtener sus datos
            for x in pedido_json:
                id = x['id']
                cantidad = float(x['cantidad'])
                precio = float(x['precio'])
                
                # 🚀 OPTIMIZACIÓN: Usar datos pre-cargados en lugar de queries individuales
                producto_info = productos_data.get(id)
                if producto_info:
                    nombre = producto_info.nombre
                    unidad = producto_info.unidad
                    moneda = producto_info.moneda
                else:
                    # Fallback por si el producto no existe (no debería pasar en condiciones normales)
                    continue
                
                # 🚀 OPTIMIZACIÓN: Agregar a lista en lugar de save individual
                productoDePedido = ProductosPedido(
                    producto=id,
                    cantidad=cantidad,
                    precio=precio,
                    unidad=unidad,
                    producto_nombre=nombre,
                    moneda=moneda
                )
                productos_pedido_list.append(productoDePedido)
            
            # 🚀 OPTIMIZACIÓN: Crear todos los productos en una sola operación
            if productos_pedido_list:
                productos_creados = ProductosPedido.objects.bulk_create(productos_pedido_list)
                # Asignar todos los productos al pedido de una vez
                pedidoExistente.productos.set(productos_creados)

            #guardamos el pedido con todos sus productos asignados y su precio total
            pedidoExistente.save()
            #respuesta de la peticion post al front
        else:
            #creamos el pedido en la variable pedido_nuevo, status inicial 'creado' y asignamos el precio total
            pedido_nuevo = Pedido(status='Por pagar', precio_total=precio_total,cliente=cliente)
            #guardamos este pedido_nuevo en la BD
            
            pedido_nuevo.save()
            pedido_id = pedido_nuevo.id
            ### Añadir los productos, cantidad y precio al pedido

            # 🚀 OPTIMIZACIÓN: Preparar lista para bulk_create
            productos_pedido_list = []
            
            #Ciclo for para recorrer cada producto del pedido y obtener sus datos
            for x in pedido_json:
                id = x['id']
                cantidad = float(x['cantidad'])
                precio = float(x['precio'])
                
                # 🚀 OPTIMIZACIÓN: Usar datos pre-cargados en lugar de queries individuales
                producto_info = productos_data.get(id)
                if producto_info:
                    nombre = producto_info.nombre
                    unidad = producto_info.unidad
                    moneda = producto_info.moneda
                else:
                    # Fallback por si el producto no existe (no debería pasar en condiciones normales)
                    continue
                
                # 🚀 OPTIMIZACIÓN: Agregar a lista en lugar de save individual
                productoDePedido = ProductosPedido(
                    producto=id,
                    cantidad=cantidad,
                    precio=precio,
                    unidad=unidad,
                    producto_nombre=nombre,
                    moneda=moneda
                )
                productos_pedido_list.append(productoDePedido)
            
            # 🚀 OPTIMIZACIÓN: Crear todos los productos en una sola operación
            if productos_pedido_list:
                productos_creados = ProductosPedido.objects.bulk_create(productos_pedido_list)
                # Asignar todos los productos al pedido de una vez
                pedido_nuevo.productos.set(productos_creados)
                
            #guardamos el pedido con todos sus productos asignados y su precio total
            pedido_nuevo.save()
            
            #respuesta de la peticion post al front

        usuario_objeto = User.objects.get(username=usuario)
        usuario_grupos = usuario_objeto.groups.all()
        is_pesador = False
        for grupo in usuario_grupos:
            if grupo.name == "PESADOR":
                is_pesador = True
        
        if is_pesador == True:
            pedido = Pedido.objects.get(id=pedido_id)
            productos_imprimir = pedido.get_productos()
            pedido.pesador = usuario
            pedido.save()
            
            # 🧹 LIMPIEZA MULTI-PESADOR: Eliminar pedido activo del pesador
            try:
                from .models import PedidoActivo
                deleted_count, _ = PedidoActivo.objects.filter(username_pesador=usuario).delete()
                if deleted_count > 0:
                    print(f"✅ Pedido activo eliminado para pesador: {usuario}")
            except Exception as e:
                print(f"⚠️ Error eliminando pedido activo: {str(e)}")
                # No fallar el guardado por este error
            
            # 🔄 MULTI-PESADOR: Verificar si modo multi-pesador está activo para imprimir doble
            modo_multi_pesador_activo = False
            try:
                modo_multi_pesador = request.POST.get('modo_multi_pesador', 'false').lower() == 'true'
                if modo_multi_pesador:
                    modo_multi_pesador_activo = True
                    print(f"🔄 Modo multi-pesador detectado en GuardarPedidoPost - impresión doble activada")
            except Exception as e:
                print(f"⚠️ Error verificando modo multi-pesador en GuardarPedidoPost: {str(e)}")
                modo_multi_pesador_activo = False
            
            # Primera impresión (siempre)
            respon = imprimirTicket(id=pedido_id,productos=productos_imprimir,pedido=pedido,usuario="",pesador=usuario,impresora=impresora,reimprimir=False)
            
            # Segunda impresión (solo si multi-pesador está activo)
            if modo_multi_pesador_activo:
                print(f"🖨️ Iniciando segunda impresión para modo multi-pesador en GuardarPedidoPost")
                respon2 = imprimirTicket(id=pedido_id,productos=productos_imprimir,pedido=pedido,usuario="",pesador=usuario,impresora=impresora,reimprimir=False)       

        if is_pesador == True:
            url = reverse('pos:pos')
            response = {
                "url":url,
                "imprimir_status":"SUCCESS",
                "id":pedido_id,
                "pesador":True
            }
        else:
            pedido = Pedido.objects.get(id=pedido_id)
            pedido.usuario = usuario
            pedido.save()   
            url = reverse('pos:pago', args=[pedido_id])    
            response = {
                "url":url,
                "pesador":False
            }
        return JsonResponse(response)

### Vista para listar los pedidos 
# Al momento de listar los pedidos el front hace una peticion POST a la ruta 'pos/pedidosList/'

class ReimprimirTicket(View):
    def post(self,request,*args, **kwargs):
        
        pedido_id = request.POST['pedido_id']
        impresora = request.POST['impresora']
        
        pedido = Pedido.objects.filter(pk=pedido_id)[0]
        productos = pedido.get_productos()
        if pedido.usuario:
            usuario = pedido.usuario
        else:
            usuario = "-"
        if pedido.pesador:
            pesador = pedido.pesador
        else:
            pesador = '='
        # Verificar si el pedido fue pagado con crédito
        credito_usado = 0
        try:
            credito_pedido = Credito.objects.filter(pedido_id=pedido_id).first()
            if credito_pedido:
                credito_usado = credito_pedido.monto_credito
        except Credito.DoesNotExist:
            credito_usado = 0
        
        # Pasar la tasa de dólar histórica si existe
        impresion = imprimirTicket(id=pedido_id, productos=productos, pedido=pedido, usuario=usuario, pesador=pesador, impresora=impresora, reimprimir=True, dolar_historico=pedido.dolar_al_pagar, credito_usado=credito_usado)
        url = reverse('pos:posPedido',  args=[pedido_id])

        response = {
            "imprimir_status": impresion,
            "id": pedido_id,
            "url": url
        }

        return JsonResponse(response)

class PedidosList(View):
    def post(self,request,*args, **kwargs):
        
        # 🎯 FILTRO PARA PESADORES: Solo mostrar sus propios pedidos
        user_groups = [group.name for group in request.user.groups.all()]
        
        if 'PESADOR' in user_groups:
            # Si es PESADOR: Solo pedidos donde él es el pesador
            pedidos = Pedido.objects.filter(pesador=request.user.username).order_by('-pk')[:100]
        else:
            # Si es CAJERO/ADMIN: Todos los pedidos (comportamiento original)
            pedidos = Pedido.objects.filter().order_by('-pk')[:100]
        
        # pedidos_lista es un dict que enviaremos al front con todos pedidos, no podemos enviar un dato QuerySet al front
        pedidos_lista = []
        
        #recorremos cada pedido en el QuerySet Pedidos para añadirlo al dict 'pedidos_lista'
        for pedido in pedidos:
            # Obtener el nombre del cliente si existe
            cliente_nombre = "-"
            if pedido.cliente != 0:
                try:
                    cliente_obj = Cliente.objects.get(pk=pedido.cliente)
                    cliente_nombre = cliente_obj.nombre
                except Cliente.DoesNotExist:
                    cliente_nombre = f"Cliente ID: {pedido.cliente}"
            
            p = {
                "pk": pedido.pk,
                "status": pedido.status,
                "preciototal": pedido.precio_total,
                "fecha": pedido.fecha,
                "cliente": cliente_nombre,  # Usar el nombre del cliente en lugar del ID
                'id': pedido.id,
                'cajero': pedido.usuario,
                'pesador': pedido.pesador or "-",  # 🎯 NUEVO: Campo pesador para mostrar en UI
            }
            pedidos_lista.append(p)
        #enviamos dict de pedidos al front
        return JsonResponse(pedidos_lista,safe=False)
    
class PedidosListTodos(View):
    def post(self,request,*args, **kwargs):
        
        # 🎯 NUEVA VISTA: Mostrar TODOS los pedidos sin restricción de roles
        # Limitado a 100 pedidos ordenados del más reciente
        pedidos = Pedido.objects.all().order_by('-pk')[:100]
        
        # pedidos_lista es un dict que enviaremos al front con todos pedidos
        pedidos_lista = []
        
        #recorremos cada pedido en el QuerySet Pedidos para añadirlo al dict 'pedidos_lista'
        for pedido in pedidos:
            # Obtener el nombre del cliente si existe
            cliente_nombre = "-"
            if pedido.cliente != 0:
                try:
                    cliente_obj = Cliente.objects.get(pk=pedido.cliente)
                    cliente_nombre = cliente_obj.nombre
                except Cliente.DoesNotExist:
                    cliente_nombre = f"Cliente ID: {pedido.cliente}"
            
            p = {
                "pk": pedido.pk,
                "status": pedido.status,
                "preciototal": pedido.precio_total,
                "fecha": pedido.fecha,
                "cliente": cliente_nombre,  # Usar el nombre del cliente en lugar del ID
                'id': pedido.id,
                'cajero': pedido.usuario,
                'pesador': pedido.pesador or "-",  # Campo pesador para mostrar en UI
            }
            pedidos_lista.append(p)
        #enviamos dict de pedidos al front
        return JsonResponse(pedidos_lista,safe=False)
    
class ClientesList(View):
    def post(self,request,*args, **kwargs):
        # pedidoses un QuerySet y hace un query a la base de datos de todos los pedidos en orden descendente ordenados por su Id o pk (pk: Primary Key)
        clientes = Cliente.objects.all().order_by('-pk')
        # pedidos_lista es un dict que enviaremos al front con todos pedidos, no podemos enviar un dato QuerySet al front
        cliente_lista = []
        #recorremos cada pedido en el QuerySet Pedidos para añadirlo al dict 'pedidos_lista'
        for cliente in clientes:
            # Calcular la deuda total del cliente
            creditos = Credito.objects.filter(cliente_id=cliente.cedula)
            abonos_totales = sum(CreditoAbono.objects.filter(credito_id__in=creditos.values_list('id', flat=True)).values_list('monto', flat=True))
            deuda_total = sum(creditos.values_list('monto_credito', flat=True)) - abonos_totales
            deuda_total = round(deuda_total, 2)
            
            # Calcular el crédito disponible como crédito máximo - deuda total
            credito_disponible = cliente.credito_maximo - deuda_total
            credito_disponible = max(0, round(credito_disponible, 2))  # Asegurar que no sea negativo
            
            c = {
                "pk": cliente.pk,
                "nombre": cliente.nombre,
                "cedula": cliente.cedula,
                "telefono": cliente.telefono,
                "zona_vive": cliente.zona_vive,
                "credito": credito_disponible,  # Ahora credito es el crédito disponible calculado
                "deuda_total": deuda_total,
                "credito_maximo": cliente.credito_maximo
            }
            cliente_lista.append(c)
        #enviamos dict de pedidos al front
        return JsonResponse(cliente_lista,safe=False)
    

class PaginaPago(LoginRequiredMixin,View):
    def get(self,request,*args, **kwargs):
        dolar = ValorDolar.objects.get(pk=1)
        pedido_id = kwargs['pedido']
        pedido = Pedido.objects.filter(pk=pedido_id)
        precio_total = pedido[0].precio_total
        
        context={
            'pedido_id':pedido_id,
            "dolar": dolar.valor,
            'precio_total':precio_total,
        }
        
        if pedido[0].cliente != 0:
            cliente = Cliente.objects.get(pk=pedido[0].cliente)
            
            # Calcular la deuda total del cliente
            creditos = Credito.objects.filter(cliente_id=cliente.cedula)
            abonos_totales = sum(CreditoAbono.objects.filter(credito_id__in=creditos.values_list('id', flat=True)).values_list('monto', flat=True))
            deuda_total = sum(creditos.values_list('monto_credito', flat=True)) - abonos_totales
            deuda_total = round(deuda_total, 2)
            
            # Calcular el crédito disponible como crédito máximo - deuda total
            credito_disponible = cliente.credito_maximo - deuda_total
            credito_disponible = max(0, round(credito_disponible, 2))  # Asegurar que no sea negativo
            
            # Pasar la información al contexto como strings para evitar NaN
            cliente.credito = str(credito_disponible)
            context['cliente'] = cliente
            context['credito'] = str(credito_disponible)  # Añadir como variable separada
            context['deuda_total'] = deuda_total
        else:
            # Si no hay cliente, establecer crédito en 0
            context['credito'] = "0"
        
        return render(request, 'pagar.html', context)

def imprimirTicket(id, productos, pedido, usuario, pesador, impresora, reimprimir, dolar_historico=None, credito_usado=0):
    fecha = datetime.now()
    # Usar tasa histórica si se proporciona, si no, la actual
    if dolar_historico is not None:
        bcv_valor = dolar_historico
    else:
        bcv_obj = ValorDolar.objects.get(pk=1)
        bcv_valor = bcv_obj.valor
    
    # Formatear hora en formato 12 horas con AM/PM
    hora_12h = fecha.strftime("%I:%M:%S %p")
    fecha_str = f'{hora_12h} - {fecha.day}/{fecha.month}/{fecha.year}'
    fecha_len = len(fecha_str)
    
    # Formatear información de cajero
    login = f'CAJERO: {usuario}'
    login_len = len(login)
    
    # Calcular espacios para alinear el cajero a la derecha
    espacios = 48 - (fecha_len + login_len)
    login = login.rjust(len(login) + espacios)
    
    # Línea con fecha y cajero
    fecha_login_line = fecha_str + login
    
    # Si hay pesador, crear una línea adicional
    if pesador:
        login_pesador = f'PESADOR: {pesador}'
        login_pesador_len = len(login_pesador)
        
        # Alinear el pesador a la derecha del ticket
        espacios_pesador = 48 - login_pesador_len
        pesador_line = ' ' * espacios_pesador + login_pesador
    else:
        pesador_line = ''
    
    # Obtener información del cliente si existe
    nombre_cliente = "CLIENTE GENERAL"
    telefono_cliente = "0000-000.00.00"
    
    if pedido.cliente != 0:
        try:
            cliente = Cliente.objects.get(pk=pedido.cliente)
            nombre_cliente = cliente.nombre
            telefono_cliente = str(cliente.telefono)
            # Formatear el número de teléfono si es necesario
            if len(telefono_cliente) == 10:
                telefono_cliente = f"{telefono_cliente[0:4]}-{telefono_cliente[4:7]}.{telefono_cliente[7:10]}"
        except Cliente.DoesNotExist:
            pass
    
    total_peso = 0
    total_unidades = 0
    productos_str = ""
    dolar = "{:.2f}".format(bcv_valor)
    sucursal = config.BUSINESS_NAME
    header = f'\x1B@\x1B\x61\x01\x1D\x54\x1C\x70\x01\x33\x1B\x21\x08{sucursal}\x1B!\x01\x1B\x21\x00\x0A\x0D------------------------------------------------\x0A\x0D'
    info = f'{fecha_login_line}\x0A\x0D\x1B\x61\x00{pesador_line}\x0A\x0D\x1B\x61\x00TASA CAMBIO $ = Bs {dolar}\x0A\x0DCLIENTE: {nombre_cliente}\x0A\x0DTelefono: {telefono_cliente}\x0A\x0D------------------------------------------------\x0A\x0D'
    tabla = f'\x1B\x44\x15\x1E\x26\x00\x1B!\x01\x1B\x21\x09       DESCRIPCION          CANTIDAD      PRECIO      SUB-TOTAL\x1B\x21\x01\x0A\x0D'

    for i in productos:

        if i.unidad == "U":
            i.cantidad = int(i.cantidad)
        if i.unidad != "U":
            total_peso += i.cantidad
        else:
            total_unidades += i.cantidad

        if i.moneda == "BS":
            precio_producto = i.precio * i.cantidad
            precio = i.precio
        if i.moneda == "USD":
            precio_producto = (i.precio * i.cantidad) * bcv_valor
            precio = i.precio * bcv_valor
        precio_producto = "{:.2f}".format(precio_producto)
        precio = "{:.2f}".format(precio)
        cantidad = str(i.cantidad)
        precio = str(precio)
        subtotal = str(precio_producto)
        #cantidad
        cantidad_ajuste = 8-(len(cantidad))
        cantidad_imprimir = cantidad.rjust(len(cantidad)+cantidad_ajuste)
        #precio
        precio_ajuste = 9-(len(precio))
        precio_imprimir = precio.rjust(len(precio)+precio_ajuste)
        #subtotal
        subtotal_ajuste = 12-(len(subtotal))
        subtotal_imprimir = subtotal.rjust(len(subtotal)+subtotal_ajuste)

        productos_str += f'{i.producto_nombre}\x09{cantidad_imprimir}\x09{precio_imprimir}\x09{subtotal_imprimir}\x0A\x0D'

    preciototal_usd = "{:.2f}".format(pedido.precio_total)
    preciototal_bs = "{:.2f}".format(bcv_valor * pedido.precio_total)
    
    # Verificar si se usó crédito para cambiar el formato del ticket
    if credito_usado > 0:
        # Formato especial para pagos con crédito - Solo mostrar total en dólares
        total = f'\x1B\x61\x02\x1B\x21\x31TOTAL REF$ = {preciototal_usd}\x1B\x21\x08\x1B\x21\x00\x0A\x0D\x0A\x0D'
    else:
        # Formato normal para pagos sin crédito - TOTAL REF$ primero (letra pequeña), TOTAL Bs segundo (letra grande)
        total = f'\x0A\x0D\x0A\x0D\x1B\x61\x02\x1B\x21\x08TOTAL REF$ = {preciototal_usd}\x0A\x0D\x0A\x0D\x1B\x21\x31TOTAL Bs = {preciototal_bs}\x1B\x21\x00\x0A\x0D\x0A\x0D'

    barcode = f'\x1B\x61\x01\x1D\x6B\x04{"PP" + str(id)}\x00{"PP-" + str(id)}\x0A\x0D'
    
    # Agregar sección de detalles de crédito DESPUÉS del código de barras
    detalles_credito = ""
    if credito_usado > 0:
        fecha_credito = fecha.strftime("%d/%m/%Y")
        hora_credito = fecha.strftime("%I:%M:%S %p")
        credito_usado_str = "{:.2f}".format(credito_usado)
        
        detalles_credito = f'------------------------------------------------\x0A\x0D'
        detalles_credito += f'\x1B\x61\x01\x1B\x21\x11DETALLES DE CREDITO\x1B\x21\x00\x0A\x0D'
        detalles_credito += f'\x1B\x61\x00Usuario: {usuario}\x0A\x0D'
        detalles_credito += f'Fecha: {fecha_credito}\x0A\x0D'
        detalles_credito += f'Hora: {hora_credito}\x0A\x0D'
        detalles_credito += f'\x0A\x0D\x1B\x61\x02\x1B\x21\x31Monto del Credito a Pagar:\x0A\x0D'
        detalles_credito += f'TOTAL REF$ = {credito_usado_str}\x1B\x21\x00\x0A\x0D\x0A\x0D'
        detalles_credito += f'\x1B\x61\x01Se toma como referencia la tasa de cambio\x0A\x0D del BCV al dia de pago\x0A\x0D\x0A\x0D'
    
    final_comandos = '\x0A\x0A\x0A\x0A\x0A\x0A\x1B\x69'
    comandos = header + info + tabla + productos_str + total + barcode + detalles_credito + final_comandos
    
    # Usar la nueva función helper para impresoras
    success, result, error_msg = conectar_socket_seguro(
        ip=impresora, 
        puerto=9100, 
        datos=comandos, 
        timeout=2,  # Timeout optimizado para impresoras
        es_balanza=False
    )
    
    if success:
        print(f"Ticket impreso exitosamente en impresora {impresora}")
        return "SUCCESS"
    else:
        return "ERROR"



class PagarPedido(View):
    def post(self,request,*args, **kwargs):
        pedido_id = kwargs['pedido']
        data = request.POST
        usuario = data['usuario']
        impresora = data['impresora']
        credito_usado = float(data['credito_usado'])
        pedido_modificado = data['pedido_modificado']
        pedido = Pedido.objects.filter(pk=pedido_id)[0]
        productos_pedido = pedido.get_productos()

        movimientos_caja = json.loads(data.get('movimientos_caja', '{}'))
        
        # Procesar pagos móviles si se proporcionan
        pagos_moviles_data = json.loads(data.get('pagos_moviles', '[]'))
        for pago_movil_data in pagos_moviles_data:
            # Crear registro de pago móvil
            pago_movil = PagoMovil(
                referencia=pago_movil_data['referencia'],
                monto=pago_movil_data['monto'],
                telefono=pago_movil_data['telefono'],
                cajero=usuario,
                pedido_id=pedido_id,
                verificado=False
            )
            
            # Si hay un cliente asociado al pedido, guardarlo
            if pedido.cliente != 0:
                try:
                    cliente_obj = Cliente.objects.get(pk=pedido.cliente)
                    pago_movil.cliente = cliente_obj.nombre
                    pago_movil.cliente_id = cliente_obj.cedula
                except Cliente.DoesNotExist:
                    pass
            
            pago_movil.save()

        for producto in productos_pedido:
            try:
                producto_query = Producto.objects.get(id=producto.producto)
            except Producto.DoesNotExist:
                # Si el producto no existe, continuar con el siguiente
                # Esto puede pasar si un producto fue eliminado después de crear el pedido
                print(f"Producto no encontrado: {producto.producto}")
                continue
            
            if producto_query.subproducto == None:
                producto_query.cantidad = producto_query.cantidad - float(producto.cantidad) 
                producto_query.save()
            else:
                try:
                    subproducto_query = Producto.objects.get(nombre=producto_query.subproducto)
                    subproducto_query.cantidad = subproducto_query.cantidad - float(producto.cantidad * producto_query.relacion_subproducto) 
                    subproducto_query.save()
                except Producto.DoesNotExist:
                    # Si el subproducto no existe, solo actualizar el producto principal
                    producto_query.cantidad = producto_query.cantidad - float(producto.cantidad) 
        producto_query.save()
        if credito_usado > 0:
            cliente = Cliente.objects.filter(pk=pedido.cliente)[0]

            cliente.credito = cliente.credito - credito_usado

            credito = Credito(
                cliente = cliente.nombre,
                cliente_id = cliente.cedula,
                monto_credito = round(credito_usado,2),
                plazo_credito = cliente.credito_plazo,
                fecha = timezone.now(),
                fecha_vencimiento = timezone.now() + timedelta(days=cliente.credito_plazo),
                abonado = 0,
                pedido_id = pedido_id,
                estado = "Pendiente"
            )
            credito.save()
        
            cliente.save()
        
        # Imprimir ticket si es necesario
        # Siempre imprimir si el pedido fue modificado O si se usó crédito
        if pedido_modificado == 'true' or credito_usado > 0:
            pesador = pedido.pesador
            impresora_response = imprimirTicket(pedido_id,productos_pedido,pedido,usuario, pesador,impresora,reimprimir=False, credito_usado=credito_usado)
            if impresora_response == "ERROR":
                return JsonResponse({"impresora": False})

        # Actualizar estado del pedido
        # Guardar la tasa de dólar al momento de pagar
        dolar_actual = ValorDolar.objects.get(pk=1)
        pedido.dolar_al_pagar = dolar_actual.valor
        
        # Asignar status según si se usó crédito o no
        if credito_usado > 0:
            pedido.status = "Pagado con Crédito"
        else:
            pedido.status = "Pagado"
            
        pedido.pagado_fecha = timezone.now()
        pedido.save()

        # ✅ NOTA: No eliminar pedido activo al pagar - se mantiene para que el pesador pueda continuar trabajando
        # El pedido activo se elimina solo cuando se guarda un nuevo pedido o se elimina manualmente

        # Actualizar el dinero esperado en caja DESPUÉS de marcar el pedido como pagado
        try:
            caja_actual = estadoCaja.objects.get(
                usuario=request.user,
                fechaFin__isnull=True
            )
            
            dinero_esperado = caja_actual.dineroEsperado or {
                'ingresos': {'USD': {}, 'BS': {}, 'DEBITO': 0, 'CREDITO': 0, 'PAGOMOVIL': 0},
                'egresos': {'USD': {}, 'BS': {}}
            }
            
            # Procesar ingresos y egresos
            for tipo in ['ingresos', 'egresos']:
                for moneda in ['USD', 'BS']:
                    if moneda in movimientos_caja[tipo]:
                        for denom, cantidad in movimientos_caja[tipo][moneda].items():
                            if tipo not in dinero_esperado:
                                dinero_esperado[tipo] = {}
                            if moneda not in dinero_esperado[tipo]:
                                dinero_esperado[tipo][moneda] = {}
                            
                            denom_str = str(denom)
                            if denom_str not in dinero_esperado[tipo][moneda]:
                                dinero_esperado[tipo][moneda][denom_str] = 0
                            dinero_esperado[tipo][moneda][denom_str] += cantidad
            
            # Agregar débito y crédito
            dinero_esperado['ingresos']['DEBITO'] = dinero_esperado['ingresos'].get('DEBITO', 0) + movimientos_caja['ingresos'].get('DEBITO', 0)
            dinero_esperado['ingresos']['CREDITO'] = dinero_esperado['ingresos'].get('CREDITO', 0) + movimientos_caja['ingresos'].get('CREDITO', 0)
            dinero_esperado['ingresos']['PAGOMOVIL'] = dinero_esperado['ingresos'].get('PAGOMOVIL', 0) + movimientos_caja['ingresos'].get('PAGOMOVIL', 0)
            
            caja_actual.dineroEsperado = dinero_esperado
            caja_actual.save()

        except estadoCaja.DoesNotExist:
            pass  # Continuar si no hay caja abierta, no afecta el pago

        url = reverse('pos:pos')
        response = {
            "url": url
        }
        return JsonResponse(response, safe=False)

    
class Home(LoginRequiredMixin,View):
    def get(self,request,*args, **kwargs):
        context={}
        return render(request, 'home.html', context)
    
class PrePesados(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        # Cargar productos directamente del modelo
        productos = Producto.objects.all().order_by('nombre')
        
        # Formatear productos para el frontend
        productos_data = []
        for producto in productos:
            # Manejar imagen del producto
            image_url = '/media/logo.png'  # imagen por defecto
            if producto.imagen:
                try:
                    image_url = producto.imagen.url
                except:
                    # Si hay error al obtener la URL, usar imagen por defecto basada en el nombre
                    encoded_name = producto.nombre.replace(' ', '_')
                    image_url = f'/media/{encoded_name}.png'
            else:
                # Si no tiene imagen, intentar con el nombre del producto
                encoded_name = producto.nombre.replace(' ', '_')
                image_url = f'/media/{encoded_name}.png'
            
            # Convertir unidad 'K' a 'KG' para mejor visualización
            unit_display = 'KG' if producto.unidad == 'K' else producto.unidad
            
            productos_data.append({
                'id': producto.id,
                'title': producto.nombre,
                'price': float(producto.precio_detal),
                'currency': producto.moneda,  # Usar la moneda del producto
                'unit': unit_display,
                'image': image_url
            })
        
        import json
        context = {
            'productos': productos_data,
            'productos_json': json.dumps(productos_data)
        }
        return render(request, 'pre_pesados.html', context)

class ObtenerPesadores(LoginRequiredMixin, View):
    """Vista para obtener lista de usuarios con rol PESADOR"""
    def get(self, request, *args, **kwargs):
        try:
            from django.contrib.auth.models import User, Group
            
            # Obtener grupo PESADOR
            try:
                grupo_pesador = Group.objects.get(name='PESADOR')
            except Group.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': 'Grupo PESADOR no existe en el sistema'
                }, status=404)
            
            # Obtener usuarios pesadores activos
            pesadores = User.objects.filter(
                groups=grupo_pesador, 
                is_active=True
            ).order_by('first_name', 'last_name', 'username')
            
            pesadores_data = []
            for pesador in pesadores:
                # Construir nombre completo
                nombre_completo = f"{pesador.first_name} {pesador.last_name}".strip()
                if not nombre_completo:
                    nombre_completo = pesador.username
                
                pesadores_data.append({
                    'id': pesador.id,
                    'username': pesador.username,
                    'nombre': pesador.first_name,
                    'apellido': pesador.last_name,
                    'nombre_completo': nombre_completo,
                    'email': pesador.email,
                    'fecha_registro': pesador.date_joined.isoformat() if pesador.date_joined else None,
                    'ultimo_login': pesador.last_login.isoformat() if pesador.last_login else None
                })
            
            return JsonResponse({
                'success': True,
                'pesadores': pesadores_data,
                'total': len(pesadores_data)
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Error al obtener pesadores: {str(e)}'
            }, status=500)



class GuardarPedidoActivo(LoginRequiredMixin, View):
    """
    Vista para guardar el pedido activo del pesador en modo multi-pesador.
    Permite persistir el estado del pedido para que pueda continuar en otra estación.
    """
    
    def post(self, request, *args, **kwargs):
        try:
            from .models import PedidoActivo
            
            # Debug: Log request details
            print(f"🔍 GuardarPedidoActivo - Content-Type: {request.content_type}")
            print(f"🔍 GuardarPedidoActivo - Request body: {request.body}")
            
            # Parsear datos del request
            try:
                body = json.loads(request.body)
                print(f"✅ JSON parsed successfully: {body}")
            except json.JSONDecodeError as e:
                print(f"❌ JSON decode error: {str(e)}")
                return JsonResponse({
                    'success': False,
                    'error': f'JSON inválido: {str(e)}'
                }, status=400)
            
            # Validar campos requeridos
            required_fields = ['username_pesador', 'pedido_json', 'precio_total']
            for field in required_fields:
                if field not in body:
                    print(f"❌ Campo faltante: {field}")
                    return JsonResponse({
                        'success': False,
                        'error': f'Campo requerido: {field}'
                    }, status=400)
            
            username_pesador = body['username_pesador']
            pedido_json = body['pedido_json']
            precio_total = float(body['precio_total'])
            cliente_id = body.get('cliente_id', 0)
            cliente_nombre = body.get('cliente_nombre', 'Cliente')
            estacion_actual = body.get('estacion_actual', '')
            
            # Validar que el usuario sea un pesador autorizado
            from django.contrib.auth.models import User, Group
            try:
                user = User.objects.get(username=username_pesador)
                grupo_pesador = Group.objects.get(name='PESADOR')
                if not user.groups.filter(name='PESADOR').exists():
                    return JsonResponse({
                        'success': False,
                        'error': 'Usuario no autorizado para modo multi-pesador'
                    }, status=403)
            except (User.DoesNotExist, Group.DoesNotExist):
                return JsonResponse({
                    'success': False,
                    'error': 'Usuario o grupo PESADOR no encontrado'
                }, status=404)
            
            # Validar que el pedido no esté vacío
            if not pedido_json or len(pedido_json) == 0:
                # Si el pedido está vacío, eliminar el registro existente si existe
                PedidoActivo.objects.filter(username_pesador=username_pesador).delete()
                return JsonResponse({
                    'success': True,
                    'message': 'Pedido activo eliminado (pedido vacío)',
                    'action': 'deleted'
                })
            
            # Crear o actualizar el pedido activo
            pedido_activo, created = PedidoActivo.objects.update_or_create(
                username_pesador=username_pesador,
                defaults={
                    'pedido_json': pedido_json,
                    'precio_total': precio_total,
                    'cliente_id': cliente_id,
                    'cliente_nombre': cliente_nombre,
                    'estacion_actual': estacion_actual
                }
            )
            
            action = 'created' if created else 'updated'
            message = f'Pedido activo {"creado" if created else "actualizado"} exitosamente'
            
            return JsonResponse({
                'success': True,
                'message': message,
                'action': action,
                'pedido_activo': {
                    'id': pedido_activo.id,
                    'username_pesador': pedido_activo.username_pesador,
                    'numero_productos': pedido_activo.numero_productos,
                    'precio_total': pedido_activo.precio_total,
                    'cliente_nombre': pedido_activo.cliente_nombre,
                    'fecha_ultima_modificacion': pedido_activo.fecha_ultima_modificacion.isoformat(),
                    'productos_display': pedido_activo.get_productos_display()
                }
            })
            
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'JSON inválido en el cuerpo de la petición'
            }, status=400)
        except ValueError as e:
            return JsonResponse({
                'success': False,
                'error': f'Error en los datos: {str(e)}'
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Error interno del servidor: {str(e)}'
            }, status=500)



class CargarPedidoActivo(LoginRequiredMixin, View):
    """
    Vista para cargar el pedido activo de un pesador específico.
    Permite recuperar el estado del pedido cuando cambia de estación.
    """
    
    def get(self, request, *args, **kwargs):
        try:
            from .models import PedidoActivo
            
            # Debug: Log request details
            print(f"🔍 CargarPedidoActivo - GET params: {request.GET}")
            
            # Obtener username del pesador desde parámetros
            username_pesador = request.GET.get('username_pesador')
            print(f"🔍 CargarPedidoActivo - username_pesador: {username_pesador}")
            
            if not username_pesador:
                print("❌ username_pesador no proporcionado")
                return JsonResponse({
                    'success': False,
                    'error': 'Parámetro username_pesador es requerido'
                }, status=400)
            
            # Validar que el usuario sea un pesador autorizado
            from django.contrib.auth.models import User, Group
            try:
                user = User.objects.get(username=username_pesador)
                if not user.groups.filter(name='PESADOR').exists():
                    return JsonResponse({
                        'success': False,
                        'error': 'Usuario no autorizado para modo multi-pesador'
                    }, status=403)
            except User.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': 'Usuario no encontrado'
                }, status=404)
            
            # Buscar pedido activo del pesador
            try:
                pedido_activo = PedidoActivo.objects.get(username_pesador=username_pesador)
                
                return JsonResponse({
                    'success': True,
                    'tiene_pedido_activo': True,
                    'pedido_activo': {
                        'id': pedido_activo.id,
                        'username_pesador': pedido_activo.username_pesador,
                        'pedido_json': pedido_activo.pedido_json,
                        'precio_total': pedido_activo.precio_total,
                        'cliente_id': pedido_activo.cliente_id,
                        'cliente_nombre': pedido_activo.cliente_nombre,
                        'numero_productos': pedido_activo.numero_productos,
                        'fecha_creacion': pedido_activo.fecha_creacion.isoformat(),
                        'fecha_ultima_modificacion': pedido_activo.fecha_ultima_modificacion.isoformat(),
                        'estacion_actual': pedido_activo.estacion_actual,
                        'productos_display': pedido_activo.get_productos_display()
                    }
                })
                
            except PedidoActivo.DoesNotExist:
                return JsonResponse({
                    'success': True,
                    'tiene_pedido_activo': False,
                    'message': 'No hay pedido activo para este pesador'
                })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Error al cargar pedido activo: {str(e)}'
            }, status=500)



class EliminarPedidoActivo(LoginRequiredMixin, View):
    """
    Vista para eliminar el pedido activo de un pesador.
    Se usa cuando se finaliza/guarda un pedido y ya no debe estar activo.
    """
    
    def post(self, request, *args, **kwargs):
        try:
            from .models import PedidoActivo
            
            # Parsear datos del request
            body = json.loads(request.body)
            username_pesador = body.get('username_pesador')
            
            if not username_pesador:
                return JsonResponse({
                    'success': False,
                    'error': 'Campo username_pesador es requerido'
                }, status=400)
            
            # Validar autorización del usuario
            from django.contrib.auth.models import User
            try:
                user = User.objects.get(username=username_pesador)
                if not user.groups.filter(name='PESADOR').exists():
                    return JsonResponse({
                        'success': False,
                        'error': 'Usuario no autorizado'
                    }, status=403)
            except User.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': 'Usuario no encontrado'
                }, status=404)
            
            # Eliminar pedido activo si existe
            deleted_count, _ = PedidoActivo.objects.filter(username_pesador=username_pesador).delete()
            
            if deleted_count > 0:
                return JsonResponse({
                    'success': True,
                    'message': 'Pedido activo eliminado exitosamente',
                    'deleted': True
                })
            else:
                return JsonResponse({
                    'success': True,
                    'message': 'No había pedido activo para eliminar',
                    'deleted': False
                })
            
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'JSON inválido en el cuerpo de la petición'
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Error al eliminar pedido activo: {str(e)}'
            }, status=500)

class ImprimirEtiquetaTSPL(LoginRequiredMixin, View):
    """
    Imprime etiquetas TSPL de forma asíncrona para productos pesados.
    Diseño: Nombre del negocio, fecha/peso/precio, nombre producto, precio total en caja, código EAN13
    """
    
    def calcular_digito_verificador_ean13(self, codigo_12_digitos):
        """Calcula el dígito verificador para código EAN13"""
        suma = 0
        for i, digito in enumerate(codigo_12_digitos):
            if i % 2 == 0:  # Posiciones impares (0, 2, 4, ...)
                suma += int(digito)
            else:  # Posiciones pares (1, 3, 5, ...)
                suma += int(digito) * 3
        
        resto = suma % 10
        return str((10 - resto) % 10)
    
    def generar_codigo_ean13(self, producto_id, peso_kg, unidad='K'):
        """Genera código EAN13: 21 + 5 dígitos producto + 5 dígitos peso/cantidad + dígito verificador"""
        # Formatear producto ID a 5 dígitos
        producto_str = f"{producto_id:05d}"
        
        # Truncar peso/cantidad según la unidad
        import math
        if unidad == 'U':
            # Para productos unitarios, truncar a entero
            peso_truncado = math.floor(peso_kg)
            peso_gramos = int(peso_truncado * 100)  # Multiplicar por 100 para compatibilidad
        else:
            # Para productos por peso, truncar a 3 decimales sin redondear
            peso_truncado = math.floor(peso_kg * 1000) / 1000  # Truncar a 3 decimales
            peso_gramos = int(peso_truncado * 100)  # Convertir kg a centenas de gramos
        
        peso_str = f"{peso_gramos:05d}"
        
        # Construir los primeros 12 dígitos
        codigo_12 = f"21{producto_str}{peso_str}"
        
        # Calcular dígito verificador
        digito_verificador = self.calcular_digito_verificador_ean13(codigo_12)
        
        return codigo_12 + digito_verificador

    def post(self, request, *args, **kwargs):
        try:
            data = request.POST
            nombre = data.get('nombre', '').strip()[:25]  # Limitar para que quepa en etiqueta
            moneda = (data.get('moneda', 'USD') or 'USD').upper()
            unidad = (data.get('unidad', 'K') or 'K').upper()
            impresora = data.get('impresora', '').strip()  # Usar la impresora enviada por el cliente
            copias = int(data.get('copias', 1))
            producto_id = int(data.get('producto_id'))
            precio_unit = float(data.get('precio_unit', 0))
            peso_original = float(data.get('peso', 0))
            
            # Truncar peso según la unidad
            import math
            if unidad == 'U':
                # Para productos unitarios, truncar a entero
                peso = math.floor(peso_original)
            else:
                # Para productos por peso, truncar a 3 decimales sin redondear
                peso = math.floor(peso_original * 1000) / 1000

            from django.conf import settings
            negocio = settings.SUCURSAL
            
            # Obtener fecha actual
            from datetime import datetime
            fecha_actual = datetime.now().strftime("%d/%m/%y")
            
            # Convertir precio unitario a dólares si es necesario
            precio_unit_usd = precio_unit
            if moneda == 'BS':
                try:
                    from .models import ValorDolar
                    valor_dolar = ValorDolar.objects.first()
                    if valor_dolar and valor_dolar.valor > 0:
                        precio_unit_usd = precio_unit / valor_dolar.valor
                    else:
                        precio_unit_usd = precio_unit / 36  # Valor por defecto si no hay tasa
                except:
                    precio_unit_usd = precio_unit / 36  # Valor por defecto si hay error
            
            # Calcular precio total en dólares
            precio_total_usd = precio_unit_usd * peso
            
            # Generar código EAN13
            codigo_barras = self.generar_codigo_ean13(producto_id, peso, unidad)
            
            # Coordenadas para etiqueta 58mm x 32mm (aprox 464x256 dots a 200 DPI)
            # Ajustando para impresora térmica típica
            
            tspl_lines = [
                "SIZE 58 mm,32 mm",
                "GAP 2 mm,0",
                "DIRECTION 0",
                "DENSITY 8",
                "REFERENCE 0,0",
                "CLS",
                
                # Nombre del negocio (centrado, parte superior)
                f'TEXT 10,17,"3",0,1,1,"{negocio}"',
                
                # Barra separadora
                'BAR 0,46,500,3',
                
                # Encabezados de las columnas
                f'TEXT 10,54,"2",0,1,1,"Fecha:"',
                f'TEXT 170,54,"2",0,1,1,"Precio:"',
                f'TEXT 314,54,"2",0,1,1,"{"Cant:" if unidad == "U" else "Peso:"}"',
                
                # Título del producto (limitado a 20 caracteres)
                f'TEXT 15,125,"4",0,1,1,"{nombre[:20]}"',
                
                # Datos de las columnas
                f'TEXT 10,78,"2",0,1,1,"{fecha_actual}"',
                f'TEXT 170,78,"2",0,1,1,"{precio_unit_usd:.2f}$/{"U" if unidad == "U" else "Kg"}"',
                f'TEXT 310,78,"3",0,1,1,"{peso:.0f} U"' if unidad == "U" else f'TEXT 310,78,"3",0,1,1,"{peso:.3f} kg"',
                'BAR 0,106,500,3',
                # Nueva sección dividida en dos columnas
                # Columna izquierda: Precio total en dólares (letra grande) con BOX
                f'BOX 20,165,230,240,2',
                f'TEXT 30,175,"2",0,1,1,"TOTAL REF"',
                f'TEXT 50,200,"4",0,1,1,"${precio_total_usd:.2f}"',
                
                # Código de barras EAN13 al lado derecho del BOX
                f'BARCODE 250,175,"EAN13",60,0,0,2,2,"{codigo_barras}"',
                
                f"PRINT {copias},1",
            ]
            
            comandos = "\r\n".join(tspl_lines) + "\r\n"

            # Imprimir comandos TSPL por consola para depuración
            print("\n" + "="*50)
            print("COMANDOS TSPL GENERADOS:")
            print("="*50)
            print(comandos)
            print("="*50)
            print(f"Código de barras: {codigo_barras}")
            print(f"Unidad: {unidad} ({'Unitario' if unidad == 'U' else 'Por Kilogramo'})")
            print(f"Peso original: {peso_original:.4f} {'U' if unidad == 'U' else 'kg'}")
            if unidad == 'U':
                print(f"Cantidad truncada: {peso:.0f} U")
            else:
                print(f"Peso truncado: {peso:.3f} kg")
            print(f"Precio unitario USD: {precio_unit_usd:.2f}$/{'U' if unidad == 'U' else 'Kg'}")
            print(f"Precio total USD: {precio_total_usd:.2f}")
            print(f"Moneda original: {moneda}")
            print(f"Fecha: {fecha_actual}")
            print(f"Impresora: {impresora}")
            print("="*50 + "\n")
            
            # Validar que se haya proporcionado una impresora
            if not impresora:
                return JsonResponse({
                    'success': False,
                    'error': 'No se ha seleccionado una impresora de etiquetas. Configure una impresora en el sistema.'
                }, status=400)
            
            # Enviar comando a la impresora
            def enviar():
                conectar_socket_seguro(ip=impresora, puerto=9100, datos=comandos, timeout=3, es_balanza=False)
            
            import threading
            hilo = threading.Thread(target=enviar, daemon=True)
            hilo.start()

            return JsonResponse({
                'success': True,
                'codigo_barras': codigo_barras,
                'precio_total_usd': round(precio_total_usd, 2),
                'fecha': fecha_actual
            })
        except Exception as e:
            return JsonResponse({ 'success': False, 'error': str(e) }, status=500)
    
class Menu(ADMIN_SUPERVISOR_AUTH, LoginRequiredMixin,View):

    def get(self,request,*args, **kwargs):
        context={}
        return render(request, 'menu.html', context)
    
class Ventas(LoginRequiredMixin,View):
    def get_ventas_periodo(self, dias, status_filter=None):
        """Calcular ventas para un período específico de días con filtro de status opcional"""
        from datetime import datetime, timedelta
        from django.utils import timezone
        
        # Calcular fecha de inicio (hace X días)
        fecha_fin = timezone.now().date()
        fecha_inicio = fecha_fin - timedelta(days=dias-1)  # -1 para incluir hoy
        
        # Filtrar pedidos pagados en el período
        if status_filter:
            ventas = Pedido.objects.filter(
                pagado_fecha__date__range=[fecha_inicio, fecha_fin],
                status=status_filter
            )
        else:
            ventas = Pedido.objects.filter(
                pagado_fecha__date__range=[fecha_inicio, fecha_fin],
            status__in=['Pagado', 'Pagado con Crédito']
            )
        
        # Calcular totales
        total_ventas = sum(pedido.precio_total for pedido in ventas if pedido.precio_total)
        cantidad_pedidos = ventas.count()
        promedio_ticket = total_ventas / cantidad_pedidos if cantidad_pedidos > 0 else 0
        
        # Si es crédito, calcular abonos
        total_abonado = 0
        if status_filter == 'Pagado con Crédito':
            # Obtener IDs de pedidos con crédito en el período
            pedidos_ids = [pedido.id for pedido in ventas]
            
            # Calcular total abonado para estos pedidos
            from .models import Credito
            creditos = Credito.objects.filter(pedido_id__in=pedidos_ids)
            total_abonado = sum(credito.abonado for credito in creditos if credito.abonado)
        
        return {
            'total_ventas': round(total_ventas, 2),
            'cantidad_pedidos': cantidad_pedidos,
            'promedio_ticket': round(promedio_ticket, 2),
            'fecha_inicio': fecha_inicio,
            'fecha_fin': fecha_fin,
            'total_abonado': round(total_abonado, 2) if total_abonado > 0 else 0
        }
    
    def get_ventas_hoy(self, status_filter=None):
        """Calcular ventas SOLO del día de hoy con filtro de status opcional"""
        from django.utils import timezone
        
        # Obtener solo la fecha de hoy
        fecha_hoy = timezone.now().date()
        
        # Filtrar pedidos pagados SOLO en el día de hoy
        if status_filter:
            ventas = Pedido.objects.filter(
                pagado_fecha__date=fecha_hoy,  # Solo el día de hoy
                status=status_filter
            )
        else:
            ventas = Pedido.objects.filter(
                pagado_fecha__date=fecha_hoy,  # Solo el día de hoy
                status__in=['Pagado', 'Pagado con Crédito']
            )
        
        # Calcular totales
        total_ventas = sum(pedido.precio_total for pedido in ventas if pedido.precio_total)
        cantidad_pedidos = ventas.count()
        promedio_ticket = total_ventas / cantidad_pedidos if cantidad_pedidos > 0 else 0
        
        return {
            'total_ventas': round(total_ventas, 2),
            'cantidad_pedidos': cantidad_pedidos,
            'promedio_ticket': round(promedio_ticket, 2),
            'fecha_inicio': fecha_hoy,
            'fecha_fin': fecha_hoy
        }
    
    def get(self, request, *args, **kwargs):
        """Vista principal de reportes de ventas"""
        # Calcular ventas totales (ambos tipos)
        ventas_hoy = self.get_ventas_hoy()
        ventas_7_dias = self.get_ventas_periodo(7)
        ventas_30_dias = self.get_ventas_periodo(30)
        
        # Calcular ventas pagadas al contado
        ventas_contado_hoy = self.get_ventas_hoy('Pagado')
        ventas_contado_7_dias = self.get_ventas_periodo(7, 'Pagado')
        ventas_contado_30_dias = self.get_ventas_periodo(30, 'Pagado')
        
        # Calcular ventas pagadas con crédito
        ventas_credito_hoy = self.get_ventas_hoy('Pagado con Crédito')
        ventas_credito_7_dias = self.get_ventas_periodo(7, 'Pagado con Crédito')
        ventas_credito_30_dias = self.get_ventas_periodo(30, 'Pagado con Crédito')
        
        context = {
            # Datos totales
            'ventas_hoy': ventas_hoy,
            'ventas_7_dias': ventas_7_dias,
            'ventas_30_dias': ventas_30_dias,
            
            # Datos pagados al contado
            'ventas_contado_hoy': ventas_contado_hoy,
            'ventas_contado_7_dias': ventas_contado_7_dias,
            'ventas_contado_30_dias': ventas_contado_30_dias,
            
            # Datos pagados con crédito
            'ventas_credito_hoy': ventas_credito_hoy,
            'ventas_credito_7_dias': ventas_credito_7_dias,
            'ventas_credito_30_dias': ventas_credito_30_dias,
        }
        
        return render(request, 'ventas.html', context)

class VentasChartData(LoginRequiredMixin, View):
    """Vista para obtener datos de ventas para los gráficos"""
    
    def get(self, request, *args, **kwargs):
        """Vista GET para probar que la URL funciona"""
        return JsonResponse({'status': 'success', 'message': 'API funcionando correctamente'})
    
    def post(self, request, *args, **kwargs):
        import json
        from datetime import datetime, timedelta
        from django.db.models import Sum
        from django.utils import timezone
        
        try:
            data = json.loads(request.body)
            start_date = datetime.strptime(data.get('start_date'), '%Y-%m-%d').date()
            end_date = datetime.strptime(data.get('end_date'), '%Y-%m-%d').date()
            ventas_type = data.get('type', 'total')
            grouping = data.get('grouping', 'day')
            
            # Filtrar pedidos por fecha y status pagado
            if ventas_type == 'contado':
                pedidos = Pedido.objects.filter(
                    pagado_fecha__date__range=[start_date, end_date],
                    status='Pagado'
                )
            elif ventas_type == 'credito':
                pedidos = Pedido.objects.filter(
                    pagado_fecha__date__range=[start_date, end_date],
                    status='Pagado con Crédito'
                )
            else:  # total
                pedidos = Pedido.objects.filter(
                    pagado_fecha__date__range=[start_date, end_date],
                    status__in=['Pagado', 'Pagado con Crédito']
                )
        
            # Debug: mostrar algunos ejemplos de fechas de pedidos
            print("=== DEBUG: Ejemplos de fechas de pedidos ===")
            for pedido in pedidos[:5]:  # Solo los primeros 5
                print(f"Pedido ID: {pedido.id}, Fecha: {pedido.pagado_fecha}, Hora: {pedido.pagado_fecha.hour}")
            print("=== FIN DEBUG ===")
            
            # Agrupar por fecha y sumar totales según la agrupación seleccionada
            if grouping == 'day':
                ventas_por_fecha = pedidos.values('pagado_fecha__date').annotate(
                    total_ventas=Sum('precio_total')
                ).order_by('pagado_fecha__date')
            elif grouping == 'week':
                ventas_por_fecha = pedidos.extra(
                    select={'semana': "DATE_TRUNC('week', pagado_fecha AT TIME ZONE 'America/Caracas')"}
                ).values('semana').annotate(
                    total_ventas=Sum('precio_total')
                ).order_by('semana')
            elif grouping == 'month':
                ventas_por_fecha = pedidos.extra(
                    select={'mes': "DATE_TRUNC('month', pagado_fecha AT TIME ZONE 'America/Caracas')"}
                ).values('mes').annotate(
                    total_ventas=Sum('precio_total')
                ).order_by('mes')
            
            # Agrupar por hora y calcular totales y cantidad
            from django.db.models import Count
            ventas_por_hora = pedidos.extra(
                select={'hora': "EXTRACT(hour FROM pagado_fecha AT TIME ZONE 'America/Caracas')"}
            ).values('hora').annotate(
                total_ventas=Sum('precio_total'),
                cantidad_pedidos=Count('id')
            ).order_by('hora')
            
            # Convertir a formato JSON
            chart_data = {
                'ventas_por_fecha': [],
                'ventas_por_hora': []
            }
            
            for venta in ventas_por_fecha:
                if grouping == 'day':
                    fecha = venta['pagado_fecha__date'].isoformat()
                elif grouping == 'week':
                    fecha = venta['semana'].isoformat()
                elif grouping == 'month':
                    fecha = venta['mes'].isoformat()
                
                chart_data['ventas_por_fecha'].append({
                    'fecha': fecha,
                    'total_ventas': float(venta['total_ventas'])
                })
            
            # Debug: imprimir los datos de ventas por hora
            print("=== DEBUG: Datos de ventas por hora ===")
            for venta in ventas_por_hora:
                print(f"Hora: {venta['hora']}, Ventas: {venta['total_ventas']}, Pedidos: {venta['cantidad_pedidos']}")
                chart_data['ventas_por_hora'].append({
                    'hora': int(venta['hora']),
                    'total_ventas': float(venta['total_ventas']),
                    'cantidad_pedidos': int(venta['cantidad_pedidos'])
                })
            print("=== FIN DEBUG ===")
            
            return JsonResponse(chart_data, safe=False)
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

class VentasPorTiempo(ADMIN_AUTH,LoginRequiredMixin,View):
    def post(self,request,*args, **kwargs):
        return JsonResponse({})

class ProductosMasVendidosData(LoginRequiredMixin, View):
    """Vista para obtener datos de productos más vendidos"""
    
    def post(self, request, *args, **kwargs):
        import json
        from datetime import datetime, timedelta
        from django.db.models import Sum, Count, Q, Case, When, F
        from django.utils import timezone
        
        try:
            data = json.loads(request.body)
            start_date = datetime.strptime(data.get('start_date'), '%Y-%m-%d').date()
            end_date = datetime.strptime(data.get('end_date'), '%Y-%m-%d').date()
            tipo_analisis = data.get('tipo', 'cantidad')  # cantidad o valor
            unidad_filtro = data.get('unidad', 'todas')  # U, K, o todas
            limit = data.get('limit', 10)
            
            # Filtrar pedidos pagados en el período
            pedidos = Pedido.objects.filter(
                pagado_fecha__date__range=[start_date, end_date],
                status__in=['Pagado', 'Pagado con Crédito']
            )
            
            # Obtener todos los productos de pedidos en el período
            productos_pedido = ProductosPedido.objects.filter(
                pedido__in=pedidos
            )
            
            # Aplicar filtro de unidad si se especifica
            if unidad_filtro != 'todas':
                productos_pedido = productos_pedido.filter(unidad=unidad_filtro)
            
            # Agrupar por producto y calcular métricas
            if tipo_analisis == 'cantidad':
                # Análisis por cantidad vendida
                productos_agrupados = productos_pedido.values(
                    'producto', 'producto_nombre', 'unidad', 'moneda'
                ).annotate(
                    cantidad_total=Sum('cantidad'),
                    veces_vendido=Count('id')
                ).order_by('-cantidad_total')[:limit]
                
                # Función para formatear números con separador de miles
                def format_number(number, decimals=0):
                    if number is None:
                        return "0"
                    formatted = f"{number:,.{decimals}f}"
                    return formatted.replace(",", ".")
                
                # Preparar datos para el gráfico
                chart_data = []
                for producto in productos_agrupados:
                    chart_data.append({
                        'producto': producto['producto_nombre'],
                        'cantidad': round(producto['cantidad_total'], 2),
                        'cantidad_formatted': format_number(producto['cantidad_total'], 2),
                        'unidad': producto['unidad'],
                        'veces_vendido': producto['veces_vendido'],
                        'veces_vendido_formatted': format_number(producto['veces_vendido']),
                        'moneda': producto['moneda']
                    })
                    
            else:  # tipo_analisis == 'valor'
                # Análisis por valor vendido
                productos_agrupados = productos_pedido.values(
                    'producto', 'producto_nombre', 'unidad', 'moneda'
                ).annotate(
                    valor_total_usd=Sum(
                        Case(
                            When(moneda='USD', then=F('precio') * F('cantidad')),
                            default=F('precio') * F('cantidad') / 120  # Tasa aproximada
                        )
                    ),
                    valor_total_bs=Sum(
                        Case(
                            When(moneda='BS', then=F('precio') * F('cantidad')),
                            default=F('precio') * F('cantidad') * 120  # Tasa aproximada
                        )
                    ),
                    cantidad_total=Sum('cantidad'),
                    veces_vendido=Count('id')
                ).order_by('-valor_total_usd')[:limit]
                
                # Función para formatear números con separador de miles
                def format_number(number, decimals=0):
                    if number is None:
                        return "0"
                    formatted = f"{number:,.{decimals}f}"
                    return formatted.replace(",", ".")
                
                # Preparar datos para el gráfico
                chart_data = []
                for producto in productos_agrupados:
                    chart_data.append({
                        'producto': producto['producto_nombre'],
                        'valor_usd': round(producto['valor_total_usd'] or 0, 2),
                        'valor_usd_formatted': format_number(producto['valor_total_usd'] or 0, 2),
                        'valor_bs': round(producto['valor_total_bs'] or 0, 2),
                        'valor_bs_formatted': format_number(producto['valor_total_bs'] or 0, 2),
                        'cantidad': round(producto['cantidad_total'], 2),
                        'cantidad_formatted': format_number(producto['cantidad_total'], 2),
                        'unidad': producto['unidad'],
                        'veces_vendido': producto['veces_vendido'],
                        'veces_vendido_formatted': format_number(producto['veces_vendido']),
                        'moneda': producto['moneda']
                    })
            
            return JsonResponse({
                'success': True,
                'data': chart_data,
                'periodo': {
                    'inicio': start_date.strftime('%d/%m/%Y'),
                    'fin': end_date.strftime('%d/%m/%Y')
                },
                'tipo_analisis': tipo_analisis,
                'unidad_filtro': unidad_filtro
            })
            
        except Exception as e:
            print(f"Error en ProductosMasVendidosData: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=400)


class ProductosSugeridosView(LoginRequiredMixin, View):
    """Vista para obtener productos sugeridos (más vendidos) para el buscador"""
    
    def get(self, request, *args, **kwargs):
        from datetime import datetime, timedelta
        from django.db.models import Sum, Count
        from django.utils import timezone
        
        try:
            # Obtener los 8 productos más vendidos en cantidad (últimos 90 días)
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=90)
            
            # Filtrar pedidos pagados en el período
            pedidos = Pedido.objects.filter(
                pagado_fecha__date__range=[start_date, end_date],
                status__in=['Pagado', 'Pagado con Crédito']
            )
            
            # Obtener productos más vendidos
            productos_sugeridos = ProductosPedido.objects.filter(
                pedido__in=pedidos
            ).values(
                'producto', 'producto_nombre', 'unidad'
            ).annotate(
                total_cantidad=Sum('cantidad')
            ).order_by('-total_cantidad')[:8]
            
            # Función para formatear números con separador de miles
            def format_number(number, decimals=0):
                if number is None:
                    return "0"
                formatted = f"{number:,.{decimals}f}"
                return formatted.replace(",", ".")
            
            # Formatear datos para la respuesta
            formatted_data = []
            for producto in productos_sugeridos:
                formatted_data.append({
                    'id': producto['producto'],
                    'nombre': producto['producto_nombre'],
                    'unidad': producto['unidad'],
                    'cantidad_total': format_number(producto['total_cantidad'], 2)
                })
            
            return JsonResponse({
                'success': True,
                'data': formatted_data
            })
            
        except Exception as e:
            print(f"Error en ProductosSugeridosView: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=400)


class MovimientosProductoData(LoginRequiredMixin, View):
    """Vista para obtener datos de movimientos de un producto específico"""
    
    def post(self, request, *args, **kwargs):
        import json
        from datetime import datetime, timedelta
        from django.db.models import Sum, Count, Q
        from django.utils import timezone
        
        try:
            print(f"📥 Datos recibidos en MovimientosProductoData: {request.body}")
            data = json.loads(request.body)
            print(f"📋 Datos parseados: {data}")
            
            # Validar que los datos requeridos estén presentes
            if not data.get('start_date') or not data.get('end_date') or not data.get('producto_id'):
                print(f"❌ Datos faltantes: start_date={data.get('start_date')}, end_date={data.get('end_date')}, producto_id={data.get('producto_id')}")
                return JsonResponse({
                    'success': False,
                    'error': 'Faltan datos requeridos: start_date, end_date, producto_id'
                }, status=400)
            
            try:
                start_date = datetime.strptime(data.get('start_date'), '%Y-%m-%d').date()
                end_date = datetime.strptime(data.get('end_date'), '%Y-%m-%d').date()
            except ValueError as e:
                return JsonResponse({
                    'success': False,
                    'error': f'Formato de fecha inválido: {str(e)}'
                }, status=400)
            
            producto_id = data.get('producto_id')
            
            # Convertir producto_id a entero si es necesario
            try:
                producto_id = int(producto_id)
            except (ValueError, TypeError):
                return JsonResponse({
                    'success': False,
                    'error': 'ID de producto inválido'
                }, status=400)
            
            if not producto_id:
                return JsonResponse({
                    'success': False,
                    'error': 'Se requiere especificar un producto'
                }, status=400)
            
            # Verificar que el producto existe en ProductosPedido
            try:
                print(f"🔍 Buscando producto con ID: {producto_id}")
                producto_info = ProductosPedido.objects.filter(producto=producto_id).first()
                print(f"📦 Producto encontrado: {producto_info}")
                if not producto_info:
                    print(f"❌ Producto no encontrado para ID: {producto_id}")
                    return JsonResponse({
                        'success': False,
                        'error': 'Producto no encontrado'
                    }, status=400)
            except Exception as e:
                print(f"❌ Error al verificar el producto: {str(e)}")
                return JsonResponse({
                    'success': False,
                    'error': 'Error al verificar el producto'
                }, status=400)
            
            # Filtrar pedidos pagados en el período
            pedidos = Pedido.objects.filter(
                pagado_fecha__date__range=[start_date, end_date],
                status__in=['Pagado', 'Pagado con Crédito']
            )
            
            # Obtener movimientos del producto específico
            movimientos = ProductosPedido.objects.filter(
                pedido__in=pedidos,
                producto=producto_id
            )
            
            # Calcular totales
            total_cantidad = movimientos.aggregate(
                total=Sum('cantidad')
            )['total'] or 0
            
            total_pedidos = movimientos.aggregate(
                total=Count('pedido', distinct=True)
            )['total'] or 0
            
            # Obtener movimientos por día para el gráfico
            movimientos_por_dia = movimientos.values(
                'pedido__pagado_fecha__date'
            ).annotate(
                cantidad_dia=Sum('cantidad'),
                pedidos_dia=Count('pedido', distinct=True)
            ).order_by('pedido__pagado_fecha__date')
            
            # Función para formatear números con separador de miles
            def format_number(number, decimals=0):
                if number is None:
                    return "0"
                formatted = f"{number:,.{decimals}f}"
                return formatted.replace(",", ".")
            
            # Preparar datos para el gráfico
            chart_data = []
            for movimiento in movimientos_por_dia:
                chart_data.append({
                    'fecha': movimiento['pedido__pagado_fecha__date'].strftime('%d/%m/%Y'),
                    'cantidad': round(movimiento['cantidad_dia'], 2),
                    'cantidad_formatted': format_number(movimiento['cantidad_dia'], 2),
                    'pedidos': movimiento['pedidos_dia'],
                    'pedidos_formatted': format_number(movimiento['pedidos_dia'])
                })
            
            return JsonResponse({
                'success': True,
                'data': chart_data,
                'resumen': {
                    'producto_nombre': producto_info.producto_nombre,
                    'producto_unidad': producto_info.unidad,
                    'total_cantidad': round(total_cantidad, 2),
                    'total_cantidad_formatted': format_number(total_cantidad, 2),
                    'total_pedidos': total_pedidos,
                    'total_pedidos_formatted': format_number(total_pedidos),
                    'promedio_por_pedido': round(total_cantidad / total_pedidos, 2) if total_pedidos > 0 else 0,
                    'promedio_por_pedido_formatted': format_number(total_cantidad / total_pedidos, 2) if total_pedidos > 0 else "0"
                },
                'periodo': {
                    'inicio': start_date.strftime('%d/%m/%Y'),
                    'fin': end_date.strftime('%d/%m/%Y')
                }
            })
            
        except Exception as e:
            print(f"Error en MovimientosProductoData: {str(e)}")
            import traceback
            print(f"Traceback completo: {traceback.format_exc()}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=400)
    
class Productos(LoginRequiredMixin, ListView):
    model = Producto
    context_object_name = 'productos'

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super().get_context_data(**kwargs)
        # Add in a QuerySet of all the books
        productos = Producto.objects.all().order_by('nombre')
        
        # Formatear cantidad con 2 decimales
        for producto in productos:
            if producto.cantidad is not None:
                producto.cantidad_formateada = "{:.2f}".format(float(producto.cantidad))
            else:
                producto.cantidad_formateada = None
        
        context["productos_list"] = productos
        return context

class ProductoCreateView(LoginRequiredMixin, CreateView):
    model = Producto
    template_name = 'pos/createproducto_form.html'
    form_class = ProductoForm
    success_url = reverse_lazy('pos:productos')
    
class ProductoUpdateView(LoginRequiredMixin, UpdateView):
    model = Producto
    form_class = ProductoForm
    template_name = 'pos/updateproducto_form.html'
    success_url = reverse_lazy('pos:productos')

    def get_object(self, queryset=None):
        return get_object_or_404(Producto, pk=self.kwargs.get('pk'))

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['categoria'].queryset = CategoriasProductos.objects.all()
        return form

class ProductoAumentarCantidad(ADMIN_AUTH,LoginRequiredMixin, View):
    def get(self,request,*args, **kwargs):
        producto_id = kwargs['pk']
        producto = Producto.objects.get(pk=producto_id)
        context = {
            'producto':producto,
        }
        return render(request,'producto_cantidad.html',context)
    def post(self,request,*args, **kwargs):
        data = request.POST

        producto = Producto.objects.get(pk=data['id'])
        producto.cantidad = producto.cantidad + float(data['cantidad'])
        producto.save()
        context = {
            'producto':producto,
        }
        return render(request,'producto_cantidad.html',context)

class ProductoDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        producto = Producto.objects.get(pk=pk)
        producto.delete()
        return redirect('pos:productos')

class UsuariosMenu(ADMIN_AUTH,LoginRequiredMixin,ListView):
    model = User
    context_object_name = 'user'

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super().get_context_data(**kwargs)
        # Add in a QuerySet of all the books
        context["user_list"] = User.objects.all()
        return context

class Dolar(LoginRequiredMixin, View):
    """
    Vista para manejar el valor del dólar.
    Permite crear el primer registro si no existe o actualizar el existente.
    """
    
    def get(self, request, pk=None):
        """
        Mostrar el formulario para crear o editar el valor del dólar
        """
        try:
            # Intentar obtener el registro existente
            dolar = ValorDolar.objects.get(pk=1)
            form = ValorDolarForm(instance=dolar)
            es_creacion = False
        except ValorDolar.DoesNotExist:
            # Si no existe, preparar formulario para creación
            form = ValorDolarForm()
            es_creacion = True
            dolar = None
        
        context = {
            'form': form,
            'object': dolar,
            'es_creacion': es_creacion,
            'mostrar_popup': request.GET.get('guardado') == 'success'
        }
        
        return render(request, 'pos/valordolar_form.html', context)
    
    def post(self, request, pk=None):
        """
        Procesar el formulario para crear o actualizar el valor del dólar
        """
        try:
            # Intentar obtener el registro existente
            dolar = ValorDolar.objects.get(pk=1)
            form = ValorDolarForm(request.POST, instance=dolar)
            es_actualizacion = True
        except ValorDolar.DoesNotExist:
            # Si no existe, crear nuevo registro
            form = ValorDolarForm(request.POST)
            es_actualizacion = False
        
        if form.is_valid():
            dolar_obj = form.save(commit=False)
            if not es_actualizacion:
                # Para nuevo registro, asegurar que tenga pk=1
                dolar_obj.pk = 1
            dolar_obj.save()
            
            # Redirigir con mensaje de éxito
            return redirect(reverse('pos:dolar', kwargs={'pk': 1}) + '?guardado=success')
        
        # Si hay errores, mostrar el formulario con errores
        context = {
            'form': form,
            'object': dolar_obj if 'dolar_obj' in locals() else None,
            'es_creacion': not es_actualizacion,
        }
        
        return render(request, 'pos/valordolar_form.html', context)

class CategoriasList(LoginRequiredMixin, ListView):
    model = CategoriasProductos
    context_object_name = 'categorias'

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super().get_context_data(**kwargs)
        # Add in a QuerySet of all the books
        context["categorias_list"] = CategoriasProductos.objects.all().order_by('orden')
        return context

class CategoriaCreateView(LoginRequiredMixin,CreateView):
    model = CategoriasProductos
    form_class = CategoriaForm
    template_name = 'pos/create_categoria.html'
    success_url = reverse_lazy('pos:categorias')

class CategoriaUpdateView(LoginRequiredMixin,UpdateView):
    model = CategoriasProductos
    form_class = CategoriaForm
    template_name = 'pos/create_categoria.html'
    success_url = reverse_lazy('pos:categorias') 
    

class CategoriaDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        categoria = CategoriasProductos.objects.get(pk=pk)
        categoria.delete()
        return redirect('pos:categorias')
    
class CrearUsuarioView(LoginRequiredMixin,CreateView):
    model = User
    form_class = CustomUserCreationForm
    template_name = 'users/create_user.html'
    success_url = reverse_lazy('pos:usuarios')  # Cambia esto a la URL deseada

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['groups'] = Group.objects.all()
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        group_name = self.request.POST.get('group')
        if group_name:
            group = Group.objects.get(name=group_name)
            self.object.groups.add(group)
        return response
    
class ModificarUsuarioView(LoginRequiredMixin,UpdateView):
    model = User
    form_class = ModificarUsuarioForm
    template_name = 'users/edit_user.html'
    success_url = reverse_lazy('pos:usuarios')  # Cambia esto a la URL deseada

class DeleteUsuarioView(LoginRequiredMixin, View):
    def post(self, request, pk):
        user = User.objects.get(pk=pk)
        user.delete()
        return redirect('pos:usuarios')

class AdminChangePasswordView(LoginRequiredMixin,PasswordChangeView):
    template_name = 'users/change_password.html'  # Reemplaza con tu plantilla personalizada
    form_class = SetPasswordForm

    def get_success_url(self):
        return reverse_lazy('pos:usuarios')

    def form_valid(self, form):
        user_id = self.kwargs['pk']  # Obtener el ID del usuario al que se cambiará la contraseña
        user = User.objects.get(pk=user_id)
        user.set_password(form.cleaned_data['new_password1'])
        user.save()
        return redirect(self.get_success_url())

class CierreCaja(LoginRequiredMixin,View):
    def post(self,request,*args, **kwargs):
        total = request.POST['total_real']
        usuario = request.POST['usuario']

        cierre = CierresDiarios(total=total,usuario=usuario)
        cierre.save()
        
        return HttpResponse(200)
    
class PedidosListMenu(LoginRequiredMixin, ListView):
    model = Pedido
    context_object_name = 'pedido'
    template_name = 'pos/pedidos_list.html'
    
    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super().get_context_data(**kwargs)
        # Obtener todos los pedidos, ordenados por fecha descendente (limitados a 3000)
        context["pedidos_list"] = Pedido.objects.all().order_by('-fecha')[:3000]
        # Añadir clientes para mostrar nombres en vez de IDs
        context["clientes"] = Cliente.objects.all()
        # Añadir usuarios para el filtro de cajeros
        context["users"] = User.objects.all()
        # Obtener lista única de pesadores para el filtro
        pesadores = Pedido.objects.exclude(pesador__isnull=True).exclude(pesador='').values_list('pesador', flat=True).distinct().order_by('pesador')
        context["pesadores"] = pesadores
        # Contar el total de pedidos
        context["total_pedidos"] = Pedido.objects.count()
        # Verificar si se limitaron los resultados
        context["resultados_limitados"] = context["total_pedidos"] > 3000
        return context

class DeletePedidoView(LoginRequiredMixin, View):
    def post(self, request, pk):
        try:
            codigo = request.POST.get('codigo')
            
            # Verificar que se proporcione el código
            if not codigo:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Se requiere código de autorización para cancelar pedidos'
                })
            
            # Obtener el pedido
            pedido = Pedido.objects.get(pk=pk)
            
            # Verificar autorización usando el mismo patrón que ValidarAutorizacionCredito
            from django.contrib.auth.hashers import check_password
            autorizado = False
            
            # Buscar usuarios que sean supervisores o administradores
            usuarios_autorizados = User.objects.filter(
                groups__name__in=['SUPERVISOR', 'ADMINISTRADOR']
            )
            
            # Verificar el código contra las contraseñas de usuarios autorizados
            for usuario in usuarios_autorizados:
                if check_password(codigo, usuario.password):
                    autorizado = True
                    break
            
            if not autorizado:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Código de autorización incorrecto'
                })
            
            # Cambiar estado a "Cancelado" en lugar de eliminar
            pedido.status = "Cancelado"
            pedido.save()
            
            return JsonResponse({
                'status': 'success',
                'message': f'Pedido #{pk} cancelado exitosamente'
            })
            
        except Pedido.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'El pedido no existe'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'Error interno: {str(e)}'
            }, status=500)

class MarcarInjustificado(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        try:
            pedido_id = request.POST.get('pedido_id')
            codigo = request.POST.get('codigo')
            
            # Verificar que se proporcionen todos los datos
            if not pedido_id or not codigo:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Faltan datos para la autorización'
                })
            
            # Obtener el pedido
            pedido = Pedido.objects.get(pk=pedido_id)
            
            # Verificar autorización usando el mismo patrón que ValidarAutorizacionCredito
            from django.contrib.auth.hashers import check_password
            autorizado = False
            
            # Buscar usuarios que sean supervisores o administradores
            usuarios_autorizados = User.objects.filter(
                groups__name__in=['SUPERVISOR', 'ADMINISTRADOR']
            )
            
            # Verificar el código contra las contraseñas de usuarios autorizados
            for usuario in usuarios_autorizados:
                if check_password(codigo, usuario.password):
                    autorizado = True
                    break
            
            if not autorizado:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Código de autorización incorrecto'
                })
            
            # Marcar como injustificado
            pedido.status = "Injustificado"
            pedido.save()
            
            return JsonResponse({
                'status': 'success',
                'message': f'Pedido #{pedido_id} marcado como injustificado exitosamente'
            })
            
        except Pedido.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'El pedido no existe'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'Error interno: {str(e)}'
            }, status=500)
    
class AdminImpresora(LoginRequiredMixin, View):
    def get(self,request,*args, **kwargs):
        context={'IMPRESORAS':IMPRESORAS.items()}
        return render(request, 'menu_impresora.html', context)

class AdminBalanza(LoginRequiredMixin, View):
    def get(self,request,*args, **kwargs):
        context={'BALANZAS':BALANZAS.items()}
        return render(request, 'menu_balanza.html', context)
    
class BalanzaImpresoraIp(ADMIN_SUPERVISOR_AUTH, LoginRequiredMixin,View):
    def get(self,request,*args, **kwargs):
        context={'BALANZAS':BALANZAS.items(), 'IMPRESORAS':IMPRESORAS.items()}
        return render(request, 'menu_balanzas_impresoras.html', context)
    
    def post(self,request,*args, **kwargs):
        balanza_id = request.POST['balanza']
        impresora_ip = request.POST['impresora']
        balanza = BalanzasImpresoras.objects.get_or_create(balanza_id=balanza_id, defaults={'impresora_ip':impresora_ip})[0]
        balanza.impresora_ip = impresora_ip
        balanza.save()
        return HttpResponse(200)
    
class BuscarCliente(LoginRequiredMixin,View):
    def post(self,request,*args, **kwargs):
        cedula = request.POST['cedula']
        if cedula == '*':
            clientes = Cliente.objects.filter()[:300]
            
        else:
            clientes = Cliente.objects.filter(cedula=cedula)
            
        clientes_arr = []

        for cliente in clientes:
            # Calcular la deuda total del cliente
            creditos = Credito.objects.filter(cliente_id=cliente.cedula)
            abonos_totales = sum(CreditoAbono.objects.filter(credito_id__in=creditos.values_list('id', flat=True)).values_list('monto', flat=True))
            deuda_total = sum(creditos.values_list('monto_credito', flat=True)) - abonos_totales
            deuda_total = round(deuda_total, 2)
            
            # Calcular el crédito disponible como crédito máximo - deuda total
            credito_disponible = cliente.credito_maximo - deuda_total
            credito_disponible = max(0, round(credito_disponible, 2))  # Asegurar que no sea negativo

            cliente_dict = {
                'id': cliente.pk,
                'nombre': cliente.nombre,
                'cedula': cliente.cedula,
                'telefono': cliente.telefono,
                'zona': cliente.zona_vive,
                'credito': credito_disponible,  # Ahora credito es el crédito disponible calculado
                'deuda_total': deuda_total
            }
            clientes_arr.append(cliente_dict)
        
        return JsonResponse(clientes_arr, safe=False)
    
class ProductosEnBalanzas(View):
    def get(self,request,*args, **kwargs):
        ProductosB = ProductosBalanzas.objects.all()
        productosB_array = []
        for x in ProductosB:
            producto = Producto.objects.get(pk=x.producto).nombre
            numeroEnB = {
                'numero':x.numero,
                'producto':producto,
            }
            productosB_array.append(numeroEnB)
        productosB_json = json.dumps(productosB_array)

        productos = Producto.objects.all().order_by('nombre')
        productos_arr = []
        for x in productos:
            producto = {
                'id':x.id, 
                'nombre':x.nombre,
            }
            productos_arr.append(producto)
        productosjson = json.dumps(productos_arr)
        context={
            'numerosBalanza':productosB_json,
            'productos':productosjson,
        }
        return render(request, 'menu_productos_balanzas.html',context)
    
    def post(self,request,*args, **kwargs):
        numBalanza = int(request.POST['numBalanza'])
        p_id = request.POST['product_id']

        numeroEnBalanza = ProductosBalanzas.objects.get(numero=numBalanza)
        numeroEnBalanza.producto = p_id
        numeroEnBalanza.save()
        url = reverse('pos:menu-balanza',)
        return HttpResponse(url, content_type='text/plain')
    
class VolverPOS(View):
    def post(self,request,*args, **kwargs):
        id = request.POST['pedido_id']
        if(id == '/'):
            url = reverse('pos:pos',)
        else:
            url = reverse('pos:posPedido', args=[id])        
        return HttpResponse(url, content_type='text/plain')
    
class BuscarPedidoPos(View):
    def post(self,request,*args, **kwargs):
        id = request.POST['id']
        
        # 🎯 FILTRO PARA PESADORES: Solo buscar en sus propios pedidos
        user_groups = [group.name for group in request.user.groups.all()]
        
        try:
            if 'PESADOR' in user_groups:
                # Si es PESADOR: Solo buscar pedidos donde él es el pesador
                pedido = Pedido.objects.get(id=id, pesador=request.user.username)
            else:
                # Si es CAJERO/ADMIN: Buscar cualquier pedido (comportamiento original)
                pedido = Pedido.objects.get(id=id)
                
            pedido_arr = {
                'id':pedido.id,
                'fecha':pedido.fecha,
                'cliente':pedido.cliente,
                'cajero':pedido.usuario,
                'pesador':pedido.pesador or "-",  # 🎯 NUEVO: Campo pesador para búsqueda
                'total':pedido.precio_total,
                'estado':pedido.status,
            }
            return JsonResponse(pedido_arr, content_type='text/plain')
            
        except Pedido.DoesNotExist:
            # Si no encuentra el pedido (o no tiene permisos), devolver error
            return JsonResponse({'error': 'Pedido no encontrado o sin permisos'}, status=404)
    

class BuscarProductoNombreMenu(View):
    def post(self,request,*args, **kwargs):
        buscar = request.POST['buscar']
        productos_arr = []

        if buscar == '':
            productos = Producto.objects.filter().order_by('nombre')
        else:
            if buscar.isnumeric(): productos = Producto.objects.filter(id=buscar).order_by('nombre')
            else: productos = Producto.objects.filter(nombre__icontains=buscar).order_by('nombre')

        for producto in productos:
            # Obtener las categorías del producto
            categorias_list = []
            for categoria in producto.categoria.all():
                categorias_list.append({
                    'id': categoria.id,
                    'nombre': categoria.nombre
                })
            
            producto_arr = {
                'id':producto.id,
                'nombre':producto.nombre,
                'cantidad':producto.cantidad,
                'unidad':producto.unidad,
                'moneda':producto.moneda,
                'costo':producto.costo,
                'precio_detal':producto.precio_detal,
                'precio_mayor':producto.precio_mayor,
                'categorias': categorias_list,
            }
            productos_arr.append(producto_arr)

        return JsonResponse(productos_arr, content_type='text/plain',safe=False)
    

class ClienteList(LoginRequiredMixin, ListView):
    model = Cliente
    context_object_name = 'cliente'

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super().get_context_data(**kwargs)
        
        # Calcular el crédito disponible para cada cliente como crédito_máximo - deuda_total
        clientes = context['cliente']
        for cliente in clientes:
            # Calcular la deuda total del cliente
            creditos = Credito.objects.filter(cliente_id=cliente.cedula)
            abonos_totales = sum(CreditoAbono.objects.filter(credito_id__in=creditos.values_list('id', flat=True)).values_list('monto', flat=True))
            deuda_total = sum(creditos.values_list('monto_credito', flat=True)) - abonos_totales
            deuda_total = round(deuda_total, 2)
            
            # Calcular el crédito disponible como crédito máximo - deuda total
            credito_disponible = cliente.credito_maximo - deuda_total
            credito_disponible = max(0, round(credito_disponible, 2))  # Asegurar que no sea negativo
            
            # Asignar el valor calculado al cliente (solo para la vista)
            cliente.credito = credito_disponible
            cliente.deuda_total = deuda_total
        
        return context

class ClienteCreateView(LoginRequiredMixin,CreateView):
    model = Cliente
    template_name = 'pos/create_cliente.html'
    fields = ['nombre','cedula','telefono', 'zona_vive','credito_maximo','credito_plazo']
    def form_valid(self, form):
        # Establece el valor de 'campo2' tomando el valor de 'campo1'
        form.instance.credito = form.instance.credito_maximo # Ejemplo de manipulación
        return super().form_valid(form)
    success_url = reverse_lazy('pos:cliente') 

class ClienteUpdateView(LoginRequiredMixin,UpdateView):
    model = Cliente
    template_name = 'pos/create_cliente.html'
    fields = ['nombre','cedula','telefono', 'zona_vive','credito_maximo','credito_plazo']
    success_url = reverse_lazy('pos:cliente') 

class ClienteDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        cliente = Cliente.objects.get(pk=pk)
        cliente.delete()
        return redirect('pos:cliente')
    

class BuscarClienteCedulaMenu(View):
    def post(self,request,*args, **kwargs):
        cedula = request.POST['cedula']
        clientes_arr = []

        if cedula == '':
            clientes = Cliente.objects.filter()
        else:
            clientes = Cliente.objects.filter(cedula=cedula)

        for cliente in clientes:
            # Calcular la deuda total del cliente
            creditos = Credito.objects.filter(cliente_id=cliente.cedula)
            abonos_totales = sum(CreditoAbono.objects.filter(credito_id__in=creditos.values_list('id', flat=True)).values_list('monto', flat=True))
            deuda_total = sum(creditos.values_list('monto_credito', flat=True)) - abonos_totales
            deuda_total = round(deuda_total, 2)
            
            # Calcular el crédito disponible como crédito máximo - deuda total
            credito_disponible = cliente.credito_maximo - deuda_total
            credito_disponible = max(0, round(credito_disponible, 2))  # Asegurar que no sea negativo
            
            cliente_arr = {
                'id':cliente.id,
                'nombre':cliente.nombre,
                'cedula':cliente.cedula,
                'telefono':cliente.telefono,
                'zona_vive':cliente.zona_vive,
                'credito':credito_disponible,
                'credito_maximo':cliente.credito_maximo,
                'deuda_total':deuda_total
            }
            clientes_arr.append(cliente_arr)

        return JsonResponse(clientes_arr, content_type='text/plain',safe=False)
    
class ConexionBalanza(View):
    def post(self,request,*args, **kwargs):
        codigo = request.POST['codigo']
        balanza_ip = request.POST['balanza']
        
        # Usar la nueva función helper con timeout optimizado para balanzas
        success, respuesta, error_msg = conectar_socket_seguro(
            ip=balanza_ip, 
            puerto=8000, 
            datos=codigo, 
            timeout=3,  # Timeout aumentado de 2 a 4 segundos
            es_balanza=True
        )
        
        if not success:
            return HttpResponse("error", 200)
        
        print(f"Respuesta de balanza {balanza_ip}: {respuesta}")
        
        # Validar respuesta - mejorada para manejar diferentes formatos
        if not respuesta:
            print(f"ERROR: Respuesta vacía de balanza {balanza_ip}")
            return HttpResponse(0, 200)
        
        # Limpiar caracteres especiales de la respuesta
        respuesta_limpia = respuesta.strip()
        
        # Si la respuesta es "Ok", devolverla tal cual
        if respuesta_limpia == "Ok":
            return HttpResponse(respuesta_limpia, 200)
        
        # Validar longitud mínima para datos de peso
        if len(respuesta_limpia) < 5:
            print(f"ERROR: Respuesta muy corta de balanza {balanza_ip}: '{respuesta_limpia}' (longitud {len(respuesta_limpia)})")
            return HttpResponse(0, 200)
        
        # Procesar respuesta de peso - mejorado para manejar diferentes formatos
        try:
            # Intentar extraer peso de diferentes formatos posibles
            if len(respuesta_limpia) >= 6:
                # Formato original: ☻00102 -> 001.02
                respuesta_str = str(respuesta_limpia[1]) + str(respuesta_limpia[2])+ "." + str(respuesta_limpia[3]) + str(respuesta_limpia[4]) + str(respuesta_limpia[5])
            else:
                # Formato alternativo: 00102 -> 001.02
                respuesta_str = str(respuesta_limpia[0]) + str(respuesta_limpia[1])+ "." + str(respuesta_limpia[2]) + str(respuesta_limpia[3]) + str(respuesta_limpia[4])
            
            respuesta_float = float(respuesta_str)
            
            # Validar que el peso sea razonable (entre 0 y 50kg)
            if 0 <= respuesta_float <=1000.0:
                print(respuesta_float)
                return HttpResponse(respuesta_float,200)
            else:
                print(f"ERROR: Peso fuera de rango válido de balanza {balanza_ip}: {respuesta_float}kg")
                return HttpResponse(0, 200)
                
        except (ValueError, IndexError) as e:
            print(f"ERROR: Error procesando peso de balanza {balanza_ip}: '{respuesta_limpia}' - {e}")
            return HttpResponse(0, 200)

class ConexionBalanzaAsync(View):
    """Vista asíncrona para comunicación con balanzas"""
    
    async def post(self, request, *args, **kwargs):
        codigo = request.POST['codigo']
        balanza_ip = request.POST['balanza']
        
        print(f"🏗️ Iniciando conexión asíncrona a balanza {balanza_ip}")
        
        # Usar conexión socket asíncrona
        success, respuesta, error_msg = await conectar_socket_async(
            ip=balanza_ip, 
            puerto=8000, 
            datos=codigo, 
            timeout=3,
            es_balanza=True
        )
        
        if not success:
            print(f"❌ Error conectando a balanza: {error_msg}")
            return HttpResponse("error", 200)
        
        print(f"📊 Respuesta de balanza {balanza_ip}: {respuesta}")
        
        # Validar y procesar respuesta
        if not respuesta:
            print(f"⚠️ Respuesta vacía de balanza {balanza_ip}")
            return HttpResponse(0, 200)
        
        respuesta_limpia = respuesta.strip()
        
        # Manejar comando "Ok"
        if respuesta_limpia == "Ok":
            return HttpResponse(respuesta_limpia, 200)
        
        # Validar longitud para datos de peso
        if len(respuesta_limpia) < 5:
            print(f"⚠️ Respuesta muy corta: '{respuesta_limpia}'")
            return HttpResponse(0, 200)
        
        # Procesar datos de peso
        try:
            if len(respuesta_limpia) >= 6:
                peso_str = f"{respuesta_limpia[1]}{respuesta_limpia[2]}{respuesta_limpia[3]}.{respuesta_limpia[4]}{respuesta_limpia[5]}"
            else:
                peso_str = f"{respuesta_limpia[0]}{respuesta_limpia[1]}{respuesta_limpia[2]}.{respuesta_limpia[3]}{respuesta_limpia[4]}"
            
            peso_float = float(peso_str)
            
            # Validar rango de peso
            if 0 <= peso_float <= 50.0:
                print(f"✅ Peso válido: {peso_float}kg")
                return HttpResponse(peso_float, 200)
            else:
                print(f"⚠️ Peso fuera de rango: {peso_float}kg")
                return HttpResponse(0, 200)
                
        except (ValueError, IndexError) as e:
            print(f"❌ Error procesando peso: '{respuesta_limpia}' - {e}")
            return HttpResponse(0, 200)
    
class Creditos(ADMIN_AUTH,View):
    def get(self,request,*args, **kwargs):
        return render(request,'pos/creditos.html')
    
    def post(self,request,*args, **kwargs):
        
        creditos = Credito.objects.all().order_by('-pk')
        if request.POST['id'][0] != '0':
            credito_id = request.POST['id']
            creditos = Credito.objects.filter(id=credito_id).order_by('-pk')
            
        if request.POST['cliente'][0] != '0':
            credito_cliente = request.POST['cliente']
            creditos = Credito.objects.filter(cliente_id=credito_cliente).order_by('-pk')
            
        if request.POST['pedido'][0] != '0':
            credito_pedido = request.POST['pedido']
            creditos = Credito.objects.filter(pedido_id=credito_pedido).order_by('-pk')
            
        if request.POST['estado'][0] != '0':
            credito_estado = request.POST['estado']
            creditos = Credito.objects.filter(estado=credito_estado).order_by('-pk')
     

        creditos_json = []
        for credito in creditos:
            credito_json = {
                'id':credito.id,
                'cliente':credito.cliente,
                'pedido':credito.pedido_id,
                'credito': credito.monto_credito,
                'plazo_credito':credito.plazo_credito,
                'fecha':credito.fecha.strftime("%d-%m-%Y"),
                'fecha_vencimiento':credito.fecha_vencimiento.strftime("%d-%m-%Y"),
                'estado':credito.estado
            }
            creditos_json.append(credito_json)
        creditos_json = json.dumps(creditos_json)
        return JsonResponse(creditos_json, safe=False)
    

class PagarCredito(View):
    def get(self,request,*args, **kwargs):
        credito = kwargs['pk']
        credito = Credito.objects.get(id=credito)
        abonos = CreditoAbono.objects.filter(credito_id=credito.id).order_by('pk')
        restante = credito.monto_credito - credito.abonado
        context = {
            'credito':credito,
            'abonos':abonos,
            'restante':restante
        }
        return render(request,'pos/pagar_credito.html', context=context)
    
    def post(self,request,*args, **kwargs):
        abonado = request.POST['monto']
        impresora = request.POST['impresora']
        credito = Credito.objects.get(id=kwargs['pk'])
        abono = CreditoAbono.objects.create(credito_id=credito.id, monto=abonado, fecha=timezone.now()) 
        abono.save()
        
        credito.abonado = credito.abonado  + float(abonado)
        abono_imprimir = {
            "cliente":credito.cliente,
            "monto":abono.monto,
            "fecha": abono.fecha,
            "restante": round(credito.monto_credito - credito.abonado, 2)
        }
        imprimirTicketAbono(impresora,abono_imprimir)
        if credito.abonado >= credito.monto_credito:
            credito.estado = "Pagado"
            cliente = Cliente.objects.filter(cedula=credito.cliente_id)[0]
            cliente.credito = cliente.credito + credito.abonado
            cliente.save()  
        credito.save()
        return redirect('pos:creditos')
    

class lista_clientes_por_deuda(View):
    def get(self,request,*args, **kwargs):
        # Obtener los parámetros de filtro de cédula y nombre desde la URL
        cedula_filtro = request.GET.get('cedula', '')
        nombre_filtro = request.GET.get('nombre', '')
        mostrar_historial = request.GET.get('historial', '') == 'true'
        
        # Filtrar clientes por cédula y/o nombre si se proporciona un filtro
        clientes = Cliente.objects.all()
        if cedula_filtro:
            clientes = clientes.filter(cedula__icontains=cedula_filtro)
        if nombre_filtro:
            clientes = clientes.filter(nombre__icontains=nombre_filtro)
        
        # Calcular la deuda total para cada cliente
        clientes_procesados = []
        for cliente in clientes:
            creditos = Credito.objects.filter(cliente_id=cliente.cedula)
            abonos_totales = sum(CreditoAbono.objects.filter(credito_id__in=creditos.values_list('id', flat=True)).values_list('monto', flat=True))
            deuda_total = sum(creditos.values_list('monto_credito', flat=True)) - abonos_totales
            deuda_total = round(deuda_total, 2)
            
            cliente.deuda_total = deuda_total
            
            # Si es historial, incluir todos los clientes. Si no, solo los con deuda > 0
            if mostrar_historial or deuda_total > 0:
                clientes_procesados.append(cliente)
        
        # Ordenar por deuda total de mayor a menor
        clientes_procesados = sorted(clientes_procesados, key=lambda x: x.deuda_total, reverse=True)
        
        # Obtener valor del dólar
        dolar = ValorDolar.objects.get(pk=1)
        
        return render(request, 'pos/creditos.html', {
            'clientes': clientes_procesados,
            'dolar': dolar.valor,
            'cedula_filtro': cedula_filtro,  # Pasar el filtro a la plantilla
            'nombre_filtro': nombre_filtro,   # Pasar el filtro a la plantilla
            'mostrar_historial': mostrar_historial,  # Pasar el estado del historial
        })
    
class detalle_cliente(View):
    def get(self,request,*args, **kwargs):
        cliente = Cliente.objects.get(id=kwargs["pk"])
        # Order by fecha in descending order (newest first)
        creditos = Credito.objects.filter(cliente_id=cliente.cedula).order_by("-fecha")
        # Get abonos and order in descending order by fecha
        abonos = CreditoAbono.objects.filter(credito_id__in=creditos.values_list('id', flat=True)).order_by("-fecha")
        # Calcular la deuda total
        deuda_total = sum(credito.monto_credito for credito in creditos) - sum(abono.monto for abono in abonos)
        cliente.deuda_total = round(deuda_total,2)

        # Obtener pedidos relacionados a los créditos y ordenarlos por fecha descendente
        pedidos_ids = creditos.values_list('pedido_id', flat=True)
        pedidos = Pedido.objects.filter(id__in=pedidos_ids).order_by("-fecha")
        
        # Obtener valor del dólar
        dolar = ValorDolar.objects.get(pk=1)

        return render(request, 'pos/cliente_credito_detalles.html', {
            'cliente': cliente, 
            'creditos': creditos, 
            'abonos': abonos, 
            'pedidos': pedidos, 
            'cliente_id': cliente.id,
            'dolar': dolar.valor
        })

def imprimirTicketAbono(impresora,abono):


    sucursal = config.BUSINESS_NAME
    header = f'\x1B@\x1B\x61\x01\x1D\x54\x1C\x70\x01\x33\x1B\x21\x08{sucursal}\x1B!\x01\x1B\x21\x00\x0A\x0D------------------------------------------------\x0A\x0D'
    cliente = f'\x1B\x61\x02\x1B\x21\Cliente: {abono["cliente"]}\x0A\x0D\x0A\x0DRESTANTE: {abono["restante"]}\x1B\x21\x08\x1B\x21\x00\x0A\x0D\x0A\x0D'
    montos = f'\x1B\x61\x02\x1B\x21\x31ABONADO: {abono["monto"]}\x0A\x0D\x0A\x0DRESTANTE: {abono["restante"]}\x1B\x21\x08\x1B\x21\x00\x0A\x0D\x0A\x0D'
    fecha = f'\x1B\x61\x02\x1B\x21\FECHA: {datetime.now().strftime("%d/%m/%Y")}\x0A\x0D\x0A\x0D\x0A\x0A\x0A\x0A\x0A\x0A\x1B\x69'
    final_comandos = '\x0A\x0A\x0A\x0A\x0A\x0A\x1B\x69'

    comandos = header + cliente + montos + fecha + final_comandos
    
    # Usar la nueva función helper para impresión de abonos
    success, result, error_msg = conectar_socket_seguro(
        ip=impresora, 
        puerto=9100, 
        datos=comandos, 
        timeout=2,  # Timeout optimizado para impresoras
        es_balanza=False
    )
    
    if success:
        print(f"Ticket de abono impreso exitosamente en impresora {impresora}")
        return "SUCCESS"
    else:
        return "ERROR"

class VerificarEstadoCaja(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        try:
            # Si el usuario es PESADOR, retornar siempre como abierta
            if request.user.groups.filter(name='PESADOR').exists():
                return JsonResponse({
                    'status': 'success',
                    'caja_abierta': True
                })
            
            # Para otros usuarios, verificar el estado real de la caja
            caja_abierta = estadoCaja.objects.filter(
                usuario=request.user,
                fechaFin__isnull=True
            ).exists()

            return JsonResponse({
                'status': 'success',
                'caja_abierta': caja_abierta
            })
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)

class AbrirCaja(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        # Si el usuario es PESADOR, no permitir abrir caja
        if request.user.groups.filter(name='PESADOR').exists():
            return JsonResponse({
                'status': 'error',
                'message': 'Los usuarios PESADOR no manejan caja'
            }, status=400)
            
        data = request.POST
        usuario = request.user
        denominacionesUSD = json.loads(data.get('denominacionesUSD'))
        denominacionesBs = json.loads(data.get('denominacionesBs'))

        # Verificar si ya existe una caja abierta para este usuario
        caja_abierta = estadoCaja.objects.filter(
            usuario=usuario,
            fechaFin__isnull=True  # Una caja sin fecha de fin está abierta
        ).first()

        if caja_abierta:
            return JsonResponse({
                'status': 'error',
                'message': 'Ya tienes una caja abierta'
            }, status=400)

        # Si no hay caja abierta, crear una nueva
        nueva_caja = estadoCaja(
            usuario=usuario,
            fechaInicio=timezone.now(),
            dineroInicio={
                'USD': denominacionesUSD,
                'BS': denominacionesBs
            }
        )
        nueva_caja.save()

        return JsonResponse({
            'status': 'success',
            'message': 'Caja abierta exitosamente'
        })
    
class ValidarAutorizacionCredito(View):
    def post(self, request):
        codigo = request.POST.get('codigo')
        autorizado = False
        
        # Buscar usuarios que sean supervisores o administradores
        usuarios_autorizados = User.objects.filter(
            groups__name__in=['SUPERVISOR', 'ADMINISTRADOR']
        )
        
        # Verificar el código contra las contraseñas de usuarios autorizados
        for usuario in usuarios_autorizados:
            if check_password(codigo, usuario.password):
                autorizado = True
                break
        
        return JsonResponse({
            'autorizado': autorizado
        })

class ValidarAutorizacionVuelto(View):
    def post(self, request):
        codigo = request.POST.get('codigo')
        monto_saldo = request.POST.get('monto_saldo', 0)
        autorizado = False
        supervisor_autoriza = None
        
        # Buscar usuarios que sean supervisores o administradores
        usuarios_autorizados = User.objects.filter(
            groups__name__in=['SUPERVISOR', 'ADMINISTRADOR']
        )
        
        # Verificar el código contra las contraseñas de usuarios autorizados
        for usuario in usuarios_autorizados:
            if check_password(codigo, usuario.password):
                autorizado = True
                supervisor_autoriza = usuario.username
                break
        
        return JsonResponse({
            'autorizado': autorizado,
            'supervisor_autoriza': supervisor_autoriza,
            'monto_autorizado': float(monto_saldo) if autorizado else 0
        })

class ProcesarPedidoInjustificado(View):
    def post(self, request):
        pedido_id = request.POST.get('pedido_id')
        codigo = request.POST.get('codigo')
        
        # Validar autorización
        autorizado = False
        supervisor_autoriza = None
        
        # Buscar usuarios que sean supervisores o administradores
        usuarios_autorizados = User.objects.filter(
            groups__name__in=['SUPERVISOR', 'ADMINISTRADOR']
        )
        
        # Verificar el código contra las contraseñas de usuarios autorizados
        for usuario in usuarios_autorizados:
            if check_password(codigo, usuario.password):
                autorizado = True
                supervisor_autoriza = usuario.username
                break
        
        if not autorizado:
            return JsonResponse({
                'success': False,
                'error': 'Código de autorización incorrecto'
            })
        
        try:
            # Buscar el pedido
            pedido = Pedido.objects.get(id=pedido_id)
            
            # Verificar que esté en estado Injustificado
            if pedido.status != 'Injustificado':
                return JsonResponse({
                    'success': False,
                    'error': 'El pedido no está en estado Injustificado'
                })
            
            # Cambiar estado a "Por pagar" para permitir el proceso de pago
            pedido.status = 'Por pagar'
            pedido.save()
            
            return JsonResponse({
                'success': True,
                'message': f'Pedido autorizado por {supervisor_autoriza}. Redirigiendo al proceso de pago...',
                'pedido_id': pedido_id,
                'supervisor_autoriza': supervisor_autoriza
            })
            
        except Pedido.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Pedido no encontrado'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Error al procesar pedido: {str(e)}'
            })

class CierresCajaListView(LoginRequiredMixin, ADMIN_AUTH, ListView):
    model = estadoCaja
    template_name = 'cierres_caja.html'
    context_object_name = 'cierres'

    def get_queryset(self):
        # Mostrar todos los registros por defecto
        queryset = estadoCaja.objects.all().order_by('-fechaInicio')
        
        for cierre in queryset:
            # Calcular totales USD
            cierre.dinero_inicial_usd = sum(float(k) * float(v) for k, v in cierre.dineroInicio.get('USD', {}).items())
            cierre.dinero_final_usd = sum(float(k) * float(v) for k, v in (cierre.dineroFinal or {}).get('USD', {}).items())
            cierre.diferencia_usd = cierre.dinero_final_usd - cierre.dinero_inicial_usd
            
            # Calcular totales BS
            cierre.dinero_inicial_bs = sum(float(k) * float(v) for k, v in cierre.dineroInicio.get('BS', {}).items())
            cierre.dinero_final_bs = sum(float(k) * float(v) for k, v in (cierre.dineroFinal or {}).get('BS', {}).items())
            cierre.diferencia_bs = cierre.dinero_final_bs - cierre.dinero_inicial_bs
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['usuarios'] = User.objects.all()
        return context

class FiltrarCierresCaja(LoginRequiredMixin, ADMIN_AUTH, View):
    def post(self, request):
        id_cierre = request.POST.get('id_cierre')
        fecha_inicio = request.POST.get('fecha_inicio')
        fecha_fin = request.POST.get('fecha_fin')
        usuario = request.POST.get('usuario')
        estado = request.POST.get('estado')

        queryset = estadoCaja.objects.all()
        
        # Filtrar por ID
        if id_cierre:
            queryset = queryset.filter(id=id_cierre)

        # Filtrar por estado
        if estado == 'abierta':
            queryset = queryset.filter(fechaFin__isnull=True)
        elif estado == 'cerrada':
            queryset = queryset.filter(fechaFin__isnull=False)

        # Aplicar otros filtros
        if fecha_inicio:
            queryset = queryset.filter(fechaInicio__gte=fecha_inicio)
        if fecha_fin:
            queryset = queryset.filter(fechaInicio__lte=fecha_fin)
        if usuario:
            queryset = queryset.filter(usuario_id=usuario)

        # Ordenar por fecha de inicio descendente
        queryset = queryset.order_by('-fechaInicio')

        for cierre in queryset:
            # Calcular totales USD
            cierre.dinero_inicial_usd = sum(float(k) * float(v) for k, v in cierre.dineroInicio.get('USD', {}).items())
            cierre.dinero_final_usd = sum(float(k) * float(v) for k, v in (cierre.dineroFinal or {}).get('USD', {}).items())
            cierre.diferencia_usd = cierre.dinero_final_usd - cierre.dinero_inicial_usd
            
            # Calcular totales BS
            cierre.dinero_inicial_bs = sum(float(k) * float(v) for k, v in cierre.dineroInicio.get('BS', {}).items())
            cierre.dinero_final_bs = sum(float(k) * float(v) for k, v in (cierre.dineroFinal or {}).get('BS', {}).items())
            cierre.diferencia_bs = cierre.dinero_final_bs - cierre.dinero_inicial_bs

        html = render_to_string('cierres_caja_tabla.html', {'cierres': queryset})
        return JsonResponse({'html': html})
    


def imprimirTicketCierre(usuario, fecha_inicio, fecha_fin, dinero_inicial, dinero_esperado, dinero_final, impresora, cierre_id=None, pedidos_pendientes_count=0):
    try:
        fecha = datetime.now()
        
        # Comandos ESC/POS iniciales
        comandos = '\x1B@'  # Inicializar impresora
        comandos += '\x1B\x61\x01'  # Centrado
        comandos += '\x1D\x21\x11'  # Doble ancho y alto
        comandos += 'CIERRE DE CAJA\n'
        comandos += '\x1D\x21\x00'  # Tamaño normal
        
        # Información básica
        comandos += '\x1B\x61\x00'  # Alineación izquierda
        if cierre_id:
            comandos += f'ID Cierre: {cierre_id}\n'
        comandos += f'Fecha Apertura: {fecha_inicio.strftime("%d/%m/%Y %H:%M")}\n'
        comandos += f'Fecha Cierre: {fecha_fin.strftime("%d/%m/%Y %H:%M")}\n'
        comandos += f'Usuario: {usuario}\n'
        
        # Agregar información de pedidos pendientes
        if pedidos_pendientes_count > 0:
            comandos += f'Pedidos pendientes: {pedidos_pendientes_count}\n'
        else:
            comandos += 'Pedidos pendientes: 0\n'
            
        comandos += '\x1B\x61\x01'  # Centrado
        comandos += '-' * 42 + '\n'
        
        # Dinero Inicial
        comandos += '\x1B\x61\x00'  # Alineación izquierda
        comandos += '\x1B\x45\x01'  # Negrita activada
        comandos += 'DINERO INICIAL:\n'
        comandos += '\x1B\x45\x00'  # Negrita desactivada
        total_inicial_usd = 0
        total_inicial_bs = 0
        
        for moneda in ['USD', 'BS']:
            if moneda in dinero_inicial and dinero_inicial[moneda]:
                comandos += f'\n{moneda}:\n'
                total_moneda = 0
                for denom, cant in sorted(dinero_inicial[moneda].items(), key=lambda x: float(x[0]), reverse=True):
                    if float(cant) > 0:
                        monto = float(denom) * float(cant)
                        total_moneda += monto
                        comandos += f'{denom:>5} x {int(cant):<3} = {monto:>8.2f}\n'
                
                if moneda == 'USD':
                    total_inicial_usd = total_moneda
                else:
                    total_inicial_bs = total_moneda
                    
                comandos += f'Total {moneda}: {total_moneda:>.2f}\n'
        
        # Resumen de movimientos (usando datos del dineroEsperado que ya incluye todos los movimientos)
        comandos += '\x1B\x45\x01'  # Negrita activada
        comandos += '\nRESUMEN DE MOVIMIENTOS:\n'
        comandos += '\x1B\x45\x00'  # Negrita desactivada
        
        # Variables para totales
        total_ingresos_usd = 0
        total_ingresos_bs = 0
        total_egresos_usd = 0
        total_egresos_bs = 0
        
        # Ingresos por método de pago
        debito_total = dinero_esperado.get('ingresos', {}).get('DEBITO', 0)
        credito_total = dinero_esperado.get('ingresos', {}).get('CREDITO', 0)
        pagomovil_total = dinero_esperado.get('ingresos', {}).get('PAGOMOVIL', 0)
        
        if debito_total > 0:
            comandos += f'DEBITO: Bs.{debito_total:.2f}\n'
        
        if credito_total > 0:
            comandos += f'CREDITO: ${credito_total:.2f}\n'
        
        if pagomovil_total > 0:
            comandos += f'PAGO MOVIL: Bs.{pagomovil_total:.2f}\n'
        
        # Ingresos en efectivo
        comandos += '\nEfectivo USD:\n'
        if 'ingresos' in dinero_esperado and 'USD' in dinero_esperado['ingresos']:
            for denom, cant in sorted(dinero_esperado['ingresos']['USD'].items(), key=lambda x: float(x[0]), reverse=True):
                if float(cant) > 0:
                    monto = float(denom) * float(cant)
                    total_ingresos_usd += monto
                    comandos += f'${denom:>5} x {int(cant):<3} = ${monto:>8.2f}\n'
        
        comandos += '\nEfectivo BS:\n'
        if 'ingresos' in dinero_esperado and 'BS' in dinero_esperado['ingresos']:
            for denom, cant in sorted(dinero_esperado['ingresos']['BS'].items(), key=lambda x: float(x[0]), reverse=True):
                if float(cant) > 0:
                    monto = float(denom) * float(cant)
                    total_ingresos_bs += monto
                    comandos += f'Bs.{denom:>5} x {int(cant):<3} = Bs.{monto:>8.2f}\n'
        
        # Egresos en efectivo
        comandos += '\nEGRESOS:\n'
        
        comandos += '\nEfectivo USD:\n'
        if 'egresos' in dinero_esperado and 'USD' in dinero_esperado['egresos']:
            for denom, cant in sorted(dinero_esperado['egresos']['USD'].items(), key=lambda x: float(x[0]), reverse=True):
                if float(cant) > 0:
                    monto = float(denom) * float(cant)
                    total_egresos_usd += monto
                    comandos += f'${denom:>5} x {int(cant):<3} = ${monto:>8.2f}\n'
        
        comandos += '\nEfectivo BS:\n'
        if 'egresos' in dinero_esperado and 'BS' in dinero_esperado['egresos']:
            for denom, cant in sorted(dinero_esperado['egresos']['BS'].items(), key=lambda x: float(x[0]), reverse=True):
                if float(cant) > 0:
                    monto = float(denom) * float(cant)
                    total_egresos_bs += monto
                    comandos += f'Bs.{denom:>5} x {int(cant):<3} = Bs.{monto:>8.2f}\n'
        
        # Totales de movimientos
        comandos += '\n\x1B\x45\x01TOTALES DE MOVIMIENTOS:\x1B\x45\x00\n'
        comandos += f'Total Ingresos USD (efectivo): ${total_ingresos_usd:.2f}\n'
        comandos += f'Total Ingresos BS: Bs.{total_ingresos_bs:.2f}\n'
        comandos += f'Total Egresos USD: ${total_egresos_usd:.2f}\n'
        comandos += f'Total Egresos BS: Bs.{total_egresos_bs:.2f}\n'
        comandos += f'Total Crédito USD (no en caja): ${credito_total:.2f}\n'
        
        # Dinero Final
        comandos += '\x1B\x45\x01'
        comandos += '\nDINERO FINAL REPORTADO:\n'
        comandos += '\x1B\x45\x00'  # Negrita desactivada
        total_final_usd = 0
        total_final_bs = 0
        
        for moneda in ['USD', 'BS']:
            if moneda in dinero_final and dinero_final[moneda]:
                comandos += f'\n{moneda}:\n'
                total_moneda = 0
                for denom, cant in sorted(dinero_final[moneda].items(), key=lambda x: float(x[0]), reverse=True):
                    if float(cant) > 0:
                        monto = float(denom) * float(cant)
                        total_moneda += monto
                        comandos += f'{denom:>5} x {int(cant):<3} = {monto:>8.2f}\n'
                
                if moneda == 'USD':
                    total_final_usd = total_moneda
                else:
                    total_final_bs = total_moneda
                
                comandos += f'Total {moneda}: {total_moneda:>.2f}\n'
        
        # Calcular totales esperados (usando directamente los datos del dineroEsperado)
        total_esperado_usd = total_inicial_usd + total_ingresos_usd - total_egresos_usd
        total_esperado_bs = total_inicial_bs + total_ingresos_bs - total_egresos_bs
        
        # Diferencias entre esperado y reportado
        comandos += '\x1B\x45\x01'  # Negrita activada
        comandos += '\nRESUMEN DE TOTALES Y DIFERENCIAS:\n'
        comandos += '\x1B\x45\x00'  # Negrita desactivada
        
        comandos += '\nUSD:\n'
        comandos += f'Inicial: ${total_inicial_usd:.2f}\n'
        comandos += f'+ Ingresos: ${total_ingresos_usd:.2f}\n'
        comandos += f'- Egresos: ${total_egresos_usd:.2f}\n'
        comandos += f'= Esperado: ${total_esperado_usd:.2f}\n'
        comandos += f'Final reportado: ${total_final_usd:.2f}\n'
        diferencia_usd = total_final_usd - total_esperado_usd
        if abs(diferencia_usd) > 0.01:  # Para evitar diferencias por redondeo
            comandos += f'Diferencia: ${diferencia_usd:+.2f}\n'
        else:
            comandos += 'Diferencia: $0.00\n'
        
        comandos += '\nBS (solo efectivo):\n'
        comandos += f'Inicial: Bs.{total_inicial_bs:.2f}\n'
        comandos += f'+ Ingresos (efectivo): Bs.{total_ingresos_bs:.2f}\n'
        comandos += f'- Egresos: Bs.{total_egresos_bs:.2f}\n'
        comandos += f'= Esperado: Bs.{total_esperado_bs:.2f}\n'
        comandos += f'Final reportado: Bs.{total_final_bs:.2f}\n'
        diferencia_bs = total_final_bs - total_esperado_bs
        if abs(diferencia_bs) > 0.01:  # Para evitar diferencias por redondeo
            comandos += f'Diferencia: Bs.{diferencia_bs:+.2f}\n'
        else:
            comandos += 'Diferencia: Bs.0.00\n'
        
        # Mostrar otros métodos de pago como información
        if debito_total > 0 or pagomovil_total > 0:
            comandos += '\nOtros métodos de pago BS (no en caja):\n'
            if debito_total > 0:
                comandos += f'Débito: Bs.{debito_total:.2f}\n'
            if pagomovil_total > 0:
                comandos += f'Pago Móvil: Bs.{pagomovil_total:.2f}\n'
        
        # Diferencias por denominación
        hay_diferencias = False
        for moneda in ['USD', 'BS']:
            diferencias_moneda = []
            
            # Obtener todas las denominaciones
            todas_denominaciones = set()
            if moneda in dinero_inicial:
                todas_denominaciones.update(dinero_inicial[moneda].keys())
            if 'ingresos' in dinero_esperado and moneda in dinero_esperado['ingresos']:
                todas_denominaciones.update(dinero_esperado['ingresos'][moneda].keys())
            if 'egresos' in dinero_esperado and moneda in dinero_esperado['egresos']:
                todas_denominaciones.update(dinero_esperado['egresos'][moneda].keys())
            if moneda in dinero_final:
                todas_denominaciones.update(dinero_final[moneda].keys())
            
            for denom in todas_denominaciones:
                inicial = float(dinero_inicial.get(moneda, {}).get(denom, 0))
                ingresos = float(dinero_esperado.get('ingresos', {}).get(moneda, {}).get(denom, 0))
                egresos = float(dinero_esperado.get('egresos', {}).get(moneda, {}).get(denom, 0))
                final = float(dinero_final.get(moneda, {}).get(denom, 0))
                
                teorico = inicial + ingresos - egresos
                diferencia = final - teorico
                
                if abs(diferencia) > 0.01:  # Para evitar diferencias por redondeo
                    hay_diferencias = True
                    signo = '+' if diferencia > 0 else ''
                    simbolo = '$' if moneda == 'USD' else 'Bs.'
                    diferencias_moneda.append(f' {simbolo}{denom}: {signo}{diferencia:.2f}')
            
            if diferencias_moneda:
                comandos += f'\nDetalle diferencias {moneda}:\n'
                comandos += '\n'.join(diferencias_moneda) + '\n'
        
        if not hay_diferencias:
            comandos += '\nNo se encontraron diferencias por denominación\n'
        
        # Nota explicativa
        comandos += '\nNOTA: El dinero esperado incluye todos\n'
        comandos += 'los movimientos de pedidos y abonos\n'
        comandos += 'de créditos registrados en este cierre.\n'
        
        # Firma
        comandos += '\n\n'
        comandos += '\x1B\x61\x01'  # Centrado
        comandos += '_' * 30
        comandos += '\nFirma\n\n'
        
        # Comandos finales
        comandos += '\n\n\n'  # Espacio para el corte
        comandos += '\x1D\x56\x41'  # Corte de papel
        comandos += '\x0A\x0A\x0A\x0A\x0A\x0A\x1B\x69'
        
        # Enviar a la impresora usando la función helper
        success, result, error_msg = conectar_socket_seguro(
            ip=impresora, 
            puerto=9100, 
            datos=comandos, 
            timeout=2,  # Timeout optimizado para impresoras
            es_balanza=False
        )
        
        if success:
            print(f"Ticket de cierre impreso exitosamente en impresora {impresora}")
            return True
        else:
            return False
        
    except Exception as e:
        print(f"Error al generar ticket de cierre: {str(e)}")
        return False

class CierreCaja(LoginRequiredMixin, View):
    def post(self, request):
        try:
            caja_actual = estadoCaja.objects.get(
                usuario=request.user,
                fechaFin__isnull=True
            )
            
            # Obtener el dinero final reportado
            denominaciones_usd = json.loads(request.POST.get('denominacionesUSD', '{}'))
            denominaciones_bs = json.loads(request.POST.get('denominacionesBs', '{}'))
            dinero_final = {
                'USD': denominaciones_usd,
                'BS': denominaciones_bs
            }
            
            # Calcular el dinero que debería haber (inicial + esperado)
            dinero_inicial = caja_actual.dineroInicio or {'USD': {}, 'BS': {}}
            dinero_esperado = caja_actual.dineroEsperado or {
                'ingresos': {'USD': {}, 'BS': {}, 'DEBITO': 0, 'CREDITO': 0, 'PAGOMOVIL': 0},
                'egresos': {'USD': {}, 'BS': {}}
            }
            
            # Calcular el dinero que debería haber
            dinero_teorico = {'USD': {}, 'BS': {}}
            
            for moneda in ['USD', 'BS']:
                # Inicializar todas las denominaciones posibles
                todas_denominaciones = set()
                todas_denominaciones.update(dinero_inicial[moneda].keys())
                todas_denominaciones.update(dinero_esperado['ingresos'][moneda].keys())
                todas_denominaciones.update(dinero_esperado['egresos'][moneda].keys())
                
                for denom in todas_denominaciones:
                    inicial = float(dinero_inicial[moneda].get(denom, 0))
                    ingresos = float(dinero_esperado['ingresos'][moneda].get(denom, 0))
                    egresos = float(dinero_esperado['egresos'][moneda].get(denom, 0))
                    
                    dinero_teorico[moneda][denom] = inicial + ingresos - egresos
            
            # Calcular diferencias
            diferencias = {'USD': {}, 'BS': {}}
            for moneda in ['USD', 'BS']:
                for denom in set(dinero_teorico[moneda].keys()) | set(dinero_final[moneda].keys()):
                    teorico = float(dinero_teorico[moneda].get(denom, 0))
                    final = float(dinero_final[moneda].get(denom, 0))
                    if teorico != final:
                        diferencias[moneda][denom] = final - teorico
            
            # Guardar el cierre
            caja_actual.dineroFinal = dinero_final
            caja_actual.fechaFin = timezone.now()
            
            # Capturar pedidos pendientes al momento del cierre
            pedidos_pendientes = Pedido.objects.filter(
                status="Por pagar",
                fecha__gte=caja_actual.fechaInicio,
                fecha__lte=timezone.now()
            ).filter(
                Q(usuario__isnull=True) | 
                Q(usuario='') | 
                Q(usuario=request.user.username)
            ).values(
                'id', 'precio_total', 'status', 'fecha', 'usuario', 'pesador', 'numero_pedido_balanza'
            )
            
            # Debug: Imprimir información para depuración
            print(f"DEBUG: Usuario del cierre: {request.user.username}")
            print(f"DEBUG: Fecha inicio caja: {caja_actual.fechaInicio}")
            print(f"DEBUG: Fecha fin (ahora): {timezone.now()}")
            print(f"DEBUG: Pedidos encontrados: {pedidos_pendientes.count()}")
            for p in pedidos_pendientes:
                print(f"DEBUG: Pedido {p['id']} - Usuario: '{p['usuario']}' - Status: {p['status']}")
            
            # Convertir a lista para poder serializar
            pedidos_pendientes_list = []
            for pedido in pedidos_pendientes:
                pedidos_pendientes_list.append({
                    'id': pedido['id'],
                    'precio_total': float(pedido['precio_total']) if pedido['precio_total'] else 0.0,
                    'status': pedido['status'],
                    'fecha': pedido['fecha'].isoformat() if pedido['fecha'] else None,
                    'usuario': pedido['usuario'] or '',
                    'pesador': pedido['pesador'] or '',
                    'numero_pedido_balanza': pedido['numero_pedido_balanza'] or None
                })
            
            caja_actual.pedidos_pendientes = pedidos_pendientes_list
            caja_actual.save()
            
            # Justo antes del return, agregamos la impresión del ticket
            impresora = request.POST.get('impresora')
            if impresora:
                imprimirTicketCierre(
                    usuario=request.user.username,
                    fecha_inicio=caja_actual.fechaInicio,
                    fecha_fin=timezone.now(),
                    dinero_inicial=caja_actual.dineroInicio or {'USD': {}, 'BS': {}},
                    dinero_esperado=caja_actual.dineroEsperado or {'ingresos': {'USD': {}, 'BS': {}}, 'egresos': {'USD': {}, 'BS': {}}},
                    dinero_final=dinero_final,
                    impresora=impresora,
                    cierre_id=caja_actual.id,
                    pedidos_pendientes_count=len(pedidos_pendientes_list)
                )

            return JsonResponse({
                'status': 'success',
                'diferencias': diferencias
            })
            
        except estadoCaja.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'No hay caja abierta'
            }, status=400)

class ActualizarDineroEsperado(LoginRequiredMixin, View):
    def post(self, request):
        try:
            caja_actual = estadoCaja.objects.get(
                usuario=request.user,
                fechaFin__isnull=True
            )
            
            pago = json.loads(request.POST.get('pago'))
            dinero_esperado = caja_actual.dineroEsperado or {'USD': {}, 'BS': {}}
            
            # Actualizar cantidades esperadas
            for moneda, denominaciones in pago.items():
                for denom, cantidad in denominaciones.items():
                    if moneda not in dinero_esperado:
                        dinero_esperado[moneda] = {}
                    dinero_esperado[moneda][denom] = dinero_esperado[moneda].get(denom, 0) + cantidad
            
            caja_actual.dineroEsperado = dinero_esperado
            caja_actual.save()
            
            return JsonResponse({'status': 'success'})
            
        except estadoCaja.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'No hay caja abierta'
            }, status=400)

class AbonarCredito(View):
    # CSRF protection is disabled for this view through settings.py
    # Be aware of security implications when processing payments
    def get(self, request, *args, **kwargs):
        cliente_id = kwargs['pk']
        cliente = Cliente.objects.get(id=cliente_id)
        dolar = ValorDolar.objects.get(pk=1)
        
        # Calcular la deuda total del cliente
        creditos_pendientes = Credito.objects.filter(cliente_id=cliente.cedula, estado='Pendiente').order_by('fecha')
        deuda_total = sum(credito.monto_credito - credito.abonado for credito in creditos_pendientes)
        
        context = {
            'cliente': cliente,
            'dolar': dolar.valor,
            'creditos_pendientes': creditos_pendientes,
            'deuda_total': round(deuda_total, 2),  # Redondear a 2 decimales
        }
        return render(request, 'pos/abonar_credito.html', context)

    def post(self, request, *args, **kwargs):
        cliente_id = kwargs['pk']
        cliente = Cliente.objects.get(id=cliente_id)
        abono_total = float(request.POST['abono_total'])
        movimientos_caja = json.loads(request.POST.get('movimientos_caja', '{}'))
        abonos = json.loads(request.POST.get('abonos', '[]'))
        dolar = ValorDolar.objects.get(pk=1)

        # Obtener créditos pendientes ordenados por fecha
        creditos_pendientes = Credito.objects.filter(cliente_id=cliente.cedula, estado='Pendiente').order_by('fecha')

        # Calcular la deuda total
        deuda_total = sum(credito.monto_credito - credito.abonado for credito in creditos_pendientes)

        # Ya no validamos que el abono no exceda la deuda total
        # if abono_total > deuda_total:
        #    return JsonResponse({'status': 'error', 'message': 'El abono excede la deuda total.'})

        # Procesar cada método de pago
        for abono in abonos:
            metodo_pago = abono['metodo']
            cantidad = abono['cantidad']
            denominaciones = abono.get('denominaciones', {})  # Obtener denominaciones si existen
            vuelto = abono.get('vuelto', {})  # Obtener vuelto si existe
            
            # Log para depuración
            print(f"Procesando abono: {metodo_pago}, cantidad: {cantidad}, dolar.valor: {dolar.valor}")
            print(f"Denominaciones: {denominaciones}")
            print(f"Vuelto: {vuelto}")
            
            # Convertir a dólares si es necesario
            if metodo_pago == 'Efectivo ($)':
                monto_dolares = cantidad
                monto_neto = cantidad
            elif metodo_pago == 'Efectivo (Bs)':
                # Usar más precisión en el cálculo
                monto_dolares = round(cantidad / dolar.valor, 4)
                monto_neto = cantidad
                print(f"Conversión Bs a USD: {cantidad} / {dolar.valor} = {monto_dolares}")
            elif metodo_pago == 'Débito':
                monto_dolares = round(cantidad / dolar.valor, 4)
                monto_neto = cantidad
                print(f"Conversión débito a USD: {cantidad} / {dolar.valor} = {monto_dolares}")
            elif metodo_pago == 'Pago Móvil':
                monto_dolares = round(cantidad / dolar.valor, 4)
                monto_neto = cantidad
                print(f"Conversión pago móvil a USD: {cantidad} / {dolar.valor} = {monto_dolares}")
            else:
                monto_dolares = cantidad
                monto_neto = cantidad
            
            print(f"Monto final en dólares: {monto_dolares}")
            
            # Crear registro de abono para cada método de pago
            # Obtener el cierre de caja activo del usuario actual
            try:
                caja_actual = estadoCaja.objects.get(
                    usuario=request.user,
                    fechaFin__isnull=True
                )
            except estadoCaja.DoesNotExist:
                caja_actual = None
            
            CreditoAbono.objects.create(
                credito_id=creditos_pendientes[0].id if creditos_pendientes else None,  # Asociar al primer crédito o None
                monto=round(monto_dolares, 2),
                fecha=timezone.now(),
                metodo_pago=metodo_pago,
                monto_neto=round(monto_neto, 2),
                denominaciones=denominaciones if denominaciones else None,  # Guardar denominaciones
                vuelto=vuelto if vuelto else None,  # Guardar vuelto
                cierre_caja=caja_actual  # Asignar al cierre de caja del usuario actual
            )
        
        # Aplicar el abono a los créditos pendientes
        abono_restante = abono_total
        for credito in creditos_pendientes:
            deuda_credito = credito.monto_credito - credito.abonado
            if abono_restante <= 0:
                break
            if abono_restante >= deuda_credito:
                credito.abonado += deuda_credito
                abono_restante -= deuda_credito
                credito.estado = 'Pagado'
            else:
                credito.abonado += abono_restante
                abono_restante = 0
            credito.save()

        # Restaurar el crédito del cliente cuando el pago elimina la deuda o genera saldo a favor
        if abono_total >= deuda_total:
            # Restaurar el crédito disponible siguiendo la misma lógica que en PagarCredito
            cliente.credito = cliente.credito + abono_total
            cliente.save()

        # Calcular deuda restante después de aplicar el abono
        deuda_restante = deuda_total - abono_total
        
        # Obtener la impresora desde los datos POST
        impresora = request.POST.get('impresora')
        
        # Imprimir ticket si hay impresora configurada
        if impresora:
            # Imprimir el ticket detallado del abono
            imprimirTicketAbonoDetallado(
                cliente=cliente,
                abono_total=abono_total,
                abonos=abonos,
                deuda_total=deuda_total,
                deuda_restante=deuda_restante,
                impresora=impresora,
                usuario=request.user.username
            )

        # Actualizar el dinero esperado en caja
        try:
            caja_actual = estadoCaja.objects.get(
                usuario=request.user,
                fechaFin__isnull=True
            )

            dinero_esperado = caja_actual.dineroEsperado or {
                'ingresos': {'USD': {}, 'BS': {}, 'DEBITO': 0, 'CREDITO': 0, 'PAGOMOVIL': 0},
                'egresos': {'USD': {}, 'BS': {}}
            }

            # Procesar ingresos y egresos
            for tipo in ['ingresos', 'egresos']:
                for moneda in ['USD', 'BS']:
                    if moneda in movimientos_caja[tipo]:
                        for denom, cantidad in movimientos_caja[tipo][moneda].items():
                            if tipo not in dinero_esperado:
                                dinero_esperado[tipo] = {}
                            if moneda not in dinero_esperado[tipo]:
                                dinero_esperado[tipo][moneda] = {}
                            
                            denom_str = str(denom)
                            if denom_str not in dinero_esperado[tipo][moneda]:
                                dinero_esperado[tipo][moneda][denom_str] = 0
                            dinero_esperado[tipo][moneda][denom_str] += cantidad
            
            # Agregar débito y pago móvil
            dinero_esperado['ingresos']['DEBITO'] = dinero_esperado['ingresos'].get('DEBITO', 0) + movimientos_caja['ingresos'].get('DEBITO', 0)
            dinero_esperado['ingresos']['PAGOMOVIL'] = dinero_esperado['ingresos'].get('PAGOMOVIL', 0) + movimientos_caja['ingresos'].get('PAGOMOVIL', 0)
            
            caja_actual.dineroEsperado = dinero_esperado
            caja_actual.save()

        except estadoCaja.DoesNotExist:
            pass  # Continuar con el abono incluso si no hay caja abierta

        return JsonResponse({'status': 'success'})

class ReimprimirTicketCierre(LoginRequiredMixin, View):
    def post(self, request, pk):
        try:
           
           cierre = estadoCaja.objects.get(pk=pk)

           impresora = request.POST.get('impresora')
           if impresora:
            
                # Reimprimir el ticket utilizando la función existente
                pedidos_pendientes_count = len(cierre.pedidos_pendientes) if cierre.pedidos_pendientes else 0
                resultado = imprimirTicketCierre(
                    usuario=cierre.usuario.username,
                    fecha_inicio=cierre.fechaInicio,
                    fecha_fin=cierre.fechaFin,
                    dinero_inicial=cierre.dineroInicio or {'USD': {}, 'BS': {}},
                    dinero_esperado=cierre.dineroEsperado or {
                        'ingresos': {'USD': {}, 'BS': {}, 'DEBITO': 0, 'CREDITO': 0, 'PAGOMOVIL': 0},
                        'egresos': {'USD': {}, 'BS': {}}
                    },
                    dinero_final=cierre.dineroFinal or {'USD': {}, 'BS': {}},
                    impresora=impresora,
                    cierre_id=pk,
                    pedidos_pendientes_count=pedidos_pendientes_count
                )
            
                if resultado:
                    return JsonResponse({'success': True})
                else:
                    return JsonResponse({'success': False, 'error': 'Error al imprimir el ticket'})
                
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

class FiltrarPedidos(LoginRequiredMixin, View):
    def post(self, request):
        # Obtener parámetros de filtro
        fecha_inicio = request.POST.get('fecha_inicio')
        fecha_fin = request.POST.get('fecha_fin')
        estado = request.POST.get('estado')
        cliente = request.POST.get('cliente')
        monto_min = request.POST.get('monto_min')
        monto_max = request.POST.get('monto_max')
        usuario = request.POST.get('usuario')
        pedido_id = request.POST.get('pedido_id')
        pesador = request.POST.get('pesador')
        
        # Comenzar con todos los pedidos
        queryset = Pedido.objects.all()
        
        # Aplicar filtros si se proporcionan
        if pedido_id:
            try:
                queryset = queryset.filter(id=int(pedido_id))
            except ValueError:
                pass
            
        if fecha_inicio:
            queryset = queryset.filter(fecha__gte=fecha_inicio)
        if fecha_fin:
            # Añadir un día para incluir todo el día final
            try:
                fecha_fin_obj = datetime.strptime(fecha_fin, "%Y-%m-%d") + timedelta(days=1)
                fecha_fin = fecha_fin_obj.strftime("%Y-%m-%d")
                queryset = queryset.filter(fecha__lt=fecha_fin)
            except (ValueError, TypeError):
                pass
                
        if estado:
            queryset = queryset.filter(status=estado)
        if cliente:
            # Buscar por ID exacto o por nombre que contenga el texto
            if cliente.isdigit():
                queryset = queryset.filter(cliente=int(cliente))
            else:
                # Buscar clientes cuyo nombre contenga el texto
                clientes_ids = Cliente.objects.filter(nombre__icontains=cliente).values_list('id', flat=True)
                queryset = queryset.filter(cliente__in=clientes_ids)
        
        if monto_min:
            try:
                queryset = queryset.filter(precio_total__gte=float(monto_min))
            except ValueError:
                pass
        if monto_max:
            try:
                queryset = queryset.filter(precio_total__lte=float(monto_max))
            except ValueError:
                pass
        if usuario:
            queryset = queryset.filter(usuario=usuario)
        if pesador:
            queryset = queryset.filter(pesador=pesador)
        
        # Ordenar por fecha descendente
        queryset = queryset.order_by('-fecha')
        
        # Contar registros totales antes de aplicar el límite
        total_count = queryset.count()
        
        # Limitar a 3000 registros para evitar sobrecarga
        queryset = queryset[:3000]
        
        # Obtener todos los clientes para mostrar nombres
        clientes = Cliente.objects.all()
        
        # Renderizar solo las filas de la tabla
        html = render_to_string('pos/pedidos_list_rows.html', {
            'pedidos_list': queryset,
            'clientes': clientes
        }, request=request)
        
        # Devolver la respuesta JSON con el HTML y el contador
        return JsonResponse({
            'html': html,
            'count': queryset.count(),
            'total_count': total_count,
            'limited': total_count > 3000
        })

class ExportarPedidosExcel(LoginRequiredMixin, View):
    def get(self, request):
        # Obtener parámetros de filtro
        fecha_inicio = request.GET.get('fecha_inicio')
        fecha_fin = request.GET.get('fecha_fin')
        estado = request.GET.get('estado')
        cliente = request.GET.get('cliente')
        monto_min = request.GET.get('monto_min')
        monto_max = request.GET.get('monto_max')
        usuario = request.GET.get('usuario')
        pedido_id = request.GET.get('pedido_id')
        pesador = request.GET.get('pesador')
        
        # Comenzar con todos los pedidos
        queryset = Pedido.objects.all()
        
        # Aplicar filtros si se proporcionan
        if pedido_id:
            queryset = queryset.filter(id=pedido_id)
            
        if fecha_inicio:
            queryset = queryset.filter(fecha__gte=fecha_inicio)
        if fecha_fin:
            # Añadir un día para incluir todo el día final
            fecha_fin = datetime.strptime(fecha_fin, "%Y-%m-%d") + timedelta(days=1)
            queryset = queryset.filter(fecha__lt=fecha_fin)
        if estado:
            queryset = queryset.filter(status=estado)
        if cliente:
            # Buscar por ID exacto o por nombre que contenga el texto
            if cliente.isdigit():
                queryset = queryset.filter(cliente=int(cliente))
            else:
                # Buscar clientes cuyo nombre contenga el texto
                clientes_ids = Cliente.objects.filter(nombre__icontains=cliente).values_list('id', flat=True)
                queryset = queryset.filter(cliente__in=clientes_ids)
        
        if monto_min:
            queryset = queryset.filter(precio_total__gte=float(monto_min))
        if monto_max:
            queryset = queryset.filter(precio_total__lte=float(monto_max))
        if usuario:
            queryset = queryset.filter(usuario=usuario)
        if pesador:
            queryset = queryset.filter(pesador=pesador)
        
        # Ordenar por fecha descendente
        queryset = queryset.order_by('-fecha')
        
        # Obtener todos los clientes para mostrar nombres
        clientes = {cliente.id: cliente.nombre for cliente in Cliente.objects.all()}
        
        # Crear respuesta CSV
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="pedidos_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['ID', 'Fecha', 'Cliente', 'Total', 'Fecha Pagado', 'Estado', 'Usuario', 'Pesador'])
        
        for pedido in queryset:
            nombre_cliente = clientes.get(pedido.cliente, 'Cliente General') if pedido.cliente != 0 else 'Cliente General'
            fecha_str = pedido.fecha.strftime("%d/%m/%Y %H:%M") if pedido.fecha else ''
            fecha_pagado_str = pedido.pagado_fecha.strftime("%d/%m/%Y %H:%M") if pedido.pagado_fecha else ''
            
            writer.writerow([
                pedido.id,
                fecha_str,
                nombre_cliente,
                f"${pedido.precio_total:.2f}",
                fecha_pagado_str,
                pedido.status,
                pedido.usuario or '',
                pedido.pesador or ''
            ])
        
        return response

# Formulario para el cambio de precios
class CambioPreciosForm(forms.Form):
    valor = forms.DecimalField(
        min_value=0,
        max_digits=10,
        decimal_places=2,
        required=True,
        label="Nuevo precio",
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
    )
    
    aplicar_a_precio_detal = forms.BooleanField(
        required=False,
        initial=True,
        label="Precio Detalle"
    )
    
    aplicar_a_precio_mayor = forms.BooleanField(
        required=False,
        label="Precio Mayor"
    )
    
    aplicar_a_precio_especial = forms.BooleanField(
        required=False,
        label="Precio Especial"
    )
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Al menos un tipo de precio debe estar seleccionado
        if not any([
            cleaned_data.get('aplicar_a_precio_detal'),
            cleaned_data.get('aplicar_a_precio_mayor'),
            cleaned_data.get('aplicar_a_precio_especial')
        ]):
            raise forms.ValidationError("Debes seleccionar al menos un tipo de precio para actualizar.")
            
        return cleaned_data

# Vista para manejar el cambio de precios
class CambioPreciosCategoria(LoginRequiredMixin, FormView):
    template_name = 'pos/cambiar_precios_categoria.html'
    form_class = CambioPreciosForm
    
    def get_success_url(self):
        return reverse_lazy('pos:categorias')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obtener la categoría
        categoria_id = self.kwargs.get('pk')
        categoria = get_object_or_404(CategoriasProductos, pk=categoria_id)
        
        # Obtener productos de esta categoría
        productos = Producto.objects.filter(categoria=categoria)
        
        context.update({
            'categoria': categoria,
            'productos': productos,
            'total_productos': productos.count()
        })
        
        return context
    
    def form_valid(self, form):
        # Obtener datos del formulario
        nuevo_precio = form.cleaned_data['valor']  # Sin convertir a float para mantener precisión decimal
        aplicar_a_precio_detal = form.cleaned_data['aplicar_a_precio_detal']
        aplicar_a_precio_mayor = form.cleaned_data['aplicar_a_precio_mayor']
        aplicar_a_precio_especial = form.cleaned_data['aplicar_a_precio_especial']
        
        # Obtener la categoría
        categoria_id = self.kwargs.get('pk')
        categoria = get_object_or_404(CategoriasProductos, pk=categoria_id)
        
        # Obtener productos de esta categoría
        productos = Producto.objects.filter(categoria=categoria)
        
        # Diccionario para almacenar campos a actualizar
        campos_a_actualizar = {}
        if aplicar_a_precio_detal:
            campos_a_actualizar['precio_detal'] = True
        if aplicar_a_precio_mayor:
            campos_a_actualizar['precio_mayor'] = True
        if aplicar_a_precio_especial:
            campos_a_actualizar['precio_especial'] = True
        
        # Contador
        productos_actualizados = 0
        
        # Actualizar precios
        for producto in productos:
            modificado = False
            
            for campo in campos_a_actualizar:
                precio_actual = getattr(producto, campo, None)
                
                # Solo actualizar si el campo tiene un valor
                if precio_actual is not None:
                    # Actualizar el campo con el precio exacto sin redondear
                    setattr(producto, campo, nuevo_precio)
                    modificado = True
            
            # Guardar el producto si fue modificado
            if modificado:
                producto.save()
                productos_actualizados += 1
        
        # Mostrar mensaje de éxito
        if productos_actualizados > 0:
            mensaje = f"Se actualizaron los precios de {productos_actualizados} productos en la categoría '{categoria.nombre}' al valor {nuevo_precio}."
            messages.success(self.request, mensaje)
        else:
            messages.warning(
                self.request,
                f"No se actualizaron productos en la categoría '{categoria.nombre}'. Verifica que los productos tengan valores en los campos seleccionados."
            )
        
        return super().form_valid(form)

class ActualizarClientePedido(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        try:
            pedido_id = request.POST.get('pedido_id')
            cliente_id = request.POST.get('cliente_id')
            
            # Obtener el pedido
            pedido = Pedido.objects.get(pk=pedido_id)
            
            # Verificar que el pedido no esté pagado
            if pedido.status in ['Pagado', 'Pagado con Crédito']:
                return JsonResponse({
                    'status': 'error',
                    'message': 'No se puede cambiar el cliente de un pedido ya pagado'
                })
            
            # Actualizar el cliente
            pedido.cliente = cliente_id
            pedido.save()
            
            return JsonResponse({
                'status': 'success',
                'message': 'Cliente actualizado correctamente'
            })
            
        except Pedido.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'El pedido no existe'
            }, status=404)
        except Exception as e:
            return JsonResponse({
            }, status=500)

def imprimirTicketAbonoDetallado(cliente, abono_total, abonos, deuda_total, deuda_restante, impresora, usuario):
    try:
        fecha = datetime.now()
        dolar = ValorDolar.objects.get(pk=1)
        
        # Formatear fecha y hora (formato 12 horas)
        fecha_str = f'{fecha.strftime("%I:%M:%S %p")} - {fecha.day}/{fecha.month}/{fecha.year}'
        fecha_len = len(fecha_str)
        
        # Formatear información de cajero
        login = f'CAJERO: {usuario}'
        login_len = len(login)
        
        # Calcular espacios para alinear el cajero a la derecha
        espacios = 48 - (fecha_len + login_len)
        login = login.rjust(len(login) + espacios)
        
        # Línea con fecha y cajero
        fecha_login_line = fecha_str + login
        
        # Comandos ESC/POS iniciales
        comandos = '\x1B@'  # Inicializar impresora
        comandos += '\x1B\x61\x01'  # Centrado
        comandos += '\x1D\x21\x11'  # Doble ancho y alto
        comandos += 'RECIBO DE ABONO\n'
        comandos += '\x1D\x21\x00'  # Tamaño normal
        
        # Cabecera
        sucursal = config.BUSINESS_NAME
        comandos += f'\x1B@\x1B\x61\x01\x1D\x54\x1C\x70\x01\x33\x1B\x21\x08{sucursal}\x1B!\x01\x1B\x21\x00\x0A\x0D'
        comandos += '------------------------------------------------\x0A\x0D'
        
        # Información básica
        comandos += '\x1B\x61\x00'  # Alineación izquierda
        comandos += f'{fecha_login_line}\x0A\x0D'
        comandos += f'TASA CAMBIO $ = Bs {dolar.valor:.2f}\x0A\x0D'
        comandos += f'CLIENTE: {cliente.nombre}\x0A\x0D'
        comandos += f'CEDULA: {cliente.cedula}\x0A\x0D'
        comandos += f'TELEFONO: {cliente.telefono}\x0A\x0D'
        comandos += '------------------------------------------------\x0A\x0D'
        
        # Información del abono
        comandos += '\x1B\x61\x01'  # Centrado
        comandos += '\x1B\x45\x01'  # Negrita activada
        comandos += 'DETALLE DEL ABONO\n'
        comandos += '\x1B\x45\x00'  # Negrita desactivada
        
        # Tabla de métodos de pago
        comandos += '\x1B\x61\x00'  # Alineación izquierda
        comandos += '\nMETODOS DE PAGO:\n'
        comandos += '------------------------------------------------\x0A\x0D'
        
        total_abono_dolares = 0
        
        for abono in abonos:
            metodo = abono['metodo']
            cantidad = abono['cantidad']
            
            if metodo == 'Efectivo ($)':
                monto_dolares = cantidad
                comandos += f'{metodo}: ${cantidad:.2f}\n'
            elif metodo == 'Efectivo (Bs)':
                monto_dolares = cantidad / dolar.valor
                comandos += f'{metodo}: Bs.{cantidad:.2f} (${monto_dolares:.2f})\n'
            elif metodo == 'Débito':
                monto_dolares = cantidad / dolar.valor
                comandos += f'{metodo}: Bs.{cantidad:.2f} (${monto_dolares:.2f})\n'
            elif metodo == 'Pago Móvil':
                monto_dolares = cantidad / dolar.valor
                comandos += f'{metodo}: Bs.{cantidad:.2f} (${monto_dolares:.2f})\n'
            
            total_abono_dolares += monto_dolares
            
        comandos += '------------------------------------------------\x0A\x0D'
        
        # Resumen de montos
        comandos += '\x1B\x61\x01'  # Centrado
        comandos += '\x1B\x45\x01'  # Negrita activada
        comandos += '\nRESUMEN\n'
        comandos += '\x1B\x45\x00'  # Negrita desactivada
        
        # Texto más grande para las líneas principales
        comandos += '\x1D\x21\x11'  # Tamaño de fuente doble altura y ancho
        comandos += f'Deuda Anterior: ${deuda_total:.2f}\n'
        comandos += '\x1D\x21\x00'  # Restaurar tamaño normal
        comandos += '\n'  # Salto de línea adicional
        
        comandos += '\x1D\x21\x11'  # Tamaño de fuente doble altura y ancho
        comandos += f'Total Abonado: ${abono_total:.2f}\n'
        comandos += '\x1D\x21\x00'  # Restaurar tamaño normal
        comandos += '\n'  # Salto de línea adicional
        
        # Estado de la deuda
        if deuda_restante > 0:
            comandos += '\x1D\x21\x11'  # Tamaño de fuente doble altura y ancho
            comandos += f'Deuda Restante: ${deuda_restante:.2f}\n'
            comandos += '\x1D\x21\x00'  # Restaurar tamaño normal
        elif deuda_restante < 0:
            comandos += f'Saldo a Favor: ${abs(deuda_restante):.2f}\n'

        else:
            comandos += 'Deuda Saldada Completamente\n'
        
        # Pie de página sin código de barras
        comandos += '\x1B\x61\x01'  # Centrado
        comandos += '\n\nGracias por su abono!\n\n'
        
        # Corte de papel y finalización
        comandos += '\x0A\x0A\x0A\x0A\x0A\x0A\x1B\x69'
        
        # Enviar a la impresora usando la función helper
        success, result, error_msg = conectar_socket_seguro(
            ip=impresora, 
            puerto=9100, 
            datos=comandos, 
            timeout=2,  # Timeout optimizado para impresoras
            es_balanza=False
        )
        
        if success:
            print(f"Ticket de abono detallado impreso exitosamente en impresora {impresora}")
            return "SUCCESS"
        else:
            return "ERROR"
        
    except Exception as e:
        print(f"Error al generar ticket de abono detallado: {str(e)}")
        return "ERROR"

class PagoMovilListView(ADMIN_SUPERVISOR_AUTH, LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        pagos_moviles = PagoMovil.objects.all().order_by('-fecha')
        context = {
            'pagos_moviles': pagos_moviles
        }
        return render(request, 'pos/pagos_moviles_list.html', context)
    
    def post(self, request, *args, **kwargs):
        # Procesar filtros
        filtros = {}
        
        if 'fecha_desde' in request.POST and request.POST['fecha_desde']:
            fecha_desde = datetime.strptime(request.POST['fecha_desde'], '%Y-%m-%d')
            filtros['fecha__gte'] = fecha_desde
            
        if 'fecha_hasta' in request.POST and request.POST['fecha_hasta']:
            fecha_hasta = datetime.strptime(request.POST['fecha_hasta'], '%Y-%m-%d')
            fecha_hasta = fecha_hasta.replace(hour=23, minute=59, second=59)
            filtros['fecha__lte'] = fecha_hasta
            
        if 'referencia' in request.POST and request.POST['referencia']:
            filtros['referencia__icontains'] = request.POST['referencia']
            
        if 'telefono' in request.POST and request.POST['telefono']:
            filtros['telefono__icontains'] = request.POST['telefono']
            
        if 'cliente' in request.POST and request.POST['cliente']:
            filtros['cliente__icontains'] = request.POST['cliente']
            
        if 'verificado' in request.POST:
            if request.POST['verificado'] == 'verificados':
                filtros['verificado'] = True
            elif request.POST['verificado'] == 'no_verificados':
                filtros['verificado'] = False
                
        # Aplicar filtros
        pagos_moviles = PagoMovil.objects.filter(**filtros).order_by('-fecha')
        
        # Convertir a formato JSON
        pagos_moviles_json = []
        for pago in pagos_moviles:
            pago_json = {
                'id': pago.id,
                'referencia': pago.referencia,
                'monto': pago.monto,
                'fecha': pago.fecha.strftime("%d-%m-%Y %H:%M"),
                'telefono': pago.telefono,
                'cliente': pago.cliente or 'N/A',
                'cajero': pago.cajero,
                'pedido_id': pago.pedido_id,
                'verificado': pago.verificado
            }
            pagos_moviles_json.append(pago_json)
            
        return JsonResponse(pagos_moviles_json, safe=False)

class VerificarPagoMovil(ADMIN_SUPERVISOR_AUTH, LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        pago_id = request.POST.get('pago_id')
        
        try:
            pago = PagoMovil.objects.get(pk=pago_id)
            pago.verificado = True
            pago.save()
            return JsonResponse({'success': True})
        except PagoMovil.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Pago móvil no encontrado'})

class CancelarAbono(View):
    def post(self, request):
        # Obtener la contraseña del supervisor
        password = request.POST.get('password')
        
        if not password:
            return JsonResponse({
                'success': False, 
                'error': 'Contraseña requerida'
            })
        
        # Buscar usuarios que sean supervisores o administradores
        usuarios_autorizados = User.objects.filter(
            groups__name__in=['SUPERVISOR', 'ADMINISTRADOR']
        )
        
        # Verificar la contraseña contra las contraseñas de usuarios autorizados
        autorizado = False
        usuario_autorizador = None
        for usuario in usuarios_autorizados:
            if check_password(password, usuario.password):
                autorizado = True
                usuario_autorizador = usuario.username
                break
        
        if not autorizado:
            return JsonResponse({
                'success': False, 
                'error': 'Contraseña de supervisor incorrecta'
            })
        
        # Obtener el ID del abono
        abono_id = request.POST.get('abono_id')
        
        if not abono_id:
            return JsonResponse({
                'success': False, 
                'error': 'ID de abono requerido'
            })
        
        try:
            # Buscar el abono
            abono = CreditoAbono.objects.get(id=abono_id)
            
            # TODO: Verificar que el abono no esté ya cancelado si se agrega campo
            # if hasattr(abono, 'cancelado') and abono.cancelado:
            #     return JsonResponse({
            #         'success': False, 
            #         'error': 'El abono ya está cancelado'
            #     })
            
            # Revertir el abono en el crédito
            try:
                credito = Credito.objects.get(id=abono.credito_id)
                credito.abonado -= abono.monto
                if credito.abonado < credito.monto_credito:
                    credito.estado = 'Pendiente'
                credito.save()
                
                # Revertir el crédito del cliente si es necesario
                cliente = Cliente.objects.get(cedula=credito.cliente_id)
                if cliente.credito >= abono.monto:
                    cliente.credito -= abono.monto
                    cliente.save()
                
            except (Credito.DoesNotExist, Cliente.DoesNotExist):
                pass
            
            # Eliminar el abono
            abono.delete()
            
            return JsonResponse({
                'success': True, 
                'message': f'Abono cancelado exitosamente por {usuario_autorizador}'
            })
            
        except CreditoAbono.DoesNotExist:
            return JsonResponse({
                'success': False, 
                'error': 'Abono no encontrado'
            })
        except Exception as e:
            return JsonResponse({
                'success': False, 
                'error': f'Error al cancelar abono: {str(e)}'
            })

class CierresCajaListView(LoginRequiredMixin, ADMIN_AUTH, ListView):
    model = estadoCaja
    template_name = 'cierres_caja.html'
    context_object_name = 'cierres'

    def get_queryset(self):
        # Mostrar todos los registros por defecto
        queryset = estadoCaja.objects.all().order_by('-fechaInicio')
        
        for cierre in queryset:
            # Calcular totales USD
            cierre.dinero_inicial_usd = sum(float(k) * float(v) for k, v in cierre.dineroInicio.get('USD', {}).items())
            cierre.dinero_final_usd = sum(float(k) * float(v) for k, v in (cierre.dineroFinal or {}).get('USD', {}).items())
            cierre.diferencia_usd = cierre.dinero_final_usd - cierre.dinero_inicial_usd
            
            # Calcular totales BS
            cierre.dinero_inicial_bs = sum(float(k) * float(v) for k, v in cierre.dineroInicio.get('BS', {}).items())
            cierre.dinero_final_bs = sum(float(k) * float(v) for k, v in (cierre.dineroFinal or {}).get('BS', {}).items())
            cierre.diferencia_bs = cierre.dinero_final_bs - cierre.dinero_inicial_bs
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['usuarios'] = User.objects.all()
        return context

class FiltrarCierresCaja(LoginRequiredMixin, ADMIN_AUTH, View):
    def post(self, request):
        id_cierre = request.POST.get('id_cierre')
        fecha_inicio = request.POST.get('fecha_inicio')
        fecha_fin = request.POST.get('fecha_fin')
        usuario = request.POST.get('usuario')
        estado = request.POST.get('estado')

        queryset = estadoCaja.objects.all()
        
        # Filtrar por ID
        if id_cierre:
            queryset = queryset.filter(id=id_cierre)

        # Filtrar por estado
        if estado == 'abierta':
            queryset = queryset.filter(fechaFin__isnull=True)
        elif estado == 'cerrada':
            queryset = queryset.filter(fechaFin__isnull=False)

        # Aplicar otros filtros
        if fecha_inicio:
            queryset = queryset.filter(fechaInicio__gte=fecha_inicio)
        if fecha_fin:
            queryset = queryset.filter(fechaInicio__lte=fecha_fin)
        if usuario:
            queryset = queryset.filter(usuario_id=usuario)

        # Ordenar por fecha de inicio descendente
        queryset = queryset.order_by('-fechaInicio')

        for cierre in queryset:
            # Calcular totales USD
            cierre.dinero_inicial_usd = sum(float(k) * float(v) for k, v in cierre.dineroInicio.get('USD', {}).items())
            cierre.dinero_final_usd = sum(float(k) * float(v) for k, v in (cierre.dineroFinal or {}).get('USD', {}).items())
            cierre.diferencia_usd = cierre.dinero_final_usd - cierre.dinero_inicial_usd
            
            # Calcular totales BS
            cierre.dinero_inicial_bs = sum(float(k) * float(v) for k, v in cierre.dineroInicio.get('BS', {}).items())
            cierre.dinero_final_bs = sum(float(k) * float(v) for k, v in (cierre.dineroFinal or {}).get('BS', {}).items())
            cierre.diferencia_bs = cierre.dinero_final_bs - cierre.dinero_inicial_bs

        html = render_to_string('cierres_caja_tabla.html', {'cierres': queryset})
        return JsonResponse({'html': html})
    
class DetalleCierreCaja(LoginRequiredMixin, ADMIN_AUTH, View):
    def get(self, request, pk):
        cierre = get_object_or_404(estadoCaja, pk=pk)
        
        # Calcular totales iniciales
        totales = {
            'inicial_usd': sum(float(k) * float(v) for k, v in cierre.dineroInicio.get('USD', {}).items()),
            'inicial_bs': sum(float(k) * float(v) for k, v in cierre.dineroInicio.get('BS', {}).items()),
        }
        
        # Obtener abonos de créditos del cierre específico
        abonos_creditos = CreditoAbono.objects.filter(
            cierre_caja=cierre
        ).order_by('fecha')
        
        # Calcular totales de abonos de créditos por método de pago
        abonos_totales = {
            'efectivo_usd': 0,
            'efectivo_bs': 0,
            'debito': 0,
            'pagomovil': 0,
            'total_usd': 0,
            'total_bs': 0
        }
        
        # Calcular denominaciones específicas de abonos de créditos
        abonos_denominaciones_usd = {}
        abonos_denominaciones_bs = {}
        abonos_egresos_usd = {}
        abonos_egresos_bs = {}
        
        # Preparar datos detallados de abonos para mostrar en tabla
        abonos_detalle = []
        
        for abono in abonos_creditos:
            # Obtener información del crédito y cliente
            try:
                credito = Credito.objects.get(id=abono.credito_id)
                cliente_nombre = credito.cliente
            except:
                cliente_nombre = "Cliente no encontrado"
            
            # Calcular totales por método de pago
            if abono.metodo_pago == 'Efectivo ($)':
                abonos_totales['efectivo_usd'] += abono.monto
                abonos_totales['total_usd'] += abono.monto
                
                # Acumular denominaciones de ingresos
                if abono.denominaciones:
                    for denom, cantidad in abono.denominaciones.items():
                        if cantidad > 0:
                            abonos_denominaciones_usd[str(denom)] = abonos_denominaciones_usd.get(str(denom), 0) + cantidad
                
                # Acumular denominaciones de egresos (vuelto)
                if abono.vuelto and 'USD' in abono.vuelto:
                    for denom, cantidad in abono.vuelto['USD'].items():
                        if cantidad > 0:
                            abonos_egresos_usd[str(denom)] = abonos_egresos_usd.get(str(denom), 0) + cantidad
                            
            elif abono.metodo_pago == 'Efectivo (Bs)':
                abonos_totales['efectivo_bs'] += abono.monto_neto or abono.monto
                # Convertir a USD para el total
                dolar = ValorDolar.objects.get(pk=1)
                abonos_totales['total_usd'] += abono.monto
                
                # Acumular denominaciones de ingresos
                if abono.denominaciones:
                    for denom, cantidad in abono.denominaciones.items():
                        if cantidad > 0:
                            abonos_denominaciones_bs[str(denom)] = abonos_denominaciones_bs.get(str(denom), 0) + cantidad
                
                # Acumular denominaciones de egresos (vuelto)
                if abono.vuelto and 'BS' in abono.vuelto:
                    for denom, cantidad in abono.vuelto['BS'].items():
                        if cantidad > 0:
                            abonos_egresos_bs[str(denom)] = abonos_egresos_bs.get(str(denom), 0) + cantidad
                            
            elif abono.metodo_pago == 'Débito':
                abonos_totales['debito'] += abono.monto_neto or abono.monto
                abonos_totales['total_usd'] += abono.monto
            elif abono.metodo_pago == 'Pago Móvil':
                abonos_totales['pagomovil'] += abono.monto_neto or abono.monto
                abonos_totales['total_usd'] += abono.monto
            
            # Agregar detalle para la tabla
            abonos_detalle.append({
                'cliente': cliente_nombre,
                'monto_usd': abono.monto,
                'metodo_pago': abono.metodo_pago,
                'monto_neto': abono.monto_neto or abono.monto,
                'fecha': abono.fecha,
                'denominaciones': abono.denominaciones,
                'vuelto': abono.vuelto
            })
        
        # Calcular totales de movimientos EXCLUYENDO los abonos de créditos
        dinero_esperado = cierre.dineroEsperado or {
            'ingresos': {'USD': {}, 'BS': {}, 'DEBITO': 0, 'CREDITO': 0, 'PAGOMOVIL': 0},
            'egresos': {'USD': {}, 'BS': {}}
        }
        
        # Calcular ingresos de efectivo RESTANDO los abonos de créditos
        ingresos_usd_pedidos = 0
        ingresos_bs_pedidos = 0
        
        # Ingresos USD (restando denominaciones de abonos)
        for denom, cantidad in dinero_esperado['ingresos'].get('USD', {}).items():
            cantidad_abonos = abonos_denominaciones_usd.get(str(denom), 0)
            cantidad_neta = cantidad - cantidad_abonos
            if cantidad_neta > 0:
                ingresos_usd_pedidos += float(denom) * cantidad_neta
        
        # Ingresos BS (restando denominaciones de abonos)
        for denom, cantidad in dinero_esperado['ingresos'].get('BS', {}).items():
            cantidad_abonos = abonos_denominaciones_bs.get(str(denom), 0)
            cantidad_neta = cantidad - cantidad_abonos
            if cantidad_neta > 0:
                ingresos_bs_pedidos += float(denom) * cantidad_neta
        
        # Calcular egresos RESTANDO los abonos de créditos
        egresos_usd_pedidos = 0
        egresos_bs_pedidos = 0
        
        # Egresos USD (restando vuelto de abonos)
        for denom, cantidad in dinero_esperado['egresos'].get('USD', {}).items():
            cantidad_abonos = abonos_egresos_usd.get(str(denom), 0)
            cantidad_neta = cantidad - cantidad_abonos
            if cantidad_neta > 0:
                egresos_usd_pedidos += float(denom) * cantidad_neta
        
        # Egresos BS (restando vuelto de abonos)
        for denom, cantidad in dinero_esperado['egresos'].get('BS', {}).items():
            cantidad_abonos = abonos_egresos_bs.get(str(denom), 0)
            cantidad_neta = cantidad - cantidad_abonos
            if cantidad_neta > 0:
                egresos_bs_pedidos += float(denom) * cantidad_neta
        
        # Calcular débito y pago móvil RESTANDO los abonos de créditos
        debito_pedidos = dinero_esperado['ingresos'].get('DEBITO', 0) - abonos_totales['debito']
        pagomovil_pedidos = dinero_esperado['ingresos'].get('PAGOMOVIL', 0) - abonos_totales['pagomovil']
        
        totales.update({
            'ingresos_usd': ingresos_usd_pedidos,
            'ingresos_bs': ingresos_bs_pedidos,
            'egresos_usd': egresos_usd_pedidos,
            'egresos_bs': egresos_bs_pedidos,
            'debito': round(max(0, debito_pedidos), 2),
            'credito': round(dinero_esperado['ingresos'].get('CREDITO', 0), 2),
            'pagomovil': round(max(0, pagomovil_pedidos), 2),
        })
        
        # Calcular totales finales y subtotales
        dinero_final = cierre.dineroFinal or {'USD': {}, 'BS': {}}
        
        # Preparar listas de denominaciones con sus subtotales
        inicial_usd = [
            {'denominacion': k, 'cantidad': v, 'subtotal': float(k) * float(v)}
            for k, v in sorted(cierre.dineroInicio.get('USD', {}).items(), key=lambda x: float(x[0]), reverse=True)
        ]
        
        inicial_bs = [
            {'denominacion': k, 'cantidad': v, 'subtotal': float(k) * float(v)}
            for k, v in sorted(cierre.dineroInicio.get('BS', {}).items(), key=lambda x: float(x[0]), reverse=True)
        ]
        
        final_usd = [
            {'denominacion': k, 'cantidad': v, 'subtotal': float(k) * float(v)}
            for k, v in sorted(dinero_final.get('USD', {}).items(), key=lambda x: float(x[0]), reverse=True)
        ]
        
        final_bs = [
            {'denominacion': k, 'cantidad': v, 'subtotal': float(k) * float(v)}
            for k, v in sorted(dinero_final.get('BS', {}).items(), key=lambda x: float(x[0]), reverse=True)
        ]
        
        # Actualizar totales finales
        totales.update({
            'final_usd': sum(item['subtotal'] for item in final_usd),
            'final_bs': sum(item['subtotal'] for item in final_bs),
        })
        
        # Calcular diferencias (incluyendo abonos de créditos en el dinero esperado)
        # Usar el dinero esperado COMPLETO (incluye abonos) vs dinero final
        dinero_esperado_total_usd = (totales['inicial_usd'] + 
                                   sum(float(k) * float(v) for k, v in dinero_esperado['ingresos'].get('USD', {}).items()) -
                                   sum(float(k) * float(v) for k, v in dinero_esperado['egresos'].get('USD', {}).items()) +
                                   dinero_esperado['ingresos'].get('DEBITO', 0) * 0)  # Débito en Bs no afecta USD
        
        dinero_esperado_total_bs = (totales['inicial_bs'] + 
                                  sum(float(k) * float(v) for k, v in dinero_esperado['ingresos'].get('BS', {}).items()) -
                                  sum(float(k) * float(v) for k, v in dinero_esperado['egresos'].get('BS', {}).items()))
        
        totales['diferencia_usd'] = totales['final_usd'] - dinero_esperado_total_usd
        totales['diferencia_bs'] = totales['final_bs'] - dinero_esperado_total_bs

        context = {
            'cierre': cierre,
            'inicial_usd': inicial_usd,
            'inicial_bs': inicial_bs,
            'final_usd': final_usd,
            'final_bs': final_bs,
            'totales': totales,
            'abonos_creditos': abonos_detalle,
            'abonos_totales': abonos_totales,
            
            # Variables de totales necesarias para el template
            'inicial_total_usd': totales['inicial_usd'],
            'inicial_total_bs': totales['inicial_bs'],
            'final_total_usd': totales['final_usd'],
            'final_total_bs': totales['final_bs'],
            'total_ingresos_usd': totales['ingresos_usd'],
            'total_ingresos_bs': totales['ingresos_bs'],
            'total_egresos_usd': totales['egresos_usd'],
            'total_egresos_bs': totales['egresos_bs'],
            'esperado_total_usd': dinero_esperado_total_usd,
            'esperado_total_bs': dinero_esperado_total_bs,
            'diferencia_usd': totales['diferencia_usd'],
            'diferencia_bs': totales['diferencia_bs'],
            'debito': totales['debito'],
            'credito': totales['credito'],
            'pagomovil': totales['pagomovil'],
            
            # Agregar pedidos pendientes al momento del cierre
            'pedidos_pendientes': cierre.pedidos_pendientes or [],
            'pedidos_pendientes_total': sum(float(p.get('precio_total', 0)) for p in (cierre.pedidos_pendientes or [])),
        }
        
        # Debug: Verificar que los pedidos pendientes llegan al template
        print(f"DEBUG DetalleCierre: Cierre ID {pk}")
        print(f"DEBUG DetalleCierre: Pedidos pendientes: {cierre.pedidos_pendientes}")
        print(f"DEBUG DetalleCierre: Total pedidos: {len(cierre.pedidos_pendientes or [])}")
        
        return render(request, 'cierre_detalle.html', context)

    @staticmethod
    def migrar_abonos_sin_cierre():
        """
        Método para migrar abonos existentes que no tienen cierre_caja asignado.
        Asigna cada abono al cierre de caja correspondiente basado en la fecha del abono.
        """
        from .models import CreditoAbono, estadoCaja
        
        abonos_sin_cierre = CreditoAbono.objects.filter(cierre_caja__isnull=True)
        
        for abono in abonos_sin_cierre:
            # Buscar el cierre de caja que corresponde a la fecha del abono
            cierre_correspondiente = estadoCaja.objects.filter(
                fechaInicio__lte=abono.fecha,
                fechaFin__gte=abono.fecha
            ).first()
            
            if not cierre_correspondiente:
                # Si no hay cierre cerrado, buscar caja abierta
                cierre_correspondiente = estadoCaja.objects.filter(
                    fechaInicio__lte=abono.fecha,
                    fechaFin__isnull=True
                ).first()
            
            if cierre_correspondiente:
                abono.cierre_caja = cierre_correspondiente
                abono.save()
                print(f"Abono {abono.id} asignado al cierre {cierre_correspondiente.id}")
            else:
                print(f"No se encontró cierre para el abono {abono.id} del {abono.fecha}")
        
        print(f"Migración completada. {abonos_sin_cierre.count()} abonos procesados.")

class MarcarDevolucion(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        try:
            pedido_id = request.POST.get('pedido_id')
            codigo = request.POST.get('codigo')
            
            # Verificar que se proporcionen todos los datos
            if not pedido_id or not codigo:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Faltan datos para la autorización'
                })
            
            # Obtener el pedido
            pedido = Pedido.objects.get(pk=pedido_id)
            
            # Verificar que el pedido esté en estado "Por pagar"
            if pedido.status != 'Por pagar':
                return JsonResponse({
                    'status': 'error',
                    'message': 'Solo se pueden marcar como devolución pedidos en estado "Por pagar"'
                })
            
            # Verificar autorización usando el mismo patrón que ValidarAutorizacionCredito
            from django.contrib.auth.hashers import check_password
            autorizado = False
            
            # Buscar usuarios que sean supervisores o administradores
            usuarios_autorizados = User.objects.filter(
                groups__name__in=['SUPERVISOR', 'ADMINISTRADOR']
            )
            
            # Verificar el código contra las contraseñas de usuarios autorizados
            for usuario in usuarios_autorizados:
                if check_password(codigo, usuario.password):
                    autorizado = True
                    break
            
            if not autorizado:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Código de autorización incorrecto'
                })
            
            # Marcar como devolución
            pedido.status = "Devolución"
            pedido.save()
            
            return JsonResponse({
                'status': 'success',
                'message': f'Pedido #{pedido_id} marcado como devolución exitosamente'
            })
            
        except Pedido.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'El pedido no existe'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'Error interno: {str(e)}'
            }, status=500)

def ImprimirEtiquetaPedido(pedido_id, pedido, productos, impresora):
    """
    Imprime etiqueta TSPL para pedido completo
    Incluye: número de pedido centrado y código de barras abajo (formato simplificado)
    """ 
    from datetime import datetime
    fecha_actual = datetime.now().strftime('%d/%m/%Y')
    hora_actual = datetime.now().strftime('%H:%M:%S')
    
    try:
        # Código de barras: "pp-" + id del pedido
        codigo_barras = f"pp-{pedido_id}"
        
        # Configuración de etiqueta TSPL (60mm x 30mm aprox) - más pequeña
        tspl_lines = [
            "SIZE 58 mm,32 mm",
            "GAP 2 mm,0",
            "DIRECTION 0",
            "DENSITY 8",
            "REFERENCE 0,0",
            "CLS",
            
            # Número de pedido centrado (parte superior)
            f'TEXT 86,120,"3",1,2,2,"#{pedido_id}"',
            
            # Código de barras centrado (parte inferior)
            f'BARCODE 120,200,"128",80,0,0,2,2,"{codigo_barras}"',

            #hora y fecha
            f'TEXT 50,20,"1",1,2,2,"{fecha_actual}"',
            f'TEXT 50,40,"1",1,2,2,"{hora_actual}"',
            
            # Imprimir
            "PRINT 1,1",
        ]
        
        comandos = "\r\n".join(tspl_lines) + "\r\n"
        
        # Debug
        print("\n" + "="*50)
        print(f"COMANDOS TSPL SIMPLIFICADOS PARA PEDIDO #{pedido_id}:")
        print("="*50)
        print(comandos)
        print("="*50)
        print(f"Código de barras: {codigo_barras}")
        print("="*50 + "\n")
        
        # Enviar a impresora TSPL
        success, result, error_msg = conectar_socket_seguro(
            ip=impresora,
            puerto=9100,  # Puerto estándar para impresoras
            datos=comandos,
            timeout=3,
            es_balanza=False
        )
        
        if success:
            print(f"✅ Etiqueta simplificada de pedido #{pedido_id} impresa exitosamente en impresora {impresora}")
            return "SUCCESS"
        else:
            print(f"❌ Error al imprimir etiqueta del pedido #{pedido_id}: {error_msg}")
            return "ERROR"
            
    except Exception as e:
        print(f"❌ Excepción en ImprimirEtiquetaPedido: {str(e)}")
        return "ERROR"

# Agregar después de la función imprimirTicket existente

def imprimir_ticket_async(pedido_id, impresora, modo_impresion='ticket'):
    """
    Función para imprimir ticket de forma asíncrona
    Compatible con django-rq o threading
    Soporta modo ticket (ESC/POS) y modo etiqueta (TSPL)
    """
    try:
        pedido = Pedido.objects.get(pk=pedido_id)
        productos = pedido.get_productos()
        
        # LÓGICA CONDICIONAL: Modo Ticket vs Modo Etiqueta
        if modo_impresion == 'etiqueta':
            # MODO ETIQUETA: Usar impresión TSPL
            resultado = ImprimirEtiquetaPedido(
                pedido_id=pedido_id,
                pedido=pedido,
                productos=productos,
                impresora=impresora
            )
        else:
            # MODO TICKET: Usar impresión ESC/POS (comportamiento actual)
            resultado = imprimirTicket(
                id=pedido_id,
                productos=productos,
                pedido=pedido,
                usuario=pedido.usuario or "-",
                pesador=pedido.pesador or "-",
                impresora=impresora,
                reimprimir=False
            )
        
        return resultado == "SUCCESS"
        
    except Exception as e:
        print(f"Error en impresión asíncrona: {e}")
        return False

class GuardarPedidoRapido(View):
    """
    Versión optimizada que separa creación de pedido de impresión
    """
    def post(self, request, *args, **kwargs):
        try:
            # Usar el mismo código optimizado pero sin impresión síncrona
            pedido = request.POST.copy()
            pedido_json = json.loads(pedido['pedidoJSON'])
            pedido_id = pedido['pedido_id']
            precio_total = pedido['precioT']
            cliente = pedido['cliente']
            usuario = pedido['usuario']
            impresora = pedido['impresora']
            modo_impresion = pedido.get('modoImpresion', 'ticket')  # OBTENER MODO DE IMPRESIÓN
            
            # Validaciones básicas
            if not pedido_json:
                return JsonResponse({
                    "success": False,
                    "error": "No hay productos en el pedido",
                    "message": "El pedido no puede estar vacío"
                }, status=400)
            
            if not usuario:
                return JsonResponse({
                    "success": False,
                    "error": "Usuario no especificado",
                    "message": "Se requiere un usuario válido"
                }, status=400)
            
            # Pre-cargar productos (mantenemos optimización)
            producto_ids = [x['id'] for x in pedido_json]
            productos_data = {}
            if producto_ids:
                productos_queryset = Producto.objects.filter(id__in=producto_ids).only('id', 'nombre', 'unidad', 'moneda')
                productos_data = {producto.id: producto for producto in productos_queryset}
            
            # Determinar si existe pedido
            if pedido_id != 'nuevo': 
                pedido_existe = Pedido.objects.filter(pk=pedido_id).exists()
            else: 
                pedido_existe = False
            
            # Crear/actualizar pedido (rápido)
            if pedido_existe:
                pedidoExistente = Pedido.objects.get(pk=pedido_id)
                productos_borrar = pedidoExistente.get_productos()
                productos_borrar.delete()
                pedidoExistente.precio_total = precio_total
                
                # Bulk create productos
                productos_pedido_list = []
                for x in pedido_json:
                    producto_info = productos_data.get(x['id'])
                    if producto_info:
                        productos_pedido_list.append(ProductosPedido(
                            producto=x['id'],
                            cantidad=float(x['cantidad']),
                            precio=float(x['precio']),
                            unidad=producto_info.unidad,
                            producto_nombre=producto_info.nombre,
                            moneda=producto_info.moneda
                        ))
                
                if productos_pedido_list:
                    productos_creados = ProductosPedido.objects.bulk_create(productos_pedido_list)
                    pedidoExistente.productos.set(productos_creados)
                
                pedidoExistente.save()
                pedido_final = pedidoExistente
            else:
                pedido_nuevo = Pedido(status='Por pagar', precio_total=precio_total, cliente=cliente)
                pedido_nuevo.save()
                pedido_id = pedido_nuevo.id
                
                # Bulk create productos
                productos_pedido_list = []
                for x in pedido_json:
                    producto_info = productos_data.get(x['id'])
                    if producto_info:
                        productos_pedido_list.append(ProductosPedido(
                            producto=x['id'],
                            cantidad=float(x['cantidad']),
                            precio=float(x['precio']),
                            unidad=producto_info.unidad,
                            producto_nombre=producto_info.nombre,
                            moneda=producto_info.moneda
                        ))
                
                if productos_pedido_list:
                    productos_creados = ProductosPedido.objects.bulk_create(productos_pedido_list)
                    pedido_nuevo.productos.set(productos_creados)
                
                pedido_nuevo.save()
                pedido_final = pedido_nuevo
            
            # Determinar tipo de usuario y flujo correspondiente
            try:
                usuario_objeto = User.objects.get(username=usuario)
                is_pesador = usuario_objeto.groups.filter(name="PESADOR").exists()
            except User.DoesNotExist:
                return JsonResponse({
                    "success": False,
                    "error": "Usuario no encontrado",
                    "message": f"El usuario '{usuario}' no existe"
                }, status=400)
            
            if is_pesador:
                # 🎯 PESADOR: Asignar pesador, imprimir asíncronamente, ir a POS
                pedido_final.pesador = usuario
                pedido_final.save()
                url_redireccion = reverse('pos:pos')
                
                # 🧹 LIMPIEZA MULTI-PESADOR: Eliminar pedido activo del pesador
                try:
                    from .models import PedidoActivo
                    deleted_count, _ = PedidoActivo.objects.filter(username_pesador=usuario).delete()
                    if deleted_count > 0:
                        print(f"✅ Pedido activo eliminado para pesador: {usuario}")
                except Exception as e:
                    print(f"⚠️ Error eliminando pedido activo: {str(e)}")
                    # No fallar el guardado por este error
                
                # 🖨️ IMPRESIÓN ASÍNCRONA: Solo para PESADORES
                import threading
                
                # 🔄 MULTI-PESADOR: Verificar si modo multi-pesador está activo para imprimir doble
                modo_multi_pesador_activo = False
                try:
                    # Verificar localStorage del frontend (se enviará como parámetro en futuras versiones)
                    # Por ahora, verificar si hay pesadores autorizados configurados
                    config_json = leer_configuracion()
                    modo_multi_pesador = request.POST.get('modo_multi_pesador', 'false').lower() == 'true'
                    if modo_multi_pesador:
                        modo_multi_pesador_activo = True
                        print(f"🔄 Modo multi-pesador detectado - impresión doble activada")
                except Exception as e:
                    print(f"⚠️ Error verificando modo multi-pesador: {str(e)}")
                    modo_multi_pesador_activo = False
                
                # Primera impresión (siempre)
                thread1 = threading.Thread(
                    target=imprimir_ticket_async, 
                    args=(pedido_id, impresora, modo_impresion)
                )
                thread1.daemon = True
                thread1.start()
                
                # Segunda impresión (solo si multi-pesador está activo)
                if modo_multi_pesador_activo:
                    print(f"🖨️ Iniciando segunda impresión para modo multi-pesador")
                    thread2 = threading.Thread(
                        target=imprimir_ticket_async, 
                        args=(pedido_id, impresora, modo_impresion)
                    )
                    thread2.daemon = True
                    thread2.start()
                
                return JsonResponse({
                    "success": True,
                    "saved": True,
                    "url": url_redireccion,
                    "pedido_id": pedido_id,
                    "mensaje": f"Pedido #{pedido_id} guardado correctamente. Imprimiendo en segundo plano...",
                    "is_pesador": True,
                    "impresion_async": True
                })
            else:
                # 💳 CAJERO/OTROS: Asignar usuario, ir directo a pantalla de pago
                pedido_final.usuario = usuario
                pedido_final.save()
                url_redireccion = reverse('pos:pago', args=[pedido_id])
                
                return JsonResponse({
                    "success": True,
                    "saved": True,
                    "url": url_redireccion,
                    "pedido_id": pedido_id,
                    "mensaje": f"Pedido #{pedido_id} guardado correctamente",
                    "is_pesador": False,
                    "impresion_async": False  # No hay impresión para no-PESADORES
                })
        
        except json.JSONDecodeError:
            return JsonResponse({
                "success": False,
                "error": "Error de formato",
                "message": "Los datos del pedido no tienen formato válido"
            }, status=400)
        
        except Exception as e:
            # Log del error para debugging
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error guardando pedido: {str(e)}")
            
            return JsonResponse({
                "success": False,
                "error": "Error interno del servidor",
                "message": "No se pudo guardar el pedido. Inténtalo nuevamente."
            }, status=500)

class VerificarImpresion(View):
    """
    Vista simple para verificar si se puede imprimir (sin jobs complejos)
    """
    def get(self, request, pedido_id):
        try:
            pedido = Pedido.objects.get(pk=pedido_id)
            # Verificar si tiene pesador asignado (indica que se procesó)
            return JsonResponse({
                "procesado": bool(pedido.pesador),
                "status": pedido.status,
                "mensaje": "Ticket procesado" if pedido.pesador else "Procesando..."
            })
        except Pedido.DoesNotExist:
            return JsonResponse({"error": "Pedido no encontrado"}, status=404)

class ReimprimirTicketRapido(View):
    """
    Vista optimizada para reimpresión no-bloqueante de tickets
    Aplica las mismas mejoras de rendimiento que GuardarPedidoRapido
    """
    def post(self, request, *args, **kwargs):
        try:
            pedido_id = request.POST.get('pedido_id')
            impresora = request.POST.get('impresora', '')
            
            if not pedido_id:
                return JsonResponse({
                    'success': False,
                    'message': 'ID de pedido requerido'
                }, status=400)
            
            # 🚀 OPTIMIZACIÓN: Obtener pedido con select_related para evitar queries N+1
            try:
                pedido = Pedido.objects.select_related().get(pk=pedido_id)
            except Pedido.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'message': f'Pedido #{pedido_id} no encontrado'
                }, status=404)
            
            # 🚀 OPTIMIZACIÓN: Pre-cargar productos en una sola query
            productos = pedido.get_productos()
            
            # 🚀 IMPRESIÓN ASÍNCRONA UNIVERSAL: Para todos los usuarios
            user_groups = [group.name for group in request.user.groups.all()]
            is_pesador = 'PESADOR' in user_groups
            
            def imprimir_reimpresion_async():
                try:
                    # Obtener dólar histórico si el pedido está pagado
                    dolar_historico = None
                    if pedido.status in ['Pagado', 'Pagado con Crédito'] and pedido.dolar_al_pagar:
                        dolar_historico = pedido.dolar_al_pagar
                    
                    resultado = imprimirTicket(
                        id=pedido_id,
                        productos=productos,
                        pedido=pedido,
                        usuario=pedido.usuario or "",
                        pesador=pedido.pesador or "",
                        impresora=impresora,
                        reimprimir=True,
                        dolar_historico=dolar_historico
                    )
                    
                    print(f"🖨️ Reimpresión asíncrona completada para pedido #{pedido_id}: {resultado}")
                    
                except Exception as e:
                    print(f"❌ Error en reimpresión asíncrona del pedido #{pedido_id}: {str(e)}")
            
            # 🚀 EJECUTAR IMPRESIÓN ASÍNCRONA: Para TODOS los usuarios
            import threading
            thread_impresion = threading.Thread(target=imprimir_reimpresion_async)
            thread_impresion.daemon = True
            thread_impresion.start()
            
            # Determinar URL de redirección según tipo de usuario
            if is_pesador:
                url_redireccion = '/pos/'
                usuario_tipo = 'PESADOR'
            else:
                url_redireccion = '/pos/'
                usuario_tipo = 'CAJERO'
            
            return JsonResponse({
                'success': True,
                'impresion_async': True,  # Siempre true ahora
                'pedido_id': pedido_id,
                'mensaje': 'Imprimiendo ticket en segundo plano...',
                'usuario_tipo': usuario_tipo,
                'is_pesador': is_pesador,
                'url': url_redireccion
            })
        
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error interno: {str(e)}'
            }, status=500)


class PagarPedidoRapido(View):
    """
    🚀 Vista optimizada para pagar pedidos con impresión asíncrona universal
    """
    def post(self, request, *args, **kwargs):
        pedido_id = kwargs['pedido']
        data = request.POST
        usuario = data['usuario']
        impresora = data['impresora']
        credito_usado = float(data['credito_usado'])
        pedido_modificado = data['pedido_modificado']
        
        try:
            # 🔒 VALIDACIÓN CRÍTICA: Obtener y verificar pedido
            try:
                pedido = Pedido.objects.get(pk=pedido_id)
            except Pedido.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': f'Pedido #{pedido_id} no encontrado'
                }, status=404)
            
            # 🔒 VALIDACIÓN CRÍTICA: Verificar que el pedido esté "Por Pagar"
            if pedido.status != "Por pagar":
                return JsonResponse({
                    'success': False,
                    'error': f'El pedido #{pedido_id} ya está {pedido.status}. No se puede procesar el pago.'
                }, status=400)
            
            # 🔒 VALIDACIÓN CRÍTICA: Verificar que la caja esté abierta
            try:
                caja_actual = estadoCaja.objects.get(
                    usuario=request.user,
                    fechaFin__isnull=True
                )
            except estadoCaja.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': 'Debe abrir la caja antes de procesar pagos'
                }, status=400)
            
            # 🔒 VALIDACIÓN: Verificar que hay productos en el pedido
            productos_pedido = pedido.get_productos()
            if not productos_pedido:
                return JsonResponse({
                    'success': False,
                    'error': f'El pedido #{pedido_id} no tiene productos'
                }, status=400)
            
            # Procesar movimientos de caja
            movimientos_caja = json.loads(data.get('movimientos_caja', '{}'))
            
            # Procesar pagos móviles si se proporcionan
            pagos_moviles_data = json.loads(data.get('pagos_moviles', '[]'))
            for pago_movil_data in pagos_moviles_data:
                pago_movil = PagoMovil(
                    referencia=pago_movil_data['referencia'],
                    monto=pago_movil_data['monto'],
                    telefono=pago_movil_data['telefono'],
                    cajero=usuario,
                    pedido_id=pedido_id,
                    verificado=False
                )
                
                # Si hay un cliente asociado al pedido, guardarlo
                if pedido.cliente != 0:
                    try:
                        cliente_obj = Cliente.objects.get(pk=pedido.cliente)
                        pago_movil.cliente = cliente_obj.nombre
                        pago_movil.cliente_id = cliente_obj.cedula
                    except Cliente.DoesNotExist:
                        pass
                
                pago_movil.save()

            # Actualizar inventario de productos
            for producto in productos_pedido:
                try:
                    producto_query = Producto.objects.get(id=producto.producto)
                except Producto.DoesNotExist:
                    # Si el producto no existe, continuar con el siguiente
                    # Esto puede pasar si un producto fue eliminado después de crear el pedido
                    print(f"Producto no encontrado: {producto.producto}")
                    continue
                
                if producto_query.subproducto == None:
                    producto_query.cantidad = producto_query.cantidad - float(producto.cantidad) 
                    producto_query.save()
                else:
                    try:
                        subproducto_query = Producto.objects.get(nombre=producto_query.subproducto)
                        subproducto_query.cantidad = subproducto_query.cantidad - float(producto.cantidad * producto_query.relacion_subproducto) 
                        subproducto_query.save()
                    except Producto.DoesNotExist:
                        # Si el subproducto no existe, solo actualizar el producto principal
                        producto_query.cantidad = producto_query.cantidad - float(producto.cantidad) 
                        producto_query.save()

            # Procesar crédito si se usó
            if credito_usado > 0:
                cliente = Cliente.objects.get(pk=pedido.cliente)
                cliente.credito = cliente.credito - credito_usado

                credito = Credito(
                    cliente=cliente.nombre,
                    cliente_id=cliente.cedula,
                    monto_credito=round(credito_usado, 2),
                    plazo_credito=cliente.credito_plazo,
                    fecha=timezone.now(),
                    fecha_vencimiento=timezone.now() + timedelta(days=cliente.credito_plazo),
                    abonado=0,
                    pedido_id=pedido_id,
                    estado="Pendiente"
                )
                credito.save()
                cliente.save()

            # Actualizar estado del pedido
            dolar_actual = ValorDolar.objects.get(pk=1)
            pedido.dolar_al_pagar = dolar_actual.valor
            
            # Asignar status según si se usó crédito o no
            if credito_usado > 0:
                pedido.status = "Pagado con Crédito"
            else:
                pedido.status = "Pagado"
                
            pedido.pagado_fecha = timezone.now()
            pedido.save()

            # ✅ NOTA: No eliminar pedido activo al pagar - se mantiene para que el pesador pueda continuar trabajando
            # El pedido activo se elimina solo cuando se guarda un nuevo pedido o se elimina manualmente

            # 💰 ACTUALIZAR DINERO ESPERADO EN CAJA (ya validada arriba)
            dinero_esperado = caja_actual.dineroEsperado or {
                'ingresos': {'USD': {}, 'BS': {}, 'DEBITO': 0, 'CREDITO': 0, 'PAGOMOVIL': 0},
                'egresos': {'USD': {}, 'BS': {}}
            }
            
            # Procesar ingresos y egresos de efectivo
            for tipo in ['ingresos', 'egresos']:
                for moneda in ['USD', 'BS']:
                    if moneda in movimientos_caja[tipo]:
                        for denom, cantidad in movimientos_caja[tipo][moneda].items():
                            if tipo not in dinero_esperado:
                                dinero_esperado[tipo] = {}
                            if moneda not in dinero_esperado[tipo]:
                                dinero_esperado[tipo][moneda] = {}
                            
                            denom_str = str(denom)
                            if denom_str not in dinero_esperado[tipo][moneda]:
                                dinero_esperado[tipo][moneda][denom_str] = 0
                            dinero_esperado[tipo][moneda][denom_str] += cantidad
            
            # Agregar métodos de pago electrónicos
            dinero_esperado['ingresos']['DEBITO'] = dinero_esperado['ingresos'].get('DEBITO', 0) + movimientos_caja['ingresos'].get('DEBITO', 0)
            dinero_esperado['ingresos']['CREDITO'] = dinero_esperado['ingresos'].get('CREDITO', 0) + movimientos_caja['ingresos'].get('CREDITO', 0)
            dinero_esperado['ingresos']['PAGOMOVIL'] = dinero_esperado['ingresos'].get('PAGOMOVIL', 0) + movimientos_caja['ingresos'].get('PAGOMOVIL', 0)
            
            # Guardar dinero esperado actualizado
            caja_actual.dineroEsperado = dinero_esperado
            caja_actual.save()

            # 🚀 IMPRESIÓN ASÍNCRONA UNIVERSAL: Para todos los usuarios
            should_print = (pedido_modificado == 'true' or credito_usado > 0)
            
            if should_print:
                def imprimir_pago_async():
                    try:
                        pesador = pedido.pesador
                        resultado = imprimirTicket(
                            id=pedido_id,
                            productos=productos_pedido,
                            pedido=pedido,
                            usuario=usuario,
                            pesador=pesador,
                            impresora=impresora,
                            reimprimir=False,
                            credito_usado=credito_usado
                        )
                        
                        print(f"🖨️ Impresión de pago asíncrona completada para pedido #{pedido_id}: {resultado}")
                        
                    except Exception as e:
                        print(f"❌ Error en impresión asíncrona del pago #{pedido_id}: {str(e)}")
                
                # Ejecutar impresión en thread separado
                import threading
                thread_impresion = threading.Thread(target=imprimir_pago_async)
                thread_impresion.daemon = True
                thread_impresion.start()

            return JsonResponse({
                'success': True,
                'pedido_id': pedido_id,
                'impresion_async': should_print,
                'mensaje': 'Pago procesado. Imprimiendo ticket en segundo plano...' if should_print else 'Pago procesado correctamente.',
                'status': pedido.status,
                'url': reverse('pos:pos')
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Error procesando el pago: {str(e)}'
            }, status=500)

class ProductAnalytics(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        """Vista principal de analíticas de productos"""
        from django.db.models import Count, Sum, Q
        
        # Métricas básicas de productos
        total_productos = Producto.objects.count()
        productos_con_stock = Producto.objects.filter(cantidad__gt=0).count()
        productos_sin_stock = Producto.objects.filter(Q(cantidad__isnull=True) | Q(cantidad=0)).count()
        productos_por_unidad = Producto.objects.filter(unidad='U').count()
        productos_por_kilo = Producto.objects.filter(unidad='K').count()
        
        # Calcular valor total del inventario (aproximado)
        valor_inventario_usd = 0
        valor_inventario_bs = 0
        
        productos_con_precio = Producto.objects.filter(
            Q(cantidad__gt=0) & 
            Q(precio_detal__gt=0)
        )
        
        for producto in productos_con_precio:
            if producto.moneda == 'USD':
                valor_inventario_usd += producto.cantidad * producto.precio_detal
            else:  # BS
                valor_inventario_bs += producto.cantidad * producto.precio_detal
        
        # Distribución por categorías
        categorias_distribucion = []
        categorias = CategoriasProductos.objects.all()
        for categoria in categorias:
            count = Producto.objects.filter(categoria=categoria).count()
            if count > 0:
                categorias_distribucion.append({
                    'nombre': categoria.nombre,
                    'cantidad': count
                })
        
        # Función para formatear números con separador de miles
        def format_number(number, decimals=0):
            if number is None:
                return "0"
            formatted = f"{number:,.{decimals}f}"
            return formatted.replace(",", ".")
        
        # Lista de productos para el selector de movimientos
        productos_lista = Producto.objects.all().order_by('nombre')
        
        context = {
            'total_productos': format_number(total_productos),
            'productos_con_stock': format_number(productos_con_stock),
            'productos_sin_stock': format_number(productos_sin_stock),
            'productos_por_unidad': format_number(productos_por_unidad),
            'productos_por_kilo': format_number(productos_por_kilo),
            'valor_inventario_usd': format_number(valor_inventario_usd, 2),
            'valor_inventario_bs': format_number(valor_inventario_bs, 2),
            'categorias_distribucion': categorias_distribucion,
            'productos_lista': productos_lista,
        }
        
        return render(request, 'productos_analytics.html', context)


# =============================================================================
# API ENDPOINTS PARA APLICACIÓN REACT NATIVE
# =============================================================================

from .serializers import CategoriaSerializer, ProductoSerializer
import json
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

class CategoriaListView(View):
    """
    API Endpoint: GET /api/categorias/
    Retorna todas las categorías disponibles ordenadas por campo 'orden'
    """
    
    def get(self, request):
        try:
            # Obtener todas las categorías ordenadas por campo orden
            categorias = CategoriasProductos.objects.all().order_by('orden')
            
            # Serializar categorías
            categorias_data = CategoriaSerializer.serialize_list(categorias)
            
            return JsonResponse(categorias_data, safe=False, json_dumps_params={'ensure_ascii': False})
            
        except Exception as e:
            return JsonResponse({
                'error': 'Error interno del servidor',
                'detail': str(e)
            }, status=500)


class ProductoListView(View):
    """
    API Endpoint: GET /api/productos/
    Retorna todos los productos disponibles ordenados alfabéticamente
    """
    
    def get(self, request):
        try:
            # Obtener todos los productos ordenados alfabéticamente por nombre
            productos = Producto.objects.all().order_by('nombre')
            
            # Serializar productos
            productos_data = ProductoSerializer.serialize_list(productos)
            
            return JsonResponse(productos_data, safe=False, json_dumps_params={'ensure_ascii': False})
            
        except Exception as e:
            return JsonResponse({
                'error': 'Error interno del servidor',
                'detail': str(e)
            }, status=500)


class ProductoDetailView(View):
    """
    API Endpoint: GET /api/productos/<id>/
    Retorna un producto específico por ID
    """
    
    def get(self, request, pk):
        try:
            # Obtener producto específico
            producto = get_object_or_404(Producto, pk=pk)
            
            # Serializar producto
            producto_data = ProductoSerializer.serialize(producto)
            
            return JsonResponse(producto_data, json_dumps_params={'ensure_ascii': False})
            
        except Producto.DoesNotExist:
            return JsonResponse({
                'error': 'Producto no encontrado',
                'detail': f'No se encontró un producto con ID {pk}'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'error': 'Error interno del servidor',
                'detail': str(e)
            }, status=500)



class CrearPedidoPesadorAPI(View):
    """
    API Endpoint: POST /api/pedidos/pesador/
    Crea un pedido específicamente para pesadores desde React Native
    
    Basado en la lógica de GuardarPedidoRapido pero optimizado para API
    """
    
    def post(self, request):
        try:
            # Parsear JSON del body
            try:
                body = json.loads(request.body)
            except json.JSONDecodeError:
                return JsonResponse({
                    "success": False,
                    "error": "JSON_DECODE_ERROR",
                    "message": "El cuerpo de la petición debe ser JSON válido"
                }, status=400)
            
            # Validar campos requeridos
            required_fields = ['productos', 'precio_total', 'usuario_pesador']
            for field in required_fields:
                if field not in body:
                    return JsonResponse({
                        "success": False,
                        "error": "MISSING_FIELD",
                        "message": f"El campo '{field}' es requerido"
                    }, status=400)
            
            productos_json = body['productos']
            precio_total = body['precio_total']
            usuario_pesador = body['usuario_pesador']
            cliente_id = body.get('cliente_id', 0)
            impresora_ip = body.get('impresora_ip', '')
            pedido_id = body.get('pedido_id', None)  # ID de pedido existente para actualizar
            
            # Validaciones básicas
            if not productos_json or len(productos_json) == 0:
                return JsonResponse({
                    "success": False,
                    "error": "EMPTY_ORDER",
                    "message": "El pedido debe contener al menos un producto"
                }, status=400)
            
            if not isinstance(precio_total, (int, float)) or precio_total <= 0:
                return JsonResponse({
                    "success": False,
                    "error": "INVALID_PRICE",
                    "message": "El precio total debe ser un número mayor a 0"
                }, status=400)
            
            # Verificar que el usuario existe y es pesador
            try:
                usuario_objeto = User.objects.get(username=usuario_pesador)
                is_pesador = usuario_objeto.groups.filter(name="PESADOR").exists()
                
                if not is_pesador:
                    return JsonResponse({
                        "success": False,
                        "error": "UNAUTHORIZED_USER",
                        "message": "El usuario no tiene permisos de pesador"
                    }, status=403)
                    
            except User.DoesNotExist:
                return JsonResponse({
                    "success": False,
                    "error": "USER_NOT_FOUND",
                    "message": f"El usuario '{usuario_pesador}' no existe"
                }, status=404)
            
            # Pre-cargar productos para optimización
            producto_ids = []
            for producto in productos_json:
                if 'id' in producto:
                    producto_ids.append(producto['id'])
                else:
                    return JsonResponse({
                        "success": False,
                        "error": "INVALID_PRODUCT",
                        "message": "Todos los productos deben tener un ID válido"
                    }, status=400)
            
            productos_data = {}
            if producto_ids:
                productos_queryset = Producto.objects.filter(id__in=producto_ids).only('id', 'nombre', 'unidad', 'moneda')
                productos_data = {producto.id: producto for producto in productos_queryset}
                
                # Verificar que todos los productos existen
                for pid in producto_ids:
                    if pid not in productos_data:
                        return JsonResponse({
                            "success": False,
                            "error": "PRODUCT_NOT_FOUND",
                            "message": f"El producto con ID {pid} no existe"
                        }, status=404)
            
            # Determinar si crear nuevo pedido o actualizar existente
            if pedido_id:
                # ACTUALIZAR PEDIDO EXISTENTE
                try:
                    pedido_existente = Pedido.objects.get(pk=pedido_id)
                    
                    # Verificar que el pedido esté "Por pagar"
                    if pedido_existente.status != 'Por pagar':
                        return JsonResponse({
                            "success": False,
                            "error": "INVALID_ORDER_STATUS",
                            "message": f"El pedido #{pedido_id} no puede ser modificado. Estado actual: {pedido_existente.status}"
                        }, status=400)
                    
                    # Verificar que el pesador sea el mismo o tenga permisos
                    if pedido_existente.pesador != usuario_pesador:
                        return JsonResponse({
                            "success": False,
                            "error": "UNAUTHORIZED_MODIFICATION",
                            "message": f"El pedido #{pedido_id} fue creado por otro pesador ({pedido_existente.pesador})"
                        }, status=403)
                    
                    # Eliminar productos existentes del pedido
                    productos_anteriores = pedido_existente.productos.all()
                    productos_anteriores.delete()
                    
                    # Actualizar información básica del pedido
                    pedido_existente.precio_total = float(precio_total)
                    pedido_existente.cliente = cliente_id
                    pedido_existente.save()
                    
                    pedido_final = pedido_existente
                    es_actualizacion = True
                    
                except Pedido.DoesNotExist:
                    return JsonResponse({
                        "success": False,
                        "error": "ORDER_NOT_FOUND",
                        "message": f"No se encontró un pedido con ID {pedido_id}"
                    }, status=404)
            else:
                # CREAR NUEVO PEDIDO
                pedido_nuevo = Pedido(
                    status='Por pagar',
                    precio_total=float(precio_total),
                    cliente=cliente_id,
                    pesador=usuario_pesador  # Asignar directamente como pesador
                )
                pedido_nuevo.save()
                pedido_final = pedido_nuevo
                es_actualizacion = False
            
            # Crear productos del pedido usando bulk_create para optimización
            productos_pedido_list = []
            for producto_data in productos_json:
                producto_id = producto_data['id']
                cantidad = producto_data.get('cantidad', 1)
                precio = producto_data.get('precio', 0)
                
                # Validar datos del producto
                if not isinstance(cantidad, (int, float)) or cantidad <= 0:
                    return JsonResponse({
                        "success": False,
                        "error": "INVALID_QUANTITY",
                        "message": f"La cantidad del producto {producto_id} debe ser mayor a 0"
                    }, status=400)
                
                if not isinstance(precio, (int, float)) or precio < 0:
                    return JsonResponse({
                        "success": False,
                        "error": "INVALID_PRODUCT_PRICE",
                        "message": f"El precio del producto {producto_id} debe ser válido"
                    }, status=400)
                
                producto_info = productos_data[producto_id]
                productos_pedido_list.append(ProductosPedido(
                    producto=producto_id,
                    cantidad=float(cantidad),
                    precio=float(precio),
                    unidad=producto_info.unidad,
                    producto_nombre=producto_info.nombre,
                    moneda=producto_info.moneda
                ))
            
            # Crear productos en bulk
            if productos_pedido_list:
                productos_creados = ProductosPedido.objects.bulk_create(productos_pedido_list)
                pedido_final.productos.set(productos_creados)
                pedido_final.save()
            
            # Impresión asíncrona si se especifica impresora
            impresion_iniciada = False
            if impresora_ip and impresora_ip.strip():
                try:
                    import threading
                    thread = threading.Thread(
                        target=imprimir_ticket_async,
                        args=(pedido_final.id, impresora_ip)
                    )
                    thread.daemon = True
                    thread.start()
                    impresion_iniciada = True
                except Exception as e:
                    # Log error pero no fallar la creación del pedido
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f"Error iniciando impresión asíncrona: {str(e)}")
            
            # Respuesta exitosa
            accion = "actualizado" if es_actualizacion else "creado"
            status_code = 200 if es_actualizacion else 201
            
            return JsonResponse({
                "success": True,
                "pedido_id": pedido_final.id,
                "message": f"Pedido #{pedido_final.id} {accion} exitosamente para pesador {usuario_pesador}",
                "data": {
                    "pedido_id": pedido_final.id,
                    "precio_total": float(pedido_final.precio_total),
                    "status": pedido_final.status,
                    "usuario_pesador": usuario_pesador,
                    "cliente_id": cliente_id,
                    "productos_count": len(productos_pedido_list),
                    "impresion_iniciada": impresion_iniciada,
                    "fecha_creacion": pedido_final.fecha.isoformat() if pedido_final.fecha else None,
                    "es_actualizacion": es_actualizacion
                }
            }, status=status_code)
            
        except Exception as e:
            # Log del error para debugging
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error creando pedido para pesador: {str(e)}")
            
            return JsonResponse({
                "success": False,
                "error": "INTERNAL_SERVER_ERROR",
                "message": "Error interno del servidor. Contacte al administrador."
            }, status=500)


class ListarPedidosAPI(View):
    """
    API Endpoint: GET /api/pedidos/
    Retorna los últimos 30 pedidos con información básica para tabla
    """
    
    def get(self, request):
        try:
            # Obtener los últimos 30 pedidos ordenados por fecha descendente
            pedidos = Pedido.objects.select_related().prefetch_related('productos').order_by('-fecha')[:30]
            
            pedidos_data = []
            for pedido in pedidos:
                # Calcular cantidad total de productos
                productos_count = pedido.productos.count()
                
                # Obtener información del cliente si existe
                cliente_info = None
                if pedido.cliente and pedido.cliente != 0:
                    try:
                        cliente = Cliente.objects.get(id=pedido.cliente)
                        cliente_info = {
                            "id": cliente.id,
                            "nombre": cliente.nombre,
                            "cedula": cliente.cedula
                        }
                    except Cliente.DoesNotExist:
                        cliente_info = None
                
                pedido_data = {
                    "id": pedido.id,
                    "fecha": pedido.fecha.isoformat() if pedido.fecha else None,
                    "status": pedido.status,
                    "precio_total": float(pedido.precio_total) if pedido.precio_total else 0.0,
                    "cliente": cliente_info,
                    "usuario": pedido.usuario or "",
                    "pesador": pedido.pesador or "",
                    "productos_count": productos_count,
                    "notas": pedido.notas or "",
                    "fecha_pagado": pedido.pagado_fecha.isoformat() if pedido.pagado_fecha else None,
                    "fecha_despachado": pedido.despachado_fecha.isoformat() if pedido.despachado_fecha else None,
                    "dolar_al_pagar": float(pedido.dolar_al_pagar) if pedido.dolar_al_pagar else None
                }
                
                pedidos_data.append(pedido_data)
            
            return JsonResponse({
                "success": True,
                "count": len(pedidos_data),
                "data": pedidos_data
            }, json_dumps_params={'ensure_ascii': False})
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error obteniendo lista de pedidos: {str(e)}")
            
            return JsonResponse({
                "success": False,
                "error": "INTERNAL_SERVER_ERROR",
                "message": "Error interno del servidor al obtener pedidos."
            }, status=500)


class DetallePedidoAPI(View):
    """
    API Endpoint: GET /api/pedidos/<id>/
    Retorna información detallada de un pedido específico
    """
    
    def get(self, request, pk):
        try:
            # Obtener pedido específico con relaciones optimizadas
            try:
                pedido = Pedido.objects.select_related().prefetch_related(
                    'productos'
                ).get(pk=pk)
            except Pedido.DoesNotExist:
                return JsonResponse({
                    "success": False,
                    "error": "ORDER_NOT_FOUND",
                    "message": f"No se encontró un pedido con ID {pk}"
                }, status=404)
            
            # Obtener información del cliente si existe
            cliente_info = None
            if pedido.cliente and pedido.cliente != 0:
                try:
                    cliente = Cliente.objects.get(id=pedido.cliente)
                    cliente_info = {
                        "id": cliente.id,
                        "nombre": cliente.nombre,
                        "cedula": cliente.cedula,
                        "telefono": cliente.telefono,
                        "zona_vive": cliente.zona_vive,
                        "credito": cliente.credito,
                        "credito_maximo": cliente.credito_maximo
                    }
                except Cliente.DoesNotExist:
                    cliente_info = None
            
            # Obtener productos del pedido con detalles
            productos_pedido = pedido.productos.all()
            productos_data = []
            
            for producto_pedido in productos_pedido:
                # Obtener información completa del producto si existe
                producto_info = None
                if producto_pedido.producto:
                    try:
                        producto = Producto.objects.get(id=producto_pedido.producto)
                        producto_info = {
                            "id": producto.id,
                            "nombre": producto.nombre,
                            "imagen": producto.imagen,
                            "barcode": producto.barcode,
                            "categoria_nombres": [cat.nombre for cat in producto.categoria.all()]
                        }
                    except Producto.DoesNotExist:
                        producto_info = None
                
                producto_data = {
                    "id": producto_pedido.id,
                    "producto_id": producto_pedido.producto,
                    "producto_nombre": producto_pedido.producto_nombre,
                    "cantidad": float(producto_pedido.cantidad) if producto_pedido.cantidad else 0.0,
                    "precio": float(producto_pedido.precio) if producto_pedido.precio else 0.0,
                    "unidad": producto_pedido.unidad,
                    "moneda": producto_pedido.moneda,
                    "subtotal": float(producto_pedido.cantidad * producto_pedido.precio) if (producto_pedido.cantidad and producto_pedido.precio) else 0.0,
                    "producto_info": producto_info
                }
                
                productos_data.append(producto_data)
            
            # Datos principales del pedido
            pedido_data = {
                "id": pedido.id,
                "fecha": pedido.fecha.isoformat() if pedido.fecha else None,
                "status": pedido.status,
                "precio_total": float(pedido.precio_total) if pedido.precio_total else 0.0,
                "cliente": cliente_info,
                "usuario": pedido.usuario or "",
                "pesador": pedido.pesador or "",
                "notas": pedido.notas or "",
                "productos": productos_data,
                "productos_count": len(productos_data),
                "fecha_pagado": pedido.pagado_fecha.isoformat() if pedido.pagado_fecha else None,
                "fecha_despachado": pedido.despachado_fecha.isoformat() if pedido.despachado_fecha else None,
                "dolar_al_pagar": float(pedido.dolar_al_pagar) if pedido.dolar_al_pagar else None,
                "numero_pedido_balanza": pedido.numero_pedido_balanza
            }
            
            return JsonResponse({
                "success": True,
                "data": pedido_data
            }, json_dumps_params={'ensure_ascii': False})
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error obteniendo detalle de pedido {pk}: {str(e)}")
            
            return JsonResponse({
                "success": False,
                "error": "INTERNAL_SERVER_ERROR",
                "message": "Error interno del servidor al obtener detalle del pedido."
            }, status=500)


class TasaDolarAPI(View):
    """
    API Endpoint: GET /api/dolar/
    Retorna la tasa de dólar actual del sistema
    """
    
    def get(self, request):
        try:
            # Obtener la tasa actual del dólar (debería haber solo un registro)
            try:
                dolar = ValorDolar.objects.get(pk=1)
            except ValorDolar.DoesNotExist:
                # Si no existe, crear un registro por defecto
                dolar = ValorDolar(valor=1.0)
                dolar.save()
            
            return JsonResponse({
                "success": True,
                "data": {
                    "id": dolar.id,
                    "valor": float(dolar.valor),
                    "moneda_base": "USD",
                    "moneda_conversion": "BS", 
                    "descripcion": f"1 USD = {dolar.valor} BS",
                    "timestamp": timezone.now().isoformat()
                }
            }, json_dumps_params={'ensure_ascii': False})
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error obteniendo tasa del dólar: {str(e)}")
            
            return JsonResponse({
                "success": False,
                "error": "INTERNAL_SERVER_ERROR",
                "message": "Error interno del servidor al obtener la tasa del dólar."
            }, status=500)


class ReimprimirTicketAPI(View):
    """
    API Endpoint: POST /api/reimprimir-ticket/
    Reimprime el ticket de un pedido existente
    """
    
    
    def post(self, request):
        try:
            # Parsear body JSON
            try:
                body = json.loads(request.body)
            except json.JSONDecodeError:
                return JsonResponse({
                    "success": False,
                    "error": "INVALID_JSON",
                    "message": "Formato JSON inválido en el cuerpo de la petición"
                }, status=400)
            
            # Validar campos requeridos
            required_fields = ['pedido_id']
            for field in required_fields:
                if field not in body:
                    return JsonResponse({
                        "success": False,
                        "error": "MISSING_FIELD",
                        "message": f"El campo '{field}' es requerido"
                    }, status=400)
            
            pedido_id = body['pedido_id']
            impresora_ip = body.get('impresora_ip', '')
            
            # Validar que el pedido_id sea un número válido
            try:
                pedido_id = int(pedido_id)
            except (ValueError, TypeError):
                return JsonResponse({
                    "success": False,
                    "error": "INVALID_PEDIDO_ID",
                    "message": "El pedido_id debe ser un número entero válido"
                }, status=400)
            
            # Buscar el pedido
            try:
                pedido = Pedido.objects.prefetch_related('productos').get(pk=pedido_id)
            except Pedido.DoesNotExist:
                return JsonResponse({
                    "success": False,
                    "error": "ORDER_NOT_FOUND",
                    "message": f"No se encontró un pedido con ID {pedido_id}"
                }, status=404)
            
            # Verificar que el pedido tenga productos
            productos_pedido = pedido.productos.all()
            if not productos_pedido.exists():
                return JsonResponse({
                    "success": False,
                    "error": "EMPTY_ORDER",
                    "message": f"El pedido #{pedido_id} no tiene productos para imprimir"
                }, status=400)
            
            # Función para imprimir ticket de forma asíncrona
            def imprimir_ticket_async(pedido_obj, impresora_ip):
                try:
                    # Obtener productos del pedido
                    productos_pedido = pedido_obj.productos.all()
                    
                    # Usar la función existente de impresión con todos los parámetros requeridos
                    imprimirTicket(
                        id=pedido_obj.id,
                        productos=productos_pedido,
                        pedido=pedido_obj,
                        usuario=pedido_obj.usuario or '-',
                        pesador=pedido_obj.pesador or '-',
                        impresora=impresora_ip,
                        reimprimir=True,  # Siempre True para reimpresiones
                        dolar_historico=pedido_obj.dolar_al_pagar  # Usar tasa histórica si existe
                    )
                except Exception as e:
                    print(f"Error en impresión asíncrona: {str(e)}")
            
            # Iniciar impresión
            impresion_iniciada = False
            if impresora_ip:
                try:
                    import threading
                    thread = threading.Thread(
                        target=imprimir_ticket_async,
                        args=(pedido, impresora_ip)
                    )
                    thread.daemon = True
                    thread.start()
                    impresion_iniciada = True
                except Exception as e:
                    print(f"Error iniciando impresión: {str(e)}")
            
            # Preparar información del pedido para la respuesta
            cliente_nombre = "Cliente genérico"
            if pedido.cliente and pedido.cliente > 0:
                try:
                    cliente_obj = Cliente.objects.get(pk=pedido.cliente)
                    cliente_nombre = f"{cliente_obj.nombre} {cliente_obj.apellido}".strip()
                except Cliente.DoesNotExist:
                    pass
            
            # Respuesta exitosa
            return JsonResponse({
                "success": True,
                "message": f"Reimpresión del pedido #{pedido_id} {'iniciada exitosamente' if impresion_iniciada else 'solicitada (sin impresora especificada)'}",
                "data": {
                    "pedido_id": pedido.id,
                    "precio_total": float(pedido.precio_total),
                    "status": pedido.status,
                    "cliente_nombre": cliente_nombre,
                    "productos_count": productos_pedido.count(),
                    "fecha_pedido": pedido.fecha.isoformat() if pedido.fecha else None,
                    "impresion_iniciada": impresion_iniciada,
                    "impresora_ip": impresora_ip if impresora_ip else "No especificada"
                }
            }, status=200)
            
        except Exception as e:
            return JsonResponse({
                "success": False,
                "error": "INTERNAL_SERVER_ERROR",
                "message": f"Error interno del servidor: {str(e)}"
            }, status=500)


class LoginAPI(View):
    """
    API Endpoint: POST /api/auth/login/
    Autentica usuario y retorna información de sesión para React Native
    """
    
    
    def post(self, request):
        try:
            # Parsear body JSON
            try:
                body = json.loads(request.body)
            except json.JSONDecodeError:
                return JsonResponse({
                    "success": False,
                    "error": "INVALID_JSON",
                    "message": "Formato JSON inválido en el cuerpo de la petición"
                }, status=400)
            
            # Validar campos requeridos
            required_fields = ['username', 'password']
            for field in required_fields:
                if field not in body:
                    return JsonResponse({
                        "success": False,
                        "error": "MISSING_FIELD",
                        "message": f"El campo '{field}' es requerido"
                    }, status=400)
            
            username = body['username'].strip()
            password = body['password']
            
            # Validar que los campos no estén vacíos
            if not username or not password:
                return JsonResponse({
                    "success": False,
                    "error": "EMPTY_CREDENTIALS",
                    "message": "Usuario y contraseña no pueden estar vacíos"
                }, status=400)
            
            # Intentar autenticar usuario
            from django.contrib.auth import authenticate
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
                if user.is_active:
                    # Usuario autenticado exitosamente
                    
                    # Obtener grupos del usuario
                    user_groups = list(user.groups.values_list('name', flat=True))
                    
                    # Determinar permisos basados en grupos
                    permissions = {
                        'can_create_orders': any(group in ['PESADOR', 'ADMINISTRADOR', 'SUPERVISOR'] for group in user_groups),
                        'can_manage_credits': any(group in ['ADMINISTRADOR', 'SUPERVISOR'] for group in user_groups),
                        'can_access_admin': any(group in ['ADMINISTRADOR'] for group in user_groups),
                        'can_supervise': any(group in ['ADMINISTRADOR', 'SUPERVISOR'] for group in user_groups),
                        'is_pesador': 'PESADOR' in user_groups,
                        'is_supervisor': 'SUPERVISOR' in user_groups,
                        'is_admin': 'ADMINISTRADOR' in user_groups
                    }
                    
                    # Generar token de sesión simple (usando user ID + timestamp)
                    import time
                    import hashlib
                    timestamp = str(int(time.time()))
                    token_string = f"{user.id}_{username}_{timestamp}"
                    session_token = hashlib.sha256(token_string.encode()).hexdigest()
                    
                    # Respuesta exitosa
                    return JsonResponse({
                        "success": True,
                        "message": f"Usuario {username} autenticado exitosamente",
                        "data": {
                            "user": {
                                "id": user.id,
                                "username": user.username,
                                "first_name": user.first_name,
                                "last_name": user.last_name,
                                "email": user.email,
                                "full_name": f"{user.first_name} {user.last_name}".strip() or user.username,
                                "groups": user_groups,
                                "is_active": user.is_active,
                                "date_joined": user.date_joined.isoformat() if user.date_joined else None,
                                "last_login": user.last_login.isoformat() if user.last_login else None
                            },
                            "permissions": permissions,
                            "session": {
                                "token": session_token,
                                "expires_in": 86400,  # 24 horas en segundos
                                "created_at": timestamp
                            },
                            "app_config": {
                                "sucursal": getattr(settings, 'SUCURSAL', 'POS System'),
                                "api_base_url": getattr(settings, 'API_BASE_URL', 'http://192.168.1.107:8004'),
                                "version": "1.0.0"
                            }
                        }
                    }, status=200)
                    
                else:
                    # Usuario inactivo
                    return JsonResponse({
                        "success": False,
                        "error": "USER_INACTIVE",
                        "message": "La cuenta de usuario está desactivada"
                    }, status=403)
            else:
                # Credenciales incorrectas
                return JsonResponse({
                    "success": False,
                    "error": "INVALID_CREDENTIALS",
                    "message": "Usuario o contraseña incorrectos"
                }, status=401)
                
        except Exception as e:
            return JsonResponse({
                "success": False,
                "error": "INTERNAL_SERVER_ERROR",
                "message": f"Error interno del servidor: {str(e)}"
            }, status=500)


class LogoutAPI(View):
    """
    API Endpoint: POST /api/auth/logout/
    Cierra sesión del usuario (principalmente para limpiar datos locales)
    """
    
    
    def post(self, request):
        try:
            # Parsear body JSON (opcional)
            body = {}
            if request.body:
                try:
                    body = json.loads(request.body)
                except json.JSONDecodeError:
                    pass  # Body opcional, continuar sin error
            
            # Obtener token si se proporciona (para logging o invalidación futura)
            token = body.get('token', '')
            username = body.get('username', 'Usuario desconocido')
            
            # Respuesta exitosa (siempre exitosa porque es logout)
            return JsonResponse({
                "success": True,
                "message": f"Sesión cerrada exitosamente para {username}",
                "data": {
                    "logged_out_at": timezone.now().isoformat(),
                    "token_invalidated": bool(token),
                    "clear_local_data": True
                }
            }, status=200)
            
        except Exception as e:
            return JsonResponse({
                "success": False,
                "error": "INTERNAL_SERVER_ERROR", 
                "message": f"Error interno del servidor: {str(e)}"
            }, status=500)


class ValidateTokenAPI(View):
    """
    API Endpoint: POST /api/auth/validate/
    Valida si un token de sesión sigue siendo válido
    """
    
    
    def post(self, request):
        try:
            # Parsear body JSON
            try:
                body = json.loads(request.body)
            except json.JSONDecodeError:
                return JsonResponse({
                    "success": False,
                    "error": "INVALID_JSON",
                    "message": "Formato JSON inválido en el cuerpo de la petición"
                }, status=400)
            
            # Validar campos requeridos
            required_fields = ['token', 'user_id']
            for field in required_fields:
                if field not in body:
                    return JsonResponse({
                        "success": False,
                        "error": "MISSING_FIELD",
                        "message": f"El campo '{field}' es requerido"
                    }, status=400)
            
            token = body['token']
            user_id = body['user_id']
            
            try:
                user_id = int(user_id)
            except (ValueError, TypeError):
                return JsonResponse({
                    "success": False,
                    "error": "INVALID_USER_ID",
                    "message": "El user_id debe ser un número entero válido"
                }, status=400)
            
            # Buscar usuario
            try:
                user = User.objects.get(pk=user_id, is_active=True)
            except User.DoesNotExist:
                return JsonResponse({
                    "success": False,
                    "error": "USER_NOT_FOUND",
                    "message": "Usuario no encontrado o inactivo"
                }, status=404)
            
            # Validación simple del token (en producción usar JWT o similar)
            import time
            current_timestamp = int(time.time())
            
            # Para validación básica, verificar que el token no sea muy antiguo
            # En una implementación real, deberías usar JWT o almacenar tokens en DB
            try:
                # Extraer timestamp del token si fue generado de manera predecible
                # Este es un método básico, para producción usar JWT
                token_valid = len(token) == 64  # SHA256 tiene 64 caracteres hexadecimales
                
                if token_valid:
                    # Token parece válido (validación básica)
                    user_groups = list(user.groups.values_list('name', flat=True))
                    
                    return JsonResponse({
                        "success": True,
                        "message": "Token válido",
                        "data": {
                            "valid": True,
                            "user": {
                                "id": user.id,
                                "username": user.username,
                                "full_name": f"{user.first_name} {user.last_name}".strip() or user.username,
                                "groups": user_groups
                            },
                            "validated_at": timezone.now().isoformat()
                        }
                    }, status=200)
                else:
                    return JsonResponse({
                        "success": False,
                        "error": "INVALID_TOKEN",
                        "message": "Token inválido o expirado"
                    }, status=401)
                    
            except Exception:
                return JsonResponse({
                    "success": False,
                    "error": "INVALID_TOKEN",
                    "message": "Token inválido o expirado"
                }, status=401)
                
        except Exception as e:
            return JsonResponse({
                "success": False,
                "error": "INTERNAL_SERVER_ERROR",
                "message": f"Error interno del servidor: {str(e)}"
            }, status=500)# ... existing code ...
class BalanzaImpresoraIp(ADMIN_SUPERVISOR_AUTH, LoginRequiredMixin,View):
    def get(self,request,*args, **kwargs):
        context={'BALANZAS':BALANZAS.items(), 'IMPRESORAS':IMPRESORAS.items()}
        return render(request, 'menu_balanzas_impresoras.html', context)
    
    def post(self,request,*args, **kwargs):
        balanza_id = request.POST['balanza']
        impresora_ip = request.POST['impresora']
        balanza = BalanzasImpresoras.objects.get_or_create(balanza_id=balanza_id, defaults={'impresora_ip':impresora_ip})[0]
        balanza.impresora_ip = impresora_ip
        balanza.save()
        return HttpResponse(200)

# Nueva vista principal de configuración
class ConfiguracionDispositivos(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        # Recargar configuración para obtener datos actualizados
        global IMPRESORAS, IMPRESORAS_ETIQUETAS, BALANZAS
        config_json = leer_configuracion()
        IMPRESORAS = config_json["IMPRESORAS"]
        IMPRESORAS_ETIQUETAS = config_json.get("IMPRESORAS_ETIQUETAS", {})
        BALANZAS = config_json["BALANZAS"]
        
        # Cargar datos básicos sin verificar conexión
        impresoras_estado = {}
        for imp_id, imp_ip in IMPRESORAS.items():
            impresoras_estado[imp_id] = {
                'ip': imp_ip,
                'online': None,  # Estado inicial desconocido
                'nombre': f"Impresora {imp_id}"
            }
        
        impresoras_etiquetas_estado = {}
        for imp_id, imp_ip in IMPRESORAS_ETIQUETAS.items():
            impresoras_etiquetas_estado[imp_id] = {
                'ip': imp_ip,
                'online': None,  # Estado inicial desconocido
                'nombre': f"Impresora de Etiquetas {imp_id}"
            }
        
        balanzas_estado = {}
        for bal_id, bal_ip in BALANZAS.items():
            balanzas_estado[bal_id] = {
                'ip': bal_ip,
                'online': None,  # Estado inicial desconocido
                'nombre': f"Balanza {bal_id}"
            }
        
        # Verificar si el usuario puede gestionar dispositivos
        puede_gestionar = (
            request.user.groups.filter(name__in=['ADMINISTRADOR', 'SUPERVISOR']).exists()
        )
        
        # Configuración multi-pesador disponible para todos los usuarios autenticados
        es_pesador = True  # Permitir acceso a todos los usuarios
        
        context = {
            'impresoras': impresoras_estado,
            'impresoras_etiquetas': impresoras_etiquetas_estado,
            'balanzas': balanzas_estado,
            'puede_gestionar': puede_gestionar,
            'es_pesador': es_pesador
        }
        return render(request, 'configuracion_dispositivos.html', context)

# Vista para verificar estado de conexión de dispositivos
class VerificarEstadoDispositivos(ADMIN_SUPERVISOR_AUTH, LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        # Obtener estado de conexión de impresoras
        impresoras_estado = {}
        for imp_id, imp_ip in IMPRESORAS.items():
            success, _, error = conectar_socket_seguro(imp_ip, 9100, "TEST", timeout=1, es_balanza=False)
            impresoras_estado[imp_id] = {
                'ip': imp_ip,
                'online': success,
                'nombre': f"Impresora {imp_id}"
            }
        
        # Obtener estado de conexión de balanzas
        balanzas_estado = {}
        for bal_id, bal_ip in BALANZAS.items():
            success, _, error = conectar_socket_seguro(bal_ip, 4001, "P", timeout=1, es_balanza=True)
            balanzas_estado[bal_id] = {
                'ip': bal_ip,
                'online': success,
                'nombre': f"Balanza {bal_id}"
            }
        
        return JsonResponse({
            'impresoras': impresoras_estado,
            'balanzas': balanzas_estado
        })

# Vista para probar impresoras
class ProbarImpresora(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        try:
            impresora_id = request.POST.get('impresora_id')
            
            print(f"🖨️ DEBUG ProbarImpresora: impresora_id={impresora_id}")
            print(f"🖨️ DEBUG ProbarImpresora: IMPRESORAS disponibles={list(IMPRESORAS.keys())}")
            
            if impresora_id not in IMPRESORAS:
                print(f"❌ DEBUG ProbarImpresora: Impresora {impresora_id} no encontrada")
                return JsonResponse({'success': False, 'message': 'Impresora no encontrada'})
            
            impresora_ip = IMPRESORAS[impresora_id]
            print(f"✅ DEBUG ProbarImpresora: Impresora {impresora_id} encontrada, IP={impresora_ip}")
            
            # Ticket de prueba
            ticket_prueba = """
^XA
^CF0,30
^FO50,50^FD*** TICKET DE PRUEBA ***^FS
^CF0,20
^FO50,100^FDImpresora: {impresora_id}^FS
^FO50,130^FDIP: {impresora_ip}^FS
^FO50,160^FDFecha: {fecha}^FS
^FO50,190^FDHora: {hora}^FS
^FO50,240^FD*** PRUEBA EXITOSA ***^FS
^XZ
""".format(
                impresora_id=impresora_id,
                impresora_ip=impresora_ip,
                fecha=timezone.now().strftime('%d/%m/%Y'),
                hora=timezone.now().strftime('%H:%M:%S')
            )
            
            print(f"🖨️ DEBUG ProbarImpresora: Conectando a IP {impresora_ip}:9100")
            success, result, error = conectar_socket_seguro(impresora_ip, 9100, ticket_prueba, timeout=3, es_balanza=False)
            
            if success:
                print(f"✅ DEBUG ProbarImpresora: Conexión exitosa a {impresora_ip}")
                response_data = {'success': True, 'message': f'Ticket de prueba enviado a Impresora {impresora_id}'}
                print(f"✅ DEBUG ProbarImpresora: Devolviendo respuesta exitosa: {response_data}")
                return JsonResponse(response_data)
            else:
                print(f"❌ DEBUG ProbarImpresora: Error conectando a {impresora_ip}: {error}")
                response_data = {'success': False, 'message': f'Error al conectar con Impresora {impresora_id}: {error}'}
                print(f"❌ DEBUG ProbarImpresora: Devolviendo error: {response_data}")
                return JsonResponse(response_data)
                
        except Exception as e:
            import traceback
            print(f"❌ DEBUG ProbarImpresora: Excepción no controlada: {str(e)}")
            print(f"❌ DEBUG ProbarImpresora: Stack trace: {traceback.format_exc()}")
            response_data = {'success': False, 'message': f'Error interno del servidor: {str(e)}'}
            print(f"❌ DEBUG ProbarImpresora: Devolviendo error de excepción: {response_data}")
            return JsonResponse(response_data)

# Vista para probar balanzas
class ProbarBalanza(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        try:
            balanza_id = request.POST.get('balanza_id')
            
            print(f"⚖️ DEBUG ProbarBalanza: balanza_id={balanza_id}")
            print(f"⚖️ DEBUG ProbarBalanza: BALANZAS disponibles={list(BALANZAS.keys())}")
            comando = request.POST.get('comando', 'P')  # P = peso, T = tare
            
            if balanza_id not in BALANZAS:
                print(f"❌ DEBUG ProbarBalanza: Balanza {balanza_id} no encontrada")
                return JsonResponse({'success': False, 'message': 'Balanza no encontrada'})
            
            balanza_ip = BALANZAS[balanza_id]
            print(f"✅ DEBUG ProbarBalanza: Balanza {balanza_id} encontrada, IP={balanza_ip}")
            print(f"⚖️ DEBUG ProbarBalanza: Enviando comando '{comando}' a {balanza_ip}:4001")
            
            success, result, error = conectar_socket_seguro(balanza_ip, 4001, comando, timeout=3, es_balanza=True)
            
            print(f"⚖️ DEBUG ProbarBalanza: Resultado - success={success}, result='{result}', error='{error}'")
            
            if success:
                if comando == 'P':
                    try:
                        peso = float(result.strip())
                        response_data = {
                            'success': True, 
                            'message': f'Peso obtenido de Balanza {balanza_id}: {peso} kg',
                            'peso': peso
                        }
                        print(f"✅ DEBUG ProbarBalanza: Devolviendo peso exitoso: {response_data}")
                        return JsonResponse(response_data)
                    except ValueError:
                        response_data = {
                            'success': True, 
                            'message': f'Respuesta de Balanza {balanza_id}: {result}',
                            'respuesta': result
                        }
                        print(f"✅ DEBUG ProbarBalanza: Devolviendo respuesta cruda: {response_data}")
                        return JsonResponse(response_data)
                elif comando == 'T':
                    response_data = {
                        'success': True, 
                        'message': f'Comando TARE enviado a Balanza {balanza_id}',
                        'respuesta': result
                    }
                    print(f"✅ DEBUG ProbarBalanza: Devolviendo resultado TARE: {response_data}")
                    return JsonResponse(response_data)
            else:
                response_data = {'success': False, 'message': f'Error al conectar con Balanza {balanza_id}: {error}'}
                print(f"❌ DEBUG ProbarBalanza: Devolviendo error: {response_data}")
                return JsonResponse(response_data)
                
        except Exception as e:
            import traceback
            print(f"❌ DEBUG ProbarBalanza: Excepción no controlada: {str(e)}")
            print(f"❌ DEBUG ProbarBalanza: Stack trace: {traceback.format_exc()}")
            response_data = {'success': False, 'message': f'Error interno del servidor: {str(e)}'}
            print(f"❌ DEBUG ProbarBalanza: Devolviendo error de excepción: {response_data}")
            return JsonResponse(response_data)

# === VISTAS PARA GESTIÓN DE CONFIGURACIÓN DE DISPOSITIVOS ===

# Vista para agregar impresora
class AgregarImpresora(ADMIN_SUPERVISOR_AUTH, LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        try:
            imp_id = request.POST.get('imp_id', '').strip()
            imp_ip = request.POST.get('imp_ip', '').strip()
            
            if not imp_id or not imp_ip:
                return JsonResponse({
                    'status': 'error',
                    'message': 'ID e IP son requeridos'
                })
            
            # Validar formato IP
            import re
            ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
            if not re.match(ip_pattern, imp_ip):
                return JsonResponse({
                    'status': 'error',
                    'message': 'Formato de IP inválido'
                })
            
            # Leer configuración actual
            config_data = leer_configuracion()
            
            # Verificar si el ID ya existe
            if imp_id in config_data["IMPRESORAS"]:
                return JsonResponse({
                    'status': 'error',
                    'message': f'Ya existe una impresora con ID: {imp_id}'
                })
            
            # Verificar si la IP ya existe
            if imp_ip in config_data["IMPRESORAS"].values():
                return JsonResponse({
                    'status': 'error',
                    'message': f'Ya existe una impresora con IP: {imp_ip}'
                })
            
            # Agregar nueva impresora
            config_data["IMPRESORAS"][imp_id] = imp_ip
            
            # Escribir configuración
            escribir_configuracion(config_data)
            
            # Actualizar variables globales
            global IMPRESORAS
            IMPRESORAS = config_data["IMPRESORAS"]
            
            return JsonResponse({
                'status': 'success',
                'message': f'Impresora {imp_id} agregada exitosamente'
            })
            
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'Error al agregar impresora: {str(e)}'
            })

# Vista para eliminar impresora
class EliminarImpresora(ADMIN_SUPERVISOR_AUTH, LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        try:
            imp_id = request.POST.get('imp_id', '').strip()
            
            if not imp_id:
                return JsonResponse({
                    'status': 'error',
                    'message': 'ID de impresora requerido'
                })
            
            # Leer configuración actual
            config_data = leer_configuracion()
            
            # Verificar si existe
            if imp_id not in config_data["IMPRESORAS"]:
                return JsonResponse({
                    'status': 'error',
                    'message': f'No existe impresora con ID: {imp_id}'
                })
            
            # Eliminar impresora
            del config_data["IMPRESORAS"][imp_id]
            
            # Escribir configuración
            escribir_configuracion(config_data)
            
            # Actualizar variables globales
            global IMPRESORAS
            IMPRESORAS = config_data["IMPRESORAS"]
            
            return JsonResponse({
                'status': 'success',
                'message': f'Impresora {imp_id} eliminada exitosamente'
            })
            
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'Error al eliminar impresora: {str(e)}'
            })

# Vista para agregar balanza
class AgregarBalanza(ADMIN_SUPERVISOR_AUTH, LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        try:
            bal_id = request.POST.get('bal_id', '').strip()
            bal_ip = request.POST.get('bal_ip', '').strip()
            
            if not bal_id or not bal_ip:
                return JsonResponse({
                    'status': 'error',
                    'message': 'ID e IP son requeridos'
                })
            
            # Validar formato IP
            import re
            ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
            if not re.match(ip_pattern, bal_ip):
                return JsonResponse({
                    'status': 'error',
                    'message': 'Formato de IP inválido'
                })
            
            # Leer configuración actual
            config_data = leer_configuracion()
            
            # Verificar si el ID ya existe
            if bal_id in config_data["BALANZAS"]:
                return JsonResponse({
                    'status': 'error',
                    'message': f'Ya existe una balanza con ID: {bal_id}'
                })
            
            # Verificar si la IP ya existe
            if bal_ip in config_data["BALANZAS"].values():
                return JsonResponse({
                    'status': 'error',
                    'message': f'Ya existe una balanza con IP: {bal_ip}'
                })
            
            # Agregar nueva balanza
            config_data["BALANZAS"][bal_id] = bal_ip
            
            # Escribir configuración
            escribir_configuracion(config_data)
            
            # Actualizar variables globales
            global BALANZAS
            BALANZAS = config_data["BALANZAS"]
            
            return JsonResponse({
                'status': 'success',
                'message': f'Balanza {bal_id} agregada exitosamente'
            })
            
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'Error al agregar balanza: {str(e)}'
            })

# Vista para eliminar balanza
class EliminarBalanza(ADMIN_SUPERVISOR_AUTH, LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        try:
            bal_id = request.POST.get('bal_id', '').strip()
            
            if not bal_id:
                return JsonResponse({
                    'status': 'error',
                    'message': 'ID de balanza requerido'
                })
            
            # Leer configuración actual
            config_data = leer_configuracion()
            
            # Verificar si existe
            if bal_id not in config_data["BALANZAS"]:
                return JsonResponse({
                    'status': 'error',
                    'message': f'No existe balanza con ID: {bal_id}'
                })
            
            # Eliminar balanza
            del config_data["BALANZAS"][bal_id]
            
            # Escribir configuración
            escribir_configuracion(config_data)
            
            # Actualizar variables globales
            global BALANZAS
            BALANZAS = config_data["BALANZAS"]
            
            return JsonResponse({
                'status': 'success',
                'message': f'Balanza {bal_id} eliminada exitosamente'
            })
            
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'Error al eliminar balanza: {str(e)}'
            })

# Vista para editar impresora
class EditarImpresora(ADMIN_SUPERVISOR_AUTH, LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        try:
            imp_id_original = request.POST.get('imp_id_original', '').strip()
            imp_id_nuevo = request.POST.get('imp_id_nuevo', '').strip()
            imp_ip_nueva = request.POST.get('imp_ip_nueva', '').strip()
            
            if not imp_id_original or not imp_id_nuevo or not imp_ip_nueva:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Todos los campos son requeridos'
                })
            
            # Validar formato IP
            import re
            ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
            if not re.match(ip_pattern, imp_ip_nueva):
                return JsonResponse({
                    'status': 'error',
                    'message': 'Formato de IP inválido'
                })
            
            # Leer configuración actual
            config_data = leer_configuracion()
            
            # Verificar si la impresora original existe
            if imp_id_original not in config_data["IMPRESORAS"]:
                return JsonResponse({
                    'status': 'error',
                    'message': f'No existe impresora con ID: {imp_id_original}'
                })
            
            # Si el ID cambió, verificar que el nuevo no exista
            if imp_id_original != imp_id_nuevo and imp_id_nuevo in config_data["IMPRESORAS"]:
                return JsonResponse({
                    'status': 'error',
                    'message': f'Ya existe una impresora con ID: {imp_id_nuevo}'
                })
            
            # Verificar si la nueva IP ya existe en otra impresora
            for id_existente, ip_existente in config_data["IMPRESORAS"].items():
                if ip_existente == imp_ip_nueva and id_existente != imp_id_original:
                    return JsonResponse({
                        'status': 'error',
                        'message': f'Ya existe una impresora con IP: {imp_ip_nueva}'
                    })
            
            # Eliminar la entrada original si el ID cambió
            if imp_id_original != imp_id_nuevo:
                del config_data["IMPRESORAS"][imp_id_original]
            
            # Agregar/actualizar con los nuevos valores
            config_data["IMPRESORAS"][imp_id_nuevo] = imp_ip_nueva
            
            # Escribir configuración
            escribir_configuracion(config_data)
            
            # Actualizar variables globales
            global IMPRESORAS
            IMPRESORAS = config_data["IMPRESORAS"]
            
            return JsonResponse({
                'status': 'success',
                'message': f'Impresora actualizada exitosamente'
            })
            
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'Error al editar impresora: {str(e)}'
            })

# Vista para editar balanza
class EditarBalanza(ADMIN_SUPERVISOR_AUTH, LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        try:
            bal_id_original = request.POST.get('bal_id_original', '').strip()
            bal_id_nuevo = request.POST.get('bal_id_nuevo', '').strip()
            bal_ip_nueva = request.POST.get('bal_ip_nueva', '').strip()
            
            if not bal_id_original or not bal_id_nuevo or not bal_ip_nueva:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Todos los campos son requeridos'
                })
            
            # Validar formato IP
            import re
            ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
            if not re.match(ip_pattern, bal_ip_nueva):
                return JsonResponse({
                    'status': 'error',
                    'message': 'Formato de IP inválido'
                })
            
            # Leer configuración actual
            config_data = leer_configuracion()
            
            # Verificar si la balanza original existe
            if bal_id_original not in config_data["BALANZAS"]:
                return JsonResponse({
                    'status': 'error',
                    'message': f'No existe balanza con ID: {bal_id_original}'
                })
            
            # Si el ID cambió, verificar que el nuevo no exista
            if bal_id_original != bal_id_nuevo and bal_id_nuevo in config_data["BALANZAS"]:
                return JsonResponse({
                    'status': 'error',
                    'message': f'Ya existe una balanza con ID: {bal_id_nuevo}'
                })
            
            # Verificar si la nueva IP ya existe en otra balanza
            for id_existente, ip_existente in config_data["BALANZAS"].items():
                if ip_existente == bal_ip_nueva and id_existente != bal_id_original:
                    return JsonResponse({
                        'status': 'error',
                        'message': f'Ya existe una balanza con IP: {bal_ip_nueva}'
                    })
            
            # Eliminar la entrada original si el ID cambió
            if bal_id_original != bal_id_nuevo:
                del config_data["BALANZAS"][bal_id_original]
            
            # Agregar/actualizar con los nuevos valores
            config_data["BALANZAS"][bal_id_nuevo] = bal_ip_nueva
            
            # Escribir configuración
            escribir_configuracion(config_data)
            
            # Actualizar variables globales
            global BALANZAS
            BALANZAS = config_data["BALANZAS"]
            
            return JsonResponse({
                'status': 'success',
                'message': f'Balanza actualizada exitosamente'
            })
            
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'Error al editar balanza: {str(e)}'
            })

# === VISTAS PARA GESTIÓN DE IMPRESORAS DE ETIQUETAS ===

# Vista para agregar impresora de etiquetas
class AgregarImpresoraEtiqueta(ADMIN_SUPERVISOR_AUTH, LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        try:
            imp_id = request.POST.get('imp_id', '').strip()
            imp_ip = request.POST.get('imp_ip', '').strip()
            
            if not imp_id or not imp_ip:
                return JsonResponse({
                    'status': 'error',
                    'message': 'ID e IP son requeridos'
                })
            
            # Validar formato IP
            import re
            ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
            if not re.match(ip_pattern, imp_ip):
                return JsonResponse({
                    'status': 'error',
                    'message': 'Formato de IP inválido'
                })
            
            # Leer configuración actual
            config_data = leer_configuracion()
            
            # Asegurar que existe la sección IMPRESORAS_ETIQUETAS
            if "IMPRESORAS_ETIQUETAS" not in config_data:
                config_data["IMPRESORAS_ETIQUETAS"] = {}
            
            # Verificar si el ID ya existe
            if imp_id in config_data["IMPRESORAS_ETIQUETAS"]:
                return JsonResponse({
                    'status': 'error',
                    'message': f'Ya existe una impresora de etiquetas con ID: {imp_id}'
                })
            
            # Verificar si la IP ya existe
            if imp_ip in config_data["IMPRESORAS_ETIQUETAS"].values():
                return JsonResponse({
                    'status': 'error',
                    'message': f'Ya existe una impresora de etiquetas con IP: {imp_ip}'
                })
            
            # Agregar nueva impresora de etiquetas
            config_data["IMPRESORAS_ETIQUETAS"][imp_id] = imp_ip
            
            # Escribir configuración
            escribir_configuracion(config_data)
            
            # Actualizar variables globales
            global IMPRESORAS_ETIQUETAS
            IMPRESORAS_ETIQUETAS = config_data["IMPRESORAS_ETIQUETAS"]
            
            return JsonResponse({
                'status': 'success',
                'message': f'Impresora de etiquetas {imp_id} agregada exitosamente'
            })
            
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'Error al agregar impresora de etiquetas: {str(e)}'
            })

# Vista para eliminar impresora de etiquetas
class EliminarImpresoraEtiqueta(ADMIN_SUPERVISOR_AUTH, LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        try:
            imp_id = request.POST.get('imp_id', '').strip()
            
            if not imp_id:
                return JsonResponse({
                    'status': 'error',
                    'message': 'ID de impresora de etiquetas requerido'
                })
            
            # Leer configuración actual
            config_data = leer_configuracion()
            
            # Verificar si existe la sección
            if "IMPRESORAS_ETIQUETAS" not in config_data:
                config_data["IMPRESORAS_ETIQUETAS"] = {}
            
            # Verificar si existe
            if imp_id not in config_data["IMPRESORAS_ETIQUETAS"]:
                return JsonResponse({
                    'status': 'error',
                    'message': f'No existe impresora de etiquetas con ID: {imp_id}'
                })
            
            # Eliminar impresora de etiquetas
            del config_data["IMPRESORAS_ETIQUETAS"][imp_id]
            
            # Escribir configuración
            escribir_configuracion(config_data)
            
            # Actualizar variables globales
            global IMPRESORAS_ETIQUETAS
            IMPRESORAS_ETIQUETAS = config_data["IMPRESORAS_ETIQUETAS"]
            
            return JsonResponse({
                'status': 'success',
                'message': f'Impresora de etiquetas {imp_id} eliminada exitosamente'
            })
            
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'Error al eliminar impresora de etiquetas: {str(e)}'
            })

# Vista para editar impresora de etiquetas
class EditarImpresoraEtiqueta(ADMIN_SUPERVISOR_AUTH, LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        try:
            imp_id_original = request.POST.get('imp_id_original', '').strip()
            imp_id_nuevo = request.POST.get('imp_id_nuevo', '').strip()
            imp_ip_nueva = request.POST.get('imp_ip_nueva', '').strip()
            
            if not imp_id_original or not imp_id_nuevo or not imp_ip_nueva:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Todos los campos son requeridos'
                })
            
            # Validar formato IP
            import re
            ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
            if not re.match(ip_pattern, imp_ip_nueva):
                return JsonResponse({
                    'status': 'error',
                    'message': 'Formato de IP inválido'
                })
            
            # Leer configuración actual
            config_data = leer_configuracion()
            
            # Asegurar que existe la sección
            if "IMPRESORAS_ETIQUETAS" not in config_data:
                config_data["IMPRESORAS_ETIQUETAS"] = {}
            
            # Verificar si la impresora original existe
            if imp_id_original not in config_data["IMPRESORAS_ETIQUETAS"]:
                return JsonResponse({
                    'status': 'error',
                    'message': f'No existe impresora de etiquetas con ID: {imp_id_original}'
                })
            
            # Si el ID cambió, verificar que el nuevo no exista
            if imp_id_original != imp_id_nuevo and imp_id_nuevo in config_data["IMPRESORAS_ETIQUETAS"]:
                return JsonResponse({
                    'status': 'error',
                    'message': f'Ya existe una impresora de etiquetas con ID: {imp_id_nuevo}'
                })
            
            # Verificar si la nueva IP ya existe en otra impresora
            for id_existente, ip_existente in config_data["IMPRESORAS_ETIQUETAS"].items():
                if ip_existente == imp_ip_nueva and id_existente != imp_id_original:
                    return JsonResponse({
                        'status': 'error',
                        'message': f'Ya existe una impresora de etiquetas con IP: {imp_ip_nueva}'
                    })
            
            # Eliminar la entrada original si el ID cambió
            if imp_id_original != imp_id_nuevo:
                del config_data["IMPRESORAS_ETIQUETAS"][imp_id_original]
            
            # Agregar/actualizar con los nuevos valores
            config_data["IMPRESORAS_ETIQUETAS"][imp_id_nuevo] = imp_ip_nueva
            
            # Escribir configuración
            escribir_configuracion(config_data)
            
            # Actualizar variables globales
            global IMPRESORAS_ETIQUETAS
            IMPRESORAS_ETIQUETAS = config_data["IMPRESORAS_ETIQUETAS"]
            
            return JsonResponse({
                'status': 'success',
                'message': f'Impresora de etiquetas actualizada exitosamente'
            })
            
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'Error al editar impresora de etiquetas: {str(e)}'
            })