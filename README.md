# Cestas de Natal — Visão Computacional

Protótipo para contar, conferir e rastrear Cestas de Natal com uma câmera na tenda de distribuição:
**palete → bancada → funcionário**, por zonas, com reconciliação contra o padrão de palete (5 × 8 = 40) e os vales-cesta.

- Plano conceitual: [`Plano_Visao_Computacional_Cestas_de_Natal.md`](Plano_Visao_Computacional_Cestas_de_Natal.md)
- Plano de execução por fase: [`docs/00_planejamento_geral.md`](docs/00_planejamento_geral.md)

## Começar (Fase 0)

Instalação (uma vez):

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Uso — sempre pelo `rodar.cmd`, que chama o Python do projeto sem precisar ativar o ambiente (não depende da política de execução do PowerShell):

```powershell
.\rodar.cmd scripts\baixar_video_exemplo.py
.\rodar.cmd scripts\contar.py --fonte data\videos\people-walking.mp4 --classes person --pular 2
.\rodar.cmd scripts\contar.py --fonte data\videos\people-walking.mp4 --classes person --pular 2 --zonas data\zonas\exemplo_people_walking.json
.\rodar.cmd scripts\ver_eventos.py
```

Detalhes e experimentos em [`docs/01_fase0_teste_zero.md`](docs/01_fase0_teste_zero.md).
