var pedido = [];

var pedido_id = $("#pedido_id").text();
if (pedido_id != "") {
  localStorage.setItem("pedido_id_reimprimir", pedido_id);
}
var precio_total_texto = $("#precio_total").text().replace(',', '.');
var bcv_texto = $("#dolar-p").text().replace(',', '.');

var precio_total = parseFloat(precio_total_texto);
var bcv = parseFloat(bcv_texto);
var pedido_status = $("#pedido_status").text();
var usuario = $("#usuario").text();
var cliente_id = $("#cliente_id").text();
var url_home = $("#url-home").text();
var cliente_nombre = $("#cliente_nombre").text();
var n = "";
var str_numeros = "";
var notas = "";
var productos_todos = $(".todos-los-productos");
var productos_array = [];
var peso = 0;
var imprimiendo = false;
var pedido_cargado_modificado = (pedido_id == "");
var beep = $("#beep").text();

// Variables para Bluetooth LE
const BLUETOOTH_SERVICE_UUID = '6e400001-b5a3-f393-e0a9-e50e24dcca9e';
const BLUETOOTH_NOTIFY_CHARACTERISTIC_UUID = '6e400003-b5a3-f393-e0a9-e50e24dcca9e';
const BLUETOOTH_WRITE_CHARACTERISTIC_UUID = '6e400002-b5a3-f393-e0a9-e50e24dcca9e';

var bluetoothDevice = null;
var bluetoothServer = null;
var bluetoothService = null;
var bluetoothNotifyCharacteristic = null;
var bluetoothWriteCharacteristic = null;
var isBluetoothConnected = false;
var currentBluetoothWeight = 0;
var lastBluetoothWeightData = null;
var bluetoothUpdateInterval = null;
var bluetoothReconnectTimeout = null;
var isBluetoothReconnecting = false;
var bluetoothAutoReconnectAttempts = 0;
var maxBluetoothReconnectAttempts = 3;
var hasBluetoothGetDevicesSupport = false;
var hasBluetoothWatchAdvertisementsSupport = false;
var isBluetoothWatchingAdvertisements = false;
var bluetoothConnectionCheckInterval = null;

// Variables para throttling de peso Bluetooth
const BLUETOOTH_THROTTLE_DELAY = 50; // 25ms entre actualizaciones de peso
var lastBluetoothUpdateTime = 0;

// Función helper para verificar si un pedido está pagado (considera ambos estados)
function isPedidoPagado(status) {
  return status === "Pagado" || status === "Pagado con Crédito";
}

// Función helper para verificar si un pedido es devolución
function isPedidoDevolucion(status) {
  return status === "Devolución";
}

function isPedidoCancelado(status) {
  return status === "Cancelado";
}

function isPedidoInjustificado(status) {
  return status === "Injustificado";
}

// Función helper para verificar si un pedido no puede ser modificado
function isPedidoNoModificable(status) {
  return isPedidoPagado(status) || isPedidoDevolucion(status) || isPedidoCancelado(status) || isPedidoInjustificado(status);
}

for (i = 0; i < productos_todos.length; i++) {
  producto = productos_todos[i].outerText.split("-");
  productos_array.push({
    id: producto[0],
    nombre: producto[1],
    precio: parseFloat(producto[2].replace(',', '.')),
    unidad: producto[3],
    barcode: producto[4],
    moneda: producto[5],
  });
}

function generateUUID() {
  var d = new Date().getTime();
  var uuid = 'xxxxxxxxxxxx4xxxyxxxxxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
      var r = (d + Math.random() * 16) % 16 | 0;
      d = Math.floor(d / 16);
      return (c == 'x' ? r : (r & 0x3 | 0x8)).toString(16);
  });
  return uuid;
}
function NumeroD(num) {
  return (Math.round(num * 100) / 100).toLocaleString("es-ES");
}
const Beep = () => {
  new Audio(beep).play();
};
const capitalize = (str) => str.charAt(0).toUpperCase() + str.slice(1);

function checkProductoCero() {
  str = [];
  pedido.forEach((producto) => {
    if (parseFloat(producto.cantidad) <= 0) {
      str.push(producto.nombre);
    }
  });

  if (str.length > 0) {
    str = str.join(", ");
    $("#hr-ocultar").hide();
    $("#producto-cero-div").show();
    $("#producto-cero").text(str);
    return true;
  } else {
    return false;
  }
}

function buscarCliente() {
  $("#tabla-clientes").html("");
  cedula = $("#buscarCliente").val();

  if (cedula == "") {
    cedula = "*";
  }
  $.ajax({
    url: "buscarClientes/",
    data: { cedula: cedula },
    type: "POST",
    dataType: "json",
    success: function (response) {
      response.forEach((x) => {
        row = `<tr class="cliente-listado">
          <th scope="row">${x.id}</th>
          <td class="cliente-nombre">${x.nombre}</td>
          <td>${x.cedula}</td>
          <td>${x.telefono}</td>
          <td>${x.zona}</td>
          <td>${x.credito}</td>
          <td>${x.deuda_total !== undefined ? '$' + x.deuda_total.toFixed(2) : '$0.00'}</td>
        </tr>`;
        $("#tabla-clientes").append(row);
      });
      cargarCliente();
    },
  });
}
function cambiarPrecioTotal(total) {
  if (isNaN(total)) {
    precioTotalUsd = 0;
    precioTotalBs = 0;
    if (pedido.length == 0) {
      $("#precio-total").text(`Total: 0.00 $ = 0.00 Bs.F`);
    }
    pedido.forEach((p) => {
      moneda = p.moneda;
      // Asegurar que precio y cantidad sean números
      let precio = parseFloat(p.precio);
      let cantidad = parseFloat(p.cantidad);
      
      if (moneda == "USD") {
        precioUsd = precio * cantidad;
      } else if (moneda == "BS") {
        precioUsd = (precio / bcv) * cantidad;
      }

      precioTotalUsd += precioUsd;
      precioTotalBs = precioTotalUsd * bcv;

      $("#precio-total").text(
        `Total: ${NumeroD(precioTotalUsd)}$ = ${NumeroD(precioTotalBs)}Bs.F`
      );
    });
  } else {
    precioTotalUsd = parseFloat(total);
    precioTotalBs = precioTotalUsd * bcv;

    $("#precio-total").text(`Total: ${NumeroD(precioTotalUsd)}$ = ${NumeroD(precioTotalBs)}Bs.F`);
  }
  
  // 🔒 Habilitar/deshabilitar botón PAGAR según el precio total
  if (precioTotalUsd > 0 && !imprimiendo) {
    $(".botonGuardarPedido").prop("disabled", false).removeClass("boton-deshabilitado");
  } else {
    $(".botonGuardarPedido").prop("disabled", true).addClass("boton-deshabilitado");
  }
}
function numerosTeclado(id) {
  $(".boton-calculadora").unbind();
  $(".boton-calculadora").click(function () {
    numero = this.id;
    numero = numero.split("-");
    numero = numero[1];
    response = "";

    if (numero == "enter") {
      if (isNaN(parseFloat(str_numeros))) {
        str_numeros = "";
      } else {
        pedido.forEach((producto) => {
          if (producto.uniqueId == id) {
            cantidad = parseFloat(str_numeros).toFixed(2);
            producto.cantidad = cantidad;
            moneda = producto.moneda;

            precio = producto.precio;

            if (moneda == "USD") {
              precioUsd = precio * cantidad;
              precioBs = precio * bcv * cantidad;
            } else if (moneda == "BS") {
              precioUsd = (precio / bcv) * cantidad;
              precioBs = precio * cantidad;
            }

            precioPorUnidad = ``;
            $("#id-" + id + "> div > div > p").text(
              `${cantidad} ${producto.unidad} en ${NumeroD(precio)} ${
                producto.moneda
              } ${producto.unidad}`
            );

            $("#id-" + id + "> div > div > h6").text(
              `${NumeroD(precioUsd)}$ = ${NumeroD(precioBs)}Bs.F`
            );
          }
        });
        str_numeros = "";
      }
    } else {
      if (this.id == "coma") {
        numero = ".";
      }
      str_numeros += numero;
      pedido.forEach((producto) => {
        if (producto.uniqueId == id) {
          cantidad = parseFloat(str_numeros).toFixed(2);
          producto.cantidad = cantidad;
          moneda = producto.moneda;

          precio = producto.precio;

          if (moneda == "USD") {
            precioUsd = precio * cantidad;
            precioBs = precio * bcv * cantidad;
          } else if (moneda == "BS") {
            precioUsd = (precio / bcv) * cantidad;
            precioBs = precio * cantidad;
          }

          precioPorUnidad = ``;
          $("#id-" + id + "> div > div > p").text(
            `${cantidad} ${producto.unidad} en ${NumeroD(precio)} ${
              producto.moneda
            } ${producto.unidad}`
          );

          $("#id-" + id + "> div > div > h6").text(
            `${NumeroD(precioUsd)}$ = ${NumeroD(precioBs)}Bs.F`
          );
        }
      });
    }

    cambiarPrecioTotal();
  });
}
function scrollProductoEnPedido(id) {
  position = 0;
  for (i in pedido) {
    if (pedido[i].id == id) {
      position = i;
    }
  }
  lista_pedidos = $("#lista-de-pedidos");
  lista_pedidos.scrollTop(position * 73);
}
function cambiarPrecioProductoPedido(id) {
  p_div_producto = $("#id-" + id + "> div > div > p").text();
  $(".pedido-div-producto").css("background-color", "#fff");
  $("#id-" + id).css("background-color", "#C7D4B6");

  $(".boton-borrar").unbind();
  $(".boton-borrar").on("click", function () {
    var found = -1;
    for (i in pedido) {
      // Comparar nombre
      if (pedido[i].uniqueId == id) {
        // Se encontró, guardar posición y salir del ciclo
        found = i;
        break;
      }
    }
    // Si el elemento existe, found será igual o mayor que cero
    if (found > -1) {
      // Eliminar elemento del arreglo
      pedido.splice(found, 1);
      pedido_cargado_modificado = true;
      cambiarPrecioTotal();
      $("#id-" + id).remove();
      cambiarPrecioTotal();
      return 0;
    }
  });
  numerosTeclado(id);
  PesoBalanza(id);
}
// Función para imprimir etiqueta automáticamente después de pesar
function imprimirEtiquetaAutomatica(producto, peso) {
  try {
    // Solo imprimir para productos pre-pesados (unidad != "U")
    if (producto.unidad === "U") {
      return;
    }

    const data = {
      'nombre': (producto.title || '').slice(0, 32),
      'precio_unit': String(producto.precio || 0),
      'moneda': String(producto.moneda || '$'),
      'unidad': String(producto.unidad || 'K'),
      'peso': String(peso),
      'producto_id': String(producto.id || 0),
      'impresora': localStorage.getItem('impresora') || '',
      'copias': '1'
    };

    // Hacer llamada AJAX a la vista de impresión
    $.ajax({
      url: '/pos/pre-pesados/imprimir-etiqueta/',
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
        'X-CSRFToken': getCookie('csrftoken')
      },
      data: data,
      success: function(response) {
        if (response.success) {
          console.log('Etiqueta impresa automáticamente:', response);
          // Mostrar notificación visual opcional
          updatePesoDisplayStatus('Etiqueta impresa', '✓');
          setTimeout(() => {
            updatePesoDisplayStatus('Listo', '');
          }, 2000);
        } else {
          console.error('Error al imprimir etiqueta:', response.error);
        }
      },
      error: function(xhr, status, error) {
        console.error('Error de red al imprimir etiqueta:', error);
      }
    });
  } catch (error) {
    console.error('Error en imprimirEtiquetaAutomatica:', error);
  }
}

