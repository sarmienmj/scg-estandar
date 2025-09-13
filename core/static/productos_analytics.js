// Función helper para formatear números con separador de miles
function formatNumber(number, decimals = 0) {
    if (number === null || number === undefined) {
        return "0";
    }
    const formatted = number.toLocaleString('es-ES', {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals
    });
    return formatted.replace(/\s/g, '.').replace(',', '.');
}

// Función helper para obtener configuración de gráfico según el tamaño de pantalla
function getChartConfig() {
    const isMobile = window.innerWidth < 768;
    const isSmallMobile = window.innerWidth < 576;
    
    return {
        isMobile: isMobile,
        isSmallMobile: isSmallMobile,
        maxRotation: isMobile ? 90 : 45,
        fontSize: {
            ticks: isMobile ? 10 : 12,
            title: isMobile ? 11 : 12,
            legend: isMobile ? 11 : 12
        },
        padding: isSmallMobile ? 0.25 : 0.5
    };
}

// Productos Analytics - Manejo de gráficos y filtros
class ProductosAnalytics {
    constructor() {
        this.charts = {};
        this.currentFilters = {
            startDate: null,
            endDate: null,
            tipo: 'cantidad', // cantidad o valor
            unidad: 'todas' // U, K, o todas
        };
        this.currentMovimientoFilters = {
            startDate: null,
            endDate: null,
            productoId: null
        };
        this.init();
    }

    init() {
        this.setupDateFilters();
        this.setupCustomDateRange();
        this.setupTipoFilters();
        this.setupUnidadFilters();
        this.setupChartContainers();
        this.loadInitialData();
        this.setupResizeHandler();
        
        // Configurar movimientos de producto
        this.setupMovimientoFilters();
        this.setupMovimientoCustomDateRange();
        this.setupProductoSelector();
        this.setupMovimientoChartContainers();
    }

    setupCustomDateRange() {
        const startDateInput = document.getElementById('startDate');
        const endDateInput = document.getElementById('endDate');
        const applyButton = document.getElementById('applyDateRange');
        
        if (startDateInput && endDateInput && applyButton) {
            // Establecer fechas por defecto (últimos 7 días)
            const today = new Date();
            const sevenDaysAgo = new Date(today);
            sevenDaysAgo.setDate(today.getDate() - 6);
            
            startDateInput.value = sevenDaysAgo.toISOString().split('T')[0];
            endDateInput.value = today.toISOString().split('T')[0];
            
            // Evento para aplicar rango personalizado
            applyButton.addEventListener('click', () => {
                const startDate = new Date(startDateInput.value);
                const endDate = new Date(endDateInput.value);
                
                if (startDate > endDate) {
                    alert('La fecha de inicio no puede ser mayor que la fecha de fin');
                    return;
                }
                
                // Remover clase active de todos los botones predefinidos
                document.querySelectorAll('[data-date-filter]').forEach(btn => {
                    btn.classList.remove('active');
                });
                
                this.currentFilters.startDate = startDate;
                this.currentFilters.endDate = endDate;
                this.loadChartData();
            });
            
            // Evento para validar fechas en tiempo real
            endDateInput.addEventListener('change', () => {
                const startDate = new Date(startDateInput.value);
                const endDate = new Date(endDateInput.value);
                
                if (startDate > endDate) {
                    endDateInput.setCustomValidity('La fecha de fin debe ser posterior a la fecha de inicio');
                } else {
                    endDateInput.setCustomValidity('');
                }
            });
        }
    }

