@echo off
chcp 65001 >nul
title Publicar Adubacao Florestal SV no GitHub
cd /d "%~dp0"

echo.
echo  ADUBACAO FLORESTAL 2026 — Santa Virginia
echo  ==========================================
echo.
echo  Esta pasta sera enviada para:
echo  github.com/lubrificacaomaquinassv-cloud/adubacao-florestal-sv
echo.
echo  ANTES: crie o repositorio vazio no GitHub com esse nome.
echo  Depois pressione uma tecla para continuar...
pause >nul

where git >nul 2>nul
if errorlevel 1 (
  echo ERRO: Git nao encontrado. Instale em https://git-scm.com
  pause
  exit /b 1
)

if not exist .git (
  git init
  git add .
  git commit -m "Painel Adubacao Florestal 2026 — Santa Virginia"
  git branch -M main
)

git remote remove origin 2>nul
git remote add origin https://github.com/lubrificacaomaquinassv-cloud/adubacao-florestal-sv.git

echo.
echo  Enviando para GitHub...
git push -u origin main

if errorlevel 1 (
  echo.
  echo  FALHOU — confira se o repositorio vazio ja foi criado no GitHub.
  echo  Veja COMO_SUBIR_NO_GITHUB.md para subir arquivo por arquivo.
) else (
  echo.
  echo  OK! Agora no Streamlit Cloud:
  echo  Repo: adubacao-florestal-sv  ^|  Main file: app.py
)

echo.
pause
