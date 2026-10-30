"""Figuras de arquitetura de software, fluxos e plano."""
from fig_lib import *
import numpy as np

NOVO = 'color="#e8782a", penwidth=2.4, style="rounded,filled,bold", fillcolor="#fff3e6"'
EXIST = 'color="#0b3c5d", fillcolor="#ffffff"'


def f_capa():
    fig, ax = plt.subplots(figsize=(7, 4.6))
    ax.axis("off"); ax.set_xlim(0, 10); ax.set_ylim(0, 6.6)
    def no(x, y, w=1.5, h=0.6, c="#9fc3dd", fc=(1, 1, 1, 0.07)):
        ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2), w, h, boxstyle="round,pad=0.02,rounding_size=0.15", fc=fc, ec=c, lw=1.6))
    pos = {0: (5, 5.9), 1: (2.3, 4.4), 2: (7.7, 4.4), 3: (1, 2.7), 4: (3.6, 2.7), 5: (6.4, 2.7), 6: (9, 2.7), 7: (0.3, 1.0), 8: (1.7, 1.0), 9: (3.2, 1.0), 10: (4.2, 1.0), 11: (5.9, 1.0), 12: (7.2, 1.0), 13: (8.5, 1.0), 14: (9.6, 1.0)}
    ed = [(0, 1), (0, 2), (1, 3), (1, 4), (2, 5), (2, 6), (3, 7), (3, 8), (4, 9), (4, 10), (5, 11), (5, 12), (6, 13), (6, 14)]
    for a, b in ed:
        ax.plot([pos[a][0], pos[b][0]], [pos[a][1], pos[b][1]], color="#6f9ec2", lw=1.4, zorder=1)
    for k, (x, y) in pos.items():
        if k == 0:
            ax.add_patch(FancyBboxPatch((x - 0.9, y - 0.32), 1.8, 0.64, boxstyle="round,pad=0.02,rounding_size=0.15", fc="#e8782a", ec="white", lw=1.6, zorder=3))
        elif k in (1, 2):
            ax.add_patch(FancyBboxPatch((x - 0.8, y - 0.3), 1.6, 0.6, boxstyle="round,pad=0.02,rounding_size=0.15", fc="#2a6fb0", ec="white", lw=1.4, zorder=3))
        elif k in (3, 4, 5, 6):
            ax.add_patch(FancyBboxPatch((x - 0.6, y - 0.26), 1.2, 0.52, boxstyle="round,pad=0.02,rounding_size=0.15", fc="#4d8cc6", ec="white", lw=1.2, zorder=3))
        else:
            ax.add_patch(Circle((x, y), 0.3, fc="#d7e6f2", ec="white", lw=1.2, zorder=3))
    salvar(fig, "capa_arvore", transparent=True)


def f_camadas():
    fig, ax = plt.subplots(figsize=(11, 5.3)); ax.axis("off"); ax.set_xlim(0, 11); ax.set_ylim(0, 5.5)
    cards = [("1  Percepção", "SSL-Vision (câmeras)\nGame Controller (árbitro)", "#4d8cc6", 0.2, 3.0),
             ("2  Interpretação", "game_observer: unidades e lado\nKalman: posição, velocidade", "#2a6fb0", 3.9, 3.0),
             ("3  Decisão", "role_assigner: papéis\nBehavior Tree: ação do momento", LARANJA, 7.6, 3.0),
             ("4  Planejamento", "D* Lite: rota sem colisões\naté o alvo da árvore", VERDE, 7.6, 0.3),
             ("5  Controle", "pure pursuit, chute, halt\núnico escritor de comandos", "#8a6bbf", 3.9, 0.3),
             ("6  Atuação", "grSim / Ra / rádio NRF24\n→ robôs", CINZA, 0.2, 0.3)]
    for t, d, c, x, y in cards:
        ax.add_patch(FancyBboxPatch((x, y), 3.2, 2.1, boxstyle="round,pad=0.02,rounding_size=0.18", fc=c, ec="none"))
        ax.text(x + 0.22, y + 1.65, t, color="white", fontsize=12.5, weight="bold", va="center")
        ax.text(x + 0.22, y + 0.8, d, color="white", fontsize=9.6, va="center", linespacing=1.5)
    def arr(p, q): ax.add_patch(FancyArrowPatch(p, q, arrowstyle="-|>", mutation_scale=18, color="#35434e", lw=2))
    arr((3.45, 4.05), (3.85, 4.05)); arr((7.15, 4.05), (7.55, 4.05)); arr((9.2, 2.95), (9.2, 2.5)); arr((7.55, 1.35), (7.15, 1.35)); arr((3.85, 1.35), (3.45, 1.35))
    ax.text(5.5, 5.35, "dados fluem dos sensores para os atuadores", ha="center", fontsize=9, color="#5b6770", style="italic")
    salvar(fig, "visao_geral_camadas")


