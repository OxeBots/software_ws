#!/usr/bin/env bash
# ==============================================================================
# SSL Kick Technical Challenge - Cenario 4
# Escanteio superior esquerdo (-2150, 1400) com defesa em (-2175, 750) e (-1675, 300)
# Permissao de execucao: chmod +x run_kick_scenario_4.sh
# ==============================================================================
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "${SCRIPT_DIR}/../install/setup.bash" ] || [ -d "${SCRIPT_DIR}/../src" ]; then
    WS_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
else
    WS_DIR="${SCRIPT_DIR}"
fi
cd "${WS_DIR}"

source /opt/ros/jazzy/setup.bash
if [ -f "${WS_DIR}/install/setup.bash" ]; then
    source "${WS_DIR}/install/setup.bash"
fi

echo "[Cenário 4] Posicionando bola e robôs no grSim (robôs atacantes na linha central)..."
python3 - << 'EOF'
import math, re, socket, struct, os, time

sim_ip = os.environ.get("SIMULATOR_IP", "")
if not sim_ip and os.path.exists("src/oxebots_bringup/config/match_config.yaml"):
    with open("src/oxebots_bringup/config/match_config.yaml") as f:
        m = re.search(r'simulator_ip:\s*"([^"]+)"', f.read())
        if m and m.group(1):
            sim_ip = m.group(1)
sim_ip = sim_ip or "127.0.0.1"

# Coordenadas em metros e orientacao em graus (Cenario 4: kick_challenge_4.xml)
ball = (-2.150, 1.400)
blue_robots = [
    (0, -2.175, -0.400, -45.0, True),  # Goleiro no poste inferior
    (1, -2.175,  0.750,  90.0, True),  # Defensor canto superior
    (2, -1.675,  0.300,   0.0, True),  # Defensor frontal
]
# Robos amarelos: atacantes na linha central (x=0) conforme kick.pdf (Regra 2)
yellow_robots = [
    (0,  2.000,  0.000, 180.0, True),   # Goleiro amarelo no proprio gol
    (1,  0.000, -0.500, 180.0, True),   # Robo atacante 1 na linha central
    (2,  0.000,  0.500, 180.0, True),   # Robo atacante 2 na linha central
]

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
            b = buf[i]; i += 1
            tag |= (b & 0x7F) << shift
            if not (b & 0x80): break
            shift += 7
        fnum, wtype = tag >> 3, tag & 7
        if wtype == 0:
            val, shift = 0, 0
            while i < n:
                b = buf[i]; i += 1
                val |= (b & 0x7F) << shift
                if not (b & 0x80): break
                shift += 7
            yield fnum, wtype, val
        elif wtype == 1:
            yield fnum, wtype, buf[i:i+8]; i += 8
        elif wtype == 2:
            ln, shift = 0, 0
            while i < n:
                b = buf[i]; i += 1
                ln |= (b & 0x7F) << shift
                if not (b & 0x80): break
                shift += 7
            yield fnum, wtype, buf[i:i+ln]; i += ln
        elif wtype == 5:
            yield fnum, wtype, struct.unpack("<f", buf[i:i+4])[0]; i += 4
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
                                if bf == 3: bx_d = bv
                                elif bf == 4: by_d = bv
                            if bx_d is not None and by_d is not None:
                                ball_mm = (bx_d, by_d)
                        elif df == 6 and dw == 2:
                            rid_d = rx_d = ry_d = rori_d = None
                            for rf, rw, rv in parse_fields(dv):
                                if rf == 2: rid_d = rv
                                elif rf == 3: rx_d = rv
                                elif rf == 4: ry_d = rv
                                elif rf == 5: rori_d = rv
                            if rid_d is not None and rx_d is not None and ry_d is not None:
                                yellows[rid_d] = (rx_d, ry_d, rori_d or 0.0)
                        elif df == 7 and dw == 2:
                            rid_d = rx_d = ry_d = rori_d = None
                            for rf, rw, rv in parse_fields(dv):
                                if rf == 2: rid_d = rv
                                elif rf == 3: rx_d = rv
                                elif rf == 4: ry_d = rv
                                elif rf == 5: rori_d = rv
                            if rid_d is not None and rx_d is not None and ry_d is not None:
                                blues[rid_d] = (rx_d, ry_d, rori_d or 0.0)
        return sender_ip, ball_mm, blues, yellows
    except Exception:
        return None, None, {}, {}
    finally:
        vsock.close()

bx, by = ball
all_robots = [
    *( (rid, x, y, deg, False, on) for rid, x, y, deg, on in blue_robots ),
    *( (rid, x, y, deg, True,  on) for rid, x, y, deg, on in yellow_robots ),
]

