# Papéis dinâmicos

Com três robôs, o time precisa decidir **quem faz o quê**: um é goleiro, e dos outros dois um ataca e o outro defende. Essa divisão não é fixa: quem está mais perto da bola, e bem posicionado para ela, deveria atacar, e isso muda o tempo todo. O sistema resolve isso com um componente separado das árvores, o `role_assigner_node`. Este capítulo explica como ele decide, como evita trocas desnecessárias e como a árvore consome o resultado.

## Por que um componente fora da árvore

Poderia-se pensar em decidir o papel dentro de cada árvore, olhando a distância à bola. Mas haveria um problema: cada robô tem a **sua** árvore e a sua visão do mundo; sem coordenação, dois robôs poderiam concluir ao mesmo tempo que "eu sou o atacante" — ou nenhum. A decisão de papel é **coletiva**: precisa de uma comparação entre todos os robôs. Por isso ela é tomada em **um único processo**, que olha o time inteiro e publica o resultado.

## O custo de cada robô

O `role_assigner_node` assina `/game_data` e, a cada mensagem, calcula um **custo** para cada robô de linha (o goleiro, identificado por `goalkeeper_id`, não participa). Quanto **menor** o custo, mais apto o robô é a atacar:

> **custo = w1 · r + w2 · (1 − cos θ)**

- `r` é a distância do robô à bola, em **metros**.
- `θ` é o ângulo entre a **direção em que o robô está indo** (ou, se está quase parado, para onde está virado) e a direção da bola. Um robô que já se move em direção à bola tem `cos θ ≈ 1` e custo de alinhamento nulo.
- `w1 = 2,0` e `w2 = 1,0` são os pesos padrão: a distância pesa o dobro do alinhamento.

A velocidade do robô é estimada por diferença finita entre duas mensagens consecutivas; se o módulo for menor que 50 mm/s, usa-se a orientação do chassi.

![O custo de papel: mais perto e mais alinhado significa mais barato](figuras/custo_papel.png)

A figura mostra o mapa de custo para uma bola em (500, 300): os círculos concêntricos são curvas de igual custo de distância, e os dois robôs recebem custos diferentes pela combinação de distância e alinhamento. O de menor custo é nomeado atacante; o outro, defensor. Com um único robô de linha, ele é o atacante e o papel de defensor é atribuído ao próprio identificador do goleiro (um "fallback" sem efeito real).

## Evitando a troca-troca: duas histereses

Se a escolha fosse simplesmente "o menor custo agora", o papel oscilaria sempre que dois robôs tivessem custos parecidos: cada oscilação interrompe e recomeça a árvore do robô, e o time perderia tempo e ficaria imprevisível. O atribuidor usa duas proteções:

1. **Histerese de custo (2,5).** O atacante atual recebe um **desconto de 2,5** no custo. Um concorrente só o "rouba" se, mesmo com esse desconto, tiver custo menor — isto é, se for *nitidamente* melhor.
2. **Histerese de tempo (2,0 s).** Mesmo que o concorrente seja nitidamente melhor, a troca só acontece se já passaram pelo menos **2 segundos** da última troca. Durante esse intervalo, o papel anterior é mantido.

![Evolução dos custos de dois robôs: a troca de atacante só acontece quando o concorrente supera o desconto e o tempo mínimo passou](figuras/histerese_papeis.png)

A {{fig:histerese_papeis}} ilustra o efeito com uma simulação da mesma regra: o robô 2 começa com custo maior e vai melhorando; a linha pontilhada mostra o custo efetivo do atacante atual (descontados 2,5). O robô 2 só assume quando sua curva cruza a pontilhada **e** o cooldown de 2 s permite. Os parâmetros (`w1`, `w2`, `hysteresis`, `time_hysteresis`) podem ser ajustados no YAML.

## Como a árvore consome os papéis

O atribuidor publica `RoleAssignment { attacker_id, defender_id }` em `/role_assignment`. No `strategy_node`, a *callback* `role_callback` copia os dois valores para as chaves `attacker_id` e `defender_id` da blackboard. As árvores então os usam por meio da condição `IsMyRole`, que compara o `robot_id` do processo com o identificador do papel pedido (`attacker` ou `defender`). Como `IsMyRole` está como guarda em `ReactiveSequence`, **quando o papel muda, o ramo antigo é interrompido no tick seguinte** e o novo é iniciado — e a ação interrompida recebe `halt`.

O goleiro, por sua vez, **não** vem do atribuidor: as árvores o identificam por `IsRobotId robot_id="0"` (o identificador 0 é fixo no código), em paralelo ao parâmetro `goalkeeper_id` do atribuidor, que só serve para excluí-lo do sorteio.

## O que o atribuidor atual não faz

O mecanismo atual cumpre bem o papel de escolher o atacante em jogo corrido, mas não foi pensado para uma partida completa. As lacunas, que a Parte IV preenche, são:

- **Não conhece o estado de jogo.** Em um kick-off ou pênalti, quem bate deveria ser escolhido por critério próprio e **mantido** durante o reinício; hoje a escolha continua sendo a do custo à bola, que pode mudar no meio da preparação.
- **O goleiro é fixo.** O regulamento permite escolher qualquer identificador (e até ficar sem goleiro) e o Game Controller informa o goleiro de cada time.
- **Não considera o número de robôs ativos.** Cartões e robôs removidos mudam quantos robôs podem jogar, mas o atribuidor só enxerga quem aparece na visão (e, como visto no Capítulo 8, um robô que some da visão continua "presente").
- **Não há exclusividade formal.** A garantia de que dois robôs não ocupam o mesmo papel depende apenas de o atribuidor publicar uma mensagem coerente; as árvores não verificam a "idade" do papel.
- **Valores iniciais fixos.** Até a primeira mensagem do atribuidor, o `strategy_node` assume `attacker_id = 2` e `defender_id = 1`.
