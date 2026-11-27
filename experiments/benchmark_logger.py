#!/usr/bin/env python3
"""Logger CSV desacoplado para experimentos e ablações do OxeBots.

Assina:
  - /game_state (oxebots_interfaces/msg/GameState)
  - /role_assignment (oxebots_interfaces/msg/RoleAssignment)
  - /game_data (oxebots_interfaces/msg/GameData)
  - /field_geometry (oxebots_interfaces/msg/SSLGeometryData)
  - /robot_commands (oxebots_interfaces/msg/RobotCmd)
  - /strategy/tick_duration_us (std_msgs/msg/Int64)

Grava CSV com cabeçalho:
  timestamp_ms,tick_duration_us,gc_state,active_robots_count,robot_id,role,x,y,v_cmd,v_meas,viol_speed_stop,viol_defense_area,viol_ball_radius,ghost_cmd
"""

import argparse
import csv
import math
from pathlib import Path
import sys
import time

from oxebots_interfaces.msg import (
    GameData,
    GameState,
    RobotCmd,
    RoleAssignment,
    SSLGeometryData,
)
import rclpy
from rclpy.node import Node
from rclpy.qos import (
    DurabilityPolicy,
    HistoryPolicy,
    QoSProfile,
    ReliabilityPolicy,
    qos_profile_sensor_data,
)
from std_msgs.msg import Int64


PHASE_NAMES = {
    GameState.PHASE_HALT: 'HALT',
    GameState.PHASE_TIMEOUT: 'TIMEOUT',
    GameState.PHASE_STOP: 'STOP',
    GameState.PHASE_BALL_PLACEMENT: 'BALL_PLACEMENT',
    GameState.PHASE_PREPARE_KICKOFF: 'PREPARE_KICKOFF',
    GameState.PHASE_KICKOFF: 'KICKOFF',
    GameState.PHASE_PREPARE_PENALTY: 'PREPARE_PENALTY',
    GameState.PHASE_PENALTY: 'PENALTY',
    GameState.PHASE_FREE_KICK: 'FREE_KICK',
    GameState.PHASE_RUN: 'RUN',
}


