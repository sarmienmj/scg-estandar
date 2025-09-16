#!/bin/bash

# Script de actualización para aplicación Django SCG
# Permite actualizar a commits específicos, ramas o latest
# Incluye sistema de backup y rollback automático

# --- VARIABLES DE CONFIGURACIÓN (heredadas del deploy.sh) ---
GITHUB_REPO="https://github.com/sarmienmj/scg-estandar.git"
PROJECT_DIR="/var/www/scg"
DJANGO_APP_DIR="core"
DJANGO_PROJECT_NAME="core"
VENV_NAME="venv"
PYTHON_VERSION="python3"
BACKUP_DIR="/var/backups/scg"
LOG_FILE="/var/log/scg_update.log"

# Variables de base de datos para backup
DB_NAME="scgdb"
DB_USER="scg"
DB_PASSWORD="django"

# --- FUNCIONES AUXILIARES ---
log_message() {
    local message="$1"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] $message" | tee -a "$LOG_FILE"
}

show_help() {
    cat << EOF
Uso: $0 [OPCIONES] [VERSION]

OPCIONES:
    -c, --commit HASH       Actualizar a un commit específico
    -b, --branch RAMA       Actualizar a la última versión de una rama
    -l, --latest            Actualizar a la última versión de main/master
    -r, --rollback          Hacer rollback a la versión anterior
    --dry-run               Simular la actualización sin aplicar cambios
    --skip-db-backup        Omitir el backup de la base de datos
    --force                 Forzar actualización ignorando advertencias
    -h, --help              Mostrar esta ayuda

EJEMPLOS:
    $0 --latest                     # Actualizar a la última versión
    $0 --branch develop             # Actualizar a la rama develop
    $0 --commit abc123def           # Actualizar a commit específico
    $0 --rollback                   # Rollback a versión anterior
    $0 --dry-run --latest           # Simular actualización a latest

NOTAS:
    - Se crea backup automático antes de cada actualización
    - Los backups se almacenan en $BACKUP_DIR
    - Los logs se guardan en $LOG_FILE
EOF
}

check_prerequisites() {
    log_message "Verificando prerequisitos..."
    
    # Verificar si está corriendo como root
    if [[ $EUID -ne 0 ]]; then
        log_message "❌ Este script debe ejecutarse como root (sudo)"
        exit 1
    fi
    
    # Verificar directorio del proyecto
    if [[ ! -d "$PROJECT_DIR" ]]; then
        log_message "❌ Directorio del proyecto no encontrado: $PROJECT_DIR"
        exit 1
    fi
    
    # Verificar entorno virtual
    if [[ ! -d "$PROJECT_DIR/$VENV_NAME" ]]; then
        log_message "❌ Entorno virtual no encontrado: $PROJECT_DIR/$VENV_NAME"
        exit 1
    fi
    
    # Verificar si los servicios están corriendo
    if ! systemctl is-active --quiet gunicorn; then
        log_message "⚠️ Servicio gunicorn no está activo"
    fi
    
    log_message "✅ Prerequisitos verificados"
}

create_backup() {
    local backup_timestamp=$(date '+%Y%m%d_%H%M%S')
    local backup_path="$BACKUP_DIR/$backup_timestamp"
    
    log_message "Creando backup en $backup_path..."
    
    # Crear directorio de backup
    mkdir -p "$backup_path"
    
    # Backup del código fuente
    log_message "Respaldando código fuente..."
    rsync -av --exclude="$VENV_NAME" --exclude="*.pyc" --exclude="__pycache__" \
          "$PROJECT_DIR/" "$backup_path/code/" 2>/dev/null
    
    # Backup de base de datos (si no se omite)
    if [[ $SKIP_DB_BACKUP != true ]]; then
        log_message "Respaldando base de datos..."
        cd "$PROJECT_DIR/$DJANGO_APP_DIR"
        source "$PROJECT_DIR/$VENV_NAME/bin/activate"
        
        # Usando Django dumpdata para backup completo
        python manage.py dumpdata --natural-foreign --natural-primary > "$backup_path/database_dump.json"
        
        # También hacer backup con pg_dump como alternativa
        PGPASSWORD="$DB_PASSWORD" pg_dump -h localhost -U "$DB_USER" "$DB_NAME" > "$backup_path/postgres_dump.sql"
        
        if [[ $? -eq 0 ]]; then
            log_message "✅ Backup de base de datos completado"
        else
            log_message "⚠️ Advertencia: Error en backup de base de datos"
        fi
    fi
    
    # Guardar información de la versión actual
    cd "$PROJECT_DIR"
    git rev-parse HEAD > "$backup_path/current_commit.txt"
    git branch --show-current > "$backup_path/current_branch.txt"
    
    # Guardar el path del backup para rollback
    echo "$backup_path" > "$BACKUP_DIR/latest_backup.txt"
    
    log_message "✅ Backup completado en $backup_path"
    return 0
}