def f_processos():
    grafo('''
  subgraph cluster_global { label="Processos únicos da equipe"; style="rounded,filled"; fillcolor="#f3f7fb"; color="#9db6cc"; fontsize=11;
    br [label="pontes SSL\\n(visão + árbitro)"]; obs [label="game_observer\\n_node"]; kf [label="kalman_filter\\n_node"]; ra [label="role_assigner\\n_node"]; {rank=same; br; obs; kf; ra;} }
  subgraph cluster_r0 { label="Um conjunto por robô (i = 0, 1, 2)"; style="rounded,filled"; fillcolor="#fff7ee"; color="#e8b98d"; fontsize=11;
    sn [label="strategy_node_i\\n(BT + blackboard)", fillcolor="#fde7d3"]; ds [label="d_star_planner\\n_node_i"]; mc [label="path_follower\\n_node_i"]; com [label="driver de\\ncomunicação"]; {rank=same; sn; ds; mc; com;} }
  br -> obs [label="visão"]; obs -> kf; obs -> ra;
  br -> sn [label="árbitro"]; obs -> sn [label="/game_data"]; kf -> sn [label="predições"]; ra -> sn [label="papéis"];
  sn -> ds [label="/robot_goal"]; ds -> mc [label="path"]; mc -> com [label="/robot_commands"];
  sn -> mc [dir=both, label="override  ⇄  status", constraint=false, color="#e8782a", fontcolor="#b25a14"];
''', "arquitetura_processos", rankdir="TB", nodesep=0.5, ranksep=1.0)


def f_fluxo():
    grafo('''
  a [label="Câmeras\\nSSL-Vision\\n~60 Hz"]; b [label="vision_bridge\\n+ observer\\n(mm, rad)"]; c [label="/game_data\\n(só publica com bola)"];
  d [label="Kalman\\nposição + velocidade\\n+ aceleração"]; e [label="strategy_node\\ntick a 60 Hz"]; f [label="/robot_goal\\n(muda >2 mm)"]; g [label="D*\\n10 Hz (40 Hz perto da bola)"];
  h [label="path follower\\n20 Hz"]; i [label="/robot_commands\\n(m/s global)"]; j [label="grSim / rádio\\nrobô"];
  a -> b -> c -> d -> e -> f -> g -> h -> i -> j;
  c -> e [constraint=false, style=dashed, label="blackboard"];
  e -> h [constraint=false, style=dashed, label="override: halt / chute / alinhar"];
''', "fluxo_dados", rankdir="LR", nodesep=0.35, ranksep=0.4)


def f_estados_gc():
    grafo('''
  node [shape=box, style="rounded,filled"];
  subgraph cluster_h { label="Halted — ninguém se move"; style="rounded,filled"; fillcolor="#f9e3e0"; color="#d99a92";
    halt [label="Halt", fillcolor="#f5c2bc"]; timeout [label="Timeout\\n(equipes livres)", fillcolor="#f5c2bc"]; }
  subgraph cluster_s { label="Stopped — bola proibida, v < 0,75 m/s"; style="rounded,filled"; fillcolor="#fdf3d9"; color="#e1c777";
    stop [label="Stop", fillcolor="#fbe7a1"]; bp [label="BallPlacement", fillcolor="#fbe7a1"]; pk [label="PrepareKickoff", fillcolor="#fbe7a1"]; pp [label="PreparePenalty", fillcolor="#fbe7a1"]; }
  subgraph cluster_r { label="Running — jogo"; style="rounded,filled"; fillcolor="#e3f3e8"; color="#8fcaa4";
    kick [label="Kickoff", fillcolor="#bfe8c9"]; pen [label="Penalty", fillcolor="#bfe8c9"]; fk [label="FreeKick", fillcolor="#bfe8c9"]; run [label="Run", fillcolor="#bfe8c9"]; }
  any [label="qualquer estado", shape=ellipse, fillcolor="#eceff1"];
  any -> halt [label="HALT"]; halt -> stop [label="STOP"];
  stop -> timeout [label="TIMEOUT"]; timeout -> stop [label="STOP"];
  stop -> bp [label="BALL_PLACEMENT"]; bp -> stop [label="STOP"]; bp -> fk [label="continua"];
  stop -> pk [label="PREPARE_KICKOFF"]; pk -> kick [label="NORMAL_START"]; kick -> run [label="bola move 0,05 m\\nou 10 s"];
  stop -> pp [label="PREPARE_PENALTY"]; pp -> pen [label="NORMAL_START"]; pen -> stop [label="10 s"];
  stop -> fk [label="DIRECT_FREE"]; fk -> run [label="bola move 0,05 m\\nou 10 s"];
  stop -> run [label="FORCE_START"]; run -> stop [label="STOP"];
''', "maquina_estados_gc", rankdir="TB", nodesep=0.35, ranksep=0.8)


