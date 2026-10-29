"""Figuras de geometria: campo, situações de bola parada, ataque, defesa, goleiro."""
from fig_lib import *
import numpy as np


def f_campo_dimensoes():
    fig, ax = plt.subplots(figsize=(9, 6.4))
    campo(ax)
    dim(ax, (-L - 500, -W - 640), (L + 500, -W - 640), "5500 mm (campo com margem)", fs=8)
    dim(ax, (-L, -W - 360), (L, -W - 360), "4500 mm (área de jogo)", fs=8)
    dim(ax, (L + 640, -W - 500), (L + 640, W + 500), "4000 mm", off=(0, 0), fs=8)
    ax.texts[-1].set_rotation(90)
    dim(ax, (L + 330, -W), (L + 330, W), "3000 mm", fs=8); ax.texts[-1].set_rotation(90)
    dim(ax, (-L, -DEF_W / 2 - 180), (-L + DEF_D, -DEF_W / 2 - 180), "500", fs=7.5)
    dim(ax, (-L + 330, -DEF_W / 2), (-L + 330, DEF_W / 2), "1350", fs=7.5); ax.texts[-1].set_rotation(90)
    dim(ax, (L - 330, -GOAL_W / 2), (L - 330, GOAL_W / 2), "800", fs=7.5); ax.texts[-1].set_rotation(90)
    texto(ax, 0, 640, "círculo central\nØ 1000 mm", fs=8)
    texto(ax, -L + 250, DEF_W / 2 + 130, "área de defesa", fs=7.5)
    texto(ax, -L - 90, -W - 160, "gol: 800 × 180 mm", fs=7.5, ha="left", cor="#e8f5ec")
    texto(ax, L - 40, -W + 120, "linha de fundo", fs=7, ha="right")
    texto(ax, -1100, W + 130, "linha de lateral (touch line)", fs=7.5); texto(ax, 90, W - 120, "meio-campo", fs=7.5, ha="left")
    ax.set_xlim(-L - 780, L + 820); ax.set_ylim(-W - 740, W + 640)
    salvar(fig, "campo_dimensoes")


