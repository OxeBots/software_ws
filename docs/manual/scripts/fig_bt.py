"""Figuras de Behavior Trees: conceitos e árvores (existentes e propostas)."""
from fig_lib import *
import fig_lib as FL


def clusters(lista, nome, titulo_ranksep=0.45, nodesep=0.25, fontsize=10, dpi=200):
    """lista: [(titulo, raiz N)] -> uma figura com as árvores lado a lado (clusters)."""
    corpo = []
    for i, (tit, raiz) in enumerate(lista):
        nodes, edges = [], []
        FL._walk(raiz, "", nodes, edges, True)
        corpo.append(f'  subgraph cluster_{i} {{ label="{esc(tit)}"; labelloc=t; fontname="{FONTE}"; fontsize=11; color="#cfd6dc"; style="rounded"; margin=14;\n'
                     + "".join(nodes) + "".join(edges) + "  }\n")
    src = (f'digraph G {{ rankdir=LR; ordering=out; nodesep={nodesep}; ranksep={titulo_ranksep}; bgcolor="white";\n'
           f'  node [fontname="{FONTE}", fontsize={fontsize}, margin="0.12,0.07"];\n  edge [color="#6b7782", arrowsize=0.6];\n'
           + "".join(corpo) + "}\n")
    dot(src, nome, dpi=dpi)


