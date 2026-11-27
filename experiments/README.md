# Guia de Execução dos Experimentos e Ablações (`experiments/`)

Este diretório contém a infraestrutura de benchmark, arquivos de configuração de ablação, o logger CSV desacoplado e os roteiros automatizados para avaliação experimental do sistema **OxeBots (SSL-EL)**.

---

## 1. Pré-requisitos: O que precisa estar aberto?

| Ferramenta | Precisa abrir? | Por quê? |
| :--- | :---: | :--- |
| **grSim** (Simulador) | **SIM** | Simula a física dos robôs/bola e publica os pacotes de visão (`224.5.23.2:10020`). |
| **SSL Game Controller** | **NÃO (deixe fechado!)** | Os scripts `e1_scenario.py` e `e2_scenario.py` emulam o árbitro e injetam a sequência legal do GC (`INIT_HALT -> INIT_STOP -> FORCE_START ...`) automaticamente. Se o Game Controller externo estiver aberto transmitindo ao mesmo tempo, ele disputará comandos com o script. |
| **RViz2 / Groot2** | **NÃO** | Os runners sobem toda a pilha ROS 2 em modo *headless* (`use_rviz:=False` / `rviz_team:=none`). |

### Checklist rápido das portas no `grSim`
Certifique-se de que no menu de configuração do `grSim` (`Communication`) as portas estejam no padrão do repositório:
* **Vision multicast address**: `224.5.23.2` | **Vision multicast port**: `10020`
* **Command listen port**: `20011` (e/ou `Simulator control port`: `10300`)
* **Blue team control port**: `10301`
* **Yellow team control port**: `10302`
* **Quantidade de robôs**: 3 Azuis (IDs `0`, `1`, `2`) e 3 Amarelos (IDs `0`, `1`, `2`) ativos em campo.

---

## 2. Estrutura do Diretório `experiments/`

```text
experiments/
├── README.md                              # Este guia de orientação
├── benchmark_logger.py                    # Logger CSV passivo (6 tópicos -> tabela única)
├── configs/
│   ├── default_benchmark.yaml             # Configuração base com todos os parâmetros expostos
│   ├── e1_a_unprotected.yaml              # E1 Config A: enable_safety_gate=false, use_reactive_preemption=false
│   ├── e1_b_preemption_only.yaml          # E1 Config B: enable_safety_gate=false, use_reactive_preemption=true
│   ├── e1_c_full.yaml                     # E1 Config C: enable_safety_gate=true,  use_reactive_preemption=true
│   ├── e2_0_greedy.yaml                   # E2 Config 0: hysteresis=0.0, time_hysteresis=0.0
│   ├── e2_1_cost_only.yaml                # E2 Config 1: hysteresis=0.6, time_hysteresis=0.0
│   ├── e2_2_time_only.yaml                # E2 Config 2: hysteresis=0.0, time_hysteresis=0.5
│   ├── e2_3_dual_calibrated.yaml          # E2 Config 3: hysteresis=0.6, time_hysteresis=0.5
│   └── e2_4_dual_legacy.yaml              # E2 Config 4: hysteresis=2.5, time_hysteresis=2.0 (Lock-In)
├── e1/
│   ├── e1_scenario.py                     # Roteiro determinístico de 38 s (Safety Gate & Preempção)
│   └── run_e1.sh                          # Runner em lote do E1 (A, B, C)
├── e2/
│   ├── e2_scenario.py                     # Roteiro determinístico de ~65 s (Histerese Dupla & Lock-In)
│   └── run_e2.sh                          # Runner em lote do E2 (5 configurações)
└── results/                               # (Ignorado pelo git) CSVs brutos e timestamps de eventos
```

---

## 3. Como Rodar o Experimento E1 (Safety Gate e Preempção Reativa — 38 s)

Com apenas o **`grSim` aberto** (e o Game Controller **fechado**), execute a partir da raiz do workspace:

* **Smoke test rápido (1 repetição de A, B e C — ~2 min no total)**:
  ```bash
  ./experiments/e1/run_e1.sh 1
  ```
* **Bateria determinística com `N` repetições (ex.: 2)**:
  ```bash
  ./experiments/e1/run_e1.sh 2
  ```
* **Modo Partida Completa (`match:=True`, Azul vs. Amarelo ativos)**:
  ```bash
  ./experiments/e1/run_e1.sh 2 --match
  ```

