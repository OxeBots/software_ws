<!-- parte: Parte II — Behavior Trees | A teoria necessária para ler, escrever e depurar as árvores do projeto, e a forma como a biblioteca BehaviorTree.CPP a coloca em prática. -->
# Behavior Trees do zero

Este capítulo ensina Behavior Trees (BTs) a partir do princípio, sem supor nenhum conhecimento prévio. Todos os conceitos são ilustrados com exemplos desenhados e, sempre que possível, ligados ao futebol de robôs. No capítulo seguinte veremos como a biblioteca que usamos, a BehaviorTree.CPP, implementa essas ideias.

## Por que usar uma árvore de comportamento

Um robô de futebol precisa tomar decisões que dependem do contexto e que podem ser interrompidas a qualquer momento. Imagine o atacante perseguindo a bola quando o árbitro apita um HALT: ele precisa largar o que estava fazendo *imediatamente*, sem terminar a jogada, e voltar à ação normal quando o jogo recomeçar.

Uma abordagem clássica para esse tipo de problema é a **máquina de estados finitos** (FSM): um conjunto de estados ("indo à bola", "chutando", "parado") e de transições entre eles. As FSMs funcionam bem enquanto pequenas, mas a quantidade de transições cresce depressa: se *qualquer* estado precisa poder ir para "parado" quando chega um HALT, cada novo estado exige mais uma transição. Reutilizar um pedaço (por exemplo, "ir até um ponto") em vários contextos também é difícil, porque as transições ficam entrelaçadas com os estados.

As Behavior Trees resolvem esses dois problemas. Elas organizam o comportamento como uma **hierarquia**: comportamentos complexos são compostos de comportamentos mais simples, e a *prioridade* entre eles é dada pela posição na árvore. Os benefícios principais são:

- **Modularidade**: cada subárvore é um bloco que pode ser testado e reutilizado isoladamente.
- **Reatividade**: a árvore é reavaliada continuamente, de modo que uma condição de alta prioridade (HALT) pode interromper um comportamento em andamento.
- **Legibilidade**: o desenho da árvore é, ao mesmo tempo, a documentação do comportamento.
- **Desenvolvimento em paralelo**: duas pessoas podem trabalhar em subárvores diferentes sem se atrapalhar.

## A anatomia de uma árvore

Uma BT é uma árvore no sentido da computação: tem uma **raiz**, **nós internos** e **folhas**. A {{fig:bt_anatomia}} mostra um exemplo pequeno, que lê "se o árbitro mandou parar, pare; senão, jogue (vá à bola e chute)".

![Uma árvore de exemplo, com a legenda de símbolos usada em todo o manual](figuras/bt_anatomia.png)

Os nós se dividem em quatro famílias:

- **Folhas de condição** (elipses verdes): fazem uma pergunta ao mundo e respondem sim ou não. Não alteram nada. Exemplo: "a bola está perto?".
- **Folhas de ação** (retângulos de cantos arredondados): *fazem* alguma coisa: mover o robô, chutar, parar.
- **Nós de controle** (retângulos azuis ou laranjas): têm vários filhos e decidem **qual filho executar e em que ordem**. Os mais importantes são `Sequence` (→) e `Fallback` (?).
- **Decoradores** (hexágonos): têm um único filho e modificam o seu comportamento ou o seu resultado (por exemplo, invertendo-o ou repetindo-o).

Há ainda as **subárvores** (retângulos tracejados), que apenas referenciam outra árvore pelo nome, permitindo reuso.

Nas figuras deste manual, os números pequenos nas arestas indicam a **ordem** dos filhos: o filho 1 tem prioridade sobre o 2, e assim por diante. Esta é uma regra de ouro: *em uma BT, a ordem dos irmãos é a prioridade*.

## O tick e os três resultados

A árvore não "roda sozinha". Ela é executada por **ticks**: a cada tick, a raiz recebe um pulso, que ela propaga aos seus filhos segundo suas regras. Cada nó, ao ser "ticado", faz o seu trabalho e devolve um de três resultados:

| Resultado | Significado |
|---|---|
| **SUCCESS** | A tarefa foi concluída com êxito (ou a condição é verdadeira). |
| **FAILURE** | A tarefa não pôde ser concluída (ou a condição é falsa). |
| **RUNNING** | A tarefa ainda está em andamento; precisa de mais ticks. |

O terceiro resultado é o que permite comportamentos que duram no tempo. "Ir até um ponto" não termina em um tick: ela devolve RUNNING a cada tick enquanto o robô se desloca e só devolve SUCCESS quando ele chega. No nosso sistema, a árvore recebe um tick **60 vezes por segundo**.

!!! note "Ticks e tempo"
    Um tick não é uma unidade de tempo, e sim um *pulso de decisão*. Entre dois ticks, nada acontece na árvore; apenas os dados do mundo (mensagens ROS 2) são atualizados em outra linha de execução. A latência de reação a um evento é, portanto, de no máximo um período de tick (cerca de 17 ms a 60 Hz) mais o tempo de processamento do próprio tick.

