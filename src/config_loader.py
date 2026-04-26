"""
Configuration loader for Disertatie project.
Loads paths from config.yaml and provides access to Framsticks path and other settings.

Requirements: PyYAML
  Install with: pip install pyyaml
"""

import os
from pathlib import Path

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False
    print("Warning: PyYAML not installed. Install with: pip install pyyaml")
    print("Falling back to hardcoded defaults.")



def get_disertatie_root():
    """Get the absolute path to the Disertatie folder (parent of src folder)."""
    src_dir = os.path.dirname(__file__)
    return os.path.abspath(os.path.join(src_dir, ".."))


def resolve_path(path_str, base_dir=None):
    """
    Resolve a path string to an absolute path.

    Args:
        path_str: Path string (can be absolute or relative)
        base_dir: Base directory for relative paths (defaults to Disertatie root)

    Returns:
        Absolute path as string
    """
    if base_dir is None:
        base_dir = get_disertatie_root()

    path = Path(path_str)
    if path.is_absolute():
        return str(path.resolve())
    else:
        return str((Path(base_dir) / path).resolve())


def load_config(config_file=None):
    """
    Load configuration from YAML file.

    Args:
        config_file: Path to config.yaml (defaults to Disertatie/config.yaml)

    Returns:
        Dictionary containing configuration
    """
    if config_file is None:
        config_file = os.path.join(get_disertatie_root(), 'config.yaml')

    if not YAML_AVAILABLE:
        return _get_default_config()

    if not os.path.exists(config_file):
        print(f"Info: Configuration file not found: {config_file}")
        return _get_default_config()

    try:
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        if config is None:
            return _get_default_config()
        return config
    except Exception as e:
        print(f"Warning: Error loading config file: {e}")
        return _get_default_config()


def _get_default_config():
    """
    Get default configuration when config.yaml is not available or not using YAML.

    Returns:
        Dictionary with default configuration
    """
    return {
        'framsticks': {
            'path': '../Framsticks54',
            'fallback_paths': [
                '../Framsticks',
                './Framsticks'
            ]
        },
        'database': {
            'path': 'algo_runs.db'
        },
        'experiments': {
            'results_dir': 'experiments',
            'simfiles_path': '../Framsticks54'
        }
    }


def get_framsticks_path(config=None):
    """
    Get the Framsticks installation path.
    Attempts primary path, then tries fallback paths if needed.

    Args:
        config: Configuration dictionary (loaded automatically if not provided)

    Returns:
        Absolute path to Framsticks directory

    Raises:
        FileNotFoundError: If no valid Framsticks path is found
    """
    if config is None:
        config = load_config()

    disertatie_root = get_disertatie_root()
    framsticks_config = config.get('framsticks', {})

    # Try primary path
    primary_path = framsticks_config.get('path')
    if primary_path:
        resolved_path = resolve_path(primary_path, disertatie_root)
        if os.path.exists(resolved_path):
            return resolved_path

    # Try fallback paths
    fallback_paths = framsticks_config.get('fallback_paths', [])
    for fallback_path in fallback_paths:
        resolved_path = resolve_path(fallback_path, disertatie_root)
        if os.path.exists(resolved_path):
            return resolved_path

    # If nothing found, raise error with helpful message
    paths_tried = [primary_path] + fallback_paths if primary_path else fallback_paths
    raise FileNotFoundError(
        f"Framsticks path not found. Tried the following:\n"
        + "\n".join([f"  - {resolve_path(p, disertatie_root)}" for p in paths_tried if p])
        + f"\n\nPlease update config.yaml in {disertatie_root} with the correct Framsticks path."
    )


def get_database_path(config=None):
    """
    Get the absolute path to the database file.

    Args:
        config: Configuration dictionary (loaded automatically if not provided)

    Returns:
        Absolute path to database file
    """
    if config is None:
        config = load_config()

    disertatie_root = get_disertatie_root()
    db_config = config.get('database', {})
    db_path = db_config.get('path', 'algo_runs.db')

    return resolve_path(db_path, disertatie_root)


def get_experiments_dir(config=None):
    """
    Get the absolute path to the experiments directory.

    Args:
        config: Configuration dictionary (loaded automatically if not provided)

    Returns:
        Absolute path to experiments directory
    """
    if config is None:
        config = load_config()

    disertatie_root = get_disertatie_root()
    exp_config = config.get('experiments', {})
    exp_dir = exp_config.get('results_dir', 'experiments')

    return resolve_path(exp_dir, disertatie_root)


def get_simfiles_path(config=None):
    """
    Get the absolute path to the simfiles directory.

    Args:
        config: Configuration dictionary (loaded automatically if not provided)

    Returns:
        Absolute path to simfiles directory
    """
    if config is None:
        config = load_config()

    disertatie_root = get_disertatie_root()
    exp_config = config.get('experiments', {})
    simfiles_path = exp_config.get('simfiles_path', '../Framsticks54')

    return resolve_path(simfiles_path, disertatie_root)