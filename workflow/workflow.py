import uuid
import os
from typing import Dict, Union, Callable, Any
from .helper_objects import TreeData  
from .utils import DecisionNode  
from objects import Tool, tool  
from external_tools import sql_tool, charting_tool, python_interpreter_tool, output_formatter_tool
import asyncio
import dspy


class Workflow:
    def __init__(self, user_id=None, conversation_id=None, model=None):
        self.user_id = str(uuid.uuid4()) if user_id is None else user_id
        self.conversation_id = str(uuid.uuid4()) if conversation_id is None else conversation_id
        
        self.tree_data = TreeData()  
        self.branches = {} 
        self.decision_nodes = {}  
        self.tools_registry = {}  
        self.current_branch = "base"
        self.model = model
        sql_tool_instance = sql_tool.SQLTool(self.model)
        chart_tool_instance = charting_tool.ChartTool(self.model)
        python_interpreter_instance = python_interpreter_tool.PythonInterpreterTool(self.model)
        output_formatter_instance = output_formatter_tool.OutputFormatterTool(self.model)
        self._create_base_branch()

        self.add_tool(sql_tool_instance, branch_id="base")
        self.add_tool(chart_tool_instance, branch_id="base")
        # self.add_tool(python_interpreter_instance, branch_id="base")
        self.add_tool(output_formatter_instance, branch_id="base")
        # Create base branch
    
    def _create_base_branch(self):
        """Create the base branch that cannot be deleted"""
        base_decision_node = DecisionNode("base", "Choose appropriate action", self.model)
        
        self.branches["base"] = {
            "instruction": "Choose appropriate action based on user request",
            "parent_branch": None
        }
        self.decision_nodes["base"] = base_decision_node
        
    def add_tool(self,
                 tool_obj: Union[Tool, Callable],  # Renamed to avoid conflict
                 branch_id: str = "base",
                 instruction: str = None,
                 inputs: Dict[str, Any] = None):
        """
        Add a tool to a branch. Tool can be:
        1. A Tool instance (subclass of Tool)
        2. A function decorated with @tool
        3. A regular function (will be auto-wrapped)
        """
        if branch_id not in self.branches:
            raise ValueError(f"Branch '{branch_id}' does not exist")
        
        # Handle different tool types
        if isinstance(tool_obj, Tool):
            tool_instance = tool_obj
        elif callable(tool_obj):
            # Check if it's already decorated (has Tool-like attributes)
            if hasattr(tool_obj, 'name') and hasattr(tool_obj, 'description'):
                tool_instance = tool_obj
            else:
                # Auto-wrap regular function using the tool decorator
                tool_instance = tool(tool_obj)  # This is your tool decorator
        else:
            raise ValueError("Tool must be a Tool instance or callable")
        
        # Override instruction/inputs if provided
        if instruction:
            tool_instance.description = instruction
        if inputs:
            tool_instance.inputs.update(inputs)
        
        # Add to decision node and registry
        self.decision_nodes[branch_id].add_tool_option(
            tool_instance.name,
            tool_instance,
            tool_instance.description
        )
        
        self.tools_registry[tool_instance.name] = {
            "tool": tool_instance,
            "branch_id": branch_id,
            "description": tool_instance.description
        }
        
        print(f"Added tool '{tool_instance.name}' to branch '{branch_id}'")


    def add_branch(self, 
               branch_id: str, 
               instruction: str, 
               parent_branch: str = "base", 
               description: str = None):
        """
        Add a new branch with its own DecisionNode.
        
        Args:
            branch_id: Unique identifier for the new branch
            instruction: Instructions for the DecisionNode in this branch
            parent_branch: Which branch this stems from (default: "base")
            description: Description shown when routing to this branch
        """
        
        # Validation
        if branch_id in self.branches:
            raise ValueError(f"Branch '{branch_id}' already exists")
        
        if parent_branch not in self.branches:
            raise ValueError(f"Parent branch '{parent_branch}' does not exist")
        
        if branch_id == "base":
            raise ValueError("Cannot create branch with reserved name 'base'")
        
        # Create new DecisionNode for this branch
        new_decision_node = DecisionNode(branch_id, instruction, self.model)
        
        # Store branch info and decision node
        self.branches[branch_id] = {
            "instruction": instruction,
            "parent_branch": parent_branch
        }
        self.decision_nodes[branch_id] = new_decision_node
        
        # Add this branch as option to parent's DecisionNode
        if description is None:
            description = f"Navigate to {branch_id} for specialized operations"
        
        self.decision_nodes[parent_branch].add_branch_option(branch_id, description)
        
        print(f"Added branch '{branch_id}' under parent '{parent_branch}'")

    def remove_branch(self, branch_id: str):
        """Remove a branch (except base)"""
        
        if branch_id == "base":
            raise ValueError("Cannot remove the base branch")
        
        if branch_id not in self.branches:
            raise ValueError(f"Branch '{branch_id}' does not exist")
        
        # Remove from parent's decision node options
        branch = self.branches[branch_id]
        parent_branch = branch["parent_branch"]
        
        if parent_branch and parent_branch in self.decision_nodes:
            # Remove this branch from parent's available branches
            if branch_id in self.decision_nodes[parent_branch].available_branches:
                del self.decision_nodes[parent_branch].available_branches[branch_id]
        
        # Remove all tools in this branch from global registry
        tools_to_remove = []
        for tool_name, tool_info in self.tools_registry.items():
            if tool_info["branch_id"] == branch_id:
                tools_to_remove.append(tool_name)
        
        for tool_name in tools_to_remove:
            del self.tools_registry[tool_name]
        
        # Remove branch and decision node
        del self.branches[branch_id]
        del self.decision_nodes[branch_id]
        
        print(f"Removed branch '{branch_id}' and all its tools")    

    async def run(self, user_prompt):
        """
        Async generator that yields Response objects step by step.
        """
        self.tree_data.update_user_prompt(user_prompt)
        self.tree_data.update_conversation_history("user", user_prompt)
        self.current_branch_node = [self.current_branch]

        while True:
            branch_to_use = self.current_branch_node[-1]
            decision_node = self.decision_nodes[branch_to_use]
            decision = await decision_node(self.tree_data)

            # # 👇 Yield status update for frontend
            # yield Response(
            #     type="status",
            #     data=[{"text": f"Decision: {decision.to_choose} -> {decision.fn_name}"}],
            #     frontend=True,
            # )

            if decision.to_choose == "branch":
                self.current_branch_node.append(decision.fn_name)

            elif decision.to_choose == "tool":
                tool = self.decision_nodes[branch_to_use].available_tools[decision.fn_name]["tool"]
                print("tool decided", tool)
                result_or_gen = tool(
                    self.tree_data,
                    inputs=decision.function_inputs,
                    model=self.model,
                )

                # 🔑 Case 1: tool is async generator (streams multiple responses)
                if hasattr(result_or_gen, "__aiter__"):
                    async for step in result_or_gen:
                        yield step
                        self.tree_data.update_memory(decision.fn_name, step)

                # 🔑 Case 2: tool is normal coroutine (returns once)
                else:
                    result = await result_or_gen
                    yield result
                    self.tree_data.update_memory(decision.fn_name, result)

                # 👇 Branch control flow (same as before)
                if decision.end_actions and branch_to_use != "base":
                    self.current_branch_node = ["base"]
                    continue
                elif decision.end_actions and branch_to_use == "base":
                    return
                elif decision.return_to_parent and branch_to_use == "base":
                    return
                elif decision.return_to_parent:
                    self.current_branch_node.pop()


if __name__ == "__main__":
    lm = dspy.LM('anthropic/claude-sonnet-4-20250514', api_key=os.getenv('ANTHROPIC_API_KEY'))
    wf = Workflow(model=lm)  # or whatever model you’re passing
    test_prompt = "use the python interpreter tool to calculate gross margin of sales rev = 100000 ; COGS = 1000"
    asyncio.run(wf.run(test_prompt))        