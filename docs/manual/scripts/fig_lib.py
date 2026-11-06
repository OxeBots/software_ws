"""Utilitários de desenho para as figuras do manual (matplotlib + graphviz)."""
import os, subprocess, math
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, FancyArrowPatch, Arc, Polygon, FancyBboxPatch, Wedge

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "figuras")
os.makedirs(OUT, exist_ok=True)

AZUL = "#0b3c5d"; AZUL2 = "#2a6fb0"; AZUL_CL = "#e8f0f7"; LARANJA = "#e8782a"; VERDE = "#2e8b57"
VERM = "#c0392b"; AMAR = "#f2c14e"; CINZA = "#5b6770"; CINZA_CL = "#eef1f4"; ROXO = "#6b4fbb"
CAMPO = "#3f9a5a"; CAMPO_ESC = "#2f7d48"

plt.rcParams["font.family"] = "Liberation Sans"
plt.rcParams["font.size"] = 9
plt.rcParams["axes.unicode_minus"] = False

L = 2250.0   # meio comprimento da área de jogo (mm)
W = 1500.0   # meia largura
DEF_D = 500.0
DEF_W = 1350.0
CIRC_R = 500.0
GOAL_W = 800.0
GOAL_D = 180.0


def salvar(fig, nome, dpi=200, transparent=False, largura_max=8.2):
    """Reduz figuras largas: o texto mantém o tamanho em pontos e, no PDF (largura útil ~6,7 pol),
    fica legível. A figura é encolhida antes de salvar."""
    w, h = fig.get_size_inches()
    if not transparent and w > largura_max:
        k = largura_max / w
        fig.set_size_inches(w * k, h * k)
        try:
            fig.tight_layout()
        except Exception:
            pass
    caminho = os.path.join(OUT, nome + ".png")
    fig.savefig(caminho, dpi=dpi, bbox_inches="tight", facecolor="none" if transparent else "white",
                pad_inches=0.08)
    plt.close(fig)
    print("  fig:", nome)


def campo(ax, margem=True, limpo=False, meio=None, linhas=True, cor_campo=CAMPO):
    """Desenha o campo SSL-EL. meio: None (campo todo) | 'esq' | 'dir'."""
    if margem:
        ax.add_patch(Rectangle((-L - 500, -W - 500), 2 * L + 1000, 2 * W + 1000, fc=CAMPO_ESC, ec="none", zorder=0))
    ax.add_patch(Rectangle((-L, -W), 2 * L, 2 * W, fc=cor_campo, ec="none", zorder=1))
    lw = 1.1
    kw = dict(color="white", lw=lw, zorder=2)
    ax.plot([-L, L, L, -L, -L], [-W, -W, W, W, -W], **kw)
    ax.plot([0, 0], [-W, W], **kw)
    ax.add_patch(Circle((0, 0), CIRC_R, fc="none", ec="white", lw=lw, zorder=2))
    for s in (-1, 1):
        x0 = s * L
        ax.add_patch(Rectangle((x0 if s < 0 else x0 - DEF_D, -DEF_W / 2), DEF_D, DEF_W, fc="none", ec="white", lw=lw, zorder=2))
        gx = x0 - GOAL_D if s < 0 else x0
        ax.add_patch(Rectangle((gx, -GOAL_W / 2), GOAL_D, GOAL_W, fc="#dfe6ea", ec="#333", lw=1.0, zorder=2))
    ax.set_aspect("equal")
    ax.axis("off")
    if meio == "esq":
        ax.set_xlim(-L - 420, 250); ax.set_ylim(-W - 420, W + 420)
    elif meio == "dir":
        ax.set_xlim(-250, L + 420); ax.set_ylim(-W - 420, W + 420)
    elif margem:
        ax.set_xlim(-L - 520, L + 520); ax.set_ylim(-W - 520, W + 520)
    else:
        ax.set_xlim(-L - 80, L + 80); ax.set_ylim(-W - 80, W + 80)


def robo(ax, x, y, ang=0.0, cor=AZUL2, rot=None, r=90, z=5, borda="white", alpha=1.0, seta=True):
    ax.add_patch(Circle((x, y), r, fc=cor, ec=borda, lw=1.2, zorder=z, alpha=alpha))
    if seta:
        ax.add_patch(Polygon([[x + r * 1.05 * math.cos(ang), y + r * 1.05 * math.sin(ang)],
                              [x + r * 0.55 * math.cos(ang + 2.4), y + r * 0.55 * math.sin(ang + 2.4)],
                              [x + r * 0.55 * math.cos(ang - 2.4), y + r * 0.55 * math.sin(ang - 2.4)]],
                             closed=True, fc="white", ec="none", zorder=z + 1, alpha=alpha))
    if rot is not None:
        ax.text(x, y - r * 1.9, rot, ha="center", va="top", fontsize=7.5, color="white", zorder=z + 2,
                bbox=dict(boxstyle="round,pad=0.15", fc=(0, 0, 0, 0.35), ec="none"))