### Sequência de estados do E1 (38 s no total, `--duration 40` no logger)
1. `INIT_HALT` (`1 s`) $\rightarrow$ `INIT_STOP` (`2 s`): setup oficial do SSL Game Controller.
2. `NORMAL_PLAY_1` via `FORCE_START` (`10 s`): jogo corrido + sprint nos últimos `2.5 s` rumo à bola.
3. `STOP` principal (`10 s`): avaliação do teto de `0.75 m/s`, clamp radial de `500 mm` e recuo via D\*.
4. `NORMAL_PLAY_2` via `FORCE_START` (`10 s`): bola posicionada próxima à borda da área adversária (`x = 1640..1660 mm, y = 0`) com o atacante alinhado atrás para estressar a proteção de área de defesa, seguido de sprint nos últimos `2.5 s`.
5. `HALT` final (`5 s`): parada imediata a partir de `NORMAL_PLAY_2`.

---

## 4. Como Rodar o Experimento E2 (Ablação da Histerese Dupla e Lock-In — ~65 s)

Com apenas o **`grSim` aberto** (e o Game Controller **fechado**), execute a partir da raiz do workspace:

* **Execução padrão (1 repetição das 5 configurações — ~6 min no total)**:
  ```bash
  ./experiments/e2/run_e2.sh 1
  ```
* **Bateria com `N` repetições (ex.: 3)**:
  ```bash
  ./experiments/e2/run_e2.sh 3
  ```

### O que o Experimento E2 avalia em cada rodada (~65 s, `--duration 68` no logger)
1. **Setup Legal do SSL GC (`3 s`)**: `INIT_HALT` (`1 s`) $\rightarrow$ `INIT_STOP` (`2 s`).
2. **Fase 1 — Estresse de Fronteira / Chattering (`0 s` a `32 s` de `NORMAL_PLAY`)**:
   * Robôs de linha ID 1 e ID 2 posicionados simetricamente em `(0.0, +0.90)` e `(0.0, -0.90)`.
   * A bola oscila a cada `0.4 s` em torno da mediatriz ($\pm 0.14\text{ m} \implies \Delta r \approx 0.28\text{ m}$) com rajadas curtas ($\pm 0.38\text{ m}$ por `0.18 s`), medindo o número de trocas espúrias (`SW_P1`), a taxa por minuto (`SW/MIN`) e a distância percorrida (`DIST_P1`).
3. **Fase 2A — Troca Legítima Moderada (`t = 32 s` a `47 s`, evento `LEGIT_SWITCH_MODERATE`)**:
   * Atacante atual posicionado a $r_{\text{att}} = 1.25\text{ m}$ da bola e defensor a $r_{\text{def}} = 0.35\text{ m}$ ($\Delta r = 0.90\text{ m}$: acima do limiar calibrado de `0.30 m`, porém abaixo do limiar legado de `1.25 m`), comprovando o **Lock-In** de `e2_4_dual_legacy`.
4. **Fase 2B — Troca Legítima Ampla (`t = 47 s` a `62 s`, evento `LEGIT_SWITCH_LARGE`)**:
   * Atacante atual posicionado a $r_{\text{att}} \approx 2.33\text{ m}$ e defensor a $r_{\text{def}} \approx 0.32\text{ m}$ ($\Delta r \approx 2.01\text{ m}$: acima de ambos os limiares), medindo a latência pura imposta pela histerese temporal (`0.0 s` vs. `0.5 s` vs. `2.0 s`).

---

## 5. Colunas dos CSVs Gerados (`experiments/results/{e1,e2}/.../run_XX.csv`)

| Coluna | Descrição |
| :--- | :--- |
| `timestamp_ms` | Timestamp epoch em milissegundos. |
| `tick_duration_us` | Tempo de execução do `StrategyNode::tickOnce()` em microssegundos ($\mu\text{s}$). |
| `gc_state` | Fase atual no `GameState` (`RUN`, `STOP`, `HALT`, `BALL_PLACEMENT`, etc.). |
| `active_robots_count` | Número de robôs aliados visíveis em `/game_data`. |
| `robot_id` | ID do robô (`0`, `1`, `2`). |
| `role` | Papel atual (`goalkeeper`, `attacker`, `defender`, `idle`). |
| `x`, `y` | Posição do robô no campo em milímetros (`mm`). |
| `v_cmd` | Velocidade linear comandada pelo controlador (`m/s`). |
| `v_meas` | Velocidade linear medida pela visão (`m/s`, filtrada em janela deslizante + mediana). |
| `viol_speed_stop` | `1` se `gc_state == STOP` e (`v_cmd > 0.751` ou `v_meas > 0.751`), senão `0`. |
| `viol_defense_area` | `1` se robô de linha invadir área de defesa (ou goleiro invadir área adversária), senão `0`. |
| `viol_ball_radius` | `1` se em `STOP`/reinício adversário e `dist(robô, bola) < 500 mm`, senão `0`. |
| `ghost_cmd` | `1` se houver comando de movimento para robô ausente da visão, senão `0`. |
