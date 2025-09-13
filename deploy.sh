#!/bin/bash

# Este script automatiza el despliegue de Django de forma interactiva y secuencial.
# Diseñado para un servidor que NO estará expuesto a Internet, en una red local.

# --- VARIABLES DE CONFIGURACIÓN ---
# Edita estas variables con la información de tu proyecto
GITHUB_REPO="https://github.com/tu-usuario/tu-repositorio-django.git"
PROJECT_DIR="/var/www/scg"
DJANGO_PROJECT_NAME="core" # Nombre de la carpeta que contiene settings.py
VENV_NAME="venv"
PYTHON_VERSION="python3"
STATIC_ROOT_DIR="$PROJECT_DIR/static"
MEDIA_ROOT_DIR="$PROJECT_DIR/media"
SERVER_IP="192.168.1.100" # La IP estática del servidor en la red local

# --- CONFIGURACIÓN DE USUARIO Y GRUPOS DE DJANGO ---
# Estas configuraciones se aplicarán a la base de datos de Django
SUPERUSER_USERNAME="scg"
SUPERUSER_PASSWORD="Servicio98"
DJANGO_GROUPS=("ADMINISTRADOR" "PESADOR" "CAJERO" "SUPERVISOR")

# --- FUNCIONES DE VALIDACIÓN ---
# Estas funciones verifican si los pre-requisitos de un paso se cumplen
check_prerequisite() {
    command -v "$1" >/dev/null 2>&1
    return $?
}

check_dir_exists() {
    [ -d "$1" ]
    return $?
}

check_file_exists() {
    [ -f "$1" ]
    return $?
}

# --- MENÚ DE AYUDA Y ESTADO DEL PROCESO ---
# Muestra una explicación del script y su estado actual
show_help() {
    echo "Uso: $0 [opción]"
    echo "  -h, --help    Muestra esta ayuda."
    echo ""
    echo "Este script guía el despliegue de Django de forma secuencial."
    echo "Los pasos se ejecutarán en orden, verificando cada etapa para asegurar un despliegue exitoso."
}

show_status() {
    echo "--- Estado del Despliegue ---"
    check_prerequisite git && echo "✔️ 1. Git instalado." || echo "❌ 1. Git NO instalado."
    check_dir_exists "$PROJECT_DIR" && echo "✔️ 2. Repositorio clonado en $PROJECT_DIR." || echo "❌ 2. Repositorio NO clonado."
    check_dir_exists "$PROJECT_DIR/$VENV_NAME" && echo "✔️ 3. Entorno virtual creado." || echo "❌ 3. Entorno virtual NO creado."
    check_file_exists "$PROJECT_DIR/$VENV_NAME/bin/gunicorn" && echo "✔️ 4. Dependencias instaladas (Gunicorn)." || echo "❌ 4. Dependencias NO instaladas."
    echo "--- Fin del Estado ---"
}

# --- PASOS INTERACTIVOS (SECUENCIALES) ---

step_1_install_deps() {
    echo "--- Paso 1: Instalando dependencias del sistema ---"
    sudo apt-get update
    sudo apt-get install -y git "$PYTHON_VERSION-venv" python3-pip postgresql postgresql-contrib nginx
    if [ $? -eq 0 ]; then
        echo "✅ Dependencias del sistema instaladas correctamente."
        return 0
    else
        echo "❌ Error al instalar dependencias del sistema."
        return 1
    fi
}

step_2_clone_repo() {
    echo "--- Paso 2: Clonando el repositorio de GitHub ---"
    if check_dir_exists "$PROJECT_DIR"; then
        echo "⚠️ El directorio del proyecto ya existe. Omitiendo la clonación."
        return 0
    fi
    git clone "$GITHUB_REPO" "$PROJECT_DIR"
    if [ $? -eq 0 ]; then
        echo "✅ Repositorio clonado en $PROJECT_DIR."
        return 0
    else
        echo "❌ Error al clonar el repositorio. Verifique la URL y los permisos."
        return 1
    fi
}

