# Portability Fixes Applied

All hardcoded absolute paths have been replaced with portable relative paths or environment variables to ensure the repository works on any computer after cloning.

## Files Modified

### 1. **platformio_slip/python_client/test_dynamic.py**
- **Changed**: Hardcoded `'COM25'` → `os.environ.get("BROCCOLI_PORT", "COM25")`
- **Benefit**: Users can set `BROCCOLI_PORT` environment variable to override default

### 2. **platformio_slip/platformio.ini**
- **Changed**: Added comments explaining how to change COM ports for different systems
- **Benefit**: Clear instructions for Windows (COMx) and Linux/Mac (/dev/ttyUSBx)

### 3. **notebooks/tools/上傳檔案 - Broccoli.ipynb**
- **Changed**: Removed excessive parent directory traversal (`'..', '..', '..', '..', '..'`)
- **Fixed**: Now uses proper relative path to find `ampy_utils.py` in same directory
- **Fixed**: Uses `REPO_ROOT` to locate `micropython_workers/` directory
- **Benefit**: Works regardless of notebook execution directory

### 4. **notebooks/tools/ampy_utils.py**
- **Changed**: Updated default COM port from `COM12` → `COM3` with clear comments
- **Added**: Comments explaining how to set port for Windows/Linux/Mac
- **Benefit**: More intuitive default with cross-platform guidance

### 5. **notebooks/demo/mini cluster test.ipynb**
- **Changed**: Commented out all old folder references (`codes/`, `external/`)
- **Added**: Warning that this is legacy MQTT-based code
- **Added**: Pointer to current SLIP-based implementation
- **Benefit**: Prevents errors from missing directories, guides users to working code

## Remaining Configuration Needed

Users cloning this repo will need to configure these settings for their hardware:

1. **COM Port Configuration** (choose one method):
   - Set environment variable: `set BROCCOLI_PORT=COMx` (Windows) or `export BROCCOLI_PORT=/dev/ttyUSBx` (Linux)
   - Edit default in files:
     - `platformio_slip/platformio.ini` - lines 20-21 (master) and 28-29 (worker)
     - `notebooks/tools/ampy_utils.py` - line 9
     - `notebooks/tools/上傳檔案 - Broccoli.ipynb` - cell with COM port settings

2. **No Other Changes Required** - All paths are now relative or configurable

## Verification

All imports and path operations now use:
- ✅ `os.path.join()` with relative paths
- ✅ `os.path.abspath()` to resolve relative to current file
- ✅ Environment variables with sensible defaults
- ✅ Cross-platform path separators (via `os.path`)
- ✅ Comments explaining what users need to customize

## Files Confirmed Portable

- `platformio_slip/python_client/test_everything.py` - Already used env var
- `platformio_slip/python_client/broccoli_cluster.py` - No hardcoded paths
- `notebooks/test_everything.ipynb` - Already used env var and relative paths
- All `micropython_workers/*.py` - Use relative imports (correct for MicroPython)

## Testing Recommendations

After cloning, users should:
1. Set `BROCCOLI_PORT` environment variable to their master node's COM port
2. Run: `cd platformio_slip/python_client && python test_everything.py`
3. Or open `notebooks/test_everything.ipynb` and run cells

No path-related errors should occur on any system (Windows/Linux/Mac).