function PesoBalanza(id) {
  id = id;
  $("#tecla-peso").unbind();
  $("#tecla-peso").on("click", function () {
    Beep(); // Reproducir sonido al presionar el botón
    const modoBalanza = getModoBalanza();
    
    if (modoBalanza === 'bluetooth') {
      // Usar peso de Bluetooth
      if (isBluetoothConnected && currentBluetoothWeight !== null) {
        peso = currentBluetoothWeight;
        sendBluetoothCommand('B')
        console.log(`Usando peso Bluetooth: ${peso} kg`);
        
        if (!isNaN(peso)) {
          pedido.forEach((producto) => {
            if (producto.uniqueId == id) {
              if (producto.unidad != "U") {
                cantidad = parseFloat(peso).toFixed(2);
                producto.cantidad = cantidad;
                moneda = producto.moneda;
                precio = producto.precio;
                pedido_cargado_modificado = true;

                precioPorUnidad = `${precio} ${moneda}/${producto.unidad}`;
                $("#id-" + id + "> div > div > p").text(
                  `${cantidad} ${producto.unidad} en ${precioPorUnidad}`
                );

                if (moneda == "USD") {
                  precioUsd = precio * cantidad;
                  precioBs = precio * bcv * cantidad;
                } else if (moneda == "BS") {
                  precioUsd = (precio * cantidad) / bcv;
                  precioBs = precio * cantidad;
                }

                $("#id-" + id + "> div > div > h6").text(
                  `${NumeroD(precioUsd)} $ = ${NumeroD(precioBs)} Bs.F`
                );
              }
            }
          });

          cambiarPrecioTotal();
          peso = 0;
        }
      } else {
        alert('Balanza Bluetooth no conectada o sin datos de peso disponibles');
      }
    } else {
      // Usar método tradicional por WiFi/Socket
    var balanza = localStorage.getItem("balanza");
    var data = {
      codigo: "W",
      balanza: balanza,
    };
    $.ajax({
      type: "POST",
      url: "/pos/balanza",
      data: data,
      success: function (response) {
        peso = parseFloat(response);
        if (!isNaN(peso)) {
          pedido.forEach((producto) => {
            if (producto.uniqueId == id) {
              if (producto.unidad != "U") {
                cantidad = parseFloat(peso).toFixed(2);
                producto.cantidad = cantidad;
                moneda = producto.moneda;
                precio = producto.precio;
                pedido_cargado_modificado = true;

                precioPorUnidad = `${precio} ${moneda}/${producto.unidad}`;
                $("#id-" + id + "> div > div > p").text(
                  `${cantidad} ${producto.unidad} en ${precioPorUnidad}`
                );

                if (moneda == "USD") {
                  precioUsd = precio * cantidad;
                  precioBs = precio * bcv * cantidad;
                } else if (moneda == "BS") {
                  precioUsd = (precio * cantidad) / bcv;
                  precioBs = precio * cantidad;
                }

                $("#id-" + id + "> div > div > h6").text(
                  `${NumeroD(precioUsd)} $ = ${NumeroD(precioBs)} Bs.F`
                );
              }
            }
          });

          cambiarPrecioTotal();
          peso = 0;
        }
      },
        error: function() {
          alert('Error conectando con la balanza WiFi');
        }
    });
    }
  });
}
function addEvent(productoid) {
  cambiarPrecioProductoPedido(productoid);

  $(".pedido-div-producto").unbind();
  $(".pedido-div-producto").on("click", function () {
    id = this.id;
    id = id.split("-");
    id = id[1];
    cambiarPrecioProductoPedido(id);
  });
}
function aumentarCantidadUno(id) {
  pedido.forEach((producto) => {
    if (producto.uniqueId == id) {
      if (producto.unidad == "U") {
        cantidad = parseFloat(producto.cantidad).toFixed(2);

        cantidad = parseFloat(cantidad) + 1;
        producto.cantidad = cantidad;
        moneda = producto.moneda;
        pedido_cargado_modificado = true;

        if (moneda == "USD") {
          precioUsd = producto.precio * cantidad;
          precioBs = precioUsd * bcv;
        } else if (moneda == "BS") {
          precioBs = producto.precio * cantidad;
          precioUsd = precioBs / bcv;
        }

        $("#id-" + producto.uniqueId + "> div > div > p").text(
          `${cantidad} ${producto.unidad} en ${NumeroD(
            producto.precio
          )} ${moneda}/${producto.unidad}`
        );
        $("#id-" + producto.uniqueId + "> div > div > h6").text(
          `${NumeroD(precioUsd)}$ = ${NumeroD(precioBs)}Bs.F`
        );
      }
    }
  });
}
function mueveReloj() {
  momentoActual = new Date();
  hora = momentoActual.getHours();
  minuto = momentoActual.getMinutes();
  segundo = momentoActual.getSeconds();

  // Formato 12 horas consistente
  let ampm = hora >= 12 ? 'PM' : 'AM';
  hora = hora % 12;
  hora = hora ? hora : 12; // La hora '0' debería ser '12'

  str_segundo = new String(segundo);
  if (str_segundo.length == 1) segundo = "0" + segundo;

  str_minuto = new String(minuto);
  if (str_minuto.length == 1) minuto = "0" + minuto;

  str_hora = new String(hora);
  if (str_hora.length == 1) hora = "0" + hora;

  horaImprimible = hora + ":" + minuto + ":" + segundo + " " + ampm;

  $("#reloj-span").text(horaImprimible);
  setTimeout("mueveReloj()", 1000);
}
function fechaHoy() {
  const tiempo = Date.now();
  const hoy = new Date(tiempo);
  str = hoy.toLocaleDateString();
  $("#fecha-span").text(str);
}
function VerificarPedidoCargado() {
  pedidoItems = $(".pedido-item > p");
  for (var i = 0; i < pedidoItems.length; i++) {
    itemTexto = pedidoItems[i].innerHTML;
    itemInfoArray = itemTexto.split("-");

    id = parseInt(itemInfoArray[0]);
    nombre = itemInfoArray[1];
    cantidad_texto = itemInfoArray[2].replace(',', '.');
    cantidad = parseFloat(cantidad_texto);
    precio_texto = itemInfoArray[3].replace(',', '.');
    precio = parseFloat(precio_texto);
    unidad = itemInfoArray[4];
    moneda = itemInfoArray[6];
    uniqueId = itemInfoArray[7].trim();
    
    pedido.push({
      id: id,
      uniqueId: uniqueId,
      nombre: nombre,
      precio: precio,
      unidad: unidad,
      cantidad: cantidad,
      moneda: moneda,
    });
  }
  
  // 🔒 Verificar estado del botón PAGAR después de cargar el pedido
  cambiarPrecioTotal();
}
function revisarExisteProductoPedido(id) {
  var f = "no";
  pedido.forEach((p) => {
    if (p.id == id) {
      f = "si";
    }
  });
  return f;
}
function cargarPedido() {
  $(".pedido-listado").unbind();
  $(".pedido-listado").on("click", function () {
    pedido_id = $(this).children().closest("th").text();

    location.assign(`/pos/${pedido_id}`);
  });
}
function buscarProductos() {
  const str_input = document.getElementById("buscar-productos").value.toLowerCase();
  const todosLosProductos = $(".agregar-producto-pedido");
  
  todosLosProductos.each(function() {
    const productoDiv = $(this);
    const textoProducto = productoDiv.find(".todos-los-productos").text();
    const productoInfo = textoProducto.split("-");
    const nombreProducto = productoInfo[1] ? productoInfo[1].toLowerCase() : "";
    
    // Mostrar el producto si el nombre coincide con la búsqueda o si está vacía
    if (str_input === "" || nombreProducto.startsWith(str_input)) {
      productoDiv.show();
    } else {
      productoDiv.hide();
    }
  });
}
function buscarProductoBarcode(scancode) {
  productos_array.forEach((producto) => {
    if (parseInt(producto["barcode"]) == parseInt(scancode)) {
      id = parseInt(producto["id"]);
      nombre = producto["nombre"];
      precio = parseFloat(producto["precio"].toString().replace(',', '.'));
      unidad = producto["unidad"];
      moneda = producto["moneda"];
      cantidad = 1;
      barcode = producto["barcode"];
      precio_display = NumeroD(precio);
      precioUsd = 0;
      precioBs = 0;
      if (moneda == "USD") {
        precioBs = precio * bcv;
        precioUsd = precio;
      } else if (moneda == "BS") {
        precioBs = precio;
        precioUsd = precio / bcv;
      }

      if (revisarExisteProductoPedido(id) == "si") {
        scrollProductoEnPedido(id);
        cambiarPrecioProductoPedido(id);
      } else {
        pedidodiv = `<div id="id-${id}" class="container apuntar mt-1 border pedido-div-producto"><div class="row"><div class="col-6"><h5 class="">${capitalize(
          nombre
        )}</h5><p class="fs-6">1 ${unidad} en ${precio_display}  ${moneda}/${unidad}</p></div><div class="col-6"><h6>${NumeroD(
          precioUsd
        )}$ = ${NumeroD(precioBs)}Bs.F</h6></div></div></div>`;
        $("#lista-de-pedidos").append(pedidodiv);
        pedido.push({
          id: id,
          nombre: nombre,
          precio: precio,
          unidad: unidad,
          cantidad: cantidad,
          barcode: barcode,
          moneda: moneda,
        });
        addEvent(id);
        cambiarPrecioTotal();
      }
    }
  });
}
function cargarCliente() {
  $(".cliente-listado").unbind();
  $(".cliente-listado").on("click", function () {
    cliente_nombre = $(this).children().closest("td").eq(0).text();
    cliente_id = $(this).children().closest("th").text();

    $("#boton-cliente > span").text(cliente_nombre);
    cliente_id = parseInt(cliente_id);
    
    // Si ya existe un pedido que no está pagado, actualizar su cliente
    if (pedido_id !== "nuevo") {
      // Crear y mostrar mensaje de carga
      const loadingDiv = $('<div>', {
        id: 'loading-message',
        text: 'Actualizando cliente... Por favor espere.'
      }).appendTo('body');
      
      // Hacer una petición AJAX para actualizar el cliente del pedido
      $.ajax({
        url: "/pos/actualizar-cliente/",
        type: "POST",
        data: {
          pedido_id: pedido_id,
          cliente_id: cliente_id
        },
        success: function(response) {
          loadingDiv.remove();
          if (response.status === "success") {
            // Mostrar notificación de éxito
            const successDiv = $('<div>', {
              id: 'success-message',
              text: 'Cliente actualizado correctamente'
            }).css({
              'position': 'fixed',
              'top': '50%',
              'left': '50%',
              'transform': 'translate(-50%, -50%)',
              'background-color': 'rgba(40, 167, 69, 0.9)',
              'color': 'white',
              'padding': '20px',
              'border-radius': '5px',
              'z-index': '9999'
            }).appendTo('body');
            
            // Desaparecer después de 2 segundos
            setTimeout(function() {
              successDiv.fadeOut(500, function() {
                $(this).remove();
              });
            }, 2000);
          } else {
            // Mostrar mensaje de error
            alert("Error al actualizar el cliente: " + response.message);
          }
        }
      });
    }
    
    $("#lista-clientes-div").hide();
    $("#hr-ocultar").show();
  });
}

function checkCaja() {
  dolar = localStorage.getItem("total_dolar");
  bolivar = localStorage.getItem("total_bolivar");
  if (!dolar || !bolivar) {
    $("#abrir-caja-div").show();
    $("#hr-ocultar").hide();
  }
}
function nombreCliente() {
  if (!cliente_nombre == "") {
    $("#boton-cliente > span").text(cliente_nombre);
  }
}
function multiplicarPrecioProductosPedidos() {
  $(".div-producto-cargado").each(function (x) {
    texto_producto = $("#" + this.id + "> p").text();
    precio_texto = texto_producto.split("-")[3].replace(',', '.');
    cantidad_texto = texto_producto.split("-")[2].replace(',', '.');
    precio = parseFloat(precio_texto);
    cantidad = parseFloat(cantidad_texto);
    moneda = texto_producto.split("-")[6];

    if (moneda == "USD") {
      precioUsd = precio * cantidad;
      precioBs = precioUsd * bcv;
    } else if (moneda == "BS") {
      precioBs = precio * cantidad;
      precioUsd = precioBs / bcv;
    }
    x = $("#" + this.id + "> div > div > h6").text(
      `${NumeroD(precioUsd)}$ = ${NumeroD(precioBs)} Bs.F`
    );
  });
}
// ==================== FUNCIONES DE PANTALLA COMPLETA ====================

// Detectar si el navegador es Chrome
function isChrome() {
  return /Chrome/.test(navigator.userAgent) && /Google Inc/.test(navigator.vendor);
}

// Comprobar si la API de pantalla completa está disponible
function isFullscreenSupported() {
  return !!(document.documentElement.requestFullscreen ||
            document.documentElement.mozRequestFullScreen ||
            document.documentElement.webkitRequestFullscreen ||
            document.documentElement.msRequestFullscreen);
}

// Entrar en pantalla completa
function requestFullscreen() {
  const element = document.documentElement;
  
  if (element.requestFullscreen) {
    return element.requestFullscreen();
  } else if (element.mozRequestFullScreen) {
    return element.mozRequestFullScreen();
  } else if (element.webkitRequestFullscreen) {
    return element.webkitRequestFullscreen();
  } else if (element.msRequestFullscreen) {
    return element.msRequestFullscreen();
  }
  return Promise.reject(new Error('Pantalla completa no soportada'));
}

// Verificar si ya está en pantalla completa
function isFullscreen() {
  return !!(document.fullscreenElement ||
            document.mozFullScreenElement ||
            document.webkitFullscreenElement ||
            document.msFullscreenElement);
}

function procesarPrePesado(scancode) {
  //logica de pre pesados
  console.log(scancode);
  
  // Verificar que el código tenga 13 dígitos y empiece con "21"
  if (scancode.length !== 13 || !scancode.startsWith("21")) {
    console.log("Código de barras inválido para producto pre-pesado");
    return;
  }
  
  // Extraer el ID del producto (posiciones 2-6, 5 dígitos)
  const producto_id_str = scancode.substring(2, 7);
  const producto_id = parseInt(producto_id_str);
  
  // Extraer el peso (posiciones 7-11, 5 dígitos en centenas de gramos)
  const peso_str = scancode.substring(7, 12);
  const peso_centenas_gramos = parseInt(peso_str);
  const peso_kg = peso_centenas_gramos / 100; // Convertir a kg
  
  console.log(`Producto ID: ${producto_id}, Peso: ${peso_kg} kg`);
  
  // Buscar el producto en el array
  const producto = productos_array.find(p => parseInt(p.id) === producto_id);
  
  if (!producto) {
    console.log(`Producto con ID ${producto_id} no encontrado`);
    return;
  }
  
  // Extraer datos del producto
  const id = parseInt(producto.id);
  const nombre = producto.nombre;
  const precio = parseFloat(producto.precio.toString().replace(',', '.'));
  const unidad = producto.unidad;
  const moneda = producto.moneda;
  const cantidad = parseFloat(peso_kg.toFixed(2)); // Usar el peso del código de barras
  const barcode = scancode; // Usar el código completo como barcode
  const precio_display = NumeroD(precio);
  
  let precioUsd = 0;
  let precioBs = 0;
  
  if (moneda == "USD") {
    precioBs = precio * bcv * cantidad;
    precioUsd = precio * cantidad;
  } else if (moneda == "BS") {
    precioBs = precio * cantidad;
    precioUsd = (precio * cantidad) / bcv;
  }
  
  // Generar un ID único para este producto pre-pesado
  const uniqueId = generateUUID();
  
  // Crear el div del producto en el pedido
  const pedidodiv = `<div id="id-${uniqueId}" class="container apuntar mt-1 border pedido-div-producto"><div class="row"><div class="col-6"><h5 class="">${capitalize(
    nombre
  )}</h5><p class="fs-6">${cantidad} ${unidad} en ${precio_display} ${moneda}/${unidad}</p></div><div class="col-6"><h6>${NumeroD(
    precioUsd
  )}$ = ${NumeroD(precioBs)}Bs.F</h6></div></div></div>`;
  
  $("#lista-de-pedidos").append(pedidodiv);
  
  // Agregar al pedido con uniqueId para productos pre-pesados
  pedido.push({
    id: id,
    uniqueId: uniqueId,
    nombre: nombre,
    precio: precio,
    unidad: unidad,
    cantidad: cantidad,
    barcode: barcode,
    moneda: moneda,
  });
  
  addEvent(uniqueId);
  cambiarPrecioTotal();
  pedido_cargado_modificado = true;
}

// Mostrar overlay de pantalla completa siempre al entrar al POS
function showFullscreenOverlay() {
  // Mostrar siempre si hay soporte para pantalla completa y no está ya en pantalla completa
  if (isFullscreenSupported() && !isFullscreen()) {
    // SIEMPRE mostrar el overlay, independientemente del modo o sesión
    $('#fullscreen-overlay').fadeIn(50);
    console.log('🖥️ Overlay de pantalla completa mostrado - SIEMPRE PEDIRÁ PANTALLA COMPLETA');
  }
}

// Ocultar overlay de pantalla completa
function hideFullscreenOverlay() {
  $('#fullscreen-overlay').fadeOut(50);
  // NO marcar como mostrado para permitir que se muestre siempre
  console.log('🔗 Overlay de pantalla completa ocultado - se mostrará de nuevo la próxima vez');
}

