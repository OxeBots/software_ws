#!/usr/bin/env python3
"""Cenário determinístico do Experimento E3 (~63 s): Tolerância a Falhas (3 -> 2 -> 1 Robôs).

Avalia a degradação graciosa de 3 -> 2 -> 1 robôs, comparando alocação estática vs. dinâmica e
a eliminação de comandos fantasma para robôs ausentes da visão.

Regras anti-crash do grSim:
  - Envia NO MÁXIMO 1 pacote grSim_Replacement (porta 20011) por transição (total = 3 pacotes em 63 s).
  - Usa turnon=False em grSim_Robot_Replacement junto com coordenada de estacionamento fora das
    câmeras para remover o robô da detecção do SSL-Vision de forma limpa e instantânea, sem
    colisão física no solver ODE.
  - Todas as coordenadas e velocidades passam por validação math.isfinite() e clamp seguro.

Sequência (~63 s):
  Setup legal do GC (3 s): INIT_HALT (1 s) -> INIT_STOP (2 s) -> NORMAL_PLAY via FORCE_START
  Fase 1 (0 s a 20 s): 3 robôs ativos (GK=0, linha=1 e 2), bola em (+0.30, +0.20)
  Fase 2 (20 s a 40 s): FAIL_3_TO_2 — remove o attacker atual; bola em (+0.40, 0.00)
  Fase 3 (40 s a 60 s): FAIL_2_TO_1 — remove o goleiro (ID 0), deixando apenas o último robô de
                        linha sobrevivente (que mantém attacker com defender=NO_ROBOT e gk=NO_ROBOT),
                        bola em (-0.60, 0.00)
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

PHASE1_S = 20.0
PHASE2_S = 20.0
PHASE3_S = 20.0

# Posições de estacionamento fora da zona de visão/jogo (com turnon=False) para robôs removidos,
# espaçadas para nunca haver superposição geométrica no ODE
OFF_FIELD_SLOTS = {
    0: (-2.35, 1.45, 0.0),
    1: (-1.75, 1.45, 0.0),
    2: (-1.15, 1.45, 0.0),
}

# Robôs amarelos estacionados e desligados (turnon=False) fora do campo de visão
PARKED_YELLOW = [
    (0, 2.35, 1.45, 180.0, True, False),
    (1, 1.75, 1.45, 180.0, True, False),
    (2, 1.15, 1.45, 180.0, True, False),
]

TOTAL_REPLACEMENT_PACKETS_SENT = 0


# --- Codificação Protobuf leve para grSim e Referee Multicast ---

def _sanitize_finite(val: float, default: float = 0.0, lo: float = -15.0, hi: float = 15.0) -> float:
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
        rx = _sanitize_finite(x, 0.0, -3.0, 3.0)
        ry = _sanitize_finite(y, 0.0, -2.0, 2.0)
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
    """Retorna apenas o IP primário do simulador para evitar pacotes duplicados."""
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


def send_single_replacement(sock, target_ips, bx_m, by_m, robot_specs, bvx=0.0, bvy=0.0):
    """Envia EXATAMENTE 1 pacote grSim_Replacement (porta 20011) por transição."""
    global TOTAL_REPLACEMENT_PACKETS_SENT
    pkt_20011 = build_grsim_packet(bx_m, by_m, robot_specs, bvx, bvy)
    for ip in target_ips:
        try:
            sock.sendto(pkt_20011, (ip, 20011))
            TOTAL_REPLACEMENT_PACKETS_SENT += 1
        except Exception:
            pass


class E3ScenarioNode(Node):
    """Injeta o árbitro, observa /game_data e /role_assignment e grava os eventos do E3."""

    def __init__(self, events_output: Path):
        super().__init__('e3_scenario_node')
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
        self._goalkeeper_id = 0
        self._blue_pos_m = {}  # id -> (x_m, y_m)

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
            self._goalkeeper_id = int(msg.goalkeeper_id)
            self._attacker_id = int(msg.attacker_id)
            self._defender_id = int(msg.defender_id)

    def _on_game_data(self, msg: GameData):
        with self._lock:
            blues = {}
            for r in msg.robots.allies:
                rx, ry = float(r.x) / 1000.0, float(r.y) / 1000.0
                if math.isfinite(rx) and math.isfinite(ry):
                    blues[int(r.id)] = (rx, ry)
            self._blue_pos_m = blues

    def get_current_roles(self):
        with self._lock:
            return self._goalkeeper_id, self._attacker_id, self._defender_id

    def get_blue_positions_m(self):
        with self._lock:
            return dict(self._blue_pos_m)

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
        self.get_logger().info(f'[E3] Evento {event_name} registrado em {ts_ms} ms')

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


def ensure_safe_ball_position(bx: float, by: float, robot_positions_m, min_clearance_m: float = 0.30):
    """Garante que a bola não seja reposicionada em cima de nenhum robô sobrevivente."""
    bx = _sanitize_finite(bx, 0.0, -1.60, 1.60)
    by = _sanitize_finite(by, 0.0, -1.10, 1.10)
    for rx, ry in robot_positions_m.values():
        dist = math.hypot(bx - rx, by - ry)
        if dist < min_clearance_m:
            dx, dy = bx - rx, by - ry
            norm = math.hypot(dx, dy)
            if norm < 1e-3:
                dx, dy, norm = 1.0, 0.0, 1.0
            bx = _sanitize_finite(rx + (dx / norm) * (min_clearance_m + 0.05), 0.0, -1.60, 1.60)
            by = _sanitize_finite(ry + (dy / norm) * (min_clearance_m + 0.05), 0.0, -1.10, 1.10)
    return bx, by


def run_sequence(node: E3ScenarioNode):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    ips = resolve_target_ips()

    # Setup único inicial (Pacote #1): 3 robôs azuis ligados (turnon=True) e 3 amarelos desligados
    initial_robots = [
        (0, -1.95, 0.00, 0.0, False, True),
        (1, -0.80, 0.45, 0.0, False, True),
        (2, -0.80, -0.45, 0.0, False, True),
        *PARKED_YELLOW,
    ]

    # Abertura legal do SSL GC: INIT_HALT (1 s) -> INIT_STOP (2 s) -> NORMAL_PLAY via FORCE_START
    node.record_event('INIT_HALT', new_command=Referee.COMMAND_HALT)
    send_single_replacement(sock, ips, 0.30, 0.20, initial_robots, bvx=0.0, bvy=0.0)
    time.sleep(1.0)

    node.record_event('INIT_STOP', new_command=Referee.COMMAND_STOP)
    time.sleep(2.0)

    # Fase 1 — Operação Nominal com 3 robôs (0 s a 20 s de NORMAL_PLAY)
    node.record_event('NORMAL_PLAY', new_command=Referee.COMMAND_FORCE_START)
    node.record_event('PHASE1_NOMINAL_3_ROBOTS')
    time.sleep(PHASE1_S)

    # Fase 2 — Perda do Atacante: Degradação 3 -> 2 robôs (20 s a 40 s)
    _, cur_att, _ = node.get_current_roles()
    removed_p2_id = cur_att if cur_att in (1, 2) else 1
    surviving_line_id = 2 if removed_p2_id == 1 else 1

    off_x2, off_y2, off_deg2 = OFF_FIELD_SLOTS[removed_p2_id]
    p2_bx, p2_by = ensure_safe_ball_position(0.40, 0.00, node.get_blue_positions_m())
    # Pacote #2: remove apenas removed_p2_id (turnon=False + slot fora de campo) e posiciona a bola
    # em (+0.40, 0.00) SEM tocar nos 2 robôs sobreviventes!
    send_single_replacement(
        sock,
        ips,
        p2_bx,
        p2_by,
        [(removed_p2_id, off_x2, off_y2, off_deg2, False, False)],
        bvx=0.0,
        bvy=0.0,
    )
    node.record_event('FAIL_3_TO_2')
    node.record_event(f'FAIL_3_TO_2_REMOVED_{removed_p2_id}_SURVIVOR_{surviving_line_id}')
    time.sleep(PHASE2_S)

    # Fase 3 — Segunda Falha: Degradação 2 -> 1 robô (40 s a 60 s)
    # Remove o goleiro (ID 0), deixando apenas o robô de linha sobrevivente (surviving_line_id)
    # para exercitar a regra de 1 robô de linha elegível (assume attacker com gk=NO_ROBOT, def=NO_ROBOT)
    # enquanto valida a ausência de comandos fantasma para os 2 robôs removidos (removed_p2_id e 0).
    removed_p3_id = 0
    off_x3, off_y3, off_deg3 = OFF_FIELD_SLOTS[removed_p3_id]
    p3_bx, p3_by = ensure_safe_ball_position(-0.60, 0.00, node.get_blue_positions_m())
    # Pacote #3: remove ID 0 (turnon=False) e posiciona a bola em (-0.60, 0.00) sem mover o sobrevivente
    send_single_replacement(
        sock,
        ips,
        p3_bx,
        p3_by,
        [(removed_p3_id, off_x3, off_y3, off_deg3, False, False)],
        bvx=0.0,
        bvy=0.0,
    )
    node.record_event('FAIL_2_TO_1')
    node.record_event(f'FAIL_2_TO_1_REMOVED_{removed_p3_id}_LAST_{surviving_line_id}')
    time.sleep(PHASE3_S)

    node.get_logger().info(
        f'[E3] Finalizado com total de {TOTAL_REPLACEMENT_PACKETS_SENT} pacotes '
        f'grSim_Replacement enviados.'
    )
    sock.close()


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description='Cenário determinístico E3 (~63 s)')
    parser.add_argument('--events-output', type=Path, required=True,
                        help='Caminho do arquivo CSV de eventos (timestamp_ms,event_name)')
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    rclpy.init(args=argv)
    node = E3ScenarioNode(events_output=args.events_output)
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