step_3_install_python_deps() {
    echo "--- Paso 3: Configurando entorno virtual e instalando dependencias ---"
    if ! check_dir_exists "$PROJECT_DIR"; then
        echo "❌ No se encontró el directorio del proyecto. Por favor, complete el Paso 2 primero."
        return 1
    fi
    cd "$PROJECT_DIR" || return 1
    "$PYTHON_VERSION" -m venv "$VENV_NAME"
    source "$VENV_NAME/bin/activate"
    pip install -r requirements.txt
    pip install gunicorn uvicorn
    if [ $? -eq 0 ]; then
        echo "✅ Dependencias de Python instaladas."
        return 0
    else
        echo "❌ Error al instalar dependencias de Python."
        return 1
    fi
}

step_4_db_migrations() {
    echo "--- Paso 4: Configurando y migrando la base de datos ---"
    if ! check_file_exists "$PROJECT_DIR/$VENV_NAME/bin/gunicorn"; then
        echo "❌ Dependencias de Python no instaladas. Por favor, complete el Paso 3 primero."
        return 1
    fi
    sudo -u postgres psql -c "CREATE DATABASE ${DJANGO_PROJECT_NAME}_db;"
    sudo -u postgres psql -c "CREATE USER ${DJANGO_PROJECT_NAME}_user WITH PASSWORD 'tu_contraseña_segura';"
    sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE ${DJANGO_PROJECT_NAME}_db TO ${DJANGO_PROJECT_NAME}_user;"
    cd "$PROJECT_DIR" || return 1
    source "$VENV_NAME/bin/activate"
    "$PYTHON_VERSION" manage.py makemigrations
    "$PYTHON_VERSION" manage.py migrate
    if [ $? -eq 0 ]; then
        echo "✅ Migraciones de base de datos completadas."
        return 0
    else
        echo "❌ Error al ejecutar las migraciones."
        return 1
    fi
}

step_5_create_superuser() {
    echo "--- Paso 5: Creando superusuario de Django ---"
    if ! check_file_exists "$PROJECT_DIR/$VENV_NAME/bin/gunicorn"; then
        echo "❌ Dependencias de Python no instaladas. Por favor, complete el Paso 3 primero."
        return 1
    fi
    cd "$PROJECT_DIR" || return 1
    source "$VENV_NAME/bin/activate"
    echo "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.filter(username='$SUPERUSER_USERNAME').exists() or User.objects.create_superuser('$SUPERUSER_USERNAME', 'admin@example.com', '$SUPERUSER_PASSWORD')" | "$PYTHON_VERSION" manage.py shell
    if [ $? -eq 0 ]; then
        echo "✅ Superusuario '$SUPERUSER_USERNAME' creado correctamente."
        return 0
    else
        echo "❌ Error al crear el superusuario."
        return 1
    fi
}

step_6_create_groups() {
    echo "--- Paso 6: Creando grupos de Django ---"
    if ! check_file_exists "$PROJECT_DIR/$VENV_NAME/bin/gunicorn"; then
        echo "❌ Dependencias de Python no instaladas. Por favor, complete el Paso 3 primero."
        return 1
    fi
    cd "$PROJECT_DIR" || return 1
    source "$VENV_NAME/bin/activate"
    for group in "${DJANGO_GROUPS[@]}"; do
        echo "from django.contrib.auth.models import Group; Group.objects.get_or_create(name='$group')" | "$PYTHON_VERSION" manage.py shell
    done
    if [ $? -eq 0 ]; then
        echo "✅ Grupos de Django creados correctamente."
        return 0
    else
        echo "❌ Error al crear los grupos."
        return 1
    fi
}

step_7_collect_static() {
    echo "--- Paso 7: Recolectando archivos estáticos y de media ---"
    if ! check_file_exists "$PROJECT_DIR/$VENV_NAME/bin/gunicorn"; then
        echo "❌ Dependencias de Python no instaladas. Por favor, complete el Paso 3 primero."
        return 1
    fi
    cd "$PROJECT_DIR" || return 1
    source "$VENV_NAME/bin/activate"
    "$PYTHON_VERSION" manage.py collectstatic --noinput
    mkdir -p "$MEDIA_ROOT_DIR"
    echo "✅ Archivos estáticos y de media recolectados."
    return 0
}