$(document).ready(function () {
  // ==================== OVERLAY DE PANTALLA COMPLETA ====================
  
  // Mostrar overlay de pantalla completa si se cumplen las condiciones
  // showFullscreenOverlay(); // COMENTADO: Modal de pantalla completa desactivado
  // Inicializar el botón mejorado al cargar la página
  initBotonGuardarMejorado();
  
  // ==================== INICIALIZACIÓN BALANZA RÁPIDA ====================
  
  // Inicializar funcionalidad de balanza rápida
  actualizarVisibilidadBotonBalanza();
  
  // Event listener para el botón de balanza rápida
  $('#boton-balanza-rapida').on('click', function() {
    abrirModalBalanzaRapida();
  });
  
  // Escuchar cambios en localStorage para actualizar UI
  window.addEventListener('storage', function(e) {
    if (e.key === 'modoImpresion') {
      actualizarVisibilidadBotonBalanza();
    }
    if (e.key === 'balanza') {
      actualizarTextoBotonBalanza();
    }
  });
  
  // Evento para botón de activar pantalla completa
  // $('#btn-fullscreen').on('click', function() {
  //   requestFullscreen()
  //     .then(function() {
  //       console.log('✅ Pantalla completa activada');
  //       hideFullscreenOverlay();
  //     })
  //     .catch(function(error) {
  //       console.error('❌ Error al activar pantalla completa:', error);
  //       alert('No se pudo activar la pantalla completa. Puede intentar presionando F11.');
  //       hideFullscreenOverlay();
  //     });
  // });
  
  // Evento para botón de continuar sin pantalla completa
  // $('#btn-skip-fullscreen').on('click', function() {
  //   console.log('⏭️ Usuario continuó sin pantalla completa');
  //   hideFullscreenOverlay();
  // });
  
  // Detectar salida de pantalla completa con ESC
  document.addEventListener('fullscreenchange', function() {
    if (!isFullscreen()) {
      console.log('🔚 Salió de pantalla completa');
    }
  });
  
  // ==================== MODALES DE PEDIDOS ====================
  
  // Si el modal de pedido pagado existe, mostrarlo al cargar la pagina
  
  if ($('#pedidoPagadoModal').length) {
    var pedidoPagadoModal = new bootstrap.Modal(document.getElementById('pedidoPagadoModal'));
    pedidoPagadoModal.show();
    
    // Agregar funcionalidad al botón Volver
    $("#btn-volver-pedido-pagado").on("click", function() {
      const currentUrl = window.location.pathname;
      const referrer = document.referrer;
      
      // Cerrar el modal primero
      pedidoPagadoModal.hide();
      
      // Si estamos en la página principal de POS (sin ID específico) o si venimos de otra página
      if (currentUrl === "/pos/" || currentUrl === "/pos") {
        // Quedarse en la página actual (modal simplemente se cierra)
      } else if (referrer && !referrer.includes("/pagar-credito/")) {
        // Si hay una página referente y no es la de pagar crédito, volver a esa página
        window.location.href = referrer;
      } else {
        // De lo contrario, ir a la página principal de POS
        window.location.href = "/pos/";
      }
    });
  }
  
  // Si el modal de pedido devolución existe, mostrarlo al cargar la página
  if ($('#pedidoDevolucionModal').length) {
    var pedidoDevolucionModal = new bootstrap.Modal(document.getElementById('pedidoDevolucionModal'));
    pedidoDevolucionModal.show();
    
    // Agregar funcionalidad al botón Volver
    $("#btn-volver-pedido-devolucion").on("click", function() {
      const currentUrl = window.location.pathname;
      const referrer = document.referrer;
      
      // Cerrar el modal primero
      pedidoDevolucionModal.hide();
      
      // Si estamos en la página principal de POS (sin ID específico) o si venimos de otra página
      if (currentUrl === "/pos/" || currentUrl === "/pos") {
        // Quedarse en la página actual (modal simplemente se cierra)
      } else if (referrer && !referrer.includes("/pagar-credito/")) {
        // Si hay una página referente y no es la de pagar crédito, volver a esa página
        window.location.href = referrer;
      } else {
        // De lo contrario, ir a la página principal de POS
        window.location.href = "/pos/";
      }
    });
  }

  // Si el modal de pedido cancelado existe, mostrarlo al cargar la página
  if ($('#pedidoCanceladoModal').length) {
    var pedidoCanceladoModal = new bootstrap.Modal(document.getElementById('pedidoCanceladoModal'));
    pedidoCanceladoModal.show();
    
    // Agregar funcionalidad al botón Volver
    $("#btn-volver-pedido-cancelado").on("click", function() {
      const currentUrl = window.location.pathname;
      const referrer = document.referrer;
      
      // Cerrar el modal primero
      pedidoCanceladoModal.hide();
      
      // Si estamos en la página principal de POS (sin ID específico) o si venimos de otra página
      if (currentUrl === "/pos/" || currentUrl === "/pos") {
        // Quedarse en la página actual (modal simplemente se cierra)
      } else if (referrer && !referrer.includes("/pagar-credito/")) {
        // Si hay una página referente y no es la de pagar crédito, volver a esa página
        window.location.href = referrer;
      } else {
        // De lo contrario, ir a la página principal de POS
        window.location.href = "/pos/";
      }
    });
  }

  // Si el modal de pedido injustificado existe, mostrarlo al cargar la página
  if ($('#pedidoInjustificadoModal').length) {
    var pedidoInjustificadoModal = new bootstrap.Modal(document.getElementById('pedidoInjustificadoModal'));
    pedidoInjustificadoModal.show();
    
    // Agregar funcionalidad al botón Volver
    $("#btn-volver-pedido-injustificado").on("click", function() {
      const currentUrl = window.location.pathname;
      const referrer = document.referrer;
      
      // Cerrar el modal primero
      pedidoInjustificadoModal.hide();
      
      // Si estamos en la página principal de POS (sin ID específico) o si venimos de otra página
      if (currentUrl === "/pos/" || currentUrl === "/pos") {
        // Quedarse en la página actual (modal simplemente se cierra)
      } else if (referrer && !referrer.includes("/pagar-credito/")) {
        // Si hay una página referente y no es la de pagar crédito, volver a esa página
        window.location.href = referrer;
      } else {
        // De lo contrario, ir a la página principal de POS
        window.location.href = "/pos/";
      }
    });
  }

  VerificarPedidoCargado();
  multiplicarPrecioProductosPedidos();
  nombreCliente();
  ///checkCaja();
  fechaHoy();
  mueveReloj();
  cambiarPrecioTotal();
  
  
  $("#boton-cerrar-caja").on("click", function () {
    $("#cerrar-caja-div").show();

  });


  $("#cerrar-caja-submit").on("click", function() {
    const denominacionesUSD = {
      "1": parseInt($("#inputCD1").val()) || 0,
      "5": parseInt($("#inputCD5").val()) || 0,
      "10": parseInt($("#inputCD10").val()) || 0,
      "20": parseInt($("#inputCD20").val()) || 0,
      "50": parseInt($("#inputCD50").val()) || 0,
      "100": parseInt($("#inputCD100").val()) || 0
    };
  
    const denominacionesBs = {
      "0.5": parseInt($("#inputCB05").val()) || 0,
      "1": parseInt($("#inputCB1").val()) || 0,
      "5": parseInt($("#inputCB5").val()) || 0,
      "10": parseInt($("#inputCB10").val()) || 0,
      "20": parseInt($("#inputCB20").val()) || 0,
      "50": parseInt($("#inputCB50").val()) || 0,
      "100": parseInt($("#inputCB100").val()) || 0
    };

    const data = {
      denominacionesUSD: JSON.stringify(denominacionesUSD),
      denominacionesBs: JSON.stringify(denominacionesBs),
      impresora: localStorage.getItem("impresora")
    };


    $.ajax({
      url: "/pos/cerrar-caja/",
      type: "POST",
      data: data,
      success: function(response) {
        $("#estado-caja-texto").text("CERRADA");
        $("#boton-estado-caja").css("background-color", "#dc3545");
        $("#cerrar-caja-div").hide();
        
        if (response.diferencias) {
          const difBs = response.diferencias.BS || {};
          const difUsd = response.diferencias.USD || {};
          
          // Verificar si hay diferencias
          const hayDiferencias = Object.values(difBs).some(v => parseFloat(v) !== 0) || 
                                Object.values(difUsd).some(v => parseFloat(v) !== 0);
          
          if (!hayDiferencias) {
            alert("No se encontraron diferencias en el cierre de caja.");
            return;
          }
          
          let mensaje = "Diferencias encontradas:\n\n";
          mensaje += "BOLIVARES          |          DOLARES\n";
          mensaje += "----------------------------------------\n";
          
          // Obtener todas las denominaciones para procesar en paralelo
          const todasDenominaciones = new Set([
            ...Object.keys(difBs),
            ...Object.keys(difUsd)
          ].sort((a, b) => parseFloat(a) - parseFloat(b)));
          
          // Procesar cada denominación
          todasDenominaciones.forEach(denom => {
            const diffBs = parseFloat(difBs[denom] || 0);
            const diffUsd = parseFloat(difUsd[denom] || 0);
            
            if (diffBs !== 0 || diffUsd !== 0) {
              const bsStr = diffBs !== 0 ? `${denom}Bs: ${diffBs > 0 ? '+' : ''}${diffBs}` : '          ';
              const usdStr = diffUsd !== 0 ? `${denom}$: ${diffUsd > 0 ? '+' : ''}${diffUsd}` : '          ';
              mensaje += `${bsStr.padEnd(15)} | ${usdStr.padStart(15)}\n`;
            }
          });
          
          alert(mensaje);
        }
      },
      error: function(xhr) {
        alert(xhr.responseJSON.message);
      }
    });
  });

  onScan.attachTo(document, {
    minLength: 2,
  });
  document.addEventListener("scan", function (sCode) {
    scancode = sCode["detail"]["scanCode"];
    scancode = scancode.toString();
    if (scancode.toLowerCase().startsWith("pp")) {
      id = scancode.substring(2);
      location.assign(`/pos/${id}`);
    } else if (scancode.toLowerCase().startsWith("21")) {
      //logica de pre pesados
      procesarPrePesado(scancode);
    } else {
      if (!isPedidoPagado(pedido_status)) {
        buscarProductoBarcode(scancode);
      }
    }
  });

  $("#caja-form-btn").on("click", function () {
    abrirCaja();
    location.reload();
  });

  $(".boton-reimprimir").on("click", function () {
    // 🚀 NUEVA FUNCIONALIDAD: Reimpresión no-bloqueante
    procesarReimpresionRapida();
  });

  if (!isPedidoPagado(pedido_status)) {
    $(".pedido-div-producto").on("click", function () {
      id = this.id;
      id = id.split("-");
      id = id[1];

      cambiarPrecioProductoPedido(id);
    });

    $(".agregar-producto-pedido").on("click", function () {
      checkProductoCero();
      texto = $("#" + this.id + "> p").text();
      productoInfo = texto.split("-");
      productoid = parseInt(productoInfo[0]);
      nombre = productoInfo[1];
      unidad = productoInfo[3];
      
      Beep();
      if(unidad == "U" && revisarExisteProductoPedido(productoid) == "si"){
        pedido.forEach((p) => {
          if (p.id == productoid) {
            scrollProductoEnPedido(productoid);
            aumentarCantidadUno(p.uniqueId);
            cambiarPrecioProductoPedido(p.uniqueId);
            cambiarPrecioTotal();
          }
        });
          
      }else {
        uniqueId = generateUUID();
        pedido_cargado_modificado = true;
        
        
        if (unidad == "U") {
          cantidad = 1;
        } else if (unidad == "K") {
          cantidad = 0;
        }
        moneda = productoInfo[5];

        precio = parseFloat(productoInfo[2].replace(',', '.'));
        if (moneda == "USD") {
          precioUsd = precio;
          precioBs = precioUsd * bcv;
          precio_display = NumeroD(precioUsd);
        } else if (moneda == "BS") {
          precioBs = precio;
          precioUsd = precioBs / bcv;
          precio_display = NumeroD(precioBs);
        }
        pedidodiv = `<div id="id-${uniqueId}" class="container apuntar mt-1 border pedido-div-producto"><div class="row"><div class="col-6"><h5 class="">${capitalize(
          nombre
        )}</h5><p class="fs-6">${cantidad} ${unidad} en ${precio_display}   ${moneda}/${unidad}</p></div><div class="col-6"><h6>${NumeroD(
          precioUsd
        )}$ = ${NumeroD(precioBs)}Bs.F</h6></div></div></div>`;

        $("#lista-de-pedidos").append(pedidodiv);
        lista_pedidos = $("#lista-de-pedidos");

        pedido.push({
          uniqueId: uniqueId,
          id: productoid,
          nombre: nombre,
          precio: precio,
          unidad: unidad,
          cantidad: cantidad,
          moneda: moneda,
        });
        numero_productos = pedido.length;
        height_scroll = numero_productos * 73;
        lista_pedidos.scrollTop(height_scroll);
        addEvent(uniqueId);
        cambiarPrecioTotal();
      }
    });

    $("#boton-cliente").on("click", function () {
      // No permitir cambiar el cliente si el pedido está pagado o es devolución
      if (isPedidoNoModificable(pedido_status)) {
        if (isPedidoDevolucion(pedido_status)) {
          alert("No se puede cambiar el cliente de un pedido marcado como DEVOLUCIÓN");
        } else {
          alert("No se puede cambiar el cliente de un pedido ya pagado");
        }
        return;
      }
      
      if ($("#lista-clientes-div").css("display") == "none") {
        $("#tabla-clientes").html("");
        $.ajax({
          url: "clientesList/",
          type: "POST",
          dataType: "json",
          success: function (response) {
            response.forEach((x) => {
              fecha = x.fecha;
              row = `<tr class="cliente-listado">
                <th scope="row">${x.pk}</th>
                <td>${x.nombre}</td>
                <td>${x.cedula}</td>
                <td>${x.telefono}</td>
                <td>${x.zona_vive}</td>
                <td>${x.credito}</td>
                <td>${x.deuda_total !== undefined ? '$' + x.deuda_total.toFixed(2) : '$0.00'}</td>
              </tr>`;
              $("#tabla-clientes").append(row);
            });
            cargarCliente();
          },
        });
        $("#buscarClienteBtn").on("click", function () {
          buscarCliente();
        });
      }
      $("#lista-clientes-div").show();
      $("#hr-ocultar").hide();
    });
    $("#cerrar-listado-clientes").on("click", function () {
      $("#lista-clientes-div").hide();
      $("#hr-ocultar").show();
    });
    $("#notas-boton").on("click", function () {
      $("#notas-div").show();
      $("#hr-ocultar").hide();
    });
    $("#cerrar-notas").on("click", function () {
      $("#notas-div").hide();
      $("#hr-ocultar").show();
    });
    $(".filtrar-por-categoria").on("click", function () {
      var textoCategoria = $("#" + this.id + "> p").text();
      var categoriaInfo = textoCategoria.split("-");
      var categoriaId = categoriaInfo[0];
      if (this.id == "categoria-div-todas") {
        categoriaId = "0";
      }
      
      // Filtrado local en frontend
      filtrarProductosPorCategoria(categoriaId);
    });
  }

  $("#boton-listar-pedidos").on("click", function () {
    if ($("#lista-pedidos-div").css("display") == "none") {
      $("#tabla-pedidos").html("");
      $.ajax({
        url: "pedidosList/",
        type: "POST",
        dataType: "json",
        success: function (response) {
          response.forEach((x) => {
            fecha = x.fecha;
            const cajeroDisplay = x.cajero || "-";
            const pesadorDisplay = x.pesador || "-";  // 🎯 NUEVO: Obtener pesador
            if (x.status == "Por pagar") {
              row = `<tr class="pedido-listado" style="background-color: #efcaca;" ><th scope="row">${
                x.pk
              }</th><td>${fecha.slice(0, 10)}</td><td>${x.cliente}</td><td>${
                cajeroDisplay
              }</td><td>${pesadorDisplay}</td><td>${NumeroD(x.preciototal)}</td><td>${
                x.status
              }</td></tr>`;
            }
            if (x.status == "Pagado" || x.status == "Pagado con Crédito") {
              row = `<tr class="pedido-listado" style="background-color: #80a77b;"><th scope="row">${
                x.pk
              }</th><td>${fecha.slice(0, 10)}</td><td>${x.cliente}</td><td>${
                cajeroDisplay
              }</td><td>${pesadorDisplay}</td><td>${NumeroD(x.preciototal)}</td><td>${
                x.status
              }</td></tr>`;
            }
            if (x.status == "Devolución") {
              row = `<tr class="pedido-listado" style="background-color: #ffc107; color: #000;"><th scope="row">${
                x.pk
              }</th><td>${fecha.slice(0, 10)}</td><td>${x.cliente}</td><td>${
                cajeroDisplay
              }</td><td>${pesadorDisplay}</td><td>${NumeroD(x.preciototal)}</td><td>${
                x.status
              }</td></tr>`;
            }

            $("#tabla-pedidos").append(row);
          });
          cargarPedido();
        },
      });
    }
    $("#lista-pedidos-div").show();
    $("#hr-ocultar").hide();
  });

  $("#cerrar-listado-pedidos").on("click", function () {
    $("#lista-pedidos-div").hide();
    $("#hr-ocultar").show();
  });

  // 🎯 NUEVO: Botón para ver todos los pedidos sin restricción de roles
  // Este botón permite a cualquier usuario ver los últimos 100 pedidos sin importar su rol
  // Útil para supervisores y administradores que necesitan ver todos los pedidos
  $("#ver-todos-pedidos-btn").on("click", function () {
    $("#tabla-pedidos").html("");
    $.ajax({
      url: "pedidosList/todos/",
      type: "POST",
      dataType: "json",
      success: function (response) {
        response.forEach((x) => {
          fecha = x.fecha;
          const cajeroDisplay = x.cajero || "-";
          const pesadorDisplay = x.pesador || "-";
          if (x.status == "Por pagar") {
            row = `<tr class="pedido-listado" style="background-color: #efcaca;" ><th scope="row">${
              x.pk
            }</th><td>${fecha.slice(0, 10)}</td><td>${x.cliente}</td><td>${
              cajeroDisplay
            }</td><td>${pesadorDisplay}</td><td>${NumeroD(x.preciototal)}</td><td>${
              x.status
            }</td></tr>`;
          }
          if (x.status == "Pagado" || x.status == "Pagado con Crédito") {
            row = `<tr class="pedido-listado" style="background-color: #80a77b;"><th scope="row">${
              x.pk
            }</th><td>${fecha.slice(0, 10)}</td><td>${x.cliente}</td><td>${
              cajeroDisplay
            }</td><td>${pesadorDisplay}</td><td>${NumeroD(x.preciototal)}</td><td>${
              x.status
            }</td></tr>`;
          }
          if (x.status == "Devolución") {
            row = `<tr class="pedido-listado" style="background-color: #ffc107; color: #000;"><th scope="row">${
              x.pk
            }</th><td>${fecha.slice(0, 10)}</td><td>${x.cliente}</td><td>${
              cajeroDisplay
            }</td><td>${pesadorDisplay}</td><td>${NumeroD(x.preciototal)}</td><td>${
              x.status
            }</td></tr>`;
          }
          if (x.status == "Cancelado") {
            row = `<tr class="pedido-listado" style="background-color: #f8d7da; color: #721c24;"><th scope="row">${
              x.pk
            }</th><td>${fecha.slice(0, 10)}</td><td>${x.cliente}</td><td>${
              cajeroDisplay
            }</td><td>${pesadorDisplay}</td><td>${NumeroD(x.preciototal)}</td><td>${
              x.status
            }</td></tr>`;
          }
          if (x.status == "Injustificado") {
            row = `<tr class="pedido-listado" style="background-color: #e2e3e5; color: #495057;"><th scope="row">${
              x.pk
            }</th><td>${fecha.slice(0, 10)}</td><td>${x.cliente}</td><td>${
              cajeroDisplay
            }</td><td>${pesadorDisplay}</td><td>${NumeroD(x.preciototal)}</td><td>${
              x.status
            }</td></tr>`;
          }
          if (x.status == "Entregado") {
            row = `<tr class="pedido-listado" style="background-color: #d4edda; color: #155724;"><th scope="row">${
              x.pk
            }</th><td>${fecha.slice(0, 10)}</td><td>${x.cliente}</td><td>${
              cajeroDisplay
            }</td><td>${pesadorDisplay}</td><td>${NumeroD(x.preciototal)}</td><td>${
              x.status
            }</td></tr>`;
          }
          if (x.status == "Despachado") {
            row = `<tr class="pedido-listado" style="background-color: #cce5ff; color: #004085;"><th scope="row">${
              x.pk
            }</th><td>${fecha.slice(0, 10)}</td><td>${x.cliente}</td><td>${
              cajeroDisplay
            }</td><td>${pesadorDisplay}</td><td>${NumeroD(x.preciototal)}</td><td>${
              x.status
            }</td></tr>`;
          }
          if (x.status == "Procesando") {
            row = `<tr class="pedido-listado" style="background-color: #fff3cd; color: #856404;"><th scope="row">${
              x.pk
            }</th><td>${fecha.slice(0, 10)}</td><td>${x.cliente}</td><td>${
              cajeroDisplay
            }</td><td>${pesadorDisplay}</td><td>${NumeroD(x.preciototal)}</td><td>${
              x.status
            }</td></tr>`;
          }

          $("#tabla-pedidos").append(row);
        });
        cargarPedido();
      },
    });
  });

  $(".nuevo-pedido").on("click", function () {
    location.assign("/pos");
  });

  $("#guardar-notas").on("click", function () {
    notas = $("#notas-textarea").val();
  });

  $("#buscar-pedido-pos-btn").on("click", function () {
    id = $("#buscar-pedido-pos").val();
    if (id == "") {
      $("#tabla-pedidos").html("");
      $.ajax({
        url: "pedidosList/",
        type: "POST",
        dataType: "json",
        success: function (response) {
          response.forEach((x) => {
            fecha = x.fecha;
            const cajeroDisplay = x.cajero || "-";
            const pesadorDisplay = x.pesador || "-";  // 🎯 NUEVO: Obtener pesador
            if (x.status == "Por pagar") {
              row = `<tr class="pedido-listado" style="background-color: #efcaca;" ><th scope="row">${
                x.pk
              }</th><td>${fecha.slice(0, 10)}</td><td>${
                x.cliente
              }</td><td>${cajeroDisplay}</td><td>${pesadorDisplay}</td><td>${NumeroD(
                x.preciototal
              )}</td><td>${x.status}</td></tr>`;
            }
            if (x.status == "Pagado" || x.status == "Pagado con Crédito") {
              row = `<tr class="pedido-listado" style="background-color: #80a77b;"><th scope="row">${
                x.pk
              }</th><td>${fecha.slice(0, 10)}</td><td>${
                x.cliente
              }</td><td>${cajeroDisplay}</td><td>${pesadorDisplay}</td><td>${NumeroD(
                x.preciototal
              )}</td><td>${x.status}</td></tr>`;
            }
            if (x.status == "Devolución") {
              row = `<tr class="pedido-listado" style="background-color: #ffc107; color: #000;"><th scope="row">${
                x.pk
              }</th><td>${fecha.slice(0, 10)}</td><td>${
                x.cliente
              }</td><td>${cajeroDisplay}</td><td>${pesadorDisplay}</td><td>${NumeroD(
                x.preciototal
              )}</td><td>${x.status}</td></tr>`;
            }
            $("#tabla-pedidos").append(row);
          });
          cargarPedido();
        },
      });
    } else {
      $("#tabla-pedidos").html("");
      $.ajax({
        type: "POST",
        url: "pedidosList/buscarPedido/",
        data: { id: id },
        success: function (pedido) {
          pedido = JSON.parse(pedido);

          fecha = pedido.fecha;
          const cajeroDisplay = pedido.cajero || "-";
          const pesadorDisplay = pedido.pesador || "-";  // 🎯 NUEVO: Obtener pesador
          row = `<tr class="pedido-listado" ><th scope="row">${
            pedido.id
          }</th><td>${fecha.slice(0, 10)}</td><td>${pedido.cliente}</td><td>${
            cajeroDisplay
          }</td><td>${pesadorDisplay}</td><td>${NumeroD(pedido.total)}</td><td>${
            pedido.estado
          }</td></tr>`;
          $("#tabla-pedidos").append(row);
          cargarPedido();
        },
      });
    }
  });

  document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("input[type=text]").forEach((node) =>
      node.addEventListener("keypress", (e) => {
        if (e.keyCode == 13) {
          e.preventDefault();
        }
      })
    );
  });

  // Configurar el botón de balanza en el header
    $('#boton-balanza-bluetooth').on('click', function() {
      $('#configurarBalanzaModal').modal('show');
      
      // Cargar configuración actual
      const modoActual = getModoBalanza();
      $(`input[name="modoBalanza"][value="${modoActual}"]`).prop('checked', true);
      
      // Mostrar/ocultar configuraciones según el modo
      if (modoActual === 'wifi') {
        $('#configuracion-wifi').show();
        $('#configuracion-bluetooth').hide();
      } else {
        $('#configuracion-wifi').hide();
        $('#configuracion-bluetooth').show();
      }
      
      updateBluetoothUIState();
    });

          // Event listener para cambio de modo de balanza
      $('input[name="modoBalanza"]').on('change', function() {
        const modo = $(this).val();
        if (modo === 'wifi') {
          $('#configuracion-wifi').show();
          $('#configuracion-bluetooth').hide();
        } else {
          $('#configuracion-wifi').hide();
          $('#configuracion-bluetooth').show();
        }
      });

    // Event listener para conectar Bluetooth
    $('#conectar-bluetooth-btn').on('click', async function() {
      try {
        await connectBluetoothDevice();
      } catch (error) {
        console.error('Error conectando Bluetooth:', error);
        alert('Error conectando a la balanza Bluetooth: ' + error.message);
      }
    });

    // Event listener para desconectar Bluetooth
    $('#desconectar-bluetooth-btn').on('click', function() {
      disconnectBluetoothDevice();
    });

          // Event listener para guardar configuración
      $('#guardar-configuracion-balanza').on('click', function() {
        const modoSeleccionado = $('input[name="modoBalanza"]:checked').val();
        
        setModoBalanza(modoSeleccionado);
        $('#configurarBalanzaModal').modal('hide');
        
        // Actualizar UI
        updateBluetoothUIState();
        
        // Acciones según el modo seleccionado
        if (modoSeleccionado === 'bluetooth') {
          // Mostrar overlay de pantalla completa al cambiar a modo Bluetooth
          setTimeout(function() {
            // Mostrar el overlay - ahora siempre se muestra sin importar la sesión
            showFullscreenOverlay();
          }, 100);
        }
      });

    // Verificar APIs experimentales de Bluetooth
    checkBluetoothExperimentalAPIs();
    
    // Inicialización automática de Bluetooth si está configurado
    const modoBalanza = getModoBalanza();
    if (modoBalanza === 'bluetooth') {
      // Intentar reconexión automática si hay dispositivo guardado
      const savedDevice = getSavedBluetoothDevice();
      if (savedDevice) {
        console.log(`📱 Dispositivo Bluetooth guardado encontrado: ${savedDevice.name}`);
        const savedTime = new Date(savedDevice.timestamp).toLocaleString();
        console.log(`📅 Guardado el: ${savedTime}`);
        
        // Solo intentar reconexión automática si getDevices() está disponible
        if (hasBluetoothGetDevicesSupport) {
          console.log('🔄 Intentando reconexión automática...');
          setTimeout(async () => {
            try {
              const reconnected = await attemptBluetoothAutoReconnect();
              if (reconnected) {
                console.log('🎉 ¡Reconexión automática exitosa!');
              } else {
                console.log('⚠️ Reconexión automática falló. Conecta manualmente si es necesario.');
              }
            } catch (error) {
              console.error('Error en reconexión automática inicial:', error);
            }
          }, 1500);
        } else {
          console.log('ℹ️ Reconexión automática requiere APIs experimentales habilitadas');
        }
      } else {
        console.log('ℹ️ No hay dispositivo Bluetooth guardado. Usa el botón para conectar uno.');
      }
    }
    
    // Manejar cambios de visibilidad de la página para reconexión
    document.addEventListener('visibilitychange', function() {
      if (!document.hidden && !isBluetoothConnected && hasBluetoothGetDevicesSupport && getModoBalanza() === 'bluetooth') {
        const savedDevice = getSavedBluetoothDevice();
        if (savedDevice) {
          console.log('👁️ Página visible de nuevo. Verificando conexión Bluetooth...');
          setTimeout(async () => {
            try {
              await attemptBluetoothAutoReconnect();
            } catch (error) {
              console.error('Error en verificación de conexión:', error);
            }
          }, 2000);
        }
      }
    });

    // Actualizar estado inicial de la UI
    updateBluetoothUIState();
    
    // Inicializar visibilidad del display según modo guardado
    const modoInicial = getModoBalanza();
    if (modoInicial === 'bluetooth') {
      $('#display-peso-bluetooth').show();
    } else {
      $('#display-peso-bluetooth').hide();
    }
    
    // Agregar hotkey para limpiar dispositivo Bluetooth guardado (Ctrl + Shift + B)
    $(document).on('keydown', function(e) {
      if (e.ctrlKey && e.shiftKey && e.keyCode === 66) { // Ctrl + Shift + B
        e.preventDefault();
        if (confirm('¿Desea limpiar el dispositivo Bluetooth guardado?')) {
          clearSavedBluetoothDevice();
          stopBluetoothWatchingAdvertisements();
          stopBluetoothConnectionMonitoring();
          
          // Limpiar timeouts de reconexión
          if (bluetoothReconnectTimeout) {
            clearTimeout(bluetoothReconnectTimeout);
            bluetoothReconnectTimeout = null;
            console.log('⏹️ Reconexión automática Bluetooth cancelada');
          }
          
          // Resetear contadores
          bluetoothAutoReconnectAttempts = 0;
          isBluetoothReconnecting = false;
          
          updateBluetoothUIState();
          alert('Dispositivo Bluetooth eliminado.');
        }
      }
    });
  




  $("#boton-c-numerico").on("click", function () {
    $("#TecladoNumerico").hide();
    $("#TecladoPesador").show();
  });
  $("#boton-c-pesador").on("click", function () {
    $("#TecladoPesador").hide();
    $("#TecladoNumerico").show();
  });

  $("#tecla-tare").on("click", function () {
    const modoBalanza = getModoBalanza();
    
    if (modoBalanza === 'bluetooth') {
      // Enviar comando TARE por Bluetooth
      if (isBluetoothConnected) {
        sendBluetoothCommand('T');
        sendBluetoothCommand('B')
        console.log('Comando TARE enviado por Bluetooth');
      } else {
        alert('Balanza Bluetooth no conectada');
      }
    } else {
      // Usar método asíncrono por WiFi/Socket
      enviarComandoBalanzaAsync('T');
    }
  });

  $("#tecla-zero").on("click", function () {
    const modoBalanza = getModoBalanza();
    
    if (modoBalanza === 'bluetooth') {
      // Enviar comando ZERO por Bluetooth
      if (isBluetoothConnected) {
        sendBluetoothCommand('Z');
        sendBluetoothCommand('B')
        console.log('Comando ZERO enviado por Bluetooth');
      } else {
        alert('Balanza Bluetooth no conectada');
      }
    } else {
      // Usar método asíncrono por WiFi/Socket
      enviarComandoBalanzaAsync('Z');
    }
  });

  $("#boton-producto-cero").on("click", function () {
    $("#producto-cero-div").hide();
    $("#hr-ocultar").show();
  });

  var fullscreenBtn = document.getElementById("fullscreen-btn");
  var fullscreenBtnSpan = document.getElementById("fullscreen-span");
  var isFullscreen = false;

  

  function enterFullscreen() {
    var docElm = document.documentElement;
    if (docElm.requestFullscreen) {
      docElm.requestFullscreen();
    } else if (docElm.mozRequestFullScreen) {
      /* Firefox */
      docElm.mozRequestFullScreen();
    } else if (docElm.webkitRequestFullscreen) {
      /* Chrome, Safari and Opera */
      docElm.webkitRequestFullscreen();
    } else if (docElm.msRequestFullscreen) {
      /* IE/Edge */
      docElm.msRequestFullscreen();
    }
  }

  function exitFullscreen() {
    if (document.exitFullscreen) {
      document.exitFullscreen();
    } else if (document.mozCancelFullScreen) {
      /* Firefox */
      document.mozCancelFullScreen();
    } else if (document.webkitExitFullscreen) {
      /* Chrome, Safari and Opera */
      document.webkitExitFullscreen();
    } else if (document.msExitFullscreen) {
      /* IE/Edge */
      document.msExitFullscreen();
    }
  }

  $("#boton-estado-caja").on("click", function () {
    const estadoCaja = $("#estado-caja-texto").text();
    
    if (estadoCaja === "CERRADA") {
      resetCajaForm('D');
      $("#abrirCajaModal").modal('show');
    } else {
      resetCajaForm('CD');
      $("#cerrarCajaModal").modal('show');
    }
  });

  $("#abrir-caja-btn").on("click", function () {
    const denominacionesUSD = {
      "1": parseInt($("#inputD1").val()) || 0,
      "5": parseInt($("#inputD5").val()) || 0,
      "10": parseInt($("#inputD10").val()) || 0,
      "20": parseInt($("#inputD20").val()) || 0,
      "50": parseInt($("#inputD50").val()) || 0,
      "100": parseInt($("#inputD100").val()) || 0
    };
  
    const denominacionesBs = {
      "0.5": parseInt($("#inputB05").val()) || 0,
      "1": parseInt($("#inputB1").val()) || 0,
      "5": parseInt($("#inputB5").val()) || 0,
      "10": parseInt($("#inputB10").val()) || 0,
      "20": parseInt($("#inputB20").val()) || 0,
      "50": parseInt($("#inputB50").val()) || 0,
      "100": parseInt($("#inputB100").val()) || 0
    };

    const data = {
      denominacionesUSD: JSON.stringify(denominacionesUSD),
      denominacionesBs: JSON.stringify(denominacionesBs)
    };

    $.ajax({
      url: "/pos/abrir-caja/",
      type: "POST",
      data: data,
      success: function (response) {
        $("#estado-caja-texto").text("ABIERTA");
        $("#boton-estado-caja").css("background-color", "#198754");
        $("#abrirCajaModal").modal('hide');
      },
      error: function (xhr) {
        // Mostrar mensaje de error
        alert(xhr.responseJSON.message);
      }
    });
  });

  // Constantes para los colores
  const BUTTON_COLOR_CLOSED = "#dc3545"; // Rojo para caja cerrada
  const BUTTON_COLOR_OPEN = "#198754";   // Verde para caja abierta

  // Actualizar la verificación de estado de caja al cargar la página
  $.ajax({
    url: "/pos/verificar-estado-caja/",
    type: "GET",
    success: function (response) {
      if (response.caja_abierta) {
        $("#estado-caja-texto").text("ABIERTA");
        $("#boton-estado-caja").css("background-color", "#198754");
        $("#abrir-caja-div").hide();
        $("#cerrar-caja-div").hide();
      } else {
        $("#estado-caja-texto").text("CERRADA");
        $("#boton-estado-caja").css("background-color", "#dc3545");
        $("#abrir-caja-div").hide();
        $("#cerrar-caja-div").hide();
      }
    },
    error: function(xhr) {
      console.error("Error verificando estado de caja:", xhr);
    }
  });
  

  $("#volver-home").on("click", function() {
    // Mostrar el modal de confirmación
    var salirPOSModal = new bootstrap.Modal(document.getElementById('salirPOSModal'));
    salirPOSModal.show();
  });
  
  // Manejador para el botón de confirmar salir del POS
  $("#confirmar-salir-pos").on("click", function() {
    window.location.href = "/pos/home/";
  });
     

});

