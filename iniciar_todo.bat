@echo off
title Lanzador Cimarron UABC (WSL Linux)
color 0A

echo ======================================================================
echo           INICIANDO ASISTENTE INTERACTIVO CIMARRON UABC
echo                      (Ejecutando en Linux / WSL)
echo ======================================================================
echo.

wsl bash -c "cd /home/zombs/Proyecto_Cimarron && ./iniciar_todo.sh"

pause