def bt_conceitos():
    # Anatomia
    arvore(N("RFB", "Decidir o que fazer", [
        N("RSEQ", "Se o árbitro mandou parar", [N("COND", "Comando é HALT?"), N("ACT", "Parar o robô")]),
        N("SEQ", "Jogar", [N("COND", "Bola está perto?"), N("ACT", "Ir até a bola"), N("ACT", "Chutar")])
    ]), "bt_anatomia", legenda=True, fontsize=11)

    # Sequence
    A = lambda lab, st: N("ACT", lab, status=st)
    clusters([
        ("Tick 1", N("SEQ", "Sequence", [N("COND", "A", status="S"), A("B", "R"), A("C", "-")], status="R")),
        ("Tick 2 (B termina)", N("SEQ", "Sequence", [N("COND", "A", status="-"), A("B", "S"), A("C", "R")], status="R")),
    ], "bt_sequence")
    clusters([
        ("Tick 1", N("RSEQ", "ReactiveSequence", [N("COND", "A", status="S"), A("B", "R"), A("C", "-")], status="R")),
        ("Tick 2 (A passou a falhar)", N("RSEQ", "ReactiveSequence", [N("COND", "A", status="F"), A("B", "-"), A("C", "-")], status="F")),
    ], "bt_reactive_sequence")
    clusters([
        ("Tick 1", N("FB", "Fallback", [N("COND", "A", status="F"), A("B", "R"), A("C", "-")], status="R")),
        ("Tick 2 (A passou a ter sucesso)", N("FB", "Fallback", [N("COND", "A", status="-"), A("B", "R"), A("C", "-")], status="R")),
    ], "bt_fallback")
    clusters([
        ("Tick 1", N("RFB", "ReactiveFallback", [N("COND", "A", status="F"), A("B", "R"), A("C", "-")], status="R")),
        ("Tick 2 (A passou a ter sucesso)", N("RFB", "ReactiveFallback", [N("COND", "A", status="S"), A("B", "-"), A("C", "-")], status="S")),
    ], "bt_reactive_fallback")
    clusters([
        ("Tick 1", N("PAR", "Parallel (success=1, failure=1)", [A("A", "R"), A("B", "R")], status="R")),
        ("Tick 2 (B conclui)", N("PAR", "Parallel (success=1, failure=1)", [A("A", "-"), A("B", "S")], status="S")),
    ], "bt_parallel")

    # Decoradores (clusters pequenos)
    lista = [
        ("Inverter", N("DEC", "Inverter", [N("COND", "IsBallClose", status="F")], status="S")),
        ("RetryUntilSuccessful(-1)", N("DEC", "RetryUntilSuccessful", [N("COND", "IsBallClose", status="F")], status="R")),
        ("Repeat(-1)", N("DEC", "Repeat", [N("ACT", "GoToPoint", status="S")], status="R")),
        ("Timeout(5000 ms)", N("DEC", "Timeout", [N("ACT", "GoToPoint", status="R")], status="R")),
        ("Delay(600 ms)", N("DEC", "Delay", [N("ACT", "AlwaysSuccess", status="-")], status="R")),
        ("ForceSuccess", N("DEC", "ForceSuccess", [N("ACT", "Ação", status="F")], status="S")),
    ]
    clusters(lista, "bt_decoradores", nodesep=0.3)

    # preempção
    clusters([
        ("Tick N — jogo normal", N("RFB", "Mestre", [
            N("RSEQ", "Ramo HALT", [N("COND", "cmd == HALT?", status="F"), N("SUB", "HaltTree", status="-")], status="F"),
            N("RSEQ", "Ramo ATACANTE", [N("COND", "papel atacante?", status="S"), N("ACT", "GoToPoint", status="R")], status="R")], status="R")),
        ("Tick N+1 — chega o HALT", N("RFB", "Mestre", [
            N("RSEQ", "Ramo HALT", [N("COND", "cmd == HALT?", status="S"), N("SUB", "HaltTree", status="S")], status="S"),
            N("RSEQ", "Ramo ATACANTE", [N("COND", "papel atacante?", status="-"), N("ACT", "GoToPoint\nhalt() → onHalted()", status="-")], status="-")], status="S")),
    ], "bt_preempcao_halt")

    # ciclo de vida de nó assíncrono
    grafo('''
  idle [label="IDLE\\n(não está executando)", fillcolor="#eceff1"];
  start [label="onStart()", shape=ellipse, fillcolor="#e8f0f7"];
  run [label="RUNNING", fillcolor="#fbe7a1"];
  onrun [label="onRunning()", shape=ellipse, fillcolor="#e8f0f7"];
  ok [label="SUCCESS", fillcolor="#bfe8c9"];
  fail [label="FAILURE", fillcolor="#f5c2bc"];
  halted [label="onHalted()\\n(limpeza)", shape=ellipse, fillcolor="#fde7d3"];
  idle -> start [label="primeiro tick"];
  start -> run [label="retorna RUNNING"];
  start -> ok [label="já concluiu"];
  start -> fail [label="erro"];
  run -> onrun [label="próximo tick"];
  onrun -> run [label="RUNNING"];
  onrun -> ok [label="chegou"];
  onrun -> fail [label="falhou"];
  run -> halted [label="pai interrompe\\n(halt)", color="#e8782a", fontcolor="#b25a14"];
  halted -> idle;
  ok -> idle [style=dashed, label="reset"]; fail -> idle [style=dashed, label="reset"];
''', "ciclo_stateful_action", rankdir="LR", nodesep=0.45, ranksep=0.65)

    # blackboard e subárvores
    grafo('''
  subgraph cluster_root { label="Blackboard da árvore principal"; style="rounded,filled"; fillcolor="#f3f7fb"; color="#9db6cc";
    r1 [label="ball_x = 812.0"]; r2 [label="ball_y = −140.0"]; r3 [label="robot_id = 1"]; r4 [label="my_goal_x = −2250"]; }
  subgraph cluster_sub { label="Blackboard da SubTree"; style="rounded,filled"; fillcolor="#fff7ee"; color="#e8b98d";
    s1 [label="bola_x  (porta)"]; s2 [label="bola_y  (porta)"]; s3 [label="pkx  (local)"]; }
  r1 -> s1 [label="bola_x=\\"{ball_x}\\""];
  r2 -> s2 [label="bola_y=\\"{ball_y}\\""];
  r3 -> r3 [style=invis];
  note [shape=note, fillcolor="#fffbe6", color="#d4c36a", label="_autoremap=\\"true\\" copia, com o mesmo nome,\\ntodas as chaves que já existem na raiz\\n(chaves novas da subárvore ficam só nela)"];
  s3 -> note [style=invis];
''', "fluxo_blackboard_subtree", rankdir="LR", nodesep=0.3, ranksep=1.0)


