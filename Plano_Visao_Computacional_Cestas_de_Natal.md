# Projeto Cesta de Natal — Visão Computacional

## 1. Objetivo

Desenvolver um protótipo de visão computacional para apoiar a operação de recebimento, movimentação, fracionamento e entrega das Cestas de Natal.

O projeto parte de um processo operacional real: na operação de 2025, aproximadamente **16.000 cestas** foram movimentadas, com referência operacional de **40 cestas por palete**, resultando em uma estimativa de aproximadamente:

**16.000 ÷ 40 = 400 paletes**

A proposta é transformar parte das conferências atualmente manuais em registros automatizados por câmeras, mantendo o operador no controle e utilizando a visão computacional como mecanismo de contagem, conferência e rastreabilidade.

O objetivo inicial não é substituir a equipe, mas criar uma segunda camada de conferência capaz de responder:

- Quantos paletes entraram?
- Quantas cestas chegaram?
- Quantas cestas foram retiradas dos paletes?
- Quantas cestas foram entregues?
- Existem divergências entre entrada, processamento e saída?
- Onde ocorreu uma divergência?
- Qual foi o volume processado em determinado período?

---

## 2. Conceito geral

A primeira versão será estruturada em **três pontos de visão**, cada um associado a uma etapa operacional.

```text
                 OPERAÇÃO CESTA DE NATAL

       ENTRADA              PROCESSAMENTO             SAÍDA
          │                       │                     │
          ▼                       ▼                     ▼
   ┌─────────────┐         ┌─────────────┐       ┌─────────────┐
   │   CÂMERA 1  │         │   CÂMERA 2  │       │   CÂMERA 3  │
   │             │         │             │       │             │
   │ Descarga /  │         │ Bancada /   │       │ Expedição / │
   │ entrada     │         │ retirada    │       │ entrega     │
   │ dos paletes │         │ das cestas  │       │             │
   └──────┬──────┘         └──────┬──────┘       └──────┬──────┘
          │                       │                     │
          └───────────────────────┼─────────────────────┘
                                  ▼
                         ┌─────────────────┐
                         │ MOTOR DE VISÃO  │
                         │ COMPUTACIONAL   │
                         └────────┬────────┘
                                  ▼
                         ┌─────────────────┐
                         │ CONTAGEM /      │
                         │ CONFERÊNCIA /   │
                         │ RASTREABILIDADE │
                         └────────┬────────┘
                                  ▼
                         ┌─────────────────┐
                         │ PAINEL / BANCO  │
                         │ DE DADOS        │
                         └─────────────────┘
```

---

# 3. Câmera 1 — Descarga e entrada dos paletes

## Objetivo

Registrar automaticamente a entrada dos paletes de Cestas de Natal no local de operação.

A câmera deverá observar uma área previamente delimitada de entrada e identificar:

- chegada de um palete;
- passagem do palete pela área de captura;
- quantidade aparente de cestas;
- identificação do palete, quando houver etiqueta ou QR Code;
- horário da entrada;
- eventuais divergências visuais.

### Primeiro MVP

A primeira versão não precisa resolver imediatamente a medição tridimensional.

O objetivo inicial é:

```text
PALLET DETECTADO
       ↓
CONTAGEM / ESTIMATIVA DE CESTAS
       ↓
REGISTRO DA ENTRADA
       ↓
EVENTO NO SISTEMA
```

Como a referência operacional é de 40 cestas por palete, o sistema poderá sinalizar automaticamente:

```text
Esperado: 40
Detectado: 40
Status: OK
```

ou:

```text
Esperado: 40
Detectado: 37
Status: DIVERGÊNCIA
```

A divergência não precisa significar automaticamente erro. Ela deverá gerar uma ocorrência para conferência humana.

---

# 4. Câmera 2 — Bancada de retirada e entrega aos funcionários

## Objetivo

Monitorar o ponto em que as cestas são retiradas dos paletes e disponibilizadas aos funcionários responsáveis pela distribuição.

Esta câmera é particularmente importante porque representa o **ponto de transformação do estoque**:

```text
PALLETE INTEIRO
       ↓
CESTAS INDIVIDUAIS
       ↓
ENTREGA AOS FUNCIONÁRIOS
```

O sistema deverá tentar detectar e contabilizar cada cesta que cruza uma região virtual definida na bancada.

Exemplo:

```text
        ÁREA DE ESTOQUE
              │
              │
              ▼
      ┌─────────────────┐
      │     BANCADA     │
      │                 │
      │   █ █ █ █ █     │
      │   █ █ █ █ █     │
      └────────┬────────┘
               │
         LINHA VIRTUAL
         ─────────────
               │
               ▼
          CESTA SAI
```