def bola(ax, x, y, r=45, z=6):
    ax.add_patch(Circle((x, y), r, fc="#ff8c1a", ec="#8a4300", lw=0.9, zorder=z))


def seta(ax, p, q, cor="white", lw=1.6, estilo="-|>", z=7, ls="-", ms=10):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle=estilo, mutation_scale=ms, color=cor, lw=lw, zorder=z, ls=ls,
                                 shrinkA=0, shrinkB=0))


def texto(ax, x, y, s, cor="white", fs=8, ha="center", va="center", z=8, bg=None, weight="normal"):
    kw = {}
    if bg:
        kw["bbox"] = dict(boxstyle="round,pad=0.25", fc=bg, ec="none", alpha=0.85)
    ax.text(x, y, s, color=cor, fontsize=fs, ha=ha, va=va, zorder=z, weight=weight, **kw)


def dim(ax, p, q, rotulo, off=(0, 0), cor="#222", fs=8):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle="<|-|>", mutation_scale=7, color=cor, lw=0.9, zorder=9,
                                 shrinkA=0, shrinkB=0))
    mx, my = (p[0] + q[0]) / 2 + off[0], (p[1] + q[1]) / 2 + off[1]
    ax.text(mx, my, rotulo, ha="center", va="center", fontsize=fs, color=cor, zorder=10,
            bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.9))


def fundo_cartao(ax, titulo=None):
    ax.axis("off")


# ----------------------------- Graphviz -----------------------------
FONTE = "Liberation Sans"


def dot(src, nome, dpi=200, engine="dot"):
    base = os.path.join(OUT, nome)
    with open(base + ".dot", "w", encoding="utf-8") as f:
        f.write(src)
    subprocess.run([engine, "-Tpng", f"-Gdpi={dpi}", base + ".dot", "-o", base + ".png"], check=True)
    os.remove(base + ".dot")
    print("  dot:", nome)


def esc(s):
    return s.replace('"', '\\"').replace("\n", "\\n")


class N:
    """Nó de uma árvore de comportamento para desenho.
    kind: SEQ RSEQ FB RFB PAR DEC COND ACT SUB
    novo=True destaca nós que ainda serão criados."""
    _cont = 0

    def __init__(self, kind, label, children=(), status=None, novo=False, nota=None):
        self.kind, self.label, self.children, self.status, self.novo, self.nota = kind, label, list(children), status, novo, nota
        N._cont += 1
        self.id = f"n{N._cont}"


ESTILO = {
    "SEQ":  dict(shape="box", style="filled", fillcolor="#dbe9f6", color=AZUL2, icone="→"),
    "RSEQ": dict(shape="box", style="filled", fillcolor="#dbe9f6", color=AZUL2, icone="→", per=2),
    "FB":   dict(shape="box", style="filled", fillcolor="#fde7d3", color=LARANJA, icone="?"),
    "RFB":  dict(shape="box", style="filled", fillcolor="#fde7d3", color=LARANJA, icone="?", per=2),
    "PAR":  dict(shape="box", style="filled", fillcolor="#e9e2f7", color=ROXO, icone="⇉"),
    "DEC":  dict(shape="hexagon", style="filled", fillcolor="#f3f0e0", color="#9a8a2a", icone="◇"),
    "COND": dict(shape="ellipse", style="filled", fillcolor="#e1f3e8", color=VERDE, icone=""),
    "ACT":  dict(shape="box", style="rounded,filled", fillcolor="white", color=AZUL, icone=""),
    "SUB":  dict(shape="box", style="rounded,filled,dashed", fillcolor="#f4f4f6", color=CINZA, icone="▣"),
}
STATUS_COR = {"S": "#bfe8c9", "F": "#f5c2bc", "R": "#fbe7a1", "-": "#eceff1"}
STATUS_TXT = {"S": "SUCCESS", "F": "FAILURE", "R": "RUNNING", "-": "não executado"}


