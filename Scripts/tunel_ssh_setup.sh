#!/bin/bash

# Script para configurar túnel SSH inverso persistente en servidor Linux local
# Este script configura un túnel SSH que permite acceso remoto a servicios locales
# a través de un VPS público, solucionando problemas de CG-NAT

# --- VARIABLES DE CONFIGURACIÓN ---
# Edita estas variables con la información de tu configuración
VPS_IP="66.29.148.38"          # IP del VPS público
VPS_USER="bdhagxkltr"          # Usuario en el VPS
VPS_SSH_PORT="22"              # Puerto SSH del VPS (por defecto 22)
LOCAL_USER=""                  # Usuario local (se detectará automáticamente si está vacío)
TUNEL_SSH_PORT=""              # Puerto del túnel SSH (parámetro requerido)
WEB_PORT=""                    # Puerto del servicio web (opcional, parámetro)
GENERATE_KEYS=true             # Generar nuevas claves SSH
KEYS_DIR="$HOME/.ssh"          # Directorio para claves SSH

# --- FUNCIONES DE VALIDACIÓN ---
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

# --- FUNCIONES DE UTILIDAD ---
show_help() {
    echo "Uso: $0 [opciones]"
    echo "  -h, --help              Muestra esta ayuda."
    echo "  -p, --port PUERTO       Puerto del túnel SSH (requerido)"
    echo "  -w, --web-port PUERTO   Puerto del servicio web (opcional)"
    echo "  -v, --vps-ip IP         IP del VPS (por defecto: $VPS_IP)"
    echo "  -u, --vps-user USER     Usuario del VPS (por defecto: $VPS_USER)"
    echo "  --no-keys               No generar nuevas claves SSH"
    echo ""
    echo "Ejemplos:"
    echo "  $0 -p 3001                    # Túnel SSH básico en puerto 3001"
    echo "  $0 -p 3001 -w 8000           # Túnel SSH + web en puerto 8000"
    echo "  $0 -p 3001 --vps-ip 1.2.3.4  # Túnel con VPS personalizado"
}

show_status() {
    echo "--- Estado de Configuración del Túnel SSH ---"
    echo "🌐 VPS configurado: $VPS_USER@$VPS_IP:$VPS_SSH_PORT"

    if [ -n "$TUNEL_SSH_PORT" ]; then
        echo "🔗 Puerto túnel SSH: $TUNEL_SSH_PORT"
    fi

    if [ -n "$WEB_PORT" ]; then
        echo "🌍 Puerto servicio web: $WEB_PORT"
    fi

    check_prerequisite autossh && echo "✔️ 1. Autossh instalado." || echo "❌ 1. Autossh NO instalado."
    check_file_exists "$KEYS_DIR/id_rsa.pub" && echo "✔️ 2. Claves SSH existen." || echo "❌ 2. Claves SSH NO existen."
    check_file_exists "/etc/systemd/system/autossh-tunel-ssh.service" && echo "✔️ 3. Servicio SSH configurado." || echo "❌ 3. Servicio SSH NO configurado."

    if [ -n "$WEB_PORT" ]; then
        check_file_exists "/etc/systemd/system/autossh-tunel-web.service" && echo "✔️ 4. Servicio web configurado." || echo "❌ 4. Servicio web NO configurado."
    fi

    echo "--- Fin del Estado ---"
}

# --- PASOS DE CONFIGURACIÓN ---

step_1_install_dependencies() {
    echo "--- Paso 1: Instalando dependencias necesarias ---"

    # Verificar si autossh ya está instalado
    if check_prerequisite autossh; then
        echo "✅ Autossh ya está instalado."
        return 0
    fi

    sudo apt-get update
    sudo apt-get install -y autossh

    if [ $? -eq 0 ]; then
        echo "✅ Autossh instalado correctamente."
        return 0
    else
        echo "❌ Error al instalar autossh."
        return 1
    fi
}

