#!/usr/bin/env python3
"""Gera os apêndices C (regras) e D (XMLs) a partir dos arquivos em anexos/."""
import csv, os, glob
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ---- Apêndice C: regras
rows = list(csv.DictReader(open(os.path.join(HERE, "anexos", "matriz-regras.csv"), encoding="utf-8")))
cob = {"coberto": "Coberto", "parcial": "Parcial", "não coberto": "Não coberto", "fora do escopo": "Fora do software"}
md = ["<!-- apendice -->", "# As regras do regulamento e onde cada uma é tratada", "",
      "Esta tabela relaciona as 30 regras do regulamento SSL-EL (edição de 2024-08-05) que afetam o software ao componente da arquitetura que as trata e ao cenário de teste que as verifica (Capítulo 23). *Cobertura hoje* indica o estado do sistema **atual** (Parte III): **Coberto** significa que existe um mecanismo no código (ainda sem teste automatizado); **Parcial**, que existe, mas com lacunas; **Não coberto**, que nada o trata; **Fora do software**, que depende de hardware ou de pessoas.", "",
      "| ID | Regra | Seção (página) | Como é tratada na arquitetura | Teste | Prio. | Cobertura hoje |", "|---|---|---|---|---|---|---|"]
for r in rows:
    md.append(f"| {r['REQ-ID']} | {r['regra']} | {r['secao/pagina PDF']} | {r['interpretacao operacional']} ({r['no/subarvore responsavel']}) | {r['condicao de teste']} | {r['prioridade']} | {cob.get(r['status de cobertura'], r['status de cobertura'])} |")
n = {}
for r in rows: n[r["status de cobertura"]] = n.get(r["status de cobertura"], 0) + 1
md += ["", f"Resumo: {n.get('coberto',0)} regras cobertas, {n.get('parcial',0)} parciais, {n.get('não coberto',0)} não cobertas e {n.get('fora do escopo',0)} fora do escopo do software.", ""]
open(os.path.join(HERE, "capitulos", "A3-regras.md"), "w", encoding="utf-8").write("\n".join(md))

# ---- Apêndice D: XMLs
ordem = [("master_strategy_el.xml", "A árvore mestre (`MainTreeEL`)", "Capítulo 16"),
         ("common.xml", "Subárvores comuns: modo degradado, HALT, TIMEOUT, cobrador e recuo", "Capítulos 17 e 18"),
         ("stop.xml", "A subárvore de STOP", "Capítulo 17"),
         ("restarts.xml", "Kick-off, pênalti e free kick", "Capítulo 18"),
         ("ball_placement_their.xml", "Ball placement do adversário", "Capítulo 18"),
         ("ball_placement_our.xml", "Ball placement nosso", "Capítulo 18"),
         ("normal_play.xml", "Jogo corrido", "Capítulo 19")]
md = ["<!-- apendice -->", "# Os arquivos XML propostos", "",
      "Os arquivos abaixo são a **especificação** das árvores da Parte IV. Eles só se tornam executáveis quando os nós novos (marcados com ✦ nas figuras) estiverem implementados e registrados; os nós existentes que usam estão listados no cabeçalho de cada arquivo. As cópias para uso estão em `docs/manual/anexos/xml-proposto/`.", ""]
for f, t, c in ordem:
    txt = open(os.path.join(HERE, "anexos", "xml-proposto", f), encoding="utf-8").read().strip()
    md += [f"## {t}", "", f"Arquivo `{f}` — referente ao {c}.", "", "```xml", txt, "```", ""]
open(os.path.join(HERE, "capitulos", "A4-xml-propostos.md"), "w", encoding="utf-8").write("\n".join(md))
print("apêndices C e D gerados")
