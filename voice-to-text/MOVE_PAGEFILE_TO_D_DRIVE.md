# Move Windows Page File to D: Drive

## Why This Helps

When the AI model runs, it uses a lot of RAM. When RAM is full, Windows uses 
the "page file" (virtual memory) on C: drive. This can consume 2-8GB of C: drive space.

Moving the page file to D: drive will free up C: drive space.

## ⚠️ IMPORTANT: Do This Carefully

Follow these steps exactly:

### Step 1: Open System Properties

1. Press `Windows + R`
2. Type: `sysdm.cpl`
3. Press Enter

### Step 2: Access Virtual Memory Settings

1. Click the **Advanced** tab
2. Under "Performance", click **Settings**
3. Click the **Advanced** tab again
4. Under "Virtual memory", click **Change**

### Step 3: Move Page File to D: Drive

1. **Uncheck** "Automatically manage paging file size for all drives"

2. **For C: drive:**
   - Select `C:`
   - Select "No paging file"
   - Click **Set**
   - Click **OK** when warned

3. **For D: drive:**
   - Select `D:`
   - Select "Custom size"
   - Initial size: `4096` MB (4GB)
   - Maximum size: `8192` MB (8GB)
   - Click **Set**

4. Click **OK** on all windows

5. **Restart your computer** (required!)

### Step 4: Verify After Restart

```powershell
Get-WmiObject Win32_PageFileUsage | Select-Object Name, AllocatedBaseSize, CurrentUsage
```

Should show: `D:\pagefile.sys`

## ✅ Result

- C: drive will have 2-8GB more free space
- D: drive will use 2-8GB for page file
- App performance stays the same

## 🔄 To Revert

Follow the same steps but:
- Set D: to "No paging file"
- Set C: to "System managed size"
- Restart

## 📊 Recommended Sizes

Based on your RAM:
- 8GB RAM: Initial 4096MB, Max 8192MB
- 16GB RAM: Initial 8192MB, Max 16384MB
- 32GB RAM: Initial 16384MB, Max 32768MB

## ⚠️ Note

You MUST restart your computer for changes to take effect!
