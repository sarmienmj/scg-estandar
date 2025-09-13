var monto = 0;
var bcv_pagar_texto = $("#dolar-p-pagar").text().replace(',', '.');
var bcv_pagar = parseFloat(bcv_pagar_texto);

var pedido_id_pagar = parseInt($("#pedido-id-pagar").text());
var usuario_pagar = $("#usuario-pagar").text();
var precio_total_pagar_texto = $("#precio-total-pagar").text().replace(',', '.');
var precio_total_pagar = parseFloat(precio_total_pagar_texto);

var cliente = $("#cliente-pagar").text();
var credito = $("#credito-pagar").text();
var credito_plazo = $("#credito-plazo-pagar").text();

// Asegurar que credito sea un número válido
if (isNaN(parseFloat(credito))) {
    credito = "0";
}
credito = parseFloat(credito);

var precio_total_bolivar = (precio_total_pagar * bcv_pagar);

var vuelto = false

var efectivo_dolares = 0;
var efectivo_bolivares = 0;
var debito_bolivares= 0;
var pagos = []
var precio_total_nuevo = precio_total_pagar
var precio_total_bolivar_nuevo = precio_total_bolivar
precio_total = precio_total
var num = ""
var numero_total = ''
var pagado_credito = false
var pagado = false; // Variable para controlar si el pedido está pagado
var pagomovil_bolivares = 0;