    setupMovimientoCustomDateRange() {
        const startDateInput = document.getElementById('movimientoStartDate');
        const endDateInput = document.getElementById('movimientoEndDate');
        const applyButton = document.getElementById('applyMovimientoDateRange');
        
        if (startDateInput && endDateInput && applyButton) {
            // Establecer fechas por defecto (últimos 7 días)
            const today = new Date();
            const sevenDaysAgo = new Date(today);
            sevenDaysAgo.setDate(today.getDate() - 6);
            
            startDateInput.value = sevenDaysAgo.toISOString().split('T')[0];
            endDateInput.value = today.toISOString().split('T')[0];
            
            // Evento para aplicar rango personalizado
            applyButton.addEventListener('click', () => {
                const startDate = new Date(startDateInput.value);
                const endDate = new Date(endDateInput.value);
                
                if (startDate > endDate) {
                    alert('La fecha de inicio no puede ser mayor que la fecha de fin');
                    return;
                }
                
                // Remover clase active de todos los botones predefinidos
                document.querySelectorAll('[data-movimiento-date-filter]').forEach(btn => {
                    btn.classList.remove('active');
                });
                
                this.currentMovimientoFilters.startDate = startDate;
                this.currentMovimientoFilters.endDate = endDate;
                
                if (this.currentMovimientoFilters.productoId) {
                    this.loadMovimientoData();
                }
            });
            
            // Evento para validar fechas en tiempo real
            endDateInput.addEventListener('change', () => {
                const startDate = new Date(startDateInput.value);
                const endDate = new Date(endDateInput.value);
                
                if (startDate > endDate) {
                    endDateInput.setCustomValidity('La fecha de fin debe ser posterior a la fecha de inicio');
                } else {
                    endDateInput.setCustomValidity('');
                }
            });
        }
    }

    setupResizeHandler() {
        // Manejar cambios de tamaño de ventana
        let resizeTimeout;
        window.addEventListener('resize', () => {
            clearTimeout(resizeTimeout);
            resizeTimeout = setTimeout(() => {
                if (this.charts.productosMasVendidos) {
                    this.charts.productosMasVendidos.resize();
                }
                if (this.charts.movimientosProducto) {
                    this.charts.movimientosProducto.resize();
                }
            }, 250);
        });
    }

    setupDateFilters() {
        // Botones de filtros predefinidos
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
    }

