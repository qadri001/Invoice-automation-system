"""Configuration loader for the invoice automation system."""
import os
import yaml
from typing import Dict, Any
from pathlib import Path


class ConfigLoader:
    """Loads and manages system configuration."""

    def __init__(self, config_path: str = None):
        if config_path is None:
            config_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), 
                "config", 
                "config.yaml"
            )
        self.config_path = config_path
        self._config = None

    def load(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        if self._config is None:
            with open(self.config_path, 'r') as f:
                self._config = yaml.safe_load(f)
        return self._config

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value using dot notation (e.g., 'system.name')."""
        keys = key.split('.')
        value = self.load()
        for k in keys:
            value = value.get(k, default) if isinstance(value, dict) else default
            if value is None:
                return default
        return value

    @property
    def input_dir(self) -> str:
        return self.get('paths.input_dir')

    @property
    def processed_dir(self) -> str:
        return self.get('paths.processed_dir')

    @property
    def database_path(self) -> str:
        return self.get('paths.database_path')

    @property
    def ocr_engine(self) -> str:
        return self.get('ocr.engine')

    @property
    def confidence_threshold(self) -> float:
        return self.get('ocr.confidence_threshold', 0.6)