get_current_version_info() {
    cd "$PROJECT_DIR"
    local current_commit=$(git rev-parse HEAD)
    local current_branch=$(git branch --show-current)
    local last_commit_date=$(git log -1 --format=%cd --date=short)
    local last_commit_msg=$(git log -1 --format=%s)
    
    log_message "Versión actual:"
    log_message "  Rama: $current_branch"
    log_message "  Commit: $current_commit"
    log_message "  Fecha: $last_commit_date"
    log_message "  Mensaje: $last_commit_msg"
}

stop_services() {
    log_message "Deteniendo servicios..."
    systemctl stop gunicorn
    if [[ $? -eq 0 ]]; then
        log_message "✅ Servicio gunicorn detenido"
    else
        log_message "⚠️ Error al detener gunicorn"
    fi
}

start_services() {
    log_message "Iniciando servicios..."
    systemctl start gunicorn
    sleep 3
    
    if systemctl is-active --quiet gunicorn; then
        log_message "✅ Servicio gunicorn iniciado correctamente"
        return 0
    else
        log_message "❌ Error al iniciar gunicorn"
        return 1
    fi
}

update_to_version() {
    local version_type="$1"
    local version_value="$2"
    
    cd "$PROJECT_DIR"
    
    log_message "Actualizando repositorio..."
    git fetch origin
    
    case "$version_type" in
        "commit")
            log_message "Cambiando a commit: $version_value"
            git checkout "$version_value"
            ;;
        "branch")
            log_message "Cambiando a rama: $version_value"
            git checkout "$version_value"
            git pull origin "$version_value"
            ;;
        "latest")
            log_message "Actualizando a la última versión de main"
            git checkout main 2>/dev/null || git checkout master 2>/dev/null
            git pull origin $(git branch --show-current)
            ;;
        *)
            log_message "❌ Tipo de versión no válido: $version_type"
            return 1
            ;;
    esac
    
    if [[ $? -eq 0 ]]; then
        log_message "✅ Código actualizado correctamente"
        return 0
    else
        log_message "❌ Error al actualizar el código"
        return 1
    fi
}

check_requirements_changes() {
    local backup_path=$(cat "$BACKUP_DIR/latest_backup.txt" 2>/dev/null)
    if [[ -n "$backup_path" && -f "$backup_path/code/requirements.txt" ]]; then
        if ! diff -q "$PROJECT_DIR/requirements.txt" "$backup_path/code/requirements.txt" >/dev/null 2>&1; then
            log_message "⚠️ Detectados cambios en requirements.txt"
            return 1
        fi
    fi
    return 0
}

update_dependencies() {
    log_message "Actualizando dependencias Python..."
    cd "$PROJECT_DIR"
    source "$VENV_NAME/bin/activate"
    
    pip install -r requirements.txt --upgrade
    
    if [[ $? -eq 0 ]]; then
        log_message "✅ Dependencias actualizadas"
        return 0
    else
        log_message "❌ Error al actualizar dependencias"
        return 1
    fi
}

run_migrations() {
    log_message "Ejecutando migraciones..."
    cd "$PROJECT_DIR/$DJANGO_APP_DIR"
    source "$PROJECT_DIR/$VENV_NAME/bin/activate"
    
    # Hacer makemigrations
    python manage.py makemigrations
    if [[ $? -ne 0 ]]; then
        log_message "❌ Error en makemigrations"
        return 1
    fi
    
    # Ejecutar migrate
    python manage.py migrate
    if [[ $? -eq 0 ]]; then
        log_message "✅ Migraciones ejecutadas correctamente"
        return 0
    else
        log_message "❌ Error al ejecutar migraciones"
        return 1
    fi
}

collect_static_files() {
    log_message "Recolectando archivos estáticos..."
    cd "$PROJECT_DIR/$DJANGO_APP_DIR"
    source "$PROJECT_DIR/$VENV_NAME/bin/activate"
    
    python manage.py collectstatic --noinput
    if [[ $? -eq 0 ]]; then
        log_message "✅ Archivos estáticos recolectados"
        return 0
    else
        log_message "⚠️ Error al recolectar archivos estáticos"
        return 1
    fi
}

health_check() {
    log_message "Verificando salud de la aplicación..."
    
    # Verificar que gunicorn está corriendo
    if ! systemctl is-active --quiet gunicorn; then
        log_message "❌ Servicio gunicorn no está activo"
        return 1
    fi
    
    # Verificar que el socket existe
    if [[ ! -S "$PROJECT_DIR/$DJANGO_PROJECT_NAME.sock" ]]; then
        log_message "❌ Socket de gunicorn no encontrado"
        return 1
    fi
    
    # Verificar conexión a base de datos
    cd "$PROJECT_DIR/$DJANGO_APP_DIR"
    source "$PROJECT_DIR/$VENV_NAME/bin/activate"
    
    python -c "
import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', '$DJANGO_PROJECT_NAME.settings')
django.setup()
from django.db import connection
cursor = connection.cursor()
cursor.execute('SELECT 1')
print('DB connection OK')
" 2>/dev/null
    
    if [[ $? -eq 0 ]]; then
        log_message "✅ Verificación de salud exitosa"
        return 0
    else
        log_message "❌ Falló la verificación de salud"
        return 1
    fi
}