def f_override():
    grafo('''
  subgraph cluster_bt { label="Folhas da árvore"; style="rounded,filled"; fillcolor="#fff7ee"; color="#e8b98d";
    h [label="Halt"]; k [label="KickBall\\nGoalkeeper"]; a [label="AlignToBall"]; g [label="GoToPoint\\n(só /robot_goal)"]; }
  ov [label="/robot_motion_override\\n(modo \\"pegajoso\\", expira em 200 ms)", shape=note, fillcolor="#fffbe6", color="#d4c36a"];
  subgraph cluster_mc { label="movement_calculation_node (único escritor de /robot_commands)"; style="rounded,filled"; fillcolor="#f3f7fb"; color="#9db6cc";
    m1 [label="1  MODE_HALT\\n→ velocidades zero", fillcolor="#f5c2bc"]; m2 [label="2  MODE_KICK\\n→ máquina de chute", fillcolor="#fde7d3"]; m3 [label="3  MODE_ALIGN_*\\n→ gira no lugar", fillcolor="#fbe7a1"]; m4 [label="4  MODE_NONE\\n→ segue a rota do D*", fillcolor="#bfe8c9"]; }
  h -> ov [label="HALT"]; k -> ov [label="KICK"]; a -> ov [label="ALIGN"]; ov -> m1; m1 -> m2 [style=dashed, label="se não"]; m2 -> m3 [style=dashed, label="se não"]; m3 -> m4 [style=dashed, label="se não"];
  g -> m4 [label="/robot_goal → D* → path"];
  out [label="/robot_commands", fillcolor="#e8f0f7"]; m1 -> out; m2 -> out; m3 -> out; m4 -> out;
''', "override_modos", rankdir="TB", nodesep=0.3, ranksep=0.6)


def f_chute():
    grafo('''
  idle [label="IDLE\\nesperando pedido", fillcolor="#eceff1"];
  fire [label="FIRING (200 ms)\\nkick_speed + avanço 0,5 m/s\\nna direção do heading", fillcolor="#fde7d3"];
  cool [label="Cooldown (600 ms)\\nrobô parado", fillcolor="#fbe7a1"];
  idle -> fire [label="MODE_KICK recebido\\ne cooldown vencido"];
  fire -> cool [label="fim da janela\\nkick_fire_count++"];
  cool -> idle [label="600 ms"];
  leaf [label="KickBall\\n(onStart guarda o contador)", fillcolor="#fff7ee", color="#e8b98d"]; ok [label="SUCCESS quando o contador sobe", shape=note, fillcolor="#e1f3e8", color="#8fcaa4"];
  leaf -> idle [style=dashed, label="reenvia MODE_KICK\\na cada tick"]; fire -> ok [style=dashed, constraint=false];
''', "maquina_chute", rankdir="TB", nodesep=0.5, ranksep=0.8)


def f_pipeline_movimento():
    grafo('''
  a [label="GoToPoint\\nonStart / onRunning", fillcolor="#fff7ee", color="#e8b98d"];
  b [label="1  Clamp da área\\n(fora da pequena área ±100 mm)"];
  c [label="2  Converte mm → m\\nmonta RobotGoal\\n(pose, planner, latch)"];
  d [label="/robot_goal"];
  e [label="D* ou linha reta\\n(+ desvio da bola)"];
  f [label="/robot_i/path"];
  g [label="Pure pursuit\\n(lookahead 100 mm)"];
  h [label="Controle P angular\\n+ velocidade linear"];
  i [label="Repulsão de contato\\n+ clamp da área"];
  j [label="/robot_commands"];
  a -> b -> c -> d -> e -> f -> g -> h -> i -> j;
''', "pipeline_movimento", rankdir="LR", nodesep=0.3, ranksep=0.35)