function resetCajaForm(prefix) {
  const denominaciones = ['1', '5', '10', '20', '50', '100'];
  const denominacionesBs = ['05', '1', '5', '10', '20', '50', '100'];
  
  // Reiniciar campos de dólares
  denominaciones.forEach(denom => {
    $(`#input${prefix}${denom}`).val(0);
  });
  
  // Reiniciar campos de bolívares
  denominacionesBs.forEach(denom => {
    $(`#input${prefix}B${denom}`).val(0);
  });
}

// ==================== FUNCIONES BLUETOOTH LE ====================

  // Función para verificar soporte de Web Bluetooth
  function checkBluetoothSupport() {
    if (!navigator.bluetooth) {
      console.error('Web Bluetooth no está soportado en este navegador');
      return false;
    }
    return true;
  }

  // Función para verificar APIs experimentales de Bluetooth
  function checkBluetoothExperimentalAPIs() {
    console.log('🔍 Verificando APIs experimentales de Bluetooth...');
    
    // Verificar getDevices()
    hasBluetoothGetDevicesSupport = (
      navigator.bluetooth && 
      typeof navigator.bluetooth.getDevices === 'function'
    );
    
    // Verificar watchAdvertisements()
    hasBluetoothWatchAdvertisementsSupport = (
      typeof BluetoothDevice !== 'undefined' &&
      BluetoothDevice.prototype &&
      typeof BluetoothDevice.prototype.watchAdvertisements === 'function'
    );
    
    console.log(`✅ getDevices(): ${hasBluetoothGetDevicesSupport ? 'disponible' : 'no disponible'}`);
    console.log(`✅ watchAdvertisements(): ${hasBluetoothWatchAdvertisementsSupport ? 'disponible' : 'no disponible'}`);
    
    if (!hasBluetoothGetDevicesSupport || !hasBluetoothWatchAdvertisementsSupport) {
      console.log('⚠️ Para mejor experiencia de reconexión, habilita los flags experimentales de Chrome');
    } else {
      console.log('✅ Todas las APIs experimentales de Bluetooth están disponibles');
    }
  }