def f_geometria_stop_placement():
    fig, axs = plt.subplots(1, 2, figsize=(11, 4.6))
    ax = axs[0]
    campo(ax, meio="dir", margem=False)
    ax.set_xlim(-300, 2050); ax.set_ylim(-900, 900)
    bola(ax, 900, 100)
    ax.add_patch(Circle((900, 100), 500, fc=(1, 1, 1, 0.12), ec="white", lw=1.4, ls="--", zorder=3))
    texto(ax, 900, 100 + 640, "raio de 0,5 m ao redor da bola", fs=8, bg=(0, 0, 0, 0.35))
    robo(ax, 1300, 450, 2.6, AZUL2, "dentro: deve recuar"); seta(ax, (1300, 450), (1520, 640))
    robo(ax, 200, -400, 0.3, AZUL2, "fora: pode ficar")
    robo(ax, 1500, -380, 3.5, "#d9a400", "adversário")
    texto(ax, 1050, -700, "STOP: velocidade < 0,75 m/s, sem tocar a bola", fs=8.5, bg=(0, 0, 0, 0.4))
    axs[0].set_title("(a) STOP", fontsize=9.5, color=AZUL, loc="left")
    ax = axs[1]
    campo(ax, meio="dir", margem=False)
    ax.set_xlim(-300, 2050); ax.set_ylim(-900, 900)
    b = np.array([300, -350]); t = np.array([1500, 380])
    d = t - b; n = np.linalg.norm(d); u = d / n; p = np.array([-u[1], u[0]])
    ang = math.degrees(math.atan2(u[1], u[0]))
    ax.add_patch(Rectangle((b[0], b[1] - 500), n, 1000, angle=0, fc="none", ec="none"))
    from matplotlib.transforms import Affine2D
    rect = Rectangle((0, -500), n, 1000, fc=(1, 0.45, 0.2, 0.22), ec="none", zorder=3)
    rect.set_transform(Affine2D().rotate_deg(ang).translate(*b) + ax.transData)
    ax.add_patch(rect)
    for c in (b, t):
        ax.add_patch(Wedge(tuple(c), 500, ang + 90 if c is t else ang + 90 + 180 * 0, ang + 270 if c is t else ang + 270, fc=(1, 0.45, 0.2, 0.22), ec="none", zorder=3))
    ax.add_patch(Wedge(tuple(b), 500, ang + 90, ang + 270, fc=(1, 0.45, 0.2, 0.22), ec="none", zorder=3))
    ax.add_patch(Wedge(tuple(t), 500, ang - 90, ang + 90, fc=(1, 0.45, 0.2, 0.22), ec="none", zorder=3))
    ax.plot([b[0], t[0]], [b[1], t[1]], color="#ffd9b8", lw=1.2, ls="--", zorder=4)
    bola(ax, *b); ax.add_patch(Circle(tuple(t), 60, fc="none", ec="#ff8c1a", lw=2, zorder=6))
    texto(ax, t[0] + 20, t[1] + 130, "posição designada", fs=8, bg=(0, 0, 0, 0.4))
    seta(ax, tuple(b + u * 70), tuple(t - u * 90), cor="#ffb066", lw=1.8)
    robo(ax, 520, -50, 0.6, AZUL2, "nosso (coloca)"); robo(ax, 1100, 150, 0.6, AZUL2, "nosso (coloca)")
    robo(ax, 700, 640, 3.4, "#d9a400", "adversário: fora do corredor")
    robo(ax, 1750, -300, 3.4, "#d9a400", None)
    texto(ax, 1000, -760, "BALL PLACEMENT: quem não coloca fica ≥ 0,5 m do corredor bola→alvo", fs=8, bg=(0, 0, 0, 0.4))
    axs[1].set_title("(b) BALL PLACEMENT", fontsize=9.5, color=AZUL, loc="left")
    fig.tight_layout()
    salvar(fig, "geometria_stop_placement")


def f_geometria_kickoff_penalty():
    fig, axs = plt.subplots(1, 2, figsize=(12, 4.8))
    ax = axs[0]; campo(ax, margem=False)
    bola(ax, 0, 0)
    for (x, y, a, c, r) in [(-1900, 0, 0, AZUL2, "goleiro"), (-700, 500, 0, AZUL2, "defensor"), (-250, 0, 0, AZUL2, "cobrador"),
                            (900, 600, math.pi, "#d9a400", None), (1300, -300, math.pi, "#d9a400", None), (2000, 0, math.pi, "#d9a400", None)]:
        robo(ax, x, y, a, c, r)
    texto(ax, -1200, 1250, "metade nossa", fs=8.5, bg=(0, 0, 0, 0.35)); texto(ax, 1200, 1250, "metade adversária", fs=8.5, bg=(0, 0, 0, 0.35))
    texto(ax, 0, -700, "só o cobrador pode entrar no círculo", fs=8, bg=(0, 0, 0, 0.35))
    ax.set_title("(a) Kick-off nosso (PREPARE_KICKOFF)", fontsize=9.5, color=AZUL, loc="left")
    ax = axs[1]; campo(ax, meio="dir", margem=False)
    ax.set_xlim(-250, 2450); ax.set_ylim(-950, 950)
    bola(ax, 1500, 0)
    ax.add_patch(Circle((1500, 0), 25, fc="none", ec="white", lw=1, zorder=7))
    texto(ax, 1500, 110, "marca de\npênalti*", fs=7, bg=(0, 0, 0, 0.35))
    robo(ax, 1100, 0, 0, AZUL2, "cobrador")
    ax.add_patch(Rectangle((-250, -950), 1500 - 250 + 250 - 1000 + 0 - 250 + 250, 0.1, fc="none"))
    ax.add_patch(Rectangle((-250, -900), 1500 - 1000 - 250 + 0, 1800, fc=(0.1, 0.4, 0.8, 0.14), ec="none", zorder=3))
    ax.plot([500, 500], [-900, 900], color="#cfe3ff", lw=1.2, ls="--", zorder=4)
    texto(ax, 160, 780, "demais robôs\n≥ 1 m atrás da bola", fs=7.5, bg=(0, 0, 0, 0.4))
    robo(ax, 200, 400, 0, AZUL2); robo(ax, 250, -420, 0, AZUL2)
    robo(ax, L - 90, 0, math.pi, "#d9a400", "goleiro na\nlinha de gol")
    texto(ax, 1800, -700, "NORMAL_START: a bola só pode\nse mover rumo ao gol adversário", fs=7.5, bg=(0, 0, 0, 0.4))
    ax.set_title("(b) Pênalti nosso (PREPARE_PENALTY)", fontsize=9.5, color=AZUL, loc="left")
    fig.tight_layout()
    salvar(fig, "geometria_kickoff_penalty")


