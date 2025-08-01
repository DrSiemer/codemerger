import os
import json
from pathlib import Path
from .constants import CONFIG_FILE, DEFAULT_FILETYPES_CONFIG, VERSION_FILE

def _create_and_get_default_config():
    """
    Creates a new config object from the default template, saves it to disk,
    and returns it. This is the definitive first-run function.
    """
    config = {'active_directory': '', 'recent_directories': [], 'filetypes': [], 'default_editor': ''}
    try:
        # Load the list of filetypes from the bundled template.
        with open(DEFAULT_FILETYPES_CONFIG, 'r', encoding='utf-8') as f:
            config['filetypes'] = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # Fallback in case the template is missing or corrupt.
        pass

    # Save the newly created config to disk before returning.
    save_config(config)
    return config

def load_config():
    """
    Loads the main application configuration from config.json.
    If the file is missing or corrupt, it's created from the default template.
    """
    try:
        # If config file doesn't exist, this will raise FileNotFoundError.
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            # If file is empty, this will raise JSONDecodeError.
            config = json.load(f)
            # If file is valid but missing keys, handle that too.
            if 'filetypes' not in config:
                raise ValueError("Config is missing 'filetypes' key.")
            if 'default_editor' not in config:
                config['default_editor'] = '' # Add missing key for backward compatibility
            return config
    except (FileNotFoundError, json.JSONDecodeError, ValueError, IOError):
        # Any failure in reading the config results in creating a new one.
        return _create_and_get_default_config()

def save_config(config):
    """Saves the complete application configuration object to config.json."""
    # Ensure filetypes are sorted alphabetically for consistency.
    if 'filetypes' in config and isinstance(config.get('filetypes'), list):
        config['filetypes'].sort(key=lambda item: item['ext'])

    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2)

def load_all_filetypes():
    """Helper function to load just the filetypes list from the main config."""
    config = load_config()
    return config.get('filetypes', [])

def save_filetypes(filetypes_list):
    """
    Loads the current config, updates the filetypes list, and saves it back.
    """
    config = load_config()
    config['filetypes'] = filetypes_list
    save_config(config)

def load_active_file_extensions():
    """Loads active filetypes from the config and returns them as a set."""
    all_types = load_all_filetypes()
    return {item['ext'] for item in all_types if item.get('active', False)}

def parse_gitignore(base_dir):
    """Parses a .gitignore file and returns a list of patterns."""
    gitignore_path = os.path.join(base_dir, '.gitignore')
    patterns = []
    if os.path.isfile(gitignore_path):
        with open(gitignore_path, 'r', encoding='utf-8') as f:
            patterns = [
                line.strip() for line in f
                if line.strip() and not line.strip().startswith('#')
            ]
    return patterns

def is_ignored(path, base_dir, gitignore_patterns):
    """Checks if a given path should be ignored based on .gitignore patterns."""
    try:
        base_path = Path(base_dir)
        target_path = Path(path)
        relative_path = target_path.relative_to(base_path)
        for p in gitignore_patterns:
            if p.endswith('/'):
                if not target_path.is_dir():
                    continue
                if relative_path.match(p.rstrip('/')) or relative_path.match('*/' + p.rstrip('/')):
                    return True
            elif p.startswith('/'):
                if relative_path.match(p.lstrip('/')):
                    return True
            else:
                if relative_path.match(p) or relative_path.match('*/' + p):
                    return True
    except ValueError:
        return False
    return False

def load_app_version():
    """
    Reads the version from version.txt and returns it as a formatted string.
    Returns a default string if the file is not found or is malformed.
    """
    try:
        version_data = {}
        with open(VERSION_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                if '=' in line:
                    key, value = line.strip().split('=', 1)
                    version_data[key.strip().lower()] = value.strip()

        major = version_data.get('major', '?')
        minor = version_data.get('minor', '?')
        revision = version_data.get('revision', '?')

        return f"v{major}.{minor}.{revision}"

    except (FileNotFoundError, IndexError):
        # Handle case where file doesn't exist or line split fails
        return "v?.?.?"