step_2_generate_ssh_keys() {
    if [ "$GENERATE_KEYS" != "true" ]; then
        echo "--- Paso 2: Omitiendo generación de claves SSH ---"
        return 0
    fi

    echo "--- Paso 2: Generando claves SSH ---"

    # Crear directorio .ssh si no existe
    mkdir -p "$KEYS_DIR"

    # Generar clave SSH si no existe
    if [ ! -f "$KEYS_DIR/id_rsa" ]; then
        echo "🔑 Generando nueva clave SSH..."
        ssh-keygen -t rsa -b 4096 -f "$KEYS_DIR/id_rsa" -N "" -C "tunel-ssh-$(hostname)-$(date +%Y%m%d)"

        if [ $? -eq 0 ]; then
            echo "✅ Clave SSH generada: $KEYS_DIR/id_rsa"
            echo "📋 Clave pública para agregar al VPS:"
            cat "$KEYS_DIR/id_rsa.pub"
            echo ""
            echo "💡 Copia el contenido anterior y agrégalo como clave autorizada en tu VPS"
        else
            echo "❌ Error al generar clave SSH."
            return 1
        fi
    else
        echo "✅ Clave SSH ya existe: $KEYS_DIR/id_rsa"
        echo "📋 Clave pública:"
        cat "$KEYS_DIR/id_rsa.pub"
    fi

    return 0
}

step_3_configure_firewall() {
    echo "--- Paso 3: Configurando firewall ---"

    # Verificar si ufw está disponible
    if check_prerequisite ufw; then
        FIREWALL_CMD="ufw"
    elif check_prerequisite iptables; then
        FIREWALL_CMD="iptables"
        echo "⚠️ Usando iptables directamente (ufw no disponible)"
    else
        echo "⚠️ No se encontró firewall (ufw/iptables). Saltando configuración de firewall."
        return 0
    fi

    echo "🔥 Configurando firewall con $FIREWALL_CMD..."

    # Permitir SSH (puerto 22)
    if [ "$FIREWALL_CMD" = "ufw" ]; then
        sudo ufw allow 22/tcp
        sudo ufw allow "$TUNEL_SSH_PORT/tcp"
        if [ -n "$WEB_PORT" ]; then
            sudo ufw allow "$WEB_PORT/tcp"
        fi
        sudo ufw --force enable
    else
        # Usar iptables
        sudo iptables -A INPUT -p tcp --dport 22 -j ACCEPT
        sudo iptables -A INPUT -p tcp --dport "$TUNEL_SSH_PORT" -j ACCEPT
        if [ -n "$WEB_PORT" ]; then
            sudo iptables -A INPUT -p tcp --dport "$WEB_PORT" -j ACCEPT
        fi
        # Guardar reglas
        sudo iptables-save | sudo tee /etc/iptables/rules.v4 > /dev/null
    fi

    if [ $? -eq 0 ]; then
        echo "✅ Firewall configurado correctamente."
        echo "   - SSH permitido (puerto 22)"
        echo "   - Túnel SSH permitido (puerto $TUNEL_SSH_PORT)"
        if [ -n "$WEB_PORT" ]; then
            echo "   - Servicio web permitido (puerto $WEB_PORT)"
        fi
        return 0
    else
        echo "❌ Error al configurar firewall."
        return 1
    fi
}

step_4_create_ssh_service() {
    echo "--- Paso 4: Creando servicio SSH para túnel persistente ---"

    # Detectar usuario local si no está configurado
    if [ -z "$LOCAL_USER" ]; then
        LOCAL_USER=$(whoami)
        echo "👤 Usuario local detectado: $LOCAL_USER"
    fi

    # Crear archivo de servicio SSH
    sudo tee /etc/systemd/system/autossh-tunel-ssh.service > /dev/null <<EOF
[Unit]
Description=Tunel SSH Inverso Persistente para Acceso Remoto ($TUNEL_SSH_PORT)
After=network-online.target
Wants=network-online.target

[Service]
User=$LOCAL_USER
Type=simple

# Comando para túnel SSH inverso
ExecStart=/usr/bin/autossh -M 0 -o "ExitOnForwardFailure yes" -o "ServerAliveInterval 30" -o "ServerAliveCountMax 3" -N -R $TUNEL_SSH_PORT:localhost:22 $VPS_USER@$VPS_IP -p $VPS_SSH_PORT

# Configuración de reinicio para persistencia
Restart=always
RestartSec=5

# Límites de recursos
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
EOF

    if [ $? -eq 0 ]; then
        echo "✅ Servicio SSH creado: /etc/systemd/system/autossh-tunel-ssh.service"
        return 0
    else
        echo "❌ Error al crear servicio SSH."
        return 1
    fi
}