Quando uma cesta cruzar a linha virtual:

```text
EVENTO:
2026-XX-XX 14:32:17

Cesta detectada: +1
```

O sistema poderá manter um contador:

```text
Cestas recebidas:       8.000
Cestas processadas:     6.420
Cestas restantes:       1.580
```

## Desafios

Esta provavelmente será uma das partes mais difíceis do projeto, porque haverá:

- pessoas;
- mãos cobrindo parcialmente as cestas;
- cestas sobrepostas;
- movimentação rápida;
- diferentes ângulos;
- objetos semelhantes;
- oclusão;
- variação de iluminação.

Por isso, o MVP deverá trabalhar com uma **zona de interesse controlada**, e não tentar interpretar todo o ambiente.

---

# 5. Câmera 3 — Saída / expedição

## Objetivo

Criar um terceiro ponto independente de conferência.

A câmera 3 deverá ficar na área de saída/expedição e registrar o momento em que as cestas deixam definitivamente o fluxo operacional.

O desenho conceitual é:

```text
ENTRADA
  │
  ▼
CÂMERA 1
  │
  ▼
ESTOQUE / PALETES
  │
  ▼
CÂMERA 2
  │
  ▼
BANCADA / DISTRIBUIÇÃO
  │
  ▼
CÂMERA 3
  │
  ▼
SAÍDA / EXPEDIÇÃO
```

Isso permite comparar três números independentes:

```text
ENTRADA
   ↓
PROCESSAMENTO
   ↓
SAÍDA
```

E detectar inconsistências.

Exemplo:

```text
Entrada:       15.920
Processadas:   15.740
Saída:         15.702

Diferença:
Entrada → Processamento = 180
Processamento → Saída  = 38
```

A ferramenta deverá permitir investigar essas diferenças em vez de simplesmente apresentar um total.

---

# 6. Arquitetura inicial

O protótipo deverá começar simples.

```text
┌──────────────┐
│ Câmera 1     │
└──────┬───────┘
       │
┌──────▼───────┐
│ Câmera 2     │
└──────┬───────┘
       │
┌──────▼───────┐
│ Câmera 3     │
└──────┬───────┘
       │
       ▼
┌────────────────────┐
│ Python              │
│                     │
│ OpenCV              │
│ Detecção            │
│ Tracking             │
│ Contagem             │
│ Regras de negócio    │
└──────────┬─────────┘
           │
           ▼
┌────────────────────┐
│ Banco de dados      │
└──────────┬─────────┘
           │
           ▼
┌────────────────────┐
│ Dashboard           │
│ Streamlit           │
└────────────────────┘
```

## Tecnologias candidatas

- Python;
- OpenCV;
- modelo de detecção de objetos;
- tracking de objetos;
- QR Code;
- ArUco para referências geométricas;
- SQLite no protótipo;
- PostgreSQL em uma eventual versão institucional;
- Streamlit para interface inicial.

A escolha definitiva do modelo de visão deverá ser feita após os primeiros testes com imagens reais.

---

# 7. Estratégia de desenvolvimento

O projeto deverá ser desenvolvido incrementalmente.

## Fase 1 — Prova de conceito

Usar vídeos reais ou simulados de paletes e testar:

- detecção das cestas;
- contagem;
- tracking;
- linha virtual;
- geração de eventos.

Resultado esperado:

```text
vídeo
  ↓
detecção
  ↓
contagem
  ↓
resultado
```

## Fase 2 — Câmera 1

Validar a entrada de paletes.

Métricas:

- paletes detectados;
- cestas estimadas;
- falsos positivos;
- falsos negativos;
- divergências;
- precisão da contagem.

## Fase 3 — Câmera 2

Validar a retirada das cestas na bancada.

Principal métrica:

**quantas cestas realmente cruzaram a linha versus quantas o sistema registrou.**

## Fase 4 — Câmera 3

Validar a saída.

A partir daqui começa a existir uma cadeia de conferência:

```text
ENTRADA → PROCESSAMENTO → SAÍDA
```

## Fase 5 — Dashboard

Criar uma interface para acompanhar:

- total recebido;
- total processado;
- total expedido;
- saldo;
- paletes;
- divergências;
- horários;
- produtividade;
- eventos de câmera.

---

# 8. Rastreabilidade

Uma evolução importante será associar os eventos visuais a identificadores.

Exemplo:

```text
PALLET-00037
       │
       ├── Entrada: 09:14
       ├── Cestas estimadas: 40
       ├── Processamento iniciado: 10:02
       ├── 40 cestas processadas
       └── Finalizado: 10:28
```

Um QR Code aplicado ao palete pode funcionar como identificador operacional.

