from django.urls import include, path
from .views import *



app_name="pos"
#definimos todas las urls de la App 'pos'

urlpatterns = [
    path('',  PosView.as_view(), name='pos'),
    path('<int:pedido>/', PosView.as_view(), name='posPedido'),

    path('filtrar-categorias/', FiltrarCategorias.as_view(), name='filtrarCategorias'),
    path('<int:pedido>/filtrar-categorias/', FiltrarCategorias.as_view(), name='filtrarCategorias2'),

    path('<int:pedido>/guardar-pedido/', GuardarPedidoPost.as_view(), name='guardarPedido2'),
    path('guardar-pedido/', GuardarPedidoPost.as_view(), name='guardarPedido'),
    
    # 🚀 NUEVAS RUTAS: Procesamiento no-bloqueante
    path('<int:pedido>/guardar-pedido-rapido/', GuardarPedidoRapido.as_view(), name='guardarPedidoRapido2'),
    path('guardar-pedido-rapido/', GuardarPedidoRapido.as_view(), name='guardarPedidoRapido'),
    path('verificar-impresion/<int:pedido_id>/', VerificarImpresion.as_view(), name='verificarImpresion'),
    path('reimprimir-ticket-rapido/', ReimprimirTicketRapido.as_view(), name='reimprimirTicketRapido'),
    path('<int:pedido>/reimprimir-ticket-rapido/', ReimprimirTicketRapido.as_view(), name='reimprimirTicketRapido2'),
    
    path('<int:pedido>/reimprimir-pedido/', ReimprimirTicket.as_view(), name='reimprimir-pedido2'),
    path('reimprimir-pedido/', ReimprimirTicket.as_view(), name='reimprimir-pedido'),

    path('<int:pedido>/pedidosList/', PedidosList.as_view(), name='listaPedidos2'),
    path('pedidosList/', PedidosList.as_view(), name='listaPedidos'),
    path('pedidosList/todos/', PedidosListTodos.as_view(), name='listaPedidosTodos'),
    path('<int:pedido>/pedidosList/todos/', PedidosListTodos.as_view(), name='listaPedidosTodos2'),
    path('pedidosList/buscarPedido/', BuscarPedidoPos.as_view(), name='BuscarPedidoPos'),
    path('<int:pedido>/pedidosList/buscarPedido/', BuscarPedidoPos.as_view(), name='BuscarPedidoPos2'),

    path('clientesList/', ClientesList.as_view(), name='listaClientes'),
    path('<int:pedido>/clientesList/', ClientesList.as_view(), name='listaClientes2'),
    path('buscarClientes/', BuscarCliente.as_view(), name='buscar-cliente'),
    path('actualizar-cliente/', ActualizarClientePedido.as_view(), name='actualizar-cliente'),

    path('<int:pedido>/pagina-pago/', PaginaPago.as_view(),name='pago'),
    path('<int:pedido>/pagina-pago/pagar-pedido/', PagarPedido.as_view(), name='pagarPedido'),
    
    # 🚀 NUEVA RUTA: Pago con impresión asíncrona
    path('<int:pedido>/pagina-pago/pagar-pedido-rapido/', PagarPedidoRapido.as_view(), name='pagarPedidoRapido'),

    path('cerrar-caja/', CierreCaja.as_view(), name='cierre-caja'),

    path('home/',  Home.as_view(), name='home'),
    path('pre-pesados/',  PrePesados.as_view(), name='pre-pesados'),
    path('pre-pesados/imprimir-etiqueta/', ImprimirEtiquetaTSPL.as_view(), name='imprimir-etiqueta-tspl'),
    path('menu/',  Menu.as_view(), name='menu'),

    path('menu/ventas/',  Ventas.as_view(), name='ventas'),
    path('menu/ventas/api/chart-data/', VentasChartData.as_view(), name='ventas-chart-data'),
    path('menu/ventas/ventas-mes/',  VentasPorTiempo.as_view(), name='ventas_por_mes'),
    path('menu/productos-analytics/',  ProductAnalytics.as_view(), name='productos-analytics'),
    path('menu/productos-analytics/api/productos-mas-vendidos/',  ProductosMasVendidosData.as_view(), name='productos-mas-vendidos-data'),
    path('menu/productos-analytics/api/movimientos-producto/',  MovimientosProductoData.as_view(), name='movimientos-producto-data'),
    path('menu/productos-analytics/api/productos-sugeridos/',  ProductosSugeridosView.as_view(), name='productos-sugeridos'),

    path('menu/productos/',  Productos.as_view(), name='productos'),
    path('menu/productos/crear',  ProductoCreateView.as_view(), name='crear-producto'),
    path('menu/productos/edit/<int:pk>',  ProductoUpdateView.as_view(), name='edit-producto'),
    path('menu/productos/delete/<int:pk>', ProductoDeleteView.as_view(), name='delete-producto'),
    path('menu/productos/cantidad/<int:pk>', ProductoAumentarCantidad.as_view(), name='producto-cantidad'),
    path('menu/productos/buscar', BuscarProductoNombreMenu.as_view(), name='producto-buscar-nombre'),

    path('menu/usuarios/',  UsuariosMenu.as_view(), name='usuarios'),
    path('menu/usuarios/create',  CrearUsuarioView.as_view(), name='user-create'),
    path('menu/usuarios/edit/<int:pk>', ModificarUsuarioView.as_view(), name='user-edit'),
    path('menu/usuarios/delete/<int:pk>', DeleteUsuarioView.as_view(), name='user_delete'),
    path('menu/usuarios/edit/password/<int:pk>', AdminChangePasswordView.as_view(), name='admin_change_password'),

    path('menu/dolar/',  Dolar.as_view(), name='dolar-create'),
    path('menu/dolar/<int:pk>',  Dolar.as_view(), name='dolar'),

    path('menu/categorias/',  CategoriasList.as_view(), name='categorias'),
    path('menu/categorias/create',  CategoriaCreateView.as_view(), name='crear-categoria'),
    path('menu/categorias/edit/<int:pk>',  CategoriaUpdateView.as_view(), name='edit-categoria'),
    path('menu/categorias/delete/<int:pk>',  CategoriaDeleteView.as_view(), name='delete-categoria'),
    path('menu/categorias/cambiar-precios/<int:pk>/', CambioPreciosCategoria.as_view(), name='cambiar-precios-categoria'),

    path('menu/pedidos/',  PedidosListMenu.as_view(), name='pedidos'),
    path('menu/pedidos/filtrar/', FiltrarPedidos.as_view(), name='filtrar-pedidos'),
    path('menu/pedidos/exportar/', ExportarPedidosExcel.as_view(), name='exportar-pedidos-excel'),
    path('menu/pedidos/delete/<int:pk>',  DeletePedidoView.as_view(), name='delete-pedido'),
    path('menu/pedidos/marcar-devolucion/', MarcarDevolucion.as_view(), name='marcar-devolucion'),
    path('menu/pedidos/marcar-injustificado/', MarcarInjustificado.as_view(), name='marcar-injustificado'),

    path('menu/impresoras',  AdminImpresora.as_view(), name='menu-impresoras'),
    path('menu/balanzas',  AdminBalanza.as_view(), name='menu-balanzas'),
    path('menu/balanzas-impresoras', BalanzaImpresoraIp.as_view(), name='menu-balanzas-impresoras'),
    
    # Nuevas rutas de configuración
    path('configuracion/', ConfiguracionDispositivos.as_view(), name='configuracion-dispositivos'),
    path('configuracion/verificar-estado/', VerificarEstadoDispositivos.as_view(), name='verificar-estado-dispositivos'),
    path('configuracion/probar-impresora/', ProbarImpresora.as_view(), name='probar-impresora'),
    path('configuracion/probar-balanza/', ProbarBalanza.as_view(), name='probar-balanza'),

    path('volver-pos/', VolverPOS.as_view(), name='volver-pos'),

    path('menu/balanzas-productos', ProductosEnBalanzas.as_view(), name='menu-balanza'),

    path('menu/cliente/',  ClienteList.as_view(), name='cliente'),
    path('menu/cliente/create',  ClienteCreateView.as_view(), name='crear-cliente'),
    path('menu/cliente/edit/<int:pk>',  ClienteUpdateView.as_view(), name='edit-cliente'),
    path('menu/cliente/delete/<int:pk>',  ClienteDeleteView.as_view(), name='delete-cliente'),
    path('menu/cliente/buscar', BuscarClienteCedulaMenu.as_view(), name='cliente-buscar'),

    path('balanza', ConexionBalanza.as_view(), name='balanza'),
    path('balanza-async', ConexionBalanzaAsync.as_view(), name='balanza-async'),

    path('creditos', lista_clientes_por_deuda.as_view(), name='creditos'),
    path('credito-detalles/credito/<int:pk>', PagarCredito.as_view(), name='Pagarcredito'),
    path('credito-detalles/<int:pk>', detalle_cliente.as_view(), name='creditoCliente'),

    path('abrir-caja/', AbrirCaja.as_view(), name='abrir-caja'),
    path('verificar-estado-caja/', VerificarEstadoCaja.as_view(), name='verificar-estado-caja'),

    path('validar-autorizacion-credito/', ValidarAutorizacionCredito.as_view(), name='validar-autorizacion-credito'),
    path('validar-autorizacion-vuelto/', ValidarAutorizacionVuelto.as_view(), name='validar-autorizacion-vuelto'),
    path('procesar-pedido-injustificado/', ProcesarPedidoInjustificado.as_view(), name='procesar-pedido-injustificado'),
    path('cancelar-abono/', CancelarAbono.as_view(), name='cancelar-abono'),

    path('menu/cierres-caja/', CierresCajaListView.as_view(), name='cierres-caja'),
    path('menu/cierres-caja/filtrar/', FiltrarCierresCaja.as_view(), name='filtrar-cierres-caja'),
    path('menu/cierres-caja/detalle/<int:pk>/', DetalleCierreCaja.as_view(), name='detalle-cierre'),
    path('reimprimir-ticket-cierre/<int:pk>', ReimprimirTicketCierre.as_view(), name='reimprimir-ticket-cierre'),

    path('abonar-credito/<int:pk>/', AbonarCredito.as_view(), name='abonar_credito'),
    
    # Pagos móviles
    path('menu/pagos-moviles/', PagoMovilListView.as_view(), name='pagos-moviles'),
    path('menu/pagos-moviles/verificar/', VerificarPagoMovil.as_view(), name='verificar-pago-movil'),
    
    # =============================================================================
    # API ENDPOINTS PARA APLICACIÓN REACT NATIVE
    # =============================================================================
    
    # API de Categorías
    path('api/categorias/', CategoriaListView.as_view(), name='categorias-list'),
    
    # API de Productos
    path('api/productos/', ProductoListView.as_view(), name='productos-list'),
    path('api/productos/<int:pk>/', ProductoDetailView.as_view(), name='producto-detail'),
    
    # API de Pedidos
    path('api/pedidos/', ListarPedidosAPI.as_view(), name='listar-pedidos'),
    path('api/pedidos/<int:pk>/', DetallePedidoAPI.as_view(), name='detalle-pedido'),
    path('api/pedidos/pesador/', CrearPedidoPesadorAPI.as_view(), name='crear-pedido-pesador'),
    
    # API de Configuración
    path('api/dolar/', TasaDolarAPI.as_view(), name='tasa-dolar'),
    path('api/reimprimir-ticket/', ReimprimirTicketAPI.as_view(), name='reimprimir-ticket'),
    
    # API de Autenticación
    path('api/auth/login/', LoginAPI.as_view(), name='auth-login'),
    path('api/auth/logout/', LogoutAPI.as_view(), name='auth-logout'),
    path('api/auth/validate/', ValidateTokenAPI.as_view(), name='auth-validate'),
]
