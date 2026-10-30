<!-- parte: Apêndices — Material de referência | Glossário, catálogo de nós e mensagens, o mapeamento das regras do regulamento para a arquitetura, os XMLs propostos e a referência de parâmetros e comandos. -->
<!-- apendice -->
# Glossário

**Ação assíncrona (stateful).** Folha de árvore que pode devolver RUNNING e continuar nos ticks seguintes; implementa `onStart`, `onRunning` e `onHalted`.

**Ação síncrona.** Folha que termina no mesmo tick em que é executada.

**Árbitro automático (autoref).** Programa que detecta infrações e as reporta ao Game Controller.

**Atacante.** Papel do robô que disputa e conduz a bola em jogo corrido.

**Ball placement.** Posicionamento da bola, depois de uma parada, na posição designada, feito pelos robôs de uma das equipes.

**Behavior Tree (BT).** Árvore de comportamento: estrutura hierárquica que representa decisões por prioridade, executada por ticks.

**Blackboard.** Dicionário compartilhado entre os nós de uma árvore; a memória da BT.

**Carga (ponto de).** Ponto 120 mm além do centro da bola, do lado do gol, usado como alvo ao conduzi-la.

**Captura (ponto de).** Ponto 115 mm atrás da bola, na reta bola–gol, onde o atacante encosta alinhado.

**Cobrador (kicker).** Robô que bate um reinício.

**Comando do árbitro.** Ordem emitida pelo Game Controller (HALT, STOP, NORMAL_START…).

**Condição.** Folha que consulta o mundo e devolve SUCCESS ou FAILURE, sem efeito.

**Controlador (movement_calculation_node).** Nó que transforma a rota em velocidades e é o único escritor de `/robot_commands`.

**D\* Lite.** Algoritmo de planejamento de caminhos incremental, usado para rotas livres de colisão.

**Decorador.** Nó de controle com um único filho que modifica seu comportamento ou resultado.

**Defensor.** Papel do robô de linha que cobre o gol sem disputar a bola.

**Estágio.** Etapa da partida (primeiro tempo, intervalo, prorrogação…); distinto do comando.

**Evento.** Ocorrência registrada pelo árbitro automático, como uma falta.

**Fábrica (BehaviorTreeFactory).** Objeto que registra os tipos de nó e cria árvores a partir de XML.

**Fase (phase).** Estado de jogo derivado pelo `referee_state_node`, correspondente aos estados da máquina de estados do regulamento.

**Fallback.** Nó de controle que tenta os filhos em ordem até um ter sucesso.

**Free kick.** Reinício com chute livre; faltas, laterais, escanteios e tiros de meta chegam como `DIRECT_FREE`.

**Game Controller (GC).** Software que traduz as decisões do árbitro em mensagens de rede.

**Goleiro.** Robô que pode entrar na própria área de defesa.

**Groot2.** Ferramenta visual para observar a árvore em execução.

**Guarda.** Condição que habilita um ramo; nesta arquitetura, sempre o primeiro filho de uma `ReactiveSequence`.

**Halt (nó).** Ação que pede ao controlador a parada do robô. **`halt()`** (método): interrupção de um nó em andamento pelo seu pai.

**Histerese.** Mecanismo que evita oscilação de uma decisão usando limiares diferentes para entrar e para sair de um estado.

**Kick-off.** Reinício no centro do campo, no início dos tempos e depois de um gol.

**Lookahead.** Distância (100 mm) do ponto da rota que o controlador persegue.

**Mestre (Master Tree).** Árvore principal, que seleciona o comportamento conforme a fase do jogo.

**NORMAL_START.** Comando que autoriza o kick-off ou o pênalti preparados.

**Override.** Pedido de modo físico (parar, chutar, alinhar) enviado ao controlador por `/robot_motion_override`.

**Papel.** Função de um robô: goleiro, atacante, defensor, cobrador.

**Parallel.** Nó de controle que executa todos os filhos a cada tick.

**Porta.** Parâmetro de entrada ou saída de uma folha, passado como atributo XML.

**Preempção.** Interrupção de um ramo em andamento por um de maior prioridade.

**Pure pursuit.** Método de seguimento de rota que persegue um ponto à frente na rota.

**ReactiveFallback / ReactiveSequence.** Variantes que reavaliam os filhos desde o primeiro a cada tick.

**Reinício.** Retomada do jogo depois de uma parada (kick-off, pênalti, free kick, force start).

**RUNNING / SUCCESS / FAILURE.** Os três resultados possíveis de um nó a cada tick.

**SafetyGate.** Estágio do controlador que aplica limites de segurança independentes da árvore.

**Sequence.** Nó de controle que executa os filhos em ordem, parando no primeiro que falha.

**STOP.** Comando que exige velocidade < 0,75 m/s e distância ≥ 0,5 m da bola.

**SubTree.** Referência a outra árvore pelo nome, para reuso.

**Tick.** Pulso de decisão que percorre a árvore; 60 por segundo no projeto.

**Transient local.** QoS do ROS 2 em que o publicador guarda o último valor para quem entra depois.

**Watchdog.** Vigilância que zera os comandos se nenhum dado novo chega em um prazo.
