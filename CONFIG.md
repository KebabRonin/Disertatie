# Configuration Guide

This project uses a `config.yaml` file to manage paths and settings in a portable way.

## Quick Start

1. **Install PyYAML** (optional but recommended):
   ```bash
   pip install pyyaml
   ```

   Without PyYAML, the system will use hardcoded defaults automatically.

2. **Edit `config.yaml`** in the Disertatie folder to match your system:
   ```yaml
   framsticks:
     path: "../Framsticks54"  # Adjust this path
     fallback_paths:
       - "../Framsticks"
   ```

3. **Run your scripts** - they will automatically load settings from `config.yaml`.

## Configuration File Structure

### Framsticks Path
```yaml
framsticks:
  path: "../Framsticks54"  # Primary path (relative to Disertatie folder)
  fallback_paths:          # Fallback paths if primary doesn't exist
    - "../Framsticks"
    - "./Framsticks"
```

**Path Types:**
- **Absolute paths**: `/full/path/to/Framsticks54`
- **Relative paths**: `../Framsticks54` (relative to Disertatie folder)

### Database Path
```yaml
database:
  path: "algo_runs.db"  # Relative to Disertatie folder
```

### Experiments Directory
```yaml
experiments:
  results_dir: "experiments"  # Relative to Disertatie folder
```

## How It Works

1. Python scripts load the config using `config_loader.py`
2. All paths are resolved relative to the Disertatie folder
3. If PyYAML is not installed, sensible defaults are used
4. The system tries the primary path, then fallback paths

## Using the Config in Your Code

```python
from config_loader import load_config, get_framsticks_path, get_database_path

# Load the configuration
config = load_config()

# Get specific paths
framsticks_path = get_framsticks_path(config)
db_path = get_database_path(config)

print(f"Using Framsticks at: {framsticks_path}")
print(f"Database at: {db_path}")
```

## Troubleshooting

### "PyYAML not installed"
Install it with: `pip install pyyaml`

### "Framsticks path not found"
1. Check your `config.yaml` file
2. Make sure the path in `framsticks.path` is correct
3. Try an absolute path instead of relative
4. Check that the directory actually exists

### Example Configurations

**Windows (Disertatie on I: drive):**
```yaml
framsticks:
  path: "I:/Framsticks54"
  fallback_paths:
    - "I:/Framsticks"
```

**Linux/Mac (home directory):**
```yaml
framsticks:
  path: "~/Framsticks54"
  fallback_paths:
    - "~/Framsticks"
```

**Relative (side-by-side folders):**
```yaml
framsticks:
  path: "../Framsticks54"
  fallback_paths:
    - "../Framsticks"
```

## Environment-Specific Configs

You can create multiple config files for different machines:

```bash
# Use config-laptop.yaml instead of config.yaml
python script.py --config config-laptop.yaml
```

Then modify your scripts to accept a config parameter:
```python
import sys
config_file = sys.argv[1] if len(sys.argv) > 1 else None
config = load_config(config_file)
```
