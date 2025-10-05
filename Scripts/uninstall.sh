#!/bin/bash

# Script de desinstalación completa para aplicación Django SCG
# Revierte todos los cambios realizados por deploy.sh
# ⚠️ ADVERTENCIA: Este script eliminará TODOS los datos de la aplicación

# --- VARIABLES DE CONFIGURACIÓN (deben coincidir con deploy.sh) ---
GITHUB_REPO="https://github.com/sarmienmj/scg-estandar.git"
PROJECT_DIR="/var/www/scg"
DJANGO_APP_DIR="core"
DJANGO_PROJECT_NAME="core"
VENV_NAME="venv"
BACKUP_DIR="/var/backups/scg_uninstall"
LOG_FILE="/var/log/scg_uninstall.log"

# Variables de base de datos
DB_NAME="scgdb"
DB_USER="scg"

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# --- FUNCIONES AUXILIARES ---
log_message() {
    local message="$1"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "[$timestamp] $message" | tee -a "$LOG_FILE"
}

log_error() {
    log_message "${RED}❌ $1${NC}"
}

log_success() {
    log_message "${GREEN}✅ $1${NC}"
}

log_warning() {
    log_message "${YELLOW}⚠️  $1${NC}"
}

show_help() {
    cat << EOF
${YELLOW}⚠️  SCRIPT DE DESINSTALACIÓN COMPLETA${NC}

${RED}ADVERTENCIA: Este script eliminará:${NC}
  - Código de la aplicación ($PROJECT_DIR)
  - Base de datos PostgreSQL ($DB_NAME)
  - Usuario PostgreSQL ($DB_USER)
  - Servicios systemd (gunicorn)
  - Configuración de Nginx
  - Archivos de backup
  - Logs de la aplicación

Uso: $0 [OPCIONES]

OPCIONES:
    --backup-only       Solo crear backup sin desinstalar
    --skip-backup       No crear backup antes de desinstalar
    --keep-db           No eliminar la base de datos
    --keep-code         No eliminar el código (solo servicios)
    --force             No pedir confirmación
    -h, --help          Mostrar esta ayuda

EJEMPLOS:
    $0                          # Desinstalación completa con confirmación
    $0 --force                  # Desinstalación sin confirmación
    $0 --backup-only            # Solo crear backup
    $0 --keep-db                # Mantener la base de datos

${YELLOW}NOTA: Se recomienda crear un backup antes de desinstalar${NC}
EOF
}

confirm_uninstall() {
    echo ""
    log_warning "═══════════════════════════════════════════════════════"
    log_warning "    ⚠️  CONFIRMACIÓN DE DESINSTALACIÓN COMPLETA"
    log_warning "═══════════════════════════════════════════════════════"
    echo ""
    log_warning "Esta acción eliminará:"
    echo "  • Toda la aplicación Django en $PROJECT_DIR"
    echo "  • Base de datos PostgreSQL: $DB_NAME"
    echo "  • Usuario PostgreSQL: $DB_USER"
    echo "  • Servicios y configuraciones de Gunicorn y Nginx"
    echo ""
    log_error "⚠️  ESTA ACCIÓN NO SE PUEDE DESHACER (sin backup)"
    echo ""
    
    read -p "¿Está SEGURO de que desea continuar? (escriba 'SI' en mayúsculas): " confirmation
    
    if [[ "$confirmation" != "SI" ]]; then
        log_message "Desinstalación cancelada por el usuario"
        exit 0
    fi
    
    read -p "¿Confirma nuevamente? (s/n): " second_confirmation
    
    if [[ "$second_confirmation" != "s" && "$second_confirmation" != "S" ]]; then
        log_message "Desinstalación cancelada por el usuario"
        exit 0
    fi
    
    log_success "Confirmación recibida. Procediendo con la desinstalación..."
}