## Sequence: "faça isto, depois isto, depois isto"

O nó `Sequence` executa os filhos **em ordem**, um de cada vez. Se um filho devolve FAILURE, a sequência inteira falha imediatamente. Se devolve RUNNING, a sequência devolve RUNNING e **retoma exatamente naquele filho** no próximo tick. Só quando todos os filhos devolvem SUCCESS a sequência devolve SUCCESS.

Pense na sequência como um "E" lógico com passos: *A e depois B e depois C*. É a escolha natural para roteiros que precisam ser completados em ordem — por exemplo, "ir ao ponto de pré-chute → alinhar → chutar".

A {{fig:bt_sequence}} mostra a execução em dois ticks. No tick 1, A tem sucesso e B fica em andamento; C ainda não é executado. No tick 2, a sequência **não repete A**: ela retoma em B (que agora conclui) e passa para C.

![Sequence: no segundo tick o nó retoma de onde parou, sem reavaliar o primeiro filho](figuras/bt_sequence.png)

Repare no detalhe da figura: "não executado" para A no tick 2. Essa **memória** da sequência é útil (não se reinicia o que já foi feito), mas tem um preço, que veremos adiante: uma condição colocada como primeiro filho **não é reavaliada** enquanto um filho posterior está em andamento.

## Fallback: "tente isto; se não der, tente aquilo"

O `Fallback` (também chamado *Selector*) é o oposto da sequência: tenta os filhos **em ordem** até um ter sucesso. Se um filho devolve SUCCESS, o fallback devolve SUCCESS imediatamente e não olha os demais. Se devolve FAILURE, passa ao próximo. Se todos falham, falha. Se um devolve RUNNING, devolve RUNNING e retoma nele.

É um "OU" lógico com ordem de preferência: *A, senão B, senão C*. Serve para **escolher entre alternativas por prioridade**: "se a bola está perto, chute; senão, aproxime-se; senão, fique parado". Na prática, é o nó que implementa os "ramos" de uma árvore mestre: cada filho é um cenário, e o primeiro cuja condição vale é o escolhido.

![Fallback: tenta os filhos em ordem até um conseguir](figuras/bt_fallback.png)

## O problema da reatividade e os nós reativos

Agora a pergunta decisiva para o futebol de robôs. Considere um `Fallback` cujo primeiro filho é "o árbitro mandou HALT? → pare" e cujo segundo filho é "jogar". O jogo normal é uma ação longa (RUNNING). O que acontece quando o HALT chega no meio do jogo?

Com o `Fallback` comum, **nada**: ele memorizou que o filho 2 está em andamento e, no próximo tick, retoma direto nele, sem nunca olhar de novo para o filho 1. O robô ignora o HALT. Esse é exatamente o tipo de erro que as variantes **reativas** existem para evitar.

!!! danger "Sequence e Fallback comuns têm memória"
    Em um `Sequence` ou `Fallback` comum, os filhos anteriores ao que está em andamento **não são reavaliados**. Usar um deles como raiz da árvore de jogo significa que HALT e STOP podem passar despercebidos durante ações longas.

### ReactiveFallback

O `ReactiveFallback` **recomeça do primeiro filho a cada tick**. Se um filho de maior prioridade passa a ter sucesso (ou a estar em andamento), os filhos de menor prioridade que estavam em execução são **interrompidos** (recebem `halt`). Por isso ele é o nó escolhido para a raiz das nossas árvores mestres: a cada tick, a árvore reavalia as prioridades de cima para baixo.

![ReactiveFallback: o filho A passa a ter sucesso e B é interrompido](figuras/bt_reactive_fallback.png)

### ReactiveSequence

O `ReactiveSequence` também **recomeça do primeiro filho a cada tick**. Ele é a versão da sequência para *guardas*: um primeiro filho que é uma condição ("sou o atacante?") é reavaliado a cada tick; se deixar de valer, a sequência falha e os filhos seguintes são interrompidos. A {{fig:bt_reactive_sequence}} mostra a diferença em relação ao `Sequence` da figura anterior: no tick 2, A é reavaliado, falha, e B é interrompido.

![ReactiveSequence: a condição A é reavaliada a cada tick](figuras/bt_reactive_sequence.png)

O preço da reatividade é que **os filhos anteriores ao que está em andamento devem ser rápidos e sem efeito colateral** — eles são executados de novo todo tick. Por isso, nos nós reativos usamos como "guardas" apenas condições e ações síncronas e baratas. A biblioteca também espera que, em um `ReactiveSequence`, só um filho seja assíncrono (de longa duração).

## Parallel: fazer várias coisas ao mesmo tempo

O `Parallel` ticka **todos** os filhos a cada tick, sem esperar um terminar para começar o outro. Dois parâmetros definem quando ele termina: `success_count` (quantos filhos precisam ter sucesso para o `Parallel` ter sucesso) e `failure_count` (quantas falhas bastam para ele falhar). Ao decidir, ele interrompe os filhos que ainda estavam em andamento.

