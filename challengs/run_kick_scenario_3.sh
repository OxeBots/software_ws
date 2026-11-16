#!/usr/bin/env bash
# ==============================================================================
# SSL Kick Technical Challenge - Cenário 3
# Bola em (-200, 0) com defesa nas alas (-1675, 700), (-1675, -700) e GK (-2175, 0)
# Permissão de execução: chmod +x run_kick_scenario_3.sh
# Uso:
#   ./challengs/run_kick_scenario_3.sh                  # Simulação (grSim)
#   ./challengs/run_kick_scenario_3.sh --real           # Jogo Real via Rádio (mode:=game)
#   ./challengs/run_kick_scenario_3.sh --ra             # Simulador ER-Force/Ra (mode:=ra)
#   ./challengs/run_kick_scenario_3.sh mode:=game ...   # Argumentos diretos do launch
# ==============================================================================
set -eo pipefail

MODE="grsim"
LAUNCH_ARGS=()
for arg in "$@"; do
    case "$arg" in
        --real|--game|-r)
            MODE="game"
            LAUNCH_ARGS+=("mode:=game")
            ;;
        --ra)
            MODE="ra"
            LAUNCH_ARGS+=("mode:=ra")
            ;;
        mode:=*)
            MODE="${arg#mode:=}"
            LAUNCH_ARGS+=("$arg")
            ;;
        -h|--help)
            echo "Uso: $0 [--real|--game|-r] [--ra] [argumentos_ros2_launch...]"
            echo "  --real, --game, -r  Executa com robôs reais via rádio NRF24 (mode:=game)"
            echo "  --ra                Executa no simulador ER-Force/Ra (mode:=ra)"
            exit 0
            ;;
        *)
            LAUNCH_ARGS+=("$arg")
            ;;
    esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "${SCRIPT_DIR}/../install/setup.bash" ] || [ -d "${SCRIPT_DIR}/../src" ]; then
    WS_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
else
    WS_DIR="${SCRIPT_DIR}"
fi
cd "${WS_DIR}"

# 1. Carrega o ambiente base do ROS 2 Jazzy
if [ -f "/opt/ros/jazzy/setup.bash" ]; then
    source /opt/ros/jazzy/setup.bash
else
    echo "[ERRO] Arquivo /opt/ros/jazzy/setup.bash não encontrado!" >&2
    exit 1
fi

# 2. Carrega o workspace local compilado
if [ -f "${WS_DIR}/install/setup.bash" ]; then
    source "${WS_DIR}/install/setup.bash"
else
    echo "[AVISO] Arquivo install/setup.bash não encontrado. Certifique-se de que o workspace foi compilado." >&2
fi

# 3. Posiciona a bola e os robôs no simulador (apenas fora do modo real)
if [ "${MODE}" != "game" ] && [ -f "${SCRIPT_DIR}/set_kick_positions.py" ]; then
    python3 "${SCRIPT_DIR}/set_kick_positions.py" 3 || true
fi

# 4. Sincroniza os XMLs do desafio com a pasta de instalação para dispensar recompilação manual
if [ -d "${WS_DIR}/install/oxebots_strategy/share/oxebots_strategy/behavior_trees" ]; then
    cp -f --remove-destination "${WS_DIR}/src/oxebots_strategy/behavior_trees/challengs/kick_challenge_"*.xml \
          "${WS_DIR}/install/oxebots_strategy/share/oxebots_strategy/behavior_trees/" 2>/dev/null || true
fi

echo "=========================================================="
echo " SSL Kick Technical Challenge - Cenário 3"
echo "  - Árvore: kick_challenge_3.xml"
echo "  - Time: yellow"
echo "  - Modo: ${MODE}"
echo "=========================================================="

exec ros2 launch oxebots_bringup ssl-new.launch.py \
    bt_xml:=kick_challenge_3.xml \
    team_color:=yellow "${LAUNCH_ARGS[@]}"
