"""Figuras de ataque, defesa, goleiro, movimento e papéis."""
from fig_lib import *
import numpy as np
import heapq


def _pano(ax, xlim, ylim, cor="#f4f7f1"):
    ax.set_xlim(*xlim); ax.set_ylim(*ylim); ax.set_aspect("equal"); ax.axis("off")
    ax.add_patch(Rectangle((xlim[0], ylim[0]), xlim[1] - xlim[0], ylim[1] - ylim[0], fc=cor, ec="#cfd6dc", zorder=0))


def _ponto(ax, p, rot, cor=LARANJA, dx=0, dy=60, fs=8, ha="center"):
    ax.plot(*p, "o", color=cor, ms=6, zorder=9, mec="white")
    ax.text(p[0] + dx, p[1] + dy, rot, fontsize=fs, ha=ha, va="bottom", color="#26333d", zorder=10)


def f_pontos_ataque():
    fig, axs = plt.subplots(1, 2, figsize=(12, 4.6))
    # (a) caso normal: gol à direita, bola na origem
    ax = axs[0]; _pano(ax, (-700, 800), (-420, 420))
    b = np.array([0.0, 0.0]); u = np.array([1.0, 0.0])  # direção bola -> gol
    ax.add_patch(Circle(tuple(b), 21.5, fc="#ff8c1a", ec="#8a4300", zorder=6))
    seta(ax, (-640, 0), (760, 0), cor="#9aa5ad", lw=1, ls="--", ms=8)
    ax.text(770, -45, "→ gol adversário", fontsize=8, color="#5b6770", ha="right", va="top")
    pk = b - u * 400; cap = b - u * 115; carry = b + u * 120; face = b + u * 400
    ax.add_patch(Circle(tuple(pk), 90, fc=(0.16, 0.44, 0.69, 0.18), ec=AZUL2, lw=1.2, zorder=3))
    ax.add_patch(Circle(tuple(cap), 90, fc=(0.16, 0.44, 0.69, 0.35), ec=AZUL2, lw=1.2, zorder=3))
    _ponto(ax, pk, "pré-chute\n(400 mm atrás da bola)", AZUL2, dy=130)
    _ponto(ax, cap, "captura\n(115 mm)", AZUL2, dy=-230, fs=8)
    _ponto(ax, carry, "ponto de carga\n(120 mm além do centro)", LARANJA, dx=20, dy=-250, ha="left")
    _ponto(ax, face, "mira da carga\n(400 mm rumo ao gol)", VERDE, dx=0, dy=110)
    ax.set_title("(a) Pontos calculados em torno da bola", fontsize=9.5, color=AZUL, loc="left")
    # (b) robô no lado errado: contorno
    ax = axs[1]; _pano(ax, (-700, 900), (-700, 900))
    ax.add_patch(Circle(tuple(b), 21.5, fc="#ff8c1a", ec="#8a4300", zorder=6))
    seta(ax, (-640, 0), (860, 0), cor="#9aa5ad", lw=1, ls="--", ms=8)
    robo(ax, 450, 300, 3.6, AZUL2, "robô", r=90)
    pk_safe = pk + np.array([0, 600])
    ax.add_patch(Circle(tuple(pk), 90, fc=(0.16, 0.44, 0.69, 0.18), ec=AZUL2, lw=1.2, zorder=3))
    ax.plot(*pk_safe, "s", color=LARANJA, ms=8, zorder=9, mec="white")
    ax.text(pk_safe[0], pk_safe[1] + 60, "waypoint de contorno\n(600 mm ao lado)", ha="center", fontsize=8, va="bottom")
    ax.text(pk[0] - 40, pk[1] - 130, "pré-chute", ha="center", fontsize=8, va="top", color=AZUL2)
    seta(ax, (390, 330), tuple(pk_safe + np.array([60, 0])), cor=LARANJA, lw=1.8)
    seta(ax, tuple(pk_safe + np.array([-10, -60])), tuple(pk + np.array([0, 100])), cor=LARANJA, lw=1.8, ls="--")
    ax.text(480, 520, "o robô está do lado do gol:\nir direto passaria pela frente da bola", fontsize=8, color=VERM, ha="left")
    ax.set_title("(b) Robô do lado errado da bola", fontsize=9.5, color=AZUL, loc="left")
    fig.tight_layout()
    salvar(fig, "pontos_ataque")


