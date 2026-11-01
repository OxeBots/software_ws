"""Figuras específicas para os slides (maiores, com menos texto) e variantes LR dos diagramas."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fig_lib
from fig_lib import *

SLIDES_OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "figuras_slides")
os.makedirs(SLIDES_OUT, exist_ok=True)


def _stack(nome, linhas, titulo_esq, titulo_dir=None):
    """Pilha em duas colunas. linhas: (n, ramo, detalhe, cor, aviso)"""
    fig, ax = plt.subplots(figsize=(12.6, 5.3))
    ax.set_xlim(0, 12.6); ax.set_ylim(0, 5.3); ax.axis("off")
    meio = (len(linhas) + 1) // 2
    for col, grupo in enumerate([linhas[:meio], linhas[meio:]]):
        x0 = 0.1 + col * 6.35
        for i, (n, ramo, det, cor, aviso) in enumerate(grupo):
            y = 4.85 - i * 0.82
            ax.add_patch(Circle((x0 + 0.33, y), 0.27, fc=cor, ec="white", lw=1.4, zorder=3))
            ax.text(x0 + 0.33, y, str(n), ha="center", va="center", color="white", fontsize=11, weight="bold", zorder=4)
            ec = LARANJA if aviso else AZUL2
            ax.add_patch(FancyBboxPatch((x0 + 0.75, y - 0.33), 5.3, 0.66, boxstyle="round,pad=0.02,rounding_size=0.12",
                                        fc="#fff4e8" if aviso else "#eaf2fa", ec=ec, lw=1.6, ls="--" if aviso else "-"))
            ax.text(x0 + 0.95, y + 0.1, ramo, ha="left", va="center", fontsize=10.5, weight="bold", color=AZUL)
            ax.text(x0 + 0.95, y - 0.16, det, ha="left", va="center", fontsize=9, color="#35434e")
            if aviso:
                ax.text(x0 + 5.95, y, aviso, ha="right", va="center", fontsize=8.5, color=LARANJA, weight="bold")
    salvar(fig, nome, largura_max=12.6)


def mestre_atual():
    linhas = [
        (1, "HaltBranch", "cmd == 0 (HALT)  →  HaltSubTree", VERM, None),
        (2, "StopBranch", "cmd == 1 (STOP)  →  StopSubTree", VERM, None),
        (3, "OurKickOffBranch", "cmd 4/5 da nossa cor  →  KickOffTree", LARANJA, None),
        (4, "OurPenaltyBranch", "cmd 6/7 da nossa cor  →  PenaltyTree", LARANJA, None),
        (5, "CornerBranch", "is_corner_kick  →  CornerTree", LARANJA, "flag nunca escrita"),
        (6, "ThrowInBranch", "is_kick_in  →  ThrowInTree", LARANJA, "flag nunca escrita"),
        (7, "FreeKickBranch", "is_free_kick  →  FreeKickTree", LARANJA, None),
        (8, "OpponentSetPieceBranch", "cmd do adversário (4–9)  →  OppSetPieceTree", LARANJA, None),
        (9, "GoalkeeperRole", "robot_id == 0  →  GoalkeeperTree", VERDE, None),
        (10, "AttackerRole", "papel = atacante  →  laço do atacante", VERDE, None),
        (11, "DefenderTree", "papel = defensor  →  ShadowBall / MarkOpponent", VERDE, None),
        (12, "Halt (idle)", "nenhum ramo serve  →  parar o robô", CINZA, None),
    ]
    _stack("slide_mestre_atual", linhas, "")


def mestre_v2():
    linhas = [
        (1, "SafetyGuard", "dados não frescos  →  DegradedModeTree", VERM, None),
        (2, "HaltBranch", "HALT  →  HaltSubTree", VERM, None),
        (3, "TimeoutBranch", "TIMEOUT  →  TimeoutTree", VERM, None),
        (4, "StopBranch", "STOP  →  StopSubTree", VERM, None),
        (5, "BallPlacementBranch", "BALL_PLACEMENT  →  nosso | deles", LARANJA, None),
        (6, "PrepareKickoffBranch", "PREPARE_KICKOFF  →  nosso | deles", LARANJA, None),
        (7, "KickoffBranch", "KICKOFF  →  KickoffExecuteOur | espera", LARANJA, None),
        (8, "PreparePenaltyBranch", "PREPARE_PENALTY  →  nosso | deles", LARANJA, None),
        (9, "PenaltyBranch", "PENALTY  →  PenaltyExecuteOur | PenaltyDefendTheir", LARANJA, None),
        (10, "FreeKickBranch", "FREE_KICK  →  FreeKickOur | FreeKickTheir", LARANJA, None),
        (11, "RunBranch", "RUN  →  NormalPlayTree", VERDE, None),
        (12, "Halt (unknown_phase)", "nenhuma fase conhecida  →  parar o robô", CINZA, None),
    ]
    _stack("slide_mestre_v2", linhas, "")


def variantes_lr():
    """Regera, em LR e em figuras_slides/, diagramas que no PDF do manual foram verticais."""
    import fig_arq
    fig_lib.OUT = SLIDES_OUT
    orig = fig_arq.grafo
    def grafo_lr(corpo, nome, rankdir="TB", **kw):
        kw.setdefault("nodesep", 0.35); kw.setdefault("ranksep", 0.6)
        return fig_lib.grafo(corpo, nome, rankdir="LR", **kw)
    fig_arq.grafo = grafo_lr
    for f in [fig_arq.f_estados_gc, fig_arq.f_override, fig_arq.f_hibrida, fig_arq.f_dependencias, fig_arq.f_strategy_node,
              fig_arq.f_chute, fig_arq.f_no_ros_vs_bt, fig_arq.f_blackboard_fluxo]:
        f()
    fig_arq.grafo = orig
    # clusters de BT (Sequence, Fallback, reativos, Parallel, decoradores, preempção): na horizontal, para ocupar a largura do slide
    import fig_bt
    dot_orig = fig_bt.dot
    fig_bt.dot = lambda src, nome, **kw: fig_lib.dot(src.replace("rankdir=LR", "rankdir=TB") if (nome.startswith("bt_") and nome != "bt_anatomia") else src, nome, **kw)
    fig_bt.bt_conceitos()
    fig_bt.dot = dot_orig
    fig_lib.OUT = os.path.join(os.path.dirname(SLIDES_OUT), "figuras")


if __name__ == "__main__":
    fig_lib.OUT = SLIDES_OUT
    mestre_atual(); mestre_v2()
    variantes_lr()
    print("figuras de slides prontas")