step_8_gunicorn_setup() {
    echo "--- Paso 8: Configurando Gunicorn ---"
    if ! check_file_exists "$PROJECT_DIR/$VENV_NAME/bin/gunicorn"; then
        echo "❌ Gunicorn no instalado. Por favor, complete el Paso 3 primero."
        return 1
    fi
    sudo tee /etc/systemd/system/gunicorn.service > /dev/null <<EOF
[Unit]
Description=Gunicorn instance for $DJANGO_PROJECT_NAME
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=$PROJECT_DIR
ExecStart=$PROJECT_DIR/$VENV_NAME/bin/gunicorn --workers 3 --bind unix:$PROJECT_DIR/$DJANGO_PROJECT_NAME.sock $DJANGO_PROJECT_NAME.asgi:application -k uvicorn.workers.UvicornWorker

[Install]
WantedBy=multi-user.target
EOF
    sudo systemctl daemon-reload
    sudo systemctl start gunicorn
    sudo systemctl enable gunicorn
    if [ $? -eq 0 ]; then
        echo "✅ Servicio de Gunicorn configurado e iniciado."
        return 0
    else
        echo "❌ Error al configurar el servicio de Gunicorn."
        return 1
    fi
}

step_9_nginx_setup() {
    echo "--- Paso 9: Configurando Nginx ---"
    if ! check_file_exists "/etc/systemd/system/gunicorn.service"; then
        echo "❌ Servicio de Gunicorn no configurado. Por favor, complete el Paso 8 primero."
        return 1
    fi
    sudo tee /etc/nginx/sites-available/"$DJANGO_PROJECT_NAME" > /dev/null <<EOF
server {
    listen 80;
    server_name $SERVER_IP;

    location = /favicon.ico { access_log off; log_not_found off; }

    location /static/ {
        root $PROJECT_DIR;
    }

    location /media/ {
        root $PROJECT_DIR;
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:$PROJECT_DIR/$DJANGO_PROJECT_NAME.sock;
    }
}
EOF
    sudo ln -s /etc/nginx/sites-available/"$DJANGO_PROJECT_NAME" /etc/nginx/sites-enabled/
    sudo rm -f /etc/nginx/sites-enabled/default
    sudo nginx -t
    if [ $? -eq 0 ]; then
        sudo systemctl restart nginx
        echo "✅ Nginx configurado y reiniciado."
        return 0
    else
        echo "❌ Error en la configuración de Nginx. Revise la sintaxis."
        return 1
    fi
}

# --- LÓGICA PRINCIPAL ---
main_menu() {
    clear
    show_status
    echo ""
    echo "--- Menú Principal de Despliegue ---"
    echo "1. Instalar dependencias del sistema"
    echo "2. Clonar el repositorio de GitHub"
    echo "3. Configurar entorno virtual e instalar dependencias de Python"
    echo "4. Configurar y migrar la base de datos PostgreSQL"
    echo "5. Crear superusuario de Django"
    echo "6. Crear grupos de Django"
    echo "7. Recolectar archivos estáticos y de media"
    echo "8. Configurar Gunicorn"
    echo "9. Configurar Nginx"
    echo "10. Ejecutar todos los pasos secuencialmente"
    echo "0. Salir"
    echo ""
    read -rp "Seleccione una opción: " choice

    case "$choice" in
        1) step_1_install_deps ;;
        2) step_2_clone_repo ;;
        3) step_3_install_python_deps ;;
        4) step_4_db_migrations ;;
        5) step_5_create_superuser ;;
        6) step_6_create_groups ;;
        7) step_7_collect_static ;;
        8) step_8_gunicorn_setup ;;
        9) step_9_nginx_setup ;;
        10)
            echo "Iniciando despliegue completo..."
            step_1_install_deps && \
            step_2_clone_repo && \
            step_3_install_python_deps && \
            step_4_db_migrations && \
            step_5_create_superuser && \
            step_6_create_groups && \
            step_7_collect_static && \
            step_8_gunicorn_setup && \
            step_9_nginx_setup
            echo "🎉 ¡Proceso de despliegue completo! 🎉"
            read -rp "Presione cualquier tecla para continuar..."
            ;;
        0) exit 0 ;;
        *) echo "Opción inválida." ;;
    esac

    read -rp "Presione Enter para volver al menú..."
    main_menu
}

# --- MANEJO DE ARGUMENTOS ---
if [ "$1" == "-h" ] || [ "$1" == "--help" ]; then
    show_help
    exit 0
fi

# Iniciar el menú principal
main_menu