rollback_to_previous() {
    local backup_path=$(cat "$BACKUP_DIR/latest_backup.txt" 2>/dev/null)
    
    if [[ -z "$backup_path" || ! -d "$backup_path" ]]; then
        log_message "❌ No se encontró backup para rollback"
        return 1
    fi
    
    log_message "Iniciando rollback desde $backup_path..."
    
    # Detener servicios
    stop_services
    
    # Restaurar código
    log_message "Restaurando código fuente..."
    rsync -av --delete --exclude="$VENV_NAME" \
          "$backup_path/code/" "$PROJECT_DIR/"
    
    # Restaurar base de datos si existe
    if [[ -f "$backup_path/database_dump.json" ]]; then
        log_message "Restaurando base de datos..."
        cd "$PROJECT_DIR/$DJANGO_APP_DIR"
        source "$PROJECT_DIR/$VENV_NAME/bin/activate"
        
        # Limpiar datos actuales y restaurar
        python manage.py flush --noinput
        python manage.py loaddata "$backup_path/database_dump.json"
        
        if [[ $? -eq 0 ]]; then
            log_message "✅ Base de datos restaurada"
        else
            log_message "⚠️ Error al restaurar base de datos"
        fi
    fi
    
    # Reinstalar dependencias por si acaso
    update_dependencies
    
    # Iniciar servicios
    start_services
    
    # Verificar salud
    if health_check; then
        log_message "✅ Rollback completado exitosamente"
        return 0
    else
        log_message "❌ Rollback completado pero hay problemas de salud"
        return 1
    fi
}

perform_update() {
    local version_type="$1"
    local version_value="$2"
    
    log_message "=== INICIANDO ACTUALIZACIÓN ==="
    get_current_version_info
    
    # Crear backup
    if ! create_backup; then
        log_message "❌ Error al crear backup. Abortando actualización."
        return 1
    fi
    
    # Detener servicios
    stop_services
    
    # Actualizar código
    if ! update_to_version "$version_type" "$version_value"; then
        log_message "❌ Error al actualizar código. Iniciando rollback..."
        rollback_to_previous
        return 1
    fi
    
    # Verificar cambios en dependencias
    if check_requirements_changes; then
        log_message "No hay cambios en requirements.txt"
    else
        log_message "Detectados cambios en dependencias, actualizando..."
        if ! update_dependencies; then
            log_message "❌ Error al actualizar dependencias. Iniciando rollback..."
            rollback_to_previous
            return 1
        fi
    fi
    
    # Ejecutar migraciones
    if ! run_migrations; then
        log_message "❌ Error en migraciones. Iniciando rollback..."
        rollback_to_previous
        return 1
    fi
    
    # Recolectar archivos estáticos
    collect_static_files
    
    # Iniciar servicios
    if ! start_services; then
        log_message "❌ Error al iniciar servicios. Iniciando rollback..."
        rollback_to_previous
        return 1
    fi
    
    # Verificar salud
    if ! health_check; then
        if [[ $FORCE != true ]]; then
            log_message "❌ Falló verificación de salud. Iniciando rollback..."
            rollback_to_previous
            return 1
        else
            log_message "⚠️ Falló verificación de salud, pero continuando por --force"
        fi
    fi
    
    log_message "=== ACTUALIZACIÓN COMPLETADA EXITOSAMENTE ==="
    get_current_version_info
    return 0
}

# --- MANEJO DE ARGUMENTOS ---
DRY_RUN=false
SKIP_DB_BACKUP=false
FORCE=false
VERSION_TYPE=""
VERSION_VALUE=""
ACTION=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -c|--commit)
            VERSION_TYPE="commit"
            VERSION_VALUE="$2"
            ACTION="update"
            shift 2
            ;;
        -b|--branch)
            VERSION_TYPE="branch"
            VERSION_VALUE="$2"
            ACTION="update"
            shift 2
            ;;
        -l|--latest)
            VERSION_TYPE="latest"
            ACTION="update"
            shift
            ;;
        -r|--rollback)
            ACTION="rollback"
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --skip-db-backup)
            SKIP_DB_BACKUP=true
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
            log_message "❌ Opción desconocida: $1"
            show_help
            exit 1
            ;;
    esac
done

# --- LÓGICA PRINCIPAL ---
if [[ -z "$ACTION" ]]; then
    log_message "❌ Debe especificar una acción"
    show_help
    exit 1
fi

# Crear directorio de logs si no existe
mkdir -p "$(dirname "$LOG_FILE")"
mkdir -p "$BACKUP_DIR"

# Verificar prerequisitos
check_prerequisites

if [[ "$ACTION" == "rollback" ]]; then
    if [[ $DRY_RUN == true ]]; then
        log_message "DRY RUN: Se haría rollback a la versión anterior"
    else
        rollback_to_previous
    fi
elif [[ "$ACTION" == "update" ]]; then
    if [[ $DRY_RUN == true ]]; then
        log_message "DRY RUN: Se actualizaría a $VERSION_TYPE: $VERSION_VALUE"
        get_current_version_info
    else
        perform_update "$VERSION_TYPE" "$VERSION_VALUE"
    fi
fi
