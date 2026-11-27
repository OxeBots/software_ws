#!/usr/bin/env python3
"""Cenário determinístico do Experimento E2 (~59 s): Histerese Dupla e Lock-In.

Regra central: os robôs só são reposicionados UMA ÚNICA VEZ no início de cada episódio/fase
(velocidade zero) e depois ficam 100% livres sob controle da stack ROS 2. Durante a Fase 1 e no
rebote de 0.8 s da Fase 2B, apenas a BOLA é reposicionada/impulsionada (sem tocar nos robôs), com
rate-limit rígido e checagem anti-colisão para nunca estourar o solver ODE do grSim.

Sequência (~59 s):
  Setup legal do GC: INIT_HALT (1 s) -> INIT_STOP (2 s) -> FORCE_START
  Fase 1  (30 s): 5 episódios livres de 6 s (PHASE1_EPISODE_1..5), bola na bissetriz (+0.45, 0.00)
  Fase 2A (12 s): LEGIT_SWITCH_MODERATE (Δr = 0.65 m, ΔC = 1.30: 0.60 < ΔC < 2.50)
  Fase 2B (14 s): LEGIT_SWITCH_LARGE (0.8 s) + LEGIT_REVERSAL_08S (13.2 s)
"""

import argparse
import csv
import math
import os
from pathlib import Path
import re
import socket
import struct
import sys
import threading
import time

from oxebots_interfaces.msg import GameData, RoleAssignment
import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy
from ssl_league_msgs.msg import Referee

EPISODE_S = 6.0
PHASE2A_S = 12.0
PHASE2B_REVERSAL_DELAY_S = 0.8
PHASE2B_TOTAL_S = 14.0
NEAR_BALL_M = 0.40
BALL_IMPULSE_MPS = 0.65
Y_LIMIT_M = 0.20
Y_REPOSITION_INWARD_M = 0.18
SLOW_BALL_MPS = 0.20
IMPULSE_COOLDOWN_S = 0.85
MAX_IMPULSES_PER_EPISODE = 2
MIN_BALL_ROBOT_CLEARANCE_M = 0.30

# Robôs amarelos estacionados fora da zona de jogo e longe dos gols e de y in [-0.8, +0.8]
PARKED_YELLOW = [
    (0, -2.05, 1.20, 0.0),
    (1, -2.05, -1.20, 0.0),
    (2, 2.05, 1.25, 180.0),
]

TOTAL_REPLACEMENT_PACKETS_SENT = 0


# --- Codificação Protobuf leve para grSim e Referee Multicast ---

def _sanitize_finite(val: float, default: float = 0.0, lo: float = -10.0, hi: float = 10.0) -> float:
    try:
        f = float(val)
    except Exception:
        return default
    if not math.isfinite(f):
        return default
    return max(lo, min(hi, f))


def varint(v: int) -> bytes:
    v = int(v) & 0xFFFFFFFFFFFFFFFF
    out = bytearray()
    while v > 0x7F:
        out.append((v & 0x7F) | 0x80)
        v >>= 7
    out.append(v & 0x7F)
    return bytes(out)


def field_msg(field_num: int, data: bytes) -> bytes:
    return varint((field_num << 3) | 2) + varint(len(data)) + data


def field_varint(field_num: int, v: int) -> bytes:
    return varint((field_num << 3) | 0) + varint(v)


def field_double(field_num: int, val: float) -> bytes:
    return varint((field_num << 3) | 1) + struct.pack('<d', _sanitize_finite(val, 0.0, -360.0, 360.0))


def field_float(field_num: int, val: float) -> bytes:
    return varint((field_num << 3) | 5) + struct.pack('<f', _sanitize_finite(val, 0.0, -360.0, 360.0))


def field_str(field_num: int, text: str) -> bytes:
    return field_msg(field_num, text.encode('utf-8'))


