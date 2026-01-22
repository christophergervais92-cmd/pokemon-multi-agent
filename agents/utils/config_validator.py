#!/usr/bin/env python3
"""
Configuration Validation

Validates configuration on startup and provides helpful error messages.
"""
import os
from typing import Dict, List, Tuple, Any, Optional
from pathlib import Path

from agents.utils.logger import get_logger

logger = get_logger("config")

# =============================================================================
# CONFIGURATION SCHEMA
# =============================================================================

CONFIG_SCHEMA = {
    # Optional - with defaults
    "LOG_LEVEL": {"type": str, "default": "INFO", "valid": ["DEBUG", "INFO", "WARNING", "ERROR"]},
    "LOG_TO_FILE": {"type": bool, "default": True},
    "LOG_TO_CONSOLE": {"type": bool, "default": True},
    "MAX_CONCURRENT_REQUESTS": {"type": int, "default": 10, "min": 1, "max": 100},
    "DB_POOL_SIZE": {"type": int, "default": 10, "min": 1, "max": 50},
    "RATE_LIMIT_REQUESTS": {"type": int, "default": 100, "min": 1},
    "RATE_LIMIT_WINDOW": {"type": int, "default": 60, "min": 1},
    
    # Optional - no defaults (will be None if not set)
    "PROXY_SERVICE_URL": {"type": str, "optional": True},
    "PROXY_SERVICE_KEY": {"type": str, "optional": True},
    "DISCORD_CLIENT_ID": {"type": str, "optional": True},
    "DISCORD_CLIENT_SECRET": {"type": str, "optional": True},
    "REDIS_URL": {"type": str, "optional": True, "default": "redis://localhost:6379/0"},
    "BESTBUY_API_KEY": {"type": str, "optional": True},
    "TWOCAPTCHA_API_KEY": {"type": str, "optional": True},
    "ANTICAPTCHA_API_KEY": {"type": str, "optional": True},
    
    # Required for certain features
    "ENCRYPTION_KEY": {"type": str, "required_for": ["discord_auth"], "min_length": 32},
}

# =============================================================================
# VALIDATION
# =============================================================================

class ConfigValidator:
    """Validates configuration on startup."""
    
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.validated_config: Dict[str, Any] = {}
    
    def validate(self, required_features: List[str] = None) -> Tuple[bool, Dict[str, Any]]:
        """
        Validate all configuration.
        
        Args:
            required_features: List of features that must be configured
        
        Returns:
            (is_valid, validated_config)
        """
        required_features = required_features or []
        
        for key, schema in CONFIG_SCHEMA.items():
            value = os.environ.get(key)
            
            # Check if required for features
            if required_features and schema.get("required_for"):
                if any(feature in required_features for feature in schema["required_for"]):
                    if not value:
                        self.errors.append(
                            f"{key} is required for features: {', '.join(schema['required_for'])}"
                        )
                        continue
            
            # Use default if not set and not required
            if not value:
                if "default" in schema:
                    value = schema["default"]
                    self.validated_config[key] = value
                    continue
                elif schema.get("optional", False):
                    self.validated_config[key] = None
                    continue
                else:
                    self.warnings.append(f"{key} not set, using default: {schema.get('default', 'None')}")
                    if "default" in schema:
                        value = schema["default"]
                    else:
                        continue
            
            # Type validation
            try:
                if schema["type"] == bool:
                    value = value.lower() in ("true", "1", "yes", "on")
                elif schema["type"] == int:
                    value = int(value)
                elif schema["type"] == float:
                    value = float(value)
                elif schema["type"] == str:
                    value = str(value)
            except (ValueError, TypeError) as e:
                self.errors.append(f"{key}: Invalid type, expected {schema['type'].__name__}, got {type(value).__name__}")
                continue
            
            # Range validation
            if schema["type"] == int:
                if "min" in schema and value < schema["min"]:
                    self.errors.append(f"{key}: Value {value} is below minimum {schema['min']}")
                    continue
                if "max" in schema and value > schema["max"]:
                    self.errors.append(f"{key}: Value {value} is above maximum {schema['max']}")
                    continue
            
            # String length validation
            if schema["type"] == str and "min_length" in schema:
                if len(value) < schema["min_length"]:
                    self.errors.append(f"{key}: Length {len(value)} is below minimum {schema['min_length']}")
                    continue
            
            # Valid values check
            if "valid" in schema:
                if value not in schema["valid"]:
                    self.errors.append(f"{key}: Value '{value}' not in valid values: {schema['valid']}")
                    continue
            
            self.validated_config[key] = value
        
        # Log results
        if self.errors:
            for error in self.errors:
                logger.error(f"Config validation error: {error}")
        
        if self.warnings:
            for warning in self.warnings:
                logger.warning(f"Config validation warning: {warning}")
        
        if not self.errors:
            logger.info("Configuration validated successfully", extra={
                "warnings": len(self.warnings),
                "validated_keys": len(self.validated_config),
            })
        
        return len(self.errors) == 0, self.validated_config
    
    def get_summary(self) -> Dict[str, Any]:
        """Get validation summary."""
        return {
            "valid": len(self.errors) == 0,
            "errors": self.errors,
            "warnings": self.warnings,
            "validated_keys": len(self.validated_config),
        }


def validate_config(required_features: List[str] = None) -> Tuple[bool, Dict[str, Any]]:
    """
    Validate configuration on startup.
    
    Args:
        required_features: List of features that must be configured
    
    Returns:
        (is_valid, validated_config)
    """
    validator = ConfigValidator()
    return validator.validate(required_features)