def arvores_atuais():
    cmd = lambda c: N("COND", f"cmd == {c}")
    # Mestre atual (master_strategy_carry.xml) - o laço do atacante fica em figura própria
    raiz = N("RFB", "MasterStrategy", [
        N("SEQ", "HaltBranch", [cmd("0 (HALT)"), N("SUB", "HaltSubTree")]),
        N("SEQ", "StopBranch", [cmd("1 (STOP)"), N("SUB", "StopSubTree")]),
        N("SEQ", "OurKickOffBranch", [N("COND", "cmd 4/5 (nossa cor)"), N("SUB", "KickOffTree")]),
        N("SEQ", "OurPenaltyBranch", [N("COND", "cmd 6/7 (nossa cor)"), N("SUB", "PenaltyTree")]),
        N("SEQ", "CornerBranch", [N("COND", "is_corner_kick"), N("SUB", "CornerTree")]),
        N("SEQ", "ThrowInBranch", [N("COND", "is_kick_in"), N("SUB", "ThrowInTree")]),
        N("SEQ", "FreeKickBranch", [N("COND", "is_free_kick"), N("SUB", "FreeKickTree")]),
        N("SEQ", "OpponentSetPieceBranch", [N("COND", "cmd 4–9 do adversário"), N("SUB", "OppSetPieceTree")]),
        N("RSEQ", "GoalkeeperRole", [N("COND", "robot_id == 0"), N("SUB", "GoalkeeperTree")]),
        N("RSEQ", "AttackerRole", [N("COND", "papel = atacante"), N("DEC", "RetryUntilSuccessful(-1)", [N("SUB", "AttackerLogicLoop")])]),
        N("SUB", "DefenderTree"),
        N("ACT", "Halt (idle)"),
    ])
    arvore(raiz, "arvore_mestre_atual", rankdir="LR", nodesep=0.1, ranksep=0.4, fontsize=10, numerar=False)

    # Atacante (carry) - parte superior
    raiz = N("RSEQ", "AttackerLogicLoop", [
        N("ACT", "UpdateBallPosition"), N("ACT", "CalculateInterception"),
        N("RFB", "AttackLogicActions", [N("SEQ", "ChaseAndKick", [
            N("ACT", "GoToPoint\nponto de pré-chute seguro\n(tolerância 120 mm)"),
            N("SUB", "ApproachAndKick\n(figura seguinte)"),
            N("DEC", "Delay 600 ms", [N("ACT", "AlwaysSuccess")])])])])
    arvore(raiz, "arvore_atacante_atual", rankdir="TB", nodesep=0.2, ranksep=0.45, fontsize=10)
    carry_fb = N("RFB", "ApproachAndKick", [
        N("SEQ", "Shoot", [N("DEC", "Inverter", [N("COND", "IsBallInOurHalf")]), N("COND", "IsBallClose\n(140 mm, 10°)"), N("ACT", "KickBall 3 m/s")]),
        N("RSEQ", "Realign", [N("DEC", "Inverter", [N("COND", "IsBallInOurHalf")]), N("ACT", "GoToPoint\nponto de captura\nstraight_line")]),
        N("RSEQ", "Carry", [N("COND", "IsBallInOurHalf"), N("ACT", "GoToPoint\nponto de carga\nstraight_line + ball_side_check")]),
    ])
    arvore(carry_fb, "arvore_approach_and_kick", rankdir="LR", nodesep=0.18, ranksep=0.45, fontsize=10)

    raiz = N("SEQ", "SelectedDefenderOnly", [
        N("COND", "IsMyRole = defender"),
        N("RFB", "Root", [
            N("SEQ", "BallInOpponentField", [N("COND", "IsBallInOpponentField"), N("ACT", "ShadowBall\n(1200 mm)")]),
            N("RFB", "BallInOurField", [
                N("SEQ", "OpponentHasPossession", [N("COND", "IsOpponentControllingBall"), N("ACT", "MarkOpponent")]),
                N("ACT", "ShadowBall\n(1000 mm)")])])])
    arvore(raiz, "arvore_defensor_atual", rankdir="TB", nodesep=0.2, ranksep=0.45, fontsize=10)

    raiz = N("FB", "RobotRoleGuard", [
        N("RSEQ", "GoalkeeperLogic", [N("COND", "IsRobotId = 0"), N("ACT", "Goalkeeper")]),
        N("ACT", "Halt (not_the_goalkeeper)")])
    arvore(raiz, "arvore_goleiro_atual", rankdir="LR", fontsize=10.5)

    raiz = N("RSEQ", "StopLogic", [N("ACT", "UpdateBallPosition"), N("ACT", "KeepDistance\n(550 mm)")])
    arvore(raiz, "arvore_stop_atual", rankdir="LR", fontsize=10.5)

    raiz = N("FB", "KickOffRoles", [
        N("SEQ", "GoalKeeperRole", [N("COND", "IsRobotId = 0"), N("SUB", "GoalkeeperTree")]),
        N("SEQ", "Kicker", [N("COND", "IsMyRole = attacker"), N("ACT", "Repeat(-1): vai a (350, 0)\naté cmd == NORMAL_START")]),
        N("SEQ", "FieldPlayers", [N("COND", "IsMyRole = defender"), N("ACT", "Repeat(-1): vai a (600, 600)\naté cmd == NORMAL_START")]),
        N("ACT", "Halt (waiting_kick_off)")])
    arvore(raiz, "arvore_kickoff_atual", rankdir="LR", nodesep=0.18, fontsize=10)


