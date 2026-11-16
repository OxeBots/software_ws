#!/usr/bin/env python3
"""
Posiciona a bola e os robôs (amarelos e azuis) nas posições iniciais (Start)
do Robot Placement Technical Challenge da RoboCup Brasil SSL-EL 2026.

Uso:
    python3 set_placement_positions.py <1|2|3|4>
"""

import sys
import math
import os
import re
import socket
import struct
import time

SCENARIOS = {
    1: {
        "name": "Free Kick 1",
        "command": "Direct Free Kick Yellow (8)",
        "ball": (1.850, 1.300),
        "blue": [
            (0, 1.850, 1.390, 270.0, True),  # Obstáculo na bola
            (1, 0.090, 0.700, 0.0, True),    # Obstáculo meio superior
            (2, 0.350, -1.000, 0.0, True),   # Obstáculo meio inferior
        ],
        "yellow": [
            (0, 0.090, -1.000, 0.0, True),   # Alvo: (2100, 300)
            (1, -0.210, 0.700, 0.0, True),   # Alvo: (1650, 900)
            (2, 0.290, -1.240, 0.0, True),   # Alvo: (1850, 900)
        ],
    },
    2: {
        "name": "Free Kick 2",
        "command": "Direct Free Kick Yellow (8)",
        "ball": (-1.850, 1.300),
        "blue": [
            (0, -1.850, 0.900, 90.0, True),  # Barreira defensiva 1
            (1, -1.650, 0.900, 90.0, True),  # Barreira defensiva 2
            (2, -2.100, 0.300, 90.0, True),  # Barreira recuada
        ],
        "yellow": [
            (0, -1.650, 0.000, 180.0, True),   # Alvo: (-1850, 1420)
            (1, -1.500, -1.150, 180.0, True),  # Alvo: (150, 700)
            (2, -2.000, -0.800, 180.0, True),  # Alvo: (-590, -600)
        ],
    },
    3: {
        "name": "Kick Off",
        "command": "Prepare Kick-Off Yellow (4)",
        "ball": (0.000, 0.000),
        "blue": [
            (0, -2.100, 0.000, 0.0, True),   # Goleiro adversário
            (1, -0.650, 0.150, 0.0, True),   # Defensor superior
            (2, -0.650, -0.150, 0.0, True),  # Defensor inferior
        ],
        "yellow": [
            (0, -1.250, -0.150, 180.0, True),  # Alvo: (2100, 0)
            (1, -1.250, 0.150, 180.0, True),   # Alvo: (250, 700)
            (2, -1.450, 0.000, 180.0, True),   # Alvo: (250, 0)
        ],
    },
    4: {
        "name": "Penalty",
        "command": "Prepare Penalty Yellow (6)",
        "ball": (-0.750, 0.000),
        "blue": [
            (0, -2.100, 0.000, 0.0, True),   # Goleiro na linha de gol
            (1, 0.310, 1.050, 180.0, True),  # Defensor superior
            (2, 0.310, -1.050, 180.0, True), # Defensor inferior
        ],
        "yellow": [
            (0, -1.450, 1.000, 180.0, True),   # Alvo: (310, 800)
            (1, -1.450, 0.000, 180.0, True),   # Batedor -> Alvo: (-250, 0)
            (2, -1.450, -1.000, 180.0, True),  # Alvo: (310, -800)
        ],
    },
}

def varint(v):
    out = bytearray()
    while v > 0x7F:
        out.append((v & 0x7F) | 0x80)
        v >>= 7
    out.append(v & 0x7F)
    return bytes(out)

def field_msg(field_num, data):
    return varint((field_num << 3) | 2) + varint(len(data)) + data

def field_varint(field_num, v):
    return varint((field_num << 3) | 0) + varint(v)

def field_double(field_num, val):
    return varint((field_num << 3) | 1) + struct.pack("<d", float(val))

def field_float(field_num, val):
    return varint((field_num << 3) | 5) + struct.pack("<f", float(val))

def parse_fields(buf):
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
            yield fnum, wtype, struct.unpack("<f", buf[i:i + 4])[0]
            i += 4
        else:
            break

def read_vision():
    vsock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    vsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        vsock.bind(("", 10020))
        mreq = struct.pack("4sl", socket.inet_aton("224.5.23.2"), socket.INADDR_ANY)
        vsock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        vsock.settimeout(0.08)
        ball_mm = None
        blues = {}
        yellows = {}
        sender_ip = None
        for _ in range(8):
            data, addr = vsock.recvfrom(65535)
            sender_ip = addr[0]
            for fnum, wtype, val in parse_fields(data):
                if fnum == 1 and wtype == 2:
                    for df, dw, dv in parse_fields(val):
                        if df == 5 and dw == 2:
                            bx_d = by_d = None
                            for bf, bw, bv in parse_fields(dv):
                                if bf == 3:
                                    bx_d = bv
                                elif bf == 4:
                                    by_d = bv
                            if bx_d is not None and by_d is not None:
                                ball_mm = (bx_d, by_d)
                        elif df == 6 and dw == 2:
                            rid_d = rx_d = ry_d = rori_d = None
                            for rf, rw, rv in parse_fields(dv):
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
                            for rf, rw, rv in parse_fields(dv):
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