create_backup() {
    local backup_timestamp=$(date '+%Y%m%d_%H%M%S')
    local backup_path="$BACKUP_DIR/backup_$backup_timestamp"
    
    log_message "Creando backup de seguridad en $backup_path..."
    
    # Crear directorio de backup
    mkdir -p "$backup_path"
    
    # Backup del código fuente si existe
    if [[ -d "$PROJECT_DIR" ]]; then
        log_message "Respaldando código fuente..."
        rsync -av --exclude="$VENV_NAME" --exclude="*.pyc" --exclude="__pycache__" \
              "$PROJECT_DIR/" "$backup_path/code/" 2>/dev/null
        log_success "Código fuente respaldado"
    fi
    
    # Backup de base de datos si existe
    if sudo -u postgres psql -lqt | cut -d \| -f 1 | grep -qw "$DB_NAME"; then
        log_message "Respaldando base de datos..."
        
        # Backup con Django dumpdata
        if [[ -d "$PROJECT_DIR/$DJANGO_APP_DIR" ]]; then
            cd "$PROJECT_DIR/$DJANGO_APP_DIR"
            source "$PROJECT_DIR/$VENV_NAME/bin/activate" 2>/dev/null
            python manage.py dumpdata --natural-foreign --natural-primary > "$backup_path/database_dump.json" 2>/dev/null
        fi
        
        # Backup con pg_dump
        sudo -u postgres pg_dump "$DB_NAME" > "$backup_path/postgres_dump.sql" 2>/dev/null
        
        log_success "Base de datos respaldada"
    fi
    
    # Backup de configuraciones de Nginx y Gunicorn
    log_message "Respaldando configuraciones..."
    mkdir -p "$backup_path/configs"
    
    if [[ -f "/etc/systemd/system/gunicorn.service" ]]; then
        cp "/etc/systemd/system/gunicorn.service" "$backup_path/configs/"
    fi
    
    if [[ -f "/etc/nginx/sites-available/$DJANGO_PROJECT_NAME" ]]; then
        cp "/etc/nginx/sites-available/$DJANGO_PROJECT_NAME" "$backup_path/configs/"
    fi
    
    # Guardar información del sistema
    log_message "Guardando información del sistema..."
    systemctl status gunicorn > "$backup_path/gunicorn_status.txt" 2>/dev/null
    systemctl status nginx > "$backup_path/nginx_status.txt" 2>/dev/null
    
    if [[ -d "$PROJECT_DIR" ]]; then
        cd "$PROJECT_DIR"
        git log -10 --oneline > "$backup_path/git_history.txt" 2>/dev/null
        git status > "$backup_path/git_status.txt" 2>/dev/null
    fi
    
    # Crear archivo de información del backup
    cat > "$backup_path/backup_info.txt" << EOF
Backup creado: $backup_timestamp
Sistema: $(uname -a)
Fecha: $(date)
Proyecto: $PROJECT_DIR
Base de datos: $DB_NAME
Usuario DB: $DB_USER

Este backup contiene:
- Código fuente de la aplicación
- Dump de la base de datos PostgreSQL (JSON y SQL)
- Configuraciones de Gunicorn y Nginx
- Estado de los servicios
- Historial de Git

Para restaurar:
1. Restaurar código: rsync -av $backup_path/code/ $PROJECT_DIR/
2. Restaurar BD: psql -U $DB_USER -d $DB_NAME < $backup_path/postgres_dump.sql
EOF
    
    log_success "Backup completo creado en: $backup_path"
    echo "$backup_path" > "$BACKUP_DIR/latest_backup.txt"
    
    return 0
}

stop_services() {
    log_message "Deteniendo servicios..."
    
    # Detener Gunicorn
    if systemctl is-active --quiet gunicorn; then
        systemctl stop gunicorn
        log_success "Servicio Gunicorn detenido"
    else
        log_warning "Servicio Gunicorn no está corriendo"
    fi
    
    # Deshabilitar Gunicorn
    if systemctl is-enabled --quiet gunicorn 2>/dev/null; then
        systemctl disable gunicorn
        log_success "Servicio Gunicorn deshabilitado"
    fi
}