function actualizarMetodoPagoActual(metodo){
    if(metodo=="dolar"){$("#metodo-pago-cantidad-actual").text("Efectivo: " + NumeroD(numero_total)+ "$")}
    if(metodo=="bolivar"){$("#metodo-pago-cantidad-actual").text("Efectivo: " + NumeroD(numero_total)+ "Bs.F")}
    if(metodo=="debito"){$("#metodo-pago-cantidad-actual").text("Debito: " + NumeroD(numero_total) + "Bs.F")}
    if(metodo=="pagomovil"){$("#metodo-pago-cantidad-actual").text("Pago Móvil: " + NumeroD(numero_total) + "Bs.F")}
    if(metodo=="credito"){$("#metodo-pago-cantidad-actual").text("Credito: " + NumeroD(numero_total) + "$")}
}
function calcularTotal(){
    let dolar = 0;
    let bolivar = 0;
    let debito = 0;
    let credito = 0;
    let pagomovil = 0;
    let dineroEsperado = {
        'ingresos': {
            'USD': {},
            'BS': {},
            'DEBITO': 0,
            'CREDITO': 0,
            'PAGOMOVIL': 0
        },
        'egresos': {
            'USD': {},
            'BS': {}
        }
    };

    pagos.forEach(pago => {
        if(pago["cantidad"] == 0) return;
        
        let cantidad = parseFloat(pago["cantidad"]);
        let esVuelto = cantidad < 0;
        let tipo = esVuelto ? 'egresos' : 'ingresos';
        
        if(pago["metodo"] == "Dolar"){
            dolar += cantidad;
            let denominacion = Math.abs(cantidad);
            if(!dineroEsperado[tipo].USD[denominacion]) {
                dineroEsperado[tipo].USD[denominacion] = 0;
            }
            dineroEsperado[tipo].USD[denominacion]++;
        }
        if(pago["metodo"] == "Bolivar"){                    
            bolivar += cantidad;
            let denominacion = Math.abs(cantidad);
            if(!dineroEsperado[tipo].BS[denominacion]) {
                dineroEsperado[tipo].BS[denominacion] = 0;
            }
            dineroEsperado[tipo].BS[denominacion]++;
        }
        if(pago["metodo"] == "Debito"){
            bolivar += parseFloat(cantidad);
            debito += parseFloat(cantidad);
            dineroEsperado.ingresos.DEBITO += parseFloat(cantidad);
        }
        if(pago["metodo"] == "PagoMovil"){
            bolivar += parseFloat(cantidad);
            pagomovil += parseFloat(cantidad);
            dineroEsperado.ingresos.PAGOMOVIL += parseFloat(cantidad);
        }
        if(pago["metodo"] == "Credito"){
            pagado_credito = true;
            dolar += parseFloat(cantidad);
            credito += parseFloat(cantidad);
            dineroEsperado.ingresos.CREDITO += parseFloat(cantidad);
        }
    });

    bolivar_a_dolar = (bolivar / bcv_pagar);
    dolar_restante = parseFloat(bolivar_a_dolar) + parseFloat(dolar);
    precio_total_nuevo = precio_total_pagar - dolar_restante;

    if(precio_total_nuevo <= 0){
        $("#boton-pagar").css('background-color','#198754')
    }else{
        $("#boton-pagar").css('background-color','#6c757d')
    }
    

    $("#restante-total-dolar").text(NumeroD(precio_total_nuevo) + "$")
    $("#restante-total-bolivar").text(NumeroD(precio_total_nuevo * bcv_pagar) + "Bs")
    abonado_dolar = (precio_total_pagar - precio_total_nuevo)
    abonado_bolivar = (abonado_dolar * bcv_pagar)
    $("#precio-total-abonado-dolar").text(NumeroD(abonado_dolar) + "$")
    $("#precio-total-abonado-bolivar").text(NumeroD(abonado_bolivar) + "Bs")

}
function eliminarPago(){
    
    $(".resumen-metodo-pago").unbind();
    $(".resumen-metodo-pago").on('click',function(){
        
        id = this.id.split("-");
        id = id[1] - 1
        pagos.forEach(pago =>{
            if (pago["id"] == id){
                delete(pagos[id])
                $("#"+ this.id ).remove()
                if(pago["metodo"] == "Credito"){
                    credito = parseFloat(credito) + parseFloat(pago["cantidad"])
                    actualizarCreditoTotal()
                }
                calcularTotal()
            }
        });
    })
}
function pagarDolar(){
    $(".btn-panel-d").unbind()
    $(".btn-panel-d").on('click', function(){

        numero = parseInt($("#"+this.id).text())
        if (vuelto == true){numero *= -1;}

        let pago = {id:pagos.length ,cantidad: numero, metodo:'Dolar'}
        pagos.push(pago)
        pagoDiv = `<div id="resumen-${pagos.length}" class="resumen-metodo-pago border eliminar"><p class="fs-6 ">Dolar: ${NumeroD(numero)} $</p></div>`
        $("#resumenDiv").append(pagoDiv)
        calcularTotal()
        eliminarPago()
    })
}
function pagarBolivar(){
    $(".btn-panel-b").unbind()
    $(".btn-panel-b").on('click', function(){

        numero = (parseFloat($("#"+this.id).text())).toFixed(2)
        if (vuelto == true){numero *= -1;}
        let pago = {id:pagos.length ,cantidad: numero, metodo:'Bolivar'}
        pagos.push(pago)
        pagoDiv = `<div id="resumen-${pagos.length}" class="resumen-metodo-pago border eliminar"><p class="fs-6 ">Bolivar: ${NumeroD(numero)} Bs</p></div>`
        $("#resumenDiv").append(pagoDiv)
        calcularTotal()
        eliminarPago()
    })
}
function pagarDebito(){
    var numero_t = ''
    $(".boton-calculadora-pagar").unbind()
    $(".boton-calculadora-pagar").on('click', function(){
        
        if ($("#" + this.id).text() == "Enter"){

            if(numero_t != 0){
                let pago = {id:pagos.length, cantidad: numero_t, metodo:'Debito'}
                pagos.push(pago)
                pagoDiv = `<div id="resumen-${pagos.length}" class="resumen-metodo-pago border eliminar"><p class="fs-6 ">Debito: ${NumeroD(numero_t)} Bs</p></div>`
                $("#resumenDiv").append(pagoDiv)
            }
        
            calcularTotal()
            eliminarPago()
            numero_t = ''
            $("#panel-texto-metodo").text("Debito: 0 Bs");
        }
        else if (this.id == "boton-calculadora-pagar-borrar"){
            numero_t =  numero_total.slice(0,-1)
            actualizarTextoDebito(numero_t)
        }
        else if (this.id == "boton-calculadora-pagar-coma"){
            numero_t +=  "."
            actualizarTextoDebito(numero_t)
        }
        else if(this.id == "boton-calculadora-pagar-d5"){
            if(precio_total_nuevo > 0){
                numero_t = (precio_total_nuevo * bcv_pagar)
            }else if(vuelto == true){
                
            }
            actualizarTextoDebito(numero_t)
        }
        else{
            numero = $("#" + this.id).text();
            numero_t += numero
            actualizarTextoDebito(numero_t)
           
        }
    })
}
function actualizarCreditoTotal(){
    // Asegurarse de que credito sea un número antes de mostrarlo
    let creditoValor = parseFloat(credito);
    if (isNaN(creditoValor)) {
        creditoValor = 0;
    }
    $("#credito-disponible").text(NumeroD(creditoValor) + " $");
}
function pagarCredito(){
    var numero_t = ''
    $(".boton-calculadora-pagar").unbind()
    $(".boton-calculadora-pagar").on('click', function(){
        
        if ($("#" + this.id).text() == "Enter"){

            if(numero_t != 0){
                if(parseFloat(numero_t) <= parseFloat(credito)){
                    credito = parseFloat(credito) - parseFloat(numero_t)
                    actualizarCreditoTotal()
                    let pago = {id:pagos.length, cantidad: numero_t, metodo:'Credito'}
                    pagos.push(pago)
                    pagoDiv = `<div id="resumen-${pagos.length}" class="resumen-metodo-pago border eliminar"><p class="fs-6 ">Credito: ${NumeroD(numero_t)} $</p></div>`
                    $("#resumenDiv").append(pagoDiv)
                }
                
            }
        
            calcularTotal()
            eliminarPago()
            numero_t = ''
            $("#panel-texto-metodo").text("Credito: 0 $");
        }
        else if (this.id == "boton-calculadora-pagar-borrar"){
            numero_t =  numero_total.slice(0,-1)
            actualizarTextoCredito(numero_t)
        }
        else if (this.id == "boton-calculadora-pagar-coma"){
            numero_t +=  "."
            actualizarTextoCredito(numero_t)
        }
        else if(this.id == "boton-calculadora-pagar-d5"){
            if(precio_total_nuevo > 0){
                numero_t = (precio_total_nuevo)
            }else if(vuelto == true){
                
            }
            actualizarTextoCredito(numero_t)
        }
        else{
            numero = $("#" + this.id).text();
            numero_t += numero
            actualizarTextoCredito(numero_t)
           
        }
    })
}
function actualizarTextoCredito(numero_t){
    $("#panel-texto-metodo").text("Credito: " + NumeroD(numero_t) + " $")
}
function actualizarTextoDebito(numero_t){
    $("#panel-texto-metodo").text("Debito: " + NumeroD(numero_t) + " Bs")
}
function darVuelto(){
    $(".metodos-pago").css('background-color', 'white');
    $("#boton-vuelto").unbind()
    $("#boton-vuelto").on('click', function(){
        vuelto = true
        $(".metodos-pago").css('background-color', 'white');
        $("#boton-vuelto").css('background-color','#198754')
        $("#panel-texto-metodo").text("Para dar vuelto seleccione Dolares o Bolivares.")
        $("#panel-texto-metodo").show();
        $("#panel-bolivares").css('display','none');
        $("#panel-dolares").css('display','none');
        $("#panel-debito").css('display','none');

    })
}
function apagarVuelto(){
    $("#boton-vuelto").css('background-color','#6c757d')
    $("#boton-vuelto").unbind()
    vuelto = false
    $("#panel-texto-metodo").text("")
    $(".metodos-pago").css('background-color', 'white');
}
function pagarPagoMovil(){
    // Manejar el botón de "Pagar Total"
    $("#btn-pagar-total-pagomovil").on('click', function() {
        // Obtener el valor restante en bolívares
        let restanteTexto = $("#restante-total-bolivar").text();
        
        // Extraer solo los números y convertir coma a punto para decimales
        let numeroLimpio = restanteTexto.replace(/[^\d,.-]/g, '').replace(',', '.');
        let restanteBolivares = parseFloat(numeroLimpio);
        
        if (!isNaN(restanteBolivares) && restanteBolivares > 0) {
            // Establecer el valor en el campo de monto
            $("#pagomovil-monto").val(restanteBolivares.toFixed(2));
        } else {
            alert("No hay monto restante para pagar");
        }
    });
    
    // Validar que la referencia tenga exactamente 4 dígitos
    $("#pagomovil-referencia").on('input', function() {
        // Asegurar que solo se ingresen números
        this.value = this.value.replace(/[^0-9]/g, '');
        
        // Limitar a 4 caracteres
        if (this.value.length > 4) {
            this.value = this.value.slice(0, 4);
        }
    });
    
    $("#confirmar-pagomovil").unbind();
    $("#confirmar-pagomovil").on('click', function(){
        let monto = parseFloat($("#pagomovil-monto").val());
        let telefono = $("#pagomovil-telefono").val();
        let referencia = $("#pagomovil-referencia").val();
        
        // Validaciones básicas
        if (isNaN(monto) || monto <= 0) {
            alert("Por favor ingrese un monto válido");
            return;
        }
        
        if (!telefono) {
            alert("Por favor ingrese un número de teléfono");
            return;
        }
        
        if (!referencia || referencia.length !== 4 || !/^\d{4}$/.test(referencia)) {
            alert("Por favor ingrese un número de referencia de exactamente 4 dígitos");
            return;
        }
        
        // Crear el objeto de pago
        let infoPagoMovil = {
            telefono: telefono,
            referencia: referencia
        };
        
        let pago = {
            id: pagos.length,
            cantidad: monto,
            metodo: 'PagoMovil',
            infoPago: infoPagoMovil
        };
        
        pagos.push(pago);
        
        // Añadir a la visualización
        let montoDolar = (monto / bcv_pagar).toFixed(2);
        let pagoDiv = `<div id="resumen-${pagos.length}" class="resumen-metodo-pago border eliminar">
            <p class="fs-6">Pago Móvil: ${NumeroD(monto)} Bs (${NumeroD(montoDolar)} $)<br>
            Ref: ${referencia}</p></div>`;
        
        $("#resumenDiv").append(pagoDiv);
        
        // Limpiar el formulario
        $("#pagomovil-monto").val('');
        $("#pagomovil-telefono").val('');
        $("#pagomovil-referencia").val('');
        
        calcularTotal();
        eliminarPago();
    });
}
$(document).ready(function () {
    $(".cliente-boton").on('click', function(){
        console.log(cliente,credito, credito_plazo)
    })
    
    // Asegurarse de que credito sea un número antes de mostrarlo
    let creditoValor = parseFloat(credito);
    if (isNaN(creditoValor)) {
        creditoValor = 0;
    }
    $('#credito-disponible').text(NumeroD(creditoValor) + " $");
    $("#p-pedido_id").text(`Pedido: #${pedido_id_pagar}`);
    $("#precio-total-dolar").text(`${NumeroD(precio_total_pagar)} $`);
    $("#precio-total-bolivar").text(`${NumeroD(precio_total_bolivar)} Bs.F`);
    $("#precio-total-abonado-dolar").text(`0.00  $`);
    $("#precio-total-abonado-bolivar").text(`0.00 Bs.F`);
    $("#restante-total-dolar").text(`${NumeroD(precio_total_pagar)} $`);
    $("#restante-total-bolivar").text(`${NumeroD(precio_total_bolivar)} Bs.F`);

    $('.metodos-pago').on('click', function(){
        $(".metodos-pago").css('background-color', 'white');
        $("#" + this.id).css('background-color', '#C7D4B6');
        metodo = this.id
        
        if(metodo=="dolar"){
            $("#panel-texto-metodo").css('display','none');
            $(".panel").css('display','none');
            $("#panel-dolares").css('display','flex');
            if (vuelto){$("#metodo-pago-cantidad-actual").text("Dar vuelto con Dolar")}else{$("#metodo-pago-cantidad-actual").text("Dolar")}
            
            pagarDolar();
        }
        if(metodo=="bolivar"){
            $("#panel-texto-metodo").css('display','none');
            $(".panel").css('display','none');
            $("#panel-bolivares").css('display','flex');
            if (vuelto){$("#metodo-pago-cantidad-actual").text("Dar vuelto con Bolivar")}else{$("#metodo-pago-cantidad-actual").text("Bolivar")}
            pagarBolivar();
        }
        if(metodo=="debito"){
            $("#panel-texto-metodo").css('display','block');
            $(".panel").css('display','none');
            $("#panel-debito").css('display','flex');
            $("#metodo-pago-cantidad-actual").text("Debito");
            pagarDebito();
        }
        if(metodo=="pagomovil"){
            $("#panel-texto-metodo").css('display','none');
            $(".panel").css('display','none');
            $("#panel-pagomovil").css('display','block');
            $("#metodo-pago-cantidad-actual").text("Pago Móvil");
            pagarPagoMovil();
        }
        if(metodo=="credito"){
            $("#panel-texto-metodo").css('display','block');
            $(".panel").css('display','none');
            $("#panel-debito").css('display','flex');
            $("#metodo-pago-cantidad-actual").text("Credito");
            
            // Mostrar modal de autorización
            var creditoAutorizado = false;
            $('#autorizacionCreditoModal').modal('show');
            
            // Limpiar valores anteriores
            $('#codigoAutorizacion').val('');
            $('#mensajeError').hide();
            
            // Configurar el detector de escaneo
            let lastKeyTime = 0;
            let buffer = '';
            const scanThreshold = 100; // milisegundos entre teclas para detectar escaneo

            // Detectar teclas para identificar escaneo
            $('#codigoAutorizacion').off('keyup').on('keyup', function(e) {
                const currentTime = new Date().getTime();
                
                // Si hay una pausa entre teclas mayor que el umbral, resetear el buffer
                if (currentTime - lastKeyTime > scanThreshold && buffer.length > 0) {
                    buffer = '';
                }
                
                // Actualizar la hora de la última tecla
                lastKeyTime = currentTime;
                
                // Agregar carácter al buffer
                if (e.key !== 'Enter') {
                    buffer += e.key;
                }
                
                // Si se presiona Enter, procesar como un escaneo completo
                if (e.key === 'Enter') {
                    e.preventDefault();
                    
                    // Asegurarse de que tenemos un código válido
                    if ($('#codigoAutorizacion').val().length > 0) {
                        // Submit automático del formulario
                        $('#formAutorizacionCredito').submit();
                    }
                }
            });
            
            // Manejar el envío del formulario de autorización
            $('#formAutorizacionCredito').off('submit').on('submit', function(e) {
                e.preventDefault(); // Prevenir el envío tradicional del formulario
                
                var codigo = $('#codigoAutorizacion').val();
                
                $.ajax({
                    type: "POST",
                    url: "/pos/validar-autorizacion-credito/",
                    data: {
                        'codigo': codigo
                    },
                    success: function(response) {
                        if(response.autorizado) {
                            creditoAutorizado = true;
                            $('#autorizacionCreditoModal').modal('hide');
                            $('#mensajeError').hide();
                            pagarCredito();
                        } else {
                            $('#mensajeError').show();
                            creditoAutorizado = false;
                        }
                    }
                });
            });

            if (!creditoAutorizado) {
                return;
            }
        }
    })

    // Agregar evento para autofocus cuando se muestra el modal
    $('#autorizacionCreditoModal').on('shown.bs.modal', function () {
        $('#codigoAutorizacion').focus();
    });

    // Agregar evento para autofocus cuando se muestra el modal de autorización de vuelto
    $('#autorizacionVueltoModal').on('shown.bs.modal', function () {
        $('#codigoAutorizacionVuelto').focus();
    });

    $("#boton-pagar").on('click', function(){
        // 🔒 VALIDACIÓN CRÍTICA: Evitar procesamiento múltiple
        if ($(this).prop("disabled")) {
            console.log("🚫 Botón de pago deshabilitado - procesamiento en curso");
            return false;
        }
        
        total_total = parseFloat(($("#restante-total-dolar").text()))
        impresora = localStorage.getItem('impresora')
        pedido_modificado = localStorage.getItem('pedido_modificado')
        credito_usado = 0

        let movimientosCaja = {
            'ingresos': {
                'USD': {},
                'BS': {},
                'DEBITO': 0,
                'CREDITO': 0,
                'PAGOMOVIL': 0
            },
            'egresos': {
                'USD': {},
                'BS': {}
            }
        };
        
        // Array para almacenar información específica de pagos móviles
        let pagoMoviles = [];

        pagos.forEach(pago => {
            if(pago.metodo == 'Credito'){
                credito_usado += parseFloat(pago.cantidad);
                movimientosCaja.ingresos.CREDITO += parseFloat(pago.cantidad);
            } else if(pago.metodo == 'PagoMovil' && pago.infoPago) {
                // Agregar información específica del pago móvil
                pagoMoviles.push({
                    referencia: pago.infoPago.referencia,
                    monto: pago.cantidad,
                    telefono: pago.infoPago.telefono
                });
                movimientosCaja.ingresos.PAGOMOVIL += parseFloat(pago.cantidad);
            } else {
                let cantidad = parseFloat(pago["cantidad"]);
                let esVuelto = cantidad < 0;
                let tipo = esVuelto ? 'egresos' : 'ingresos';
                
                if(pago["metodo"] == "Dolar"){
                    let denominacion = Math.abs(cantidad);
                    if(!movimientosCaja[tipo].USD[denominacion]) {
                        movimientosCaja[tipo].USD[denominacion] = 0;
                    }
                    movimientosCaja[tipo].USD[denominacion]++;
                }
                if(pago["metodo"] == "Bolivar"){                    
                    let denominacion = Math.abs(cantidad);
                    if(!movimientosCaja[tipo].BS[denominacion]) {
                        movimientosCaja[tipo].BS[denominacion] = 0;
                    }
                    movimientosCaja[tipo].BS[denominacion]++;
                }
                if(pago["metodo"] == "Debito"){
                    movimientosCaja.ingresos.DEBITO += parseFloat(cantidad);
                }
            }
        });

        // ⚠️ NUEVA VALIDACIÓN: Saldo a favor del POS (monto negativo)
        if (total_total < 0) {
            let saldoFavor = Math.abs(total_total);
            let saldoBolivares = (saldoFavor * bcv_pagar).toFixed(2);
            
            // Mostrar información del saldo a favor
            $('#saldo-favor-monto').html(`
                <span class="text-success">
                    Saldo a favor: $${saldoFavor.toFixed(2)} (${NumeroD(saldoBolivares)} Bs)
                </span>
            `);
            
            // Variable para controlar autorización
            var vueltoAutorizado = false;
            
            // Mostrar modal de autorización
            $('#autorizacionVueltoModal').modal('show');
            
            // Limpiar valores anteriores
            $('#codigoAutorizacionVuelto').val('');
            $('#mensajeErrorVuelto').hide();
            
            // Configurar detector de escaneo para autorización de vuelto
            let lastKeyTimeVuelto = 0;
            let bufferVuelto = '';
            const scanThresholdVuelto = 100;

            $('#codigoAutorizacionVuelto').off('keyup').on('keyup', function(e) {
                const currentTime = new Date().getTime();
                
                if (currentTime - lastKeyTimeVuelto > scanThresholdVuelto && bufferVuelto.length > 0) {
                    bufferVuelto = '';
                }
                
                lastKeyTimeVuelto = currentTime;
                
                if (e.key !== 'Enter') {
                    bufferVuelto += e.key;
                }
                
                if (e.key === 'Enter') {
                    e.preventDefault();
                    
                    if ($('#codigoAutorizacionVuelto').val().length > 0) {
                        $('#formAutorizacionVuelto').submit();
                    }
                }
            });
            
            // Manejar envío del formulario de autorización de vuelto
            $('#formAutorizacionVuelto').off('submit').on('submit', function(e) {
                e.preventDefault();
                
                var codigo = $('#codigoAutorizacionVuelto').val();
                
                $.ajax({
                    type: "POST",
                    url: "/pos/validar-autorizacion-vuelto/",
                    data: {
                        'codigo': codigo,
                        'monto_saldo': saldoFavor.toFixed(2)
                    },
                    success: function(response) {
                        if(response.autorizado) {
                            vueltoAutorizado = true;
                            $('#autorizacionVueltoModal').modal('hide');
                            $('#mensajeErrorVuelto').hide();
                            
                            // Continuar con el proceso de pago autorizado
                            console.log(`Saldo a favor autorizado por: ${response.supervisor}`);
                            procesarPago();
                        } else {
                            $('#mensajeErrorVuelto').show();
                            vueltoAutorizado = false;
                        }
                    },
                    error: function() {
                        alert("Error al validar autorización. Intente nuevamente.");
                    }
                });
            });
            
            return; // No proceder hasta que se autorice
        }

        // Validación de cambio excesivo ANTES de proceder con el pago
        if (total_total < -1) {
            // El cambio es mayor a 1 dólar, mostrar confirmación
            let cambioAbsoluto = Math.abs(total_total);
            let cambioBolivares = (cambioAbsoluto * bcv_pagar).toFixed(2);
            
            $('#cambio-excesivo-monto').html(`
                <span class="text-danger">
                    Cambio: $${cambioAbsoluto.toFixed(2)} (${NumeroD(cambioBolivares)} Bs)
                </span>
            `);
            
            // Mostrar modal de confirmación
            $('#confirmacionCambioModal').modal('show');
            
            // Manejar la confirmación
            $('#confirmarPagoExcesivo').off('click').on('click', function() {
                $('#confirmacionCambioModal').modal('hide');
                procesarPago(); // Proceder con el pago si confirma
            });
            
            return; // No proceder hasta que el usuario confirme
        }

        // Si el total es mayor a 0 o el cambio es menor a 1 dólar, proceder normalmente
        if (total_total <= 0){
            procesarPago();
        }
        
        // 🚀 FUNCIÓN PARA PROCESAR PAGO CON IMPRESIÓN ASÍNCRONA
        function procesarPago() {
            // 🔒 VALIDACIÓN CRÍTICA: Deshabilitar botón inmediatamente para evitar doble-pago
            $("#botonPagar").prop("disabled", true);
            
            // Mostrar modal de procesamiento
            mostrarModalProcesandoPago();
            
            $.ajax({
                type: "POST",
                url: "pagar-pedido-rapido/",  // Nueva URL optimizada
                data: {
                    'pedido_id': pedido_id_pagar,
                    'usuario': usuario_pagar,
                    'impresora': impresora,
                    'pedido_modificado': pedido_modificado,
                    'credito_usado': credito_usado,
                    'movimientos_caja': JSON.stringify(movimientosCaja),
                    'pagos_moviles': JSON.stringify(pagoMoviles)
                },
                timeout: 12000, // Aumentar timeout a 12 segundos
                success: function (response) {
                    ocultarModalProcesandoPago();
                    
                    if (response.success) {
                        // 🚀 PAGO PROCESADO EXITOSAMENTE
                        if (response.impresion_async) {
                            // Mostrar notificación de pago procesado
                            mostrarNotificacionPago(response.pedido_id, response.mensaje);
                            
                            // ⚡ REDIRECCIÓN OPTIMIZADA: 0.8 segundos para ver notificación
                            setTimeout(function() {
                                window.location.href = response.url;
                            }, 800);
                        } else {
                            // Sin impresión: mostrar éxito y redirección rápida
                            mostrarNotificacionPago(response.pedido_id, "Pago procesado correctamente");
                            setTimeout(function() {
                                window.location.href = response.url;
                            }, 500);
                        }
                    } else {
                        // 🔒 REHABILITAR BOTÓN en caso de error
                        $("#botonPagar").prop("disabled", false);
                        alert("Error: " + response.error);
                    }
                },
                error: function(xhr) {
                    ocultarModalProcesandoPago();
                    
                    // 🔒 REHABILITAR BOTÓN en caso de error
                    $("#botonPagar").prop("disabled", false);
                    
                    // Manejo mejorado de errores
                    if (xhr.status === 408 || xhr.statusText === 'timeout') {
                        alert("⏰ El pago está tomando más tiempo del esperado. Verifique si el pago se procesó antes de intentar nuevamente.");
                    } else if (xhr.status === 400) {
                        // Errores de validación (pedido ya pagado, caja cerrada, etc.)
                        const errorMsg = xhr.responseJSON?.error || "Error de validación";
                        alert("⚠️ " + errorMsg);
                    } else if (xhr.status === 404) {
                        // Pedido no encontrado
                        const errorMsg = xhr.responseJSON?.error || "Pedido no encontrado";
                        alert("❌ " + errorMsg);
                    } else {
                        // Error genérico
                        const errorMsg = xhr.responseJSON?.error || "Error procesando el pago";
                        alert("❌ Error: " + errorMsg);
                    }
                }
            });
        }
    })
    $("#volver-boton").on('click', function(){
        $.ajax({
            url: "/pos/volver-pos/", data: { 'pedido_id':pedido_id_pagar}, type: 'POST',
            success: function (urlDestino) {
                window.location.href = urlDestino;
            }
        })
    })
});