def parse_fields(buf: bytes):
    i, n = 0, len(buf)
    while i < n:
        tag, shift = 0, 0
        while i < n:
            b = buf[i]
            i += 1
            tag |= (b & 0x7F) << shift
            if not (b & 0x80):
                break
            shift += 7
        fnum, wtype = tag >> 3, tag & 7
        if wtype == 0:
            val, shift = 0, 0
            while i < n:
                b = buf[i]
                i += 1
                val |= (b & 0x7F) << shift
                if not (b & 0x80):
                    break
                shift += 7
            yield fnum, wtype, val
        elif wtype == 1:
            yield fnum, wtype, buf[i:i + 8]
            i += 8
        elif wtype == 2:
            ln, shift = 0, 0
            while i < n:
                b = buf[i]
                i += 1
                ln |= (b & 0x7F) << shift
                if not (b & 0x80):
                    break
                shift += 7
            yield fnum, wtype, buf[i:i + ln]
            i += ln
        elif wtype == 5:
            yield fnum, wtype, struct.unpack('<f', buf[i:i + 4])[0]
            i += 4
        else:
            break


def read_vision(timeout_s: float = 0.08, max_packets: int = 6):
    vsock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    vsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        vsock.bind(('', 10020))
        mreq = struct.pack('4sl', socket.inet_aton('224.5.23.2'), socket.INADDR_ANY)
        vsock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        vsock.settimeout(timeout_s)
        ball_mm = None
        blues = {}
        yellows = {}
        sender_ip = None
        for _ in range(max_packets):
            data, addr = vsock.recvfrom(65535)
            sender_ip = addr[0]
            for fnum, wtype, val in parse_fields(data):
                if fnum == 1 and wtype == 2:
                    for df, dw, dv in parse_fields(val):
                        if df == 5 and dw == 2:
                            bx_d = by_d = None
                            for bf, _bw, bv in parse_fields(dv):
                                if bf == 3:
                                    bx_d = bv
                                elif bf == 4:
                                    by_d = bv
                            if bx_d is not None and by_d is not None:
                                ball_mm = (bx_d, by_d)
                        elif df in (6, 7) and dw == 2:
                            rid_d = rx_d = ry_d = rori_d = None
                            for rf, _rw, rv in parse_fields(dv):
                                if rf == 2:
                                    rid_d = rv
                                elif rf == 3:
                                    rx_d = rv
                                elif rf == 4:
                                    ry_d = rv
                                elif rf == 5:
                                    rori_d = rv
                            if rid_d is not None and rx_d is not None and ry_d is not None:
                                target = yellows if df == 6 else blues
                                target[rid_d] = (rx_d, ry_d, rori_d or 0.0)
        return sender_ip, ball_mm, blues, yellows
    except Exception:
        return None, None, {}, {}
    finally:
        vsock.close()


def build_grsim_packet(bx, by, all_robots, bvx=0.0, bvy=0.0):
    bx = _sanitize_finite(bx, 0.0, -2.5, 2.5)
    by = _sanitize_finite(by, 0.0, -1.8, 1.8)
    bvx = _sanitize_finite(bvx, 0.0, -3.0, 3.0)
    bvy = _sanitize_finite(bvy, 0.0, -3.0, 3.0)
    ball_rep = (
        field_double(1, bx) + field_double(2, by)
        + field_double(3, bvx) + field_double(4, bvy)
    )
    rep_payload = field_msg(1, ball_rep)
    for rid, x, y, deg, is_yellow, turnon in all_robots:
        rx = _sanitize_finite(x, 0.0, -2.5, 2.5)
        ry = _sanitize_finite(y, 0.0, -1.8, 1.8)
        rdeg = _sanitize_finite(deg, 0.0, -360.0, 360.0)
        r_msg = (
            field_double(1, rx) + field_double(2, ry) + field_double(3, rdeg)
            + field_varint(4, int(rid)) + field_varint(5, 1 if is_yellow else 0)
            + field_varint(6, 1 if turnon else 0)
        )
        rep_payload += field_msg(2, r_msg)
    return field_msg(2, rep_payload)


