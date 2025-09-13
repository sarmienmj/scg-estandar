$(document).ready(function () {
    var abonoTotal = 0;
    
    // Obtener el valor del BCV con precisión decimal completa
    var bcvValorStr = $("#dolar-valor").data("valor") || "0";
    // Convertir comas decimales a puntos para parsear correctamente
    bcvValorStr = String(bcvValorStr).replace(',', '.');
    // Asegurar que los decimales se mantengan
    var bcv = parseFloat(bcvValorStr);
    
    // Logs para depuración
    console.log("Valor BCV original:", $("#dolar-valor").data("valor"));
    console.log("Valor BCV string procesado:", bcvValorStr);
    console.log("Valor BCV parseado:", bcv);
    console.log("Tipo de valor BCV:", typeof bcv);
    
    // Obtener el valor de deuda total y asegurar que los decimales se manejen correctamente
    var deudaTotalStr = $("#cliente-info").data("deuda-total") || "0";
    // Convertir cualquier valor con coma decimal a punto decimal para procesar correctamente
    deudaTotalStr = String(deudaTotalStr).replace(',', '.');
    var deudaTotal = parseFloat(deudaTotalStr);
    
    // Verificar en la consola el valor correcto
    console.log("Deuda total original:", $("#cliente-info").data("deuda-total"));
    console.log("Deuda total procesada:", deudaTotal);
    
    var movimientosCaja = {
        'ingresos': {
            'USD': {},
            'BS': {},
            'DEBITO': 0,
            'PAGOMOVIL': 0
        },
        'egresos': {
            'USD': {},
            'BS': {}
        }
    };

    var clienteId = $('#cliente-info').data('cliente-id');
    var abonos = [];
    var metodoActivo = null;
    
    // Variables para contar denominaciones
    var denominacionesUSD = {};
    var denominacionesBS = {};
    var vueltoUSD = {};
    var vueltoBS = {};

    // Abrir el modal al hacer clic en el botón
    $('#abrir-modal-abono').on('click', function() {
        $('#modal-abono').modal('show');
        // Inicializar la visibilidad del botón "Abonar Total"
        controlarVisibilidadAbonarTotal();
    });

    function actualizarAbono(metodo, cantidad) {
        // Asegurar que cantidad sea un número con decimales precisos
        cantidad = parseFloat(parseFloat(cantidad).toFixed(2));
        
        // Obtener denominaciones si es efectivo
        var denominaciones = {};
        if (metodo === 'Efectivo ($)' || metodo === 'Efectivo (Bs)') {
            denominaciones = obtenerDenominaciones();
        }

        // Calcular equivalente en dólares para mostrar
        let montoDolares = metodo === 'Efectivo ($)' ? 
            cantidad : parseFloat((cantidad / bcv).toFixed(4));
        
        // Logs adicionales para depurar
        console.log("Método:", metodo, "Cantidad:", cantidad, "BCV:", bcv, "Dólares calculados:", montoDolares);
        
        // Guardar información del abono con denominaciones
        var existingAbonoIndex = abonos.findIndex(a => a.metodo === metodo);
        
        // Obtener información del vuelto si es efectivo
        var vueltoInfo = {};
        if (metodo === 'Efectivo ($)') {
            vueltoInfo = { USD: { ...vueltoUSD } };
        } else if (metodo === 'Efectivo (Bs)') {
            vueltoInfo = { BS: { ...vueltoBS } };
        }
        
        if (existingAbonoIndex !== -1) {
            abonos[existingAbonoIndex].cantidad = cantidad;
            abonos[existingAbonoIndex].denominaciones = denominaciones;
            abonos[existingAbonoIndex].vuelto = vueltoInfo;
        } else {
            abonos.push({ 
                metodo: metodo, 
                cantidad: cantidad,
                denominaciones: denominaciones,
                vuelto: vueltoInfo
            });
        }

        // Recalcular movimientos de caja
        recalcularMovimientosCaja();

        // Recalcular el total
        abonoTotal = 0;
        abonos.forEach(function(abono) {
            let abonoDolares = abono.metodo === 'Efectivo ($)' ? 
                abono.cantidad : parseFloat((abono.cantidad / bcv).toFixed(4));
            abonoTotal += parseFloat(abonoDolares);
        });
        
        // Redondear el total solo al final para mostrar
        abonoTotal = parseFloat(abonoTotal.toFixed(2));
        
        console.log("Total abono calculado:", abonoTotal);
        
        // Actualizar la visualización
        mostrarResumenAbonos();
    }

    function mostrarResumenAbonos() {
        $('#detalles-abono-modal').empty();
        
        if (abonos.length === 0) {
            $('#detalles-abono-modal').html('<p class="text-muted">Selecciona un método de pago para registrar un abono.</p>');
            return;
        }
        
        var html = '<div class="table-responsive"><table class="table table-sm">';
        html += '<thead><tr><th>Método</th><th>Monto</th><th>Equivalente USD</th><th>Acciones</th></tr></thead><tbody>';
        
        abonos.forEach(function(abono, index) {
            var moneda = abono.metodo === 'Efectivo ($)' ? '$' : 'Bs';
            var montoDolares = abono.metodo === 'Efectivo ($)' ? 
                abono.cantidad : parseFloat((abono.cantidad / bcv).toFixed(4));
            
            // Crear detalles de denominaciones si existen
            var detallesDenominaciones = '';
            if (abono.denominaciones && Object.keys(abono.denominaciones).length > 0) {
                detallesDenominaciones = '<br><small class="text-muted">Denominaciones: ';
                var denoms = [];
                for (var valor in abono.denominaciones) {
                    var cant = abono.denominaciones[valor];
                    if (cant > 0) {
                        denoms.push(`${cant}x${moneda}${valor}`);
                    }
                }
                detallesDenominaciones += denoms.join(', ') + '</small>';
            }
                
            html += `<tr>
                <td>${abono.metodo}</td>
                <td>${moneda} ${abono.cantidad.toFixed(2)}${detallesDenominaciones}</td>
                <td>$ ${parseFloat(montoDolares).toFixed(2)}</td>
                <td><button class="btn btn-sm btn-danger eliminar-abono" data-index="${index}">Eliminar</button></td>
            </tr>`;
        });
        
        html += '</tbody></table></div>';
        
        // Calcular saldo restante con precisión decimal
        var saldoRestante = parseFloat((parseFloat(deudaTotal) - parseFloat(abonoTotal)).toFixed(2));
        
        html += `<div class="alert alert-info mt-3">
            <div class="row">
                <div class="col-md-4"><strong>Deuda total:</strong></div>
                <div class="col-md-8">$ ${parseFloat(deudaTotal).toFixed(2)}</div>
            </div>
            <div class="row">
                <div class="col-md-4"><strong>Total a abonar:</strong></div>
                <div class="col-md-8">$ ${parseFloat(abonoTotal).toFixed(2)}</div>
            </div>
        </div>`;
        
        if (saldoRestante > 0) {
            // Todavía hay deuda pendiente
            html += `<div class="alert alert-warning mt-2">
                <div class="row">
                    <div class="col-md-4"><strong>Deuda restante:</strong></div>
                    <div class="col-md-8">$ ${saldoRestante.toFixed(2)}</div>
                </div>
            </div>`;
        } else if (saldoRestante < 0) {
            // Abono mayor que la deuda (saldo a favor)
            html += `<div class="alert alert-success mt-2">
                <div class="row">
                    <div class="col-md-4"><strong>Saldo a favor:</strong></div>
                    <div class="col-md-8">$ ${Math.abs(saldoRestante).toFixed(2)}</div>
                </div>
                <div class="row mt-1">
                    <div class="col-12 small"><i>El cliente tendrá un saldo a favor que podrá utilizar en futuras compras.</i></div>
                </div>
            </div>`;
        } else {
            // Abono exacto
            html += `<div class="alert alert-success mt-2">
                <div class="row">
                    <div class="col-md-4"><strong>Estado:</strong></div>
                    <div class="col-md-8">Deuda saldada completamente</div>
                </div>
            </div>`;
        }
        
        $('#detalles-abono-modal').html(html);
        
        // Evento para eliminar abonos individuales
        $('.eliminar-abono').on('click', function() {
            var index = $(this).data('index');
            abonos.splice(index, 1);
            
            // Recalcular movimientos de caja
            recalcularMovimientosCaja();
            
            // Recalcular total
            abonoTotal = 0;
            abonos.forEach(function(abono) {
                let abonoDolares = abono.metodo === 'Efectivo ($)' ? 
                    abono.cantidad : parseFloat((abono.cantidad / bcv).toFixed(4));
                abonoTotal += parseFloat(abonoDolares);
            });
            
            mostrarResumenAbonos();
        });
    }

    function recalcularMovimientosCaja() {
        movimientosCaja = {
            'ingresos': {
                'USD': {},
                'BS': {},
                'DEBITO': 0,
                'PAGOMOVIL': 0
            },
            'egresos': {
                'USD': {},
                'BS': {}
            }
        };
        
        abonos.forEach(function(abono) {
            if (abono.metodo === 'Efectivo ($)') {
                // Procesar denominaciones para ingresos
                if (abono.denominaciones && Object.keys(abono.denominaciones).length > 0) {
                    for (var denom in abono.denominaciones) {
                        var cantidad = abono.denominaciones[denom];
                        if (cantidad > 0) {
                            if (!movimientosCaja.ingresos.USD[denom]) {
                                movimientosCaja.ingresos.USD[denom] = 0;
                            }
                            movimientosCaja.ingresos.USD[denom] += cantidad;
                        }
                    }
                }
                
                // Procesar vuelto para egresos
                if (abono.vuelto && abono.vuelto.USD && Object.keys(abono.vuelto.USD).length > 0) {
                    for (var denom in abono.vuelto.USD) {
                        var cantidad = abono.vuelto.USD[denom];
                        if (cantidad > 0) {
                            if (!movimientosCaja.egresos.USD[denom]) {
                                movimientosCaja.egresos.USD[denom] = 0;
                            }
                            movimientosCaja.egresos.USD[denom] += cantidad;
                        }
                    }
                }
                
            } else if (abono.metodo === 'Efectivo (Bs)') {
                // Procesar denominaciones para ingresos
                if (abono.denominaciones && Object.keys(abono.denominaciones).length > 0) {
                    for (var denom in abono.denominaciones) {
                        var cantidad = abono.denominaciones[denom];
                        if (cantidad > 0) {
                            if (!movimientosCaja.ingresos.BS[denom]) {
                                movimientosCaja.ingresos.BS[denom] = 0;
                            }
                            movimientosCaja.ingresos.BS[denom] += cantidad;
                        }
                    }
                }
                
                // Procesar vuelto para egresos
                if (abono.vuelto && abono.vuelto.BS && Object.keys(abono.vuelto.BS).length > 0) {
                    for (var denom in abono.vuelto.BS) {
                        var cantidad = abono.vuelto.BS[denom];
                        if (cantidad > 0) {
                            if (!movimientosCaja.egresos.BS[denom]) {
                                movimientosCaja.egresos.BS[denom] = 0;
                            }
                            movimientosCaja.egresos.BS[denom] += cantidad;
                        }
                    }
                }
                
            } else if (abono.metodo === 'Débito') {
                movimientosCaja.ingresos.DEBITO += abono.cantidad;
            } else if (abono.metodo === 'Pago Móvil') {
                movimientosCaja.ingresos.PAGOMOVIL += abono.cantidad;
            }
        });
    }

    // Limpiar los abonos y reiniciar
    function limpiarAbonos() {
        abonoTotal = 0;
        abonos = [];
        movimientosCaja = {
            'ingresos': {
                'USD': {},
                'BS': {},
                'DEBITO': 0,
                'PAGOMOVIL': 0
            },
            'egresos': {
                'USD': {},
                'BS': {}
            }
        };
        mostrarResumenAbonos();
    }

    // Función para controlar la visibilidad del botón "Abonar Total"
    function controlarVisibilidadAbonarTotal() {
        var botonAbonarTotal = $('#btn-abonar-total');
        
        // Solo mostrar el botón si el método activo es Débito o Pago Móvil
        if (metodoActivo === 'metodo-debito' || metodoActivo === 'metodo-pagomovil') {
            botonAbonarTotal.show();
        } else {
            botonAbonarTotal.hide();
        }
    }

    // Manejar clics en métodos de pago
    $('.list-group-item').on('click', function() {
        $('.list-group-item').removeClass('active');
        $(this).addClass('active');
        metodoActivo = $(this).attr('id');
        
        // Controlar visibilidad del botón "Abonar Total"
        controlarVisibilidadAbonarTotal();
        
        // Ocultar todas las secciones primero
        $('#seccion-denominaciones').hide();
        $('#denominaciones-usd').hide();
        $('#denominaciones-bs').hide();
        $('#monto-simple').hide();
        
        // Limpiar valores anteriores
        $('.denominacion-usd, .denominacion-bs').val(0);
        $('#monto-simple-input').val('');
        
        // Limpiar contadores de denominaciones
        denominacionesUSD = {};
        denominacionesBS = {};
        vueltoUSD = {};
        vueltoBS = {};
        actualizarTotalUSD();
        actualizarTotalBS();
        actualizarVueltoUSD();
        actualizarVueltoBS();
        
        // Mostrar la sección correspondiente según el método
        $('#seccion-denominaciones').show();
        
        switch(metodoActivo) {
            case 'metodo-efectivo-dolar':
                $('#denominaciones-usd').show();
                break;
            case 'metodo-efectivo-bolivar':
                $('#denominaciones-bs').show();
                break;
            case 'metodo-debito':
                $('#monto-simple').show();
                $('#titulo-monto-simple').text('Monto del Débito');
                $('#simbolo-moneda').text('Bs');
                break;
            case 'metodo-pagomovil':
                $('#monto-simple').show();
                $('#titulo-monto-simple').text('Monto del Pago Móvil');
                $('#simbolo-moneda').text('Bs');
                break;
        }
        
        // Remover formulario anterior si existe
        if ($('#form-abono').length) {
            $('#form-abono').remove();
        }
    });

    // Eventos para botones de denominaciones USD
    $(document).on('click', '.btn-denominacion-usd', function() {
        var valor = parseFloat($(this).data('valor'));
        
        if (!denominacionesUSD[valor]) {
            denominacionesUSD[valor] = 0;
        }
        denominacionesUSD[valor]++;
        
        actualizarTotalUSD();
        
        // Efecto visual del botón
        $(this).addClass('btn-success').removeClass('btn-outline-success');
        setTimeout(() => {
            $(this).removeClass('btn-success').addClass('btn-outline-success');
        }, 200);
    });

    // Eventos para botones de denominaciones BS
    $(document).on('click', '.btn-denominacion-bs', function() {
        var valor = parseFloat($(this).data('valor'));
        
        if (!denominacionesBS[valor]) {
            denominacionesBS[valor] = 0;
        }
        denominacionesBS[valor]++;
        
        actualizarTotalBS();
        
        // Efecto visual del botón
        $(this).addClass('btn-primary').removeClass('btn-outline-primary');
        setTimeout(() => {
            $(this).removeClass('btn-primary').addClass('btn-outline-primary');
        }, 200);
    });

    // Función para actualizar total USD
    function actualizarTotalUSD() {
        var total = 0;
        var detalles = [];
        
        for (var valor in denominacionesUSD) {
            var cantidad = denominacionesUSD[valor];
            if (cantidad > 0) {
                total += parseFloat(valor) * cantidad;
                detalles.push(`${cantidad}x$${valor}`);
            }
        }
        
        $('#total-usd').text('$' + total.toFixed(2));
        $('#detalle-denominaciones-usd').text(detalles.length > 0 ? detalles.join(', ') : 'Ninguna');
        
        // Calcular vuelto total
        var totalVuelto = 0;
        for (var valor in vueltoUSD) {
            var cantidad = vueltoUSD[valor];
            if (cantidad > 0) {
                totalVuelto += parseFloat(valor) * cantidad;
            }
        }
        
        // Calcular abono neto
        var abonoNeto = total - totalVuelto;
        $('#abono-neto-usd').text('$' + abonoNeto.toFixed(2));
        
        // Actualizar abono si hay un total válido
        if (abonoNeto > 0) {
            actualizarAbono('Efectivo ($)', abonoNeto);
        }
    }

    // Función para actualizar total BS
    function actualizarTotalBS() {
        var total = 0;
        var detalles = [];
        
        for (var valor in denominacionesBS) {
            var cantidad = denominacionesBS[valor];
            if (cantidad > 0) {
                total += parseFloat(valor) * cantidad;
                detalles.push(`${cantidad}x${valor}Bs`);
            }
        }
        
        $('#total-bs').text('Bs ' + total.toFixed(2));
        $('#detalle-denominaciones-bs').text(detalles.length > 0 ? detalles.join(', ') : 'Ninguna');
        
        // Calcular equivalente en USD del total recibido
        var equivalenteUsd = total / bcv;
        $('#equivalente-usd').text('$' + equivalenteUsd.toFixed(2));
        
        // Calcular vuelto total
        var totalVuelto = 0;
        for (var valor in vueltoBS) {
            var cantidad = vueltoBS[valor];
            if (cantidad > 0) {
                totalVuelto += parseFloat(valor) * cantidad;
            }
        }
        
        // Calcular abono neto
        var abonoNeto = total - totalVuelto;
        $('#abono-neto-bs').text('Bs ' + abonoNeto.toFixed(2));
        
        // Calcular equivalente USD del abono neto
        var abonoNetoUsd = abonoNeto / bcv;
        $('#abono-neto-bs-usd').text('$' + abonoNetoUsd.toFixed(2));
        
        // Actualizar abono si hay un total válido
        if (abonoNeto > 0) {
            actualizarAbono('Efectivo (Bs)', abonoNeto);
        }
    }

    // Botones para limpiar denominaciones
    $(document).on('click', '#limpiar-usd', function() {
        denominacionesUSD = {};
        actualizarTotalUSD();
    });

    $(document).on('click', '#limpiar-bs', function() {
        denominacionesBS = {};
        actualizarTotalBS();
    });

    // Eventos para botones de vuelto USD
    $(document).on('click', '.btn-vuelto-usd', function() {
        var valor = parseFloat($(this).data('valor'));
        
        if (!vueltoUSD[valor]) {
            vueltoUSD[valor] = 0;
        }
        vueltoUSD[valor]++;
        
        actualizarVueltoUSD();
        
        // Efecto visual del botón
        $(this).addClass('btn-danger').removeClass('btn-outline-danger');
        setTimeout(() => {
            $(this).removeClass('btn-danger').addClass('btn-outline-danger');
        }, 200);
    });

    // Eventos para botones de vuelto BS
    $(document).on('click', '.btn-vuelto-bs', function() {
        var valor = parseFloat($(this).data('valor'));
        
        if (!vueltoBS[valor]) {
            vueltoBS[valor] = 0;
        }
        vueltoBS[valor]++;
        
        actualizarVueltoBS();
        
        // Efecto visual del botón
        $(this).addClass('btn-danger').removeClass('btn-outline-danger');
        setTimeout(() => {
            $(this).removeClass('btn-danger').addClass('btn-outline-danger');
        }, 200);
    });

    // Función para actualizar vuelto USD
    function actualizarVueltoUSD() {
        var totalVuelto = 0;
        var detalles = [];
        
        for (var valor in vueltoUSD) {
            var cantidad = vueltoUSD[valor];
            if (cantidad > 0) {
                totalVuelto += parseFloat(valor) * cantidad;
                detalles.push(`${cantidad}x$${valor}`);
            }
        }
        
        $('#vuelto-usd').text('$' + totalVuelto.toFixed(2));
        $('#detalle-vuelto-usd').text(detalles.length > 0 ? detalles.join(', ') : 'Ninguno');
        
        // Calcular abono neto USD (recibido - vuelto)
        var totalRecibido = 0;
        for (var valor in denominacionesUSD) {
            var cantidad = denominacionesUSD[valor];
            if (cantidad > 0) {
                totalRecibido += parseFloat(valor) * cantidad;
            }
        }
        
        var abonoNeto = totalRecibido - totalVuelto;
        $('#abono-neto-usd').text('$' + abonoNeto.toFixed(2));
        
        // Actualizar abono si hay un total válido
        if (abonoNeto > 0) {
            actualizarAbono('Efectivo ($)', abonoNeto);
        }
    }

    // Función para actualizar vuelto BS
    function actualizarVueltoBS() {
        var totalVuelto = 0;
        var detalles = [];
        
        for (var valor in vueltoBS) {
            var cantidad = vueltoBS[valor];
            if (cantidad > 0) {
                totalVuelto += parseFloat(valor) * cantidad;
                detalles.push(`${cantidad}x${valor}Bs`);
            }
        }
        
        $('#vuelto-bs').text('Bs ' + totalVuelto.toFixed(2));
        $('#detalle-vuelto-bs').text(detalles.length > 0 ? detalles.join(', ') : 'Ninguno');
        
        // Calcular abono neto BS (recibido - vuelto)
        var totalRecibido = 0;
        for (var valor in denominacionesBS) {
            var cantidad = denominacionesBS[valor];
            if (cantidad > 0) {
                totalRecibido += parseFloat(valor) * cantidad;
            }
        }
        
        var abonoNeto = totalRecibido - totalVuelto;
        $('#abono-neto-bs').text('Bs ' + abonoNeto.toFixed(2));
        
        // Calcular equivalente USD del abono neto
        var abonoNetoUsd = abonoNeto / bcv;
        $('#abono-neto-bs-usd').text('$' + abonoNetoUsd.toFixed(2));
        
        // Actualizar abono si hay un total válido
        if (abonoNeto > 0) {
            actualizarAbono('Efectivo (Bs)', abonoNeto);
        }
    }

    // Botones para limpiar vuelto
    $(document).on('click', '#limpiar-vuelto-usd', function() {
        vueltoUSD = {};
        actualizarVueltoUSD();
    });

    $(document).on('click', '#limpiar-vuelto-bs', function() {
        vueltoBS = {};
        actualizarVueltoBS();
    });

    // Manejar input de monto simple (Débito/Pago Móvil)
    $(document).on('input', '#monto-simple-input', function() {
        var monto = parseFloat($(this).val()) || 0;
        var equivalenteUsd = monto / bcv;
        $('#equivalencia-texto').text('Equivalente: $' + equivalenteUsd.toFixed(2));
        
        if (monto > 0) {
                var metodoTexto = "";
                switch(metodoActivo) {
                    case 'metodo-debito':
                        metodoTexto = "Débito";
                        break;
                    case 'metodo-pagomovil':
                        metodoTexto = "Pago Móvil";
                        break;
                }
            actualizarAbono(metodoTexto, monto);
        }
    });

    // Función auxiliar para obtener denominaciones del método activo
    function obtenerDenominaciones() {
        var denominaciones = {};
        
        if (metodoActivo === 'metodo-efectivo-dolar') {
            // Copiar denominaciones USD
            for (var valor in denominacionesUSD) {
                if (denominacionesUSD[valor] > 0) {
                    denominaciones[valor] = denominacionesUSD[valor];
                }
            }
        } else if (metodoActivo === 'metodo-efectivo-bolivar') {
            // Copiar denominaciones BS
            for (var valor in denominacionesBS) {
                if (denominacionesBS[valor] > 0) {
                    denominaciones[valor] = denominacionesBS[valor];
                }
            }
        }
        
        return denominaciones;
    }

    // Botón para abonar el total
    $('#btn-abonar-total').on('click', function() {
        if (!metodoActivo) {
            alert("Primero seleccione un método de pago");
            return;
        }
        
        var metodoTexto = "";
        var montoTotal = 0;
        
        // Calcular la deuda restante después de los abonos ya registrados
        var deudaRestante = deudaTotal - abonoTotal;
        
        // Si no queda deuda, mostrar mensaje y salir
        if (deudaRestante <= 0) {
            alert("Ya se ha cubierto el total de la deuda con los abonos registrados.");
            return;
        }
        
        switch(metodoActivo) {
            case 'metodo-efectivo-dolar':
                metodoTexto = "Efectivo ($)";
                montoTotal = deudaRestante;
                break;
            case 'metodo-efectivo-bolivar':
                metodoTexto = "Efectivo (Bs)";
                montoTotal = parseFloat((deudaRestante * bcv).toFixed(2));
                break;
            case 'metodo-debito':
                metodoTexto = "Débito";
                montoTotal = parseFloat((deudaRestante * bcv).toFixed(2));
                break;
            case 'metodo-pagomovil':
                metodoTexto = "Pago Móvil";
                montoTotal = parseFloat((deudaRestante * bcv).toFixed(2));
                break;
        }
        
        // Preguntar confirmación
        if (confirm(`¿Desea abonar el resto de la deuda (${metodoTexto}: ${montoTotal.toFixed(2)}) ?`)) {
            actualizarAbono(metodoTexto, montoTotal);
            if ($('#form-abono').length) {
                $('#form-abono').remove();
            }
        }
    });

    // Evento para confirmar el abono
    $('#confirmar-abono-modal').on('click', function () {
        if (abonos.length === 0) {
            alert('Debe agregar al menos un método de pago antes de confirmar');
            return;
        }
        
        // Obtener la impresora configurada en localStorage
        var impresora = localStorage.getItem('impresora');
        
        $.ajax({
            type: 'POST',
            url: `/pos/abonar-credito/${clienteId}/`,
            data: {
                'abono_total': abonoTotal,
                'movimientos_caja': JSON.stringify(movimientosCaja),
                'abonos': JSON.stringify(abonos),
                'impresora': impresora
            },
            success: function (response) {
                if (response.status === 'success') {
                    alert('Abono realizado con éxito');
                    location.reload();
                } else {
                    alert(response.message || 'Error al procesar el abono');
                }
            },
            error: function() {
                alert('Error de conexión al procesar el abono');
            }
        });
    });

    $('.list-group-item').removeClass('active');
    console.log("Modal cerrado");
    
    // Evento para reiniciar estado cuando se cierra el modal de abono
    $('#modal-abono').on('hidden.bs.modal', function() {
        metodoActivo = null;
        $('#btn-abonar-total').hide();
        $('.list-group-item').removeClass('active');
    });
});

