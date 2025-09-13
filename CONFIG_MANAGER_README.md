# Gestor de Configuración - Sistema POS SCG

Este sistema proporciona dos métodos para gestionar la configuración de impresoras y balanzas en el archivo `config.txt`:

1. **Comando Django** (`config_manager.py`) - Integrado con el framework Django
2. **Script independiente** (`config_cli.py`) - Funciona sin necesidad de Django

## 📁 Estructura del archivo config.txt

```json
{
   "HOST":"192.168.1.8",
   "PORT":"8000",
   "IMPRESORAS":{
      "1":"192.168.1.101",
      "2":"192.168.1.112",
      "3":"192.168.1.45",
      "4":"192.168.1.104",
      "Etiqueta":"192.168.1.125"
   },
   "BALANZAS":{
      "ICM1":"192.168.1.103",
      "ICM2":"192.168.1.4"
   }
}
```

## 🔧 Método 1: Comando Django

### Ubicación
`core/pos/management/commands/config_manager.py`

### Uso
```bash
# Desde el directorio del proyecto Django (donde está manage.py)
cd core

# Listar toda la configuración
python manage.py config_manager list

# Listar solo impresoras
python manage.py config_manager list impresora

# Listar solo balanzas
python manage.py config_manager list balanza

# Agregar una impresora
python manage.py config_manager add impresora --nombre "Caja5" --ip "192.168.1.200"

# Agregar una balanza
python manage.py config_manager add balanza --nombre "ICM3" --ip "192.168.1.50"

# Actualizar IP de un dispositivo
python manage.py config_manager update impresora --nombre "Caja5" --ip "192.168.1.201"

# Eliminar un dispositivo
python manage.py config_manager remove balanza --nombre "ICM3"
```

### Características
- ✅ Integrado con Django
- ✅ Usa la configuración de Django para localizar archivos
- ✅ Manejo de errores con mensajes coloridos
- ✅ Validaciones completas

## 🚀 Método 2: Script Independiente

### Ubicación
`config_cli.py` (en la raíz del proyecto)

### Uso
```bash
# Desde la raíz del proyecto (donde está config_cli.py)

# Listar toda la configuración
python config_cli.py list

# Listar solo impresoras
python config_cli.py list impresora

# Listar solo balanzas
python config_cli.py list balanza

# Agregar una impresora
python config_cli.py add impresora --nombre "Caja5" --ip "192.168.1.200"

# Agregar una balanza
python config_cli.py add balanza --nombre "ICM3" --ip "192.168.1.50"

# Actualizar IP de un dispositivo
python config_cli.py update impresora --nombre "Caja5" --ip "192.168.1.201"

# Eliminar un dispositivo
python config_cli.py remove balanza --nombre "ICM3"
```

### Características
- ✅ No requiere Django
- ✅ Funciona de forma independiente
- ✅ Interfaz con emojis y colores
- ✅ Validación de IP
- ✅ Confirmación para eliminaciones
- ✅ Backup automático antes de guardar
- ✅ Manejo robusto de errores

## 📋 Comandos Disponibles

### `list` - Listar dispositivos
```bash
# Toda la configuración
python config_cli.py list

# Solo impresoras
python config_cli.py list impresora

# Solo balanzas
python config_cli.py list balanza
```

### `add` - Agregar dispositivo
```bash
python config_cli.py add [impresora|balanza] --nombre "NOMBRE" --ip "IP"

# Ejemplos:
python config_cli.py add impresora --nombre "Caja6" --ip "192.168.1.210"
python config_cli.py add balanza --nombre "Balanza_Principal" --ip "192.168.1.55"
```

### `update` - Actualizar IP
```bash
python config_cli.py update [impresora|balanza] --nombre "NOMBRE" --ip "NUEVA_IP"

# Ejemplos:
python config_cli.py update impresora --nombre "Caja6" --ip "192.168.1.211"
python config_cli.py update balanza --nombre "ICM1" --ip "192.168.1.105"
```

### `remove` - Eliminar dispositivo
```bash
python config_cli.py remove [impresora|balanza] --nombre "NOMBRE"

# Ejemplos:
python config_cli.py remove impresora --nombre "Caja6"
python config_cli.py remove balanza --nombre "ICM3"
```

## 🛡️ Características de Seguridad

### Validaciones
- ✅ **Formato IP**: Valida que la IP tenga formato xxx.xxx.xxx.xxx
- ✅ **Rangos IP**: Verifica que cada octeto esté entre 0-255
- ✅ **Duplicados**: Previene agregar dispositivos con nombres existentes
- ✅ **Existencia**: Verifica que el dispositivo exista antes de actualizar/eliminar

### Backup y Recuperación
- ✅ **Backup automático**: El script independiente crea un backup antes de cada modificación
- ✅ **Validación JSON**: Verifica la integridad del archivo antes de guardar
- ✅ **Manejo de errores**: Rollback automático en caso de error

### Confirmaciones
- ✅ **Eliminación**: Solicita confirmación antes de eliminar dispositivos
- ✅ **Mensajes claros**: Feedback detallado de cada operación

## 🔍 Ejemplos Prácticos

### Escenario 1: Agregar nueva caja registradora
```bash
# Verificar configuración actual
python config_cli.py list impresora

# Agregar nueva impresora para caja 7
python config_cli.py add impresora --nombre "Caja7" --ip "192.168.1.220"

# Verificar que se agregó correctamente
python config_cli.py list impresora
```

### Escenario 2: Cambiar IP de balanza existente
```bash
# Ver balanzas actuales
python config_cli.py list balanza

# Actualizar IP de ICM1
python config_cli.py update balanza --nombre "ICM1" --ip "192.168.1.110"

# Confirmar cambio
python config_cli.py list balanza
```

### Escenario 3: Eliminar dispositivo obsoleto
```bash
# Ver todos los dispositivos
python config_cli.py list

# Eliminar impresora antigua (con confirmación)
python config_cli.py remove impresora --nombre "Etiqueta"

# Verificar eliminación
python config_cli.py list impresora
```

## ⚠️ Notas Importantes

1. **Backup**: El script independiente crea automáticamente un archivo `config.txt.backup` antes de cada modificación

2. **Permisos**: Asegúrese de tener permisos de escritura en el directorio `core/core/`

3. **Formato**: El archivo mantiene el formato JSON con indentación de 3 espacios

4. **Encoding**: Se usa UTF-8 para soportar caracteres especiales

5. **Validación**: Siempre valide la configuración después de cambios importantes:
   ```bash
   python config_cli.py list
   ```

## 🚨 Solución de Problemas

### Error: "Archivo de configuración no encontrado"
- Verifique que está ejecutando el comando desde el directorio correcto
- Para Django: debe estar en el directorio `core/`
- Para script independiente: debe estar en la raíz del proyecto

### Error: "Formato JSON inválido"
- El archivo `config.txt` está corrupto
- Restaure desde el backup: `config.txt.backup`
- O corrija manualmente el formato JSON

### Error: "IP inválida"
- Verifique que la IP tenga formato xxx.xxx.xxx.xxx
- Cada número debe estar entre 0-255
- Ejemplo válido: `192.168.1.100`

### Error de permisos
- Ejecute como administrador si es necesario
- Verifique permisos de escritura en el directorio

## 📞 Soporte

Para problemas o mejoras, contacte al equipo de desarrollo del sistema POS SCG.