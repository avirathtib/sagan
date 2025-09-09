from typing import Any, Dict, List, Callable, Union
from dataclasses import dataclass
from abc import ABC, abstractmethod
import inspect
from helper_functions import to_json_string, sanitize_for_json

class Response:
    def __init__(self, data, type=None, frontend=None, metadata=None, description=None):
        self.type = type or None
        self.data = data
        self.frontend = frontend or None
        self.metadata = metadata or {}
        self.description = description

    def to_dict(self):
        return sanitize_for_json({
            "type": self.type,
            "data": self.data,
            "frontend": self.frontend,
            "metadata": self.metadata,
            "description": self.description,
        })


@dataclass
class Error:
    agent_name: str
    error: str

class Tool(ABC):
    """Base Tool class that can be subclassed for custom tools"""
    
    def __init__(self, name: str, description: str, inputs: Dict[str, Any] = None):
        self.name = name
        self.description = description
        self.inputs = inputs or {}
    
    @abstractmethod
    async def __call__(self, tree_data, inputs: Dict[str, Any], **kwargs) -> Response:
        """Override this method in subclasses"""
        pass
    
    def _format_result(self, raw_result: Any) -> Response:
        """Convert any result into Response format"""
        if isinstance(raw_result, Response):
            return raw_result
        elif isinstance(raw_result, str):
            return Response(
                type="text",
                data=[{"text": raw_result}],
                frontend=True,
                metadata={},
                description=self.description
            )
        elif isinstance(raw_result, dict):
            return Response(
                type="data_message",
                data=[raw_result],
                frontend=True,
                metadata={},
                description=self.description
            )
        elif isinstance(raw_result, list):
            return Response(
                type="table",
                data=raw_result,
                frontend=True,
                metadata={},
                description=self.description
            )
        else:
            return Response(
                type="data_message",
                data=[{"result": str(raw_result)}],
                frontend=True,
                metadata={},
                description=self.description
            )

def tool(function: Callable = None, *, name: str = None, description: str = None):
    """Decorator to convert functions into Tools"""
    
    def decorator(func: Callable) -> Tool:
        tool_name = name or func.__name__
        tool_description = description or func.__doc__ or f"Execute {func.__name__}"
        
        # Extract inputs from function signature
        sig = inspect.signature(func)
        tool_inputs = {}
        
        for param_name, param in sig.parameters.items():
            if param_name not in ['tree_data', 'inputs']:  # Skip special params
                tool_inputs[param_name] = {
                    "type": param.annotation if param.annotation != inspect.Parameter.empty else "any",
                    "required": param.default == inspect.Parameter.empty,
                    "default": param.default if param.default != inspect.Parameter.empty else None
                }
        
        class FunctionTool(Tool):
            def __init__(self):
                super().__init__(tool_name, tool_description, tool_inputs)
                self._original_function = func
            
            async def __call__(self, tree_data, inputs: Dict[str, Any], **kwargs) -> Response:
                try:
                    # Call the original function with inputs
                    if inspect.iscoroutinefunction(func):
                        result = await func(**inputs)
                    else:
                        result = func(**inputs)
                    
                    # Format result into Response
                    return self._format_result(result)
                    
                except Exception as e:
                    return Response(
                        type="text",
                        data=[{"text": f"Error in {self.name}: {str(e)}"}],
                        frontend=True,
                        metadata={"error": True},
                        description=f"Error executing {self.name}"
                    )
        
        return FunctionTool()
    
    if function is None:
        return decorator
    else:
        return decorator(function)        