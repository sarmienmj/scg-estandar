var url1 = $("#url-pos").text();
var url2 = $("#url-menu").text();
var url3 = $("#url-creditos").text();
var url4 = $("#url-prepesados").text();
var url5 = $("#url-inventario").text();
var url6 = $("#url-configuracion").text();
var urlLogout = $("#url-logout").text();
console.log(url3)
$("#home-pos-boton").on('click', function () {
    location.assign(url1);
});
$("#home-menu-boton").on('click', function () {
    location.assign(url2);
});
$("#home-prestamo-boton").on('click', function () {
    location.assign(url3);
});

// Nuevo: botón PRE PESADOS
$("#home-prepesados-boton").on('click', function () {
    location.assign(url4);
});

// Nuevo: botón INVENTARIO
$("#home-inventario-boton").on('click', function () {
    location.assign(url5);
});

// Nuevo: botón CONFIGURACIÓN
$("#home-configuracion-boton").on('click', function () {
    location.assign(url6);
});

// Manejador para el botón de cerrar sesión
$("#btn-cerrar-sesion").on('click', function() {
    // Mostrar el modal usando jQuery
    $("#cerrarSesionModal").modal('show');
});

// Manejador para el botón de confirmar en el modal
$("#confirmar-cerrar-sesion").on('click', function() {
    // Redirigir a la URL de logout
    window.location.href = urlLogout;
});

function mueveReloj(){
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
    setTimeout("mueveReloj()",1000)
}

function fechaHoy(){
    const tiempo = Date.now();
    const hoy = new Date(tiempo);
    str = hoy.toLocaleDateString()
    $("#fecha-span").text(str);
}
$(document).ready(function () {
    fechaHoy();
    mueveReloj();
})