def f_fases_atacante():
    fig, axs = plt.subplots(2, 2, figsize=(11.5, 7.2))
    cfg = [
        ("1  Aproximação", "GoToPoint → ponto de pré-chute seguro\n(planejador D*, desvia de obstáculos)"),
        ("2  Realinhar (bola no campo adversário)", "GoToPoint → ponto de captura\n(linha reta, olhando para a mira)"),
        ("3  Chutar", "IsBallClose (≤140 mm, ≤10°) → KickBall"),
        ("4  Conduzir (bola no nosso campo)", "GoToPoint → ponto de carga, empurrando a bola\n(linha reta, com ball_side_check)"),
    ]
    for ax, (t, d) in zip(axs.flat, cfg):
        _pano(ax, (-800, 900), (-420, 420))
        ax.set_title(t, fontsize=10, color=AZUL, loc="left"); ax.text(-770, -390, d, fontsize=8, color="#35434e", va="bottom")
        ax.add_patch(Circle((0, 0), 21.5, fc="#ff8c1a", ec="#8a4300", zorder=6))
        seta(ax, (-740, 0), (860, 0), cor="#b8c2c9", lw=0.9, ls="--", ms=7)
    a0, a1, a2, a3 = axs.flat
    robo(a0, -700, 260, -0.4, AZUL2, None); seta(a0, (-630, 235), (-430, 40), cor=LARANJA, lw=2); robo(a0, -400, 0, 0, AZUL2, None, alpha=0.35)
    a0.plot(-400, 0, "o", color=LARANJA, mec="white", zorder=9)
    robo(a1, -420, 0, 0, AZUL2, None, alpha=0.4); seta(a1, (-330, 0), (-150, 0), cor=LARANJA, lw=2); robo(a1, -115, 0, 0, AZUL2, None)
    a1.text(-115, -150, "captura", fontsize=8, ha="center", color=AZUL2)
    robo(a2, -115, 0, 0, AZUL2, None)
    a2.add_patch(Wedge((-115, 0), 140, -10, 10, fc=(0.9, 0.3, 0.1, 0.25), ec=LARANJA, zorder=4))
    seta(a2, (30, 0), (700, 0), cor=VERM, lw=2.4)
    a2.text(380, 40, "chute ≤ 3 m/s", fontsize=8.5, color=VERM, ha="center")
    robo(a3, -115, 0, 0, AZUL2, None)
    a3.plot(120, 0, "o", color=LARANJA, mec="white", zorder=9); a3.text(120, 60, "ponto de carga", fontsize=8, ha="center")
    seta(a3, (-20, 0), (100, 0), cor=LARANJA, lw=2.2)
    a3.plot(400, 0, "o", color=VERDE, mec="white", zorder=9); a3.text(400, 60, "mira", fontsize=8, ha="center")
    fig.tight_layout()
    salvar(fig, "fases_atacante")


def f_defensor():
    fig, axs = plt.subplots(1, 2, figsize=(12, 4.6))
    for ax in axs:
        campo(ax, meio="esq", margem=False)
        ax.set_xlim(-L - 150, 650); ax.set_ylim(-W - 100, W + 100)
    # (a) ShadowBall
    ax = axs[0]
    bx, by = -250, 520; vx, vy = -500, -250
    bola(ax, bx, by); seta(ax, (bx, by), (bx + vx * 0.9, by + vy * 0.9), cor="#ffd9b8", lw=1.8)
    px, py = bx + vx * 0.3, by + vy * 0.3
    ax.plot(px, py, "x", color="white", ms=7, zorder=8)
    texto(ax, px + 200, py + 260, "bola prevista\n(0,3 s à frente)", fs=7.5, bg=(0, 0, 0, 0.35))
    tx, ty = px - 1200, max(-900, min(900, py))
    lim = -L + DEF_D + 200
    ax.plot([lim, lim], [-W, W], color="#ffcc66", lw=1.2, ls="--", zorder=4)
    texto(ax, lim + 30, -W + 110, "limite: área + 200 mm", fs=7.5, ha="left", bg=(0, 0, 0, 0.35))
    tx = max(tx, lim)
    ax.add_patch(Circle((tx, ty), 5, fc="none"))
    robo(ax, tx, ty, 0.3, AZUL2, "defensor")
    seta(ax, (px - 30, py - 10), (tx + 110, ty + 20), cor="white", lw=1.2, ls=":")
    texto(ax, (px + tx) / 2 + 100, ty - 520, "distância fixa rumo ao próprio gol\n(1200 mm; 1000 mm em nosso campo)", fs=7.5, bg=(0, 0, 0, 0.35))
    ax.set_title("(a) ShadowBall: acompanhar a bola prevista", fontsize=9.5, color=AZUL, loc="left")
    # (b) MarkOpponent
    ax = axs[1]
    bx, by = -700, 650
    bola(ax, bx, by)
    robo(ax, bx + 150, by - 40, 3.5, "#d9a400", "adversário c/ posse")
    gx, gy = -L, 0
    u = np.array([gx - bx, gy - by]); u = u / np.linalg.norm(u)
    ax.plot([bx, gx], [by, gy], color="#ffd9b8", lw=1.2, ls="--", zorder=4)
    mx, my = bx + u[0] * 400, by + u[1] * 400
    robo(ax, mx, my, math.atan2(by - my, bx - mx), AZUL2, "defensor")
    texto(ax, mx + 150, my - 420, "ponto na linha bola→gol\na 400 mm da bola", fs=7.5, bg=(0, 0, 0, 0.35))
    ax.set_title("(b) MarkOpponent: bloquear a linha de chute", fontsize=9.5, color=AZUL, loc="left")
    fig.tight_layout()
    salvar(fig, "defensor_shadow_mark")


