<!-- parte: Parte I — A partida e o ecossistema | Antes de falar de árvores de comportamento, é preciso entender o jogo que o software precisa jogar e a pilha de programas que transforma imagens de câmera em movimento de robô. -->
# Introdução

## O que este manual é

Este manual descreve, de ponta a ponta, o software de estratégia do time **OxeBots** para a categoria **RoboCup Small Size League – Entry Level (SSL-EL)**: como um robô decide o que fazer, como essa decisão vira movimento e como a equipe pode evoluir esse software até uma versão capaz de disputar uma partida inteira, respeitando o regulamento do início ao fim.

Ele foi escrito para ser lido de duas maneiras. Quem está chegando agora na equipe pode lê-lo do começo ao fim e sair com uma imagem completa do sistema — do campo de futebol à última linha de C++ que manda um comando de velocidade ao robô. Quem já conhece o projeto pode usá-lo como referência: cada capítulo é razoavelmente autocontido e as tabelas dos capítulos e apêndices foram feitas para consulta rápida.

O foco está em **Behavior Trees** (árvores de comportamento), a técnica que o projeto usa para representar decisões. O manual não pressupõe que você já as conheça: o Capítulo 4 constrói o assunto do zero, com exemplos desenhados passo a passo.

## O desafio: jogar uma partida inteira sozinho

Uma partida de SSL-EL é disputada por robôs **totalmente autônomos**: durante o jogo, nenhum humano da equipe pode digitar informação no sistema, exceto em intervalos e pedidos de tempo. O único elo entre o software e o mundo externo são dois fluxos de dados compartilhados por todas as equipes:

- as **imagens das câmeras** (SSL-Vision), que dizem onde estão a bola e todos os robôs, e
- os **comandos do árbitro** (Game Controller), que dizem em que estado o jogo está: parado, em andamento, aguardando um pênalti, em pedido de tempo e assim por diante.

A partir desses dois fluxos, cada robô precisa, várias dezenas de vezes por segundo, responder à pergunta *"o que eu devo fazer agora?"*. E a resposta depende de muita coisa ao mesmo tempo: qual é o comando do árbitro, qual é o meu papel (goleiro, atacante, defensor), onde está a bola, onde estão os outros robôs, o que o regulamento permite naquele instante.

Há uma assimetria importante aqui: errar uma jogada é aceitável, mas **violar uma regra de segurança não é**. Se o árbitro manda parar tudo (HALT), os robôs precisam parar — não importa o quão perto da bola ou do gol estejam. Boa parte da arquitetura descrita neste manual existe para que esse tipo de interrupção seja *garantida*, e não apenas provável.

## As camadas do software

O software do OxeBots é organizado em camadas, cada uma com uma responsabilidade bem definida, como mostra a {{fig:visao_geral_camadas}}.

![As camadas do software, da percepção à atuação](figuras/visao_geral_camadas.png)

1. **Percepção**: as câmeras compartilhadas e o Game Controller entregam dados brutos pela rede.
2. **Interpretação**: um observador converte esses dados para as unidades e referenciais internos (milímetros, radianos), e filtros de Kalman estimam posição, velocidade e aceleração da bola e dos robôs.
3. **Decisão**: um atribuidor de papéis escolhe quem é o atacante e quem é o defensor, e a Behavior Tree de cada robô decide a ação do momento.
4. **Planejamento**: o planejador D\* Lite calcula uma rota livre de colisões até o alvo escolhido pela árvore.
5. **Controle**: um controlador transforma a rota em velocidades de roda e é o único responsável por enviar comandos ao robô, incluindo o chute e a parada de emergência.
6. **Atuação**: um driver entrega o comando ao simulador (grSim ou ER-Force Ra) ou ao rádio dos robôs reais.

Este manual percorre essas camadas de baixo para cima ao descrever o sistema atual (Parte III) e de cima para baixo ao propor a arquitetura de jogo completo (Parte IV). A fronteira mais importante para a estratégia é entre a **decisão** e o **planejamento/controle**: a árvore diz *aonde* ir e *o que* fazer (ir a um ponto, chutar, parar); os módulos abaixo cuidam de *como* fazê-lo.