// Función para guardar dispositivo Bluetooth en localStorage
function saveBluetoothDevice(device) {
  const deviceInfo = {
    id: device.id,
    name: device.name || 'Dispositivo Desconocido',
    timestamp: Date.now()
  };
  localStorage.setItem('bluetoothBalanzaDevice', JSON.stringify(deviceInfo));
  console.log(`Dispositivo Bluetooth guardado: ${deviceInfo.name}`);
}

// Función para obtener dispositivo Bluetooth guardado
function getSavedBluetoothDevice() {
  const saved = localStorage.getItem('bluetoothBalanzaDevice');
  if (saved) {
    try {
      return JSON.parse(saved);
    } catch (e) {
      console.error('Error al leer dispositivo Bluetooth guardado');
      localStorage.removeItem('bluetoothBalanzaDevice');
    }
  }
  return null;
}

  // Función para limpiar dispositivo Bluetooth guardado
  function clearSavedBluetoothDevice() {
    localStorage.removeItem('bluetoothBalanzaDevice');
    console.log('Información de dispositivo Bluetooth eliminada');
  }

  // Función para iniciar monitoreo de anuncios Bluetooth
  async function startBluetoothWatchingAdvertisements(targetDevice) {
    if (!hasBluetoothWatchAdvertisementsSupport || !targetDevice) {
      return false;
    }
    
    try {
      if (!isBluetoothWatchingAdvertisements) {
        console.log('📡 Iniciando monitoreo de anuncios del dispositivo...');
        
        // Escuchar cuando el dispositivo anuncie su presencia
        targetDevice.addEventListener('advertisementreceived', (event) => {
          console.log(`📢 Anuncio recibido de ${event.device.name || 'dispositivo'}`);
          
          // Si no estamos conectados, intentar reconexión
          if (!isBluetoothConnected && !isBluetoothReconnecting) {
            console.log('🔄 Dispositivo detectado, iniciando reconexión...');
            setTimeout(() => attemptBluetoothAutoReconnect(), 1000);
          }
        });
        
        await targetDevice.watchAdvertisements();
        isBluetoothWatchingAdvertisements = true;
        console.log('✅ Monitoreo de anuncios activado');
        return true;
      }
    } catch (error) {
      console.error(`❌ Error configurando watchAdvertisements: ${error.message}`);
      return false;
    }
  }

  // Función para detener monitoreo de anuncios Bluetooth
  function stopBluetoothWatchingAdvertisements() {
    if (bluetoothDevice && isBluetoothWatchingAdvertisements && hasBluetoothWatchAdvertisementsSupport) {
      try {
        if (typeof bluetoothDevice.stopWatchingAdvertisements === 'function') {
          bluetoothDevice.stopWatchingAdvertisements();
        }
        isBluetoothWatchingAdvertisements = false;
        console.log('⏹️ Monitoreo de anuncios desactivado');
      } catch (error) {
        console.error(`Error deteniendo watchAdvertisements: ${error.message}`);
      }
    }
  }

  // Función para esperar anuncios del dispositivo
  async function waitForBluetoothDeviceAdvertisement(targetDevice, timeoutMs = 15000) {
    if (!hasBluetoothWatchAdvertisementsSupport || !targetDevice) {
      return false;
    }
    
    return new Promise((resolve) => {
      let advertisementReceived = false;
      let timeoutId = null;
      
      const onAdvertisement = (event) => {
        if (!advertisementReceived) {
          advertisementReceived = true;
          console.log(`📢 Anuncio recibido de ${event.device.name || 'dispositivo'}`);
          
          // Limpiar listeners y timeout
          targetDevice.removeEventListener('advertisementreceived', onAdvertisement);
          if (timeoutId) {
            clearTimeout(timeoutId);
          }
          
          resolve(true);
        }
      };
      
      // Configurar timeout
      timeoutId = setTimeout(() => {
        if (!advertisementReceived) {
          targetDevice.removeEventListener('advertisementreceived', onAdvertisement);
          console.log('⏰ Timeout esperando anuncios del dispositivo');
          resolve(false);
        }
      }, timeoutMs);
      
      // Escuchar anuncios
      targetDevice.addEventListener('advertisementreceived', onAdvertisement);
      
      // Iniciar watchAdvertisements si no está activo
      if (!isBluetoothWatchingAdvertisements) {
        startBluetoothWatchingAdvertisements(targetDevice);
      }
    });
  }

  // Función para verificar conexión periódicamente
  function startBluetoothConnectionMonitoring() {
    if (bluetoothConnectionCheckInterval) {
      clearInterval(bluetoothConnectionCheckInterval);
    }
    
    bluetoothConnectionCheckInterval = setInterval(() => {
      if (bluetoothDevice && getModoBalanza() === 'bluetooth') {
        // Verificar si el dispositivo está realmente conectado
        if (!bluetoothDevice.gatt || !bluetoothDevice.gatt.connected) {
          if (isBluetoothConnected) {
            console.log('⚠️ Conexión Bluetooth perdida detectada por monitoreo');
            handleBluetoothDisconnection({ target: bluetoothDevice });
          }
        }
      }
    }, 5000); // Verificar cada 5 segundos
  }

  // Función para detener monitoreo de conexión
  function stopBluetoothConnectionMonitoring() {
    if (bluetoothConnectionCheckInterval) {
      clearInterval(bluetoothConnectionCheckInterval);
      bluetoothConnectionCheckInterval = null;
    }
  }

