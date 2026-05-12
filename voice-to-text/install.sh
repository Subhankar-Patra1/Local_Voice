#!/bin/bash
set -e
echo "Installing Voice-to-Text..."

# Detect OS
OS="$(uname -s)"

echo ""
echo "Step 1: Installing PyTorch..."

# PyTorch with CUDA (Linux) or CPU (macOS)
if [ "$OS" = "Linux" ]; then
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
else
    pip install torch torchvision torchaudio
fi

echo ""
echo "Step 2: Installing other dependencies..."
pip install -r requirements.txt

# Linux extras
if [ "$OS" = "Linux" ]; then
    echo ""
    echo "Step 3: Installing text injection tools for Linux..."
    sudo apt-get update
    sudo apt-get install -y xdotool wtype 2>/dev/null || true
    
    # ydotool (Wayland kernel-level injection)
    if sudo apt-get install -y ydotool 2>/dev/null; then
        sudo systemctl enable --now ydotool 2>/dev/null || \
            echo "ydotool installed but daemon not started. Run: sudo systemctl enable --now ydotool"
    else
        echo "Could not install ydotool. Install manually for Wayland support."
    fi
    
    echo ""
    echo "NOTE: For ydotool to work, add your user to the input group:"
    echo "  sudo usermod -aG input \$USER"
    echo "  Then log out and log back in."
fi

echo ""
echo "Done! Run: python main.py"