## Como o manual está organizado

O conteúdo está dividido em cinco partes, ilustradas na {{fig:mapa_do_manual}}.

![Mapa do manual: as cinco partes e os capítulos de cada uma](figuras/mapa_do_manual.png)

- **Parte I — A partida e o ecossistema** (Capítulos 1 a 3). O jogo, as regras que afetam o software e a visão geral dos programas.
- **Parte II — Behavior Trees** (Capítulos 4 e 5). A teoria necessária e como a biblioteca BehaviorTree.CPP a implementa.
- **Parte III — O sistema atual** (Capítulos 6 a 13). Como cada peça funciona hoje: o nó de estratégia, o movimento, a percepção, o ataque, a defesa, os papéis e a árvore mestre — e uma lista honesta de pontos de atenção que precisam ser resolvidos antes de uma partida completa.
- **Parte IV — A Master Tree de jogo completo** (Capítulos 14 a 21). A arquitetura proposta: um estado de jogo único e confiável, uma árvore mestre com prioridades claras, uma subárvore para cada situação regulamentar, papéis dinâmicos e os contratos de dados entre as peças.
- **Parte V — Implementação** (Capítulos 22 a 24). Um tutorial para criar uma nova folha de árvore, a estratégia de testes e o plano de trabalho de quatro semanas.

Os apêndices reúnem o glossário, a referência de mensagens e tópicos ROS 2, o mapeamento das regras do regulamento para a arquitetura, os arquivos XML propostos e a referência de parâmetros e comandos de execução.

## Convenções usadas

Ao longo do texto, algumas convenções ajudam a distinguir o que **existe hoje** do que **está proposto**:

- Trechos em `fonte monoespaçada` são nomes de arquivos, nós, tópicos, parâmetros ou código.
- Nas figuras de árvores, nós com borda laranja e o símbolo **✦** são nós **novos**, a serem criados. Os demais já existem no repositório.
- Caixas coloridas destacam informações de natureza diferente: azul para observações, verde para dicas, laranja para pontos de atenção, vermelho para riscos de segurança e roxo para exemplos.
- Unidades: posições em **milímetros**, ângulos em **radianos** e velocidades em **metros por segundo**, salvo indicação em contrário. As mensagens de ROS 2 que carregam uma pose para o planejador usam metros; a conversão é feita em um ponto único e documentado (Capítulo 7).

!!! note "Versões de referência"
    O software roda sobre **ROS 2 Jazzy** (Ubuntu 24.04, no *devcontainer* do projeto) e usa a biblioteca **BehaviorTree.CPP 4.10**. Parte da semântica detalhada dos nós de controle foi conferida no código-fonte da série 4.6; sempre que um comportamento for crítico para a segurança, o plano de testes (Capítulo 23) inclui um teste que o confirma na versão instalada.

!!! tip "Quem compila o quê"
    Por regra do time, a compilação do workspace (`./build.sh`, que chama `colcon build`) é feita por quem desenvolve, dentro do devcontainer. Os exemplos de código deste manual são escritos para serem colados no repositório; compile e teste antes de usar.

## Termos que merecem atenção desde já

Algumas palavras do regulamento parecem sinônimas, mas não são, e confundi-las é a origem de muitos erros de estratégia:

- **Comando do árbitro**: a ordem que o Game Controller emite (HALT, STOP, NORMAL_START…).
- **Estágio da partida**: o momento do jogo no tempo (primeiro tempo, intervalo, prorrogação…).
- **Evento**: uma ocorrência registrada pelo árbitro automático, como uma falta.
- **Autorização de movimento**: se o robô pode se mover. O HALT proíbe; o STOP permite, com limite de velocidade.
- **Autorização de tocar na bola**: só existe depois que a partida é retomada por NORMAL_START, por um chute livre ou por FORCE_START.

O glossário completo está no Apêndice A.