def build_referee_udp_packet(command: int, counter: int, blue_on_positive: bool = False) -> bytes:
    now_us = int(time.time() * 1_000_000)

    def encode_team(name: str) -> bytes:
        return (
            field_str(1, name) + field_varint(2, 0) + field_varint(3, 0) + field_varint(5, 0)
            + field_varint(6, 4) + field_varint(7, 300000000) + field_varint(8, 0)
            + field_varint(12, 0) + field_varint(13, 3)
        )

    return (
        field_varint(1, now_us) + field_varint(2, 1) + field_varint(4, command)
        + field_varint(5, counter) + field_varint(6, now_us)
        + field_msg(7, encode_team('Yellow')) + field_msg(8, encode_team('Blue'))
        + field_varint(10, 1 if blue_on_positive else 0)
    )


def resolve_target_ips():
    """Retorna apenas o IP primário do simulador para evitar pacotes duplicados por loopback+LAN."""
    vision_ip, _, _, _ = read_vision()
    if vision_ip:
        return [vision_ip]
    sim_ip = os.environ.get('SIMULATOR_IP', '')
    cfg_path = Path(__file__).resolve().parents[2] / 'src/oxebots_bringup/config/match_config.yaml'
    if not sim_ip and cfg_path.is_file():
        m = re.search(r'simulator_ip:\s*"([^"]+)"', cfg_path.read_text(encoding='utf-8'))
        if m and m.group(1):
            sim_ip = m.group(1)
    return [sim_ip or '127.0.0.1']


def teleport_sim(sock, target_ips, bx_m, by_m, blue_robots=None, yellow_robots=None,
                 bvx=0.0, bvy=0.0):
    """Envia UMA ÚNICA mensagem grSim_Replacement (porta 20011) por IP-alvo, sem duplicatas."""
    global TOTAL_REPLACEMENT_PACKETS_SENT
    all_robots = []
    if blue_robots:
        all_robots.extend((rid, x, y, deg, False, True) for rid, x, y, deg in blue_robots)
    if yellow_robots:
        all_robots.extend((rid, x, y, deg, True, True) for rid, x, y, deg in yellow_robots)
    pkt_20011 = build_grsim_packet(bx_m, by_m, all_robots, bvx, bvy)
    for ip in target_ips:
        try:
            sock.sendto(pkt_20011, (ip, 20011))
            TOTAL_REPLACEMENT_PACKETS_SENT += 1
        except Exception:
            pass


