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
function pagarCredito(id){
    window.location.href = "/pos/credito/" + id
}
function abonarCredito(id){
    impresora = localStorage.getItem("impresora");
    monto = $("#input-credito-abonar").val()
    $.ajax({
        url: id,
        type: "POST",
        data: {
            monto: monto,
            impresora:impresora
        },
        success: function (data) {
            console.log(data)
            window.location.href = "/pos/credito-detalles/credito/" + id
}})

}

function creditoPorId(id){
    cargarCreditos(id, 0, 0, 0)
}
function creditoPorCliente(id){
    cargarCreditos(0, id, 0, 0)
}
function creditoPorPedido(id){
    cargarCreditos(0, 0, id, 0)
}
function creditoPorEstado(estado){
    console.log(estado)
    cargarCreditos(0, 0, 0, estado)
}
function creditosTodos(){
    cargarCreditos(0, 0, 0, 0)
}
function creditosPorId(){
    id = $("#input-buscar-id").val()
    cargarCreditos(id, 0, 0, 0)
}
function creditosPorCliente(){
    id = $("#input-buscar-cliente").val()
    cargarCreditos(0, id, 0, 0)
}
function creditosPorPedido(){
    id = $("#input-buscar-pedido").val()
    cargarCreditos(0, 0, id, 0)
}

function cargarCreditos(id, cliente, pedido, estado) {
    data = {
        id: id,
        cliente: cliente,
        pedido: pedido,
        estado: estado
    }
    console.log(data)
    $.ajax({
        url: "/pos/creditos",
        type: "POST",
        data: data,
        success: function (creditos) {
            $("#tabla-creditos").empty();
            creditos = $.parseJSON(creditos);
            
            creditos.forEach(credito => {
                if(credito.estado == "Vencido"){
                    $("#tabla-creditos").append(
                        "<tr class='table-danger'><td>" + credito.id + "</td><td>" + credito.cliente + "</td><td>" + credito.pedido + "</td><td>" + credito.credito + "</td><td>" + credito.estado + "</td><td>" + credito.fecha + "</td><td>" + credito.fecha_vencimiento + "</td><td> <button onClick='pagarCredito(" + credito.id + ")' class='btn btn-success'>Abonar</button> </td></tr>"
                    )
                }
                else if(credito.estado == "Pagado"){
                    $("#tabla-creditos").append(
                        "<tr class='table-success'><td>" + credito.id + "</td><td>" + credito.cliente + "</td><td>" + credito.pedido + "</td><td>" + credito.credito + "</td><td>" + credito.estado + "</td><td>" + credito.fecha + "</td><td>" + credito.fecha_vencimiento + "</td><td> <button onClick='pagarCredito(" + credito.id + ")' class='btn btn-success'>Ver Abonos</button> </td></tr>"
                    );
                }else{
                    $("#tabla-creditos").append(
                        "<tr class='table-warning'><td>" + credito.id + "</td><td>" + credito.cliente + "</td><td>" + credito.pedido + "</td><td>" + credito.credito + "</td><td>" + credito.estado + "</td><td>" + credito.fecha + "</td><td>" + credito.fecha_vencimiento + "</td><td> <button onClick='pagarCredito(" + credito.id + ")' class='btn btn-success'>Abonar</button> </td></tr>"
                    );
                }
                
            });
        }
    })
}
$(document).ready(function () {
    fechaHoy();
    creditosTodos();
    mueveReloj();
})
