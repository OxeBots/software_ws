#!/usr/bin/env python3
"""Gera o PDF de slides (16:9) que apresenta o manual. Conteúdo em scripts/slides_conteudo.py."""
import html, os, re, sys
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "scripts"))
for extra in os.environ.get("MANUAL_PYLIBS", "").split(":"):
    if extra:
        sys.path.insert(0, extra)
import markdown
from weasyprint import HTML
import slides_conteudo as C

TITULO = "Manual da Estratégia OxeBots"


def inline(s):
    out = markdown.markdown(s, extensions=["fenced_code"])
    return re.sub(r"^<p>(.*)</p>$", r"\1", out.strip(), flags=re.S)


def _caminho(nome):
    for d in ("figuras_slides", "figuras"):
        p = os.path.join(HERE, d, nome + ".png")
        if os.path.exists(p):
            return d, p
    raise FileNotFoundError(nome)


def aspecto(nome):
    from PIL import Image
    _, p = _caminho(nome)
    w, h = Image.open(p).size
    return w / h


def img(nome, estilo="", caixa=None):
    """caixa=(largura, altura) em px: a figura é ajustada (e ampliada, se preciso) para caber."""
    d, _ = _caminho(nome)
    if caixa:
        ar = aspecto(nome)
        w = min(caixa[0], caixa[1] * ar)
        estilo = f"width:{int(w)}px;height:auto;" + estilo
    return f'<img src="{d}/{nome}.png" style="{estilo}"/>'


def lista(itens):
    return "<ul>" + "".join(f"<li>{inline(i)}</li>" for i in itens) + "</ul>"