def f_goleiro():
    fig, axs = plt.subplots(1, 2, figsize=(12, 4.8))
    for ax in axs:
        campo(ax, meio="esq", margem=False)
        ax.set_xlim(-L - 200, 500); ax.set_ylim(-W - 80, W + 80)
    ax = axs[0]
    bola(ax, -1100, 600)
    robo(ax, -L + 120 + 90, 440, 0.45, AZUL2, "goleiro")
    ax.plot([-L + 210] * 2, [-350, 350], color="white", lw=1.2, ls="--", zorder=4)
    seta(ax, (-L + 210, 440), (-L + 210, 440))
    seta(ax, (-L + 150, -350), (-L + 150, 350), cor=LARANJA, lw=1.6, estilo="<|-|>")
    texto(ax, -L + 520, -480, "segue o y da bola na linha do gol,\n120 mm à frente da linha de fundo", fs=8, bg=(0, 0, 0, 0.4), ha="left")
    ax.set_title("(a) Bola fora da área: defender na linha", fontsize=9.5, color=AZUL, loc="left")
    ax = axs[1]
    bola(ax, -L + 300, 250)
    ang = math.atan2((W + 500) - 250, 0 - (-L + 300))
    u = np.array([math.cos(ang), math.sin(ang)])
    pre = np.array([-L + 300, 250]) - u * 200
    robo(ax, pre[0], pre[1], ang, AZUL2, "goleiro")
    seta(ax, (-L + 300 + 40, 250 + 20), (-L + 300 + u[0] * 700, 250 + u[1] * 700), cor=LARANJA, lw=2.2)
    texto(ax, -L + 420, 1010, "afasta para a lateral\n(y = ±(L/2 + 500 mm))", fs=8, bg=(0, 0, 0, 0.4), ha="left")
    texto(ax, -L + 700, -520, "bola na área: vai atrás da bola,\navança e chuta (≤ 3 m/s)", fs=8, bg=(0, 0, 0, 0.4), ha="left")
    ax.set_title("(b) Bola na área: sair e afastar", fontsize=9.5, color=AZUL, loc="left")
    fig.tight_layout()
    salvar(fig, "goleiro_estados")