def build_grsim_packet(bx, by, all_robots, scale=1.0):
    ball_rep = field_double(1, bx * scale) + field_double(2, by * scale) + field_double(3, 0.0) + field_double(4, 0.0)
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

def build_sim_cmd_packet(bx, by, all_robots, scale=1.0):
    t_ball = (
        field_float(1, bx * scale) + field_float(2, by * scale) + field_float(3, 0.0)
        + field_float(4, 0.0) + field_float(5, 0.0) + field_float(6, 0.0)
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

def build_robot_ctrl(vels, is_yellow=False):
    pkt = b""
    for rid, vx, vy, vw in vels:
        glob_vel = field_float(1, vx) + field_float(2, vy) + field_float(3, vw)
        move_cmd = field_msg(3, glob_vel)
        rcmd = field_varint(1, rid) + field_msg(2, move_cmd) + field_float(3, 0.0) + field_float(4, 0.0) + field_float(5, 0.0)
        pkt += field_msg(1, rcmd)
    return pkt

def setup_scenario(scenario_id):
    if scenario_id not in SCENARIOS:
        print(f"[ERRO] Cenário {scenario_id} inválido. Escolha de 1 a 4.")
        sys.exit(1)

    sc = SCENARIOS[scenario_id]
    print(f"==========================================================")
    print(f" [Placement Challenge] Configurando Cenário {scenario_id}: {sc['name']}")
    print(f" Comando GC esperado: {sc['command']}")
    print(f"==========================================================")

    sim_ip = os.environ.get("SIMULATOR_IP", "")
    config_candidates = [
        "src/oxebots_bringup/config/match_config.yaml",
        os.path.join(os.path.dirname(__file__), "../src/oxebots_bringup/config/match_config.yaml"),
    ]
    for cfg in config_candidates:
        if not sim_ip and os.path.exists(cfg):
            with open(cfg) as f:
                m = re.search(r'simulator_ip:\s*"([^"]+)"', f.read())
                if m and m.group(1):
                    sim_ip = m.group(1)
                    break
    sim_ip = sim_ip or "127.0.0.1"

    bx, by = sc["ball"]
    blue_robots = sc["blue"]
    yellow_robots = sc["yellow"]

    all_robots = [
        *( (rid, x, y, deg, False, on) for rid, x, y, deg, on in blue_robots ),
        *( (rid, x, y, deg, True, on) for rid, x, y, deg, on in yellow_robots ),
    ]

    vision_ip, ball_mm, blues, yellows = read_vision()
    target_ips = list(dict.fromkeys([ip for ip in [sim_ip, vision_ip, "127.0.0.1", "172.17.0.1", "172.17.0.2"] if ip]))
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def is_positioned(b_mm, bl_map, yl_map):
        if b_mm is None or math.hypot(b_mm[0] - bx * 1000.0, b_mm[1] - by * 1000.0) > 150.0:
            return False
        for rid, tx, ty, _, _ in blue_robots:
            if rid not in bl_map or math.hypot(bl_map[rid][0] - tx * 1000.0, bl_map[rid][1] - ty * 1000.0) > 150.0:
                return False
        for rid, tx, ty, _, _ in yellow_robots:
            if rid not in yl_map or math.hypot(yl_map[rid][0] - tx * 1000.0, yl_map[rid][1] - ty * 1000.0) > 150.0:
                return False
        return True

    # Tentativa 1: grSim_Packet na porta 20011 (metros)
    pkt_20011 = build_grsim_packet(bx, by, all_robots, 1.0)
    for ip in target_ips:
        for _ in range(3):
            try:
                sock.sendto(pkt_20011, (ip, 20011))
            except Exception:
                pass
    time.sleep(0.12)
    _, ball_mm, blues, yellows = read_vision()

    # Tentativa 2: SimulatorCommand na porta 10300 (metros)
    if not is_positioned(ball_mm, blues, yellows):
        pkt_10300_m = build_sim_cmd_packet(bx, by, all_robots, 1.0)
        for ip in target_ips:
            for _ in range(3):
                try:
                    sock.sendto(pkt_10300_m, (ip, 10300))
                except Exception:
                    pass
        time.sleep(0.12)
        _, ball_mm, blues, yellows = read_vision()

    # Tentativa 3: SimulatorCommand na porta 10300 (milímetros) + 20011
    if not is_positioned(ball_mm, blues, yellows):
        pkt_10300_mm = build_sim_cmd_packet(bx, by, all_robots, 1000.0)
        for ip in target_ips:
            for _ in range(3):
                try:
                    sock.sendto(pkt_10300_mm, (ip, 10300))
                    sock.sendto(pkt_20011, (ip, 20011))
                except Exception:
                    pass
        time.sleep(0.12)
        _, ball_mm, blues, yellows = read_vision()

    sock.close()

    _, ball_mm, blues, yellows = read_vision()
    print(f"[Cenário {scenario_id}] Estado SSL-Vision após setup:")
    print(f"  - Bola: {ball_mm}")
    print(f"  - Robôs Azuis:   { {k: (round(v[0]), round(v[1])) for k, v in blues.items()} }")
    print(f"  - Robôs Amarelos: { {k: (round(v[0]), round(v[1])) for k, v in yellows.items()} }")
    print(f"[Cenário {scenario_id}] Setup de posições iniciais finalizado!")

if __name__ == "__main__":
    sid = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    setup_scenario(sid)
