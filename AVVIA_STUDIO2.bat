@echo off
cd /d "%~dp0"
echo Avvio Questionario Sistema 3 - Studio 2...
py -m streamlit run app.py
if errorlevel 1 (
    echo.
    echo Avvio con py non riuscito. Provo con python...
    python -m streamlit run app.py
)
pause