def f_clamp_area():
    fig, ax = plt.subplots(figsize=(9, 4.6))
    campo(ax, meio="dir", margem=False)
    ax.set_xlim(900, L + 350); ax.set_ylim(-W + 300, W - 300)
    ax.add_patch(Rectangle((L - DEF_D - 100, -DEF_W / 2 - 100), DEF_D + 100, DEF_W + 200, fc=(0.9, 0.2, 0.1, 0.18), ec="#ffcc66", ls="--", lw=1.4, zorder=3))
    texto(ax, L - DEF_D - 100, DEF_W / 2 + 190, "margem de 100 mm", fs=7.5, ha="left", bg=(0, 0, 0, 0.35))
    p = (L - 250, 280); q = (L - DEF_D - 100, 280)
    ax.plot(*p, "x", color="white", ms=8, zorder=9); texto(ax, p[0], p[1] + 120, "alvo pedido pela árvore", fs=7.5, bg=(0, 0, 0, 0.35))
    robo(ax, q[0] - 60 - 20, q[1] + 20, 0, AZUL2, "alvo efetivo (jogador de linha)")
    seta(ax, (p[0] - 30, p[1]), (q[0] + 10, q[1]), cor="#ffd9b8", lw=1.8)
    texto(ax, 1500, -500, "O GoToPoint empurra alvos que caiam na área adversária (e na própria, exceto o goleiro)\npara fora dela, com margem de 100 mm. O controlador ainda zera a velocidade de entrada.", fs=8, bg=(0, 0, 0, 0.45), ha="left")
    salvar(fig, "clamp_area")


def _astar(grid, s, g):
    H, Wd = grid.shape
    pq = [(0, s)]; came = {s: None}; cost = {s: 0}
    while pq:
        _, cur = heapq.heappop(pq)
        if cur == g: break
        for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)]:
            n = (cur[0] + dx, cur[1] + dy)
            if 0 <= n[0] < Wd and 0 <= n[1] < H and grid[n[1], n[0]] == 0:
                c = cost[cur] + (1.414 if dx and dy else 1)
                if n not in cost or c < cost[n]:
                    cost[n] = c; came[n] = cur
                    heapq.heappush(pq, (c + math.hypot(g[0] - n[0], g[1] - n[1]), n))
    path = []; cur = g
    while cur is not None:
        path.append(cur); cur = came.get(cur)
    return path[::-1]


def f_dstar():
    Wd, H = 50, 34
    grid = np.zeros((H, Wd), int); infl = np.zeros((H, Wd), int)
    obst = [(24, 17, 4), (34, 22, 4), (18, 8, 4), (8, 20, 4)]
    for ox, oy, r in obst:
        for y in range(H):
            for x in range(Wd):
                if (x - ox) ** 2 + (y - oy) ** 2 <= r * r: grid[y, x] = 1
    # parede da área adversária (direita)
    for y in range(H):
        for x in range(Wd):
            if x >= 42 and 8 <= y <= 26: grid[y, x] = 2
    g2 = (grid > 0).astype(int)
    path = _astar(g2, (3, 4), (38, 28))
    fig, ax = plt.subplots(figsize=(10, 6.2))
    cmap = {0: "#f4f7f1", 1: "#f2b8b0", 2: "#c7a6e8"}
    for y in range(H):
        for x in range(Wd):
            ax.add_patch(Rectangle((x, y), 1, 1, fc=cmap[grid[y, x]], ec="#e1e6e9", lw=0.3))
    px = [p[0] + .5 for p in path]; py = [p[1] + .5 for p in path]
    ax.plot(px, py, color=AZUL2, lw=2.4, zorder=5)
    ax.plot(px[0], py[0], "o", color=AZUL, ms=10, zorder=6); ax.plot(px[-1], py[-1], "*", color=LARANJA, ms=16, zorder=6)
    for ox, oy, r in obst:
        ax.plot(ox + .5, oy + .5, "o", color="#8f2d20", ms=8, zorder=6)
    ax.text(3.6, 5.6, "robô", fontsize=9, color=AZUL); ax.text(38.7, 28.3, "alvo", fontsize=9, color=LARANJA)
    ax.text(24.5, 22.2, "robô adversário\ninflado (150 mm)", fontsize=8, ha="center", color="#8f2d20")
    ax.text(46, 17, "parede da\nárea\n(valor 101)", fontsize=8, ha="center", color="#5b3a8c")
    ax.set_xlim(0, Wd); ax.set_ylim(0, H); ax.set_aspect("equal"); ax.axis("off")
    ax.set_title("Grade de ocupação do D* (células de 50 mm — esquema reduzido) e o caminho encontrado", fontsize=9.5, color=AZUL, loc="left")
    salvar(fig, "dstar_grade")