class Deck:
    def __init__(self):
        self.slides, self.parte, self.n = [], "", 0

    def _wrap(self, titulo, corpo, nota=None, kicker=None):
        self.n += 1
        k = f"<small>{html.escape(kicker or self.parte)}</small>" if (kicker or self.parte) else ""
        nt = ""
        if nota:
            cls, txt = ("", nota) if isinstance(nota, str) else nota
            nt = f'<div class="nota {cls}">{inline(txt)}</div>'
        self.slides.append(
            f'<section class="slide"><div class="topo"></div><h1 class="t">{k}{inline(titulo)}</h1>{corpo}{nt}'
            f'<div class="rodape"><span><b>OxeBots</b> · {TITULO}</span><span>{self.n}</span></div></section>')

    # --- tipos de slide
    def capa(self, titulo, sub, figura, pe):
        self.n += 1
        self.slides.append(f'<section class="slide capa"><div class="faixa"></div><div class="tx"><div class="selo">OxeBots · RoboCup SSL Entry Level</div>'
                           f'<h1>{titulo}</h1><div class="sub">{sub}</div></div>{img(figura)}<div class="pe">{pe}</div></section>')

    def divisor(self, rotulo, titulo, texto, caps):
        self.n += 1
        self.parte = f"{rotulo} — {titulo}"
        self.slides.append(f'<section class="slide parte"><div class="barra"></div><div class="tx"><div class="rot">{rotulo}</div><h1>{titulo}</h1>'
                           f'<p>{texto}</p><div class="caps">{caps}</div></div></section>')

    def pontos(self, titulo, itens, nota=None, cols=1):
        corpo = f'<div class="corpo"><div class="col-txt" style="flex:1 1 100%">{lista(itens)}</div></div>'
        self._wrap(titulo, corpo, nota)

    UTIL_W, UTIL_H = 1168, 534

    @staticmethod
    def _h_nota(nota):
        return 62 if nota else 0

    def fig(self, titulo, figura, itens=None, legenda=None, lado="dir", nota=None, larg=62, altura=None):
        ar = aspecto(figura)
        hn = self._h_nota(nota)
        leg = 26 if legenda else 0
        if itens and ar >= 1.7:                         # figura larga: em cima, texto embaixo em 2 colunas
            linhas = (len(itens) + 1) // 2
            h_txt = 20 + linhas * 52
            caixa = (self.UTIL_W, self.UTIL_H - hn - h_txt - leg)
            corpo = (f'<div class="fig-full">{img(figura, caixa=caixa)}' + (f'<div class="legenda">{html.escape(legenda)}</div>' if legenda else "")
                     + f'</div><div style="column-count:2;column-gap:40px;margin-top:10px;font-size:21px">{lista(itens)}</div>')
        elif itens:                                     # figura alta/quadrada: ao lado do texto
            wf = int(self.UTIL_W * max(larg, 50) / 100) - 20
            caixa = (wf, self.UTIL_H - hn - leg)
            f = f'<div class="col-fig" style="flex:0 0 {wf}px">{img(figura, caixa=caixa)}' + (f'<div class="legenda">{html.escape(legenda)}</div>' if legenda else "") + "</div>"
            t = f'<div class="col-txt" style="flex:1 1 auto;font-size:23px">{lista(itens)}</div>'
            corpo = f'<div class="corpo centro" style="min-height:{self.UTIL_H - hn - 6}px">{f + t if lado == "dir" else t + f}</div>'
        else:                                           # só a figura
            caixa = (self.UTIL_W, self.UTIL_H - hn - leg)
            corpo = f'<div class="fig-full">{img(figura, caixa=caixa)}' + (f'<div class="legenda">{html.escape(legenda)}</div>' if legenda else "") + "</div>"
        self._wrap(titulo, corpo, nota)

    def duas(self, titulo, f1, f2, l1=None, l2=None, itens=None, nota=None, altura=None):
        """Duas figuras: cada uma ganha um slide inteiro (legibilidade); o texto vai ao segundo."""
        self.fig(f"{titulo} (1/2)", f1, None, legenda=l1)
        self.fig(f"{titulo} (2/2)", f2, itens, legenda=l2, nota=nota)

    def cartoes(self, titulo, cards, cols=3, nota=None, extra=""):
        cs = "".join(f'<div class="card {c[2] if len(c) > 2 else ""}"><h3>{inline(c[0])}</h3>{self._card_txt(c[1])}</div>' for c in cards)
        um = " um" if len(cards) <= cols else ""
        self._wrap(titulo, f'<div class="cards c{cols}{um}">{cs}</div>{extra}', nota)

    @staticmethod
    def _card_txt(t):
        return lista(t) if isinstance(t, list) else f"<p>{inline(t)}</p>"

    def tabela(self, titulo, cab, linhas, nota=None, antes=None):
        th = "".join(f"<th>{inline(c)}</th>" for c in cab)
        tr = "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in l) + "</tr>" for l in linhas)
        pre = f"<p>{inline(antes)}</p>" if antes else ""
        self._wrap(titulo, f"{pre}<table><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table>", nota)

    def codigo(self, titulo, cod, itens=None, nota=None, figura=None):
        c = f'<pre><code>{html.escape(cod)}</code></pre>'
        if figura:
            corpo = f'<div class="corpo"><div class="col-txt" style="flex:1 1 52%">{c}{lista(itens) if itens else ""}</div><div class="col-fig" style="flex:1 1 48%">{img(figura, caixa=(560, 470))}</div></div>'
        elif itens:
            corpo = f'<div class="corpo"><div class="col-txt" style="flex:1 1 60%">{c}</div><div class="col-txt" style="flex:1 1 40%">{lista(itens)}</div></div>'
        else:
            corpo = c
        self._wrap(titulo, corpo, nota)

    def html(self):
        return ('<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><title>Apresentação — Manual da Estratégia OxeBots</title></head><body>'
                + "".join(self.slides) + "</body></html>")


if __name__ == "__main__":
    d = Deck()
    C.montar(d)
    open(os.path.join(HERE, "Apresentacao-Manual-OxeBots.html"), "w", encoding="utf-8").write(d.html())
    HTML(string=d.html(), base_url=HERE).write_pdf(os.path.join(HERE, "Apresentacao-Manual-OxeBots.pdf"),
                                                   stylesheets=[os.path.join(HERE, "estilo_slides.css")])
    print("slides:", d.n)