step_5_create_web_service() {
    if [ -z "$WEB_PORT" ]; then
        echo "--- Paso 5: Omitiendo servicio web (no especificado) ---"
        return 0
    fi

    echo "--- Paso 5: Creando servicio web para túnel persistente ---"

    # Crear archivo de servicio web
    sudo tee /etc/systemd/system/autossh-tunel-web.service > /dev/null <<EOF
[Unit]
Description=Tunel SSH Inverso Persistente para Servicio Web ($WEB_PORT)
After=network-online.target
Wants=network-online.target

[Service]
User=$LOCAL_USER
Type=simple

# Comando para túnel web
ExecStart=/usr/bin/autossh -M 0 -o "ExitOnForwardFailure yes" -o "ServerAliveInterval 30" -o "ServerAliveCountMax 3" -N -R $WEB_PORT:localhost:$WEB_PORT $VPS_USER@$VPS_IP -p $VPS_SSH_PORT

# Configuración de reinicio para persistencia
Restart=always
RestartSec=5

# Límites de recursos
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
EOF

    if [ $? -eq 0 ]; then
        echo "✅ Servicio web creado: /etc/systemd/system/autossh-tunel-web.service"
        return 0
    else
        echo "❌ Error al crear servicio web."
        return 1
    fi
}

step_6_enable_and_start_services() {
    echo "--- Paso 6: Habilitando e iniciando servicios ---"

    # Recargar systemd
    sudo systemctl daemon-reload

    # Habilitar servicios
    sudo systemctl enable autossh-tunel-ssh.service
    echo "✅ Servicio SSH habilitado."

    if [ -n "$WEB_PORT" ]; then
        sudo systemctl enable autossh-tunel-web.service
        echo "✅ Servicio web habilitado."
    fi

    # Iniciar servicios
    sudo systemctl start autossh-tunel-ssh.service
    if [ $? -eq 0 ]; then
        echo "✅ Servicio SSH iniciado."
    else
        echo "❌ Error al iniciar servicio SSH."
        return 1
    fi

    if [ -n "$WEB_PORT" ]; then
        sudo systemctl start autossh-tunel-web.service
        if [ $? -eq 0 ]; then
            echo "✅ Servicio web iniciado."
        else
            echo "❌ Error al iniciar servicio web."
            return 1
        fi
    fi

    return 0
}

step_7_show_connection_info() {
    echo "--- Paso 7: Información de conexión ---"
    echo ""
    echo "🎉 ¡Configuración del túnel SSH completada!"
    echo ""
    echo "📋 Información de conexión:"
    echo "   🌐 VPS: $VPS_USER@$VPS_IP:$VPS_SSH_PORT"
    echo "   🔗 Túnel SSH: Puerto $TUNEL_SSH_PORT → localhost:22"
    if [ -n "$WEB_PORT" ]; then
        echo "   🌍 Túnel Web: Puerto $WEB_PORT → localhost:$WEB_PORT"
    fi
    echo ""
    echo "🔑 Comandos de conexión:"
    echo "   📡 SSH: ssh -J $VPS_USER@$VPS_IP:$VPS_SSH_PORT $LOCAL_USER@$VPS_IP -p $TUNEL_SSH_PORT"
    if [ -n "$WEB_PORT" ]; then
        echo "   🌐 Web: http://$VPS_IP:$WEB_PORT"
    fi
    echo ""
    echo "📁 Ubicación de claves SSH:"
    echo "   🔐 Clave privada: $KEYS_DIR/id_rsa"
    echo "   🔑 Clave pública: $KEYS_DIR/id_rsa.pub"
    echo ""
    echo "💡 Agrega la clave pública al VPS para permitir conexiones sin contraseña."
    echo ""
    echo "🔧 Gestión de servicios:"
    echo "   Ver estado: sudo systemctl status autossh-tunel-ssh.service"
    echo "   Reiniciar:  sudo systemctl restart autossh-tunel-ssh.service"
    echo "   Logs:       sudo journalctl -u autossh-tunel-ssh.service -f"
}