remove_nginx_config() {
    log_message "Eliminando configuración de Nginx..."
    
    # Eliminar symlink en sites-enabled
    if [[ -L "/etc/nginx/sites-enabled/$DJANGO_PROJECT_NAME" ]]; then
        rm "/etc/nginx/sites-enabled/$DJANGO_PROJECT_NAME"
        log_success "Symlink de Nginx eliminado"
    fi
    
    # Eliminar archivo de configuración
    if [[ -f "/etc/nginx/sites-available/$DJANGO_PROJECT_NAME" ]]; then
        rm "/etc/nginx/sites-available/$DJANGO_PROJECT_NAME"
        log_success "Configuración de Nginx eliminada"
    fi
    
    # Restaurar configuración default si no existe
    if [[ ! -L "/etc/nginx/sites-enabled/default" ]] && [[ -f "/etc/nginx/sites-available/default" ]]; then
        ln -s /etc/nginx/sites-available/default /etc/nginx/sites-enabled/default
        log_message "Configuración default de Nginx restaurada"
    fi
    
    # Reiniciar Nginx
    nginx -t && systemctl reload nginx
    log_success "Nginx reconfigurado"
}

remove_gunicorn_service() {
    log_message "Eliminando servicio de Gunicorn..."
    
    if [[ -f "/etc/systemd/system/gunicorn.service" ]]; then
        rm "/etc/systemd/system/gunicorn.service"
        systemctl daemon-reload
        log_success "Servicio de Gunicorn eliminado"
    else
        log_warning "Archivo de servicio Gunicorn no encontrado"
    fi
}

remove_database() {
    log_message "Eliminando base de datos PostgreSQL..."
    
    # Verificar si la base de datos existe
    if sudo -u postgres psql -lqt | cut -d \| -f 1 | grep -qw "$DB_NAME"; then
        # Terminar conexiones activas
        sudo -u postgres psql -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$DB_NAME';" 2>/dev/null
        
        # Eliminar base de datos
        sudo -u postgres psql -c "DROP DATABASE IF EXISTS $DB_NAME;"
        log_success "Base de datos $DB_NAME eliminada"
    else
        log_warning "Base de datos $DB_NAME no existe"
    fi
    
    # Eliminar usuario de PostgreSQL
    if sudo -u postgres psql -t -c "SELECT 1 FROM pg_roles WHERE rolname='$DB_USER'" | grep -q 1; then
        sudo -u postgres psql -c "DROP USER IF EXISTS $DB_USER;"
        log_success "Usuario PostgreSQL $DB_USER eliminado"
    else
        log_warning "Usuario PostgreSQL $DB_USER no existe"
    fi
}

remove_project_directory() {
    log_message "Eliminando directorio del proyecto..."
    
    if [[ -d "$PROJECT_DIR" ]]; then
        # Verificar que no estamos en el directorio
        if [[ "$PWD" == "$PROJECT_DIR"* ]]; then
            cd /tmp
        fi
        
        rm -rf "$PROJECT_DIR"
        log_success "Directorio $PROJECT_DIR eliminado"
    else
        log_warning "Directorio $PROJECT_DIR no existe"
    fi
    
    # Eliminar socket si existe
    if [[ -S "$PROJECT_DIR/$DJANGO_PROJECT_NAME.sock" ]]; then
        rm "$PROJECT_DIR/$DJANGO_PROJECT_NAME.sock"
        log_success "Socket de Gunicorn eliminado"
    fi
}

remove_logs() {
    log_message "Limpiando logs..."
    
    # Lista de posibles archivos de log
    local log_files=(
        "/var/log/scg_update.log"
        "$PROJECT_DIR/$DJANGO_APP_DIR/django_errors.log"
    )
    
    for log_file in "${log_files[@]}"; do
        if [[ -f "$log_file" ]]; then
            rm "$log_file"
            log_message "Log eliminado: $log_file"
        fi
    done
    
    log_success "Logs limpiados"
}