def f_strategy_node():
    grafo('''
  subgraph cluster_sn { label="strategy_node_i  (processo ROS 2)"; style="rounded,filled"; fillcolor="#f8fafc"; color="#9db6cc"; fontsize=11;
    subgraph cluster_cb { label="thread do executor (callbacks)"; style="rounded,filled"; fillcolor="#eef3f8"; color="#b4c7d8";
      cb1 [label="game_callback\\npose, bola, velocidade, posse"]; cb2 [label="gc_callback\\ncomando, estágio, ponto designado"]; cb3 [label="geometry_callback\\ncampo, gols, áreas"]; cb4 [label="role_callback\\natacante / defensor"]; }
    bb [label="Blackboard\\n(chaves compartilhadas)", shape=cylinder, fillcolor="#fffbe6", color="#d4c36a"];
    subgraph cluster_tk { label="thread principal (tick a 60 Hz)"; style="rounded,filled"; fillcolor="#fff7ee"; color="#e8b98d";
      tick [label="tree.tickOnce()"]; arv [label="Árvore XML\\n(master_strategy_carry)", fillcolor="#fde7d3"]; }
    cb1 -> bb; cb2 -> bb; cb3 -> bb; cb4 -> bb; bb -> tick [label="leitura"]; tick -> arv;
  }
  arv -> out [label="folhas publicam\\n/robot_goal, /robot_motion_override"]; out [label="tópicos ROS 2", shape=note, fillcolor="#e8f0f7"];
  g2 [label="Groot2\\nporta 1667+id (azul)\\n1677+id (amarelo)", shape=note, fillcolor="#e1f3e8", color="#8fcaa4"]; arv -> g2 [style=dashed];
''', "strategy_node_estrutura", rankdir="TB", nodesep=0.3, ranksep=0.6)


def f_no_ros_vs_bt():
    grafo('''
  subgraph cluster_p { label="Processo strategy_node_1 (executável)"; style="rounded,filled"; fillcolor="#f8fafc"; color="#9db6cc";
    nd [label="rclcpp::Node \\"strategy_node_1\\"\\n(publishers, subscriptions, parâmetros)", fillcolor="#e8f0f7"];
    subgraph cluster_bt { label="Behavior Tree (objetos C++, não são nós ROS)"; style="rounded,filled"; fillcolor="#fff7ee"; color="#e8b98d";
      a [label="Sequence"]; b [label="IsBallClose"]; c [label="GoToPoint"]; a -> b; a -> c; }
    c -> nd [label="recebe shared_ptr<Node>\\ne cria seu publisher /robot_goal", style=dashed];
  }
  out [label="/robot_goal", shape=note, fillcolor="#e1f3e8", color="#8fcaa4"]; nd -> out;
''', "no_ros_vs_no_bt", rankdir="TB", nodesep=0.35, ranksep=0.8)


def f_hibrida():
    grafo(f'''
  subgraph cluster_ext {{ label="Entradas"; style="rounded,filled"; fillcolor="#f3f7fb"; color="#9db6cc";
    gc [label="Game Controller\\n(Referee)"]; vis [label="Visão / Observer\\n(GameData + carimbo)", {NOVO}]; }}
  subgraph cluster_team {{ label="Serviços de equipe (fora da BT)"; style="rounded,filled"; fillcolor="#eef3f8"; color="#9db6cc";
    rs [label="referee_state_node\\nGameState", {NOVO}]; ra [label="role_assigner_node\\nroles + cobrador + época", {NOVO}]; }}
  subgraph cluster_robot {{ label="Por robô"; style="rounded,filled"; fillcolor="#fff7ee"; color="#e8b98d";
    bt [label="Master Tree v2\\n(strategy_node_i)", {NOVO}]; ds [label="D*"]; sg [label="movement_calculation\\n+ SafetyGate", {NOVO}]; }}
  rad [label="Rádio / simulador"];
  gc -> rs; vis -> ra; vis -> bt; rs -> bt [label="/game_state"]; rs -> sg [label="/game_state\\n(limite de velocidade)", color="#e8782a"]; ra -> bt [label="/role_assignment"];
  bt -> ds [label="/robot_goal"]; bt -> sg [label="override"]; ds -> sg [label="path"]; sg -> rad [label="/robot_commands"];
''', "arquitetura_hibrida", rankdir="TB", nodesep=0.35, ranksep=0.7)


