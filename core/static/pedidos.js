$(document).ready(function() {
  // Manejar el envío del formulario de filtros
  $('#filtro-pedidos-form').on('submit', function(e) {
    e.preventDefault();
    
    // Recoger los datos del formulario
    const fechaInicio = document.getElementById('fecha_inicio').value;
    const fechaFin = document.getElementById('fecha_fin').value;
    const estado = document.getElementById('estado').value;
    const cliente = document.getElementById('cliente').value;
    const montoMin = document.getElementById('monto_min').value;
    const montoMax = document.getElementById('monto_max').value;
    const usuario = document.getElementById('usuario').value;
    const pedidoId = document.getElementById('pedido_id').value;
    const pesador = document.getElementById('pesador').value;
    
    // Mostrar indicador de carga
    $('#resultados-contador').removeClass('alert-info alert-success alert-warning alert-danger')
      .addClass('alert-info')
      .text('Cargando resultados...');
    
    // Enviar solicitud AJAX para filtrar
    $.ajax({
      url: "/pos/menu/pedidos/filtrar/",
      type: "POST",
      data: {
        'fecha_inicio': fechaInicio,
        'fecha_fin': fechaFin,
        'estado': estado,
        'cliente': cliente,
        'monto_min': montoMin,
        'monto_max': montoMax,
        'usuario': usuario,
        'pedido_id': pedidoId,
        'pesador': pesador
      },
      success: function(response) {
        console.log("Respuesta recibida:", response);
        // Actualizar la tabla con los resultados filtrados
        $('#menu-lista-pedidos').html(response.html);
        
        // Actualizar contador de resultados
        actualizarContador(response.count, response.total_count, response.limited);
      },
      error: function(xhr, status, error) {
        console.error("Error al filtrar los pedidos:", error);
        $('#resultados-contador').removeClass('alert-info alert-success alert-warning')
          .addClass('alert-danger')
          .text('Error al filtrar los pedidos: ' + error);
      }
    });
  });
  
  // Limpiar resultados cuando se resetea el formulario
  document.getElementById('filtro-pedidos-form').addEventListener('reset', function() {
    setTimeout(function() {
      document.getElementById('filtro-pedidos-form').dispatchEvent(new Event('submit'));
    }, 10);
  });
  
  // Actualizar contador de resultados
  function actualizarContador(cantidad, total, limitado) {
    const resultadosElement = document.getElementById('resultados-contador');
    
    if (cantidad === 0) {
      resultadosElement.className = 'alert alert-warning mb-3 mt-3';
      resultadosElement.textContent = 'No se encontraron pedidos con los filtros aplicados';
    } else {
      if (limitado) {
        resultadosElement.className = 'alert alert-warning mb-3 mt-3';
        resultadosElement.textContent = `Mostrando ${cantidad} de ${total} pedidos encontrados (resultados limitados a 3000 registros)`;
      } else {
        resultadosElement.className = 'alert alert-success mb-3 mt-3';
        resultadosElement.textContent = `Se encontraron ${cantidad} pedido(s)`;
      }
    }
  }
  
  // Añadir un filtro inicial al cargar la página
  $('#filtro-pedidos-form').submit();
  
  // Funcionalidad para marcar como devolución
  $(document).on('click', '.btn-marcar-devolucion', function() {
    const pedidoId = $(this).data('pedido-id');
    $('#pedido-devolucion-id').text(pedidoId);
    $('#pedido-id-devolucion').val(pedidoId);
    
    // Limpiar formulario
    $('#form-autorizacion-devolucion')[0].reset();
    $('#mensaje-autorizacion').hide();
    
    // Asegurar que el modal esté en el body
    const modal = $('#modalAutorizacionDevolucion');
    if (modal.parent().prop('tagName') !== 'BODY') {
      modal.appendTo('body');
    }
    
    // Aplicar estilos específicos para z-index
    modal.css('z-index', '9999');
    modal.find('.modal-dialog').css('z-index', '10000');
    modal.find('.modal-content').css('z-index', '10001');
    
    // Mostrar modal con configuración específica
    modal.modal({
      backdrop: 'static',
      keyboard: false,
      focus: true
    });
    
    modal.modal('show');
  });
  
  // Confirmar devolución
  $('#btn-confirmar-devolucion').on('click', function() {
    const formData = {
      pedido_id: $('#pedido-id-devolucion').val(),
      codigo: $('#codigo-autorizacion').val()
    };
    
    // Validar campos
    if (!formData.codigo) {
      mostrarMensajeAutorizacion('Por favor ingrese el código de autorización', 'danger');
      return;
    }
    
    // Deshabilitar botón mientras se procesa
    $(this).prop('disabled', true).html('<i class="fas fa-spinner fa-spin"></i> Procesando...');
    
    // Enviar solicitud AJAX
    $.ajax({
      url: "/pos/menu/pedidos/marcar-devolucion/",
      type: "POST",
      data: formData,
      success: function(response) {
        if (response.status === 'success') {
          mostrarMensajeAutorizacion(response.message, 'success');
          
          // Recargar la tabla después de 2 segundos
          setTimeout(function() {
            $('#modalAutorizacionDevolucion').modal('hide');
            $('#filtro-pedidos-form').submit(); // Recargar filtros
          }, 2000);
        } else {
          mostrarMensajeAutorizacion(response.message, 'danger');
        }
      },
      error: function(xhr, status, error) {
        let errorMessage = 'Error al procesar la devolución';
        if (xhr.responseJSON && xhr.responseJSON.message) {
          errorMessage = xhr.responseJSON.message;
        }
        mostrarMensajeAutorizacion(errorMessage, 'danger');
      },
      complete: function() {
        // Rehabilitar botón
        $('#btn-confirmar-devolucion').prop('disabled', false).html('<i class="fas fa-check"></i> Confirmar Devolución');
      }
    });
  });
  
  // Función helper para mostrar mensajes en el modal
  function mostrarMensajeAutorizacion(mensaje, tipo) {
    const alertClass = tipo === 'success' ? 'alert-success' : 'alert-danger';
    $('#mensaje-autorizacion')
      .removeClass('alert-success alert-danger')
      .addClass('alert ' + alertClass)
      .text(mensaje)
      .show();
  }
  
  // Funcionalidad para marcar como injustificado
  $(document).on('click', '.btn-marcar-injustificado', function() {
    const pedidoId = $(this).data('pedido-id');
    $('#pedido-injustificado-id').text(pedidoId);
    $('#pedido-id-injustificado').val(pedidoId);
    
    // Limpiar formulario
    $('#form-autorizacion-injustificado')[0].reset();
    $('#mensaje-autorizacion-injustificado').hide();
    
    // Asegurar que el modal esté en el body
    const modal = $('#modalAutorizacionInjustificado');
    if (modal.parent().prop('tagName') !== 'BODY') {
      modal.appendTo('body');
    }
    
    // Aplicar estilos específicos para z-index
    modal.css('z-index', '9999');
    modal.find('.modal-dialog').css('z-index', '10000');
    modal.find('.modal-content').css('z-index', '10001');
    
    // Mostrar modal con configuración específica
    modal.modal({
      backdrop: 'static',
      keyboard: false,
      focus: true
    });
    
    modal.modal('show');
  });
  
  // Confirmar injustificado
  $('#btn-confirmar-injustificado').on('click', function() {
    const formData = {
      pedido_id: $('#pedido-id-injustificado').val(),
      codigo: $('#codigo-autorizacion-injustificado').val()
    };
    
    // Validar campos
    if (!formData.codigo) {
      mostrarMensajeAutorizacionInjustificado('Por favor ingrese el código de autorización', 'danger');
      return;
    }
    
    // Deshabilitar botón mientras se procesa
    $(this).prop('disabled', true).html('<i class="fas fa-spinner fa-spin"></i> Procesando...');
    
    // Enviar solicitud AJAX
    $.ajax({
      url: "/pos/menu/pedidos/marcar-injustificado/",
      type: "POST",
      data: formData,
      success: function(response) {
        if (response.status === 'success') {
          mostrarMensajeAutorizacionInjustificado(response.message, 'success');
          
          // Recargar la tabla después de 2 segundos
          setTimeout(function() {
            $('#modalAutorizacionInjustificado').modal('hide');
            $('#filtro-pedidos-form').submit(); // Recargar filtros
          }, 2000);
        } else {
          mostrarMensajeAutorizacionInjustificado(response.message, 'danger');
        }
      },
      error: function(xhr, status, error) {
        let errorMessage = 'Error al procesar la marcación como injustificado';
        if (xhr.responseJSON && xhr.responseJSON.message) {
          errorMessage = xhr.responseJSON.message;
        }
        mostrarMensajeAutorizacionInjustificado(errorMessage, 'danger');
      },
      complete: function() {
        // Rehabilitar botón
        $('#btn-confirmar-injustificado').prop('disabled', false).html('<i class="fas fa-check"></i> Confirmar Injustificado');
      }
    });
  });
  
  // Funcionalidad para cancelar pedido
  $(document).on('click', '.btn-cancelar-pedido', function() {
    const pedidoId = $(this).data('pedido-id');
    $('#pedido-cancelar-id').text(pedidoId);
    $('#pedido-id-cancelar').val(pedidoId);
    
    // Limpiar formulario
    $('#form-autorizacion-cancelar')[0].reset();
    $('#mensaje-autorizacion-cancelar').hide();
    
    // Asegurar que el modal esté en el body
    const modal = $('#modalAutorizacionCancelar');
    if (modal.parent().prop('tagName') !== 'BODY') {
      modal.appendTo('body');
    }
    
    // Aplicar estilos específicos para z-index
    modal.css('z-index', '9999');
    modal.find('.modal-dialog').css('z-index', '10000');
    modal.find('.modal-content').css('z-index', '10001');
    
    // Mostrar modal con configuración específica
    modal.modal({
      backdrop: 'static',
      keyboard: false,
      focus: true
    });
    
    modal.modal('show');
  });
  
  // Confirmar cancelación
  $('#btn-confirmar-cancelar').on('click', function() {
    const formData = {
      codigo: $('#codigo-autorizacion-cancelar').val()
    };
    
    // Validar campos
    if (!formData.codigo) {
      mostrarMensajeAutorizacionCancelar('Por favor ingrese el código de autorización', 'danger');
      return;
    }
    
    // Deshabilitar botón mientras se procesa
    $(this).prop('disabled', true).html('<i class="fas fa-spinner fa-spin"></i> Procesando...');
    
    const pedidoId = $('#pedido-id-cancelar').val();
    
    // Enviar solicitud AJAX
    $.ajax({
      url: `/pos/menu/pedidos/delete/${pedidoId}`,
      type: "POST",
      data: formData,
      success: function(response) {
        if (response.status === 'success') {
          mostrarMensajeAutorizacionCancelar(response.message, 'success');
          
          // Recargar la tabla después de 2 segundos
          setTimeout(function() {
            $('#modalAutorizacionCancelar').modal('hide');
            $('#filtro-pedidos-form').submit(); // Recargar filtros
          }, 2000);
        } else {
          mostrarMensajeAutorizacionCancelar(response.message, 'danger');
        }
      },
      error: function(xhr, status, error) {
        let errorMessage = 'Error al cancelar el pedido';
        if (xhr.responseJSON && xhr.responseJSON.message) {
          errorMessage = xhr.responseJSON.message;
        }
        mostrarMensajeAutorizacionCancelar(errorMessage, 'danger');
      },
      complete: function() {
        // Rehabilitar botón
        $('#btn-confirmar-cancelar').prop('disabled', false).html('<i class="fas fa-check"></i> Confirmar Cancelación');
      }
    });
  });
  
  // Función helper para mostrar mensajes en el modal de injustificado
  function mostrarMensajeAutorizacionInjustificado(mensaje, tipo) {
    const alertClass = tipo === 'success' ? 'alert-success' : 'alert-danger';
    $('#mensaje-autorizacion-injustificado')
      .removeClass('alert-success alert-danger')
      .addClass('alert ' + alertClass)
      .text(mensaje)
      .show();
  }
  
  // Función helper para mostrar mensajes en el modal de cancelar
  function mostrarMensajeAutorizacionCancelar(mensaje, tipo) {
    const alertClass = tipo === 'success' ? 'alert-success' : 'alert-danger';
    $('#mensaje-autorizacion-cancelar')
      .removeClass('alert-success alert-danger')
      .addClass('alert ' + alertClass)
      .text(mensaje)
      .show();
  }

  // Exportar a Excel
  document.getElementById('btn-exportar-excel').addEventListener('click', function(e) {
    e.preventDefault();
    
    // Verificar si hay demasiados registros
    const resultadosText = document.getElementById('resultados-contador').textContent;
    if (resultadosText.includes('limitados') && !confirm('Estás intentando exportar una gran cantidad de registros. Esto podría tardar mucho tiempo. ¿Deseas continuar?')) {
      return;
    }
    
    // Recoger todos los valores del formulario
    const formData = new FormData(document.getElementById('filtro-pedidos-form'));
    
    // Redirigir a la URL de exportación con los parámetros del formulario
    let queryParams = new URLSearchParams(formData).toString();
    window.location.href = "/pos/menu/pedidos/exportar/?" + queryParams;
  });
});