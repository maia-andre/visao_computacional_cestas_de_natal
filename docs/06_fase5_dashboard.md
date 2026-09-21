# Fase 5 — Dashboard

**Objetivo:** uma tela que responde, em tempo real e com evidência: *quantas saíram dos paletes, quantas foram entregues, quantas estão na bancada e onde está a diferença?*

Ferramenta: **Streamlit** lendo `data/db/eventos.sqlite`. Zero front-end; roda com `.\rodar.cmd -m streamlit run app\dashboard.py`.

## Telas

### 1. Visão geral (a tela que fica na tenda)

```
┌──────────────────────────────────────────────────────────────────┐
│  CESTAS DE NATAL — 03/12/2026                       14:32:17     │
├────────────────┬────────────────┬────────────────┬───────────────┤
│  PROCESSADAS   │   ENTREGUES    │  NA BANCADA    │  PALETES      │
│    11.940      │    11.902      │  contado:  38  │  esvaziados   │
│  (312 diretas) │  (312 diretas) │  visível:  37  │     298       │
├────────────────┴────────────────┴────────────────┴───────────────┤
│  Divergências abertas: 2     Cestas/hora (última h): 412         │
│  ⚠ bancada: contado 38 × visível 37 há 4 min                     │
└──────────────────────────────────────────────────────────────────┘
```

"Contado × visível" é a auto-conferência: saldo dos eventos versus cestas que a câmera vê na zona `bancada` agora.

### 2. Paletes

Blocos (ou paletes com QR, quando houver): início · fim · saídas contadas · esperado 40 · status. Clicar abre os snapshots do período.

### 3. Divergências

Ocorrências geradas automaticamente:
- bloco/palete com saídas ≠ 40;
- contado × visível na bancada divergindo por mais de N minutos;
- fechamento: entregues (câmera + lotes declarados) ≠ vales recolhidos.

Cada uma com hora, snapshots, e campo para o operador registrar a resolução ("recontado: 40, falso alarme").

### 4. Lançamentos manuais

- **Entrega em lote**: N cestas, N vales, hora — para entregas diretas fora do quadro.
- **Vales recolhidos**: total por turno/dia.
- **Palete esvaziado** (se a detecção de palete ainda não estiver confiável): botão "palete esvaziado agora".

### 5. Produtividade

Cestas por hora ao longo do dia; comparação entre dias; horário de pico.

### 6. Eventos brutos

Filtro por sessão / hora / transição / anulados; lista com snapshot. É a trilha de auditoria.

## Tabelas no banco

| tabela | conteúdo |
|---|---|
| `eventos` | já existe — cada transição, com `anulado` para vai-e-volta |
| `lancamentos_manuais` | tipo (lote / vales / palete), quantidade, hora, quem |
| `divergencias` | tipo, referência (período / palete), ids de eventos, resolução, quem resolveu |
| `sessoes` | câmera, início, fim, parâmetros usados (zonas, conf, modelo) — reprodutibilidade |

SQLite basta para o protótipo. Se virar sistema institucional com várias máquinas escrevendo ao mesmo tempo, migrar para PostgreSQL (o esquema é o mesmo).

## Critério de conclusão

- [ ] Visão geral atualizando sozinha enquanto a câmera roda.
- [ ] Toda divergência abre os snapshots correspondentes.
- [ ] Lançamentos manuais e resolução de divergência sem tocar no banco.
- [ ] Um dia inteiro exportável para CSV/Excel.