def f_pure_pursuit():
    fig, ax = plt.subplots(figsize=(8.4, 4.4))
    ax.set_aspect("equal"); ax.axis("off")
    xs = np.linspace(0, 10, 60); ys = 1.6 * np.sin(xs / 2.6) + 0.3 * xs / 3
    ax.plot(xs, ys, color=AZUL2, lw=2.2)
    for x, y in zip(xs[::6], ys[::6]): ax.plot(x, y, ".", color=AZUL2, ms=6)
    rx, ry = xs[8], ys[8] - 0.7
    ax.add_patch(Circle((rx, ry), 0.55, fc=AZUL, ec="white", zorder=5))
    ax.add_patch(Circle((rx, ry), 2.0, fc="none", ec=LARANJA, ls="--", lw=1.4))
    idx = next(i for i, (x, y) in enumerate(zip(xs, ys)) if math.hypot(x - rx, y - ry) > 2.0 and x > rx)
    ax.plot(xs[idx], ys[idx], "o", color=LARANJA, ms=9, zorder=6)
    seta(ax, (rx, ry), (xs[idx], ys[idx]), cor=LARANJA, lw=2)
    ax.text(rx - 0.2, ry - 0.95, "robô", ha="right", fontsize=9)
    ax.text(xs[idx] + 0.2, ys[idx] + 0.35, "alvo de perseguição (lookahead)", fontsize=9, color=LARANJA)
    ax.text(rx + 1.2, ry - 1.9, "raio = lookahead_distance (100 mm)", fontsize=8.5, color=LARANJA, ha="left")
    ax.text(0, ys[0] + 0.9, "rota do D* (poses de 5 em 5 cm)", fontsize=9, color=AZUL2)
    ax.text(5.7, -2.7, "velocidade = min(v_max, distância × ganho) na direção do alvo", fontsize=9, color="#35434e")
    ax.set_xlim(-0.5, 11); ax.set_ylim(-3.2, 3.2)
    salvar(fig, "pure_pursuit")


def f_inversao_lado():
    fig, axs = plt.subplots(1, 2, figsize=(11, 3.9))
    for ax in axs: campo(ax, margem=False)
    ax = axs[0]
    robo(ax, 1200, 350, 0.4, "#d9a400", "robô amarelo na visão"); bola(ax, 600, 300)
    ax.set_title("Visão original: (x, y, θ)", fontsize=9.5, color=AZUL, loc="left")
    ax = axs[1]
    robo(ax, -1200, -350, 0.4 + math.pi, "#d9a400", "invert_sides = true"); bola(ax, -600, -300)
    ax.set_title("Após o observer: (−x, −y, θ + π)", fontsize=9.5, color=AZUL, loc="left")
    fig.tight_layout()
    salvar(fig, "inversao_lado")


def f_lado_literais():
    fig, axs = plt.subplots(1, 2, figsize=(12, 4.4))
    pontos = [(350, 0, "(350, 0)\ncobrador kick-off"), (600, 600, "(600, 600)\ndefensor kick-off"),
              (-1500, 0, "(−1500, 0)\ndefensor set-piece"), (-500, 0, "(−500, 0)\napoio free kick")]
    for ax, (tit, gol_x) in zip(axs, [("Time azul: defende o gol de x = −2250", -L), ("Time amarelo: defende o gol de x = +2250", L)]):
        campo(ax, margem=False)
        ax.add_patch(Rectangle((-L - 20 if gol_x < 0 else L - 10, -450), 30, 900, fc="none", ec=LARANJA, lw=2.5, zorder=9))
        texto(ax, gol_x * 0.62, 1300, "nosso gol", fs=8.5, bg=(0, 0, 0, 0.35))
        for x, y, r in pontos:
            na_nossa = (x < 0) == (gol_x < 0)
            ax.plot(x, y, "o", ms=9, color="white" if na_nossa else VERM, mec="black", zorder=9)
            ax.text(x, y - 130, r, fontsize=6.8, ha="center", va="top", color="white", zorder=10,
                    bbox=dict(boxstyle="round,pad=0.15", fc=(0, 0.4, 0, 0.5) if na_nossa else (0.7, 0.1, 0.1, 0.7), ec="none"))
        ax.set_title(tit, fontsize=9.5, color=AZUL, loc="left")
    fig.tight_layout()
    salvar(fig, "lado_literais")


