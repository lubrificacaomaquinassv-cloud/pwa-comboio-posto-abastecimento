@echo off
chcp 65001 >nul
set ORIGEM=%USERPROFILE%\Desktop\DADOS_PAINEL\fazenda_santa_virginia_completo.kml
set DEST=%~dp0dados\fazenda_santa_virginia_completo.kml
if not exist "%ORIGEM%" (
  echo ERRO: KML nao encontrado em %ORIGEM%
  pause
  exit /b 1
)
if not exist "%~dp0dados" mkdir "%~dp0dados"
copy /Y "%ORIGEM%" "%DEST%"
echo.
echo OK — KML copiado para dados\
echo.
echo Proximo NO POWERSHELL ^(uma linha por vez^):
echo   cd %~dp0
echo   git add dados\fazenda_santa_virginia_completo.kml
echo   git commit -m "KML do mapa no repositorio"
echo   git push
echo.
echo Depois: Streamlit - Reiniciar app ^(branch painel-adubacao^)
echo Nao precisa senha do Postgres para o mapa.
pause