Isso permite sair de uma simples contagem para uma verdadeira trilha de movimentação.

---

# 9. Medição física

A medição de dimensões não precisa fazer parte do primeiro MVP, mas deverá ser considerada desde a arquitetura.

Possíveis aplicações futuras:

- comprimento do palete;
- largura;
- altura da carga;
- volume;
- área ocupada;
- distância entre paletes;
- ocupação do espaço.

Para isso poderão ser estudados:

- calibração da câmera;
- marcadores ArUco;
- objetos de referência;
- visão estéreo;
- sensores de profundidade;
- reconstrução 3D.

A regra é não introduzir complexidade 3D antes de provar que a contagem 2D funciona.

---

# 10. Métricas de validação

Como o processo é conhecido e possui contagem real, o projeto poderá ser validado quantitativamente.

Para cada câmera:

```text
Total real
Total detectado
Acertos
Falsos positivos
Falsos negativos
Precisão
Recall
```

Exemplo:

```text
Cestas reais:       1.000
Cestas detectadas:    982
Detecções corretas:    970

Precisão:             XX%
Recall:               XX%
```

Também deverão ser registradas as condições em que ocorreram os erros:

- iluminação;
- distância;
- ângulo;
- velocidade;
- oclusão;
- pessoas na cena;
- empilhamento.

---

# 11. Dataset próprio

Uma das primeiras entregas técnicas deverá ser a criação de um pequeno dataset da própria operação.

Gravar:

- paletes completos;
- paletes parcialmente completos;
- cestas isoladas;
- cestas sobrepostas;
- retirada das cestas;
- movimentação de pessoas;
- diferentes condições de iluminação;
- diferentes ângulos de câmera.

O dataset deverá representar o ambiente real tanto quanto possível.

Isso é importante porque um modelo que funciona perfeitamente em imagens de laboratório pode falhar completamente diante de um palete real, plástico refletivo, funcionário passando na frente e iluminação ruim.

---

# 12. Segurança e privacidade

As câmeras deverão ser posicionadas com foco operacional.

O sistema deverá priorizar:

- objetos;
- paletes;
- cestas;
- áreas de passagem;
- eventos de movimentação.

A identificação facial de funcionários não é necessária para o objetivo inicial e deverá ser evitada.

Quando possível, o processamento deverá trabalhar com o mínimo de dados pessoais necessário.

---

# 13. Resultado esperado do MVP

Ao final do primeiro ciclo, o protótipo deverá conseguir demonstrar:

```text
             CESTA DE NATAL

       ┌──────────────────┐
       │  CÂMERA 1        │
       │  ENTRADA         │
       │                  │
       │  400 paletes     │
       │  ≈16.000 cestas  │
       └────────┬─────────┘
                │
                ▼
       ┌──────────────────┐
       │  CÂMERA 2        │
       │  PROCESSAMENTO   │
       │                  │
       │  +1 cesta/evento │
       └────────┬─────────┘
                │
                ▼
       ┌──────────────────┐
       │  CÂMERA 3        │
       │  EXPEDIÇÃO       │
       │                  │
       │  +1 cesta/evento │
       └────────┬─────────┘
                │
                ▼
       ┌──────────────────┐
       │  CONFERÊNCIA     │
       │                  │
       │ Entrada           │
       │ Processamento     │
       │ Saída             │
       │ Divergências      │
       └──────────────────┘
```

O sucesso do MVP não será medido por “ter IA”.

Será medido por conseguir responder, com evidência:

> **Quantas cestas entraram, quantas foram processadas, quantas saíram e onde está qualquer diferença?**

---

# 14. Evolução futura

Depois de validado o caso das Cestas de Natal, o mesmo motor poderá ser adaptado para outros problemas logísticos.

Possíveis extensões:

- contagem automática de caixas;
- conferência de paletes;
- ocupação de áreas;
- medição de volumes;
- inventário visual;
- identificação de posições;
- conferência de recebimento;
- conferência de expedição;
- leitura de QR Code;
- detecção de espaços vazios;
- estimativa de área ocupada;
- acompanhamento de produtividade;
- integração com sistemas de estoque.

A Cesta de Natal funcionará, portanto, como um **caso real de validação para uma plataforma maior de visão computacional aplicada à logística**.

---

# 15. Princípio do projeto

A arquitetura deverá seguir uma regra simples:

> **Primeiro fazer a câmera contar. Depois fazer a câmera entender. Por último fazer a câmera medir.**

A primeira vitória será detectar corretamente uma cesta.

A segunda será contar quarenta.

A terceira será acompanhar milhares.

A quarta será transformar isso em informação operacional confiável.
