import inspect
from typing import get_type_hints, get_origin, get_args, Callable, Any, Literal
from enum import Enum

def _python_type_to_json_type(py_type: Any) -> dict:
    origin = get_origin(py_type)
    args = get_args(py_type)

    # Handle Literal
    if origin is Literal:
        return {
            "type": _python_type_to_json_type(type(args[0]))["type"],
            "enum": list(args)
        }

    # Handle Enum
    if isinstance(py_type, type) and issubclass(py_type, Enum):
        return {
            "type": "string",
            "enum": [e.value for e in py_type]
        }

    # Handle List[X]
    if origin == list and args:
        return {
            "type": "array",
            "items": _python_type_to_json_type(args[0])
        }

    # Basic type mapping
    mapping = {
        str: "string",
        int: "integer",
        float: "number",
        bool: "boolean",
        list: "array",
        dict: "object"
    }

    return {"type": mapping.get(origin or py_type, "string")}


def _parse_pydoc(func: Callable) -> dict:
    doc = inspect.getdoc(func) or ""
    lines = doc.splitlines()
    description_lines = []
    param_descriptions = {}

    for line in lines:
        stripped = line.strip()
        # Coleta descrição geral até encontrar o primeiro ':param'
        if stripped.startswith(":param"):
            break
        description_lines.append(stripped)

    for line in lines:
        line = line.strip()
        if line.startswith(":param"):
            try:
                param, desc = line[7:].split(":", 1)
                param_descriptions[param.strip()] = desc.strip()
            except ValueError:
                continue  # Ignora linha mal formatada

    description = " ".join(description_lines).strip()

    return {
        "description": description,
        "param_descriptions": param_descriptions
    }


def to_openai_tool(func: Callable) -> dict:
    sig = inspect.signature(func)
    hints = get_type_hints(func)
    doc_info = _parse_pydoc(func)

    properties = {}
    for name, param in sig.parameters.items():
        param_type = hints.get(name, str)
        json_schema = _python_type_to_json_type(param_type)
        json_schema["description"] = doc_info["param_descriptions"].get(name, "No description provided.")
        properties[name] = json_schema

    return {
        "type": "function",
        "function": {
            "name": func.__name__,
            "description": doc_info["description"],
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": list(sig.parameters),
                "additionalProperties": False
            },
            "strict": True
        }
    }
