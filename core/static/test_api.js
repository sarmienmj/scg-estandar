// Script de prueba para verificar que la API funciona
console.log('Probando API de ventas...');

// Probar GET request
fetch('/pos/menu/ventas/api/chart-data/')
    .then(response => {
        console.log('Status:', response.status);
        return response.json();
    })
    .then(data => {
        console.log('Respuesta GET:', data);
    })
    .catch(error => {
        console.error('Error en GET:', error);
    });

// Probar POST request
const testData = {
    start_date: '2024-01-01',
    end_date: '2024-12-31',
    type: 'total'
};

fetch('/pos/menu/ventas/api/chart-data/', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value || ''
    },
    body: JSON.stringify(testData)
})
.then(response => {
    console.log('Status POST:', response.status);
    return response.json();
})
.then(data => {
    console.log('Respuesta POST:', data);
})
.catch(error => {
    console.error('Error en POST:', error);
}); 