def _no_dot(n, prefix=""):
    e = ESTILO[n.kind]
    lab = (e["icone"] + "  " if e["icone"] else "") + n.label + ("  ✦" if n.novo else "")
    if n.status:
        lab += "\n[" + STATUS_TXT[n.status] + "]"
    style = e["style"] + (",bold" if n.novo else "")
    attrs = [f'label="{esc(lab)}"', f'shape={e["shape"]}', f'style="{style}"',
             f'fillcolor="{STATUS_COR[n.status] if n.status else e["fillcolor"]}"',
             f'color="{LARANJA if n.novo else e["color"]}"', f'penwidth={2.4 if n.novo else 1.3}']
    if "per" in e:
        attrs.append(f'peripheries={e["per"]}')
    return f'  {prefix}{n.id} [{", ".join(attrs)}];\n'


def _walk(n, prefix, out_nodes, out_edges, numerar=True):
    out_nodes.append(_no_dot(n, prefix))
    ctrl = n.kind in ("SEQ", "RSEQ", "FB", "RFB", "PAR")
    for i, c in enumerate(n.children, 1):
        lab = f' [xlabel="{i}", fontsize=9, fontcolor="#7a858d"]' if (numerar and ctrl and len(n.children) > 1) else ""
        out_edges.append(f"  {prefix}{n.id} -> {prefix}{c.id}{lab};\n")
        _walk(c, prefix, out_nodes, out_edges, numerar)


def arvore(raiz, nome, rankdir="LR", titulo=None, legenda=False, nodesep=0.28, ranksep=0.5, fontsize=10, numerar=True, dpi=200, largura=None):
    nodes, edges = [], []
    _walk(raiz, "", nodes, edges, numerar)
    src = (f'digraph G {{\n  rankdir={rankdir}; ordering=out; nodesep={nodesep}; ranksep={ranksep}; bgcolor="white";\n'
           f'  node [fontname="{FONTE}", fontsize={fontsize}, margin="0.12,0.07"];\n  edge [color="#6b7782", arrowsize=0.6, fontname="{FONTE}"];\n')
    if titulo:
        src += f'  labelloc=t; label="{esc(titulo)}"; fontname="{FONTE}"; fontsize=12;\n'
    src += "".join(nodes) + "".join(edges)
    if legenda:
        src += _legenda()
    src += "}\n"
    dot(src, nome, dpi=dpi)


def _legenda():
    return ('  subgraph cluster_leg { label="Legenda"; fontname="%s"; fontsize=9; color="#cfd6dc"; style="rounded";\n'
            '    l1 [label="→  Sequence", shape=box, style=filled, fillcolor="#dbe9f6", color="%s", fontname="%s", fontsize=8];\n'
            '    l2 [label="→  ReactiveSequence", shape=box, style=filled, fillcolor="#dbe9f6", color="%s", peripheries=2, fontname="%s", fontsize=8];\n'
            '    l3 [label="?  Fallback", shape=box, style=filled, fillcolor="#fde7d3", color="%s", fontname="%s", fontsize=8];\n'
            '    l4 [label="?  ReactiveFallback", shape=box, style=filled, fillcolor="#fde7d3", color="%s", peripheries=2, fontname="%s", fontsize=8];\n'
            '    l5 [label="condição", shape=ellipse, style=filled, fillcolor="#e1f3e8", color="%s", fontname="%s", fontsize=8];\n'
            '    l6 [label="ação", shape=box, style="rounded,filled", fillcolor=white, color="%s", fontname="%s", fontsize=8];\n'
            '    l7 [label="▣  subárvore", shape=box, style="rounded,filled,dashed", fillcolor="#f4f4f6", color="%s", fontname="%s", fontsize=8];\n'
            '    l8 [label="nó novo  ✦", shape=box, style="rounded,filled,bold", fillcolor=white, color="%s", penwidth=2.4, fontname="%s", fontsize=8];\n'
            '    l1 -> l2 -> l3 -> l4 [style=invis]; l5 -> l6 -> l7 -> l8 [style=invis]; }\n'
            % (FONTE, AZUL2, FONTE, AZUL2, FONTE, LARANJA, FONTE, LARANJA, FONTE, VERDE, FONTE, AZUL, FONTE, CINZA, FONTE, LARANJA, FONTE))


def grafo(src_corpo, nome, rankdir="LR", nodesep=0.4, ranksep=0.7, extra="", dpi=200):
    src = (f'digraph G {{\n  rankdir={rankdir}; nodesep={nodesep}; ranksep={ranksep}; bgcolor="white"; compound=true; {extra}\n'
           f'  node [fontname="{FONTE}", fontsize=10, margin="0.14,0.08", shape=box, style="rounded,filled", fillcolor="white", color="{AZUL}"];\n'
           f'  edge [color="#6b7782", arrowsize=0.7, fontname="{FONTE}", fontsize=8.5, fontcolor="#44525d"];\n'
           f'{src_corpo}\n}}\n')
    dot(src, nome, dpi=dpi)
