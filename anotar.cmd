@echo off
rem Sobe o Label Studio para anotar os frames da Fase 2.
rem
rem As duas variaveis abaixo sao obrigatorias: as tarefas do projeto cesta_v1
rem guardam as imagens como caminhos relativos (frames\<video>\<frame>.jpg) servidos
rem por /data/local-files/. Sem elas o Label Studio abre, mas as imagens vem quebradas.
rem
rem   .\anotar.cmd
rem
rem Depois abra http://localhost:8080 -> projeto cesta_v1. Ctrl+C aqui encerra.
rem O Label Studio roda no Python global (nao no .venv do projeto).

set "LOCAL_FILES_SERVING_ENABLED=true"
set "LOCAL_FILES_DOCUMENT_ROOT=%~dp0data\dataset"

echo Servindo imagens de: %LOCAL_FILES_DOCUMENT_ROOT%
echo Abra http://localhost:8080 quando subir.
echo.

label-studio start
