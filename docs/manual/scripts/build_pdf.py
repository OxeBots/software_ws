#!/usr/bin/env python3
"""Gera o PDF (e o .md consolidado) do Manual da Estratégia OxeBots.

Uso (a partir de docs/manual):  python3 scripts/build_pdf.py
Requer: markdown, weasyprint, pygments  (pip install markdown weasyprint pygments)
"""
import glob, os, re, sys, html
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for extra in os.environ.get("MANUAL_PYLIBS", "").split(":"):
    if extra:
        sys.path.insert(0, extra)
import markdown
from weasyprint import HTML

TITULO = "Manual da Estratégia OxeBots"
SUBTITULO = "Behavior Trees, arquitetura de jogo e implementação para a RoboCup Small Size League – Entry Level"
VERSAO = "Versão 1.0 · Outubro de 2026"

MARK_PARTE = re.compile(r"^<!--\s*parte:\s*(.*?)\s*\|\s*(.*?)\s*-->\s*$", re.M)
MARK_APENDICE = re.compile(r"^<!--\s*apendice\s*-->\s*$", re.M)
IMG = re.compile(r"^!\[(?P<alt>[^\]]*)\]\((?P<src>[^)]+)\)\s*$", re.M)
REF = re.compile(r"\{\{fig:([A-Za-z0-9_\-]+)\}\}")
LETRAS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
ALTAS = {"arvore_mestre_atual"}


def ler_capitulos():
    arqs = sorted(glob.glob(os.path.join(HERE, "capitulos", "*.md")))
    caps, n_cap, n_ap = [], 0, 0
    for a in arqs:
        txt = open(a, encoding="utf-8").read()
        parte = MARK_PARTE.search(txt)
        apendice = bool(MARK_APENDICE.search(txt))
        txt = MARK_PARTE.sub("", txt)
        txt = MARK_APENDICE.sub("", txt).strip() + "\n"
        if apendice:
            rot = LETRAS[n_ap]; n_ap += 1
        else:
            n_cap += 1; rot = str(n_cap)
        caps.append(dict(arquivo=a, texto=txt, rot=rot, apendice=apendice,
                         parte=(parte.group(1), parte.group(2)) if parte else None))
    return caps


def numerar_figuras(caps):
    fig_num, lista = {}, []
    for c in caps:
        k = 0
        for m in IMG.finditer(c["texto"]):
            k += 1
            stem = os.path.splitext(os.path.basename(m.group("src")))[0]
            num = f"{c['rot']}.{k}"
            fig_num[stem] = num
            lista.append((stem, num, m.group("alt")))
    return fig_num, lista


def resolver_figuras_md(texto, fig_num):
    """Para o .md consolidado: legenda em itálico abaixo da imagem; referências em texto."""
    def img(m):
        stem = os.path.splitext(os.path.basename(m.group("src")))[0]
        return f"![{m.group('alt')}]({m.group('src')})\n\n*Figura {fig_num[stem]} — {m.group('alt')}*\n"
    texto = IMG.sub(img, texto)
    return REF.sub(lambda m: f"Figura {fig_num[m.group(1)]}", texto)


def md_para_html(texto, fig_num):
    def img(m):
        stem = os.path.splitext(os.path.basename(m.group("src")))[0]
        return (f'<figure id="fig-{stem}"{" class=alta" if stem in ALTAS else ""}><img src="{m.group("src")}" alt=""/>'
                f'<figcaption><b>Figura {fig_num[stem]}</b> — {html.escape(m.group("alt"))}</figcaption></figure>\n')
    texto = IMG.sub(img, texto)
    texto = REF.sub(lambda m: f'<a href="#fig-{m.group(1)}">Figura {fig_num[m.group(1)]}</a>', texto)
    md = markdown.Markdown(
        extensions=["tables", "fenced_code", "admonition", "sane_lists", "codehilite", "md_in_html"],
        extension_configs={"codehilite": {"guess_lang": False, "noclasses": True, "pygments_style": "friendly"}},
    )
    return md.convert(texto)


def numerar_titulos(corpo, rot, indice, primeiro):
    c = [0, 0, 0]
    def sub(m):
        nivel = int(m.group(1)); conteudo = m.group(2)
        if nivel == 1:
            cls = "cap primeiro" if primeiro else "cap"
            rotulo = (f"Apêndice {rot}" if rot in LETRAS else f"Capítulo {rot}")
            indice.append(("cap", rot, re.sub("<.*?>", "", conteudo), f"c{rot}"))
            return (f'<h1 class="{cls}" id="c{rot}" data-titulo="{rotulo} — {html.escape(re.sub("<.*?>", "", conteudo))}"><span class="num">{rotulo}</span>{conteudo}</h1>')
        if nivel == 2:
            c[0] += 1; c[1] = 0
            n = f"{rot}.{c[0]}"; i = f"c{rot}s{c[0]}"
            indice.append(("sec", n, re.sub("<.*?>", "", conteudo), i))
            return f'<h2 id="{i}"><span class="num">{n}</span>{conteudo}</h2>'
        if nivel == 3:
            c[1] += 1
            n = f"{rot}.{c[0]}.{c[1]}"
            return f'<h3><span class="num">{n}</span>{conteudo}</h3>'
        return m.group(0)
    return re.sub(r"<h([1-3])>(.*?)</h\1>", sub, corpo, flags=re.S)