class BenchmarkLoggerNode(Node):
    """Nó ROS 2 de logging CSV para avaliação de segurança, reatividade e alocação."""

    def __init__(self, output_path: Path, duration_s: float):
        super().__init__('benchmark_logger_node')
        self.output_path = output_path
        self.duration_s = duration_s
        self.start_monotonic = time.monotonic()

        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.csv_file = open(self.output_path, 'w', newline='', encoding='utf-8')
        self.writer = csv.writer(self.csv_file)
        self.writer.writerow([
            'timestamp_ms',
            'tick_duration_us',
            'gc_state',
            'active_robots_count',
            'robot_id',
            'role',
            'x',
            'y',
            'v_cmd',
            'v_meas',
            'viol_speed_stop',
            'viol_defense_area',
            'viol_ball_radius',
            'ghost_cmd',
        ])
        self.csv_file.flush()

        # Estado cacheado
        self.last_game_state = None
        self.last_roles = None
        self.last_game_data = None
        self.last_tick_duration_us = 0

        # Geometria padrão SSL-EL (em mm) até /field_geometry chegar
        self.field_length_mm = 4500.0
        self.field_width_mm = 3000.0
        self.penalty_depth_mm = 500.0
        self.penalty_width_mm = 1350.0

        # Histórico para derivada de velocidade medida (v_meas em m/s) e últimos comandos (v_cmd)
        self.robot_pos_history = {}  # robot_id -> list of (x_mm, y_mm, t_sec)
        self.robot_v_window = {}     # robot_id -> list of recent raw speeds (for median filter)
        self.robot_v_meas = {}       # robot_id -> float (m/s)
        self.last_cmd_by_id = {}     # robot_id -> (v_cmd_mps, ang_vel, kick_speed, t_monotonic)

        latched_qos = QoSProfile(
            history=HistoryPolicy.KEEP_LAST,
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
        )

        self.create_subscription(GameState, '/game_state', self._on_game_state, latched_qos)
        self.create_subscription(RoleAssignment, '/role_assignment', self._on_roles, latched_qos)
        self.create_subscription(SSLGeometryData, '/field_geometry', self._on_geometry, latched_qos)
        self.create_subscription(GameData, '/game_data', self._on_game_data, 10)
        self.create_subscription(
            RobotCmd, '/robot_commands', self._on_robot_commands, qos_profile_sensor_data
        )
        self.create_subscription(Int64, '/strategy/tick_duration_us', self._on_tick_duration, 10)

        # Timer de verificação de duração (20 Hz)
        self.finished = False
        self._timer = self.create_timer(0.05, self._check_duration)

    def _on_game_state(self, msg: GameState):
        self.last_game_state = msg

    def _on_roles(self, msg: RoleAssignment):
        self.last_roles = msg

    def _on_geometry(self, msg: SSLGeometryData):
        if msg.field.field_length > 0:
            self.field_length_mm = float(msg.field.field_length)
        if msg.field.field_width > 0:
            self.field_width_mm = float(msg.field.field_width)
        if msg.field.penalty_area_depth > 0:
            self.penalty_depth_mm = float(msg.field.penalty_area_depth)
        if msg.field.penalty_area_width > 0:
            self.penalty_width_mm = float(msg.field.penalty_area_width)

    def _on_tick_duration(self, msg: Int64):
        self.last_tick_duration_us = int(msg.data)

    def _on_robot_commands(self, msg: RobotCmd):
        now_m = time.monotonic()
        for rcmd in msg.robots:
            rid = int(rcmd.id)
            v_cmd = math.hypot(float(rcmd.x_velocity), float(rcmd.y_velocity))
            self.last_cmd_by_id[rid] = (
                v_cmd,
                float(rcmd.angular_velocity),
                float(rcmd.kick_speed),
                now_m,
            )

        # Se algum comando foi emitido para um robô invisível/ausente de game_data, registra ghost_cmd
        if self.last_game_data is not None:
            active_set = {int(r.id) for r in self.last_game_data.robots.allies}
            for rcmd in msg.robots:
                rid = int(rcmd.id)
                if rid not in active_set:
                    v_cmd = math.hypot(float(rcmd.x_velocity), float(rcmd.y_velocity))
                    has_motion = (
                        v_cmd > 1e-3
                        or abs(float(rcmd.angular_velocity)) > 1e-3
                        or float(rcmd.kick_speed) > 1e-3
                    )
                    if has_motion:
                        self._write_row(
                            robot_id=rid,
                            x_mm=float('nan'),
                            y_mm=float('nan'),
                            v_cmd=v_cmd,
                            v_meas=0.0,
                            active_count=len(active_set),
                            is_active=False,
                            ghost_cmd=1,
                        )

    def _on_game_data(self, msg: GameData):
        now_m = time.monotonic()
        self.last_game_data = msg
        allies = list(msg.robots.allies)
        active_count = len(allies)
        active_set = {int(r.id) for r in allies}

        for ally in allies:
            rid = int(ally.id)
            x_mm = float(ally.x)
            y_mm = float(ally.y)

            # Usa o timestamp de detecção do próprio robô (ally.stamp) se preenchido,
            # com fallback para msg.header.stamp ou relógio monotônico
            t_frame = now_m
            if hasattr(ally, 'stamp') and (ally.stamp.sec > 0 or ally.stamp.nanosec > 0):
                t_frame = float(ally.stamp.sec) + float(ally.stamp.nanosec) * 1e-9
            elif hasattr(msg, 'header') and (msg.header.stamp.sec > 0 or msg.header.stamp.nanosec > 0):
                t_frame = float(msg.header.stamp.sec) + float(msg.header.stamp.nanosec) * 1e-9

            v_meas = self.robot_v_meas.get(rid, 0.0)
            hist = self.robot_pos_history.setdefault(rid, [])
            v_win = self.robot_v_window.setdefault(rid, [])

            if hist:
                last_x, last_y, last_t = hist[-1]
                dt_last = t_frame - last_t
                if dt_last < -1.0 or dt_last > 1.0:
                    # Salto de relógio / reinício
                    hist.clear()
                    v_win.clear()
                    hist.append((x_mm, y_mm, t_frame))
                    v_meas = 0.0
                elif (x_mm != last_x or y_mm != last_y) and dt_last >= 0.004:
                    hist.append((x_mm, y_mm, t_frame))
                    if len(hist) > 5:
                        hist.pop(0)
                    # Calcula velocidade em janela de >= 45 ms (~3 frames) para eliminar jitter
                    # quando dois pacotes UDP do SSL-Vision chegam agrupados
                    anchor_x, anchor_y, anchor_t = hist[0]
                    for hx, hy, ht in reversed(hist[:-1]):
                        if (t_frame - ht) >= 0.045:
                            anchor_x, anchor_y, anchor_t = hx, hy, ht
                            break
                    dt_span = t_frame - anchor_t
                    if dt_span >= 0.025:
                        raw_v = math.hypot(x_mm - anchor_x, y_mm - anchor_y) / dt_span / 1000.0
                        if raw_v > 6.0:
                            # Teleporte no simulador: reseta janela de velocidade
                            hist.clear()
                            v_win.clear()
                            hist.append((x_mm, y_mm, t_frame))
                            v_meas = 0.0
                        else:
                            v_win.append(raw_v)
                            if len(v_win) > 3:
                                v_win.pop(0)
                            sorted_w = sorted(v_win)
                            median_v = sorted_w[len(sorted_w) // 2]
                            v_meas = 0.6 * median_v + 0.4 * v_meas
                elif dt_last > 0.12:
                    v_meas = 0.0
                    v_win.clear()
                    hist.clear()
                    hist.append((x_mm, y_mm, t_frame))
            else:
                hist.append((x_mm, y_mm, t_frame))

            self.robot_v_meas[rid] = v_meas

            v_cmd = 0.0
            if rid in self.last_cmd_by_id:
                cmd_v, _, _, cmd_t = self.last_cmd_by_id[rid]
                if (now_m - cmd_t) <= 0.25:
                    v_cmd = cmd_v

            self._write_row(
                robot_id=rid,
                x_mm=x_mm,
                y_mm=y_mm,
                v_cmd=v_cmd,
                v_meas=v_meas,
                active_count=active_count,
                is_active=True,
                ghost_cmd=0,
            )

        # Verifica robôs que têm papel ativo atribuído mas sumiram da visão e continuam recebendo comando
        for rid, (cmd_v, cmd_w, cmd_k, cmd_t) in list(self.last_cmd_by_id.items()):
            if rid not in active_set and (now_m - cmd_t) <= 0.10:
                if cmd_v > 1e-3 or abs(cmd_w) > 1e-3 or cmd_k > 1e-3:
                    self._write_row(
                        robot_id=rid,
                        x_mm=float('nan'),
                        y_mm=float('nan'),
                        v_cmd=cmd_v,
                        v_meas=0.0,
                        active_count=active_count,
                        is_active=False,
                        ghost_cmd=1,
                    )

    def _resolve_role(self, robot_id: int) -> str:
        if self.last_roles is None:
            return 'idle'
        if robot_id == int(self.last_roles.goalkeeper_id):
            return 'goalkeeper'
        if robot_id == int(self.last_roles.attacker_id):
            return 'attacker'
        if robot_id == int(self.last_roles.defender_id):
            return 'defender'
        return 'idle'

    def _resolve_gc_state(self) -> str:
        if self.last_game_state is None:
            return 'UNKNOWN'
        return PHASE_NAMES.get(int(self.last_game_state.phase), 'UNKNOWN')

    def _check_defense_area_violation(self, robot_id: int, role: str, x_mm: float, y_mm: float) -> int:
        if math.isnan(x_mm) or math.isnan(y_mm):
            return 0
        half_len = self.field_length_mm / 2.0
        area_x_limit = half_len - self.penalty_depth_mm
        area_y_limit = self.penalty_width_mm / 2.0

        our_positive = False
        gk_id = 0
        if self.last_game_state is not None:
            our_positive = bool(self.last_game_state.our_goal_positive_x)
            gk_id = int(self.last_game_state.our_goalkeeper_id)
        elif self.last_roles is not None and self.last_roles.goalkeeper_id != RoleAssignment.NO_ROBOT:
            gk_id = int(self.last_roles.goalkeeper_id)

        is_gk = (robot_id == gk_id) or (role == 'goalkeeper')

        in_pos_area = (x_mm > area_x_limit) and (abs(y_mm) < area_y_limit)
        in_neg_area = (x_mm < -area_x_limit) and (abs(y_mm) < area_y_limit)

        if in_pos_area:
            if not (is_gk and our_positive):
                return 1
        if in_neg_area:
            if not (is_gk and not our_positive):
                return 1
        return 0

    def _check_ball_radius_violation(self, gc_state: str, x_mm: float, y_mm: float) -> int:
        if math.isnan(x_mm) or math.isnan(y_mm) or self.last_game_data is None:
            return 0
        min_dist_mm = 0.0
        if self.last_game_state is not None:
            if self.last_game_state.ball_min_distance_mm > 0.0:
                min_dist_mm = float(self.last_game_state.ball_min_distance_mm)
            elif gc_state == 'STOP':
                min_dist_mm = 500.0
        elif gc_state == 'STOP':
            min_dist_mm = 500.0

        if min_dist_mm <= 0.0:
            return 0

        bx = float(self.last_game_data.ball.x)
        by = float(self.last_game_data.ball.y)
        dist_mm = math.hypot(x_mm - bx, y_mm - by)
        return 1 if dist_mm < min_dist_mm else 0

    def _write_row(
        self,
        robot_id: int,
        x_mm: float,
        y_mm: float,
        v_cmd: float,
        v_meas: float,
        active_count: int,
        is_active: bool,
        ghost_cmd: int,
    ):
        timestamp_ms = int(time.time() * 1000)
        gc_state = self._resolve_gc_state()
        role = self._resolve_role(robot_id)

        # Limiar da regra SSL-EL: viol_speed_stop = 1 se em STOP e velocidade > 0.75 m/s
        # (tolerância de 1e-3 m/s para evitar falso positivo por arredondamento float32 de 0.75f)
        viol_speed_stop = 1 if (gc_state == 'STOP' and (v_cmd > 0.751 or v_meas > 0.751)) else 0
        viol_defense_area = (
            self._check_defense_area_violation(robot_id, role, x_mm, y_mm) if is_active else 0
        )
        viol_ball_radius = (
            self._check_ball_radius_violation(gc_state, x_mm, y_mm) if is_active else 0
        )

        x_str = f'{x_mm:.2f}' if not math.isnan(x_mm) else 'NaN'
        y_str = f'{y_mm:.2f}' if not math.isnan(y_mm) else 'NaN'

        self.writer.writerow([
            timestamp_ms,
            self.last_tick_duration_us,
            gc_state,
            active_count,
            robot_id,
            role,
            x_str,
            y_str,
            f'{v_cmd:.4f}',
            f'{v_meas:.4f}',
            viol_speed_stop,
            viol_defense_area,
            viol_ball_radius,
            ghost_cmd,
        ])

    def _check_duration(self):
        if not self.finished and (time.monotonic() - self.start_monotonic) >= self.duration_s:
            self.finished = True

    def stop_timers(self):
        if self._timer is not None:
            try:
                self.destroy_timer(self._timer)
            except Exception:
                pass
            self._timer = None

    def close(self):
        if self.csv_file and not self.csv_file.closed:
            self.csv_file.flush()
            self.csv_file.close()


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description='Logger CSV desacoplado de benchmark do OxeBots')
    parser.add_argument(
        '--output',
        type=Path,
        required=True,
        help='Caminho do arquivo CSV de saída (ex.: experiments/results/run.csv)',
    )
    parser.add_argument(
        '--duration',
        type=float,
        required=True,
        help='Duração da coleta em segundos',
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    rclpy.init(args=argv)
    node = BenchmarkLoggerNode(output_path=args.output, duration_s=args.duration)
    try:
        while rclpy.ok() and not node.finished:
            rclpy.spin_once(node, timeout_sec=0.05)
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        # 1. Cancela timers
        node.stop_timers()
        # 2. Salva e fecha o CSV
        node.close()
        # 3. Destrói o nó e desliga o ROS 2
        try:
            node.destroy_node()
        except Exception:
            pass
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main(sys.argv[1:])
