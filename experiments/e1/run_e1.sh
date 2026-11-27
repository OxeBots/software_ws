#!/usr/bin/env bash
# ==============================================================================
# Runner em Lote do Experimento E1 (Ablação do Safety Gate e Preempção Reativa)
#
# Uso:
#   ./experiments/e1/run_e1.sh [N] [--match]
#
# Argumentos:
#   N         Número de repetições por configuração A, B, C (padrão: 2)
#   --match   Executa com partida completa Azul vs. Amarelo (match:=True)
#             em vez do modo determinístico de time único (team_color:=blue)
# ==============================================================================

set -eo pipefail

# Redireciona automaticamente para o DevContainer caso executado no host
if [ ! -f /.dockerenv ] && command -v docker >/dev/null 2>&1; then
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    WS_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
    CONTAINER_NAME=$(docker ps --filter "label=devcontainer.local_folder=$WS_ROOT" --format "{{.Names}}" | head -n 1)
    if [ -z "$CONTAINER_NAME" ]; then
        CONTAINER_NAME=$(docker ps --format "{{.Names}}" | grep -E "software_ws|blackburn" | head -n 1)
    fi
    if [ -n "$CONTAINER_NAME" ]; then
        echo "[E1] Redirecionando execução para o DevContainer ($CONTAINER_NAME)..."
        exec docker exec "$CONTAINER_NAME" bash -c "cd /software_ws && /software_ws/experiments/e1/run_e1.sh $*"
    fi
fi

REPS=2
MATCH_MODE=false

for arg in "$@"; do
    case "$arg" in
        --match)
            MATCH_MODE=true
            ;;
        -h|--help)
            echo "Uso: $0 [N_REPETICOES] [--match]"
            echo "  N_REPETICOES  Número de rodadas por configuração (default: 2)"
            echo "  --match       Roda com match:=True (Azul vs. Amarelo ativos)"
            exit 0
            ;;
        *)
            if [[ "$arg" =~ ^[0-9]+$ ]]; then
                REPS="$arg"
            else
                echo "[ERRO] Argumento desconhecido: $arg" >&2
                exit 1
            fi
            ;;
    esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WS_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "${WS_DIR}"

if [ -f "/opt/ros/jazzy/setup.bash" ]; then
    source /opt/ros/jazzy/setup.bash
elif [ -f "/opt/ros/humble/setup.bash" ]; then
    source /opt/ros/humble/setup.bash
fi

if [ -f "${WS_DIR}/install/setup.bash" ]; then
    source "${WS_DIR}/install/setup.bash"
else
    echo "[ERRO] install/setup.bash não encontrado. Execute ./build.sh primeiro." >&2
    exit 1
fi

LAUNCH_PID=""
LOGGER_PID=""
SCENARIO_PID=""

cleanup_round() {
    for pid_var in SCENARIO_PID LOGGER_PID LAUNCH_PID; do
        pid="${!pid_var}"
        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            kill -SIGINT "$pid" 2>/dev/null || true
        fi
    done
    sleep 1
    for pid_var in SCENARIO_PID LOGGER_PID LAUNCH_PID; do
        pid="${!pid_var}"
        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            kill -SIGTERM "$pid" 2>/dev/null || true
        fi
    done
    sleep 1
    # Garante encerramento limpo de quaisquer nós remanescentes da rodada
    pkill -f "oxebots_bringup" 2>/dev/null || true
    pkill -f "strategy_node" 2>/dev/null || true
    pkill -f "movement_calculation_node" 2>/dev/null || true
    pkill -f "d_star_planner_node" 2>/dev/null || true
    pkill -f "trajectory_setpoint_node" 2>/dev/null || true
    pkill -f "role_assigner_node" 2>/dev/null || true
    pkill -f "referee_state_node" 2>/dev/null || true
    pkill -f "game_observer_node" 2>/dev/null || true
    pkill -f "field_visualizer_node" 2>/dev/null || true
    pkill -f "kalman_filter_node" 2>/dev/null || true
    pkill -f "grSim_controller_node" 2>/dev/null || true
    pkill -f "vision_bridge_node" 2>/dev/null || true
    pkill -f "gc_multicast_bridge" 2>/dev/null || true
    pkill -f "team_client_node" 2>/dev/null || true
    pkill -f "benchmark_logger.py" 2>/dev/null || true
    pkill -f "e1_scenario.py" 2>/dev/null || true
    LAUNCH_PID=""
    LOGGER_PID=""
    SCENARIO_PID=""
}

