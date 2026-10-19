@echo off
chcp 65001 >nul
title Atualizar Painel Adubacao no Streamlit
echo.
echo === Atualizar painel (GitHub adubacao-florestal-sv) ===
echo.

where git >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Git nao instalado.
    echo Baixe e instale: https://git-scm.com/download/win
    echo Depois execute este arquivo de novo.
    pause
    exit /b 1
)

cd /d "%USERPROFILE%\Desktop"
echo Pasta de trabalho: %CD%\pwa-adubacao
echo.

if exist "pwa-adubacao" (
    echo Removendo pasta antiga...
    rmdir /s /q "pwa-adubacao"
)

echo Baixando codigo novo...
git clone -b adubacao-florestal-sv --single-branch "https://github.com/lubrificacaomaquinassv-cloud/pwa-comboio-posto-abastecimento.git" "pwa-adubacao"
if errorlevel 1 (
    echo [ERRO] Falha no git clone. Verifique internet e login GitHub.
    pause
    exit /b 1
)

cd pwa-adubacao
powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\ATUALIZAR_PAINEL_NO_GITHUB.ps1"
if errorlevel 1 (
    echo.
    echo [ERRO] Falha ao enviar para GitHub. Faca login: git config --global user.email "seu@email.com"
    pause
    exit /b 1
)

echo.
echo ========================================
echo OK! Agora no Streamlit:
echo   menu ... (canto inferior direito) -^> Reboot app
echo   espere 2 minutos e atualize F5
echo ========================================
pause