def f_camadas_decisao():
    fig, ax = plt.subplots(figsize=(10, 4.9))
    ax.axis("off"); ax.set_xlim(0, 10); ax.set_ylim(0, 6.2)
    cam = [("0  Segurança", "dados frescos? HALT? → parar\\nBT (SafetyGuard) + SafetyGate no controlador", VERM),
           ("1  Fase do jogo", "STOP, placement, kickoff, pênalti, free kick, jogo corrido\\nBT: ramos do mestre", LARANJA),
           ("2  Papéis", "goleiro, atacante, defensor, cobrador\\nrole_assigner (ROS) + HasRole (BT)", AZUL2),
           ("3  Comportamentos", "atacar, defender, cobrar, afastar-se\\nsubárvores", VERDE),
           ("4  Habilidades e controle", "GoToPoint, KickOnce, D*, pure pursuit\\nfolhas C++ + nós ROS 2", CINZA)]
    for i, (t, d, c) in enumerate(cam):
        y = 5.4 - i * 1.15
        ax.add_patch(FancyBboxPatch((0.2 + i * 0.25, y - 0.45), 9.4 - i * 0.5, 0.95, boxstyle="round,pad=0.02,rounding_size=0.12", fc=c, ec="none", alpha=0.92))
        ax.text(0.5 + i * 0.25, y + 0.05, t, color="white", fontsize=11, weight="bold", va="center")
        ax.text(3.6 + i * 0.1, y + 0.02, d.replace("\\n", "\n"), color="white", fontsize=8.8, va="center")
    ax.annotate("", xy=(9.85, 0.2), xytext=(9.85, 5.9), arrowprops=dict(arrowstyle="<|-", color="#5b6770", lw=1.2))
    ax.text(9.95, 3.0, "prioridade ↑", rotation=90, va="center", fontsize=9, color="#5b6770")
    salvar(fig, "camadas_decisao")


def f_mapa_comando_fase():
    grafo('''
  node [shape=box];
  subgraph cluster_c { label="Referee.command"; style="rounded,filled"; fillcolor="#f3f7fb"; color="#9db6cc";
    c0 [label="HALT (0)"]; c1 [label="STOP (1)"]; c2 [label="NORMAL_START (2)"]; c3 [label="FORCE_START (3)"];
    c4 [label="PREPARE_KICKOFF_Y/B (4/5)"]; c6 [label="PREPARE_PENALTY_Y/B (6/7)"]; c8 [label="DIRECT_FREE_Y/B (8/9)"];
    c12 [label="TIMEOUT_Y/B (12/13)"]; c16 [label="BALL_PLACEMENT_Y/B (16/17)"]; cl [label="INDIRECT (10/11), GOAL (14/15)\\nlegados", fillcolor="#eceff1"]; }
  subgraph cluster_p { label="GameState.phase"; style="rounded,filled"; fillcolor="#fff3e6"; color="#e8b98d";
    p0 [label="HALT", fillcolor="#f5c2bc"]; p1 [label="STOP", fillcolor="#fbe7a1"]; p2 [label="KICKOFF  ou  PENALTY\\n(depende do PREPARE anterior)", fillcolor="#bfe8c9"];
    p3 [label="RUN", fillcolor="#bfe8c9"]; p4 [label="PREPARE_KICKOFF", fillcolor="#fbe7a1"]; p6 [label="PREPARE_PENALTY", fillcolor="#fbe7a1"]; p8 [label="FREE_KICK", fillcolor="#bfe8c9"];
    p12 [label="TIMEOUT", fillcolor="#f5c2bc"]; p16 [label="BALL_PLACEMENT", fillcolor="#fbe7a1"]; }
  c0 -> p0; c1 -> p1; c2 -> p2 [label="restart_ctx"]; c3 -> p3; c4 -> p4 [label="we_favored = cor"]; c6 -> p6 [label="we_favored = cor"]; c8 -> p8 [label="we_favored = cor"];
  c12 -> p12; c16 -> p16 [label="we_favored = cor"]; cl -> p8 [style=dashed, label="10/11 → FREE_KICK"]; cl -> p1 [style=dashed, label="14/15 → STOP"];
''', "mapa_comando_fase", rankdir="LR", nodesep=0.22, ranksep=1.2)


def f_game_state_pipeline():
    grafo(f'''
  a [label="Referee\\n(ssl_league_msgs)"]; b [label="1  Descarta repetidas\\ne antigas\\n(command_counter)", {NOVO}];
  c [label="2  Mapeia comando → fase", {NOVO}]; d [label="3  Memoriza o contexto\\ndo reinício\\n(PREPARE → NORMAL_START)", {NOVO}];
  e [label="4  Deriva flags:\\nwe_favored, speed_limit,\\nball_min_distance, can_place_ball", {NOVO}]; f [label="5  Lado do campo\\n(blue_team_on_positive_half)", {NOVO}];
  g [label="6  Marca stale se o GC\\ncalar > 500 ms", {NOVO}]; h [label="/game_state\\n(reliable, transient_local)", fillcolor="#e1f3e8", color="#8fcaa4"];
  a -> b -> c -> d -> e -> f -> g -> h;
''', "game_state_pipeline", rankdir="LR", nodesep=0.3, ranksep=0.35)


