from dspy.primitives.module import Module
from workflow.helper_objects import Memory
import copy
import dspy
import json
from typing import Dict, Any

class ContextAndCall(Module):
    def __init__(self, signature, tree_data):
        super().__init__()
        self.tree_data = copy.copy(tree_data)
        self.predict = dspy.Predict(signature)
    
    def format_memory(self, memory: Memory):
        if not memory.memory:
            return "No previous actions taken."
        
        memory_formatted = ""
        for item in memory.memory:
            memory_formatted += f"{item['ordering_number']}: {item['agent_name']}\n"
            memory_formatted += f"Description: {item['description']}\n"
            memory_formatted += f"Result: {str(item['data_from_agent_call'])}...\n\n"
        return memory_formatted
    
    def format_failures(self) -> str:
        if not self.tree_data.failures:
            return "No previous failures recorded."
        
        failures_formatted = ""
        for failure in self.tree_data.failures:
            error = failure['error']
            timestamp = failure['timestamp'].strftime("%Y-%m-%d %H:%M:%S")
            failures_formatted += f"Failed Agent: {error.agent_name}\n"
            failures_formatted += f"Error: {error.error_message}\n"
            failures_formatted += f"Timestamp: {timestamp}\n\n"
        return failures_formatted
    
    async def aforward(self, 
                      available_tools: Dict[str, Any] = None, 
                      available_branches: Dict[str, str] = None, 
                      guidance = None,
                      chart_type = None,
                      **kwargs):
        """Call with auto-injected context. Tools and branches are optional."""
        
        # Set defaults for optional parameters
        
        
        kwargs.update({
            "context": self.tree_data.context,
            "user_prompt": getattr(self.tree_data, 'user_prompt', ''),
            "memory": self.format_memory(self.tree_data.memory),
            "conversation_history": self.tree_data.conversation_history,
            "previous_errors": self.format_failures(),
            
        })

        if available_tools is not None:
            kwargs["available_tools"] = available_tools
        if available_branches is not None:
            kwargs["available_branches"] = available_branches
        
        if guidance is not None:
            kwargs["guidance"] = guidance

        if chart_type is not None: 
            kwargs["chart_type"] = chart_type
        # with open('kwargs.json', 'w') as f:
        #     json.dump(kwargs, f)
        
        return await self.predict.acall(**kwargs)