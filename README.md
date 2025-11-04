# Projeto de capacitação

## Pre-requisitos(recomendado)

To run this workspace locally, you will need the following:

- Ubuntu (qualquer versão)
- Docker
- Vscode com devConteiner
- Git

## Installing

1. Clonar repositório com a branch certa para o projeto:

    ```bash
    git clone -b add_strategy_repo --single-branch --recurse-submodules git@github.com:matheuscctb/Sele-o_ws.git

    ```

2. após abrir no vscode, clicar F1 e selecionar reopen in conteiner. Após isso, tudo que é necessário será instalado no conteiner



3. Para fazer o build do projeto utilizar o comando :

    ```bash
    ./build.sh
    ```
Serão criados os executáveis. Logo após utilizar o comando abaixo para ativar o terminal:
    ```bash
    source install/setup.bash
    ```    

4. Para rodar o ambiente, primeiro abra o gRsim e depois de compilado e ativado os terminais, execute o código abaixo:

    ```bash
    ros2 launch oxebots_bringup ssl.launch
    ```

5. Objetivo do projeto:
O objetivo principal deste projeto é o desenvolvimento e a implementação das **lógicas de estratégia** do time.

> **Atenção:** Os demais módulos (controle, simulação, visão, etc.) já estão implementados e funcionais. **Não é necessário modificar nenhum outro pacote de software fora o de estratégia.**

## 🛠️ Tarefas Principais

O trabalho está focado em duas entregas centrais:

### 1. Criação de uma Estratégia de Jogo Básica

Deve-se implementar uma lógica de jogo simples, definindo os papéis fundamentais para uma partida:

* **Goleiro:** Posicionamento e defesa da nossa meta.
* **Defensor:** Posicionamento de bloqueio e apoio ao goleiro.
* **Atacante:** Posicionamento ofensivo e lógica de chute a gol.

Para toda a movimentação dos robôs, deve-se utilizar o módulo `go_to_point`, que já está validado e operacional.

### 2. Árvore de Comportamento (Behavior Tree)

A lógica de decisão que coordena os papéis (Goleiro, Defensor, Atacante) deve ser implementada usando uma Árvore de Comportamento. O arquivo final da árvore deve ser gerado em formato `.xml`.

---

## 🔬 Ferramentas de Monitoramento e Debug

Para auxiliar no desenvolvimento e verificar se os nós estão se comunicando corretamente, recomendamos o uso das seguintes ferramentas:

* **`rqt_graph`**: Excelente para visualizar a arquitetura dos nós ROS, seus tópicos e como eles estão conectados em tempo real.
    ```bash
    rosrun rqt_graph rqt_graph
    ```

* **`Wireshark`**: Útil para uma análise de baixo nível, permitindo inspecionar os pacotes de rede que estão sendo trocados (especialmente útil para debugar a comunicação com o simulador ou o sistema de visão).

* Para obter a posição da bola e dos robôs inimigos, você pode utilizar o nó game_observer do pacote oxebots_observers. Este nó processa os dados brutos de visão e publica a posição da bola no tópico **`/game_data`**. A posição dos robôs inimigos também pode ser encontrada neste mesmo tópico. Para obter a posição (x, y) da bola, você deve ouvir o tópico **`/game_data`** e acessar o campo `ball.pos`. Para a posição dos robôs inimigos, você acessará ocampo `robots_enemies`

   