def build_grsim_packet(scale=1.0):
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

def build_sim_cmd_packet(scale=1.0):
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

def build_blue_ctrl(vels):
    pkt = b""
    for rid, vx, vy, vw in vels:
        glob_vel = field_float(1, vx) + field_float(2, vy) + field_float(3, vw)
        move_cmd = field_msg(3, glob_vel)
        rcmd = field_varint(1, rid) + field_msg(2, move_cmd) + field_float(3, 0.0) + field_float(4, 0.0) + field_float(5, 0.0)
        pkt += field_msg(1, rcmd)
    return pkt

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
pkt_20011 = build_grsim_packet(1.0)
for ip in target_ips:
    for _ in range(3):
        sock.sendto(pkt_20011, (ip, 20011))
time.sleep(0.12)
_, ball_mm, blues, yellows = read_vision()

# Tentativa 2: SimulatorCommand na porta 10300 (metros) se 20011 nao moveu
if not is_positioned(ball_mm, blues, yellows):
    pkt_10300_m = build_sim_cmd_packet(1.0)
    for ip in target_ips:
        for _ in range(3):
            sock.sendto(pkt_10300_m, (ip, 10300))
    time.sleep(0.12)
    _, ball_mm, blues, yellows = read_vision()

# Tentativa 3: SimulatorCommand na porta 10300 (milimetros) se ainda nao moveu
if not is_positioned(ball_mm, blues, yellows):
    pkt_10300_mm = build_sim_cmd_packet(1000.0)
    for ip in target_ips:
        for _ in range(3):
            sock.sendto(pkt_10300_mm, (ip, 10300))
            sock.sendto(pkt_20011, (ip, 20011))
    time.sleep(0.12)
    _, ball_mm, blues, yellows = read_vision()

# Fallback garantido para os robos azuis via porta 10301 (RobotControl) caso teleporte esteja desabilitado
if blues and not all(rid in blues and math.hypot(blues[rid][0] - tx * 1000.0, blues[rid][1] - ty * 1000.0) <= 120.0 for rid, tx, ty, _, _ in blue_robots):
    print("[Cenário 4] Movendo robôs azuis via porta 10301 (RobotControl)...")
    t0 = time.time()
    while time.time() - t0 < 3.0:
        _, _, blues = read_vision()
        cmds = []
        done = True
        for rid, tx, ty, tdeg, _ in blue_robots:
            if rid in blues:
                rx, ry, rori = blues[rid]
                dx, dy = (tx * 1000.0 - rx) / 1000.0, (ty * 1000.0 - ry) / 1000.0
                dist = math.hypot(dx, dy)
                dori = math.atan2(math.sin(math.radians(tdeg) - rori), math.cos(math.radians(tdeg) - rori))
                if dist > 0.08 or abs(dori) > 0.15:
                    done = False
                vx = max(-1.5, min(1.5, 2.5 * dx)) if dist > 0.04 else 0.0
                vy = max(-1.5, min(1.5, 2.5 * dy)) if dist > 0.04 else 0.0
                vw = max(-3.0, min(3.0, 2.5 * dori)) if abs(dori) > 0.08 else 0.0
                cmds.append((rid, vx, vy, vw))
        if cmds:
            ctrl_pkt = build_blue_ctrl(cmds)
            for ip in target_ips:
                sock.sendto(ctrl_pkt, (ip, 10301))
        if done:
            break

# Zera velocidade dos robos azuis na porta 10301
zero_pkt = build_blue_ctrl([(rid, 0.0, 0.0, 0.0) for rid in range(3)])
for ip in target_ips:
    for _ in range(3):
        sock.sendto(zero_pkt, (ip, 10301))
sock.close()

_, ball_mm, blues, yellows = read_vision()
print(f"[Cenário 4] Estado SSL-Vision após setup: Bola={ball_mm} | Azuis={ {k: (round(v[0]), round(v[1])) for k, v in blues.items()} } | Amarelos={ {k: (round(v[0]), round(v[1])) for k, v in yellows.items()} }")
EOF

cp -f --remove-destination "${WS_DIR}/src/oxebots_strategy/behavior_trees/challengs/kick_challenge_"*.xml \
      "${WS_DIR}/install/oxebots_strategy/share/oxebots_strategy/behavior_trees/" 2>/dev/null || true

exec ros2 launch oxebots_bringup ssl-new.launch.py \
  bt_xml:=kick_challenge_4.xml \
  team_color:=yellow
