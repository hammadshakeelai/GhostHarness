from typing import Dict, Any, Callable, Awaitable
from pydantic import BaseModel

class ToolDefinition(BaseModel):
    name: str
    description: str
    parameters: Dict[str, Any]

class Tool:
    def __init__(self, name: str, description: str, parameters: Dict[str, Any], func: Callable[..., Awaitable[Dict[str, Any]]]):
        self.name = name
        self.description = description
        self.parameters = parameters
        self.func = func

    def to_openai_dict(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            }
        }

    async def execute(self, **kwargs) -> Dict[str, Any]:
        return await self.func(**kwargs)
