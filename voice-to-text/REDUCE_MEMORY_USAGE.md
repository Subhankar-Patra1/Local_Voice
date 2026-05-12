# Reduce Memory Usage

If C: drive space is still being consumed during runtime, try these optimizations:

## Option 1: Use a Smaller Model (Fastest Fix)

Edit `config.py`:

```python
# Change from:
MODEL = "large-v3-turbo"  # Uses ~2-3GB RAM

# To:
MODEL = "base"  # Uses ~500MB RAM (much faster, slightly less accurate)
```

**Model Memory Usage:**
- `tiny`: ~200MB RAM (very fast, lower accuracy)
- `base`: ~500MB RAM (fast, good accuracy)
- `small`: ~1GB RAM (medium speed, good accuracy)
- `medium`: ~2GB RAM (slower, very good accuracy)
- `large-v3-turbo`: ~2-3GB RAM (medium speed, excellent accuracy)
- `large-v3`: ~3-4GB RAM (slow, best accuracy)

## Option 2: Optimize Compute Type

Already optimized in `config.py`:

```python
COMPUTE_TYPE = "int8_float16"  # ✅ Already using lowest memory option
```

This is already the most memory-efficient setting for CUDA.

## Option 3: Close Other Programs

Before running the app, close:
- ❌ Web browsers (Chrome/Edge use a lot of RAM)
- ❌ Other AI tools
- ❌ Video editors
- ❌ Games
- ❌ Multiple IDE windows

## Option 4: Increase Your RAM

If you frequently run out of memory:
- Consider upgrading from 8GB to 16GB RAM
- Or from 16GB to 32GB RAM

## Option 5: Monitor Memory Usage

Check what's using memory:

```powershell
# See memory usage
Get-Process | Sort-Object WorkingSet -Descending | Select-Object -First 10 Name, @{Name="Memory(MB)";Expression={[math]::Round($_.WorkingSet / 1MB, 2)}}
```

## Recommended Settings for Low Memory

Edit `config.py`:

```python
MODEL = "base"  # Smaller model
DEVICE = "cuda"  # Keep GPU acceleration
COMPUTE_TYPE = "int8_float16"  # Already optimal
```

This will use:
- ~500MB RAM instead of ~2-3GB
- Still very accurate for English
- Much faster transcription
- Less C: drive consumption

## Test Different Models

Try each model and see which works best for you:

```python
# Fastest, lowest memory
MODEL = "base"

# Good balance
MODEL = "small"

# Best accuracy (if you have RAM)
MODEL = "large-v3-turbo"
```

## ✅ Summary

**Best fix for C: drive consumption:**
1. Move page file to D: drive (see MOVE_PAGEFILE_TO_D_DRIVE.md)
2. Use smaller model: `MODEL = "base"`
3. Close other programs before running

This should keep C: drive usage minimal during runtime.
