from .prompt_decision import DecisionPrompt
from typing import Any, Dict
import dspy
from utils import ContextAndCall

class DecisionNode:
    def __init__(self, branch_id: str, instruction: str, model):
        self.branch_id = branch_id
        self.instruction = instruction
        self.available_tools = {}
        self.available_branches = {}
        self.model = model

    def add_tool_option(self, tool_name: str, tool_instance, description: str):
        """Add a Tool instance with its input schema"""
        if tool_name in self.available_tools:
            raise ValueError(f"Tool {tool_name} already exists.")
        self.available_tools[tool_name] = {
            "tool": tool_instance,
            "description": description,
            "inputs": tool_instance.inputs  # Store the input schema
        }

    def add_branch_option(self, branch_name: str, description: str):
        if branch_name in self.available_branches:
            raise ValueError(f"Branch {branch_name} already exists.")
        self.available_branches[branch_name] = {
            "description": description
        }

    def get_available_tools_formatted(self) -> Dict[str, Any]:
        """Format tools with descriptions and input schemas for DSPy"""
        formatted = {}
        for name, info in self.available_tools.items():
            formatted[name] = {
                "description": info["description"],
                "inputs": info["inputs"]  # Include input requirements
            }
        return formatted

    def get_available_branches_formatted(self) -> Dict[str, str]:
        """Format branches for DSPy"""
        return {name: info["description"] for name, info in self.available_branches.items()}

    async def __call__(self, tree_data):
        decision_module = ContextAndCall(DecisionPrompt, tree_data)
        output = await decision_module.aforward(
            available_tools=self.get_available_tools_formatted(),
            available_branches=self.get_available_branches_formatted(),
            lm=self.model  # Use 'lm' parameter name for DSPy
        )
        return output