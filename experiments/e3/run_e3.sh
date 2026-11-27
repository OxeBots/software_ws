#!/usr/bin/env bash
# ==============================================================================
# Runner em Lote do Experimento E3 (Tolerância a Falhas: 3 -> 2 -> 1 Robôs)
#
# Uso:
#   ./experiments/e3/run_e3.sh [N]
#
# Argumentos:
#   N   Número de repetições por configuração (padrão: 1)
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
        echo "[E3] Redirecionando execução para o DevContainer ($CONTAINER_NAME)..."
        exec docker exec "$CONTAINER_NAME" bash -c "cd /software_ws && /software_ws/experiments/e3/run_e3.sh $*"
    fi
fi

REPS=1

for arg in "$@"; do
    case "$arg" in
        -h|--help)
            echo "Uso: $0 [N_REPETICOES]"
            echo "  N_REPETICOES  Número de rodadas por configuração (default: 1)"
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
    pkill -f "e3_scenario.py" 2>/dev/null || true
    LAUNCH_PID=""
    LOGGER_PID=""
    SCENARIO_PID=""
}

validate_csv_coverage() {
    local csv_file="$1"
    python3 - "$csv_file" << 'PYEOF'
import csv
import sys
from pathlib import Path

p = Path(sys.argv[1])
if not p.is_file():
    print("arquivo ausente")
    sys.exit(1)

ts_list = []
with open(p, newline="", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        try:
            ts_list.append(int(r["timestamp_ms"]))
        except Exception:
            pass

if len(ts_list) < 100:
    print(f"amostras insuficientes ({len(ts_list)})")
    sys.exit(1)

ts_sorted = sorted(set(ts_list))
cov_s = (ts_sorted[-1] - ts_sorted[0]) / 1000.0
max_gap_s = max((b - a) / 1000.0 for a, b in zip(ts_sorted, ts_sorted[1:])) if len(ts_sorted) > 1 else 0.0

if cov_s < 55.0 or max_gap_s >= 1.5:
    print(f"cobertura={cov_s:.2f}s (<55s) ou max_gap={max_gap_s:.2f}s (>=1.5s)")
    sys.exit(1)

print(f"cobertura={cov_s:.2f}s, max_gap={max_gap_s:.2f}s")
sys.exit(0)
PYEOF
}

check_grsim_alive() {
    python3 - << 'PYEOF'
import sys
import time
from experiments.e3.e3_scenario import read_vision

deadline = time.monotonic() + 3.0
while time.monotonic() < deadline:
    sender_ip, ball_mm, blues, yellows = read_vision(timeout_s=0.25, max_packets=4)
    if sender_ip is not None or blues or yellows or ball_mm is not None:
        sys.exit(0)
    time.sleep(0.1)
sys.exit(1)
PYEOF
}

trap cleanup_round EXIT INT TERM

echo "=================================================================="
echo " Experimento E3 — Tolerância a Falhas (Degradação 3 -> 2 -> 1 Robôs)"
echo "  - Repetições (N): ${REPS}"
echo "=================================================================="

if ! check_grsim_alive; then
    echo "[ERRO] grSim parou de enviar visão — reinicie o grSim" >&2
    exit 2
fi
echo "[OK] Fluxo multicast do SSL-Vision/grSim confirmado (224.5.23.2:10020)."

CONFIG_KEYS=("static" "dynamic")
declare -A CONFIG_YAMLS=(
    ["static"]="experiments/configs/e3_static.yaml"
    ["dynamic"]="experiments/configs/e3_dynamic.yaml"
)

MAX_EXTRA_RETRIES=2

for cfg in "${CONFIG_KEYS[@]}"; do
    yaml_path="${CONFIG_YAMLS[$cfg]}"
    out_dir="${WS_DIR}/experiments/results/e3/${cfg}"
    mkdir -p "${out_dir}"

    for ((run_idx=1; run_idx<=REPS; run_idx++)); do
        run_tag=$(printf "%02d" "${run_idx}")
        csv_out="${out_dir}/run_${run_tag}.csv"
        events_out="${out_dir}/run_${run_tag}_events.csv"

        attempt=0
        while true; do
            attempt=$((attempt + 1))

            if ! check_grsim_alive; then
                echo "[ERRO] grSim parou de enviar visão — reinicie o grSim" >&2
                exit 2
            fi

            echo ""
            echo "------------------------------------------------------------------"
            echo " [E3] Configuração ${cfg} (${yaml_path}) — Execução ${run_tag}/${REPS} (tentativa ${attempt}/$((MAX_EXTRA_RETRIES + 1)))"
            echo "------------------------------------------------------------------"

            cleanup_round

            # 1. Sobe a stack ROS 2 headless (time azul)
            ROS_DOMAIN_ID=0 ros2 launch oxebots_bringup ssl-new.launch.py \
                team_color:=blue use_rviz:=False require_gc:=True \
                config_file:="${WS_DIR}/${yaml_path}" > "/tmp/e3_launch_${cfg}_${run_tag}.log" 2>&1 &
            LAUNCH_PID=$!

            sleep 4

            # 2. Inicia o logger CSV (66 s para cobrir o roteiro de ~63 s)
            ROS_DOMAIN_ID=0 python3 "${WS_DIR}/experiments/benchmark_logger.py" \
                --output "${csv_out}" \
                --duration 66 &
            LOGGER_PID=$!

            # 3. Executa o cenário determinístico (~63 s)
            ROS_DOMAIN_ID=0 python3 "${WS_DIR}/experiments/e3/e3_scenario.py" \
                --events-output "${events_out}"
            SCENARIO_PID=""

            wait "${LOGGER_PID}" 2>/dev/null || true
            LOGGER_PID=""

            cleanup_round
            sleep 1

            # 4. Guarda de integridade contra queda de visão ((t_max - t_min) >= 55 s e max_gap < 1.5 s)
            if diag_msg=$(validate_csv_coverage "${csv_out}"); then
                echo "[OK] Integridade de visão validada (${diag_msg})."
                break
            else
                if ! check_grsim_alive; then
                    echo "[ERRO] grSim parou de enviar visão — reinicie o grSim" >&2
                    exit 2
                fi
                if [ "${attempt}" -le "${MAX_EXTRA_RETRIES}" ]; then
                    echo "[WARN] Queda de visão detectada (${diag_msg}) — repetindo execução (${attempt}/${MAX_EXTRA_RETRIES})..."
                else
                    echo "[WARN] Queda de visão detectada (${diag_msg}) — limite de tentativas atingido; mantendo último CSV."
                    break
                fi
            fi
        done
    done
done

echo ""
echo "=============================================================================================================="
echo " RESUMO COMPARATIVO DO EXPERIMENTO E3 (Tolerância a Falhas: Degradação 3 -> 2 -> 1 Robôs)"
echo "=============================================================================================================="

python3 - << 'EOF'
import csv
import glob
import math
from pathlib import Path
import statistics

base_dir = Path("experiments/results/e3")
configs = ["static", "dynamic"]

header = (
    f"{'CONFIG':<10} | {'REALLOC_3_2_MS':<14} | {'ATT_COV_P2(%)':<13} | "
    f"{'T_BALL_P2_MS':<12} | {'REALLOC_2_1_OK':<14} | {'FINAL_ROLE':<10} | "
    f"{'GHOST_CMD':<9} | {'TICK_P99_US':<11}"
)
print(header)
print("-" * len(header))

def percentile(sorted_vals, pct):
    if not sorted_vals:
        return 0.0
    idx = min(len(sorted_vals) - 1, max(0, int(math.ceil((pct / 100.0) * len(sorted_vals))) - 1))
    return float(sorted_vals[idx])

for cfg in configs:
    run_files = sorted(glob.glob(str(base_dir / cfg / "run_[0-9][0-9].csv")))
    if not run_files:
        print(f"{cfg:<10} | (sem arquivos coletados)")
        continue

    realloc_3_2_list = []
    att_cov_p2_list = []
    t_ball_p2_list = []
    realloc_2_1_ok_count = 0
    final_roles = []
    ghost_cmd_list = []
    tick_p99_list = []

    for rf in run_files:
        rf_path = Path(rf)
        ev_path = rf_path.with_name(rf_path.stem + "_events.csv")

        ev_map = {}
        removed_p2 = "1"
        survivor_line = "2"
        removed_p3 = "0"
        if ev_path.is_file():
            with open(ev_path, newline="", encoding="utf-8") as ef:
                for row in csv.DictReader(ef):
                    ename = row.get("event_name", "")
                    ev_map[ename] = int(row["timestamp_ms"])
                    if ename.startswith("FAIL_3_TO_2_REMOVED_") and "_SURVIVOR_" in ename:
                        parts = ename.split("FAIL_3_TO_2_REMOVED_")[-1].split("_SURVIVOR_")
                        removed_p2, survivor_line = parts[0], parts[1]
                    elif ename.startswith("FAIL_2_TO_1_REMOVED_") and "_LAST_" in ename:
                        parts = ename.split("FAIL_2_TO_1_REMOVED_")[-1].split("_LAST_")
                        removed_p3, survivor_line = parts[0], parts[1]

        rows = list(csv.DictReader(open(rf_path, newline="", encoding="utf-8")))
        if not rows:
            continue

        t0 = int(rows[0]["timestamp_ms"])
        t_f32 = ev_map.get("FAIL_3_TO_2", t0 + 23000)
        t_f21 = ev_map.get("FAIL_2_TO_1", t_f32 + 20000)

        realloc_3_2_lat = None
        p2_timestamps = set()
        p2_att_timestamps = set()
        t_ball_p2 = None
        p2_bx_mm, p2_by_mm = 400.0, 0.0
        p2_started_far = set()

        p3_role_counts = {}
        ghost_cmd_total = 0
        ticks_us = []

        for row in rows:
            ts = int(row["timestamp_ms"])
            rid = row["robot_id"]
            role = row["role"]
            try:
                t_us = int(row["tick_duration_us"])
                if t_us > 0:
                    ticks_us.append(t_us)
            except Exception:
                pass
            try:
                x_mm = float(row["x"])
                y_mm = float(row["y"])
            except ValueError:
                x_mm, y_mm = float("nan"), float("nan")
            try:
                v_cmd = float(row["v_cmd"])
            except ValueError:
                v_cmd = 0.0
            try:
                g_flag = int(row["ghost_cmd"])
            except ValueError:
                g_flag = 0

            is_visible = not (math.isnan(x_mm) or math.isnan(y_mm))

            # Fase 2: t_f32 <= ts < t_f21
            if t_f32 <= ts < t_f21:
                if realloc_3_2_lat is None and rid == survivor_line and role == "attacker" and is_visible:
                    realloc_3_2_lat = ts - t_f32

                # Cobertura de atacante após 1 s da falha (janela de expiração de 500 ms + histerese)
                if ts >= t_f32 + 1000 and is_visible:
                    p2_timestamps.add(ts)
                    if role == "attacker":
                        p2_att_timestamps.add(ts)

                if is_visible and rid != removed_p2:
                    dist_ball = math.hypot(x_mm - p2_bx_mm, y_mm - p2_by_mm)
                    if dist_ball > 300.0:
                        p2_started_far.add(rid)
                    if t_ball_p2 is None and rid in p2_started_far and dist_ball < 250.0:
                        t_ball_p2 = ts - t_f32

            # Fase 3: ts >= t_f21 + 1000 ms (regime estabilizado com 1 robô restante)
            if ts >= t_f21 + 1000:
                if rid == survivor_line and is_visible:
                    p3_role_counts[role] = p3_role_counts.get(role, 0) + 1

            # Contagem de comandos fantasma (> 600 ms após a remoção do respectivo robô)
            if rid == removed_p2 and ts > t_f32 + 600 and (v_cmd > 0.01 or g_flag == 1):
                ghost_cmd_total += 1
            if rid == removed_p3 and ts > t_f21 + 600 and (v_cmd > 0.01 or g_flag == 1):
                ghost_cmd_total += 1

        if realloc_3_2_lat is not None:
            realloc_3_2_list.append(float(realloc_3_2_lat))

        cov_pct = (100.0 * len(p2_att_timestamps) / len(p2_timestamps)) if p2_timestamps else 0.0
        att_cov_p2_list.append(cov_pct)

        if t_ball_p2 is not None:
            t_ball_p2_list.append(float(t_ball_p2))

        if p3_role_counts:
            dominant_role = max(p3_role_counts.items(), key=lambda kv: kv[1])[0]
        else:
            dominant_role = "NONE"
        final_roles.append(dominant_role)

        # Em dynamic, 1 robô de linha sobrevivente assume attacker; em static, permanece defender
        if dominant_role == "attacker":
            realloc_2_1_ok_count += 1

        ghost_cmd_list.append(ghost_cmd_total)
        tick_p99_list.append(percentile(sorted(ticks_us), 99.0))

    n_runs = len(run_files)
    realloc_32_str = f"{statistics.mean(realloc_3_2_list):.1f} ms" if realloc_3_2_list else "NONE"
    att_cov_str = f"{statistics.mean(att_cov_p2_list):.1f}%" if att_cov_p2_list else "0.0%"
    t_ball_str = f"{statistics.mean(t_ball_p2_list):.1f} ms" if t_ball_p2_list else "TIMEOUT"
    realloc_21_str = "YES" if realloc_2_1_ok_count == n_runs else ("NO" if realloc_2_1_ok_count == 0 else f"{realloc_2_1_ok_count}/{n_runs}")
    final_role_str = final_roles[-1] if final_roles else "NONE"
    ghost_str = f"{statistics.mean(ghost_cmd_list):.1f}" if ghost_cmd_list else "0.0"
    tick_p99_str = f"{statistics.mean(tick_p99_list):.1f}" if tick_p99_list else "0.0"

    print(
        f"{cfg:<10} | {realloc_32_str:<14} | {att_cov_str:<13} | "
        f"{t_ball_str:<12} | {realloc_21_str:<14} | {final_role_str:<10} | "
        f"{ghost_str:<9} | {tick_p99_str:<11}"
    )

print("-" * len(header))
EOF