trap cleanup_round EXIT INT TERM

echo "=================================================================="
echo " Experimento E1 — Ablação do Safety Gate e Preempção Reativa"
echo "  - Repetições (N): ${REPS}"
echo "  - Modo Partida (match:=True): ${MATCH_MODE}"
echo "=================================================================="

# Checagem rápida de pacotes de visão do grSim (224.5.23.2:10020)
python3 - << 'EOF'
import sys
from experiments.e1.e1_scenario import read_vision
sender_ip, ball_mm, blues, yellows = read_vision()
if sender_ip is None and not blues and not yellows:
    print("[AVISO] Nenhum pacote multicast do SSL-Vision/grSim detectado em 224.5.23.2:10020!")
    print("        Certifique-se de que o grSim está aberto antes de rodar o experimento.")
    sys.exit(2)
print(f"[OK] Visão detectada de {sender_ip} (azuis={len(blues)}, amarelos={len(yellows)}, bola={ball_mm})")
EOF

CONFIG_KEYS=("A" "B" "C")
declare -A CONFIG_YAMLS=(
    ["A"]="experiments/configs/e1_a_unprotected.yaml"
    ["B"]="experiments/configs/e1_b_preemption_only.yaml"
    ["C"]="experiments/configs/e1_c_full.yaml"
)

for cfg in "${CONFIG_KEYS[@]}"; do
    yaml_path="${CONFIG_YAMLS[$cfg]}"
    out_dir="${WS_DIR}/experiments/results/e1/${cfg}"
    mkdir -p "${out_dir}"

    for ((run_idx=1; run_idx<=REPS; run_idx++)); do
        run_tag=$(printf "%02d" "${run_idx}")
        csv_out="${out_dir}/run_${run_tag}.csv"
        events_out="${out_dir}/run_${run_tag}_events.csv"

        echo ""
        echo "------------------------------------------------------------------"
        echo " [E1] Configuração ${cfg} (${yaml_path}) — Execução ${run_tag}/${REPS}"
        echo "------------------------------------------------------------------"

        cleanup_round

        # 1. Sobe a stack ROS 2
        if [ "${MATCH_MODE}" = true ]; then
            ROS_DOMAIN_ID=0 ros2 launch oxebots_bringup ssl-new.launch.py \
                match:=True rviz_team:=none require_gc:=True \
                config_file:="${WS_DIR}/${yaml_path}" > "/tmp/e1_launch_${cfg}_${run_tag}.log" 2>&1 &
        else
            ROS_DOMAIN_ID=0 ros2 launch oxebots_bringup ssl-new.launch.py \
                team_color:=blue use_rviz:=False require_gc:=True \
                config_file:="${WS_DIR}/${yaml_path}" > "/tmp/e1_launch_${cfg}_${run_tag}.log" 2>&1 &
        fi
        LAUNCH_PID=$!

        # Aguarda os nós inicializarem e /game_data começar a publicar
        sleep 4

        # 2. Inicia o logger CSV (40 s para cobrir o roteiro de 38 s)
        ROS_DOMAIN_ID=0 python3 "${WS_DIR}/experiments/benchmark_logger.py" \
            --output "${csv_out}" \
            --duration 40 &
        LOGGER_PID=$!

        # 3. Executa o cenário determinístico (38 s)
        ROS_DOMAIN_ID=0 python3 "${WS_DIR}/experiments/e1/e1_scenario.py" \
            --events-output "${events_out}"
        SCENARIO_PID=""

        # Aguarda o logger finalizar
        wait "${LOGGER_PID}" 2>/dev/null || true
        LOGGER_PID=""

        # 4. Encerra de forma limpa a rodada atual
        cleanup_round
        sleep 1
    done
done

echo ""
echo "=================================================================="
echo " RESUMO COMPARATIVO DO EXPERIMENTO E1 (A vs. B vs. C)"
echo "=================================================================="

python3 - << 'EOF'
import csv
import glob
from pathlib import Path
import statistics

base_dir = Path("experiments/results/e1")
configs = ["A", "B", "C"]

header = (
    f"{'CFG':<4} | {'TICKS':<7} | {'VIOL_STOP':<9} | {'STOP(>1s)':<9} | {'CMD>0.75':<8} | "
    f"{'MEAS>0.75':<9} | {'MAX_V_STOP':<10} | {'VIOL_AREA':<9} | {'VIOL_BALL':<9} | "
    f"{'BALL(>2s)':<9} | {'HALT_LAT_MS':<11}"
)
print(header)
print("-" * len(header))