// Función para conectar a dispositivo Bluetooth específico
async function connectToBluetoothDevice(targetDevice) {
  try {
    bluetoothDevice = targetDevice;
    console.log(`Conectando a: ${bluetoothDevice.name || 'Desconocido'}`);
    
    // Conectar al servidor GATT
    bluetoothServer = await bluetoothDevice.gatt.connect();
    console.log('Conectado al servidor GATT');
    
    // Obtener el servicio
    bluetoothService = await bluetoothServer.getPrimaryService(BLUETOOTH_SERVICE_UUID);
    console.log('Servicio Bluetooth obtenido');
    
    // Obtener características
    bluetoothNotifyCharacteristic = await bluetoothService.getCharacteristic(BLUETOOTH_NOTIFY_CHARACTERISTIC_UUID);
    bluetoothWriteCharacteristic = await bluetoothService.getCharacteristic(BLUETOOTH_WRITE_CHARACTERISTIC_UUID);
    console.log('Características Bluetooth obtenidas');
    
    // Configurar notificaciones
    await bluetoothNotifyCharacteristic.startNotifications();
    bluetoothNotifyCharacteristic.addEventListener('characteristicvaluechanged', handleBluetoothNotification);
    console.log('Notificaciones Bluetooth activadas');
    
    // Configurar evento de desconexión
    bluetoothDevice.addEventListener('gattserverdisconnected', handleBluetoothDisconnection);
    
    isBluetoothConnected = true;
    updateBluetoothUIState();
    console.log('¡Conexión Bluetooth completada exitosamente!');
    
    // Guardar dispositivo para reconexión futura
    saveBluetoothDevice(bluetoothDevice);
    
    // Configurar watchAdvertisements para futuras desconexiones
    await startBluetoothWatchingAdvertisements(bluetoothDevice);
    
    // Iniciar monitoreo de conexión
    startBluetoothConnectionMonitoring();
    
    return true;
  } catch (error) {
    console.error(`Error conectando a dispositivo Bluetooth: ${error.message}`);
    throw error;
  }
}

  // Función para manejar notificaciones Bluetooth (datos del peso)
  function handleBluetoothNotification(event) {
    const value = event.target.value;
    
    // Convertir ArrayBuffer a string
    let rawData = '';
    for (let i = 0; i < value.byteLength; i++) {
      rawData += String.fromCharCode(value.getUint8(i));
    }
    
    // Parsear el peso: convertir de entero a float
    let parsedWeight = 0;
    
    try {
      // Limpiar el string (remover espacios y caracteres no numéricos excepto números)
      const cleanData = rawData.replace(/[^\d]/g, '');
      
      if (cleanData && cleanData.length > 0) {
        // Convertir a número y dividir por 100 para obtener decimales
        const weightInt = parseInt(cleanData, 10);
        parsedWeight = weightInt / 100;
        
        // Actualizar peso actual
        currentBluetoothWeight = parsedWeight;
        
        // Guardar los datos más recientes
        lastBluetoothWeightData = {
          weight: parsedWeight,
          raw: rawData,
          timestamp: Date.now()
        };
        
        // Aplicar throttling: solo actualizar display si han pasado al menos 25ms
        const now = Date.now();
        if (now - lastBluetoothUpdateTime >= BLUETOOTH_THROTTLE_DELAY) {
          updateWeightDisplay(parsedWeight);
          lastBluetoothUpdateTime = now;
        }
        
      }
    } catch (error) {
      console.error(`Error parseando peso Bluetooth: ${error.message}`);
    }
  }

  // Función para actualizar el display de peso
  function updateWeightDisplay(weight) {
    if (isBluetoothConnected && getModoBalanza() === 'bluetooth') {
      // Actualizar el display fijo en la sección de pedidos
      const formattedWeight = weight.toFixed(2);
      $('#peso-display-valor').text(formattedWeight);
    }
  }

  // Función para actualizar el estado del display de peso
  function updatePesoDisplayStatus(status, valor = '') {
    if (getModoBalanza() === 'bluetooth') {
      switch(status) {
        case 'conectando':
          $('#peso-display-valor').text('CONECTANDO...');
          break;
        case 'error':
          $('#peso-display-valor').text('ERROR CONEXION');
          break;
        case 'desconectado':
          $('#peso-display-valor').text('00.00');
          break;
        case 'peso':
          $('#peso-display-valor').text(valor);
          break;
      }
    }
  }

  // Función para manejar desconexión Bluetooth
  function handleBluetoothDisconnection(event) {
    console.log('🔌 Dispositivo Bluetooth desconectado');
    
    // Mostrar alerta al usuario
    if (getModoBalanza() === 'bluetooth') {
      alert('⚠️ Balanza Bluetooth desconectada. Reintentando conexión automática...');
    }
    
    isBluetoothConnected = false;
    bluetoothDevice = null;
    bluetoothServer = null;
    bluetoothService = null;
    bluetoothNotifyCharacteristic = null;
    bluetoothWriteCharacteristic = null;
    currentBluetoothWeight = 0;
    lastBluetoothWeightData = null;
    
    // Detener monitoreo de conexión
    stopBluetoothConnectionMonitoring();
    
    // Limpiar timeouts de reconexión
    if (bluetoothReconnectTimeout) {
      clearTimeout(bluetoothReconnectTimeout);
      bluetoothReconnectTimeout = null;
    }
    isBluetoothReconnecting = false;
    
    updateBluetoothUIState();
    
    // Intentar reconexión automática si hay dispositivo guardado
    const savedDevice = getSavedBluetoothDevice();
    if (savedDevice && getModoBalanza() === 'bluetooth') {
      console.log('Dispositivo Bluetooth desconectado. Iniciando reconexión automática en 3 segundos...');
      scheduleBluetoothReconnection(3000);
    }
  }

// Función para programar reintento de reconexión Bluetooth
function scheduleBluetoothReconnection(delay) {
  if (bluetoothReconnectTimeout) {
    clearTimeout(bluetoothReconnectTimeout);
  }
  
  const seconds = Math.ceil(delay / 1000);
  console.log(`Próximo intento de reconexión Bluetooth en ${seconds} segundos...`);
  
  bluetoothReconnectTimeout = setTimeout(async () => {
    if (!isBluetoothConnected && getSavedBluetoothDevice()) {
      console.log('Reintentando reconexión automática Bluetooth...');
      await attemptBluetoothAutoReconnect();
    }
  }, delay);
}

// Función para reconexión automática Bluetooth
async function attemptBluetoothAutoReconnect() {
  const savedDevice = getSavedBluetoothDevice();
  if (!savedDevice) {
    console.log('No hay dispositivo Bluetooth guardado para reconectar');
    return false;
  }
  
  if (isBluetoothReconnecting) {
    console.log('Ya hay un intento de reconexión Bluetooth en progreso...');
    return false;
  }
  
  isBluetoothReconnecting = true;
  updatePesoDisplayStatus('conectando');
  console.log(`Intentando reconexión automática Bluetooth a: ${savedDevice.name}`);
  
  try {
    // Verificar soporte de Web Bluetooth primero
    if (!navigator.bluetooth) {
      throw new Error('Web Bluetooth no está soportado');
    }
    
    let targetDevice = null;
    
    // Intentar usar getDevices() si está disponible
    if (navigator.bluetooth.getDevices) {
      try {
        console.log('Usando getDevices() para buscar dispositivo Bluetooth...');
        const devices = await navigator.bluetooth.getDevices();
        console.log(`Se encontraron ${devices.length} dispositivos Bluetooth autorizados`);
        
        // Buscar por ID primero (más confiable)
        if (savedDevice.id) {
          targetDevice = devices.find(d => d.id === savedDevice.id);
          if (targetDevice) {
            console.log(`Dispositivo Bluetooth encontrado por ID: ${targetDevice.name || 'Sin nombre'}`);
          }
        }
        
        // Si no se encuentra por ID, buscar por nombre
        if (!targetDevice && savedDevice.name && savedDevice.name !== 'Dispositivo Desconocido') {
          targetDevice = devices.find(d => d.name === savedDevice.name);
          if (targetDevice) {
            console.log(`Dispositivo Bluetooth encontrado por nombre: ${targetDevice.name}`);
            // Actualizar ID si cambió
            if (targetDevice.id !== savedDevice.id) {
              console.log('Actualizando ID del dispositivo Bluetooth');
              saveBluetoothDevice(targetDevice);
            }
          }
        }
      } catch (getDevicesError) {
        console.error(`Error usando getDevices() Bluetooth: ${getDevicesError.message}`);
      }
    }
    
            // Si no se encontró con getDevices()
        if (!targetDevice) {
          console.log('No se encontró el dispositivo Bluetooth con getDevices() o API no disponible');
          throw new Error('Dispositivo Bluetooth no encontrado en dispositivos autorizados');
        }
        
        // Verificar si ya está conectado
        if (targetDevice.gatt && targetDevice.gatt.connected) {
          console.log('El dispositivo Bluetooth ya estaba conectado');
          bluetoothDevice = targetDevice;
          bluetoothServer = targetDevice.gatt;
          
          // Configurar watchAdvertisements para futuras desconexiones
          await startBluetoothWatchingAdvertisements(targetDevice);
          
          await setupBluetoothServices();
          return true;
        } else {
          // Usar watchAdvertisements antes de conectar si está disponible
          if (hasBluetoothWatchAdvertisementsSupport) {
            console.log('📡 Esperando anuncios del dispositivo antes de conectar...');
            const deviceDetected = await waitForBluetoothDeviceAdvertisement(targetDevice, 15000);
            
            if (deviceDetected) {
              console.log('📢 Dispositivo detectado físicamente. Conectando...');
              await connectToBluetoothDevice(targetDevice);
              return true;
            } else {
              console.log('⏰ Timeout esperando anuncios del dispositivo');
              throw new Error('Dispositivo no detectado físicamente después de 15 segundos');
            }
          } else {
            // Fallback: intentar conectar directamente
            console.log('Conectando al dispositivo Bluetooth encontrado...');
            await connectToBluetoothDevice(targetDevice);
            return true;
          }
        }
    
  } catch (error) {
    return handleBluetoothReconnectionError(error);
  } finally {
    isBluetoothReconnecting = false;
  }
}

// Función para manejar errores específicos de reconexión Bluetooth
function handleBluetoothReconnectionError(error) {
  const errorMessage = error.message.toLowerCase();
  
  if (errorMessage.includes('no longer in range') || errorMessage.includes('out of range')) {
    console.error('Dispositivo Bluetooth fuera de alcance. Reintentando en 10 segundos...');
    scheduleBluetoothReconnection(10000);
    return false;
  } else if (errorMessage.includes('device not found') || errorMessage.includes('not available')) {
    console.error('Dispositivo Bluetooth no disponible. Reintentando en 5 segundos...');
    scheduleBluetoothReconnection(5000);
    return false;
  } else if (errorMessage.includes('connection failed') || errorMessage.includes('gatt')) {
    console.error('Error de conexión GATT Bluetooth. Reintentando en 3 segundos...');
    scheduleBluetoothReconnection(3000);
    return false;
  } else {
    // Error genérico
    console.error(`Error en reconexión automática Bluetooth: ${error.message}`);
    bluetoothAutoReconnectAttempts++;
    
    if (bluetoothAutoReconnectAttempts >= maxBluetoothReconnectAttempts) {
      console.error(`Máximo de intentos Bluetooth alcanzado (${maxBluetoothReconnectAttempts}). Limpiando dispositivo guardado.`);
      updatePesoDisplayStatus('error');
      
      // Después de 5 segundos, cambiar a desconectado
      setTimeout(() => {
        updatePesoDisplayStatus('desconectado');
      }, 5000);
      
      clearSavedBluetoothDevice();
    } else {
      console.log(`Intento Bluetooth ${bluetoothAutoReconnectAttempts}/${maxBluetoothReconnectAttempts} fallido`);
      const delay = Math.min(2000 * Math.pow(2, bluetoothAutoReconnectAttempts), 30000);
      scheduleBluetoothReconnection(delay);
    }
    return false;
  }
}

// Función para configurar servicios Bluetooth (extraída para reutilización)
async function setupBluetoothServices() {
  try {
    // Obtener el servicio
    bluetoothService = await bluetoothServer.getPrimaryService(BLUETOOTH_SERVICE_UUID);
    console.log('Servicio Bluetooth encontrado');
    
    // Obtener características
    bluetoothNotifyCharacteristic = await bluetoothService.getCharacteristic(BLUETOOTH_NOTIFY_CHARACTERISTIC_UUID);
    bluetoothWriteCharacteristic = await bluetoothService.getCharacteristic(BLUETOOTH_WRITE_CHARACTERISTIC_UUID);
    console.log('Características Bluetooth obtenidas');
    
    // Configurar notificaciones
    await bluetoothNotifyCharacteristic.startNotifications();
    bluetoothNotifyCharacteristic.addEventListener('characteristicvaluechanged', handleBluetoothNotification);
    console.log('Notificaciones Bluetooth activadas');
    
    // Configurar evento de desconexión
    bluetoothDevice.addEventListener('gattserverdisconnected', handleBluetoothDisconnection);
    
    isBluetoothConnected = true;
    updateBluetoothUIState();
    console.log('¡Configuración de servicios Bluetooth completada!');
    
    // Auto-cerrar el modal de configuración cuando se conecte exitosamente
    $('#configurarBalanzaModal').modal('hide');
    
    // Guardar dispositivo para reconexión futura
    saveBluetoothDevice(bluetoothDevice);
    
    // Iniciar monitoreo de conexión
    startBluetoothConnectionMonitoring();
    
  } catch (error) {
    console.error(`Error configurando servicios Bluetooth: ${error.message}`);
    throw error;
  }
}

// Función para conectar manualmente a dispositivo Bluetooth
async function connectBluetoothDevice() {
  try {
    console.log('Iniciando conexión Bluetooth manual...');
    updatePesoDisplayStatus('conectando');
    
    // Verificar soporte de Web Bluetooth
    if (!checkBluetoothSupport()) {
      throw new Error('Web Bluetooth no está soportado en este navegador');
    }
    
    // Solicitar dispositivo
    const selectedDevice = await navigator.bluetooth.requestDevice({
      acceptAllDevices: true,
      optionalServices: [BLUETOOTH_SERVICE_UUID]
    });
    
    console.log(`Dispositivo Bluetooth seleccionado: ${selectedDevice.name || 'Desconocido'}`);
    
    await connectToBluetoothDevice(selectedDevice);
    
  } catch (error) {
    console.error(`Error de conexión Bluetooth manual: ${error.message}`);
    isBluetoothConnected = false;
    updatePesoDisplayStatus('error');
    
    // Después de 3 segundos, cambiar a desconectado
    setTimeout(() => {
      updatePesoDisplayStatus('desconectado');
    }, 3000);
    
    updateBluetoothUIState();
  }
}

  // Función para desconectar dispositivo Bluetooth
  function disconnectBluetoothDevice() {
    try {
      // Limpiar timeouts de reconexión para desconexión manual
      if (bluetoothReconnectTimeout) {
        clearTimeout(bluetoothReconnectTimeout);
        bluetoothReconnectTimeout = null;
        console.log('Reconexión automática Bluetooth cancelada');
      }
      
      // Detener monitoreo de anuncios
      stopBluetoothWatchingAdvertisements();
      
      // Detener monitoreo de conexión
      stopBluetoothConnectionMonitoring();
      
      if (bluetoothDevice && bluetoothDevice.gatt.connected) {
        bluetoothDevice.gatt.disconnect();
      }
      console.log('Dispositivo Bluetooth desconectado manualmente');
    } catch (error) {
      console.error(`Error al desconectar Bluetooth: ${error.message}`);
    }
  }

// Función para enviar comandos Bluetooth
async function sendBluetoothCommand(command) {
  try {
    if (!bluetoothWriteCharacteristic) {
      throw new Error('No hay conexión Bluetooth activa');
    }
    
    // Convertir comando a ArrayBuffer
    const encoder = new TextEncoder();
    const data = encoder.encode(command);
    
    await bluetoothWriteCharacteristic.writeValue(data);
    console.log(`Comando Bluetooth enviado: ${command}`);
    
  } catch (error) {
    console.error(`Error enviando comando Bluetooth ${command}: ${error.message}`);
  }
}

  // Función para actualizar el estado de la UI Bluetooth
  function updateBluetoothUIState() {
    const modoBalanza = getModoBalanza();
    
    if (modoBalanza === 'bluetooth') {
      // Mostrar el display fijo de peso
      $('#display-peso-bluetooth').show();
      
      if (isBluetoothConnected) {
        // Conectado: Botón verde y actualizar status en modal
        $('#boton-balanza-bluetooth').css('background-color', '#28a745');
        $('#bluetooth-connection-status').text('Estado: Conectado');
        $('#conectar-bluetooth-btn').prop('disabled', true);
        $('#desconectar-bluetooth-btn').prop('disabled', false);
        
        // Inicializar display con peso actual o ceros
        const currentWeight = currentBluetoothWeight || 0;
        updateWeightDisplay(currentWeight);
      } else {
        // Desconectado: Botón gris
        $('#boton-balanza-bluetooth').css('background-color', '#6c757d');
        $('#bluetooth-connection-status').text('Estado: Desconectado');
        $('#conectar-bluetooth-btn').prop('disabled', false);
        $('#desconectar-bluetooth-btn').prop('disabled', true);
        
        // Mostrar 00.00 cuando esté desconectado
        updatePesoDisplayStatus('desconectado');
      }
    } else {
      // Modo WiFi: Ocultar display y mostrar botón azul
      $('#display-peso-bluetooth').hide();
      $('#boton-balanza-bluetooth').css('background-color', '#0d6efd');
    }
  }