def f_safety_gate():
    grafo(f'''
  a [label="path follower\\n(velocidade desejada)"]; b [label="repulsão + clamp de área"];
  c [label="SafetyGate", {NOVO}]; 
  d1 [label="HALT ⇒ velocidade = 0", {NOVO}]; d2 [label="módulo de v ≤ speed_limit\\n(0,75 em STOP; 1,5 no jogo)", {NOVO}];
  d3 [label="watchdog: sem goal/override\\npor 500 ms ⇒ zero", {NOVO}]; d4 [label="kick_speed ≤ 3,0 m/s", {NOVO}];
  e [label="/robot_commands"];
  gs [label="/game_state", shape=note, fillcolor="#e1f3e8", color="#8fcaa4"];
  a -> b -> c; gs -> c [style=dashed]; c -> d1 -> d2 -> d3 -> d4 -> e;
''', "safety_gate", rankdir="LR", nodesep=0.3, ranksep=0.35)


def f_blackboard_fluxo():
    grafo(f'''
  subgraph cluster_in {{ label="Fontes (callbacks ROS 2)"; style="rounded,filled"; fillcolor="#f3f7fb"; color="#9db6cc";
    s1 [label="/game_state"]; s2 [label="/game_data"]; s3 [label="/role_assignment"]; s4 [label="/field_geometry"]; }}
  snap [label="refresh() no início de cada tick\\n(snapshot imutável)", {NOVO}];
  subgraph cluster_bb {{ label="Blackboard (raiz)"; style="rounded,filled"; fillcolor="#fffbe6"; color="#d4c36a";
    k1 [label="phase\\nrestart_ctx\\nwe_favored"]; k2 [label="robot_pose\\nball, ball_vel"]; k3 [label="role\\nkicker_id, epoch"]; k4 [label="own_goal_x\\nside_sign, field_*"]; k5 [label="gc_age_ms\\npose_age_ms\\nball_age_ms"]; }}
  subgraph cluster_n {{ label="Consumidores"; style="rounded,filled"; fillcolor="#fff7ee"; color="#e8b98d";
    n1 [label="CheckGameState\\nWeAreFavored"]; n2 [label="HasRole"]; n3 [label="GoToPoint\\nComputeLegalSlot"]; n4 [label="IsDataFresh"]; }}
  s1 -> snap; s2 -> snap; s3 -> snap; s4 -> snap; snap -> k1; snap -> k2; snap -> k3; snap -> k4; snap -> k5;
  k1 -> n1; k3 -> n2; k2 -> n3; k4 -> n3; k5 -> n4;
''', "blackboard_fluxo", rankdir="TB", nodesep=0.18, ranksep=0.7)


def f_piramide():
    fig, ax = plt.subplots(figsize=(9, 4.6)); ax.axis("off"); ax.set_xlim(0, 10); ax.set_ylim(0, 6)
    niveis = [("Partidas completas simuladas", "2 × 5 min, sem faltas por causa do software", LARANJA, 1.2),
              ("Cenários de regra (grSim + Game Controller)", "um cenário por regra e por transição", "#d9a400", 2.6),
              ("Integração ROS 2 e Master Tree", "HALT preempta; ramo correto por fase", VERDE, 4.0),
              ("Testes unitários de folhas, condições e blackboard", "retornos, halt, dados ausentes", AZUL2, 5.4),
              ("Validação estática dos XMLs", "IDs, portas, subárvores", AZUL, 6.8)]
    for i, (t, d, c, w) in enumerate(niveis):
        y = 5.0 - i * 1.0; h = 0.9; cx = 5; w = 3.0 + i * 1.5
        ax.add_patch(FancyBboxPatch((cx - w / 2, y - h / 2), w, h, boxstyle="round,pad=0.02,rounding_size=0.1", fc=c, ec="white"))
        ax.text(cx, y + 0.12, t, ha="center", va="center", color="white", fontsize=9.2, weight="bold")
        ax.text(cx, y - 0.22, d, ha="center", va="center", color="white", fontsize=7.8)
    ax.text(9.6, 5.0, "poucos,\nlentos", ha="right", fontsize=8.5, color="#5b6770"); ax.text(9.6, 1.0, "muitos,\nrápidos", ha="right", fontsize=8.5, color="#5b6770")
    salvar(fig, "piramide_testes")