// Variables globales para cancelar abono
var abonoIdCancelar = null;

// Función para manejar el click en botones de cancelar abono
$(document).on('click', '.cancelar-abono-btn', function() {
    abonoIdCancelar = $(this).data('abono-id');
    var monto = $(this).data('monto');
    var metodo = $(this).data('metodo');
    var fecha = $(this).data('fecha');
    
    // Llenar los datos del abono en el modal
    $('#abono-monto-cancelar').text(monto);
    $('#abono-metodo-cancelar').text(metodo);
    $('#abono-fecha-cancelar').text(fecha);
    
    // Limpiar el campo de código y ocultar mensaje de error
    $('#codigoAutorizacionAbono').val('');
    $('#mensajeErrorAbono').hide();
    
    // Mostrar el modal
    $('#autorizacionCancelarAbonoModal').modal('show');
});

// Función para validar y cancelar el abono
$('#btnValidarCancelarAbono').on('click', function() {
    var codigo = $('#codigoAutorizacionAbono').val();
    
    if (!codigo) {
        $('#mensajeErrorAbono').text('Por favor ingrese el código de autorización').show();
        return;
    }
    
    if (!abonoIdCancelar) {
        $('#mensajeErrorAbono').text('Error: No se ha seleccionado ningún abono').show();
        return;
    }
    
    // Deshabilitar el botón durante la validación
    $('#btnValidarCancelarAbono').prop('disabled', true).text('Validando...');
    
    $.ajax({
        url: '/pos/cancelar-abono/',
        type: 'POST',
        data: {
            'password': codigo,
            'abono_id': abonoIdCancelar
        },
        success: function(response) {
            if (response.success) {
                // Éxito: cerrar modal y recargar página
                $('#autorizacionCancelarAbonoModal').modal('hide');
                alert('Abono cancelado exitosamente');
                location.reload(); // Recargar para actualizar la lista
            } else {
                // Error en la validación o cancelación
                $('#mensajeErrorAbono').text(response.error || 'Error al cancelar el abono').show();
            }
        },
        error: function(xhr, status, error) {
            console.error('Error en la petición AJAX:', error);
            $('#mensajeErrorAbono').text('Error de conexión. Intente nuevamente.').show();
        },
        complete: function() {
            // Rehabilitar el botón
            $('#btnValidarCancelarAbono').prop('disabled', false).text('Confirmar Cancelación');
        }
    });
});

// Limpiar datos cuando se cierra el modal de cancelar abono
$('#autorizacionCancelarAbonoModal').on('hidden.bs.modal', function() {
    abonoIdCancelar = null;
    $('#codigoAutorizacionAbono').val('');
    $('#mensajeErrorAbono').hide();
    $('#btnValidarCancelarAbono').prop('disabled', false).text('Confirmar Cancelación');
});

// Permitir envío del formulario con Enter
$('#formAutorizacionCancelarAbono').on('submit', function(e) {
    e.preventDefault();
    $('#btnValidarCancelarAbono').click();
}); 