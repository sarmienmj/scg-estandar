#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Comando de Django para poblar la base de datos con productos y categorías
Basándose en las imágenes disponibles en la carpeta ImagenesProductos
"""

from django.core.management.base import BaseCommand
from pos.models import CategoriasProductos, Producto, Cliente, Pedido, ProductosPedido
from django.utils import timezone
from datetime import timedelta
import random


class Command(BaseCommand):
    help = 'Poblar la base de datos con categorías, productos, clientes y pedidos de ejemplo'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limpiar',
            action='store_true',
            help='Limpiar datos existentes antes de poblar',
        )
        parser.add_argument(
            '--clientes',
            action='store_true',
            help='Poblar también clientes (20 clientes)',
        )
        parser.add_argument(
            '--pedidos',
            action='store_true',
            help='Crear pedidos de ejemplo (30 pedidos con productos)',
        )

    def handle(self, *args, **options):
        if options['limpiar']:
            self.stdout.write(self.style.WARNING('🗑️  Limpiando datos existentes...'))
            if options['pedidos']:
                ProductosPedido.objects.all().delete()
                Pedido.objects.all().delete()
                self.stdout.write(self.style.SUCCESS('✅ Pedidos eliminados'))
            Producto.objects.all().delete()
            CategoriasProductos.objects.all().delete()
            if options['clientes']:
                Cliente.objects.all().delete()
                self.stdout.write(self.style.SUCCESS('✅ Clientes eliminados'))
            self.stdout.write(self.style.SUCCESS('✅ Productos y categorías eliminados'))

        self.stdout.write(self.style.SUCCESS('🚀 Iniciando población de base de datos...'))
        
        # Crear categorías
        self.crear_categorias()
        
        # Crear productos
        self.crear_productos()
        
        # Crear clientes si se solicita
        if options['clientes']:
            self.crear_clientes()
        
        # Crear pedidos si se solicita
        if options['pedidos']:
            self.crear_pedidos()
        
        self.stdout.write(
            self.style.SUCCESS('🎉 ¡Base de datos poblada exitosamente!')
        )

    def crear_categorias(self):
        """Crear las categorías de productos"""
        self.stdout.write('📁 Creando categorías...')
        
        categorias = [
            {
                'nombre': 'Combo1',
                'imagen': '/static/categorias/combo1.png',
                'orden': 1
            },
            {
                'nombre': 'Combo2',
                'imagen': '/static/categorias/combo2.png',
                'orden': 2
            },
            {
                'nombre': 'Combo3',
                'imagen': '/static/categorias/combo3.png',
                'orden': 3
            },
            {
                'nombre': 'Combo4',
                'imagen': '/static/categorias/combo4.png',
                'orden': 4
            },
            {
                'nombre': 'Dulces',
                'imagen': '/static/categorias/dulces.png',
                'orden': 5
            },
            {
                'nombre': 'Detergentes',
                'imagen': '/static/categorias/detergentes.png',
                'orden': 6
            },
            {
                'nombre': 'Nevera',
                'imagen': '/static/categorias/nevera.png',
                'orden': 9
            },
            {
                'nombre': 'Panes',
                'imagen': '/static/categorias/panes.png',
                'orden': 10
            }     
            
            
        ]
        
        for cat_data in categorias:
            categoria, created = CategoriasProductos.objects.get_or_create(
                nombre=cat_data['nombre'],
                defaults={
                    'imagen': cat_data['imagen'],
                    'orden': cat_data['orden']
                }
            )
            
            if created:
                self.stdout.write(f'  ✅ Categoría creada: {categoria.nombre}')
            else:
                self.stdout.write(f'  ⚠️  Categoría ya existía: {categoria.nombre}')

    def crear_productos(self):
        """Crear productos basándose en las imágenes disponibles"""
        self.stdout.write('🥬 Creando productos...')
        
        # Obtener categorías
        cat_combo1 = CategoriasProductos.objects.get(nombre='Combo1')
        cat_combo2 = CategoriasProductos.objects.get(nombre='Combo2')
        cat_combo3 = CategoriasProductos.objects.get(nombre='Combo3')
        cat_combo4 = CategoriasProductos.objects.get(nombre='Combo4')
        cat_dulces = CategoriasProductos.objects.get(nombre='Dulces')
        cat_detergentes = CategoriasProductos.objects.get(nombre='Detergentes')
        cat_nevera = CategoriasProductos.objects.get(nombre='Nevera')
        cat_panes = CategoriasProductos.objects.get(nombre='Panes')
        
        # Definir productos basándose en las imágenes
        productos = [
            # FRUTAS - COMBO1
            {
                'nombre': 'Aguacate',
                'imagen': 'Aguacate',
                'categoria': cat_combo1,
                'unidad': 'U',
                'moneda': 'USD',
                'precio_detal': 2.50,
                'precio_mayor': 2.00,
                'costo': 1.50,
                'cantidad': 100
            },
            {
                'nombre': 'Parchita',
                'imagen': 'Parchita',
                'categoria': cat_combo1,
                'unidad': 'K',
                'moneda': 'USD',
                'precio_detal': 3.00,
                'precio_mayor': 2.50,
                'costo': 2.00,
                'cantidad': 50
            },
            {
                'nombre': 'Patilla',
                'imagen': 'Patilla',
                'categoria': cat_combo1,
                'unidad': 'K',
                'moneda': 'BS',
                'precio_detal': 120.00,
                'precio_mayor': 100.00,
                'costo': 80.00,
                'cantidad': 30
            },
            {
                'nombre': 'Piña',
                'imagen': 'Piña',
                'categoria': cat_combo1,
                'unidad': 'U',
                'moneda': 'USD',
                'precio_detal': 4.00,
                'precio_mayor': 3.50,
                'costo': 2.50,
                'cantidad': 25
            },
            {
                'nombre': 'Plátano',
                'imagen': 'Platano',
                'categoria': cat_combo1,
                'unidad': 'K',
                'moneda': 'BS',
                'precio_detal': 163.00,
                'precio_mayor': 140.00,
                'costo': 100.00,
                'cantidad': 80
            },
            {
                'nombre': 'Tamarindo',
                'imagen': 'Tamarindo',
                'categoria': cat_combo1,
                'unidad': 'K',
                'moneda': 'USD',
                'precio_detal': 5.00,
                'precio_mayor': 4.50,
                'costo': 3.50,
                'cantidad': 20
            },
            {
                'nombre': 'Tomate de Árbol',
                'imagen': 'Tomate de Arbol',
                'categoria': cat_combo1,
                'unidad': 'K',
                'moneda': 'USD',
                'precio_detal': 4.50,
                'precio_mayor': 4.00,
                'costo': 3.00,
                'cantidad': 30
            },
            {
                'nombre': 'Topocho',
                'imagen': 'Topocho',
                'categoria': cat_combo1,
                'unidad': 'K',
                'moneda': 'BS',
                'precio_detal': 145.00,
                'precio_mayor': 120.00,
                'costo': 90.00,
                'cantidad': 60
            },
            
            # VERDURAS Y HORTALIZAS - COMBO2
            {
                'nombre': 'Acelga',
                'imagen': 'Acelga',
                'categoria': cat_combo2,
                'unidad': 'K',
                'moneda': 'USD',
                'precio_detal': 3.50,
                'precio_mayor': 3.00,
                'costo': 2.00,
                'cantidad': 15
            },
            {
                'nombre': 'Ají Dulce',
                'imagen': 'Aji Dulce',
                'categoria': cat_combo2,
                'unidad': 'K',
                'moneda': 'USD',
                'precio_detal': 8.00,
                'precio_mayor': 7.00,
                'costo': 5.00,
                'cantidad': 10
            },
            {
                'nombre': 'Apio',
                'imagen': 'Apio',
                'categoria': cat_combo2,
                'unidad': 'K',
                'moneda': 'USD',
                'precio_detal': 4.00,
                'precio_mayor': 3.50,
                'costo': 2.50,
                'cantidad': 20
            },
            {
                'nombre': 'Auyama',
                'imagen': 'Auyama',
                'categoria': cat_combo2,
                'unidad': 'K',
                'moneda': 'BS',
                'precio_detal': 144.00,
                'precio_mayor': 120.00,
                'costo': 80.00,
                'cantidad': 40
            },
            {
                'nombre': 'Berenjena',
                'imagen': 'Berenjena',
                'categoria': cat_combo2,
                'unidad': 'K',
                'moneda': 'USD',
                'precio_detal': 3.00,
                'precio_mayor': 2.50,
                'costo': 1.80,
                'cantidad': 25
            },
            {
                'nombre': 'Pepino',
                'imagen': 'Pepino',
                'categoria': cat_combo2,
                'unidad': 'K',
                'moneda': 'BS',
                'precio_detal': 200.00,
                'precio_mayor': 160.00,
                'costo': 120.00,    
                'cantidad': 35
            },
            {
                'nombre': 'Pimentón',
                'imagen': 'Pimenton',
                'categoria': cat_combo2,
                'unidad': 'K',
                'moneda': 'USD',
                'precio_detal': 5.00,
                'precio_mayor': 4.50,
                'costo': 3.50,
                'cantidad': 20
            },
            {
                'nombre': 'Rábano',
                'imagen': 'Rabano',
                'categoria': cat_combo2,
                'unidad': 'K',
                'moneda': 'BS',
                'precio_detal': 280.00,
                'precio_mayor': 240.00,
                'costo': 160.00,
                'cantidad': 15
            },
            {
                'nombre': 'Remolacha',
                'imagen': 'Remolacha',
                'categoria': cat_combo2,
                'unidad': 'K',
                'moneda': 'BS',
                'precio_detal': 224.00,
                'precio_mayor': 184.00,
                'costo': 144.00,
                'cantidad': 30
            },
            {
                'nombre': 'Repollo Blanco',
                'imagen': 'Repollo Blanco',
                'categoria': cat_combo2,
                'unidad': 'K',
                'moneda': 'BS',
                'precio_detal': 200.00,
                'precio_mayor': 160.00,
                'costo': 120.00,
                'cantidad': 40
            },
            {
                'nombre': 'Repollo Morado',
                'imagen': 'Repollo Morado',
                'categoria': cat_combo2,
                'unidad': 'K',
                'moneda': 'USD',
                'precio_detal': 3.00,
                'precio_mayor': 2.50,
                'costo': 2.00,
                'cantidad': 25
            },
            {
                'nombre': 'Tomate',
                'imagen': 'Tomate',
                'categoria': cat_combo2,
                'unidad': 'K',
                'moneda': 'USD',
                'precio_detal': 4.00,
                'precio_mayor': 3.50,
                'costo': 2.50,
                'cantidad': 50
            },
            {
                'nombre': 'Zanahoria',
                'imagen': 'Zanahoria',
                'categoria': cat_combo2,
                'unidad': 'K',
                'moneda': 'BS',
                'precio_detal': 224.00,
                'precio_mayor': 184.00,
                'costo': 144.00,
                'cantidad': 45
            },
            
            # TUBÉRCULOS - COMBO3
            {
                'nombre': 'Batata',
                'imagen': 'Batata',
                'categoria': cat_combo3,
                'unidad': 'K',
                'moneda': 'BS',
                'precio_detal': 176.00,
                'precio_mayor': 144.00,
                'costo': 104.00,
                'cantidad': 60
            },
            {
                'nombre': 'Ocumo Blanco',
                'imagen': 'Ocumo Blanco',
                'categoria': cat_combo3,
                'unidad': 'K',
                'moneda': 'USD',
                'precio_detal': 3.50,
                'precio_mayor': 3.00,
                'costo': 2.50,
                'cantidad': 35
            },
            {
                'nombre': 'Ocumo Chino',
                'imagen': 'Ocumo Chino',
                'categoria': cat_combo3,
                'unidad': 'K',
                'moneda': 'USD',
                'precio_detal': 4.00,
                'precio_mayor': 3.50,
                'costo': 3.00,
                'cantidad': 25
            },
            {
                'nombre': 'Papa',
                'imagen': 'Papa',
                'categoria': cat_combo3,
                'unidad': 'K',
                'moneda': 'BS',
                'precio_detal': 200.00,
                'precio_mayor': 160.00,
                'costo': 120.00,
                'cantidad': 100
            },
            {
                'nombre': 'Papa Colombiana',
                'imagen': 'Papa Colombiana',
                'categoria': cat_combo3,
                'unidad': 'K',
                'moneda': 'USD',
                'precio_detal': 3.00,
                'precio_mayor': 2.50,
                'costo': 2.00,
                'cantidad': 60
            },
            {
                'nombre': 'Yuca',
                'imagen': 'Yuca',
                'categoria': cat_combo3,
                'unidad': 'K',
                'moneda': 'BS',
                'precio_detal': 160.00,
                'precio_mayor': 144.00,
                'costo': 96.00,
                'cantidad': 80
            },
            {
                'nombre': 'Ñame',
                'imagen': 'Ñame',
                'categoria': cat_combo3,
                'unidad': 'K',
                'moneda': 'BS',
                'precio_detal': 304.00,
                'precio_mayor': 264.00,
                'costo': 224.00,
                'cantidad': 40
            },
            
            # HIERBAS Y CONDIMENTOS - COMBO4
            {
                'nombre': 'Ajo',
                'imagen': 'Ajo',
                'categoria': cat_combo4,
                'unidad': 'K',
                'moneda': 'USD',
                'precio_detal': 9.00,
                'precio_mayor': 8.00,
                'costo': 6.50,
                'cantidad': 5
            },
            {
                'nombre': 'Ajo Pelado',
                'imagen': 'Ajo Pelado',
                'categoria': cat_combo4,
                'unidad': 'K',
                'moneda': 'BS',
                'precio_detal': 560.00,
                'precio_mayor': 480.00,
                'costo': 400.00,
                'cantidad': 3
            },
            {
                'nombre': 'Ajoporro',
                'imagen': 'Ajo Porro',
                'categoria': cat_combo4,
                'unidad': 'K',
                'moneda': 'USD',
                'precio_detal': 6.00,
                'precio_mayor': 5.00,
                'costo': 4.00,
                'cantidad': 10
            },
            {
                'nombre': 'Albahaca',
                'imagen': 'Albahaca',
                'categoria': cat_combo4,
                'unidad': 'K',
                'moneda': 'USD',
                'precio_detal': 8.00,
                'precio_mayor': 7.00,
                'costo': 5.00,
                'cantidad': 5
            },
            
            # PANES - CATEGORÍA PANES
            {
                'nombre': 'Pan Andino',
                'imagen': 'Pan Andino',
                'categoria': cat_panes,
                'unidad': 'U',
                'moneda': 'USD',
                'precio_detal': 1.50,
                'precio_mayor': 1.00,
                'costo': 0.50,
                'cantidad': 100
            },
            {
                'nombre': 'Pan arabito',
                'imagen': 'Pan arabito',
                'categoria': cat_panes,
                'unidad': 'U',
                'moneda': 'USD',
                'precio_detal': 1.50,
                'precio_mayor': 1.00,
                'costo': 0.50,
                'cantidad': 100
            },
            {
                'nombre': 'Andino',
                'imagen': 'Andino',
                'categoria': cat_panes,
                'unidad': 'U',
                'moneda': 'USD',
                'precio_detal': 1.00,
                'precio_mayor': 0.50,
                'costo': 0.25,
                'cantidad': 100
            },
            {
                'nombre': 'Pan Sandwich',
                'imagen': 'Pan Sandwich',
                'categoria': cat_panes,
                'unidad': 'U',
                'moneda': 'BS',
                'precio_detal': 120.00,
                'precio_mayor': 104.00,
                'costo': 80.00,
                'cantidad': 50
            },
            
            # DULCES - CATEGORÍA DULCES
            {
                'nombre': 'Alfajores',
                'imagen': 'Alfajores',
                'categoria': cat_dulces,
                'unidad': 'U',
                'moneda': 'USD',
                'precio_detal': 1.00,
                'precio_mayor': 0.50,
                'costo': 0.25,
                'cantidad': 100
            },
            {
                'nombre': 'Ariel 4 kg',
                'imagen': 'Ariel 4 kg',
                'categoria': cat_detergentes,
                'unidad': 'U',
                'moneda': 'USD',
                'precio_detal': 1.00,
                'precio_mayor': 0.50,
                'costo': 0.25,
                'cantidad': 100
            },
            {
                'nombre': 'Brillaking',
                'imagen': 'Brillaking',
                'categoria': cat_detergentes,
                'unidad': 'U',
                'moneda': 'USD',
                'precio_detal': 1.00,
                'precio_mayor': 0.50,
                'costo': 0.25,
                'cantidad': 100
            },
            {
                'nombre': 'Postobon 2.5 Lts',
                'imagen': 'Postobon 2.5 Lts',
                'categoria': cat_nevera,
                'unidad': 'U',
                'moneda': 'USD',
                'precio_detal': 1.00,
                'precio_mayor': 0.50,
                'costo': 0.25,
                'cantidad': 100
            },
            {
                'nombre': 'Jugo pulp 250  ml',
                'imagen': 'Jugo pulp 250  ml',
                'categoria': cat_nevera,
                'unidad': 'U',
                'moneda': 'USD',
                'precio_detal': 1.00,
                'precio_mayor': 0.50,
                'costo': 0.25,
                'cantidad': 100
            },
            {
                'nombre': 'Pepsi 2,5 Lts',
                'imagen': 'Pepsi 2,5 Lts',
                'categoria': cat_nevera,
                'unidad': 'U',
                'moneda': 'USD',
                'precio_detal': 1.00,
                'precio_mayor': 0.50,
                'costo': 0.25,
                'cantidad': 100
            },
            {
                'nombre': 'Ariel 1kg',
                'imagen': 'Ariel 1kg',
                'categoria': cat_detergentes,
                'unidad': 'U',
                'moneda': 'USD',
                'precio_detal': 1.00,
                'precio_mayor': 0.50,
                'costo': 0.25,
                'cantidad': 100
            },
            {
                'nombre': 'Ariel 2kg',
                'imagen': 'Ariel 2kg',
                'categoria': cat_detergentes,
                'unidad': 'U',
                'moneda': 'USD',
                'precio_detal': 1.00,
                'precio_mayor': 0.50,
                'costo': 0.25,
                'cantidad': 100
            },
            {
                'nombre': 'Barra de Guayaba',
                'imagen': 'Barra de Guayaba',
                'categoria': cat_dulces,
                'unidad': 'U',
                'moneda': 'USD',
                'precio_detal': 1.00,
                'precio_mayor': 0.50,
                'costo': 0.25,
                'cantidad': 100
            },
            
            # NEVERA - CATEGORÍA NEVERA
            {
                'nombre': 'Speed',
                'imagen': 'Speed',
                'categoria': cat_nevera,
                'unidad': 'U',
                'moneda': 'USD',
                'precio_detal': 1.00,
                'precio_mayor': 0.50,
                'costo': 0.25,
                'cantidad': 100
            }
        ]
        
        productos_creados = 0
        for prod_data in productos:
            # Generar código de barras aleatorio (opcional)
            barcode = f"78901234{random.randint(10000, 99999)}"
            
            producto, created = Producto.objects.get_or_create(
                nombre=prod_data['nombre'],
                defaults={
                    'cantidad': prod_data['cantidad'],
                    'unidad': prod_data['unidad'],
                    'moneda': prod_data['moneda'],
                    'imagen': prod_data['imagen'],
                    'barcode': barcode,
                    'costo': prod_data['costo'],
                    'precio_detal': prod_data['precio_detal'],
                    'precio_mayor': prod_data['precio_mayor'],
                    'precio_especial': prod_data.get('precio_especial', prod_data['precio_mayor'] * 0.9),
                    'subproducto': '',
                    'relacion_subproducto': 0
                }
            )
            
            if created:
                # Agregar categoría
                producto.categoria.add(prod_data['categoria'])
                producto.save()
                productos_creados += 1
                self.stdout.write(f'  ✅ Producto creado: {producto.nombre} - ${producto.precio_detal:.2f}')
            else:
                self.stdout.write(f'  ⚠️  Producto ya existía: {producto.nombre}')
        
        self.stdout.write(
            self.style.SUCCESS(f'🎯 {productos_creados} productos creados exitosamente')
        )

    def crear_clientes(self):
        """Crear 20 clientes con datos realistas venezolanos"""
        self.stdout.write('👥 Creando clientes...')
        
        # Datos realistas venezolanos
        nombres = [
            'José Luis García', 'María Elena Rodríguez', 'Carlos Alberto Pérez',
            'Ana Victoria Martínez', 'Luis Eduardo Hernández', 'Carmen Rosa López',
            'Miguel Angel González', 'Rosa María Fernández', 'Pedro Antonio Silva',
            'Luz Mireya Ramírez', 'Rafael Enrique Torres', 'Gloria Isabel Morales',
            'Juan Carlos Díaz', 'Yolanda Beatriz Ruiz', 'Fernando José Mendoza',
            'Teresa del Carmen Jiménez', 'Roberto Carlos Vargas', 'Marlene Esperanza Castro',
            'Alfredo Jesús Rojas', 'Nellys Coromoto Gutiérrez'
        ]
        
        zonas_caracas = [
            'Los Teques', 'Maracay', 'Valencia', 'Barquisimeto', 'Maracaibo',
            'Petare', 'Catia', 'San Martín', 'Chacao', 'Baruta',
            'El Hatillo', 'Sucre', 'Libertador', 'Antimano', 'El Valle',
            'La Vega', 'Las Mercedes', 'Los Palos Grandes', 'Altamira', 'Sabana Grande'
        ]
        
        prefijos_telefono = ['0212', '0414', '0424', '0416', '0426']
        
        clientes_creados = 0
        for i, nombre in enumerate(nombres):
            # Generar cédula realista (8 cifras)
            cedula = f"V-{random.randint(10000000, 29999999)}"
            
            # Generar teléfono venezolano
            prefijo = random.choice(prefijos_telefono)
            if prefijo == '0212':  # Teléfono fijo
                numero = f"{prefijo}-{random.randint(100, 999)}-{random.randint(1000, 9999)}"
            else:  # Celular
                numero = f"{prefijo}-{random.randint(100, 999)}-{random.randint(1000, 9999)}"
            
            # Asignar zona
            zona = zonas_caracas[i]
            
            # Configurar créditos variados
            tiene_credito = random.choice([True, False, False])  # 33% tienen crédito
            if tiene_credito:
                credito_actual = random.randint(50, 500)
                credito_max = random.randint(credito_actual + 100, 1000)
                plazo = random.choice([7, 15, 30, 45])  # días
            else:
                credito_actual = 0
                credito_max = random.randint(200, 800)  # límite disponible
                plazo = 0
            
            cliente, created = Cliente.objects.get_or_create(
                cedula=cedula,
                defaults={
                    'nombre': nombre,
                    'telefono': numero,
                    'zona_vive': zona,
                    'credito': credito_max,
                    'credito_maximo': credito_max,
                    'credito_plazo': plazo
                }
            )
            
            if created:
                clientes_creados += 1
                status_credito = f"${credito_actual}" if credito_actual > 0 else "Sin deuda"
                self.stdout.write(f'  ✅ Cliente creado: {nombre} - {zona} - Crédito: {status_credito}')
            else:
                self.stdout.write(f'  ⚠️  Cliente ya existía: {nombre}')
        
        self.stdout.write(
            self.style.SUCCESS(f'👥 {clientes_creados} clientes creados exitosamente')
        )

    def crear_pedidos(self):
        """Crear 500 pedidos de ejemplo con productos asociados"""
        self.stdout.write('🛒 Creando pedidos de ejemplo...')
        
        # Verificar que existan productos y clientes
        productos = list(Producto.objects.all())
        clientes = list(Cliente.objects.all())
        
        if not productos:
            self.stdout.write(self.style.ERROR('❌ No hay productos disponibles. Ejecuta primero sin --pedidos para crear productos.'))
            return
        
        if not clientes:
            self.stdout.write(self.style.WARNING('⚠️  No hay clientes disponibles. Los pedidos se crearán sin cliente asignado.'))
            clientes = [None]  # Pedidos sin cliente (cliente=0)
        
        # Estados posibles para los pedidos (solo pagados)
        estados_pedidos = [
            'Pagado', 'Pagado', 'Pagado', 'Pagado', 'Pagado',  'Pagado'
        ]
        
        # Usuarios ejemplo
        usuarios = ['admin', 'cajero1', 'cajero2', 'vendedor1', 'cajero3', 'vendedor2']
        pesadores = ['pesador1', 'pesador2', 'pesador3', None, None, None]  # Algunos sin pesador
        
        # Definir rango de fechas: desde 10/07/2025 hacia atrás 10 días
        from datetime import datetime
        fecha_actual = datetime(2025, 7, 23)  # 10/07/2025
        fecha_limite = fecha_actual - timedelta(days=30)  # 10 días atrás
        
        # Convertir a timezone aware
        fecha_actual_tz = timezone.make_aware(fecha_actual)
        fecha_limite_tz = timezone.make_aware(fecha_limite)
        
        pedidos_creados = 0
        total_productos_pedidos = 0
        
        self.stdout.write(f'📅 Creando pedidos entre {fecha_limite.strftime("%d/%m/%Y")} y {fecha_actual.strftime("%d/%m/%Y")}')
        
        for i in range(1200):
            # Seleccionar cliente aleatorio (o None si no hay clientes)
            cliente = random.choice(clientes) if clientes[0] is not None else None
            cliente_id = cliente.id if cliente else 0
            
            # Seleccionar estado aleatorio
            estado = random.choice(estados_pedidos)
            
            # Crear fecha aleatoria entre fecha_limite y fecha_actual
            diferencia_dias = (fecha_actual_tz - fecha_limite_tz).days
            dias_aleatorios = random.randint(0, diferencia_dias)
            horas_aleatorias = random.randint(8, 20)  # Horario comercial
            minutos_aleatorios = random.randint(0, 59)
            
            fecha_pedido = fecha_limite_tz + timedelta(
                days=dias_aleatorios, 
                hours=horas_aleatorias, 
                minutes=minutos_aleatorios
            )
            
            # Seleccionar usuario y pesador
            usuario = random.choice(usuarios)
            pesador = random.choice(pesadores)
            
            # Crear el pedido (sin precio_total aún)
            pedido = Pedido.objects.create(
                status=estado,
                precio_total=0.0,  # Se calculará después
                cliente=cliente_id,
                usuario=usuario,
                pesador=pesador,
                notas=f"Pedido de ejemplo #{i+1} - Creado automáticamente"
            )
            
            # Actualizar la fecha manualmente (ya que auto_now_add=True ignora el valor pasado)
            pedido.fecha = fecha_pedido
            pedido.save(update_fields=['fecha'])
            
            # Seleccionar 2-8 productos aleatorios para el pedido
            num_productos = random.randint(2, 8)
            productos_seleccionados = random.sample(productos, min(num_productos, len(productos)))
            
            productos_pedido_lista = []
            precio_total_pedido = 0.0
            
            for producto in productos_seleccionados:
                # Determinar cantidad según la unidad
                if producto.unidad == 'U':
                    cantidad = random.randint(1, 5)  # 1-5 unidades
                else:  # Kg
                    cantidad = round(random.uniform(0.2, 8.0), 2)  # 0.5-3.0 kg
                
                # Usar precio de detalle (precio_detal)
                precio_unitario = producto.precio_detal
                precio_total_producto = precio_unitario * cantidad
                
                # Crear ProductosPedido
                producto_pedido = ProductosPedido.objects.create(
                    producto=producto.id,
                    producto_nombre=producto.nombre,
                    cantidad=cantidad,
                    precio=precio_unitario,
                    unidad=producto.unidad,
                    moneda=producto.moneda
                )
                
                productos_pedido_lista.append(producto_pedido)
                
                # Calcular precio total en USD para el pedido
                if producto.moneda == 'USD':
                    precio_total_pedido += precio_total_producto
                else:  # BS - convertir a USD (tasa aproximada)
                    tasa_cambio = 120  # Tasa de ejemplo
                    precio_total_pedido += precio_total_producto / tasa_cambio
                
                total_productos_pedidos += 1
            
            # Asignar productos al pedido
            pedido.productos.set(productos_pedido_lista)
            
            # Actualizar precio total del pedido
            pedido.precio_total = round(precio_total_pedido, 2)
            
            # Todos los pedidos están pagados, agregar fecha de pago
            fecha_pago = fecha_pedido + timedelta(minutes=random.randint(5, 60))
            pedido.pagado_fecha = fecha_pago
            
            # Guardar todos los cambios de una vez
            pedido.save()
            pedidos_creados += 1
            
            # Mostrar información del pedido creado
            cliente_info = cliente.nombre if cliente else "Sin cliente"
            self.stdout.write(
                f'  ✅ Pedido #{pedido.id}: {cliente_info} - {len(productos_pedido_lista)} productos - ${pedido.precio_total:.2f} - {estado}'
            )
        
        self.stdout.write(
            self.style.SUCCESS(f'🛒 {pedidos_creados} pedidos creados con {total_productos_pedidos} productos en total')
        )
        self.stdout.write(
            self.style.SUCCESS(f'📊 Distribución temporal: {fecha_limite.strftime("%d/%m/%Y")} - {fecha_actual.strftime("%d/%m/%Y")} (10 días)')
        ) 