for cfg in configs:
    run_files = sorted(glob.glob(str(base_dir / cfg / "run_[0-9][0-9].csv")))
    if not run_files:
        print(f"{cfg:<4} | (sem arquivos coletados)")
        continue

    total_rows = 0
    viol_stop = 0
    viol_stop_after_1s = 0
    cmd_over_stop = 0
    meas_over_stop = 0
    max_v_stop = 0.0
    viol_area = 0
    viol_ball = 0
    viol_ball_after_2s = 0
    halt_latencies_ms = []

    for rf in run_files:
        rf_path = Path(rf)
        ev_path = rf_path.with_name(rf_path.stem + "_events.csv")

        np1_ts = None
        stop_ts = None
        np2_ts = None
        halt_ts = None
        if ev_path.is_file():
            with open(ev_path, newline="", encoding="utf-8") as ef:
                for row in csv.DictReader(ef):
                    ev_name = row.get("event_name")
                    if ev_name in ("NORMAL_PLAY_1", "NORMAL_PLAY"):
                        np1_ts = int(row["timestamp_ms"])
                    elif ev_name == "STOP":
                        stop_ts = int(row["timestamp_ms"])
                    elif ev_name == "NORMAL_PLAY_2":
                        np2_ts = int(row["timestamp_ms"])
                    elif ev_name == "HALT":
                        halt_ts = int(row["timestamp_ms"])

        # Rastreia latência de HALT individualmente por robot_id que estava em movimento antes do HALT
        had_motion_by_robot = {}
        first_zero_by_robot = {}
        prev_state = None
        phase_start_ts = None

        with open(rf_path, newline="", encoding="utf-8") as cf:
            for row in csv.DictReader(cf):
                total_rows += 1
                ts = int(row["timestamp_ms"])
                rid = row["robot_id"]
                state = row["gc_state"]
                v_cmd = float(row["v_cmd"])
                v_meas = float(row["v_meas"])

                if state != prev_state:
                    phase_start_ts = ts
                    prev_state = state

                # Ignora a janela inicial de setup (HALT 1s + INIT_STOP 2s antes do NORMAL_PLAY_1)
                if np1_ts is not None and ts < np1_ts:
                    continue

                # Tempo relativo ao início do STOP principal (ou à transição de estado no CSV)
                if state == "STOP" and stop_ts is not None and ts >= stop_ts:
                    rel_phase_ms = ts - stop_ts
                else:
                    rel_phase_ms = (ts - phase_start_ts) if phase_start_ts is not None else 0

                v_stop_flag = int(row["viol_speed_stop"])
                v_ball_flag = int(row["viol_ball_radius"])
                viol_stop += v_stop_flag
                viol_area += int(row["viol_defense_area"])
                viol_ball += v_ball_flag

                if v_stop_flag and rel_phase_ms > 1000:
                    viol_stop_after_1s += 1
                if v_ball_flag and rel_phase_ms > 2000:
                    viol_ball_after_2s += 1

                if state == "STOP":
                    if v_cmd > 0.751:
                        cmd_over_stop += 1
                    if v_meas > 0.751:
                        meas_over_stop += 1
                    max_v_stop = max(max_v_stop, v_cmd, v_meas)

                if halt_ts is not None:
                    halt_end = halt_ts + 5000
                    if halt_ts - 600 <= ts < halt_ts and v_cmd > 0.05:
                        had_motion_by_robot[rid] = True
                    elif halt_ts <= ts < halt_end and rid not in first_zero_by_robot:
                        if v_cmd <= 1e-3:
                            first_zero_by_robot[rid] = ts - halt_ts

        if halt_ts is not None:
            halt_window = 5000
            for rid, was_moving in had_motion_by_robot.items():
                if was_moving:
                    lat = first_zero_by_robot.get(rid, halt_window)
                    halt_latencies_ms.append(float(lat))

    mean_halt_lat = (
        f"{statistics.mean(halt_latencies_ms):.1f} ms"
        if halt_latencies_ms
        else "N/A"
    )
    print(
        f"{cfg:<4} | {total_rows:<7} | {viol_stop:<9} | {viol_stop_after_1s:<9} | {cmd_over_stop:<8} | "
        f"{meas_over_stop:<9} | {max_v_stop:<10.3f} | {viol_area:<9} | {viol_ball:<9} | "
        f"{viol_ball_after_2s:<9} | {mean_halt_lat:<11}"
    )

print("-" * len(header))
EOF
