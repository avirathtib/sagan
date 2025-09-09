import json
from datetime import datetime, date, time
from decimal import Decimal
from uuid import UUID
from typing import Any, Dict, List, Union
import logging

logger = logging.getLogger(__name__)
def sanitize_for_json(obj: Any) -> Any:
    """
    Recursively sanitize an object (or list of objects) for JSON serialization.
    
    Converts common non-JSON types to strings:
    - UUID -> string
    - datetime/date/time -> ISO format string
    - Decimal -> string
    - bytes -> base64 string
    - sets -> lists
    
    Removes keys with unsupported types that can't be converted.
    
    Args:
        obj: Object, list, dict, or primitive to sanitize
        
    Returns:
        JSON-serializable version of the object
    """
    
    # Handle None and primitives (str, int, float, bool)
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    
    # Handle UUID
    if isinstance(obj, UUID):
        return str(obj)
    
    # Handle datetime objects
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, date):
        return obj.isoformat()
    if isinstance(obj, time):
        return obj.isoformat()
    
    # Handle Decimal
    if isinstance(obj, Decimal):
        return str(obj)
    
    # Handle bytes
    if isinstance(obj, bytes):
        import base64
        return base64.b64encode(obj).decode('utf-8')
    
    # Handle sets
    if isinstance(obj, set):
        return [sanitize_for_json(item) for item in obj]
    
    # Handle lists and tuples
    if isinstance(obj, (list, tuple)):
        return [sanitize_for_json(item) for item in obj]
    
    # Handle dictionaries
    if isinstance(obj, dict):
        sanitized = {}
        for key, value in obj.items():
            # Convert non-string keys to strings
            if not isinstance(key, str):
                try:
                    key = str(key)
                except:
                    logger.warning(f"Skipping non-convertible key: {key}")
                    continue
            
            try:
                sanitized[key] = sanitize_for_json(value)
            except Exception as e:
                logger.warning(f"Skipping key '{key}' due to serialization error: {e}")
                continue
        
        return sanitized
    
    # Handle objects with __dict__ (custom classes)
    if hasattr(obj, '__dict__'):
        try:
            return sanitize_for_json(obj.__dict__)
        except:
            logger.warning(f"Could not serialize object of type {type(obj)}")
            return f"<{type(obj).__name__} object>"
    
    # Handle dataclasses
    if hasattr(obj, '__dataclass_fields__'):
        from dataclasses import asdict
        try:
            return sanitize_for_json(asdict(obj))
        except:
            logger.warning(f"Could not serialize dataclass {type(obj)}")
            return f"<{type(obj).__name__} dataclass>"
    
    # Fallback: try to convert to string, or remove if that fails
    try:
        return str(obj)
    except:
        logger.warning(f"Removing non-serializable object of type {type(obj)}")
        return None


def to_json_string(obj: Any, **kwargs) -> str:
    """
    Convert object to JSON string with sanitization.
    
    Args:
        obj: Object to convert
        **kwargs: Additional arguments for json.dumps
        
    Returns:
        JSON string
    """
    sanitized = sanitize_for_json(obj)
    
    # Default JSON settings
    json_kwargs = {
        'ensure_ascii': False,
        'indent': 2,
        'separators': (',', ': ')
    }
    json_kwargs.update(kwargs)
    
    return json.dumps(sanitized, **json_kwargs)