# --- LÓGICA PRINCIPAL ---
main_menu() {
    clear
    show_status
    echo ""
    echo "--- Menú de Configuración del Túnel SSH ---"
    echo "1. Instalar dependencias (autossh)"
    echo "2. Generar claves SSH"
    echo "3. Configurar firewall"
    echo "4. Crear servicio SSH para túnel"
    echo "5. Crear servicio web para túnel (opcional)"
    echo "6. Habilitar e iniciar servicios"
    echo "7. Mostrar información de conexión"
    echo "8. Ejecutar configuración completa"
    echo "0. Salir"
    echo ""
    read -rp "Seleccione una opción: " choice

    case "$choice" in
        1) step_1_install_dependencies ;;
        2) step_2_generate_ssh_keys ;;
        3) step_3_configure_firewall ;;
        4) step_4_create_ssh_service ;;
        5) step_5_create_web_service ;;
        6) step_6_enable_and_start_services ;;
        7) step_7_show_connection_info ;;
        8)
            echo "🚀 Iniciando configuración completa del túnel SSH..."
            step_1_install_dependencies && \
            step_2_generate_ssh_keys && \
            step_3_configure_firewall && \
            step_4_create_ssh_service && \
            step_5_create_web_service && \
            step_6_enable_and_start_services && \
            step_7_show_connection_info
            echo ""
            echo "🎉 ¡Configuración completa del túnel SSH finalizada!"
            read -rp "Presione cualquier tecla para continuar..."
            ;;
        0) exit 0 ;;
        *) echo "❌ Opción inválida." ;;
    esac

    read -rp "Presione Enter para volver al menú..."
    main_menu
}

# --- MANEJO DE ARGUMENTOS ---
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -p|--port)
            if [[ -n $2 && $2 =~ ^[0-9]+$ ]]; then
                TUNEL_SSH_PORT="$2"
                echo "🔗 Puerto del túnel SSH: $TUNEL_SSH_PORT"
                shift 2
            else
                echo "❌ Error: El puerto debe ser un número válido."
                echo "Ejemplo: $0 -p 3001"
                exit 1
            fi
            ;;
        -w|--web-port)
            if [[ -n $2 && $2 =~ ^[0-9]+$ ]]; then
                WEB_PORT="$2"
                echo "🌍 Puerto del servicio web: $WEB_PORT"
                shift 2
            else
                echo "❌ Error: El puerto web debe ser un número válido."
                echo "Ejemplo: $0 -p 3001 -w 8000"
                exit 1
            fi
            ;;
        -v|--vps-ip)
            if [[ -n $2 ]]; then
                VPS_IP="$2"
                echo "🌐 IP del VPS: $VPS_IP"
                shift 2
            else
                echo "❌ Error: Se requiere especificar la IP del VPS."
                exit 1
            fi
            ;;
        -u|--vps-user)
            if [[ -n $2 ]]; then
                VPS_USER="$2"
                echo "👤 Usuario del VPS: $VPS_USER"
                shift 2
            else
                echo "❌ Error: Se requiere especificar el usuario del VPS."
                exit 1
            fi
            ;;
        --no-keys)
            GENERATE_KEYS=false
            echo "🔑 No se generarán nuevas claves SSH"
            shift
            ;;
        *)
            echo "❌ Opción desconocida: $1"
            echo "Use $0 --help para ver las opciones disponibles."
            exit 1
            ;;
    esac
done

# --- VALIDACIONES PREVIAS ---
if [ -z "$TUNEL_SSH_PORT" ]; then
    echo "❌ Error: El puerto del túnel SSH es requerido."
    echo "Use $0 -p PUERTO para especificarlo."
    exit 1
fi

# Verificar que el puerto no esté en uso
if ss -tuln | grep -q ":$TUNEL_SSH_PORT "; then
    echo "⚠️ Advertencia: El puerto $TUNEL_SSH_PORT parece estar en uso."
    echo "   Continuar podría causar conflictos."
    read -rp "   ¿Desea continuar de todos modos? (s/n): " confirm
    if [[ ! $confirm =~ ^[Ss]$ ]]; then
        echo "❌ Configuración cancelada por el usuario."
        exit 1
    fi
fi

# --- INICIAR MENÚ PRINCIPAL ---
main_menu