![Parallel com success_count=1: quando B conclui, A é interrompido](figuras/bt_parallel.png)

O `Parallel` serve para ações genuinamente independentes (por exemplo, "mover" e "vigiar a bola"). Cuidado: filhos que já concluíram **não são reexecutados** enquanto o `Parallel` está ativo, de modo que uma condição que passou fica "congelada" como verdadeira. Em muitas das árvores do projeto, o padrão `Parallel(success=1, failure=1)` é usado para "persiga a bola e, assim que estiver perto, chute".

## Decoradores

Os decoradores modificam o comportamento de um único filho. Os mais usados ({{fig:bt_decoradores}}):

- **`Inverter`**: troca SUCCESS por FAILURE e vice-versa (RUNNING passa). Serve para negar condições: `Inverter(IsBallInOurHalf)` significa "a bola *não* está na nossa metade". Note que **não** é o mesmo que "reativo" nem que "reverso".
- **`RetryUntilSuccessful(n)`**: se o filho falha, tenta de novo, até `n` vezes (`-1` = sem limite). Usado como "espere até que a condição seja verdadeira".
- **`Repeat(n)`**: se o filho tem sucesso, repete, `n` vezes (`-1` = sem limite).
- **`Timeout(ms)`**: se o filho não terminar no prazo, interrompe-o e devolve FAILURE.
- **`Delay(ms)`**: espera um tempo antes de executar o filho (usado como "cooldown").
- **`ForceSuccess` / `ForceFailure`**: forçam o resultado, escondendo o do filho. Úteis, mas perigosos: escondem falhas.

![Os decoradores mais usados e um exemplo de cada](figuras/bt_decoradores.png)

## Preempção: a razão de ser de tudo isso

Juntando as peças, podemos agora acompanhar o cenário que motivou o capítulo: o atacante em jogo e o HALT que chega. A árvore tem um `ReactiveFallback` na raiz, com o ramo de HALT em primeiro lugar e o do atacante depois, como na {{fig:bt_preempcao_halt}}.

![Preempção: o ramo de HALT passa a ter sucesso e o movimento em andamento é interrompido](figuras/bt_preempcao_halt.png)

- No **tick N**, a condição "o comando é HALT?" falha; o fallback passa ao ramo do atacante, que está em andamento (`GoToPoint` devolve RUNNING).
- No **tick N+1**, o comando virou HALT. O `ReactiveFallback` recomeça do primeiro filho: a condição agora vale, a subárvore de parada tem sucesso e o fallback devolve SUCCESS. Os filhos de prioridade menor, que estavam em andamento, recebem `halt()` — a folha `GoToPoint` é avisada de que foi interrompida e pode fazer sua limpeza.

Essa interrupção é a **preempção**. Ela acontece em no máximo um tick e não depende de a ação interrompida "colaborar": é a estrutura da árvore que a garante.

!!! tip "Regra prática para escolher o nó"
    - Precisa que uma condição seja **reavaliada a cada tick**? Use `ReactiveSequence`.
    - Precisa escolher entre alternativas **com preempção por prioridade**? Use `ReactiveFallback`.
    - Roteiro de passos que **deve ser completado em ordem, sem reavaliar**? Use `Sequence`.
    - Ações independentes simultâneas? Use `Parallel`.

## Ações síncronas e assíncronas

Uma última distinção, essencial para escrever folhas corretas:

- Uma ação **síncrona** faz seu trabalho e devolve SUCCESS ou FAILURE no mesmo tick. Condições são sempre síncronas.
- Uma ação **assíncrona** (ou *stateful*) pode devolver RUNNING e continuar nos ticks seguintes. Ela precisa saber o que fazer se for **interrompida** (`halt`), para não deixar o robô em um estado indevido.

A regra de ouro: **nunca bloqueie dentro de um tick**. Esperar uma resposta de rede, dormir ou fazer um cálculo demorado dentro de uma folha congela a árvore inteira e, com ela, a capacidade de reagir a um HALT. Quando algo demora, a folha deve devolver RUNNING e voltar no tick seguinte.

## Um exemplo completo, em prosa

Para fixar, leia a árvore da {{fig:bt_anatomia}} como se fosse um programa:

1. O `ReactiveFallback` raiz tenta o filho 1: um `ReactiveSequence` que verifica "o comando é HALT?".
2. Se for, executa "parar o robô" e a raiz devolve SUCCESS — fim do tick.
3. Se não for, o filho 1 falha e o fallback tenta o filho 2: uma `Sequence` chamada "Jogar".
4. A sequência verifica "a bola está perto?". Se não, falha, e a raiz falha (nenhuma alternativa serviu).
5. Se estiver perto, ela executa "ir até a bola" (RUNNING por vários ticks) e, ao chegar, "chutar".
6. A cada novo tick, a raiz volta ao passo 1: se o HALT chegar a qualquer momento, o passo 2 assume e a sequência "Jogar" é interrompida.

Esse é todo o modelo mental necessário. No próximo capítulo vemos como ele é escrito em XML e implementado em C++.
