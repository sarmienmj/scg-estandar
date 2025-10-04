// Función helper para generar fila de producto de forma consistente
function generarFilaProducto(x) {
    // Generar HTML para categorías
    let categoriasHtml = '';
    if (x.categorias && x.categorias.length > 0) {
        categoriasHtml = x.categorias.map(cat => 
            `<span class="badge bg-info me-1">${cat.nombre}</span>`
        ).join('');
    } else {
        categoriasHtml = '<span class="badge bg-light text-dark">Sin categoría</span>';
    }

    // Formatear cantidad a máximo 7 dígitos
    let cantidadFormateada = x.cantidad;
    if (x.cantidad) {
        const cantidadStr = parseFloat(x.cantidad).toString();
        cantidadFormateada = cantidadStr.substring(0, 8); // 7 dígitos + posible punto decimal
    }

    return `<tr>
                <td class="product-id">#${x.id}</td>
                <td class="product-name">${x.nombre}</td>
                <td class="product-quantity">
                  ${x.cantidad ? cantidadFormateada : '<span class="text-muted">-</span>'}
                </td>
                <td>
                  <span class="badge bg-secondary">${x.unidad}</span>
                </td>
                <td>
                  <span class="badge bg-primary">${x.moneda}</span>
                </td>
                <td class="product-price">
                  ${x.costo ? '$' + x.costo : '<span class="text-muted">-</span>'}
                </td>
                <td class="product-price">$${x.precio_detal}</td>
                <td class="product-price">
                  ${x.precio_mayor ? '$' + x.precio_mayor : '<span class="text-muted">-</span>'}
                </td>
                <td class="product-category">
                  ${categoriasHtml}
                </td>
                <td class="text-center">
                  <div class="btn-group" role="group">
                    <a href="edit/${x.id}" class="btn btn-action btn-edit me-1" 
                       title="Modificar producto">
                      ✏️
                    </a>
                    <a href="cantidad/${x.id}" class="btn btn-action btn-quantity me-1" 
                       title="Ajustar cantidad">
                      ±
                    </a>
                    <form method="post" action="delete/${x.id}" 
                          style="display: inline;" 
                          onsubmit="return confirm('¿Estás seguro de que quieres eliminar este producto?')">
                      <button type="submit" class="btn btn-action btn-delete" 
                              title="Eliminar producto">
                        🗑️
                      </button>
                    </form>
                  </div>
                </td>
              </tr>`;
}

function mueveReloj() {
    momentoActual = new Date()
    hora = momentoActual.getHours()
    minuto = momentoActual.getMinutes()
    segundo = momentoActual.getSeconds()

    // Formato 12 horas consistente
    let ampm = hora >= 12 ? 'PM' : 'AM';
    hora = hora % 12;
    hora = hora ? hora : 12; // La hora '0' debería ser '12'

    str_segundo = new String(segundo)
    if (str_segundo.length == 1)
        segundo = "0" + segundo

    str_minuto = new String(minuto)
    if (str_minuto.length == 1)
        minuto = "0" + minuto

    str_hora = new String(hora)
    if (str_hora.length == 1)
        hora = "0" + hora

    horaImprimible = hora + ":" + minuto + ":" + segundo + " " + ampm

    $("#reloj-span").text(horaImprimible);
    setTimeout("mueveReloj()", 1000)
}
function fechaHoy() {
    const tiempo = Date.now();
    const hoy = new Date(tiempo);
    str = hoy.toLocaleDateString()
    $("#fecha-span").text(str);
}

