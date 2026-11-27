#!/usr/bin/env python3
"""Cenário determinístico 100% automatizado do Experimento E1 (38 s).

Reposiciona robôs e bola no grSim via UDP (portas 20011/10300) e injeta estados do
Game Controller programaticamente em /gc_multicast_bridge/referee_messages (e via
multicast UDP 224.5.23.1:10003 para compatibilidade com match:=True).

Sequência cronometrada fiel à máquina de estados oficial do SSL Game Controller (38 s):
  1. HALT inicial de setup (1 s)
  2. STOP inicial de setup (2 s)
  3. NORMAL_PLAY via FORCE_START (10 s)
  4. STOP principal de avaliação (10 s)
  5. NORMAL_PLAY via FORCE_START com pressão na borda da área (10 s)
  6. HALT final de avaliação de preempção (5 s)
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

from geometry_msgs.msg import Point32
import rclpy
from rclpy.node import Node
from ssl_league_msgs.msg import Referee


# --- Codificação Protobuf leve (compatível com challengs/set_kick_positions.py) ---

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
    return varint((field_num << 3) | 1) + struct.pack('<d', float(val))


def field_float(field_num: int, val: float) -> bytes:
    return varint((field_num << 3) | 5) + struct.pack('<f', float(val))


def field_str(field_num: int, text: str) -> bytes:
    raw = text.encode('utf-8')
    return field_msg(field_num, raw)


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


def read_vision():
    vsock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    vsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        vsock.bind(('', 10020))
        mreq = struct.pack('4sl', socket.inet_aton('224.5.23.2'), socket.INADDR_ANY)
        vsock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        vsock.settimeout(0.08)
        ball_mm = None
        blues = {}
        yellows = {}
        sender_ip = None
        for _ in range(6):
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
                        elif df == 6 and dw == 2:
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
                                yellows[rid_d] = (rx_d, ry_d, rori_d or 0.0)
                        elif df == 7 and dw == 2:
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
                                blues[rid_d] = (rx_d, ry_d, rori_d or 0.0)
        return sender_ip, ball_mm, blues, yellows
    except Exception:
        return None, None, {}, {}
    finally:
        vsock.close()


def build_grsim_packet(bx, by, all_robots, scale=1.0, bvx=0.0, bvy=0.0):
    ball_rep = (
        field_double(1, bx * scale)
        + field_double(2, by * scale)
        + field_double(3, bvx)
        + field_double(4, bvy)
    )
    rep_payload = field_msg(1, ball_rep)
    for rid, x, y, deg, is_yellow, turnon in all_robots:
        r_msg = (
            field_double(1, x * scale)
            + field_double(2, y * scale)
            + field_double(3, deg)
            + field_varint(4, rid)
            + field_varint(5, 1 if is_yellow else 0)
            + field_varint(6, 1 if turnon else 0)
        )
        rep_payload += field_msg(2, r_msg)
    return field_msg(2, rep_payload)


def build_sim_cmd_packet(bx, by, all_robots, scale=1.0, bvx=0.0, bvy=0.0):
    t_ball = (
        field_float(1, bx * scale)
        + field_float(2, by * scale)
        + field_float(3, 0.0)
        + field_float(4, bvx)
        + field_float(5, bvy)
        + field_float(6, 0.0)
    )
    sim_ctrl = field_msg(1, t_ball)
    for rid, x, y, deg, is_yellow, turnon in all_robots:
        rid_msg = field_varint(1, rid) + field_varint(2, 1 if is_yellow else 2)
        t_rob = (
            field_msg(1, rid_msg)
            + field_float(2, x * scale)
            + field_float(3, y * scale)
            + field_float(4, math.radians(deg))
            + field_float(5, 0.0)
            + field_float(6, 0.0)
            + field_float(7, 0.0)
            + field_varint(8, 1 if turnon else 0)
        )
        sim_ctrl += field_msg(2, t_rob)
    return field_msg(1, sim_ctrl)


def build_referee_udp_packet(
    command: int,
    counter: int,
    designated_pos_m=None,
    blue_on_positive: bool = False,
) -> bytes:
    """Codifica SSL_Referee em Protobuf para multicast UDP 224.5.23.1:10003."""
    now_us = int(time.time() * 1_000_000)

    def encode_team(name: str) -> bytes:
        return (
            field_str(1, name)
            + field_varint(2, 0)   # score
            + field_varint(3, 0)   # red_cards
            + field_varint(5, 0)   # yellow_cards
            + field_varint(6, 4)   # timeouts
            + field_varint(7, 300000000)  # timeout_time
            + field_varint(8, 0)   # goalkeeper = 0
            + field_varint(12, 0)  # can_place_ball = False
            + field_varint(13, 3)  # max_allowed_bots = 3
        )

    pkt = (
        field_varint(1, now_us)
        + field_varint(2, 1)  # STAGE_NORMAL_FIRST_HALF
        + field_varint(4, command)
        + field_varint(5, counter)
        + field_varint(6, now_us)
        + field_msg(7, encode_team('Yellow'))
        + field_msg(8, encode_team('Blue'))
        + field_varint(10, 1 if blue_on_positive else 0)
    )
    if designated_pos_m is not None:
        # No protobuf oficial SSL_Referee, designated_position é em milímetros
        pt = (
            field_float(1, float(designated_pos_m[0]) * 1000.0)
            + field_float(2, float(designated_pos_m[1]) * 1000.0)
        )
        pkt += field_msg(9, pt)
    return pkt


def resolve_target_ips():
    sim_ip = os.environ.get('SIMULATOR_IP', '')
    cfg_path = Path(__file__).resolve().parents[2] / 'src/oxebots_bringup/config/match_config.yaml'
    if not sim_ip and cfg_path.is_file():
        m = re.search(r'simulator_ip:\s*"([^"]+)"', cfg_path.read_text(encoding='utf-8'))
        if m and m.group(1):
            sim_ip = m.group(1)
    sim_ip = sim_ip or '127.0.0.1'
    vision_ip, _, _, _ = read_vision()
    return list(
        dict.fromkeys(
            ip for ip in [sim_ip, vision_ip, '127.0.0.1', '172.17.0.1', '172.17.0.2'] if ip
        )
    )


def teleport_sim(sock, target_ips, bx_m, by_m, blue_robots=None, yellow_robots=None):
    """Teleporta bola e opcionalmente robôs no grSim via portas 20011 e 10300."""
    all_robots = []
    if blue_robots:
        all_robots.extend((rid, x, y, deg, False, on) for rid, x, y, deg, on in blue_robots)
    if yellow_robots:
        all_robots.extend((rid, x, y, deg, True, on) for rid, x, y, deg, on in yellow_robots)

    pkt_20011 = build_grsim_packet(bx_m, by_m, all_robots, 1.0)
    pkt_10300 = build_sim_cmd_packet(bx_m, by_m, all_robots, 1.0)
    for ip in target_ips:
        for _ in range(3):
            try:
                sock.sendto(pkt_20011, (ip, 20011))
                sock.sendto(pkt_10300, (ip, 10300))
            except Exception:
                pass


class E1ScenarioNode(Node):
    """Injeta comandos do Game Controller a 10 Hz e registra timestamps das transições."""

    def __init__(self, events_output: Path):
        super().__init__('e1_scenario_node')
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
        self._designated_pos_m = None

        self._referee_pub = self.create_publisher(
            Referee, '/gc_multicast_bridge/referee_messages', 10
        )
        self._udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        try:
            self._udp_sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
        except Exception:
            pass

        self._timer = self.create_timer(0.1, self._publish_referee)

    def _build_ros_referee_msg(self) -> Referee:
        msg = Referee()
        msg.stage = Referee.STAGE_NORMAL_FIRST_HALF
        msg.command = self._command
        msg.command_counter = self._counter
        msg.blue_team_on_positive_half = [False]
        if self._designated_pos_m is not None:
            pt = Point32()
            pt.x = float(self._designated_pos_m[0])
            pt.y = float(self._designated_pos_m[1])
            pt.z = 0.0
            msg.designated_position = [pt]
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
            udp_pkt = build_referee_udp_packet(
                self._command, self._counter, self._designated_pos_m, False
            )
        self._referee_pub.publish(msg)
        if self._udp_sock is not None:
            try:
                self._udp_sock.sendto(udp_pkt, ('224.5.23.1', 10003))
            except Exception:
                pass

    def transition(self, event_name: str, command: int, designated_pos_m=None):
        """Aplica nova transição de comando do GC e grava o timestamp exato em ms."""
        if self._stop_event.is_set() or not rclpy.ok():
            return
        with self._lock:
            self._counter += 1
            self._command = command
            self._designated_pos_m = designated_pos_m
            msg = self._build_ros_referee_msg()
            udp_pkt = build_referee_udp_packet(
                self._command, self._counter, self._designated_pos_m, False
            )

        ts_ms = int(time.time() * 1000)
        self._referee_pub.publish(msg)
        if self._udp_sock is not None:
            try:
                self._udp_sock.sendto(udp_pkt, ('224.5.23.1', 10003))
            except Exception:
                pass

        self.events_writer.writerow([ts_ms, event_name])
        self.events_file.flush()
        self.get_logger().info(
            f'[E1] Transição {event_name} (cmd={command}, counter={self._counter}) em {ts_ms} ms'
        )

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


def run_sequence(node: E1ScenarioNode):
    """Executa o roteiro determinístico de 38 s fiel à máquina de estados oficial do SSL GC.

    Sequência (38 s):
      1. INIT_HALT (1 s)
      2. INIT_STOP (2 s)
      3. NORMAL_PLAY_1 via FORCE_START (10 s)
      4. STOP (10 s)
      5. NORMAL_PLAY_2 via FORCE_START (10 s)
      6. HALT (5 s)
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    target_ips = resolve_target_ips()

    # Posição inicial (distante > 1.75 m da bola para que o STOP inicial de 2 s seja limpo):
    # - Goleiro azul (0) na meta (-2.05, 0.0)
    # - Atacante azul (1) em (-0.80, -0.25)
    # - Defensor azul (2) em (-1.35, 0.35)
    # - Bola em (0.95, 0.05)
    initial_blue = [
        (0, -2.050, 0.000, 0.0, True),
        (1, -0.800, -0.250, 0.0, True),
        (2, -1.350, 0.350, 0.0, True),
    ]
    initial_yellow = [
        (0, 2.050, 0.300, 180.0, True),
        (1, 1.550, -0.850, 180.0, True),
        (2, 1.550, 0.850, 180.0, True),
    ]

    # -------------------------------------------------------------------------
    # 1. HALT inicial (1 s) — posicionamento no simulador
    # -------------------------------------------------------------------------
    node.transition('INIT_HALT', Referee.COMMAND_HALT)
    teleport_sim(sock, target_ips, 0.950, 0.050, initial_blue, initial_yellow)
    time.sleep(0.5)
    teleport_sim(sock, target_ips, 0.950, 0.050, initial_blue, initial_yellow)
    time.sleep(0.5)

    # -------------------------------------------------------------------------
    # 2. STOP inicial de preparação (2 s) — transição oficial HALT -> STOP -> FORCE_START
    # -------------------------------------------------------------------------
    node.transition('INIT_STOP', Referee.COMMAND_STOP)
    time.sleep(2.0)

    # -------------------------------------------------------------------------
    # 3. NORMAL_PLAY_1 via FORCE_START (10 s)
    # -------------------------------------------------------------------------
    node.transition('NORMAL_PLAY_1', Referee.COMMAND_FORCE_START)
    # 7.5 s de jogo corrido completo; nos últimos 2.5 s antes do STOP principal,
    # reposiciona o atacante em sprint rumo à bola para que a transição RUN -> STOP
    # ocorra com o robô em alta velocidade (> 1.0 m/s) e perto da bola.
    time.sleep(7.5)
    sprint_blue = [
        (0, -2.050, 0.000, 0.0, True),
        (1, -0.850, 0.000, 0.0, True),
        (2, -1.450, 0.250, 0.0, True),
    ]
    teleport_sim(sock, target_ips, 0.650, 0.000, sprint_blue, initial_yellow)
    time.sleep(2.5)

    # -------------------------------------------------------------------------
    # 4. STOP principal (10 s) — teto de 0.75 m/s e recuo do raio de 500 mm da bola
    # -------------------------------------------------------------------------
    _, _, blues_now, _ = read_vision()
    if 1 in blues_now:
        rx_m = blues_now[1][0] / 1000.0
        ry_m = blues_now[1][1] / 1000.0
        teleport_sim(sock, target_ips, min(rx_m + 0.320, 1.550), ry_m)
    else:
        teleport_sim(sock, target_ips, 0.350, 0.000)

    node.transition('STOP', Referee.COMMAND_STOP)
    time.sleep(10.0)

    # -------------------------------------------------------------------------
    # 5. NORMAL_PLAY_2 via FORCE_START (10 s) — estresse da borda da área adversária e corrida p/ HALT
    # -------------------------------------------------------------------------
    # Posiciona a bola próxima à borda frontal da área adversária (x = 1.64 m, y = 0.0 m; borda = 1.75 m)
    # com o atacante (1) alinhado logo atrás (x = 1.15 m, y = 0.0 m) para que o avanço em linha reta /
    # chute estresse diretamente a invasão de área em A e B (validando o clampVelocities em C).
    area_stress_blue = [
        (0, -2.050, 0.000, 0.0, True),
        (1, 1.150, 0.000, 0.0, True),
        (2, -1.400, 0.300, 0.0, True),
    ]
    teleport_sim(sock, target_ips, 1.640, 0.000, area_stress_blue, initial_yellow)
    node.transition('NORMAL_PLAY_2', Referee.COMMAND_FORCE_START)
    time.sleep(3.5)
    teleport_sim(sock, target_ips, 1.660, -0.050, area_stress_blue, initial_yellow)
    time.sleep(4.0)

    # Nos últimos 2.5 s antes do HALT, garante corrida em alta velocidade (> 0.8 m/s)
    pre_halt_blue = [
        (0, -2.050, 0.000, 0.0, True),
        (1, -0.700, -0.150, 0.0, True),
        (2, -1.400, 0.300, 0.0, True),
    ]
    teleport_sim(sock, target_ips, 0.900, 0.150, pre_halt_blue, initial_yellow)
    time.sleep(2.5)

    # -------------------------------------------------------------------------
    # 6. HALT final (5 s) — parada imediata a partir de NORMAL_PLAY
    # -------------------------------------------------------------------------
    node.transition('HALT', Referee.COMMAND_HALT)
    time.sleep(5.0)

    sock.close()


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description='Cenário determinístico E1 (30 s)')
    parser.add_argument(
        '--events-output',
        type=Path,
        required=True,
        help='Caminho do arquivo CSV de eventos (timestamp_ms,event_name)',
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    rclpy.init(args=argv)
    node = E1ScenarioNode(events_output=args.events_output)
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
        # 1. Sinaliza parada e aguarda encerramento da thread de spin
        stop_event.set()
        node._stop_event.set()
        if spin_thread.is_alive():
            spin_thread.join(timeout=2.0)

        # 2. Cancela timers e fecha sockets UDP
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
