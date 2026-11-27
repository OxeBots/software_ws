# Guia de Execução dos Experimentos e Ablações (`experiments/`)

Este diretório contém a infraestrutura de benchmark, arquivos de configuração de ablação, o logger CSV desacoplado e os roteiros automatizados para avaliação experimental do sistema **OxeBots (SSL-EL)**.

---

## 1. Pré-requisitos: O que precisa estar aberto?

| Ferramenta | Precisa abrir? | Por quê? |
| :--- | :---: | :--- |
| **grSim** (Simulador) | **SIM** | Simula a física dos robôs/bola e publica os pacotes de visão (`224.5.23.2:10020`). |
| **SSL Game Controller** | **NÃO (deixe fechado!)** | O próprio script `e1_scenario.py` emula o árbitro e injeta os estados (`RUN`, `STOP`, `HALT`, `BALL_PLACEMENT`, `NORMAL_START`) de forma 100% automatizada e determinística. Se o Game Controller externo estiver aberto transmitindo ao mesmo tempo, ele disputará comandos com o script. |
| **RViz2 / Groot2** | **NÃO** | O runner sobe toda a pilha ROS 2 em modo *headless* (`use_rviz:=False` / `rviz_team:=none`). |

### Checklist rápido das portas no `grSim`
Certifique-se de que no menu de configuração do `grSim` (`Communication`) as portas estejam no padrão do repositório:
* **Vision multicast address**: `224.5.23.2` | **Vision multicast port**: `10020`
* **Command listen port**: `20011` (e/ou `Simulator control port`: `10300`)
* **Blue team control port**: `10301`
* **Yellow team control port**: `10302`
* **Quantidade de robôs**: 3 Azuis (IDs `0`, `1`, `2`) e 3 Amarelos (IDs `0`, `1`, `2`) ativos em campo.

> **Dica**: Se o `grSim` estiver rodando no Windows/Host e o ROS 2 no container/WSL, confira se o `simulator_ip` em `src/oxebots_bringup/config/match_config.yaml` aponta para o IP correto do host (ou `127.0.0.1` se estiver em rede `host`).

---

## 2. Estrutura do Diretório `experiments/`

```text
experiments/
├── README.md                              # Este guia de orientação
├── benchmark_logger.py                    # Logger CSV passivo (6 tópicos -> tabela única)
├── configs/
│   ├── default_benchmark.yaml             # Configuração base com todos os parâmetros expostos
│   ├── e1_a_unprotected.yaml              # Config A: enable_safety_gate=false, use_reactive_preemption=false
│   ├── e1_b_preemption_only.yaml          # Config B: enable_safety_gate=false, use_reactive_preemption=true
│   └── e1_c_full.yaml                     # Config C: enable_safety_gate=true,  use_reactive_preemption=true
├── e1/
│   ├── e1_scenario.py                     # Roteiro determinístico de 30 s (posições + árbitro)
│   └── run_e1.sh                          # Runner em lote que executa A, B e C e gera o resumo
└── results/                               # (Ignorado pelo git) CSVs brutos e timestamps de eventos
```

---

## 3. Como Rodar o Experimento E1 (Safety Gate e Preempção Reativa)

Com o **`grSim` aberto** (e o Game Controller **fechado**), execute a partir da raiz do workspace (`/home/matheus/software_ws`).
*(O script `run_e1.sh` detecta automaticamente se você está no host e redireciona a execução para dentro do DevContainer).*

### Opção 1 — Smoke Test Rápido (1 repetição de A, B e C — ~1,5 minuto)
Ideal para validar rapidamente que o `grSim` está recebendo comandos e gerando os CSVs:
```bash
./experiments/e1/run_e1.sh 1
```

### Opção 2 — Bateria Determinística Padrão (Recomendada para a Tabela de Ablação)
Roda `N` repetições (padrão `2`, ou ex.: `5` para o artigo) com o Time Azul ativo e os robôs amarelos fixos como obstáculos determinísticos:
```bash
./experiments/e1/run_e1.sh 2
```