def f_custo_papel():
    fig, axs = plt.subplots(1, 2, figsize=(12, 4.6), gridspec_kw=dict(width_ratios=[1.35, 1]))
    ax = axs[0]
    campo(ax, margem=False)
    bxy = (500, 300)
    xs = np.linspace(-L, L, 180); ys = np.linspace(-W, W, 120)
    X, Y = np.meshgrid(xs, ys)
    R = np.hypot(X - bxy[0], Y - bxy[1]) / 1000.0
    ax.contourf(X, Y, 2.0 * R, levels=np.arange(0, 6.5, 0.5), cmap="Blues_r", alpha=0.40, zorder=2)
    cs = ax.contour(X, Y, 2.0 * R, levels=[1, 2, 3, 4], colors="white", linewidths=0.9, zorder=3)
    ax.clabel(cs, fmt="%.0f", fontsize=7)
    bola(ax, *bxy)
    def custo(p, ang):
        d = math.hypot(bxy[0] - p[0], bxy[1] - p[1]); to = math.atan2(bxy[1] - p[1], bxy[0] - p[0])
        return 2.0 * d / 1000.0 + 1.0 * (1 - math.cos(ang - to))
    r1, a1 = (-600, -300), 0.35; r2, a2 = (1300, 800), 3.3
    robo(ax, *r1, a1, AZUL2, f"R1  custo ≈ {custo(r1, a1):.2f}"); robo(ax, *r2, a2, AZUL2, f"R2  custo ≈ {custo(r2, a2):.2f}")
    texto(ax, 0, -W - 10, "menor custo → papel de atacante (R2)", fs=8, bg=(0, 0, 0, 0.4))
    ax.set_title("Custo de papel: mais perto e mais alinhado = mais barato", fontsize=9.5, color=AZUL, loc="left")
    ax = axs[1]
    ax.set_title("Parâmetros do role_assigner_node", fontsize=9.5, color=AZUL, loc="left")
    ax.axis("off"); ax.set_xlim(0, 10); ax.set_ylim(0, 10)
    linhas = [("custo = w1·r + w2·(1 − cos θ)", "r = distância à bola (m); θ = ângulo entre\na direção de movimento (ou frente) e a bola"),
              ("w1 = 2,0   w2 = 1,0", "distância pesa o dobro do alinhamento"),
              ("histerese de custo = 2,5", "o atacante atual ganha 2,5 de desconto:\nninguém o rouba por pouco"),
              ("histerese de tempo = 2,0 s", "mínimo de 2 s entre trocas de atacante")]
    y = 9.6
    for a_, b_ in linhas:
        ax.add_patch(FancyBboxPatch((0.1, y - 2.0), 9.8, 2.15, boxstyle="round,pad=0.05,rounding_size=0.2", fc=AZUL_CL, ec="none"))
        ax.text(0.4, y - 0.2, a_, fontsize=9.6, weight="bold", color=AZUL, va="top")
        ax.text(0.4, y - 0.95, b_, fontsize=8.4, color="#26333d", va="top")
        y -= 2.45
    fig.tight_layout()
    salvar(fig, "custo_papel")


def f_histerese():
    rng = np.random.default_rng(3)
    t = np.linspace(0, 12, 600)
    c1 = 3.0 - 0.0 * t + 0.35 * np.sin(t * 0.9)
    c2 = 4.6 - 0.28 * t + 0.25 * np.sin(t * 1.3 + 1)
    atk = 1; last_change = -9; seq = []
    cur1 = c1.copy(); cur2 = c2.copy()
    for i, tt in enumerate(t):
        e1 = c1[i] - (2.5 if atk == 1 else 0); e2 = c2[i] - (2.5 if atk == 2 else 0)
        best = 1 if e1 < e2 else 2
        if best != atk and tt - last_change >= 2.0:
            atk = best; last_change = tt
        seq.append(atk)
    seq = np.array(seq)
    fig, axs = plt.subplots(2, 1, figsize=(9.5, 5.2), sharex=True, gridspec_kw=dict(height_ratios=[3, 1]))
    ax = axs[0]
    ax.plot(t, c1, color=AZUL2, lw=2, label="custo do robô 1"); ax.plot(t, c2, color=LARANJA, lw=2, label="custo do robô 2")
    ax.plot(t, np.where(seq == 1, c1 - 2.5, np.nan), color=AZUL2, lw=1.2, ls=":", label="custo efetivo do atacante atual (−2,5)")
    ax.plot(t, np.where(seq == 2, c2 - 2.5, np.nan), color=LARANJA, lw=1.2, ls=":")
    ax.set_ylabel("custo"); ax.legend(fontsize=8, loc="upper right", frameon=False); ax.grid(alpha=0.25)
    ax.set_title("O robô 2 só vira atacante quando é mais barato mesmo descontada a histerese — e depois do cooldown de 2 s", fontsize=9, color=AZUL, loc="left")
    ax = axs[1]
    ax.fill_between(t, 0, 1, where=seq == 1, color=AZUL2, alpha=0.6, step="mid", label="atacante = R1")
    ax.fill_between(t, 0, 1, where=seq == 2, color=LARANJA, alpha=0.7, step="mid", label="atacante = R2")
    ax.set_yticks([]); ax.set_xlabel("tempo (s)"); ax.legend(fontsize=8, ncol=2, loc="upper center", frameon=False, bbox_to_anchor=(0.5, 1.5))
    fig.tight_layout()
    salvar(fig, "histerese_papeis")