def numerar_titulos_md(texto, rot):
    out, c, dentro = [], [0, 0], False
    for lin in texto.splitlines():
        if lin.startswith("```"):
            dentro = not dentro
        if not dentro:
            m = re.match(r"^(#{1,3})\s+(.*)$", lin)
            if m:
                nv = len(m.group(1))
                if nv == 1:
                    lin = f"# {'Apêndice ' if rot in LETRAS else 'Capítulo '}{rot} — {m.group(2)}"
                elif nv == 2:
                    c[0] += 1; c[1] = 0; lin = f"## {rot}.{c[0]} {m.group(2)}"
                else:
                    c[1] += 1; lin = f"### {rot}.{c[0]}.{c[1]} {m.group(2)}"
        out.append(lin)
    return "\n".join(out)


def montar():
    caps = ler_capitulos()
    fig_num, lista_fig = numerar_figuras(caps)
    indice, partes_html, md_total = [], [], []
    corpo_html = []
    primeiro = True
    for c in caps:
        if c["parte"]:
            t, d = c["parte"]
            indice.append(("parte", "", t, f"p{len(indice)}"))
            corpo_html.append(
                f'<section class="parte" id="p{len(indice)-1}"><div class="barra"></div><div class="inner">'
                f'<div class="rot">{html.escape(t.split("—")[0].strip())}</div>'
                f'<h1>{html.escape(t.split("—",1)[1].strip() if "—" in t else t)}</h1><p>{html.escape(d)}</p></div></section>')
            md_total.append(f"\n\n---\n\n# {t}\n\n*{d}*\n\n")
        h = md_para_html(c["texto"], fig_num)
        corpo_html.append(numerar_titulos(h, c["rot"], indice, primeiro))
        primeiro = False
        md_total.append(numerar_titulos_md(resolver_figuras_md(c["texto"], fig_num), c["rot"]) + "\n")

    # Sumário
    linhas = []
    for tipo, n, t, i in indice:
        if tipo == "parte":
            linhas.append(f'<div class="linha parte-l"><a href="#{i}">{html.escape(t)}</a></div>')
        elif tipo == "cap":
            rot = ("Apêndice " + n) if n in LETRAS else n
            linhas.append(f'<div class="linha cap"><a href="#{i}"><span class="num">{rot}</span>{html.escape(t)}</a></div>')
        else:
            linhas.append(f'<div class="linha sec"><a href="#{i}"><span class="num">{n}</span>{html.escape(t)}</a></div>')
    sumario = '<section class="sumario"><h1 class="tit">Sumário</h1>' + "\n".join(linhas) + "</section>"

    lf = ['<section class="sumario"><h1 class="tit" style="page-break-before:always">Lista de figuras</h1>']
    for stem, num, alt in lista_fig:
        lf.append(f'<div class="linha sec"><a href="#fig-{stem}"><span class="num">{num}</span>{html.escape(alt)}</a></div>')
    lf.append("</section>")

    capa_img = '<img class="logo-bt" src="figuras/capa_arvore.png" alt=""/>' if os.path.exists(os.path.join(HERE, "figuras", "capa_arvore.png")) else ""
    capa = (f'<section class="capa"><div class="conteudo"><div class="selo">OxeBots · RoboCup SSL Entry Level</div>'
            f'<h1>{TITULO}</h1><div class="sub">{SUBTITULO}</div></div><div class="faixa"></div>{capa_img}'
            f'<div class="rodape"><b>{VERSAO}</b><br/>Equipe OxeBots</div></section>')

    doc = (f'<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><title>{TITULO}</title></head><body>'
           + capa + sumario + "".join(lf) + "\n".join(corpo_html) + "</body></html>")
    open(os.path.join(HERE, "Manual-Estrategia-OxeBots.html"), "w", encoding="utf-8").write(doc)
    HTML(string=doc, base_url=HERE).write_pdf(
        os.path.join(HERE, "Manual-Estrategia-OxeBots.pdf"),
        stylesheets=[os.path.join(HERE, "estilo.css")])

    cab = f"# {TITULO}\n\n*{SUBTITULO}*\n\n{VERSAO}\n\n## Sumário\n\n"
    for tipo, n, t, i in indice:
        if tipo == "parte": cab += f"\n**{t}**\n\n"
        elif tipo == "cap": cab += f"- {'Apêndice ' if n in LETRAS else 'Capítulo '}{n} — {t}\n"
        else: cab += f"  - {n} {t}\n"
    open(os.path.join(HERE, "Manual-Estrategia-OxeBots.md"), "w", encoding="utf-8").write(cab + "\n" + "".join(md_total))
    print("ok:", len(caps), "capítulos,", len(lista_fig), "figuras")


if __name__ == "__main__":
    montar()