function EscogerImpresora() {

    var impresora = document.getElementById('impresora')
    var opcion = impresora.value;
    if (opcion == 'null') {
        alert("Por favor, escoja una impresora")
    } else {
        localStorage.setItem('impresora', opcion)
        alert(`Su impresora es la ${opcion}`)
    }
}
function EscogerBalanza() {

    var balanza = document.getElementById('balanza')
    var opcion = balanza.value;
    if (opcion == 'null') {
        alert("Por favor, escoja una impresora")
    } else {
        localStorage.setItem('balanza', opcion)
        alert(`Su balanza es la ${opcion}`)
    }
}
function guardarImpresoraBalanza(balanza) {
    var balanza = balanza.id
    var impresora = document.getElementById(`${balanza}`).value

    $.ajax({
        type: "post",
        url: "/pos/menu/balanzas-impresoras",
        data: { 'balanza': balanza, 'impresora': impresora },
        success: function (response) {
            alert("La balanza:" + balanza + " imprimirá en la impresora:" + impresora)
        }
    })
}

$(document).ready(function () {
    fechaHoy();
    mueveReloj();
    txt = $("#datos-string").html()

    if (txt != undefined) {

        txt = $("#datos-string").html().trim()
        productos = $("#productos-string").html().trim()
        productos = JSON.parse(productos)
        productosBjson = JSON.parse(txt)
        selects = $(".selects-numeros")
        opciontxt = ''


        productos.forEach(x => {
            opcion = `<option value="${x.id}">${x.nombre}</option>`
            opciontxt = opciontxt + opcion
        })
        selects.each(function () {
            var select = $(this);
            select.append(opciontxt)
        })
        productosBjson.forEach(x => {
            option = $(`#s${x.numero} option:contains('${x.producto}')`)
            option.prop("selected", true);
        })
    }

    $(".selects-numeros").on('change', function () {
        product_id = parseInt(this.value)
        numBlza = parseInt(this.id.slice(1))

        $.ajax({
            type: "POST", url: "/pos/menu/balanzas-productos", data: { 'numBalanza': numBlza, 'product_id': product_id },
        })
    })

    $("#boton-crear-producto").on('click', function () {
        url = $("#crear-producto-url").html();
        window.location.href = url;
    })
    $("#boton-crear-categoria").on('click', function () {
        url = $("#crear-categoria-url").html();
        window.location.href = url;
    })
    $("#boton-crear-usuario").on('click', function () {
        url = $("#crear-usuario-url").html();
        window.location.href = url;
    })
    $("#boton-crear-cliente").on('click', function () {
        url = $("#crear-cliente-url").html();
        window.location.href = url;
    })


    $("#buscar-cliente-btn").on('click', function () {
        console.log("HHHHHHHHH")
        cedula = $("#buscar-cliente-menu").val()
        $("#clientes-tabla").html("")
        $.ajax({
            url: "/pos/menu/cliente/buscar", type: 'POST', data: { 'cedula': cedula }, dataType: 'json',
            success: function (response) {
                response.forEach(x => {
                    row = `
                        <tr>
                            <th scope="row">${x.id}</th>
                            <td>${x.nombre}</td>
                            <td>${x.cedula}</td>
                            <td>${x.telefono}</td>
                            <td>${x.zona_vive}</td>
                            <td>${x.credito}</td>
                            <td><a href="edit/${x.id}">Modificar</a></td>
                            <td>
                                <form method="post" action="delete/${x.id}">
                                    <input type="submit" value="Eliminar">
                                </form>
                            </td>
                        </tr>`
                    $("#clientes-tabla").append(row)
                })

            }

        })
    })


    $("#buscar-pedido-btn").on('click', function () {
        id = $("#buscar-pedido-id-menu").val()
        if (id == '') {
            $("#menu-lista-pedidos").html("")
            $.ajax({
                url: "/pos/pedidosList/", type: 'POST', dataType: 'json',
                success: function (response) {
                    console.log(response)
                    response.forEach(x => {
                        fecha = x.fecha
                        if (x.status == 'Por pagar') {
                            row = `<tr class="pedido-listado" style="background-color: #efcaca;" ><th scope="row">${x.pk}</th><td>${fecha.slice(0, 10)}</td><td>${x.cliente}</td><td>pedido.cajero</td><td>${x.preciototal}</td><td>${x.status}</td><td><form method="post" action="delete/{{x.pk}}"><input type="submit" value="Eliminar"></form></td></tr>`
                        }
                        if (x.status == 'Pagado') {
                            row = `<tr class="pedido-listado" style="background-color: #80a77b;"><th scope="row">${x.pk}</th><td>${fecha.slice(0, 10)}</td><td>${x.cliente}</td><td>pedido.cajero</td><td>${x.preciototal}</td><td>${x.status}</td><td><form method="post" action="delete/{{x.pk}}"><input type="submit" value="Eliminar"></form></td></tr>`
                        }

                        $("#menu-lista-pedidos").append(row)
                    })

                }

            })
        } else {
            $("#menu-lista-pedidos").html("")
            $.ajax({
                type: "POST",
                url: "/pos/pedidosList/buscarPedido/",
                data: { 'id': id },
                success: function (pedido) {
                    pedido = JSON.parse(pedido)
                    console.log(typeof (pedido), pedido)
                    fecha = pedido.fecha
                    row = `<tr class="pedido-listado" ><th scope="row">${pedido.id}</th><td>${fecha.slice(0, 10)}</td><td>${pedido.cliente}</td><td>${pedido.cajero}</td><td>${pedido.total}</td><td>${pedido.estado}</td><td><form method="post" action="delete/{{x.pk}}"><input type="submit" value="Eliminar"></form></td></tr>`
                    $("#menu-lista-pedidos").append(row)

                }
            });
        }
    })
    $("#buscar-producto-nombre-btn").on('click', function () {
        buscar = $("#buscar-producto-nombre-list").val()
        if (buscar == '') {
            $("#tabla-productos-menu").html("")
            $.ajax({
                url: "/pos/menu/productos/buscar", type: 'POST', dataType: 'json', data: { buscar: buscar },
                success: function (response) {
                    response.forEach(x => {
                        $("#tabla-productos-menu").append(generarFilaProducto(x));
                    })
                }
            })
        } else {
            $("#tabla-productos-menu").html("")
            $.ajax({
                url: "/pos/menu/productos/buscar", type: 'POST', dataType: 'json', data: { buscar: buscar },
                success: function (response) {
                    response.forEach(x => {
                        $("#tabla-productos-menu").append(generarFilaProducto(x));
                    })
                }
            })
        }
    })
    $("#buscar-producto-id-btn").on('click', function () {
        let buscar = $("#buscar-producto-id-list").val().trim();
        $("#tabla-productos-menu").html("");
        if (buscar === '') {
            $.ajax({
                url: "/pos/menu/productos/buscar", type: 'POST', dataType: 'json', data: { buscar: '' },
                success: function (response) {
                    response.forEach(x => {
                        $("#tabla-productos-menu").append(generarFilaProducto(x));
                    })
                }
            })
        } else {
            // Buscar por ID o barcode
            $.ajax({
                url: "/pos/menu/productos/buscar", type: 'POST', dataType: 'json', data: { buscar: buscar },
                success: function (response) {
                    // Filtrar por barcode si no es numérico
                    let resultados = response;
                    if (!/^[0-9]+$/.test(buscar)) {
                        resultados = response.filter(x => x.barcode && x.barcode.toLowerCase() === buscar.toLowerCase());
                    } else {
                        // Si es numérico, mostrar todos los que coincidan por ID o barcode
                        resultados = response.filter(x => x.id == buscar || (x.barcode && x.barcode == buscar));
                    }
                    if (resultados.length === 0) {
                        $("#tabla-productos-menu").append('<tr><td colspan="10" class="text-center text-muted">No se encontraron productos</td></tr>');
                    } else {
                        resultados.forEach(x => {
                            $("#tabla-productos-menu").append(generarFilaProducto(x));
                        })
                    }
                }
            })
        }
    });
})