def f_normal_start():
    fig, ax = plt.subplots(figsize=(11.5, 3.8))
    cmds = [("STOP", 0, 2, "#b8c4cc"), ("PREPARE_PENALTY (nosso)", 2, 4, AZUL2), ("NORMAL_START", 4, 5.6, LARANJA), ("jogo", 5.6, 7.2, "#9fd3b0")]
    for n, a, b, c in cmds:
        ax.add_patch(Rectangle((a, 2.4), b - a, 0.8, fc=c, ec="white", lw=2))
        ax.text((a + b) / 2, 2.8, n, ha="center", va="center", fontsize=8.5, color="white" if c in (AZUL2, LARANJA) else "#26333d")
    ax.text(-0.1, 2.8, "árbitro\n(comando)", ha="right", va="center", fontsize=8.5, color=AZUL)
    ramos = [("StopBranch", 0, 2, "#c4d6e6"), ("OurPenaltyBranch\n→ PenaltyTree", 2, 4, AZUL2), ("(nenhum ramo de bola\nparada casa)", 4, 5.6, "#f5c2bc"), ("AttackerRole / Defender", 5.6, 7.2, "#9fd3b0")]
    for n, a, b, c in ramos:
        ax.add_patch(Rectangle((a, 1.1), b - a, 0.9, fc=c, ec="white", lw=2))
        ax.text((a + b) / 2, 1.55, n, ha="center", va="center", fontsize=8, color="white" if c == AZUL2 else "#26333d")
    ax.text(-0.1, 1.55, "ramo ativo\nno mestre\natual", ha="right", va="center", fontsize=8.5, color=AZUL)
    ax.text(4.8, 0.6, "Em NORMAL_START o ramo do pênalti deixa de casar (ele exige cmd 6/7).\nA parte \"ExecutePenalty\" da PenaltyTree nunca chega a rodar.", ha="center", va="top", fontsize=8.8, color=VERM)
    ax.set_xlim(-1.6, 7.4); ax.set_ylim(-0.4, 3.5); ax.axis("off")
    salvar(fig, "normal_start_sem_contexto")


def f_preempcao_timeline():
    fig, ax = plt.subplots(figsize=(11.5, 3.9))
    fases = [("RUN", 0, 4, "#9fd3b0"), ("STOP", 4, 6.5, "#b8c4cc"), ("PREPARE_KICKOFF", 6.5, 9.5, AZUL2), ("KICKOFF", 9.5, 11.5, LARANJA), ("RUN", 11.5, 14, "#9fd3b0")]
    for n, a, b, c in fases:
        ax.add_patch(Rectangle((a, 2.3), b - a, 0.7, fc=c, ec="white", lw=2))
        ax.text((a + b) / 2, 2.65, n, ha="center", va="center", fontsize=8.3, color="white" if c in (AZUL2, LARANJA) else "#26333d")
    ramos = [("NormalPlayTree\n(atacante: GoToPoint RUNNING)", 0, 4, "#9fd3b0"), ("StopTree", 4, 6.5, "#b8c4cc"),
             ("PrepareKickoffOurTree", 6.5, 9.5, AZUL2), ("KickoffExecuteOurTree", 9.5, 11.5, LARANJA), ("NormalPlayTree", 11.5, 14, "#9fd3b0")]
    for n, a, b, c in ramos:
        ax.add_patch(Rectangle((a, 1.2), b - a, 0.8, fc=c, ec="white", lw=2))
        ax.text((a + b) / 2, 1.6, n, ha="center", va="center", fontsize=7.8, color="white" if c in (AZUL2, LARANJA) else "#26333d")
    ax.text(-0.15, 2.65, "GameState.phase", ha="right", va="center", fontsize=8.5, color=AZUL)
    ax.text(-0.15, 1.6, "ramo ativo\nda Master", ha="right", va="center", fontsize=8.5, color=AZUL)
    for x, lab in [(4, "STOP\nchega"), (6.5, "PREPARE_\nKICKOFF"), (9.5, "NORMAL_\nSTART"), (11.5, "bola\nse move")]:
        ax.annotate("", xy=(x, 2.3), xytext=(x, 3.45), arrowprops=dict(arrowstyle="-|>", color=VERM, lw=1.3))
        ax.text(x, 3.55, lab, ha="center", va="bottom", fontsize=7.5, color=VERM)
    ax.text(7, 0.5, "A cada tick o mestre reavalia os ramos de cima para baixo; o ramo anterior recebe halt() assim que o novo assume.", ha="center", fontsize=8.8, color="#35434e")
    ax.set_xlim(-2.4, 14.3); ax.set_ylim(0.2, 4.4); ax.axis("off")
    salvar(fig, "preempcao_timeline")