class E2ScenarioNode(Node):
    """Injeta o árbitro, observa /game_data e /role_assignment e grava os eventos do E2."""

    def __init__(self, events_output: Path):
        super().__init__('e2_scenario_node')
        self.events_output = events_output
        self.events_output.parent.mkdir(parents=True, exist_ok=True)
        self.events_file = open(self.events_output, 'w', newline='', encoding='utf-8')
        self.events_writer = csv.writer(self.events_file)
        self.events_writer.writerow(['timestamp_ms', 'event_name'])
        self.events_file.flush()

        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._command = Referee.COMMAND_HALT
        self._counter = 0
        self._attacker_id = 1
        self._defender_id = 2
        self._ball_hist = []     # (t_mono, x_m, y_m)
        self._blue_pos_m = {}    # id -> (x_m, y_m)
        self._yellow_pos_m = {}  # id -> (x_m, y_m)

        self._referee_pub = self.create_publisher(
            Referee, '/gc_multicast_bridge/referee_messages', 10)
        latched_qos = QoSProfile(
            history=HistoryPolicy.KEEP_LAST, depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.create_subscription(RoleAssignment, '/role_assignment', self._on_roles, latched_qos)
        self.create_subscription(GameData, '/game_data', self._on_game_data, 10)

        self._udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        try:
            self._udp_sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
        except Exception:
            pass
        self._timer = self.create_timer(0.1, self._publish_referee)

    def _on_roles(self, msg: RoleAssignment):
        with self._lock:
            att, dfn = int(msg.attacker_id), int(msg.defender_id)
            if att in (1, 2):
                self._attacker_id = att
                self._defender_id = dfn if dfn in (1, 2) else (2 if att == 1 else 1)

    def _on_game_data(self, msg: GameData):
        now = time.monotonic()
        bx = float(msg.ball.x) / 1000.0
        by = float(msg.ball.y) / 1000.0
        if not (math.isfinite(bx) and math.isfinite(by)):
            return
        with self._lock:
            self._ball_hist.append((now, bx, by))
            if len(self._ball_hist) > 40:
                del self._ball_hist[:20]
            blues = {}
            for r in msg.robots.allies:
                rx, ry = float(r.x) / 1000.0, float(r.y) / 1000.0
                if math.isfinite(rx) and math.isfinite(ry):
                    blues[int(r.id)] = (rx, ry)
            yellows = {}
            for r in msg.robots.enemies:
                rx, ry = float(r.x) / 1000.0, float(r.y) / 1000.0
                if math.isfinite(rx) and math.isfinite(ry):
                    yellows[int(r.id)] = (rx, ry)
            self._blue_pos_m = blues
            self._yellow_pos_m = yellows

    def get_attacker_defender(self):
        with self._lock:
            return self._attacker_id, self._defender_id

    def get_robot_pos_m(self, rid: int, fallback=(0.0, 0.0)):
        with self._lock:
            return self._blue_pos_m.get(int(rid), fallback)

    def get_all_robot_positions_m(self):
        with self._lock:
            pts = list(self._blue_pos_m.values()) + list(self._yellow_pos_m.values())
            for _, x, y, _ in PARKED_YELLOW:
                pts.append((x, y))
            return pts

    def get_ball_state(self):
        """Devolve (x_m, y_m, vy_mps, speed_mps, min_dist_any_robot_m); None se sem dados."""
        with self._lock:
            if not self._ball_hist:
                return None
            t_now, bx, by = self._ball_hist[-1]
            speed = 0.0
            vy = 0.0
            for t_old, ox, oy in reversed(self._ball_hist[:-1]):
                dt = t_now - t_old
                if dt >= 0.06:
                    speed = math.hypot(bx - ox, by - oy) / dt
                    vy = (by - oy) / dt
                    break
            all_pts = list(self._blue_pos_m.values()) + list(self._yellow_pos_m.values())
            for _, px, py, _ in PARKED_YELLOW:
                all_pts.append((px, py))
            dists = [math.hypot(x - bx, y - by) for x, y in all_pts]
            return bx, by, vy, speed, (min(dists) if dists else float('inf'))

    def wait_for_teleport_confirmation(self, sock, ips, target_ball_m, target_robots_m=None,
                                       blue_robots=None, yellow_robots=None,
                                       tol_m=0.12, timeout_s=0.35):
        """Aguarda /game_data confirmar o teleporte (sem loop de reenvio; no máximo 1 retry após 250 ms)."""
        t0 = time.monotonic()
        deadline = t0 + timeout_s
        retried = False
        tbx, tby = target_ball_m
        while time.monotonic() < deadline:
            with self._lock:
                ball_ok = False
                if self._ball_hist:
                    _, bx, by = self._ball_hist[-1]
                    ball_ok = math.hypot(bx - tbx, by - tby) < tol_m
                robots_ok = True
                if target_robots_m:
                    for rid, (rx, ry) in target_robots_m.items():
                        cur = self._blue_pos_m.get(int(rid))
                        if cur is None or math.hypot(cur[0] - rx, cur[1] - ry) >= tol_m:
                            robots_ok = False
                            break
                if ball_ok and robots_ok:
                    return True
            if not retried and (time.monotonic() - t0) >= 0.25:
                retried = True
                teleport_sim(sock, ips, tbx, tby, blue_robots, yellow_robots, bvx=0.0, bvy=0.0)
            time.sleep(0.015)
        return False

    def _build_ros_referee_msg(self) -> Referee:
        msg = Referee()
        msg.stage = Referee.STAGE_NORMAL_FIRST_HALF
        msg.command = self._command
        msg.command_counter = self._counter
        msg.blue_team_on_positive_half = [False]
        for team in (msg.yellow, msg.blue):
            team.goalkeeper = 0
            team.can_place_ball = [False]
            team.max_allowed_bots = [3]
        return msg

    def _publish_referee(self):
        if self._stop_event.is_set() or not rclpy.ok():
            return
        with self._lock:
            msg = self._build_ros_referee_msg()
            udp_pkt = build_referee_udp_packet(self._command, self._counter, False)
        self._referee_pub.publish(msg)
        if self._udp_sock is not None:
            try:
                self._udp_sock.sendto(udp_pkt, ('224.5.23.1', 10003))
            except Exception:
                pass

    def record_event(self, event_name: str, new_command=None):
        if self._stop_event.is_set() or not rclpy.ok():
            return
        msg = udp_pkt = None
        with self._lock:
            if new_command is not None:
                self._counter += 1
                self._command = new_command
                msg = self._build_ros_referee_msg()
                udp_pkt = build_referee_udp_packet(self._command, self._counter, False)
        ts_ms = int(time.time() * 1000)
        if msg is not None:
            self._referee_pub.publish(msg)
            if self._udp_sock is not None:
                try:
                    self._udp_sock.sendto(udp_pkt, ('224.5.23.1', 10003))
                except Exception:
                    pass
        self.events_writer.writerow([ts_ms, event_name])
        self.events_file.flush()
        self.get_logger().info(f'[E2] Evento {event_name} registrado em {ts_ms} ms')

    def stop_timers_and_sockets(self):
        self._stop_event.set()
        if self._timer is not None:
            try:
                self.destroy_timer(self._timer)
            except Exception:
                pass
            self._timer = None
        if self._udp_sock is not None:
            try:
                self._udp_sock.close()
            except Exception:
                pass
            self._udp_sock = None

    def close_csv(self):
        if self.events_file and not self.events_file.closed:
            self.events_file.flush()
            self.events_file.close()


def ensure_safe_ball_position(bx: float, by: float, robot_positions, min_clearance_m: float = 0.30):
    """Faz clamp ao campo útil (fora das áreas de defesa) e afasta de qualquer robô a < 0.30 m."""
    bx = _sanitize_finite(bx, 0.0, -1.60, 1.60)
    by = _sanitize_finite(by, 0.0, -1.10, 1.10)
    # Garante fora das áreas de defesa (|x| > 1.35 m com |y| < 0.65 m)
    if abs(bx) > 1.35 and abs(by) < 0.65:
        bx = math.copysign(1.35, bx)

    for rx, ry in robot_positions:
        dist = math.hypot(bx - rx, by - ry)
        if dist < min_clearance_m:
            dx = bx - rx
            dy = by - ry
            norm = math.hypot(dx, dy)
            if norm < 1e-3:
                dx, dy, norm = 1.0, 0.0, 1.0
            bx = rx + (dx / norm) * (min_clearance_m + 0.05)
            by = ry + (dy / norm) * (min_clearance_m + 0.05)
            bx = _sanitize_finite(bx, 0.0, -1.60, 1.60)
            by = _sanitize_finite(by, 0.0, -1.10, 1.10)
    return bx, by


def run_phase1_episode(node, sock, ips, idx, yellow):
    """Episódio livre de 6 s: bola na bissetriz (+0.45, 0.00), máx. 2 impulsos, cooldown >= 0.85 s."""
    sign = 1.0 if idx % 2 == 1 else -1.0
    ball_x, ball_y = 0.45, 0.00
    blue = [
        (0, -1.95, 0.00, 0.0),
        (1, -0.65, 0.70, 0.0),
        (2, -0.65, -0.70, 0.0),
    ]
    node.record_event(f'PHASE1_EPISODE_{idx}')
    teleport_sim(sock, ips, ball_x, ball_y, blue, yellow, bvx=0.0, bvy=BALL_IMPULSE_MPS * sign)

    t_end = time.monotonic() + EPISODE_S
    released = False
    impulses_sent = 0
    last_impulse = time.monotonic()
    cur_sign = sign
    while time.monotonic() < t_end:
        time.sleep(0.06)
        if released or impulses_sent >= MAX_IMPULSES_PER_EPISODE:
            continue
        if time.monotonic() - last_impulse < IMPULSE_COOLDOWN_S:
            continue
        state = node.get_ball_state()
        if state is None:
            continue
        bx, by, vy, speed, min_dist_any = state
        # Se qualquer robô (azul ou amarelo) chegou a < 0.40 m da bola, libera de vez o episódio
        if min_dist_any < NEAR_BALL_M:
            released = True
            continue
        moving_away_from_center = (by > Y_LIMIT_M and vy >= -0.05) or (by < -Y_LIMIT_M and vy <= 0.05)
        stalled = speed < SLOW_BALL_MPS
        if moving_away_from_center or stalled:
            if abs(by) > Y_LIMIT_M:
                cur_sign = -math.copysign(1.0, by)
                safe_y = math.copysign(Y_REPOSITION_INWARD_M, by)
            else:
                cur_sign = -cur_sign
                safe_y = _sanitize_finite(by, 0.0, -Y_REPOSITION_INWARD_M, Y_REPOSITION_INWARD_M)
            safe_x = _sanitize_finite(bx, 0.45, -1.20, 1.20)
            # Confirma distância >= 0.40 m para a nova coordenada da bola antes de enviar
            robots_pts = node.get_all_robot_positions_m()
            if any(math.hypot(safe_x - rx, safe_y - ry) < NEAR_BALL_M for rx, ry in robots_pts):
                released = True
                continue
            teleport_sim(sock, ips, safe_x, safe_y, bvx=0.0, bvy=BALL_IMPULSE_MPS * cur_sign)
            impulses_sent += 1
            last_impulse = time.monotonic()


def run_phase2a_moderate(node, sock, ips, yellow):
    """Fase 2A (12 s): Δr = 0.65 m, ΔC = 1.30 (0.60 < ΔC < 2.50 -> prova Lock-In no legado)."""
    att_id, def_id = node.get_attacker_defender()
    bx, by = 1.35, -0.35
    def_pos = (0.90, -0.35)
    att_pos = (0.25, -0.35)
    robots = [
        (0, -1.95, 0.00, 0.0),
        (def_id, def_pos[0], def_pos[1], 0.0),
        (att_id, att_pos[0], att_pos[1], 0.0),
    ]
    teleport_sim(sock, ips, bx, by, robots, yellow, bvx=0.0, bvy=0.0)
    node.wait_for_teleport_confirmation(
        sock, ips, (bx, by), {def_id: def_pos, att_id: att_pos},
        blue_robots=robots, yellow_robots=yellow, tol_m=0.12, timeout_s=0.35)
    node.record_event('LEGIT_SWITCH_MODERATE')
    node.record_event(f'LEGIT_SWITCH_MODERATE_ATT_{att_id}_DEF_{def_id}')
    time.sleep(PHASE2A_S)


def run_phase2b_large_and_reversal(node, sock, ips, yellow):
    """Fase 2B (14 s): troca ampla (ΔC ≈ 4.1 > 2.5) + rebote de bola aos 0.8 s (sem mover robôs)."""
    # Passo 2B-1: LEGIT_SWITCH_LARGE
    att_id, def_id = node.get_attacker_defender()
    bx, by = 1.10, -0.40
    def_pos = (0.60, -0.40)
    att_pos = (-1.30, 0.40)
    robots = [
        (0, -1.95, 0.00, 0.0),
        (def_id, def_pos[0], def_pos[1], 0.0),
        (att_id, att_pos[0], att_pos[1], 0.0),
    ]
    teleport_sim(sock, ips, bx, by, robots, yellow, bvx=0.0, bvy=0.0)
    node.wait_for_teleport_confirmation(
        sock, ips, (bx, by), {def_id: def_pos, att_id: att_pos},
        blue_robots=robots, yellow_robots=yellow, tol_m=0.12, timeout_s=0.35)
    node.record_event('LEGIT_SWITCH_LARGE')
    node.record_event(f'LEGIT_SWITCH_LARGE_ATT_{att_id}_DEF_{def_id}')

    # Aguarda exatamente 0.8 s com os robôs livres
    time.sleep(PHASE2B_REVERSAL_DELAY_S)

    # Passo 2B-2: LEGIT_REVERSAL_08S — reposiciona APENAS a bola parada a 0.45 m à frente do novo defensor
    rev_att_id, rev_def_id = node.get_attacker_defender()
    target_def_id = rev_def_id if rev_def_id in (1, 2) else att_id
    x_def, y_def = node.get_robot_pos_m(target_def_id, fallback=(-1.30, 0.40))
    raw_bx = x_def + 0.45
    raw_by = y_def
    rev_bx, rev_by = ensure_safe_ball_position(
        raw_bx, raw_by, node.get_all_robot_positions_m(),
        min_clearance_m=MIN_BALL_ROBOT_CLEARANCE_M)
    teleport_sim(sock, ips, rev_bx, rev_by, bvx=0.0, bvy=0.0)
    node.wait_for_teleport_confirmation(
        sock, ips, (rev_bx, rev_by), tol_m=0.12, timeout_s=0.25)
    node.record_event('LEGIT_REVERSAL_08S')
    node.record_event(f'LEGIT_REVERSAL_08S_ATT_{rev_att_id}_DEF_{target_def_id}')

    time.sleep(PHASE2B_TOTAL_S - PHASE2B_REVERSAL_DELAY_S)


def run_sequence(node: E2ScenarioNode):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    ips = resolve_target_ips()
    start_blue = [
        (0, -1.95, 0.00, 0.0),
        (1, -0.65, 0.70, 0.0),
        (2, -0.65, -0.70, 0.0),
    ]

    # Abertura legal do SSL GC: INIT_HALT (1 s) -> INIT_STOP (2 s) -> FORCE_START
    node.record_event('INIT_HALT', new_command=Referee.COMMAND_HALT)
    teleport_sim(sock, ips, 0.45, 0.00, start_blue, PARKED_YELLOW)
    time.sleep(1.0)
    node.record_event('INIT_STOP', new_command=Referee.COMMAND_STOP)
    time.sleep(2.0)
    node.record_event('NORMAL_PLAY', new_command=Referee.COMMAND_FORCE_START)

    # Fase 1: 5 episódios livres de 6 s = 30 s
    for idx in range(1, 6):
        run_phase1_episode(node, sock, ips, idx, PARKED_YELLOW)

    # Fase 2A (12 s): troca moderada (0.60 < ΔC = 1.30 < 2.50)
    run_phase2a_moderate(node, sock, ips, PARKED_YELLOW)

    # Fase 2B (14 s): troca ampla + rebote em 0.8 s
    run_phase2b_large_and_reversal(node, sock, ips, PARKED_YELLOW)

    node.get_logger().info(
        f'[E2] Finalizado com total de {TOTAL_REPLACEMENT_PACKETS_SENT} pacotes '
        f'grSim_Replacement enviados.'
    )
    sock.close()


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description='Cenário determinístico E2 (~59 s)')
    parser.add_argument('--events-output', type=Path, required=True,
                        help='Caminho do arquivo CSV de eventos (timestamp_ms,event_name)')
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    rclpy.init(args=argv)
    node = E2ScenarioNode(events_output=args.events_output)
    stop_event = threading.Event()

    def spin_worker():
        while rclpy.ok() and not stop_event.is_set() and not node._stop_event.is_set():
            rclpy.spin_once(node, timeout_sec=0.05)

    spin_thread = threading.Thread(target=spin_worker, daemon=True)
    spin_thread.start()

    try:
        run_sequence(node)
    except KeyboardInterrupt:
        pass
    finally:
        # 1. Sinaliza parada e aguarda a thread de spin
        stop_event.set()
        node._stop_event.set()
        if spin_thread.is_alive():
            spin_thread.join(timeout=2.0)
        # 2. Cancela timers e fecha sockets
        node.stop_timers_and_sockets()
        # 3. Salva e fecha o CSV de eventos
        node.close_csv()
        # 4. Destrói o nó e desliga o ROS 2
        try:
            node.destroy_node()
        except Exception:
            pass
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main(sys.argv[1:])