def f_geometria_freekick():
    fig, ax = plt.subplots(figsize=(9.5, 5.6))
    campo(ax, meio="dir", margem=False)
    ax.set_xlim(-200, 2480); ax.set_ylim(-1650, 1650)
    # faixa proibida p/ posicionar bola: 0,2 m das linhas e 1 m da área de defesa
    ax.add_patch(Rectangle((L - DEF_D - 1000, -DEF_W / 2 - 1000), DEF_D + 1000, DEF_W + 2000, fc=(0.85, 0.15, 0.1, 0.22), ec="none", zorder=3))
    texto(ax, L - 700, 1180, "ponto de bola não pode\nestar a < 1 m da área", fs=7.5, bg=(0, 0, 0, 0.4))
    ax.add_patch(Rectangle((L - DEF_D - 200, -DEF_W / 2 - 200), DEF_D + 200, DEF_W + 400, fc="none", ec="#ffcc66", lw=1.4, ls="--", zorder=4))
    texto(ax, L - DEF_D - 560, -DEF_W / 2 - 330, "atacantes: ≥ 0,2 m da área adversária\n(em STOP e FREE KICK)", fs=7.5, bg=(0, 0, 0, 0.4), ha="center")
    bola(ax, 900, 500)
    ax.add_patch(Circle((900, 500), 500, fc=(1, 1, 1, 0.12), ec="white", lw=1.4, ls="--", zorder=3))
    texto(ax, 900, 500 + 640, "adversários ≥ 0,5 m", fs=8, bg=(0, 0, 0, 0.4))
    robo(ax, 520, 380, 0.15, AZUL2, "cobrador")
    seta(ax, (610, 410), (800, 480), cor="#ffd9b8")
    robo(ax, 1500, -250, 0, AZUL2, "apoio")
    robo(ax, 1500, 650, math.pi, "#d9a400", "parede"); robo(ax, 1400, 150, math.pi, "#d9a400", None)
    texto(ax, 450, -1300, "FREE KICK nosso: o cobrador chuta em até 10 s;\na bola entra em jogo após mover 0,05 m", fs=8, bg=(0, 0, 0, 0.4), ha="left")
    salvar(fig, "geometria_freekick")


