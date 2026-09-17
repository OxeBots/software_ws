#!/bin/bash
# ==============================================================================
# Script para executar partida simulada entre Time Azul e Time Amarelo
# Time Azul:    ROS_DOMAIN_ID=0  |  grSim UDP Port 10301  |  is_yellow_team: false
# Time Amarelo: ROS_DOMAIN_ID=1  |  grSim UDP Port 10302  |  is_yellow_team: true
# ==============================================================================

set -e

# Se estiver executando no host e o container estiver ativo, redireciona para o DevContainer
if [ ! -f /.dockerenv ] && command -v docker >/dev/null 2>&1; then
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    CONTAINER_NAME=$(docker ps --filter "label=devcontainer.local_folder=$SCRIPT_DIR" --format "{{.Names}}" | head -n 1)
    if [ -z "$CONTAINER_NAME" ]; then
        CONTAINER_NAME=$(docker ps --format "{{.Names}}" | grep -E "software_ws" | head -n 1)
    fi
    if [ -n "$CONTAINER_NAME" ]; then
        echo "Redirecionando execução para o DevContainer ($CONTAINER_NAME)..."
        exec docker exec -it "$CONTAINER_NAME" bash -c "source /opt/ros/jazzy/setup.bash && source /software_ws/install/setup.bash && /software_ws/run_match.sh $*"
    fi
fi

# Carrega ambiente ROS2 e workspace
if [ -f "/opt/ros/jazzy/setup.bash" ]; then
    source /opt/ros/jazzy/setup.bash
elif [ -f "/opt/ros/humble/setup.bash" ]; then
    source /opt/ros/humble/setup.bash
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/install/setup.bash" ]; then
    source "$SCRIPT_DIR/install/setup.bash"
fi

echo "=========================================================="
echo "    INICIANDO PARTIDA SIMULADA: TIME AZUL X TIME AMARELO  "
echo "=========================================================="
echo "  - Azul:    ROS_DOMAIN_ID=0 (grSim port 10301)"
echo "  - Amarelo: ROS_DOMAIN_ID=1 (grSim port 10302)"
echo "  - Visão:   Multicast 224.5.23.2:10020"
echo "  - Juiz:    Multicast 224.5.23.1:10003"
echo "=========================================================="
echo "Pressione Ctrl+C para encerrar a partida a qualquer momento."
echo ""

ros2 launch oxebots_bringup match.launch.py "$@"
