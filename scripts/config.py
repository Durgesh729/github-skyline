import os
import json
from scripts.logger import setup_logger

logger = setup_logger()

class ConfigError(Exception):
    """Custom exception class for configuration errors."""
    pass

class ConfigManager:
    """
    Manages application configuration, validation, and theme resolution.
    Loads settings from config.json and merges theme parameters.
    """
    def __init__(self, config_path=None):
        self.root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if config_path is None:
            config_path = os.path.join(self.root_dir, 'config.json')
        self.config_path = config_path
        self.config_data = {}
        self.theme_data = {}
        
        self.load_config()

    def load_config(self):
        """Loads and validates config.json."""
        if not os.path.exists(self.config_path):
            raise ConfigError(f"Configuration file not found at: {self.config_path}")
            
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config_data = json.load(f)
            logger.info(f"Loaded base configuration from {self.config_path}")
        except json.JSONDecodeError as e:
            raise ConfigError(f"Invalid JSON format in config.json: {e}")
            
        self._validate_base_config()
        self.load_theme(self.config_data.get("theme", "cyberpunk"))

    def _validate_base_config(self):
        """Performs structural and type checks on config settings."""
        required_fields = ["username", "theme", "output_dir", "docs_dir"]
        for field in required_fields:
            if field not in self.config_data or not self.config_data[field]:
                raise ConfigError(f"Missing required configuration parameter: '{field}'")
                
        if not isinstance(self.config_data.get("username"), str):
            raise ConfigError("Configuration parameter 'username' must be a string.")

        # Resolve output directories
        self.output_dir = os.path.join(self.root_dir, self.config_data["output_dir"])
        self.docs_dir = os.path.join(self.root_dir, self.config_data["docs_dir"])

    def load_theme(self, theme_name):
        """Loads theme files from the themes directory."""
        themes_dir = os.path.join(self.root_dir, 'themes')
        theme_file = os.path.join(themes_dir, f"{theme_name}.json")
        
        if not os.path.exists(theme_file):
            logger.warning(f"Theme '{theme_name}' not found at {theme_file}. Falling back to 'cyberpunk'.")
            theme_name = "cyberpunk"
            theme_file = os.path.join(themes_dir, "cyberpunk.json")
            if not os.path.exists(theme_file):
                raise ConfigError("Default 'cyberpunk' theme file is missing from themes directory.")

        try:
            with open(theme_file, 'r', encoding='utf-8') as f:
                self.theme_data = json.load(f)
            logger.info(f"Successfully loaded theme: {self.theme_data.get('name', theme_name)}")
        except json.JSONDecodeError as e:
            raise ConfigError(f"Theme file '{theme_name}.json' contains invalid JSON: {e}")
            
        self.config_data["theme"] = theme_name
        self._validate_theme()

    def _validate_theme(self):
        """Verifies structure of loaded theme dictionary."""
        required_sections = ["name", "background", "grid", "building", "text", "effects"]
        for section in required_sections:
            if section not in self.theme_data:
                raise ConfigError(f"Theme structure is missing section: '{section}'")

    def get(self, key, default=None):
        """Retrieve root config attributes."""
        return self.config_data.get(key, default)

    @property
    def username(self):
        return self.config_data.get("username")

    @property
    def svg_settings(self):
        return self.config_data.get("svg_settings", {})

    @property
    def animation_settings(self):
        return self.config_data.get("animation_settings", {})

    @property
    def github_pages_url(self):
        return self.config_data.get("github_pages_url", "")

    def get_available_themes(self):
        """Scans the themes directory and returns a sorted list of available themes."""
        themes_dir = os.path.join(self.root_dir, 'themes')
        if not os.path.exists(themes_dir):
            return []
        
        themes = []
        for file in os.listdir(themes_dir):
            if file.endswith('.json'):
                themes.append(file[:-5])
        return sorted(themes)