def f_slots():
    fig, axs = plt.subplots(1, 2, figsize=(12, 4.4))
    ax = axs[0]; campo(ax, margem=False)
    pts = [("goleiro", -L + 150, 0, AZUL2), ("defensor\n(kickoff_def)", -900, 520, AZUL2), ("cobrador\n(kickoff_kicker)", -280, 0, AZUL2),
           ("parede\n(wall)", -1500, -300, "#7a8ea0")]
    for r, x, y, c in pts: robo(ax, x, y, 0, c, r)
    bola(ax, 0, 0)
    ax.set_title("Kick-off nosso e defesa, defendendo o gol da esquerda (own_goal_x < 0)", fontsize=9.5, color=AZUL, loc="left")
    ax = axs[1]; campo(ax, margem=False)
    pts = [("goleiro", L - 150, 0, AZUL2), ("defensor", 900, -520, AZUL2), ("cobrador", 280, 0, AZUL2)]
    for r, x, y, c in pts: robo(ax, x, y, math.pi, c, r)
    bola(ax, 0, 0)
    ax.set_title("Os mesmos slots, defendendo o gol da direita (own_goal_x > 0): espelhados por side_sign", fontsize=9.5, color=AZUL, loc="left")
    fig.tight_layout()
    salvar(fig, "slots_legais")


def f_degradacao():
    fig, axs = plt.subplots(1, 3, figsize=(12, 3.4))
    cenarios = [("3 robôs ativos", [("GK", AZUL), ("ATK", LARANJA), ("DEF", VERDE)]),
                ("2 robôs ativos", [("GK", AZUL), ("ATK\n(recua em nosso campo)", LARANJA)]),
                ("1 robô ativo", [("GK", AZUL)])]
    for ax, (t, rs) in zip(axs, cenarios):
        ax.set_xlim(0, 10); ax.set_ylim(0, 6); ax.axis("off")
        ax.set_title(t, fontsize=10, color=AZUL, loc="left")
        for i, (n, c) in enumerate(rs):
            x = 1.2 + i * 3.1
            ax.add_patch(Circle((x + 0.9, 3.2), 1.0, fc=c, ec="white", lw=2))
            ax.text(x + 0.9, 3.2, n.split("\n")[0], color="white", ha="center", va="center", fontsize=10, weight="bold")
            if "\n" in n:
                ax.text(x + 0.9, 1.7, n.split("\n")[1], ha="center", va="top", fontsize=7.8, color="#35434e")
        for i in range(len(rs), 3):
            x = 1.2 + i * 3.1
            ax.add_patch(Circle((x + 0.9, 3.2), 1.0, fc="#e3e8ec", ec="#b8c2c9", lw=1.5, ls="--"))
            ax.text(x + 0.9, 3.2, "—", ha="center", va="center", color="#9aa5ad", fontsize=14)
    fig.tight_layout()
    salvar(fig, "degradacao_papeis")


if __name__ == "__main__":
    for f in [f_pontos_ataque, f_fases_atacante, f_defensor, f_goleiro, f_clamp_area, f_dstar, f_pure_pursuit, f_inversao_lado,
              f_lado_literais, f_custo_papel, f_histerese, f_normal_start, f_preempcao_timeline, f_slots, f_degradacao]:
        f()