    setupTipoFilters() {
        // Botones de tipo de análisis
        const tipoButtons = document.querySelectorAll('[data-tipo]');
        tipoButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                e.preventDefault();
                
                // Remover clase active de todos los botones
                tipoButtons.forEach(btn => btn.classList.remove('active'));
                
                // Añadir clase active al botón clickeado
                button.classList.add('active');
                
                const tipo = button.dataset.tipo;
                this.currentFilters.tipo = tipo;
                this.loadChartData();
            });
        });
    }

    setupUnidadFilters() {
        // Botones de filtro de unidad
        const unidadButtons = document.querySelectorAll('[data-unidad]');
        unidadButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                e.preventDefault();
                
                // Remover clase active de todos los botones
                unidadButtons.forEach(btn => btn.classList.remove('active'));
                
                // Añadir clase active al botón clickeado
                button.classList.add('active');
                
                const unidad = button.dataset.unidad;
                this.currentFilters.unidad = unidad;
                this.loadChartData();
            });
        });
    }

    applyDateFilter(filterType) {
        const today = new Date();
        let startDate, endDate;

        switch (filterType) {
            case '7days':
                startDate = new Date(today);
                startDate.setDate(today.getDate() - 6);
                break;
            case '30days':
                startDate = new Date(today);
                startDate.setDate(today.getDate() - 29);
                break;
            case '90days':
                startDate = new Date(today);
                startDate.setDate(today.getDate() - 89);
                break;
            default:
                return;
        }

        endDate = new Date(today);
        this.currentFilters.startDate = startDate;
        this.currentFilters.endDate = endDate;
        
        // Actualizar campos de fecha personalizada
        const startDateInput = document.getElementById('startDate');
        const endDateInput = document.getElementById('endDate');
        if (startDateInput && endDateInput) {
            startDateInput.value = startDate.toISOString().split('T')[0];
            endDateInput.value = endDate.toISOString().split('T')[0];
        }
        
        this.loadChartData();
    }

    setupChartContainers() {
        // Crear contenedor para el gráfico
        const chartContainer = document.getElementById('productosChartsContainer');
        if (!chartContainer) return;

        // Contenedor para el gráfico de productos más vendidos
        const productosChartDiv = document.createElement('div');
        productosChartDiv.className = 'col-12 mb-4';
        productosChartDiv.innerHTML = `
            <div class="card shadow-sm">
                <div class="card-header bg-white">
                    <h5 class="mb-0" id="chartTitle">📊 Productos Más Vendidos</h5>
                </div>
                <div class="card-body">
                    <canvas id="productosMasVendidosChart" width="400" height="200"></canvas>
                </div>
            </div>
        `;
        chartContainer.appendChild(productosChartDiv);
    }

    loadInitialData() {
        // Cargar datos iniciales (últimos 7 días)
        this.applyDateFilter('7days');
    }

    async loadChartData() {
        if (!this.currentFilters.startDate || !this.currentFilters.endDate) return;

        try {
            const response = await fetch('/pos/menu/productos-analytics/api/productos-mas-vendidos/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    start_date: this.currentFilters.startDate.toISOString().split('T')[0],
                    end_date: this.currentFilters.endDate.toISOString().split('T')[0],
                    tipo: this.currentFilters.tipo,
                    unidad: this.currentFilters.unidad,
                    limit: 10
                })
            });

            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    this.renderProductosMasVendidosChart(data.data, data.periodo, data.tipo_analisis, data.unidad_filtro);
                } else {
                    console.error('Error en la respuesta:', data.error);
                }
            } else {
                console.error('Error cargando datos del gráfico');
            }
        } catch (error) {
            console.error('Error en la petición:', error);
        }
    }

    renderProductosMasVendidosChart(data, periodo, tipoAnalisis, unidadFiltro) {
        const ctx = document.getElementById('productosMasVendidosChart');
        if (!ctx) return;

        // Destruir gráfico existente si existe
        if (this.charts.productosMasVendidos) {
            this.charts.productosMasVendidos.destroy();
        }

        // Preparar datos para el gráfico
        const labels = data.map(item => item.producto);
        let datasets = [];

        if (tipoAnalisis === 'cantidad') {
            // Gráfico por cantidad
            datasets.push({
                label: `Cantidad Vendida (${unidadFiltro === 'U' ? 'Unidades' : unidadFiltro === 'K' ? 'Kilos' : 'Total'})`,
                data: data.map(item => item.cantidad),
                backgroundColor: 'rgba(0, 30, 98, 0.8)',
                borderColor: 'rgba(0, 30, 98, 1)',
                borderWidth: 2,
                borderRadius: 4,
                borderSkipped: false,
            });
        } else {
            // Gráfico por valor
            datasets.push({
                label: 'Valor Total (USD)',
                data: data.map(item => item.valor_usd),
                backgroundColor: 'rgba(65, 143, 222, 0.8)',
                borderColor: 'rgba(65, 143, 222, 1)',
                borderWidth: 2,
                borderRadius: 4,
                borderSkipped: false,
                yAxisID: 'y'
            });
        }

        // Actualizar título del gráfico
        const chartTitle = document.getElementById('chartTitle');
        if (chartTitle) {
            const tipoText = tipoAnalisis === 'cantidad' ? 'Cantidad' : 'Valor';
            const unidadText = unidadFiltro === 'U' ? 'Unidades' : unidadFiltro === 'K' ? 'Kilos' : 'Todas las Unidades';
            chartTitle.textContent = `📊 Top 10 Productos por ${tipoText} - ${unidadText}`;
        }

        // Configuración del gráfico
        const chartConfig = getChartConfig();
        const config = {
            type: 'bar',
            data: {
                labels: labels,
                datasets: datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: true,
                        position: 'top',
                        labels: {
                            font: {
                                size: chartConfig.fontSize.legend
                            }
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const dataIndex = context.dataIndex;
                                const item = data[dataIndex];
                                let label = context.dataset.label + ': ';
                                
                                if (tipoAnalisis === 'cantidad') {
                                    label += item.cantidad_formatted + ' ' + item.unidad;
                                    label += ' (Vendido ' + item.veces_vendido_formatted + ' veces)';
                                } else {
                                    label += '$' + item.valor_usd_formatted + ' USD';
                                    label += ' / ' + item.valor_bs_formatted + ' Bs.F';
                                    label += ' (' + item.cantidad_formatted + ' ' + item.unidad + ')';
                                }
                                return label;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        ticks: {
                            maxRotation: chartConfig.maxRotation,
                            minRotation: 0,
                            font: {
                                size: chartConfig.fontSize.ticks
                            }
                        }
                    },
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: tipoAnalisis === 'cantidad' ? 'Cantidad' : 'Valor (USD)',
                            font: {
                                size: chartConfig.fontSize.title
                            }
                        },
                        ticks: {
                            callback: function(value) {
                                return formatNumber(value, tipoAnalisis === 'cantidad' ? 2 : 2);
                            },
                            font: {
                                size: chartConfig.fontSize.ticks
                            }
                        }
                    }
                }
            }
        };

        // Crear el gráfico
        this.charts.productosMasVendidos = new Chart(ctx, config);

        // Mostrar información del período
        this.showPeriodoInfo(periodo);
    }

    showPeriodoInfo(periodo) {
        // Crear o actualizar información del período
        let periodoInfo = document.getElementById('periodoInfo');
        if (!periodoInfo) {
            periodoInfo = document.createElement('div');
            periodoInfo.id = 'periodoInfo';
            periodoInfo.className = 'alert alert-info mt-3';
            document.getElementById('productosChartsContainer').appendChild(periodoInfo);
        }
        
        periodoInfo.innerHTML = `
            <strong>📅 Período de Análisis:</strong> ${periodo.inicio} - ${periodo.fin}
        `;
    }

    setupMovimientoFilters() {
        // Botones de filtros de fecha para movimientos
        const filterButtons = document.querySelectorAll('[data-movimiento-date-filter]');
        filterButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                e.preventDefault();
                
                // Remover clase active de todos los botones
                filterButtons.forEach(btn => btn.classList.remove('active'));
                
                // Añadir clase active al botón clickeado
                button.classList.add('active');
                
                const filterType = button.dataset.movimientoDateFilter;
                this.applyMovimientoDateFilter(filterType);
            });
        });
    }

    setupProductoSelector() {
        const productoSelector = document.getElementById('productoSelector');
        const productoSearch = document.getElementById('productoSearch');
        const productoDropdown = document.getElementById('productoDropdown');
        
        if (productoSelector && productoSearch && productoDropdown) {
            // Obtener todas las opciones del select original
            const originalOptions = Array.from(productoSelector.querySelectorAll('option')).slice(1); // Excluir la primera opción vacía
            
            // Función para filtrar productos
            const filterProductos = (searchTerm) => {
                const filtered = originalOptions.filter(option => {
                    const nombre = option.getAttribute('data-nombre') || '';
                    const displayText = option.textContent.toLowerCase();
                    return nombre.includes(searchTerm.toLowerCase()) || 
                           displayText.includes(searchTerm.toLowerCase());
                });
                
                return filtered.slice(0, 10); // Limitar a 10 resultados
            };
            
            // Función para mostrar resultados
            const showResults = (results) => {
                productoDropdown.innerHTML = '';
                
                if (results.length === 0) {
                    productoDropdown.innerHTML = '<div class="producto-option text-muted">No se encontraron productos</div>';
                    productoDropdown.style.display = 'block';
                    return;
                }
                
                results.forEach((option, index) => {
                    const div = document.createElement('div');
                    div.className = 'producto-option';
                    div.setAttribute('data-value', option.value);
                    div.setAttribute('data-unidad', option.getAttribute('data-unidad'));
                    
                    const nombre = option.textContent.split(' (')[0];
                    const unidad = option.textContent.match(/\(([^)]+)\)/)?.[1] || '';
                    
                    div.innerHTML = `
                        <div class="producto-nombre">${nombre}</div>
                        <div class="producto-unidad">${unidad}</div>
                    `;
                    
                    // Evento click para seleccionar
                    div.addEventListener('click', () => {
                        selectProducto(option.value, nombre, unidad);
                    });
                    
                    // Evento hover para resaltar
                    div.addEventListener('mouseenter', () => {
                        productoDropdown.querySelectorAll('.producto-option').forEach(opt => opt.classList.remove('selected'));
                        div.classList.add('selected');
                    });
                    
                    productoDropdown.appendChild(div);
                });
                
                productoDropdown.style.display = 'block';
            };
            
            // Función para seleccionar producto
            const selectProducto = (productoId, nombre, unidad) => {
                productoSearch.value = `${nombre} (${unidad})`;
                productoDropdown.style.display = 'none';
                
                if (productoId) {
                    this.currentMovimientoFilters.productoId = productoId;
                    this.loadMovimientoData();
                } else {
                    // Ocultar resumen y gráficos si no hay producto seleccionado
                    document.getElementById('resumenProducto').style.display = 'none';
                    const container = document.getElementById('movimientosChartsContainer');
                    if (container) {
                        container.innerHTML = '';
                    }
                }
            };
            
            // Evento de búsqueda
            productoSearch.addEventListener('input', (e) => {
                const searchTerm = e.target.value.trim();
                
                if (searchTerm.length === 0) {
                    productoDropdown.style.display = 'none';
                    return;
                }
                
                const results = filterProductos(searchTerm);
                showResults(results);
            });
            
            // Evento de focus para mostrar resultados iniciales
            productoSearch.addEventListener('focus', (e) => {
                const searchTerm = e.target.value.trim();
                if (searchTerm.length > 0) {
                    const results = filterProductos(searchTerm);
                    showResults(results);
                } else {
                    // Si está vacío, mostrar sugerencias
                    this.loadProductosSugeridos();
                }
            });
            
            // Evento de teclado para navegación
            let selectedIndex = -1;
            productoSearch.addEventListener('keydown', (e) => {
                const options = productoDropdown.querySelectorAll('.producto-option');
                
                if (options.length === 0) return;
                
                switch (e.key) {
                    case 'ArrowDown':
                        e.preventDefault();
                        selectedIndex = Math.min(selectedIndex + 1, options.length - 1);
                        updateSelection(options, selectedIndex);
                        break;
                    case 'ArrowUp':
                        e.preventDefault();
                        selectedIndex = Math.max(selectedIndex - 1, -1);
                        updateSelection(options, selectedIndex);
                        break;
                    case 'Enter':
                        e.preventDefault();
                        if (selectedIndex >= 0 && options[selectedIndex]) {
                            const option = options[selectedIndex];
                            const productoId = option.getAttribute('data-value');
                            const nombre = option.querySelector('.producto-nombre').textContent;
                            const unidad = option.querySelector('.producto-unidad').textContent;
                            selectProducto(productoId, nombre, unidad);
                        }
                        break;
                    case 'Escape':
                        productoDropdown.style.display = 'none';
                        selectedIndex = -1;
                        break;
                }
            });
            
            // Función para actualizar selección visual
            const updateSelection = (options, index) => {
                options.forEach((opt, i) => {
                    opt.classList.toggle('selected', i === index);
                });
                
                if (index >= 0 && options[index]) {
                    options[index].scrollIntoView({ block: 'nearest' });
                }
            };
            
            // Cerrar dropdown al hacer click fuera
            document.addEventListener('click', (e) => {
                if (!productoSearch.contains(e.target) && !productoDropdown.contains(e.target)) {
                    productoDropdown.style.display = 'none';
                    selectedIndex = -1;
                }
            });
        }
    }

    applyMovimientoDateFilter(filterType) {
        const today = new Date();
        let startDate, endDate;

        switch (filterType) {
            case '7days':
                startDate = new Date(today);
                startDate.setDate(today.getDate() - 6);
                break;
            case '30days':
                startDate = new Date(today);
                startDate.setDate(today.getDate() - 29);
                break;
            case '90days':
                startDate = new Date(today);
                startDate.setDate(today.getDate() - 89);
                break;
            default:
                return;
        }

        endDate = new Date(today);
        this.currentMovimientoFilters.startDate = startDate;
        this.currentMovimientoFilters.endDate = endDate;
        
        // Actualizar campos de fecha personalizada
        const startDateInput = document.getElementById('movimientoStartDate');
        const endDateInput = document.getElementById('movimientoEndDate');
        if (startDateInput && endDateInput) {
            startDateInput.value = startDate.toISOString().split('T')[0];
            endDateInput.value = endDate.toISOString().split('T')[0];
        }
        
        if (this.currentMovimientoFilters.productoId) {
            this.loadMovimientoData();
        }
    }

    setupMovimientoChartContainers() {
        // Crear contenedor para el gráfico de movimientos
        const chartContainer = document.getElementById('movimientosChartsContainer');
        if (!chartContainer) return;

        // Contenedor para el gráfico de movimientos por día
        const movimientosChartDiv = document.createElement('div');
        movimientosChartDiv.className = 'col-12 mb-4';
        movimientosChartDiv.innerHTML = `
            <div class="card shadow-sm">
                <div class="card-header bg-white">
                    <h5 class="mb-0" id="movimientoChartTitle">📈 Movimientos por Día</h5>
                </div>
                <div class="card-body">
                    <canvas id="movimientosProductoChart" width="400" height="200"></canvas>
                </div>
            </div>
        `;
        chartContainer.appendChild(movimientosChartDiv);
    }

    async loadMovimientoData() {
        if (!this.currentMovimientoFilters.startDate || 
            !this.currentMovimientoFilters.endDate || 
            !this.currentMovimientoFilters.productoId) return;

        try {
            const response = await fetch('/pos/menu/productos-analytics/api/movimientos-producto/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    start_date: this.currentMovimientoFilters.startDate.toISOString().split('T')[0],
                    end_date: this.currentMovimientoFilters.endDate.toISOString().split('T')[0],
                    producto_id: this.currentMovimientoFilters.productoId
                })
            });

            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    this.renderMovimientosChart(data.data, data.resumen, data.periodo);
                    this.updateResumenProducto(data.resumen);
                } else {
                    console.error('Error en la respuesta:', data.error);
                }
            } else {
                console.error('Error cargando datos de movimientos');
            }
        } catch (error) {
            console.error('Error en la petición de movimientos:', error);
        }
    }

    renderMovimientosChart(data, resumen, periodo) {
        const ctx = document.getElementById('movimientosProductoChart');
        if (!ctx) return;

        // Destruir gráfico existente si existe
        if (this.charts.movimientosProducto) {
            this.charts.movimientosProducto.destroy();
        }

        // Preparar datos para el gráfico
        const labels = data.map(item => item.fecha);
        const datasets = [
            {
                label: `Cantidad Vendida (${resumen.producto_unidad})`,
                data: data.map(item => item.cantidad),
                backgroundColor: 'rgba(0, 30, 98, 0.8)',
                borderColor: 'rgba(0, 30, 98, 1)',
                borderWidth: 2,
                borderRadius: 4,
                borderSkipped: false
            }
        ];

        // Actualizar título del gráfico
        const chartTitle = document.getElementById('movimientoChartTitle');
        if (chartTitle) {
            chartTitle.textContent = `📈 Movimientos de ${resumen.producto_nombre} - ${resumen.producto_unidad}`;
        }

        // Configuración del gráfico
        const chartConfig = getChartConfig();
        const config = {
            type: 'bar',
            data: {
                labels: labels,
                datasets: datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: true,
                        position: 'top',
                        labels: {
                            font: {
                                size: chartConfig.fontSize.legend
                            }
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const dataIndex = context.dataIndex;
                                const item = data[dataIndex];
                                let label = context.dataset.label + ': ';
                                label += item.cantidad_formatted + ' ' + resumen.producto_unidad;
                                label += ' (' + item.pedidos_formatted + ' pedidos)';
                                return label;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        ticks: {
                            maxRotation: chartConfig.maxRotation,
                            minRotation: 0,
                            font: {
                                size: chartConfig.fontSize.ticks
                            }
                        }
                    },
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        title: {
                            display: true,
                            text: `Cantidad (${resumen.producto_unidad})`,
                            font: {
                                size: chartConfig.fontSize.title
                            }
                        },
                        ticks: {
                            callback: function(value) {
                                return formatNumber(value, 2);
                            },
                            font: {
                                size: chartConfig.fontSize.ticks
                            }
                        }
                    }
                }
            }
        };

        // Crear el gráfico
        this.charts.movimientosProducto = new Chart(ctx, config);

        // Mostrar información del período
        this.showMovimientoPeriodoInfo(periodo);
    }

    updateResumenProducto(resumen) {
        // Mostrar el resumen
        document.getElementById('resumenProducto').style.display = 'block';
        
        // Actualizar valores
        document.getElementById('totalVendido').textContent = resumen.total_cantidad_formatted;
        document.getElementById('vecesVendido').textContent = resumen.total_pedidos_formatted;
        document.getElementById('promedioVenta').textContent = resumen.promedio_por_pedido_formatted;
        document.getElementById('unidadProducto').textContent = resumen.producto_unidad;
    }

    showMovimientoPeriodoInfo(periodo) {
        // Crear o actualizar información del período
        let periodoInfo = document.getElementById('movimientoPeriodoInfo');
        if (!periodoInfo) {
            periodoInfo = document.createElement('div');
            periodoInfo.id = 'movimientoPeriodoInfo';
            periodoInfo.className = 'alert alert-info mt-3';
            document.getElementById('movimientosChartsContainer').appendChild(periodoInfo);
        }
        
        periodoInfo.innerHTML = `
            <strong>📅 Período de Análisis:</strong> ${periodo.inicio} - ${periodo.fin}
        `;
    }

    getCSRFToken() {
        const token = document.querySelector('[name=csrfmiddlewaretoken]');
        return token ? token.value : '';
    }

    async loadProductosSugeridos() {
        const productoDropdown = document.getElementById('productoDropdown');
        const productoSearch = document.getElementById('productoSearch');
        
        if (!productoDropdown || !productoSearch) return;
        
        try {
            const response = await fetch('/pos/menu/productos-analytics/api/productos-sugeridos/', {
                method: 'GET',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': this.getCSRFToken()
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                
                if (data.success && data.data.length > 0) {
                    // Mostrar sugerencias
                    productoDropdown.innerHTML = '';
                    
                    // Añadir título de sugerencias
                    const tituloDiv = document.createElement('div');
                    tituloDiv.className = 'producto-option producto-sugerencia-titulo';
                    tituloDiv.innerHTML = '<strong>🔥 Productos más vendidos:</strong>';
                    productoDropdown.appendChild(tituloDiv);
                    
                    // Añadir productos sugeridos
                    data.data.forEach((producto) => {
                        const div = document.createElement('div');
                        div.className = 'producto-option producto-sugerencia';
                        div.setAttribute('data-value', producto.id);
                        div.setAttribute('data-unidad', producto.unidad);
                        
                        div.innerHTML = `
                            <div class="producto-nombre">${producto.nombre}</div>
                            <div class="producto-unidad">${producto.unidad} - ${producto.cantidad_total} vendidos</div>
                        `;
                        
                        // Evento click para seleccionar
                        div.addEventListener('click', () => {
                            this.selectProductoSugerido(producto.id, producto.nombre, producto.unidad);
                        });
                        
                        // Evento hover para resaltar
                        div.addEventListener('mouseenter', () => {
                            productoDropdown.querySelectorAll('.producto-option').forEach(opt => opt.classList.remove('selected'));
                            div.classList.add('selected');
                        });
                        
                        productoDropdown.appendChild(div);
                    });
                    
                    productoDropdown.style.display = 'block';
                } else {
                    // Si no hay sugerencias, mostrar mensaje
                    productoDropdown.innerHTML = '<div class="producto-option text-muted">No hay productos sugeridos disponibles</div>';
                    productoDropdown.style.display = 'block';
                }
            } else {
                console.error('Error al cargar productos sugeridos:', response.statusText);
            }
        } catch (error) {
            console.error('Error al cargar productos sugeridos:', error);
        }
    }

    selectProductoSugerido(productoId, nombre, unidad) {
        const productoSearch = document.getElementById('productoSearch');
        const productoDropdown = document.getElementById('productoDropdown');
        
        if (productoSearch && productoDropdown) {
            productoSearch.value = `${nombre} (${unidad})`;
            productoDropdown.style.display = 'none';
            
            if (productoId) {
                this.currentMovimientoFilters.productoId = productoId;
                this.loadMovimientoData();
            }
        }
    }
}

// Inicializar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', function() {
    window.productosAnalytics = new ProductosAnalytics();
}); 