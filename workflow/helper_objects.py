import json
from typing import Any, Dict, List 
from helper_functions import to_json_string
from objects import Response, Error
from datetime import date, datetime

class Memory:
    def __init__(self, memory: List[Dict[str, Any]] = None):
        if memory is None: 
            memory = []
        self.memory = memory
        self.ordering_number = 1

    def add_to_memory(self, agent_name: str, response: Response):
        to_add_object = {
            "ordering_number" : self.ordering_number,
            "agent_name" : agent_name,
            "data_from_agent_call" : response.data,
            "description" : response.description,
            "response_type": response.type,

        }
        self.memory.append(to_add_object)
        self.ordering_number = self.ordering_number + 1

    def to_json(self, object_to_sanitize: Dict):
        return to_json_string(object_to_sanitize)

             

class TreeData:
    def __init__(self, user_prompt = "", max_count: int = 5):
        self.user_prompt = user_prompt
        self.memory = Memory()
        self.conversation_history = [] #in the form of {role: user, content: message} internally
        self.failures = []
        self.step_count = 0
        self.max_count = max_count
        self.context = None
        with open('/Users/apple/Desktop/builds/ai-data-search-py/preprocessing/context.json', mode='r') as f:
            self.context = json.dumps(json.load(f))
        # self.task_ledger = []
        # self.progress_ledger = []
    
    def update_user_prompt(self, user_prompt: str):
        self.user_prompt = user_prompt

    def update_memory(self, agent_name: str, response: Response):
        self.memory.add_to_memory(agent_name, response)

    def update_conversation_history(self, role: str, content: str):
        self.conversation_history.append({"role": role, "content": content})

    def update_failures(self, agent_name: str, failure: str):
        error = Error(agent_name, failure)
        self.failures.append({"error": error, "timestamp": datetime.now()})

    def update_step_count(self):
        self.step_count = self.step_count + 1      