$("#boton-vuelto").on('click', function(){
    console.log("vuelto")
    vuelto = !vuelto
    $(".metodos-pago").css('background-color', 'white');
    if(vuelto){
        $("#boton-vuelto").css('background-color', '#198754');
        $("#panel-texto-metodo").text("Para dar vuelto seleccione Dolares o Bolivares.")
        $("#panel-texto-metodo").show();
    }
    else{
        $("#boton-vuelto").css('background-color', '#6c757d');
        $("#panel-texto-metodo").text("")
        $(".metodos-pago").css('background-color', 'white');
    }
    $("#panel-bolivares").css('display','none');
    $("#panel-dolares").css('display','none');
    $("#panel-debito").css('display','none');

    
})

// ==================== FUNCIONES PARA PAGO ASÍNCRONO ====================

function mostrarModalProcesandoPago() {
    const modalHtml = `
        <div id="modal-procesando-pago" style="
            position: fixed; top: 0; left: 0; width: 100%; height: 100%; 
            background-color: rgba(0,0,0,0.7); z-index: 9999; display: flex; 
            justify-content: center; align-items: center;">
            <div style="
                background: white; padding: 30px; border-radius: 10px; 
                text-align: center; max-width: 400px; box-shadow: 0 4px 20px rgba(0,0,0,0.3);">
                <div style="margin-bottom: 20px;">
                    <div style="
                        border: 4px solid #f3f3f3; border-top: 4px solid #28a745; 
                        border-radius: 50%; width: 40px; height: 40px; 
                        animation: spin 1s linear infinite; margin: 0 auto;">
                    </div>
                </div>
                <h4 style="color: #333; margin-bottom: 10px;">💳 Procesando Pago...</h4>
                <p style="color: #666; margin: 0;">El ticket se imprimirá automáticamente</p>
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

function ocultarModalProcesandoPago() {
    $("#modal-procesando-pago").remove();
}

function mostrarNotificacionPago(pedidoId, mensaje) {
    const notificacionHtml = `
        <div id="notificacion-pago" style="
            position: fixed; top: 20px; right: 20px; 
            background: #28a745; color: white; padding: 15px 20px; 
            border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            z-index: 9998; max-width: 350px;">
            <div style="display: flex; align-items: center;">
                <div style="margin-right: 10px;">💳</div>
                <div>
                    <strong>Pago Procesado - Pedido #${pedidoId}</strong><br>
                    <small>${mensaje}</small>
                </div>
            </div>
        </div>
    `;
    
    $("body").append(notificacionHtml);
    
    // Auto-remover después de 4 segundos
    setTimeout(function() {
        $("#notificacion-pago").fadeOut(500, function() {
            $(this).remove();
        });
    }, 4000);
}