def f_gantt():
    fig, ax = plt.subplots(figsize=(11, 5.3))
    tarefas = [
        ("Contratos e GameState (G01–G05)", 0, 1, AZUL), ("Dados: stamp, blackboard, lado (D01, D03)", 0, 1.6, AZUL2),
        ("SafetyGate e correções de movimento (M01–M04)", 0, 1.8, VERM), ("Harness e validador de XML (T01–T03)", 0, 1.2, VERDE),
        ("Master v2: segurança, HALT, TIMEOUT, STOP (A01–A02, E01–E02)", 0.4, 1.9, LARANJA),
        ("Kickoff, free kick, ball placement (E03–E08)", 1, 3, LARANJA), ("Papéis e goleiro (P01–P02, K01)", 1, 2.6, AZUL2),
        ("Pênalti (E06, K02) e degradação (P03)", 2, 3.6, LARANJA), ("Montagem final da Master (A06)", 2.4, 3.2, AZUL),
        ("Testes de integração e cenários (T04–T06)", 1.4, 3.6, VERDE), ("Partidas completas, regressão, ajustes (T07–T09)", 3, 4, VERDE),
    ]
    for i, (n, a, b, c) in enumerate(tarefas):
        y = len(tarefas) - i
        ax.barh(y, b - a, left=a, height=0.62, color=c, alpha=0.9)
        ax.text(a + 0.03, y, n, va="center", ha="left", fontsize=8, color="white" if (b - a) > 1.6 else "#26333d") if (b - a) > 1.6 else ax.text(b + 0.04, y, n, va="center", ha="left", fontsize=8, color="#26333d")
    ax.set_xlim(0, 5.7); ax.set_ylim(0.2, len(tarefas) + 1)
    ax.set_xticks([0.5, 1.5, 2.5, 3.5]); ax.set_xticklabels(["Semana 1", "Semana 2", "Semana 3", "Semana 4"])
    for x in (1, 2, 3): ax.axvline(x, color="#cfd6dc", lw=1)
    ax.set_yticks([]); 
    for s in ("top", "right", "left"): ax.spines[s].set_visible(False)
    salvar(fig, "gantt_4_semanas")


def f_dependencias():
    grafo('''
  node [shape=box];
  g1 [label="G01 GameState.msg", fillcolor="#fde7d3"]; g2 [label="G02 referee_state_node", fillcolor="#fde7d3"];
  d3 [label="D03 blackboard + lado", fillcolor="#fde7d3"]; m1 [label="M01 SafetyGate", fillcolor="#f5c2bc"];
  a1 [label="A01 condições novas"]; m3 [label="M03 GoToPoint"]; m4 [label="M04 KeepDistance /\\nHoldPosition"]; e1 [label="E01 StopTree"];
  a2 [label="A02 Master v2 (esqueleto)", fillcolor="#bfe8c9"]; e8 [label="E08 KickOnce +\\nRestartKicker"]; m2 [label="M02 PrecisionKick"];
  e5 [label="E05 Kickoff"]; e6 [label="E06 Pênalti"]; e7 [label="E07 Free kick"]; k2 [label="K02 Goleiro pênalti"]; p2 [label="P02 Papéis ampliados"];
  a6 [label="A06 Master completa", fillcolor="#bfe8c9"]; t7 [label="T07 Conformidade"]; t9 [label="T09 Partidas simuladas", fillcolor="#bfe8c9"];
  g1 -> g2 -> a1; d3 -> a1; g1 -> m1; m1 -> m4; m3 -> e1; m4 -> e1; a1 -> a2; e1 -> a2; m1 -> m2 -> e8; e8 -> e5; p2 -> e5; e1 -> e5; e5 -> e6; k2 -> e6; e5 -> e7;
  a2 -> a6; e5 -> a6; e6 -> a6; e7 -> a6; a6 -> t7 -> t9;
''', "grafo_dependencias", rankdir="TB", nodesep=0.22, ranksep=0.55)


def f_mapa_manual():
    grafo('''
  node [shape=box, style="rounded,filled"];
  p1 [label="Parte I\\nA partida e o ecossistema\\n(caps. 1–3)", fillcolor="#dbe9f6"];
  p2 [label="Parte II\\nBehavior Trees\\n(caps. 4–5)", fillcolor="#e1f3e8"];
  p3 [label="Parte III\\nO sistema atual\\n(caps. 6–13)", fillcolor="#fde7d3"];
  p4 [label="Parte IV\\nA Master Tree de jogo completo\\n(caps. 14–21)", fillcolor="#fbe7a1"];
  p5 [label="Parte V\\nImplementação\\n(caps. 22–24)", fillcolor="#e9e2f7"];
  p1 -> p2 -> p3 -> p4 -> p5;
''', "mapa_do_manual", rankdir="LR", nodesep=0.3, ranksep=0.4)


