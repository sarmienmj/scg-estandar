// Función para obtener el valor de una cookie (para el token CSRF)


$(document).ready(function() {
    // Manejador de eventos para el botón de reimprimir ticket
    $('#btn-reimprimir-ticket').on('click', function() {
        console.log('Reimprimir ticket');
        // Obtener el ID del cierre actual de la URL
        const urlParts = window.location.pathname.split('/');
        const cierreId = urlParts[urlParts.length - 2];
        console.log("ID del cierre: " + cierreId);
        
        // Crear y mostrar mensaje de carga
        const loadingDiv = $('<div>', {
            id: 'loading-message',
            text: 'Imprimiendo ticket del cierre #' + cierreId + '... Por favor espere.'
        }).css({
            'position': 'fixed',
            'top': '50%',
            'left': '50%',
            'transform': 'translate(-50%, -50%)',
            'background-color': 'rgba(0, 0, 0, 0.7)',
            'color': 'white',
            'padding': '20px',
            'border-radius': '5px',
            'z-index': '9999'
        }).appendTo('body');
        
        // Enviar solicitud AJAX para reimprimir el ticket
        impresora = localStorage.getItem('impresora')
        $.ajax({
            url: '/pos/reimprimir-ticket-cierre/' + cierreId,
            type: 'POST',
            data: {
                impresora: impresora
            },
            success: function(response) {
                loadingDiv.remove();
                if (response.success) {
                    alert('El ticket se ha enviado a la impresora correctamente.');
                } else {
                    alert('Error: ' + (response.error || 'No se pudo imprimir el ticket.'));
                }
            },
            error: function(xhr, status, error) {
                loadingDiv.remove();
                alert('Error al comunicarse con el servidor: ' + error);
            }
        });
    });
}); 