#!/usr/bin/env bash
# ==============================================================================
# Runner em Lote do Experimento E2 (Ablação da Histerese Dupla e Lock-In)
#
# Uso:
#   ./experiments/e2/run_e2.sh [N]
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
        echo "[E2] Redirecionando execução para o DevContainer ($CONTAINER_NAME)..."
        exec docker exec "$CONTAINER_NAME" bash -c "cd /software_ws && /software_ws/experiments/e2/run_e2.sh $*"
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
    pkill -f "e2_scenario.py" 2>/dev/null || true
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

if cov_s < 52.0 or max_gap_s >= 1.5:
    print(f"cobertura={cov_s:.2f}s (<52s) ou max_gap={max_gap_s:.2f}s (>=1.5s)")
    sys.exit(1)

print(f"cobertura={cov_s:.2f}s, max_gap={max_gap_s:.2f}s")
sys.exit(0)
PYEOF
}

check_grsim_alive() {
    python3 - << 'PYEOF'
import sys
import time
from experiments.e2.e2_scenario import read_vision

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
echo " Experimento E2 — Ablação da Histerese Dupla e Análise de Lock-In"
echo "  - Repetições (N): ${REPS}"
echo "=================================================================="

if ! check_grsim_alive; then
    echo "[ERRO] grSim parou de enviar visão — reinicie o grSim" >&2
    exit 2
fi
echo "[OK] Fluxo multicast do SSL-Vision/grSim confirmado (224.5.23.2:10020)."

CONFIG_KEYS=("greedy" "cost_only" "time_only" "dual_calibrated" "dual_legacy")
declare -A CONFIG_YAMLS=(
    ["greedy"]="experiments/configs/e2_0_greedy.yaml"
    ["cost_only"]="experiments/configs/e2_1_cost_only.yaml"
    ["time_only"]="experiments/configs/e2_2_time_only.yaml"
    ["dual_calibrated"]="experiments/configs/e2_3_dual_calibrated.yaml"
    ["dual_legacy"]="experiments/configs/e2_4_dual_legacy.yaml"
)

MAX_EXTRA_RETRIES=2

for cfg in "${CONFIG_KEYS[@]}"; do
    yaml_path="${CONFIG_YAMLS[$cfg]}"
    out_dir="${WS_DIR}/experiments/results/e2/${cfg}"
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
            echo " [E2] Configuração ${cfg} (${yaml_path}) — Execução ${run_tag}/${REPS} (tentativa ${attempt}/$((MAX_EXTRA_RETRIES + 1)))"
            echo "------------------------------------------------------------------"

            cleanup_round

            # 1. Sobe a stack ROS 2 headless (time azul)
            ROS_DOMAIN_ID=0 ros2 launch oxebots_bringup ssl-new.launch.py \
                team_color:=blue use_rviz:=False require_gc:=True \
                config_file:="${WS_DIR}/${yaml_path}" > "/tmp/e2_launch_${cfg}_${run_tag}.log" 2>&1 &
            LAUNCH_PID=$!

            sleep 4

            # 2. Inicia o logger CSV (62 s para cobrir o roteiro de ~59 s)
            ROS_DOMAIN_ID=0 python3 "${WS_DIR}/experiments/benchmark_logger.py" \
                --output "${csv_out}" \
                --duration 62 &
            LOGGER_PID=$!

            # 3. Executa o cenário determinístico (~59 s)
            ROS_DOMAIN_ID=0 python3 "${WS_DIR}/experiments/e2/e2_scenario.py" \
                --events-output "${events_out}"
            SCENARIO_PID=""

            wait "${LOGGER_PID}" 2>/dev/null || true
            LOGGER_PID=""

            cleanup_round
            sleep 1

            # 4. Guarda de integridade contra queda de visão ((t_max - t_min) >= 52 s e max_gap < 1.5 s)
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
echo "====================================================================================================================="
echo " RESUMO COMPARATIVO DO EXPERIMENTO E2 (Histerese Dupla: Custo vs. Tempo e Lock-In)"
echo "====================================================================================================================="

python3 - << 'EOF'
import csv
import glob
import math
from pathlib import Path
import statistics

base_dir = Path("experiments/results/e2")
configs = ["greedy", "cost_only", "time_only", "dual_calibrated", "dual_legacy"]

header = (
    f"{'CONFIG':<16} | {'SW_P1':<6} | {'SW/MIN':<7} | {'DIST_P1(m)':<10} | "
    f"{'MOD_OK':<6} | {'MOD_LAT_MS':<11} | {'MOD_T_BALL_MS':<13} | "
    f"{'LRG_LAT_MS':<11} | {'REV_OK':<6} | {'REV_LAT_MS':<11}"
)
print(header)
print("-" * len(header))

for cfg in configs:
    run_files = sorted(glob.glob(str(base_dir / cfg / "run_[0-9][0-9].csv")))
    if not run_files:
        print(f"{cfg:<16} | (sem arquivos coletados)")
        continue

    sw_p1_list = []
    sw_rate_list = []
    dist_p1_list = []
    mod_ok_count = 0
    mod_lat_list = []
    mod_t_ball_list = []
    lrg_lat_list = []
    rev_ok_count = 0
    rev_lat_list = []

    for rf in run_files:
        rf_path = Path(rf)
        ev_path = rf_path.with_name(rf_path.stem + "_events.csv")

        ev_map = {}
        mod_def_id = "2"
        lrg_def_id = "2"
        rev_def_id = None
        if ev_path.is_file():
            with open(ev_path, newline="", encoding="utf-8") as ef:
                for row in csv.DictReader(ef):
                    ename = row.get("event_name", "")
                    ev_map[ename] = int(row["timestamp_ms"])
                    if ename.startswith("LEGIT_SWITCH_MODERATE_ATT_") and "_DEF_" in ename:
                        mod_def_id = ename.split("_DEF_")[-1]
                    elif ename.startswith("LEGIT_SWITCH_LARGE_ATT_") and "_DEF_" in ename:
                        lrg_def_id = ename.split("_DEF_")[-1]
                        if rev_def_id is None:
                            rev_def_id = ename.split("LEGIT_SWITCH_LARGE_ATT_")[-1].split("_DEF_")[0]
                    elif ename.startswith("LEGIT_REVERSAL_08S_ATT_") and "_DEF_" in ename:
                        rev_def_id = ename.split("_DEF_")[-1]

        if rev_def_id is None:
            rev_def_id = "1" if lrg_def_id == "2" else "2"

        t_p1 = ev_map.get("PHASE1_EPISODE_1", ev_map.get("PHASE1_CHATTERING"))
        t_mod = ev_map.get("LEGIT_SWITCH_MODERATE")
        t_lrg = ev_map.get("LEGIT_SWITCH_LARGE")
        t_rev = ev_map.get("LEGIT_REVERSAL_08S")

        rows = list(csv.DictReader(open(rf_path, newline="", encoding="utf-8")))
        if not rows:
            continue

        if t_p1 is None:
            t_p1 = int(rows[0]["timestamp_ms"])
        if t_mod is None:
            t_mod = t_p1 + 30000
        if t_lrg is None:
            t_lrg = t_mod + 12000
        if t_rev is None:
            t_rev = t_lrg + 800

        t_p1_eval_end = t_mod
        p1_attacker_prev = None
        sw_p1 = 0
        prev_pos_p1 = {}
        dist_p1_m = 0.0

        mod_switch_lat = None
        mod_t_ball = None
        lrg_switch_lat = None
        rev_switch_lat = None

        # Posições iniciais da bola nas fases 2A e 2B-1 (em mm)
        mod_bx_mm, mod_by_mm = 1350.0, -350.0
        lrg_bx_mm, lrg_by_mm = 1100.0, -400.0
        mod_started_far = set()

        for row in rows:
            ts = int(row["timestamp_ms"])
            rid = row["robot_id"]
            role = row["role"]
            try:
                x_mm = float(row["x"])
                y_mm = float(row["y"])
            except ValueError:
                x_mm, y_mm = float("nan"), float("nan")

            # Fase 1: contagem de trocas de atacante e distância física percorrida pelos robôs de linha
            if t_p1 <= ts < t_p1_eval_end:
                if role == "attacker":
                    if p1_attacker_prev is not None and rid != p1_attacker_prev:
                        sw_p1 += 1
                    p1_attacker_prev = rid

                if rid in ("1", "2") and not (math.isnan(x_mm) or math.isnan(y_mm)):
                    if rid in prev_pos_p1:
                        px, py = prev_pos_p1[rid]
                        step_m = math.hypot(x_mm - px, y_mm - py) / 1000.0
                        # Ignora reposicionamento entre os 5 episódios (> 0.25 m num único frame)
                        if step_m < 0.25:
                            dist_p1_m += step_m
                    prev_pos_p1[rid] = (x_mm, y_mm)

            # Fase 2A (12 s livres): troca legítima moderada (0.60 < ΔC = 1.30 < 2.50)
            # e tempo até algum robô azul chegar a < 250 mm da bola (após confirmar que começou a > 300 mm)
            if t_mod <= ts < t_lrg:
                dist_mod_ball = (
                    math.hypot(x_mm - mod_bx_mm, y_mm - mod_by_mm)
                    if not (math.isnan(x_mm) or math.isnan(y_mm))
                    else float("inf")
                )
                if rid in ("1", "2") and dist_mod_ball > 300.0:
                    mod_started_far.add(rid)
                if (
                    mod_t_ball is None
                    and rid in mod_started_far
                    and dist_mod_ball < 250.0
                ):
                    mod_t_ball = ts - t_mod
                if (
                    mod_switch_lat is None
                    and rid == mod_def_id
                    and role == "attacker"
                    and dist_mod_ball > 165.0
                ):
                    mod_switch_lat = ts - t_mod

            # Fase 2B-1 (0.8 s): troca legítima ampla antes do rebote
            if t_lrg <= ts < t_rev:
                dist_lrg_ball = (
                    math.hypot(x_mm - lrg_bx_mm, y_mm - lrg_by_mm)
                    if not (math.isnan(x_mm) or math.isnan(y_mm))
                    else float("inf")
                )
                if (
                    lrg_switch_lat is None
                    and rid == lrg_def_id
                    and role == "attacker"
                    and dist_lrg_ball > 165.0
                ):
                    lrg_switch_lat = ts - t_lrg

            # Fase 2B-2 (após t_rev = t_lrg + 0.8 s): rebote de bola a 0.45 m do novo defensor
            if t_rev <= ts <= t_lrg + 14000:
                if (
                    rev_switch_lat is None
                    and rid == rev_def_id
                    and role == "attacker"
                ):
                    rev_switch_lat = ts - t_rev

        p1_dur_min = max(1e-3, (t_p1_eval_end - t_p1) / 60000.0)
        sw_p1_list.append(sw_p1)
        sw_rate_list.append(sw_p1 / p1_dur_min)
        dist_p1_list.append(dist_p1_m)

        if mod_switch_lat is not None:
            mod_ok_count += 1
            mod_lat_list.append(float(mod_switch_lat))
        if mod_t_ball is not None:
            mod_t_ball_list.append(float(mod_t_ball))
        if lrg_switch_lat is not None:
            lrg_lat_list.append(float(lrg_switch_lat))
        if rev_switch_lat is not None:
            rev_ok_count += 1
            rev_lat_list.append(float(rev_switch_lat))

    n_runs = len(run_files)
    mean_sw = statistics.mean(sw_p1_list) if sw_p1_list else 0.0
    mean_rate = statistics.mean(sw_rate_list) if sw_rate_list else 0.0
    mean_dist = statistics.mean(dist_p1_list) if dist_p1_list else 0.0
    mod_ok_str = "YES" if mod_ok_count == n_runs else ("NO" if mod_ok_count == 0 else f"{mod_ok_count}/{n_runs}")
    mod_lat_str = f"{statistics.mean(mod_lat_list):.1f} ms" if mod_lat_list else "LOCK-IN"
    mod_t_ball_str = f"{statistics.mean(mod_t_ball_list):.1f} ms" if mod_t_ball_list else "TIMEOUT"
    lrg_lat_str = f"{statistics.mean(lrg_lat_list):.1f} ms" if lrg_lat_list else "TIMEOUT"
    rev_ok_str = "YES" if rev_ok_count == n_runs else ("NO" if rev_ok_count == 0 else f"{rev_ok_count}/{n_runs}")
    rev_lat_str = f"{statistics.mean(rev_lat_list):.1f} ms" if rev_lat_list else "TIMEOUT"

    print(
        f"{cfg:<16} | {mean_sw:<6.1f} | {mean_rate:<7.1f} | {mean_dist:<10.2f} | "
        f"{mod_ok_str:<6} | {mod_lat_str:<11} | {mod_t_ball_str:<13} | "
        f"{lrg_lat_str:<11} | {rev_ok_str:<6} | {rev_lat_str:<11}"
    )

print("-" * len(header))
EOF
