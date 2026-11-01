# Manual da Estratégia OxeBots

Este diretório contém o manual completo (PDF e Markdown) e tudo o que é necessário para regenerá-lo.

- **`Manual-Estrategia-OxeBots.pdf`** — o manual pronto para leitura (capa, sumário, 24 capítulos, 5 apêndices, lista de figuras).
- **`Manual-Estrategia-OxeBots.md`** — a mesma versão em Markdown consolidado (as imagens ficam em `figuras/`).
- `capitulos/` — o texto-fonte, um arquivo por capítulo (`NN-*.md`) e por apêndice (`A*-*.md`).
- `figuras/` — as figuras (geradas por `scripts/gerar_figuras.py`).
- `anexos/` — backlog, matriz de regras e XMLs propostos.

## Regenerar

Dependências (Python 3): `pip install markdown weasyprint pygments matplotlib`, mais o Graphviz (`dot`).

```bash
cd docs/manual
python3 scripts/gerar_figuras.py      # figuras (matplotlib + graphviz)
python3 scripts/gerar_apendices.py    # apêndices C e D, a partir de anexos/
python3 scripts/build_pdf.py          # PDF + Markdown consolidado
```

Para editar o texto, altere os arquivos de `capitulos/`. Os marcadores `<!-- parte: ... -->` e `<!-- apendice -->` no início de um arquivo criam a divisória de parte e a numeração por letra; imagens em uma linha própria, `![legenda](figuras/arquivo.png)`, viram figuras numeradas e podem ser citadas com `{{fig:arquivo}}`.