def mestre_v2_pilha():
    """A Master Tree v2 como pilha de prioridades (mais legível que o desenho em árvore)."""
    from matplotlib.patches import FancyBboxPatch
    linhas = [
        (1, "SafetyGuard", "dados NÃO frescos\n(IsDataFresh falha)", "DegradedModeTree", VERM),
        (2, "HaltBranch", "HALT", "HaltSubTree", VERM),
        (3, "TimeoutBranch", "TIMEOUT", "TimeoutTree", VERM),
        (4, "StopBranch", "STOP", "StopSubTree", VERM),
        (5, "BallPlacementBranch", "BALL_PLACEMENT", "BallPlacementOurTree\n| BallPlacementTheirTree", LARANJA),
        (6, "PrepareKickoffBranch", "PREPARE_KICKOFF", "PrepareKickoffOurTree\n| PrepareKickoffTheirTree", LARANJA),
        (7, "KickoffBranch", "KICKOFF", "KickoffExecuteOurTree\n| PrepareKickoffTheirTree", LARANJA),
        (8, "PreparePenaltyBranch", "PREPARE_PENALTY", "PreparePenaltyOurTree\n| PreparePenaltyTheirTree", LARANJA),
        (9, "PenaltyBranch", "PENALTY", "PenaltyExecuteOurTree\n| PenaltyDefendTheirTree", LARANJA),
        (10, "FreeKickBranch", "FREE_KICK", "FreeKickOurTree\n| FreeKickTheirTree", LARANJA),
        (11, "RunBranch", "RUN", "NormalPlayTree", VERDE),
        (12, "Halt (unknown_phase)", "nenhuma fase\nconhecida", "parar o robô", CINZA),
    ]
    fig, ax = plt.subplots(figsize=(7.6, 8.2))
    ax.set_ylim(-0.6, 13.4); ax.axis("off")
    for x, t in [(0.45, "Prio."), (2.45, "Ramo\n(ReactiveSequence)"), (5.15, "Guarda\n(phase ==)"), (8.75, "Subárvore\n(nosso | deles)")]:
        ax.text(x, 12.95, t, ha="center", va="center", fontsize=8.3, weight="bold", color=AZUL, linespacing=1.1)
    for i, (n, ramo, guarda, sub, cor) in enumerate(linhas):
        y = 11.9 - i
        ax.add_patch(Circle((0.45, y), 0.33, fc=cor, ec="white", lw=1.5, zorder=3))
        ax.text(0.45, y, str(n), ha="center", va="center", color="white", fontsize=9, weight="bold", zorder=4)
        ax.add_patch(FancyBboxPatch((1.0, y - 0.38), 2.9, 0.76, boxstyle="round,pad=0.02,rounding_size=0.12", fc="#dbe9f6", ec=AZUL2, lw=1.4))
        ax.add_patch(FancyBboxPatch((1.06, y - 0.32), 2.78, 0.64, boxstyle="round,pad=0.02,rounding_size=0.1", fc="none", ec=AZUL2, lw=0.8))
        ax.text(2.45, y, ramo, ha="center", va="center", fontsize=7.8)
        ax.add_patch(FancyBboxPatch((4.15, y - 0.38), 2.1, 0.76, boxstyle="round,pad=0.02,rounding_size=0.3", fc="#e1f3e8", ec=VERDE, lw=1.4))
        ax.text(5.2, y, guarda, ha="center", va="center", fontsize=7.4, linespacing=1.2)
        ax.add_patch(FancyBboxPatch((6.6, y - 0.38), 4.3, 0.76, boxstyle="round,pad=0.02,rounding_size=0.12", fc="#f4f4f6", ec=CINZA, lw=1.4, ls="--"))
        ax.text(8.75, y, sub, ha="center", va="center", fontsize=7.4, linespacing=1.2)
        ax.plot([3.9, 4.15], [y, y], color="#6b7782", lw=1.2); ax.plot([6.25, 6.6], [y, y], color="#6b7782", lw=1.2)
    for (a_, b_, rot, cor) in [(1, 4, "segurança", VERM), (5, 10, "reinícios", LARANJA), (11, 11, "jogo", VERDE), (12, 12, "rede", CINZA)]:
        ya, yb = 11.9 - (a_ - 1) + 0.42, 11.9 - (b_ - 1) - 0.42
        ax.plot([11.1, 11.1], [yb, ya], color=cor, lw=3)
        ax.text(11.28, (ya + yb) / 2, rot, rotation=270, ha="left", va="center", fontsize=8, color=cor, weight="bold")
    ax.set_xlim(0, 11.8)
    ax.text(5.9, -0.45, "A cada tick, a raiz (ReactiveFallback) tenta os ramos de cima para baixo;\no primeiro que casa interrompe os de baixo.", ha="center", fontsize=7.8, color="#35434e", style="italic")
    salvar(fig, "arvore_mestre_v2", largura_max=8.0)