// Función para obtener el modo de balanza configurado
function getModoBalanza() {
  return localStorage.getItem('modoBalanza') || 'wifi';
}

  // Función para establecer el modo de balanza
  function setModoBalanza(modo) {
    localStorage.setItem('modoBalanza', modo);
    console.log(`Modo de balanza establecido: ${modo}`);
  }

  // ==================== FUNCIONES ASÍNCRONAS PARA SOCKET ====================
  
  // Función para enviar comandos de control asíncronos
  async function enviarComandoBalanzaAsync(comando) {
    const balanza = localStorage.getItem("balanza");
    
    if (!balanza) {
      alert('No hay balanza configurada');
      return;
    }
    
    try {
      const response = await fetch('/pos/balanza-async', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'X-CSRFToken': getCookie('csrftoken')
        },
        body: new URLSearchParams({
          'codigo': comando,
          'balanza': balanza
        })
      });
      
      const resultado = await response.text();
      console.log(`📤 Comando ${comando} enviado. Respuesta: ${resultado}`);
      
    } catch (error) {
      console.error(`❌ Error enviando comando ${comando}:`, error);
      alert(`Error comunicándose con la balanza: ${error.message}`);
    }
  }

  // Función mejorada para obtener peso de balanza asíncrona
  async function obtenerPesoBalanzaAsync() {
    const balanza = localStorage.getItem("balanza");
    
    if (!balanza) {
      alert('No hay balanza configurada');
      return;
    }
    
    try {
      const response = await fetch('/pos/balanza-async', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'X-CSRFToken': getCookie('csrftoken')
        },
        body: new URLSearchParams({
          'codigo': 'P',  // Comando para obtener peso
          'balanza': balanza
        })
      });
      
      const resultado = await response.text();
      
      if (resultado === 'error') {
        throw new Error('Error de comunicación con balanza');
      }
      
      const peso = parseFloat(resultado);
      if (peso > 0) {
        console.log(`✅ Peso obtenido: ${peso}kg`);
        return peso;
      }
      
    } catch (error) {
      console.error('❌ Error obteniendo peso:', error);
      alert('Error comunicándose con la balanza: ' + error.message);
    }
  }

  // Función helper para obtener token CSRF
  function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
      const cookies = document.cookie.split(';');
      for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i].trim();
        if (cookie.substring(0, name.length + 1) === (name + '=')) {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  }

  // ==================== INICIALIZACIÓN Y EVENT LISTENERS ====================

  // Event listeners para el modal de configuración de balanza
  

  // Agregar evento para autofocus cuando se muestra el modal de autorización de vuelto
  $('#autorizacionVueltoModal').on('shown.bs.modal', function () {
      $('#codigoAutorizacionVuelto').focus();
  });

  // ==================== GESTIÓN DE PEDIDOS INJUSTIFICADOS ====================
  
  // Evento para el botón "Procesar Pedido" en modal injustificado
  $(document).on('click', '#btn-procesar-injustificado', function() {
      const pedidoId = $(this).data('pedido-id');
      
      // Verificar que hay caja abierta
      if ($("#estado-caja-texto").text() === "CERRADA") {
          alert("Debe abrir la caja antes de procesar pagos");
          return;
      }
      
      // Guardar el ID del pedido para uso posterior
      localStorage.setItem('pedido_injustificado_id', pedidoId);
      
      // Mostrar modal de autorización
      const modal = new bootstrap.Modal(document.getElementById('autorizacionInjustificadoModal'));
      modal.show();
  });
  
  // Agregar evento para autofocus cuando se muestra el modal de autorización injustificado
  $('#autorizacionInjustificadoModal').on('shown.bs.modal', function () {
      $('#codigoAutorizacionInjustificado').focus();
      // Limpiar campos al mostrar
      $('#codigoAutorizacionInjustificado').val('');
      $('#error-autorizacion-injustificado').addClass('d-none');
  });
  
  // Evento para confirmar autorización de pedido injustificado
  $(document).on('click', '#btn-confirmar-autorizacion-injustificado', function() {
      const codigo = $('#codigoAutorizacionInjustificado').val().trim();
      const pedidoId = localStorage.getItem('pedido_injustificado_id');
      
      if (!codigo) {
          $('#error-autorizacion-injustificado').removeClass('d-none').text('Debe ingresar un código de autorización');
          return;
      }
      
      // Deshabilitar botón mientras procesa
      $(this).prop('disabled', true).html('<i class="fas fa-spinner fa-spin me-2"></i>Procesando...');
      
      $.ajax({
          url: '/pos/procesar-pedido-injustificado/',
          type: 'POST',
          data: {
              'pedido_id': pedidoId,
              'codigo': codigo,
              'csrfmiddlewaretoken': $('[name=csrfmiddlewaretoken]').val()
          },
          success: function(response) {
              if (response.success) {
                  // Cerrar modal
                  $('#autorizacionInjustificadoModal').modal('hide');
                  
                  // Mostrar mensaje de éxito
                  alert(response.message);
                  
                                      // Redirigir al proceso de pago del pedido autorizado
                    window.location.href = `/pos/${pedidoId}/pagina-pago/`;
              } else {
                  $('#error-autorizacion-injustificado').removeClass('d-none').text(response.error);
              }
          },
          error: function(xhr) {
              console.error('Error al procesar autorización:', xhr);
              $('#error-autorizacion-injustificado').removeClass('d-none').text('Error al procesar la autorización');
          },
          complete: function() {
              // Rehabilitar botón
              $('#btn-confirmar-autorizacion-injustificado').prop('disabled', false).html('<i class="fas fa-check me-2"></i>Autorizar y Procesar');
          }
      });
  });
  
  // Permitir envío con Enter en el campo de código de autorización injustificado
  $(document).on('keypress', '#codigoAutorizacionInjustificado', function(e) {
      if (e.which === 13) { // Enter key
          e.preventDefault();
          $('#btn-confirmar-autorizacion-injustificado').click();
      }
  });
  
  // Limpiar localStorage cuando se cierra el modal de autorización injustificado
  $('#autorizacionInjustificadoModal').on('hidden.bs.modal', function() {
      localStorage.removeItem('pedido_injustificado_id');
  });

  // Función para filtrar productos por categoría en frontend
  function filtrarProductosPorCategoria(categoriaId) {
    // Obtener todos los productos del DOM
    console.log("filtrarProductosPorCategoria");
    const todosLosProductos = $(".agregar-producto-pedido");
    
    todosLosProductos.each(function() {
      const productoDiv = $(this);
      const textoProducto = productoDiv.find(".todos-los-productos").text();
      const productoInfo = textoProducto.split("-");
      
      // El último elemento contiene las categorías: "1,3,5," 
      const categoriasTexto = productoInfo[6] || "";
      // Remover espacios y filtrar elementos vacíos
      const categoriasArray = categoriasTexto.split(",")
        .map(cat => cat.trim())
        .filter(cat => cat !== "");
      
      // Si es "mostrar todos" (categoriaId = "0") o el producto pertenece a la categoría
      const mostrarTodos = categoriaId === "0";
      const tieneCategoria = categoriasArray.includes(categoriaId);
      
      if (mostrarTodos || tieneCategoria) {
        productoDiv.show();
      } else {
        productoDiv.hide();
      }
    });
  }

  // ==================== FUNCIONES PARA PROCESAMIENTO NO-BLOQUEANTE ====================

  // Botón de guardar pedido mejorado (no-bloqueante)
  function initBotonGuardarMejorado() {
    // 🔒 Inicializar botón bloqueado por defecto
    $(".botonGuardarPedido").prop("disabled", true).addClass("boton-deshabilitado");
    
    // 🔒 Verificar estado inicial del botón (solo si está imprimiendo)
    if (imprimiendo) {
      $(".botonGuardarPedido").prop("disabled", true).addClass("boton-deshabilitado");
    }
    
    $(".botonGuardarPedido").off("click").on("click", function () {
      // 🔒 Verificar si el botón está deshabilitado
      if ($(this).prop("disabled")) {
        console.log("🚫 Botón de guardar deshabilitado - procesamiento en curso");
        return false;
      }
      
      if (isPedidoNoModificable(pedido_status)) {
        if (isPedidoDevolucion(pedido_status)) {
          alert("Este pedido fue marcado como DEVOLUCIÓN. No puede volver a procesarse.");
        } else {
          alert("Este pedido ya está pagado. No puede volver a procesarse.");
        }
        return;
      }

      const userGroups = $("#user-groups").text();
  
      if (!userGroups.includes('PESADOR')) {
        if ($("#estado-caja-texto").text() === "CERRADA") {
          alert("Debe abrir la caja antes de procesar pagos");
          return;
        }
      }

      if (checkProductoCero() == false) {
        if (imprimiendo == false) {
          procesarPedidoNoBloquante();
        }
      }
    });
  }

  function procesarPedidoNoBloquante() {
    // 🔒 BLOQUEAR BOTÓN DE GUARDAR durante el procesamiento
    $(".botonGuardarPedido").prop("disabled", true).css({
      "opacity": "0.6",
      "cursor": "not-allowed"
    });
    
    // Preparar datos del pedido
    if (pedido_cargado_modificado == true) {
      localStorage.setItem("pedido_modificado", true);
    } else {
      localStorage.setItem("pedido_modificado", false);
    }

    imprimiendo = true;
    if (isNaN(pedido_id) || pedido_id == "") {
      pedido_id = "nuevo";
    }

    var precioT = 0;
    pedido.forEach((p) => {
      moneda = p.moneda;
      p.precio = parseFloat(p.precio);

      if (moneda == "USD") {
        precioT += p.precio * p.cantidad;
      } else if (moneda == "BS") {
        precio = (p.precio / bcv) * p.cantidad;
        precioT += precio;
      }
    });

    if (cliente_id == "") {
      cliente_id = 0;
    } else {
      cliente_id = parseInt(cliente_id);
    }

    var pedido_json = JSON.stringify(pedido);
    
    if (precioT > 0) {
      // Mostrar feedback inmediato pero no bloqueante
      mostrarProcesamientoRapido();

      $.ajax({
        url: "guardar-pedido-rapido/", // Nueva URL optimizada
        data: {
          impresora: localStorage.getItem("impresora"),
          usuario: usuario,
          pedidoJSON: pedido_json,
          pedido: pedido,
          cliente: cliente_id,
          precioT: precioT,
          notas: notas,
          pedido_id: pedido_id,
          modoImpresion: localStorage.getItem("modoImpresion") || "ticket", // AGREGAR MODO DE IMPRESIÓN
        },
        type: "POST",
        timeout: 10000, // 10 segundos timeout
        success: function (response) {
          ocultarProcesamientoRapido();
          rehabilitarBotonGuardar();
          
          // ✅ VERIFICAR SI EL PEDIDO SE GUARDÓ EXITOSAMENTE
          if (response.success && response.saved) {
            // 🎯 PEDIDO GUARDADO EXITOSAMENTE: Proceder con la lógica de redirección
            if (response.is_pesador) {
              // 🎯 PESADOR: Mostrar notificación de impresión y redirigir a POS
              if (response.impresion_async) {
                mostrarMensajeImpresionAsyncCentrado(response.pedido_id, response.mensaje);
                
                // Redirigir después de 2 segundos para ver la notificación
                setTimeout(function() {
                  window.location.href = response.url;
                }, 2000);
              } else {
                // Fallback: ir directo si no hay impresión
                window.location.href = response.url;
              }
            } else {
              // 💳 CAJERO/OTROS: Ir directamente a página de pago sin impresión
              window.location.href = response.url;
            }
          } else {
            // ❌ PEDIDO NO SE GUARDÓ: Mostrar error y no redirigir
            const errorMessage = response.message || "Error desconocido al guardar el pedido";
            alert("❌ No se pudo guardar el pedido: " + errorMessage);
            console.error("Error del servidor:", response.error);
            imprimiendo = false; // Permitir reintentos
          }
        },
        error: function(xhr) {
          ocultarProcesamientoRapido();
          rehabilitarBotonGuardar();
          imprimiendo = false;
          
          console.error("Error AJAX:", xhr);
          
          if (xhr.status === 408 || xhr.statusText === 'timeout') {
            alert("⏱️ El procesamiento está tomando más tiempo del esperado.\n\n" +
                  "¿Qué hacer?\n" +
                  "• Revisa si el pedido aparece en la lista de pedidos\n" +
                  "• Si no aparece, puedes intentar guardar nuevamente\n" +
                  "• Si aparece, el pedido se guardó correctamente");
          } else if (xhr.status === 400) {
            // Error de validación del servidor
            const errorData = xhr.responseJSON || {};
            const errorMessage = errorData.message || "Error de validación";
            alert("⚠️ " + errorMessage);
          } else if (xhr.status === 500) {
            // Error interno del servidor
            const errorData = xhr.responseJSON || {};
            const errorMessage = errorData.message || "Error interno del servidor";
            alert("🔧 " + errorMessage);
          } else {
            // Error genérico
            const errorMessage = xhr.responseJSON?.message || "Error procesando el pedido";
            alert("❌ " + errorMessage);
          }
        }
      });
    }
  }

  function mostrarProcesamientoRapido() {
    // Crear modal ligero de procesamiento
    const modalHtml = `
      <div id="procesamiento-rapido-modal" style="
        position: fixed; top: 0; left: 0; width: 100%; height: 100%; 
        background-color: rgba(0,0,0,0.7); z-index: 9999; display: flex; 
        justify-content: center; align-items: center;">
        <div style="
          background: white; padding: 30px; border-radius: 10px; 
          text-align: center; max-width: 400px; box-shadow: 0 4px 20px rgba(0,0,0,0.3);">
          <div style="margin-bottom: 20px;">
            <div style="
              border: 4px solid #f3f3f3; border-top: 4px solid #3498db; 
              border-radius: 50%; width: 40px; height: 40px; 
              animation: spin 1s linear infinite; margin: 0 auto;">
            </div>
          </div>
          <h4 style="color: #333; margin-bottom: 10px;">Guardando Pedido...</h4>
          <p style="color: #666; margin: 0;">El ticket se imprimirá automáticamente</p>
          <button id="btn-continuar-trabajo" style="
            margin-top: 15px; padding: 8px 15px; background: #2c3e50; 
            color: white; border: none; border-radius: 5px; cursor: pointer; display: none;">
            Continuar trabajando
          </button>
        </div>
      </div>
      <style>
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      </style>
    `;
    
    $("body").append(modalHtml);
    
    // Permitir continuar trabajando después de 3 segundos
    setTimeout(function() {
      $("#btn-continuar-trabajo").show().on("click", function() {
        $("#procesamiento-rapido-modal").remove();
        rehabilitarBotonGuardar(); // 🔒 Rehabilitar botón al cancelar
        imprimiendo = false; // Permitir otros clicks
      });
    }, 3000);
  }

  function ocultarProcesamientoRapido() {
    $("#procesamiento-rapido-modal").remove();
    imprimiendo = false;
  }

  // 🔒 FUNCIÓN HELPER: Rehabilitar botón de guardar
  function rehabilitarBotonGuardar() {
    // Solo rehabilitar si el precio total es mayor a 0
    if (precioTotalUsd > 0 && !imprimiendo) {
      $(".botonGuardarPedido").prop("disabled", false).removeClass("boton-deshabilitado");
    } else {
      $(".botonGuardarPedido").prop("disabled", true).addClass("boton-deshabilitado");
    }
  }

  function mostrarMensajeImpresionAsync(pedidoId, mensaje) {
    // Crear notificación no-intrusiva mejorada
    const notificacionHtml = `
      <div id="notificacion-impresion" style="
        position: fixed; top: 20px; right: 20px; 
        background: #17a2b8; color: white; padding: 15px 20px; 
        border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        z-index: 9998; max-width: 350px;">
        <div style="display: flex; align-items: center;">
          <div style="margin-right: 10px;">🖨️</div>
          <div>
            <strong>Pedido #${pedidoId} guardado</strong><br>
            <small>${mensaje}</small>
          </div>
        </div>
      </div>
    `;
    
    $("body").append(notificacionHtml);
    
    // Auto-remover después de 4 segundos
    setTimeout(function() {
      $("#notificacion-impresion").fadeOut(500, function() {
        $(this).remove();
      });
    }, 4000);
  }

  // 🎯 FUNCIÓN NUEVA: Toast centrado en la pantalla
  function mostrarMensajeImpresionAsyncCentrado(pedidoId, mensaje) {
    // Crear notificación centrada mejorada
    const notificacionHtml = `
      <div id="notificacion-impresion-centrada" style="
        position: fixed; 
        top: 50%; 
        left: 50%; 
        transform: translate(-50%, -50%);
        background: linear-gradient(135deg, #17a2b8, #138496); 
        color: white; 
        padding: 20px 25px; 
        border-radius: 12px; 
        box-shadow: 0 8px 25px rgba(0,0,0,0.3);
        z-index: 9998; 
        max-width: 400px;
        min-width: 300px;
        animation: slideInScale 0.4s ease-out;">
        <div style="display: flex; align-items: center; text-align: center;">
          <div style="margin-right: 15px; font-size: 24px;">🖨️</div>
          <div style="flex: 1;">
            <strong style="font-size: 16px; display: block; margin-bottom: 5px;">
              ✅ Pedido #${pedidoId} guardado
            </strong>
            <small style="font-size: 14px; opacity: 0.9;">${mensaje}</small>
          </div>
        </div>
      </div>
      <style>
        @keyframes slideInScale {
          0% { 
            opacity: 0; 
            transform: translate(-50%, -50%) scale(0.7); 
          }
          100% { 
            opacity: 1; 
            transform: translate(-50%, -50%) scale(1); 
          }
        }
      </style>
    `;
    
    $("body").append(notificacionHtml);
    
    // Auto-remover después de 3 segundos con animación de salida
    setTimeout(function() {
      $("#notificacion-impresion-centrada").css({
        'animation': 'slideOutScale 0.3s ease-in forwards'
      });
      
      // Agregar keyframes para salida
      if (!$('#slideOutScaleStyle').length) {
        $('head').append(`
          <style id="slideOutScaleStyle">
            @keyframes slideOutScale {
              0% { 
                opacity: 1; 
                transform: translate(-50%, -50%) scale(1); 
              }
              100% { 
                opacity: 0; 
                transform: translate(-50%, -50%) scale(0.7); 
              }
            }
          </style>
        `);
      }
      
      setTimeout(function() {
        $("#notificacion-impresion-centrada").remove();
      }, 300);
    }, 3000);
  }

  // ==================== FUNCIONES PARA REIMPRESIÓN NO-BLOQUEANTE ====================

  function procesarReimpresionRapida() {
    const pedidoId = localStorage.getItem("pedido_id_reimprimir");
    const impresora = localStorage.getItem("impresora");
    
    if (!pedidoId) {
      alert("No hay pedido seleccionado para reimprimir");
      return;
    }
    
    // Mostrar feedback ligero no-bloqueante
    mostrarProcesamientoReimpresion();

    $.ajax({
      url: "reimprimir-ticket-rapido/", // Nueva URL optimizada
      data: {
        pedido_id: pedidoId,
        impresora: impresora,
      },
      type: "POST",
      timeout: 8000, // 8 segundos timeout
      success: function (response) {
        ocultarProcesamientoReimpresion();
        
        // ✅ VERIFICAR SI LA REIMPRESIÓN SE PROCESÓ EXITOSAMENTE
        if (response.success) {
          // 🚀 TODOS LOS USUARIOS: Reimpresión asíncrona universal
          if (response.impresion_async) {
            // Mostrar mensaje apropiado según tipo de usuario
            if (response.is_pesador) {
              mostrarMensajeReimpresionAsync(response.pedido_id, response.mensaje);
              // PESADOR: Redirigir rápidamente al POS
              setTimeout(function() {
                window.location.href = response.url;
              }, 1200);
            } else {
              mostrarMensajeReimpresionAsync(response.pedido_id, response.mensaje);
              // CAJERO: Mostrar que está imprimiendo en background
              setTimeout(function() {
                window.location.href = response.url;
              }, 1200);
            }
          } else {
            // Fallback por si acaso (no debería llegar aquí)
            mostrarMensajeReimpresionExito(response.pedido_id, response.mensaje);
            setTimeout(function() {
              window.location.href = response.url;
            }, 1000);
          }
        } else {
          // ❌ REIMPRESIÓN NO SE PROCESÓ: Mostrar error y no redirigir
          const errorMessage = response.message || "Error desconocido en la reimpresión";
          alert("❌ No se pudo procesar la reimpresión: " + errorMessage);
          console.error("Error del servidor:", response.error);
        }
      },
      error: function(xhr) {
        ocultarProcesamientoReimpresion();
        
        if (xhr.status === 408 || xhr.statusText === 'timeout') {
          alert("La reimpresión está tomando más tiempo del esperado. El ticket puede haberse impreso correctamente.");
        } else {
          const errorMsg = xhr.responseJSON?.message || "Error reimprimiendo el ticket";
          alert("Error: " + errorMsg);
        }
      }
    });
  }

  function mostrarProcesamientoReimpresion() {
    const modalHtml = `
      <div id="procesamiento-reimpresion-modal" style="
        position: fixed; top: 0; left: 0; width: 100%; height: 100%; 
        background-color: rgba(0,0,0,0.6); z-index: 9999; display: flex; 
        justify-content: center; align-items: center;">
        <div style="
          background: white; padding: 25px; border-radius: 10px; 
          text-align: center; max-width: 350px; box-shadow: 0 4px 20px rgba(0,0,0,0.3);">
          <div style="margin-bottom: 15px;">
            <div style="
              border: 3px solid #f3f3f3; border-top: 3px solid #007bff; 
              border-radius: 50%; width: 35px; height: 35px; 
              animation: spin 1s linear infinite; margin: 0 auto;">
            </div>
          </div>
          <h4 style="color: #333; margin-bottom: 8px;">🖨️ Reimprimiendo Ticket...</h4>
          <p style="color: #666; margin: 0; font-size: 14px;">El ticket se imprimirá automáticamente</p>
        </div>
      </div>
      <style>
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      </style>
    `;
    
    $("body").append(modalHtml);
  }

  function ocultarProcesamientoReimpresion() {
    $("#procesamiento-reimpresion-modal").remove();
  }

  function mostrarMensajeReimpresionAsync(pedidoId, mensaje) {
    const notificacionHtml = `
      <div id="notificacion-reimpresion" style="
        position: fixed; top: 20px; right: 20px; 
        background: #17a2b8; color: white; padding: 15px 20px; 
        border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        z-index: 9998; max-width: 350px;">
        <div style="display: flex; align-items: center;">
          <div style="margin-right: 10px;">🖨️</div>
          <div>
            <strong>Reimprimiendo Pedido #${pedidoId}</strong><br>
            <small>${mensaje}</small>
          </div>
        </div>
      </div>
    `;
    
    $("body").append(notificacionHtml);
    
    setTimeout(function() {
      $("#notificacion-reimpresion").fadeOut(500, function() {
        $(this).remove();
      });
    }, 4000);
  }

  function mostrarMensajeReimpresionExito(pedidoId, mensaje) {
    const notificacionHtml = `
      <div id="notificacion-reimpresion-exito" style="
        position: fixed; top: 20px; right: 20px; 
        background: #28a745; color: white; padding: 15px 20px; 
        border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        z-index: 9998; max-width: 350px;">
        <div style="display: flex; align-items: center;">
          <div style="margin-right: 10px;">✅</div>
          <div>
            <strong>Ticket #${pedidoId} Reimpreso</strong><br>
            <small>${mensaje}</small>
          </div>
        </div>
      </div>
    `;
    
    $("body").append(notificacionHtml);
    
    setTimeout(function() {
      $("#notificacion-reimpresion-exito").fadeOut(500, function() {
        $(this).remove();
      });
    }, 3000);
  }

  // ==================== SISTEMA DE BALANZA RÁPIDA PARA MODO ETIQUETA ====================
  
  // Variables globales para balanzas
  const balanzasDisponibles = {
    'ICM1': {
      id: 'ICM1',
      nombre: 'Balanza ICM1',
      ip: '192.168.1.103'
    },
    'ICM2': {
      id: 'ICM2', 
      nombre: 'Balanza ICM2',
      ip: '192.168.1.4'
    }
  };
  
  // Función para detectar modo de impresión y mostrar/ocultar botón
  function actualizarVisibilidadBotonBalanza() {
    const modoImpresion = localStorage.getItem('modoImpresion') || 'ticket';
    const botonBalanza = document.getElementById('boton-balanza-rapida');
    
    if (modoImpresion === 'etiqueta') {
      if (botonBalanza) {
        botonBalanza.style.display = 'block';
        actualizarTextoBotonBalanza();
      }
    } else {
      if (botonBalanza) {
        botonBalanza.style.display = 'none';
      }
    }
  }
  
  // Función para actualizar el texto del botón con la balanza seleccionada
  function actualizarTextoBotonBalanza() {
    const balanzaIp = localStorage.getItem('balanza');
    const textoElement = document.getElementById('balanza-rapida-texto');
    
    // Buscar la balanza por IP
    const balanzaEncontrada = Object.values(balanzasDisponibles).find(b => b.ip === balanzaIp);
    
    if (balanzaEncontrada) {
      textoElement.textContent = balanzaEncontrada.nombre;
    } else {
      textoElement.textContent = 'Seleccione Balanza';
    }
  }
  
  // Función para abrir modal de selección de balanzas
  function abrirModalBalanzaRapida() {
    const container = document.getElementById('balanzas-cards-container');
    container.innerHTML = '';
    
    // Crear cards para cada balanza
    Object.values(balanzasDisponibles).forEach(balanza => {
      const balanzaIpActual = localStorage.getItem('balanza');
      const esSeleccionada = balanzaIpActual === balanza.ip;
      
      const card = `
        <div class="col-md-6">
          <div class="card mb-3 balanza-card ${esSeleccionada ? 'border-success' : 'border-secondary'}" 
               data-balanza-id="${balanza.id}" 
               style="cursor: pointer; transition: all 0.3s ease;">
            <div class="card-header ${esSeleccionada ? 'bg-success text-white' : 'bg-light'}">
              <h5 class="card-title mb-0">
                <i class="fas fa-weight-hanging"></i> ${balanza.nombre}
                ${esSeleccionada ? '<i class="fas fa-check-circle float-end"></i>' : ''}
              </h5>
            </div>
            <div class="card-body text-center">
              <p class="card-text">
                <strong>IP:</strong> <code>${balanza.ip}</code><br>
                <small class="text-muted">Identificador: ${balanza.id}</small>
              </p>
              <button class="btn ${esSeleccionada ? 'btn-success' : 'btn-outline-success'} btn-seleccionar-balanza" 
                      data-balanza-id="${balanza.id}">
                <i class="fas ${esSeleccionada ? 'fa-check' : 'fa-hand-pointer'}"></i>
                ${esSeleccionada ? 'Seleccionada' : 'Seleccionar'}
              </button>
            </div>
          </div>
        </div>
      `;
      
      container.innerHTML += card;
    });
    
    // Agregar event listeners a las cards y botones
    document.querySelectorAll('.balanza-card').forEach(card => {
      card.addEventListener('click', function() {
        const balanzaId = this.dataset.balanzaId;
        seleccionarBalanzaRapida(balanzaId);
      });
    });
    
    document.querySelectorAll('.btn-seleccionar-balanza').forEach(btn => {
      btn.addEventListener('click', function(e) {
        e.stopPropagation(); // Evitar que se dispare el evento del card
        const balanzaId = this.dataset.balanzaId;
        seleccionarBalanzaRapida(balanzaId);
      });
    });
    
    // Mostrar modal
    const modal = new bootstrap.Modal(document.getElementById('modalBalanzaRapida'));
    modal.show();
  }
  
  // Función para seleccionar una balanza
  function seleccionarBalanzaRapida(balanzaId) {
    if (balanzasDisponibles[balanzaId]) {
      const balanza = balanzasDisponibles[balanzaId];
      
      // Guardar en localStorage usando el campo 'balanza' existente
      localStorage.setItem('balanza', balanza.ip);
      
      // Actualizar botón en navbar
      actualizarTextoBotonBalanza();
      
      // Cerrar modal
      const modal = bootstrap.Modal.getInstance(document.getElementById('modalBalanzaRapida'));
      if (modal) {
        modal.hide();
      }
      
      // Mostrar confirmación
      mostrarNotificacionBalanzaSeleccionada(balanza);
      
      console.log(`✅ Balanza seleccionada: ${balanza.nombre} (${balanza.ip})`);
    }
  }
  
  // Función para mostrar notificación de balanza seleccionada
  function mostrarNotificacionBalanzaSeleccionada(balanza) {
    const notificacionHtml = `
      <div id="notificacion-balanza-seleccionada" style="
        position: fixed; top: 20px; right: 20px; 
        background: #20c997; color: white; padding: 15px 20px; 
        border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        z-index: 9999; max-width: 350px;">
        <div style="display: flex; align-items: center;">
          <div style="margin-right: 10px;">
            <i class="fas fa-weight-hanging"></i>
          </div>
          <div>
            <strong>Balanza Seleccionada</strong><br>
            <small>${balanza.nombre} - IP: ${balanza.ip}</small>
          </div>
        </div>
      </div>
    `;
    
    $("body").append(notificacionHtml);
    
    setTimeout(function() {
      $("#notificacion-balanza-seleccionada").fadeOut(500, function() {
        $(this).remove();
      });
    }, 3000);
  }
  




  // ==================== INICIALIZACIÓN Y EVENT LISTENERS ====================