show_uninstall_summary() {
    echo ""
    log_success "═══════════════════════════════════════════════════════"
    log_success "    ✅ DESINSTALACIÓN COMPLETADA EXITOSAMENTE"
    log_success "═══════════════════════════════════════════════════════"
    echo ""
    echo "Elementos eliminados:"
    echo "  ✅ Código de la aplicación"
    echo "  ✅ Base de datos PostgreSQL"
    echo "  ✅ Usuario PostgreSQL"
    echo "  ✅ Servicio de Gunicorn"
    echo "  ✅ Configuración de Nginx"
    echo "  ✅ Logs de la aplicación"
    echo ""
    
    if [[ -f "$BACKUP_DIR/latest_backup.txt" ]]; then
        local latest_backup=$(cat "$BACKUP_DIR/latest_backup.txt")
        log_success "Backup guardado en: $latest_backup"
        echo ""
        echo "Para restaurar desde el backup:"
        echo "  1. Restaurar código:"
        echo "     rsync -av $latest_backup/code/ $PROJECT_DIR/"
        echo "  2. Crear base de datos:"
        echo "     sudo -u postgres createdb $DB_NAME"
        echo "  3. Restaurar base de datos:"
        echo "     sudo -u postgres psql $DB_NAME < $latest_backup/postgres_dump.sql"
    fi
    
    echo ""
    log_message "El sistema está listo para una instalación limpia"
    echo ""
}

perform_uninstall() {
    log_message "═══════════════════════════════════════════════════════"
    log_message "    INICIANDO PROCESO DE DESINSTALACIÓN"
    log_message "═══════════════════════════════════════════════════════"
    
    # Paso 1: Detener servicios
    stop_services
    
    # Paso 2: Eliminar configuración de Nginx
    remove_nginx_config
    
    # Paso 3: Eliminar servicio de Gunicorn
    remove_gunicorn_service
    
    # Paso 4: Eliminar base de datos (si no se especificó --keep-db)
    if [[ $KEEP_DB != true ]]; then
        remove_database
    else
        log_warning "Base de datos conservada según --keep-db"
    fi
    
    # Paso 5: Eliminar directorio del proyecto (si no se especificó --keep-code)
    if [[ $KEEP_CODE != true ]]; then
        remove_project_directory
    else
        log_warning "Código conservado según --keep-code"
    fi
    
    # Paso 6: Limpiar logs
    remove_logs
    
    # Mostrar resumen
    show_uninstall_summary
}

# --- MANEJO DE ARGUMENTOS ---
SKIP_BACKUP=false
BACKUP_ONLY=false
KEEP_DB=false
KEEP_CODE=false
FORCE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --backup-only)
            BACKUP_ONLY=true
            shift
            ;;
        --skip-backup)
            SKIP_BACKUP=true
            shift
            ;;
        --keep-db)
            KEEP_DB=true
            shift
            ;;
        --keep-code)
            KEEP_CODE=true
            shift
            ;;
        --force)
            FORCE=true
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            log_error "Opción desconocida: $1"
            show_help
            exit 1
            ;;
    esac
done

# --- VERIFICACIÓN DE PERMISOS ---
if [[ $EUID -ne 0 ]]; then
    log_error "Este script debe ejecutarse como root (sudo)"
    exit 1
fi

# Crear directorio de logs
mkdir -p "$(dirname "$LOG_FILE")"
mkdir -p "$BACKUP_DIR"

log_message "Iniciando script de desinstalación..."
log_message "Log guardándose en: $LOG_FILE"

# --- LÓGICA PRINCIPAL ---

# Solo crear backup
if [[ $BACKUP_ONLY == true ]]; then
    log_message "Modo: Solo crear backup"
    create_backup
    log_success "Backup completado. No se realizó desinstalación."
    exit 0
fi

# Confirmar desinstalación
if [[ $FORCE != true ]]; then
    confirm_uninstall
fi

# Crear backup antes de desinstalar
if [[ $SKIP_BACKUP != true ]]; then
    create_backup
else
    log_warning "Saltando creación de backup según --skip-backup"
fi

# Realizar desinstalación
perform_uninstall

log_message "Script de desinstalación finalizado"
log_message "Log completo: $LOG_FILE"

exit 0

