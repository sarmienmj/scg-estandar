// Ventas Charts - Manejo de gráficos y filtros de fecha
class VentasCharts {
    constructor() {
        this.charts = {};
        this.currentFilters = {
            startDate: null,
            endDate: null,
            type: 'total', // total, contado, credito
            grouping: 'day' // day, week, month
        };
        this.init();
    }

    init() {
        this.setupDateFilters();
        this.setupChartContainers();
        this.loadInitialData();
        this.setupResizeHandler();
    }

    setupResizeHandler() {
        // Manejar cambios de tamaño de ventana
        let resizeTimeout;
        window.addEventListener('resize', () => {
            clearTimeout(resizeTimeout);
            resizeTimeout = setTimeout(() => {
                if (this.charts.ventasPorFecha) {
                    this.charts.ventasPorFecha.resize();
                }
                if (this.charts.ventasPorHora) {
                    this.charts.ventasPorHora.resize();
                }
            }, 250);
        });
    }

    setupDateFilters() {
        // Botones de filtros predefinidos (tanto horizontales como verticales)
        const filterButtons = document.querySelectorAll('[data-date-filter]');
        filterButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                e.preventDefault();
                
                // Remover clase active de todos los botones
                filterButtons.forEach(btn => btn.classList.remove('active'));
                
                // Añadir clase active al botón clickeado
                button.classList.add('active');
                
                const filterType = button.dataset.dateFilter;
                this.applyDateFilter(filterType);
            });
        });

        // Date range picker personalizado
        const customDateInputs = document.querySelectorAll('.custom-date-input');
        customDateInputs.forEach(input => {
            input.addEventListener('change', () => {
                // Remover clase active de todos los botones predefinidos
                filterButtons.forEach(btn => btn.classList.remove('active'));
                this.applyCustomDateFilter();
            });
        });
    }

    applyDateFilter(filterType) {
        const today = new Date();
        let startDate, endDate;

        switch (filterType) {
            case '7days':
                startDate = new Date(today);
                startDate.setDate(today.getDate() - 6); // -6 para incluir hoy + 6 días anteriores = 7 días total
                break;
            case '30days':
                startDate = new Date(today);
                startDate.setDate(today.getDate() - 29); // -29 para incluir hoy + 29 días anteriores = 30 días total
                break;
            case '90days':
                startDate = new Date(today);
                startDate.setDate(today.getDate() - 89); // -89 para incluir hoy + 89 días anteriores = 90 días total
                break;
            case 'year':
                startDate = new Date(today.getFullYear(), 0, 1); // 1 de enero
                break;
            default:
                return;
        }

        endDate = new Date(today);
        this.updateDateInputs(startDate, endDate);
        this.currentFilters.startDate = startDate;
        this.currentFilters.endDate = endDate;
        this.loadChartData();
    }

    applyCustomDateFilter() {
        const startInput = document.getElementById('startDate');
        const endInput = document.getElementById('endDate');
        
        if (startInput.value && endInput.value) {
            this.currentFilters.startDate = new Date(startInput.value);
            this.currentFilters.endDate = new Date(endInput.value);
            this.loadChartData();
        }
    }

    updateDateInputs(startDate, endDate) {
        const startInput = document.getElementById('startDate');
        const endInput = document.getElementById('endDate');
        
        if (startInput && endInput) {
            startInput.value = this.formatDateForInput(startDate);
            endInput.value = this.formatDateForInput(endDate);
        }
    }

    formatDateForInput(date) {
        return date.toISOString().split('T')[0];
    }

    setupChartContainers() {
        // Crear contenedores para los gráficos
        const chartContainer = document.getElementById('ventasChartsContainer');
        if (!chartContainer) return;

        // Determinar clases CSS según el tamaño de pantalla
        const isMobile = window.innerWidth < 768;
        const marginClass = isMobile ? 'mb-2' : 'mb-4';

        // Contenedor para el gráfico de ventas por fecha
        const salesChartDiv = document.createElement('div');
        salesChartDiv.className = `col-12 ${marginClass}`;
        salesChartDiv.innerHTML = `
            <div class="card shadow-sm">
                <div class="card-header bg-white">
                    <h5 class="mb-0">📈 Ventas por Fecha</h5>
                </div>
                <div class="card-body">
                    <canvas id="ventasPorFechaChart" width="400" height="200"></canvas>
                </div>
            </div>
        `;
        chartContainer.appendChild(salesChartDiv);

        // Contenedor para el gráfico de ventas por horas
        const hourlyChartDiv = document.createElement('div');
        hourlyChartDiv.className = `col-12 ${marginClass}`;
        hourlyChartDiv.innerHTML = `
            <div class="card shadow-sm">
                <div class="card-header bg-white">
                    <h5 class="mb-0">🕐 Ventas por Horas</h5>
                </div>
                <div class="card-body">
                    <canvas id="ventasPorHoraChart" width="400" height="200"></canvas>
                </div>
            </div>
        `;
        chartContainer.appendChild(hourlyChartDiv);
    }

    loadInitialData() {
        // Cargar datos iniciales (últimos 7 días)
        this.applyDateFilter('7days');
    }

    async loadChartData() {
        if (!this.currentFilters.startDate || !this.currentFilters.endDate) return;

        try {
            const response = await fetch('/pos/menu/ventas/api/chart-data/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    start_date: this.currentFilters.startDate.toISOString().split('T')[0],
                    end_date: this.currentFilters.endDate.toISOString().split('T')[0],
                    type: this.currentFilters.type,
                    grouping: this.currentFilters.grouping
                })
            });

            if (response.ok) {
                const data = await response.json();
                this.renderVentasPorFechaChart(data.ventas_por_fecha);
                this.renderVentasPorHoraChart(data.ventas_por_hora);
            } else {
                console.error('Error cargando datos del gráfico');
            }
        } catch (error) {
            console.error('Error en la petición:', error);
        }
    }

    renderVentasPorFechaChart(data) {
        const ctx = document.getElementById('ventasPorFechaChart');
        if (!ctx) return;

        // Destruir gráfico existente si existe
        if (this.charts.ventasPorFecha) {
            this.charts.ventasPorFecha.destroy();
        }

        // Preparar datos para el gráfico
        const labels = data.map(item => {
            const date = new Date(item.fecha);
            
            if (this.currentFilters.grouping === 'day') {
                return date.toLocaleDateString('es-ES', { 
                    day: '2-digit', 
                    month: '2-digit' 
                });
            } else if (this.currentFilters.grouping === 'week') {
                return `Semana ${date.toLocaleDateString('es-ES', { 
                    day: '2-digit', 
                    month: '2-digit' 
                })}`;
            } else if (this.currentFilters.grouping === 'month') {
                return date.toLocaleDateString('es-ES', { 
                    month: 'long', 
                    year: 'numeric' 
                });
            }
        });

        const values = data.map(item => parseFloat(item.total_ventas));

        // Crear el gráfico
        this.charts.ventasPorFecha = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Ventas Totales',
                    data: values,
                    borderColor: '#001E62',
                    backgroundColor: 'rgba(0, 30, 98, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0, // Sin suavizado de curva
                    pointBackgroundColor: '#001E62',
                    pointBorderColor: '#ffffff',
                    pointBorderWidth: 1,
                    pointRadius: 3, // Puntos más pequeños
                    pointHoverRadius: 5 // Puntos hover más pequeños
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                aspectRatio: window.innerWidth < 768 ? 1.5 : 2, // Aspecto más cuadrado en móviles
                plugins: {
                    legend: {
                        display: true,
                        position: 'top',
                        labels: {
                            color: '#001E62',
                            font: {
                                weight: 'bold',
                                size: window.innerWidth < 768 ? 10 : 12
                            },
                            usePointStyle: true,
                            pointStyle: 'circle',
                            padding: window.innerWidth < 768 ? 8 : 12
                        }
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        backgroundColor: 'rgba(0, 30, 98, 0.9)',
                        titleColor: '#ffffff',
                        bodyColor: '#ffffff',
                        borderColor: '#001E62',
                        borderWidth: 1,
                        cornerRadius: 8,
                        displayColors: false,
                        titleFont: {
                            size: window.innerWidth < 768 ? 11 : 13
                        },
                        bodyFont: {
                            size: window.innerWidth < 768 ? 10 : 12
                        },
                        callbacks: {
                            title: function(context) {
                                // Obtener la fecha original del dataset
                                const dataIndex = context[0].dataIndex;
                                const originalDate = new Date(data[dataIndex].fecha);
                                
                                // Formatear según la agrupación
                                if (window.ventasCharts.currentFilters.grouping === 'day') {
                                    const diasSemana = ['Domingo', 'Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado'];
                                    const diaSemana = diasSemana[originalDate.getDay()];
                                    
                                    if (window.innerWidth < 768) {
                                        const fechaFormateada = originalDate.toLocaleDateString('es-ES', {
                                            day: 'numeric',
                                            month: 'short',
                                            year: 'numeric'
                                        });
                                        return `${diaSemana}, ${fechaFormateada}`;
                                    } else {
                                        const fechaFormateada = originalDate.toLocaleDateString('es-ES', {
                                            day: 'numeric',
                                            month: 'long',
                                            year: 'numeric'
                                        });
                                        return `${diaSemana}, ${fechaFormateada}`;
                                    }
                                } else if (window.ventasCharts.currentFilters.grouping === 'week') {
                                    const fechaFin = new Date(originalDate);
                                    fechaFin.setDate(originalDate.getDate() + 6);
                                    
                                    if (window.innerWidth < 768) {
                                        return `Semana ${originalDate.toLocaleDateString('es-ES', {day: '2-digit', month: '2-digit'})} - ${fechaFin.toLocaleDateString('es-ES', {day: '2-digit', month: '2-digit'})}`;
                                    } else {
                                        return `Semana del ${originalDate.toLocaleDateString('es-ES', {day: 'numeric', month: 'long'})} al ${fechaFin.toLocaleDateString('es-ES', {day: 'numeric', month: 'long', year: 'numeric'})}`;
                                    }
                                } else if (window.ventasCharts.currentFilters.grouping === 'month') {
                                    return originalDate.toLocaleDateString('es-ES', {
                                        month: 'long',
                                        year: 'numeric'
                                    });
                                }
                            },
                            label: function(context) {
                                return '💰 Ventas: $' + context.parsed.y.toLocaleString('es-ES');
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        display: true,
                        title: {
                            display: true,
                            text: this.currentFilters.grouping === 'day' ? '📅 Fecha' : 
                                 this.currentFilters.grouping === 'week' ? '📆 Semana' : '📅 Mes',
                            color: '#001E62',
                            font: {
                                weight: 'bold',
                                size: window.innerWidth < 768 ? 10 : 12
                            }
                        },
                        grid: {
                            display: false
                        },
                        ticks: {
                            color: '#666666',
                            font: {
                                size: window.innerWidth < 768 ? 9 : 11
                            },
                            maxRotation: window.innerWidth < 768 ? 45 : 0,
                            minRotation: window.innerWidth < 768 ? 45 : 0
                        }
                    },
                    y: {
                        display: true,
                        title: {
                            display: false, // Ocultar el label del eje Y
                        },
                        beginAtZero: true,
                        ticks: {
                            color: '#666666',
                            font: {
                                size: window.innerWidth < 768 ? 9 : 11
                            },
                            callback: function(value) {
                                // En móviles, mostrar valores más compactos
                                if (window.innerWidth < 768) {
                                    if (value >= 1000) {
                                        return '$' + (value / 1000).toFixed(1) + 'K';
                                    }
                                    return '$' + value.toLocaleString('es-ES');
                                }
                                return '$' + value.toLocaleString('es-ES');
                            }
                        },
                        grid: {
                            color: 'rgba(0, 30, 98, 0.1)',
                            lineWidth: 1
                        }
                    }
                },
                interaction: {
                    mode: 'nearest',
                    axis: 'x',
                    intersect: false
                }
            }
        });
    }

    renderVentasPorHoraChart(data) {
        const ctx = document.getElementById('ventasPorHoraChart');
        if (!ctx) return;

        // Destruir gráfico existente si existe
        if (this.charts.ventasPorHora) {
            this.charts.ventasPorHora.destroy();
        }

        // Crear array de las 24 horas con formato AM/PM
        const horas24 = [];
        for (let i = 0; i < 24; i++) {
            let horaFormateada;
            if (i === 0) horaFormateada = '12am';
            else if (i === 12) horaFormateada = '12pm';
            else if (i > 12) horaFormateada = (i - 12) + 'pm';
            else horaFormateada = i + 'am';
            horas24.push(horaFormateada);
        }

        // Crear arrays para ventas y pedidos con valores 0 para todas las horas
        const ventasValues = new Array(24).fill(0);
        const pedidosValues = new Array(24).fill(0);

        // Llenar los datos reales en las posiciones correctas
        data.forEach(item => {
            const hora = item.hora;
            ventasValues[hora] = parseFloat(item.total_ventas);
            pedidosValues[hora] = parseInt(item.cantidad_pedidos);
        });

        // Crear el gráfico
        this.charts.ventasPorHora = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: horas24,
                datasets: [
                    {
                        label: '💰 Ventas ($)',
                        data: ventasValues,
                        backgroundColor: 'rgba(0, 30, 98, 0.8)',
                        borderColor: '#001E62',
                        borderWidth: 1,
                        yAxisID: 'y'
                    },
                    {
                        label: '📦 Cantidad de Pedidos',
                        data: pedidosValues,
                        backgroundColor: 'rgba(65, 143, 222, 0.8)',
                        borderColor: '#418FDE',
                        borderWidth: 1,
                        yAxisID: 'y1',
                        type: 'line',
                        fill: false,
                        tension: 0,
                        pointBackgroundColor: '#418FDE',
                        pointBorderColor: '#ffffff',
                        pointBorderWidth: 1,
                        pointRadius: 4,
                        pointHoverRadius: 6
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                aspectRatio: window.innerWidth < 768 ? 1.5 : 2, // Aspecto más cuadrado en móviles
                plugins: {
                    legend: {
                        display: true,
                        position: 'top',
                        labels: {
                            color: '#001E62',
                            font: {
                                weight: 'bold',
                                size: window.innerWidth < 768 ? 10 : 12
                            },
                            usePointStyle: true,
                            pointStyle: 'circle',
                            padding: window.innerWidth < 768 ? 8 : 12
                        }
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        backgroundColor: 'rgba(0, 30, 98, 0.9)',
                        titleColor: '#ffffff',
                        bodyColor: '#ffffff',
                        borderColor: '#001E62',
                        borderWidth: 1,
                        cornerRadius: 8,
                        displayColors: true,
                        titleFont: {
                            size: window.innerWidth < 768 ? 11 : 13
                        },
                        bodyFont: {
                            size: window.innerWidth < 768 ? 10 : 12
                        },
                        callbacks: {
                            title: function(context) {
                                const horaIndex = context[0].dataIndex;
                                const horas24 = ['12am', '1am', '2am', '3am', '4am', '5am', '6am', '7am', '8am', '9am', '10am', '11am', '12pm', '1pm', '2pm', '3pm', '4pm', '5pm', '6pm', '7pm', '8pm', '9pm', '10pm', '11pm'];
                                return '🕐 ' + horas24[horaIndex];
                            },
                            label: function(context) {
                                if (context.dataset.label.includes('Ventas')) {
                                    return '💰 Ventas: $' + context.parsed.y.toLocaleString('es-ES');
                                } else {
                                    return '📦 Pedidos: ' + context.parsed.y;
                                }
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        display: true,
                        title: {
                            display: true,
                            text: '🕐 Hora del Día',
                            color: '#001E62',
                            font: {
                                weight: 'bold',
                                size: window.innerWidth < 768 ? 10 : 12
                            }
                        },
                        grid: {
                            display: false
                        },
                        ticks: {
                            color: '#666666',
                            font: {
                                size: window.innerWidth < 768 ? 9 : 11
                            },
                            maxTicksLimit: window.innerWidth < 768 ? 12 : 24, // Mostrar menos etiquetas en móviles
                            callback: function(value, index) {
                                // Mostrar solo algunas horas para evitar saturación
                                const labels = ['12am', '3am', '6am', '9am', '12pm', '3pm', '6pm', '9pm'];
                                if (window.innerWidth < 768) {
                                    return labels[index] || '';
                                }
                                // En desktop, mostrar todas las horas
                                const horas24 = ['12am', '1am', '2am', '3am', '4am', '5am', '6am', '7am', '8am', '9am', '10am', '11am', '12pm', '1pm', '2pm', '3pm', '4pm', '5pm', '6pm', '7pm', '8pm', '9pm', '10pm', '11pm'];
                                return horas24[index] || '';
                            }
                        }
                    },
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        title: {
                            display: true,
                            text: '💰 Ventas ($)',
                            color: '#001E62',
                            font: {
                                weight: 'bold',
                                size: window.innerWidth < 768 ? 10 : 12
                            }
                        },
                        beginAtZero: true,
                        ticks: {
                            color: '#666666',
                            font: {
                                size: window.innerWidth < 768 ? 9 : 11
                            },
                            callback: function(value) {
                                if (window.innerWidth < 768) {
                                    if (value >= 1000) {
                                        return '$' + (value / 1000).toFixed(1) + 'K';
                                    }
                                    return '$' + value.toLocaleString('es-ES');
                                }
                                return '$' + value.toLocaleString('es-ES');
                            }
                        },
                        grid: {
                            color: 'rgba(0, 30, 98, 0.1)',
                            lineWidth: 1
                        }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        title: {
                            display: true,
                            text: '📦 Cantidad de Pedidos',
                            color: '#418FDE',
                            font: {
                                weight: 'bold',
                                size: window.innerWidth < 768 ? 10 : 12
                            }
                        },
                        beginAtZero: true,
                        ticks: {
                            color: '#666666',
                            font: {
                                size: window.innerWidth < 768 ? 9 : 11
                            }
                        },
                        grid: {
                            drawOnChartArea: false
                        }
                    }
                },
                interaction: {
                    mode: 'nearest',
                    axis: 'x',
                    intersect: false
                }
            }
        });
    }

    getCSRFToken() {
        const token = document.querySelector('[name=csrfmiddlewaretoken]');
        return token ? token.value : '';
    }

    // Método para cambiar el tipo de ventas (total, contado, crédito)
    changeVentasType(type) {
        this.currentFilters.type = type;
        
        // Actualizar botones activos (tanto horizontales como verticales)
        const typeButtons = document.querySelectorAll('[onclick*="changeVentasType"]');
        typeButtons.forEach(button => {
            button.classList.remove('active');
            if (button.onclick.toString().includes(type)) {
                button.classList.add('active');
            }
        });
        
        this.loadChartData();
    }

    // Método para cambiar la agrupación temporal (día, semana, mes)
    changeGrouping(grouping) {
        this.currentFilters.grouping = grouping;
        
        // Actualizar botones activos (tanto horizontales como verticales)
        const groupingButtons = document.querySelectorAll('[onclick*="changeGrouping"]');
        groupingButtons.forEach(button => {
            button.classList.remove('active');
            if (button.onclick.toString().includes(grouping)) {
                button.classList.add('active');
            }
        });
        
        this.loadChartData();
    }
}

// Inicializar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', function() {
    // Verificar si estamos en la página de ventas
    if (document.getElementById('ventasChartsContainer')) {
        window.ventasCharts = new VentasCharts();
    }
}); 