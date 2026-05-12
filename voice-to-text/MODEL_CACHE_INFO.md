# Model Cache Location

## ✅ Models will be downloaded to D: drive

To save space on your C: drive, all AI models are configured to download to:

```
D:\Local_Voice\models\
```

## How It Works

The app sets these environment variables before loading any models:
- `HF_HOME=D:\Local_Voice\models`
- `HUGGINGFACE_HUB_CACHE=D:\Local_Voice\models`

This is configured in:
1. **main.py** - Sets environment variables at the very top
2. **run.bat** - Sets environment variables before running Python

## First Run

On first run, the `large-v3-turbo` model (~1.5GB) will be downloaded to:
```
D:\Local_Voice\models\hub\models--Systran--faster-whisper-large-v3-turbo\
```

## Disk Space

- **large-v3-turbo**: ~1.5GB
- **large-v3**: ~3GB
- **medium**: ~1.5GB
- **small**: ~500MB
- **base**: ~150MB
- **tiny**: ~75MB

## Changing Model Location

To use a different location, edit both:

**1. main.py** (lines 6-7):
```python
os.environ["HF_HOME"] = "D:/Local_Voice/models"
os.environ["HUGGINGFACE_HUB_CACHE"] = "D:/Local_Voice/models"
```

**2. run.bat** (lines 4-5):
```batch
set HF_HOME=D:\Local_Voice\models
set HUGGINGFACE_HUB_CACHE=D:\Local_Voice\models
```

## Verifying Location

After first run, check that models are in D: drive:
```powershell
dir D:\Local_Voice\models\hub\
```

You should see a folder like:
```
models--Systran--faster-whisper-large-v3-turbo
```

## Cleaning Up Old Models

If you previously downloaded models to C: drive, you can delete them:
```powershell
# Check if old models exist
dir C:\Users\$env:USERNAME\.cache\huggingface\hub\

# Delete old models (optional)
Remove-Item -Recurse -Force C:\Users\$env:USERNAME\.cache\huggingface\hub\models--Systran*
```

## ✅ All Set!

Your models will now download to D: drive automatically when you run the app.
