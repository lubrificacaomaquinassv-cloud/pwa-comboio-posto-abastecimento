@echo off
cd /d "%~dp0"
set ORIGEM=%~dp0data\orcamento.db
set DEST=%~1
if "%DEST%"=="" set DEST=E:\backup-orcamento
if not exist "%ORIGEM%" (
  echo Arquivo nao encontrado: %ORIGEM%
  echo Rode o app pelo menos uma vez para criar o banco.
  pause
  exit /b 1
)
if not exist "%DEST%" mkdir "%DEST%"
set ARQ=%DEST%\orcamento_%date:~-4%%date:~3,2%%date:~0,2%_%time:~0,2%%time:~3,2%.db
set ARQ=%ARQ: =0%
copy /Y "%ORIGEM%" "%ARQ%"
copy /Y "%ORIGEM%" "%DEST%\orcamento.db"
echo.
echo Backup salvo em:
echo   %ARQ%
echo   %DEST%\orcamento.db
echo.
echo Tamanho tipico: poucos KB ou MB — cabe em qualquer pendrive.
echo Para restaurar: copie orcamento.db para a pasta data\ do app.
pause
