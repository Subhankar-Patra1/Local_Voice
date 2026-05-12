@echo off
echo Installing Voice-to-Text...
echo.
echo Step 1: Installing PyTorch with CUDA 12.1 support...
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
echo.
echo Step 2: Installing other dependencies...
pip install -r requirements.txt
echo.
echo Done! Run: python main.py
pause