def arvores_propostas():
    G = lambda ph: N("COND", f"phase == {ph}", novo=True)
    nosso = lambda t: N("SUB", t, novo=False)
    # Mestre v2 (compacto: "nosso ou deles" vira um único nó de subárvore)
    def ramo(nome, fase, t_nosso, t_deles):
        return N("RSEQ", nome, [G(fase), N("SUB", f"{t_nosso}  (se favorecidos)\n{t_deles}  (caso contrário)", novo=True)])
    raiz = N("RFB", "MainTreeEL", [
        N("RSEQ", "SafetyGuard", [N("DEC", "Inverter", [N("COND", "IsDataFresh", novo=True)]), N("SUB", "DegradedModeTree", novo=True)]),
        N("RSEQ", "HaltBranch", [G("HALT"), N("SUB", "HaltSubTree")]),
        N("RSEQ", "TimeoutBranch", [G("TIMEOUT"), N("SUB", "TimeoutTree", novo=True)]),
        N("RSEQ", "StopBranch", [G("STOP"), N("SUB", "StopSubTree")]),
        ramo("BallPlacementBranch", "BALL_PLACEMENT", "BallPlacementOurTree", "BallPlacementTheirTree"),
        ramo("PrepareKickoffBranch", "PREPARE_KICKOFF", "PrepareKickoffOurTree", "PrepareKickoffTheirTree"),
        ramo("KickoffBranch", "KICKOFF", "KickoffExecuteOurTree", "PrepareKickoffTheirTree"),
        ramo("PreparePenaltyBranch", "PREPARE_PENALTY", "PreparePenaltyOurTree", "PreparePenaltyTheirTree"),
        ramo("PenaltyBranch", "PENALTY", "PenaltyExecuteOurTree", "PenaltyDefendTheirTree"),
        ramo("FreeKickBranch", "FREE_KICK", "FreeKickOurTree", "FreeKickTheirTree"),
        N("RSEQ", "RunBranch", [G("RUN"), N("SUB", "NormalPlayTree")]),
        N("ACT", "Halt (unknown_phase)")])
    mestre_v2_pilha()

    # StopTree
    raiz = N("RSEQ", "StopLogic", [
        N("ACT", "SetMotionLimit 0.75 m/s", novo=True),
        N("RFB", "StopAction", [
            N("RSEQ", "RetreatIfClose", [N("COND", "IsBallClose (650 mm)"), N("ACT", "ComputeLegalSlot\n(retreat)", novo=True), N("ACT", "GoToPoint")]),
            N("ACT", "HoldPosition", novo=True)])])
    arvore(raiz, "arvore_stop", fontsize=10.5, nodesep=0.3)

    # Prepare kickoff nosso
    raiz = N("RFB", "PrepareKickoffOurTree", [
        N("RSEQ", "", [N("COND", "HasRole = goalkeeper", novo=True), N("SUB", "GoalkeeperTree")]),
        N("RSEQ", "", [N("COND", "HasRole = kicker", novo=True), N("ACT", "ComputeLegalSlot\n(kickoff_kicker)", novo=True), N("ACT", "GoToPoint\nface = bola")]),
        N("RSEQ", "", [N("ACT", "ComputeLegalSlot\n(kickoff_def)", novo=True), N("ACT", "GoToPoint\nface = bola")])])
    arvore(raiz, "arvore_prepare_kickoff", nodesep=0.22, fontsize=10)

    # Restart kicker
    raiz = N("SEQ", "RestartKickerTree", [
        N("ACT", "UpdateBallPosition"), N("ACT", "GoToPoint\npré-chute, face = alvo"),
        N("ACT", "KickOnce\n(≤ 3 m/s, timeout 10 s)", novo=True)])
    arvore(raiz, "arvore_restart_kicker", nodesep=0.3, fontsize=10.5)

    # Penalty execute/defend
    raiz = N("RFB", "PenaltyDefendTheirTree", [
        N("RSEQ", "", [N("COND", "HasRole = goalkeeper", novo=True), N("RFB", "", [
            N("RSEQ", "", [N("DEC", "Inverter", [N("COND", "WaitBallInPlay", novo=True)]), N("ACT", "PenaltyKeeperLine", novo=True)]),
            N("SUB", "GoalkeeperTree")])]),
        N("ACT", "HoldPosition\n(≥ 1 m atrás da bola)", novo=True)])
    arvore(raiz, "arvore_penalty_defesa", rankdir="TB", nodesep=0.2, fontsize=10)

    # Free kick nosso
    raiz = N("RFB", "FreeKickOurTree", [
        N("RSEQ", "", [N("COND", "HasRole = goalkeeper", novo=True), N("SUB", "GoalkeeperTree")]),
        N("RSEQ", "", [N("COND", "HasRole = kicker", novo=True), N("SUB", "RestartKickerTree")]),
        N("RSEQ", "", [N("ACT", "ComputeLegalSlot\n(freekick_support)", novo=True), N("ACT", "GoToPoint")])])
    arvore(raiz, "arvore_freekick", nodesep=0.22, fontsize=10)

    # Ball placement nosso / deles
    raiz = N("RFB", "BallPlacementOurTree", [
        N("RSEQ", "PlacerRole", [N("COND", "HasRole = kicker", novo=True), N("ACT", "ComputePlacementApproach", novo=True), N("ACT", "GoToPoint\n(ponto de captura)"), N("ACT", "PlaceBall\n(30 s)", novo=True)]),
        N("SUB", "StopSubTree")])
    arvore(raiz, "arvore_ballplacement_nosso", nodesep=0.2, fontsize=10)
    raiz = N("RSEQ", "BallPlacementTheirTree", [
        N("ACT", "SetMotionLimit 0.75", novo=True),
        N("RFB", "", [N("ACT", "AvoidPlacementCorridor\n(margem 550 mm)", novo=True), N("ACT", "HoldPosition", novo=True)])])
    arvore(raiz, "arvore_ballplacement_deles", nodesep=0.3, fontsize=10.5)

    # Normal play
    raiz = N("RFB", "NormalPlayTree", [
        N("RSEQ", "GoalkeeperRole", [N("COND", "HasRole = goalkeeper", novo=True), N("SUB", "GoalkeeperTree")]),
        N("RSEQ", "AttackerRole", [N("COND", "HasRole = attacker", novo=True), N("SUB", "AttackerTree")]),
        N("RSEQ", "DefenderRole", [N("COND", "HasRole = defender", novo=True), N("SUB", "DefenderTree")]),
        N("ACT", "Halt (idle)")])
    arvore(raiz, "arvore_normalplay", nodesep=0.22, fontsize=10.5)


if __name__ == "__main__":
    bt_conceitos(); arvores_atuais(); arvores_propostas()
