# software_ws — OxeBots SSL-EL

Workspace ROS 2 da equipe **OxeBots** (UFBA) para a categoria **RoboCup Small Size League – Entry Level (SSL-EL)**.

Este repositório reúne, através de submódulos Git, toda a pilha de software responsável pela autonomia da equipe: comunicação com a visão e o árbitro oficial, percepção e fusão de dados em campo, predição por Filtro de Kalman, máquina de decisão via Behavior Trees (BehaviorTree.CPP), planejamento de trajetórias (D* Lite) e controle de baixo nível/rádio NRF24.

---

## 1. Arquitetura e Submódulos

A estrutura dentro de `src/` é organizada em repositórios desacoplados como submódulos:

| Pacote / Submódulo | Descrição | Linguagem / Tecnologias |
| :--- | :--- | :--- |
| [`oxebots_interfaces`](src/oxebots_interfaces) | Mensagens (`.msg`), serviços (`.srv`), definições Protobuf e Bitproto. | ROS 2 IDL, Protobuf, Bitproto |
| [`oxebots_observers`](src/oxebots_observers) | Recepção de pacotes SSL-Vision e Game Controller; fusão e deduplicação de câmeras; publicação de ocupação do campo (`/map`). | C++20, ROS 2 Jazzy |
| [`oxebots_prediction`](src/oxebots_prediction) | Filtro de Kalman contínuo para rastreamento e predição da bola (atrito com carpete) e dos robôs. | C++20, Eigen3, ROS 2 Jazzy |
| [`oxebots_strategy`](src/oxebots_strategy) | Decisão em tempo real (Behavior Tree 4.x), escalonador de papéis, planejador D* Lite, gerador de setpoints e seguidor de caminho (PD). | C++20, BehaviorTree.CPP v4, ROS 2 Jazzy |
| [`oxebots_comms`](src/oxebots_comms) | Envio de comandos para simulador (grSim / SSL-RA via UDP) e para hardware real (NRF24L01 via serial e Bitproto). | C++20, Python 3, libserialport, Bitproto |
| [`oxebots_bringup`](src/oxebots_bringup) | Launch files unificados para subir visão, estratégia, controle e pontes de simulação/real. | Python Launch System, ROS 2 |
| [`oxebots_trajectory_analysis`](src/oxebots_trajectory_analysis) | Ferramentas de análise e plotagem de trajetórias reais vs. planejadas. | Python 3, Matplotlib, Tkinter |
| [`ssl_ros_bridge`](src/ssl_ros_bridge) | Ponte UDP multicast para converter pacotes oficiais SSL-Vision e Game Controller em tópicos ROS 2. | C++20, Protobuf |

---

## 2. Pré-requisitos

O software do OxeBots é padronizado em:
- **Sistema Operacional:** Ubuntu 24.04 LTS (Noble Numbat)
- **Distribuição ROS:** [ROS 2 Jazzy Jalisco](https://docs.ros.org/en/jazzy/Installation.html)
- **Compilador C++:** GCC/G++ 13+ (suporte a C++20)
- **Contêineres:** Docker + Dev Containers (Visual Studio Code ou CLI)

> [!NOTE]
> É altamente recomendado executar o workspace dentro do ambiente padronizado em **Dev Container**, onde todas as dependências do sistema e do ROS Jazzy já vêm instaladas e isoladas da máquina host.

---

## 3. Instalação e Configuração

### 3.1 Clonando o Repositório com Submódulos

```bash
git clone --recurse-submodules https://github.com/OxeBots/software_ws.git
cd software_ws
```

Caso já tenha clonado sem a flag recursiva:
```bash
git submodule update --init --recursive
```

### 3.2 Execução com Dev Container (Recomendado)

1. Abra a pasta do projeto no VS Code com a extensão **Dev Containers** instalada.
2. Pressione `F1` (ou `Ctrl+Shift+P`) e selecione **Dev Containers: Reopen in Container**.
3. O contêiner `osrf/ros:jazzy-desktop-full` será inicializado com os volumes montados em `/software_ws`.

Se sua máquina tiver GPU NVIDIA e você desejar aceleração de hardware:
Descomente as seções de `--gpus all` em `.devcontainer/devcontainer.json`.

### 3.3 Configuração de Dependências (`setup.sh` e `rosdep`)

Dentro do ambiente (ou no container):
```bash
bash setup.sh
```

Ou execute o `rosdep` para verificar dependências de sistema:
```bash
rosdep update
rosdep install --from-paths src --ignore-src -y --rosdistro jazzy
```

---

## 4. Compilação (`build.sh`)

Para compilar sem esgotar memória RAM (limitando workers e threads paralelas):
```bash
bash build.sh
```

Ou manualmente com `colcon`:
```bash
source /opt/ros/jazzy/setup.bash
MAKEFLAGS="-j2" CMAKE_BUILD_PARALLEL_LEVEL=2 colcon build --symlink-install --parallel-workers 2
```

Para carregar o ambiente após a compilação:
```bash
source install/setup.bash
```

---

## 5. Execução do Sistema

### 5.1 Execução Completa via Launch

Para iniciar a pilha com a ponte de simulação grSim:
```bash
ros2 launch oxebots_bringup ssl-new.launch.py is_yellow_team:=false invert_sides:=false
```

Parâmetros comuns de inicialização:
- `is_yellow_team`: `true` se o time for o Amarelo; `false` se for Azul.
- `invert_sides`: `true` se o time estiver defendendo o gol invertido.
- `simulator_ip`: IP da máquina onde o grSim/simulador está rodando (padrão: `127.0.0.1`).

### 5.2 Scripts de Auxílio de Partida

- `./run_match.sh`: Inicia a partida e nós principais de forma orquestrada.
- `./test_system.sh`: Executa testes automatizados do workspace.

---

## 6. Portas de Rede e Comunicação

O sistema conecta-se a softwares padrão da RoboCup SSL e dispositivos físicos:

| Protocolo | Porta Padrão | Destino / Origem | Finalidade |
| :--- | :--- | :--- | :--- |
| UDP Multicast | `10006` (`224.5.23.2`) | SSL-Vision | Recepção de pacotes de rastreamento das câmeras de campo. |
| UDP Multicast | `10003` (`224.5.23.1`) | Game Controller | Recepção de comandos do árbitro oficial da partida. |
| UDP Unicast | `10301` / `10302` | grSim / SSL-RA | Envio de comandos de velocidade e chute (Azul: 10301, Amarelo: 10302). |
| Serial USB | `/dev/ttyUSB0` (ou `/dev/ttyACM0`) | Base NRF24 | Transmissão de rádio com pacotes compactos Bitproto para robôs físicos. |

---

## 7. Testes e Validação

Para rodar os testes unitários do workspace:
```bash
colcon test --parallel-workers 2
colcon test-result --all
```

---

## 8. Licença

Este projeto é desenvolvido para competições acadêmicas e open-source sob a licença **GPLv3**. Consulte os arquivos de licença em cada submódulo para mais detalhes.
