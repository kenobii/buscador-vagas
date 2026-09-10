@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================
echo   Buscador de Vagas - Analista/Coord. Adm.
echo ============================================
echo.
python buscar_vagas.py
echo.
echo (pode fechar esta janela)
pause