### Opção 3 — Modo Partida Completa (`match:=True`, Azul vs. Amarelo ativos)
Sobe os dois times completos (`ROS_DOMAIN_ID=0` para Azul e `ROS_DOMAIN_ID=1` para Amarelo) disputando bola simultaneamente enquanto avalia as configurações no Time Azul:
```bash
./experiments/e1/run_e1.sh 2 --match
```

---

## 4. O que o Experimento E1 faz em cada rodada (30 segundos)

Para cada configuração (**A**, **B** e **C**) e cada repetição (`01..N`), o `run_e1.sh` sobe a stack limpa, inicia o `benchmark_logger.py` e roda o `e1_scenario.py`:

1. **`NORMAL_PLAY` / `RUN` (8 s)**:
   * Posiciona a bola perto da borda da área de defesa (`1.55 m, 0.05 m`) e os robôs de linha azuis recuados para que acelerem em velocidade máxima ($> 1.0\text{ m/s}$). Aos `5.5 s`, reposiciona o atacante em sprint rumo à bola para chegar em alta velocidade no instante exato da transição.
2. **`STOP` (6 s)**:
   * Injeta `COMMAND_STOP` com a bola próxima à trajetória do atacante para testar:
     * Limite regulamentar de velocidade em parada ($\le 0.75\text{ m/s}$).
     * Clamp radial de distância mínima da bola ($500\text{ mm}$).
   * Aos `4.5 s` de `STOP`, move a bola para forçar os robôs a estarem em movimento ativo no instante em que o `HALT` será disparado.
3. **`HALT` (4 s)**:
   * Injeta `COMMAND_HALT` e grava o timestamp exato em `run_XX_events.csv` para medir quantos milissegundos o comando `v_cmd` leva para cair a `0.0 m/s`.
4. **`BALL_PLACEMENT` (8 s)**:
   * Injeta `COMMAND_BALL_PLACEMENT_YELLOW` com `designated_position = (-1.55 m, 0.35 m)` (próximo à área de defesa azul), obrigando os robôs a evitarem o corredor de reposicionamento e a área.
5. **`NORMAL_START` sem preparação prévia (4 s)**:
   * Injeta `COMMAND_NORMAL_START` sem `PREPARE_*` anterior (contexto `RESTART_NONE` $\rightarrow$ `PHASE_RUN`).

---

## 5. Arquivos Gerados e Colunas dos CSVs

Ao final da bateria, os resultados ficam salvos em:
* `experiments/results/e1/{A,B,C}/run_XX.csv`: série temporal de todos os robôs (~60 Hz).
* `experiments/results/e1/{A,B,C}/run_XX_events.csv`: instante exato (`timestamp_ms,event_name`) de cada mudança de estado injetada.

### Colunas de `run_XX.csv`
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
| `v_meas` | Velocidade linear medida pela visão (`m/s`). |
| `viol_speed_stop` | `1` se `gc_state == STOP` e (`v_cmd > 0.75` ou `v_meas > 0.75`), senão `0`. |
| `viol_defense_area` | `1` se robô de linha invadir área de defesa (ou goleiro invadir área adversária), senão `0`. |
| `viol_ball_radius` | `1` se em `STOP`/reinício adversário e `dist(robô, bola) < 500 mm`, senão `0`. |
| `ghost_cmd` | `1` se houver comando de movimento para robô ausente da visão, senão `0`. |

---

## 6. Como usar o `benchmark_logger.py` isoladamente (Partida Manual)

Caso queira gravar um CSV durante uma partida manual (usando o Game Controller real ou outro cenário):

1. Suba a partida com um YAML de benchmark:
   ```bash
   ./run_match.sh config_file:=experiments/configs/default_benchmark.yaml
   ```
2. Em outro terminal (dentro do DevContainer), dispare o logger pela duração desejada:
   ```bash
   source /opt/ros/jazzy/setup.bash
   source install/setup.bash
   ROS_DOMAIN_ID=0 python3 experiments/benchmark_logger.py \
     --output experiments/results/manual_run.csv \
     --duration 60
   ```