def f_linha_do_tempo_partida():
    fig, ax = plt.subplots(figsize=(11, 3.4))
    segs = [("1º tempo\n300 s", 300, AZUL2), ("intervalo\n300 s", 300, "#b8c4cc"), ("2º tempo\n300 s", 300, AZUL2),
            ("pré-prorrog.\n300 s", 300, "#b8c4cc"), ("prorrog. 1º\n150 s", 150, "#4d8cc6"), ("interv.\n120 s", 120, "#b8c4cc"),
            ("prorrog. 2º\n150 s", 150, "#4d8cc6"), ("pré-pên.\n120 s", 120, "#b8c4cc"), ("shoot-out\nilimitado", 200, LARANJA)]
    x = 0
    for nome, d, c in segs:
        ax.add_patch(Rectangle((x, 0), d, 1, fc=c, ec="white", lw=2))
        ax.text(x + d / 2, 0.5, nome, ha="center", va="center", fontsize=7.8, color="white" if c not in ("#b8c4cc",) else "#33414c")
        x += d
    ax.annotate("", xy=(900, 1.55), xytext=(0, 1.55), arrowprops=dict(arrowstyle="<|-|>", color=AZUL))
    ax.text(450, 1.7, "tempo regulamentar (todas as partidas)", ha="center", color=AZUL, fontsize=9)
    ax.annotate("", xy=(1620, 1.55), xytext=(900, 1.55), arrowprops=dict(arrowstyle="<|-|>", color=CINZA))
    ax.text(1260, 1.7, "só em jogo eliminatório empatado", ha="center", color=CINZA, fontsize=9)
    ax.text(1620 + 100, 1.7, "pênaltis", ha="center", color=LARANJA, fontsize=9)
    ax.text(0, -0.45, "O relógio da partida PÁRA durante STOP, HALT, preparação de kick-off/pênalti e ball placement.\nPor isso o tempo real de jogo é bem maior que o tempo de jogo.",
            fontsize=8.5, color="#35434e", va="top")
    ax.set_xlim(-20, 1850); ax.set_ylim(-1.0, 2.2); ax.axis("off")
    salvar(fig, "linha_do_tempo_partida")


def f_sistemas_coordenadas():
    fig, axs = plt.subplots(1, 2, figsize=(11.5, 4.6), gridspec_kw=dict(width_ratios=[1.6, 1]))
    ax = axs[0]; campo(ax, margem=False)
    seta(ax, (-L - 60, -W - 190), (-L + 900, -W - 190), cor="#222", lw=1.6)
    seta(ax, (-L - 60, -W - 190), (-L - 60, -W + 700), cor="#222", lw=1.6)
    texto(ax, -L + 950, -W - 190, "+x", cor="#222", ha="left", fs=9); texto(ax, -L - 60, -W + 760, "+y", cor="#222", va="bottom", fs=9)
    texto(ax, 0, 0, "(0, 0)", fs=8, bg=(0, 0, 0, 0.35))
    robo(ax, 900, 500, 0.6, AZUL2, None, r=110)
    seta(ax, (900, 500), (900 + 360 * math.cos(0.6), 500 + 360 * math.sin(0.6)), cor="white")
    ax.add_patch(Arc((900, 500), 520, 520, theta1=0, theta2=math.degrees(0.6), color="white", lw=1.4, zorder=8))
    texto(ax, 1260, 470, "θ (rad)", fs=8.5); texto(ax, 1130, 690, "robô: x, y em mm", fs=8, bg=(0, 0, 0, 0.35))
    ax.set_title("Frame do campo usado em todo o software (mm, rad, anti-horário)", fontsize=9.5, color=AZUL, loc="left")
    ax = axs[1]; ax.axis("off"); ax.set_xlim(0, 10); ax.set_ylim(0, 10)
    linhas = [("Unidades", "posição em mm (GameData, blackboard);\nm apenas em RobotGoal e nos tópicos de path"),
              ("Ângulos", "radianos, normalizados em [−π, π];\nθ = 0 aponta para +x"),
              ("Velocidades", "RobotCmd: m/s no frame global\nchute: m/s"),
              ("Lado", "x do gol próprio = ±L/2 conforme a cor\n(ver cap. 8 e 20)")]
    y = 9.3
    for t, d in linhas:
        ax.add_patch(FancyBboxPatch((0.1, y - 1.75), 9.7, 1.9, boxstyle="round,pad=0.05,rounding_size=0.2", fc=AZUL_CL, ec="none"))
        ax.text(0.4, y - 0.15, t, fontsize=9.5, weight="bold", color=AZUL, va="top")
        ax.text(0.4, y - 0.75, d, fontsize=8.3, color="#26333d", va="top")
        y -= 2.3
    fig.tight_layout()
    salvar(fig, "sistemas_de_coordenadas")


if __name__ == "__main__":
    f_campo_dimensoes(); f_geometria_stop_placement(); f_geometria_kickoff_penalty(); f_geometria_freekick()
    f_linha_do_tempo_partida(); f_sistemas_coordenadas()
