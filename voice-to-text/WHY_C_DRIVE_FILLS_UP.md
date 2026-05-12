# Why C: Drive Fills Up When Running the App

## 📊 Understanding the Issue

**Model Storage (D: drive)**: ✅ ~1.5GB - Stored permanently on D: drive  
**Runtime Memory (C: drive)**: ⚠️ 2-8GB - Temporary usage during runtime

## 🔍 What's Happening

### 1. **Page File (Virtual Memory)** - Main Culprit

When you run the app:
1. Model loads from D: drive into RAM (~2-3GB)
2. If RAM is full, Windows uses C: drive as "virtual memory"
3. Creates/expands `C:\pagefile.sys` (2-8GB)
4. This is TEMPORARY - freed when app closes

**Check your page file:**
```powershell
Get-WmiObject Win32_PageFileUsage
```

### 2. **Temporary Files**

The app creates temp files in:
- `C:\Users\<YourName>\AppData\Local\Temp\`
- Audio buffers
- Transcription cache
- Python temp files

**Now fixed**: Temp files go to `D:\Local_Voice\temp\` ✅

### 3. **System RAM Pressure**

Your system has limited RAM (probably 8-16GB):
- Windows: ~2GB
- Browser: ~1-2GB
- Voice app: ~2-3GB
- Other apps: ~1-2GB
- **Total**: Exceeds physical RAM → Uses C: drive page file

## ✅ Solutions (In Order of Effectiveness)

### Solution 1: Move Page File to D: Drive (BEST FIX)

This moves the 2-8GB virtual memory file from C: to D: drive.

**See detailed guide**: `MOVE_PAGEFILE_TO_D_DRIVE.md`

**Quick steps:**
1. Press `Windows + R`, type `sysdm.cpl`
2. Advanced → Performance Settings → Advanced → Virtual Memory → Change
3. Uncheck "Automatically manage"
4. C: drive → "No paging file" → Set
5. D: drive → "Custom size" → Initial: 4096, Max: 8192 → Set
6. Restart computer

**Result**: Saves 2-8GB on C: drive ✅

### Solution 2: Use Smaller Model (EASIEST FIX)

Edit `config.py`:
```python
MODEL = "base"  # Instead of "large-v3-turbo"
```

**Memory usage:**
- `large-v3-turbo`: ~2-3GB RAM
- `base`: ~500MB RAM

**Result**: Uses 80% less memory, reduces page file usage ✅

### Solution 3: Temp Files to D: Drive (ALREADY DONE)

Updated `main.py` to use `D:\Local_Voice\temp\` for all temp files.

**Result**: Temp files no longer fill C: drive ✅

### Solution 4: Close Other Programs

Before running the app:
- Close Chrome/Edge (uses 1-2GB RAM)
- Close other heavy apps
- Keep only essential programs running

**Result**: More RAM available, less page file usage ✅

### Solution 5: Add More RAM (Hardware)

Upgrade your system RAM:
- 8GB → 16GB
- 16GB → 32GB

**Result**: Less reliance on page file ✅

## 📈 Expected C: Drive Usage

### Before Fixes:
- Model download: 0GB (on D: drive) ✅
- Page file: 2-8GB (on C: drive) ❌
- Temp files: 100-500MB (on C: drive) ❌
- **Total C: usage**: 2-8.5GB ❌

### After Fixes:
- Model download: 0GB (on D: drive) ✅
- Page file: 0GB (moved to D: drive) ✅
- Temp files: 0GB (moved to D: drive) ✅
- **Total C: usage**: ~0GB ✅

## 🎯 Recommended Action Plan

**Do these in order:**

1. ✅ **Move page file to D: drive** (see MOVE_PAGEFILE_TO_D_DRIVE.md)
   - Saves 2-8GB on C: drive
   - One-time setup, permanent fix
   - Requires restart

2. ✅ **Temp files already moved to D: drive** (already done in main.py)
   - Saves 100-500MB on C: drive
   - Automatic

3. ⚙️ **Optional: Use smaller model** (edit config.py)
   - Change `MODEL = "base"`
   - Reduces RAM usage by 80%
   - Slightly less accurate but much faster

4. 🧹 **Close other programs** before running
   - Frees up RAM
   - Reduces page file usage

## 🔍 Monitor Usage

### Check C: drive space:
```powershell
Get-PSDrive C | Select-Object Used, Free
```

### Check memory usage:
```powershell
Get-Process python | Select-Object Name, @{Name="Memory(MB)";Expression={[math]::Round($_.WorkingSet / 1MB, 2)}}
```

### Check page file location:
```powershell
Get-WmiObject Win32_PageFileUsage | Select-Object Name, AllocatedBaseSize, CurrentUsage
```

## ✅ Summary

**The model is on D: drive** ✅  
**But runtime uses C: drive for:**
- ❌ Page file (virtual memory) - **MOVE TO D: DRIVE**
- ✅ Temp files - **ALREADY MOVED TO D: DRIVE**

**Best fix**: Move page file to D: drive (see MOVE_PAGEFILE_TO_D_DRIVE.md)

After moving page file, C: drive usage during runtime should be minimal (<100MB).