def _snake(nome, defs, linhas, extra=""):
    corpo = defs + "".join("  {rank=same; " + " -> ".join(l) + ";}\n" for l in linhas)
    n = max(len(l) for l in linhas)
    for k in range(n):
        col = [l[k] for l in linhas if len(l) > k]
        if len(col) > 1:
            corpo += "  " + " -> ".join(col) + " [style=invis, weight=60];\n"
    for a_, b_ in zip(linhas, linhas[1:]):
        corpo += f"  {a_[-1]} -> {b_[0]} [constraint=false];\n"
    grafo(corpo + extra, nome, rankdir="TB", nodesep=0.45, ranksep=0.6)


def f_fluxo():
    _snake("fluxo_dados", '''
  a [label="Câmeras\\nSSL-Vision\\n~60 Hz"]; b [label="vision_bridge\\n+ observer\\n(mm, rad)"]; c [label="/game_data\\n(só publica com bola)"];
  d [label="Kalman\\nposição, velocidade,\\naceleração"]; e [label="strategy_node\\ntick a 60 Hz"]; f [label="/robot_goal\\n(muda > 2 mm)"];
  g [label="D*\\n10 Hz (40 Hz perto\\nda bola)"]; h [label="path follower\\n20 Hz"]; i [label="/robot_commands\\n(m/s global)"]; j [label="grSim / rádio\\n→ robô"];
''', [list("abc"), list("def"), list("ghi"), list("j")])


def f_pipeline_movimento():
    _snake("pipeline_movimento", '''
  a [label="GoToPoint\\nonStart / onRunning", fillcolor="#fff7ee", color="#e8b98d"];
  b [label="1  Clamp da área\\n(fora da pequena área, ±100 mm)"];
  c [label="2  mm → m, monta RobotGoal\\n(pose, planner, latch)"]; d [label="/robot_goal"]; e [label="D* ou linha reta\\n(+ desvio da bola)"];
  f [label="/robot_i/path"]; g [label="Pure pursuit\\n(lookahead 100 mm)"]; h [label="Controle P angular\\n+ velocidade linear"];
  i [label="Repulsão de contato\\n+ clamp da área"]; j [label="/robot_commands"];
''', [list("abc"), list("def"), list("ghi"), list("j")])


def f_game_state_pipeline():
    _snake("game_state_pipeline", f'''
  a [label="Referee\\n(ssl_league_msgs)"]; b [label="1  Descarta repetidas\\ne antigas\\n(command_counter)", {NOVO}];
  c [label="2  Mapeia\\ncomando → fase", {NOVO}]; d [label="3  Memoriza o contexto\\ndo reinício", {NOVO}];
  e [label="4  Deriva flags:\\nwe_favored, speed_limit,\\nball_min_distance", {NOVO}]; f [label="5  Lado do campo\\n(blue_team_on_positive_half)", {NOVO}];
  g [label="6  Marca stale se o GC\\ncalar > 500 ms", {NOVO}]; h [label="/game_state\\n(reliable, transient_local)", fillcolor="#e1f3e8", color="#8fcaa4"];
''', [list("abc"), list("def"), list("gh")])


def f_safety_gate():
    _snake("safety_gate", f'''
  a [label="path follower\\n(velocidade desejada)"]; b [label="repulsão + clamp de área"]; c [label="SafetyGate", {NOVO}];
  d1 [label="HALT ⇒ velocidade = 0", {NOVO}]; d2 [label="|v| ≤ speed_limit\\n(0,75 em STOP; 1,5 no jogo)", {NOVO}];
  d3 [label="watchdog: sem goal/override\\npor 500 ms ⇒ zero", {NOVO}]; d4 [label="kick_speed ≤ 3,0 m/s", {NOVO}]; e [label="/robot_commands"];
  gs [label="/game_state", shape=note, fillcolor="#e1f3e8", color="#8fcaa4"];
''', [["gs", "a", "b"], ["c", "d1", "d2"], ["d3", "d4", "e"]], "  gs -> c [style=dashed, constraint=false];\n")


if __name__ == "__main__":
    for f in [f_capa, f_camadas, f_processos, f_fluxo, f_estados_gc, f_override, f_chute, f_pipeline_movimento, f_strategy_node,
              f_no_ros_vs_bt, f_hibrida, f_camadas_decisao, f_mapa_comando_fase, f_game_state_pipeline, f_safety_gate,
              f_blackboard_fluxo, f_piramide, f_gantt, f_dependencias, f_mapa_manual]:
        f()
