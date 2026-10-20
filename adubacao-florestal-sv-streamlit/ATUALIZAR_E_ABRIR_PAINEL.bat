@echo off
chcp 65001 >nul
cd /d "%~dp0\.."
echo.
echo === Atualizar codigo do GitHub e abrir painel local ===
echo.

git fetch origin cursor/adubacao-supabase-mapa-fbe9
git checkout cursor/adubacao-supabase-mapa-fbe9
git pull origin cursor/adubacao-supabase-mapa-fbe9

call "%~dp0RODAR_PAINEL_LOCAL.bat"
