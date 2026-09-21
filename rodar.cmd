@echo off
rem Atalho: roda qualquer script com o Python do projeto (.venv), sem precisar ativar nada.
rem   .\rodar.cmd scripts\contar.py --fonte data\videos\people-walking.mp4 --classes person
rem   .\rodar.cmd scripts\ver_eventos.py
"%~dp0.venv\Scripts\python.exe" %*
