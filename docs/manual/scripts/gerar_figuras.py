#!/usr/bin/env python3
"""Gera todas as figuras do manual em docs/manual/figuras/ (requer matplotlib e graphviz 'dot')."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fig_campo, fig_bt, fig_ataque, fig_arq

fig_campo.f_campo_dimensoes(); fig_campo.f_geometria_stop_placement(); fig_campo.f_geometria_kickoff_penalty()
fig_campo.f_geometria_freekick(); fig_campo.f_linha_do_tempo_partida(); fig_campo.f_sistemas_coordenadas()
fig_bt.bt_conceitos(); fig_bt.arvores_atuais(); fig_bt.arvores_propostas()
for f in [fig_ataque.f_pontos_ataque, fig_ataque.f_fases_atacante, fig_ataque.f_defensor, fig_ataque.f_goleiro, fig_ataque.f_clamp_area,
          fig_ataque.f_dstar, fig_ataque.f_pure_pursuit, fig_ataque.f_inversao_lado, fig_ataque.f_lado_literais, fig_ataque.f_custo_papel,
          fig_ataque.f_histerese, fig_ataque.f_normal_start, fig_ataque.f_preempcao_timeline, fig_ataque.f_slots, fig_ataque.f_degradacao]:
    f()
for f in [fig_arq.f_capa, fig_arq.f_camadas, fig_arq.f_processos, fig_arq.f_fluxo, fig_arq.f_estados_gc, fig_arq.f_override, fig_arq.f_chute,
          fig_arq.f_pipeline_movimento, fig_arq.f_strategy_node, fig_arq.f_no_ros_vs_bt, fig_arq.f_hibrida, fig_arq.f_camadas_decisao,
          fig_arq.f_mapa_comando_fase, fig_arq.f_game_state_pipeline, fig_arq.f_safety_gate, fig_arq.f_blackboard_fluxo, fig_arq.f_piramide,
          fig_arq.f_gantt, fig_arq.f_dependencias, fig_arq.f_mapa_manual]:
    f()
print("figuras prontas")
