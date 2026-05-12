@echo off
echo Starting Voice-to-Text...
echo.
echo Setting model cache location to D:\Local_Voice\models
set HF_HOME=D:\Local_Voice\models
set HUGGINGFACE_HUB_CACHE=D:\Local_Voice\models
echo.
.\venv\Scripts\python.exe main.py
pause
