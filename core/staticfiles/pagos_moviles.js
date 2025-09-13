/**
 * JavaScript para la gestión de pagos móviles
 */

$(document).ready(function() {
    // Filtrar pagos
    $("#btn-filtrar").click(function() {
        filtrarPagos();
    });
    
    // Resetear filtros
    $("#btn-reset").click(function() {
        $("#form-filtros")[0].reset();
        filtrarPagos();
    });
    
    // Verificar pago
    $(document).on("click", ".verificar-pago", function() {
        const pagoId = $(this).data("id");
        const url = $(this).data("url");
        console.log("Botón Verificar clickeado. ID del pago:", pagoId);
        verificarPago(pagoId, url);
    });
});

/**
 * Filtra los pagos móviles según los criterios especificados
 */
function filtrarPagos() {
    $.ajax({
        type: "POST",
        url: "",
        data: $("#form-filtros").serialize(),
        success: function(data) {
            actualizarTablaPagos(data);
        }
    });
}

/**
 * Envía una solicitud para verificar un pago móvil
 * @param {number} pagoId - ID del pago a verificar
 * @param {string} url - URL para verificar el pago
 */
function verificarPago(pagoId, url) {
    console.log("Iniciando verificación del pago ID:", pagoId);
    $.ajax({
        type: "POST",
        url: url,
        data: {
            'pago_id': pagoId
        },
        beforeSend: function() {
            console.log("Enviando solicitud con datos:", {
                'pago_id': pagoId,
                'url': url
            });
        },
        success: function(response) {
            console.log("Respuesta recibida:", response);
            if (response.success) {
                console.log("Verificación exitosa, actualizando tabla");
                // Actualizar la tabla después de verificar
                filtrarPagos();
            } else {
                console.error("Error en verificación:", response.error);
                alert("Error al verificar el pago: " + response.error);
            }
        },
        error: function(xhr, status, error) {
            console.error("Error en la solicitud AJAX:", status, error);
            console.error("Detalles del error:", xhr.responseText);
            alert("Error en la comunicación con el servidor. Por favor, intente nuevamente.");
        }
    });
}

/**
 * Actualiza la tabla de pagos móviles con los datos recibidos
 * @param {Array} pagos - Lista de pagos móviles
 */
function actualizarTablaPagos(pagos) {
    const tabla = $("#pagos-moviles-tabla");
    tabla.empty();
    
    if (pagos.length === 0) {
        tabla.append(`
            <tr>
                <td colspan="9" class="text-center">No se encontraron pagos móviles</td>
            </tr>
        `);
        return;
    }
    
    pagos.forEach(pago => {
        const rowClass = pago.verificado ? "table-success" : "table-danger";
        const estadoBadge = pago.verificado 
            ? '<span class="badge bg-success">Verificado</span>' 
            : '<span class="badge bg-danger">No Verificado</span>';
        const accionVerificar = pago.verificado
            ? '<button class="btn btn-sm btn-secondary" disabled>Verificado</button>'
            : `<button class="btn btn-sm btn-success verificar-pago" data-id="${pago.id}" data-url="/pos/menu/pagos-moviles/verificar/">Verificar</button>`;
            
        tabla.append(`
            <tr class="${rowClass}">
                <td>${pago.referencia}</td>
                <td>${pago.monto}</td>
                <td>${pago.fecha}</td>
                <td>${pago.telefono}</td>
                <td>${pago.cliente}</td>
                <td>${pago.cajero}</td>
                <td>${pago.pedido_id}</td>
                <td>${estadoBadge}</td>
                <td>
                    <div class="btn-group">
                        ${accionVerificar}
                        <a href="/pos/${pago.pedido_id}/" class="btn btn-sm btn-info ms-1">Ver Pedido</a>
                    </div>
                </td>
            </tr>
        `);
    });
} 