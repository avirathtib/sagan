import json
import asyncio
import os
from typing import Dict, Any, Optional
from fastapi import WebSocket
from workflow.workflow import Workflow
import dspy

class AnalysisWebSocketHandler:
    def __init__(self, websocket: WebSocket, conversation_id: str, connection_manager=None):
        self.websocket = websocket
        self.conversation_id = conversation_id
        self.connection_manager = connection_manager

    async def send_message(self, message: Dict[str, Any]):
        await self.websocket.send_text(json.dumps(message))

    async def send_status(self, status: str, details: Optional[str] = None):
        message = {
            "type": "status",
            "status": status,
            "conversation_id": self.conversation_id
        }
        if details:
            message["details"] = details
        await self.send_message(message)

    async def send_data_chunk(self, chunk: Any, chunk_type: str = "data"):
        message = {
            "type": "data_chunk",
            "chunk_type": chunk_type,
            "data": chunk,
            "conversation_id": self.conversation_id
        }
        await self.send_message(message)

    async def send_error(self, error: str, error_code: Optional[str] = None):
        message = {
            "type": "error",
            "error": error,
            "conversation_id": self.conversation_id
        }
        if error_code:
            message["error_code"] = error_code
        await self.send_message(message)

    async def send_completion(self, summary: Optional[str] = None):
        message = {
            "type": "complete",
            "conversation_id": self.conversation_id
        }
        if summary:
            message["summary"] = summary
        await self.send_message(message)

    async def process_analyze_request(self, query: str, options: Optional[Dict[str, Any]] = None):
        try:
            await self.send_status("initializing", "Starting data analysis...")
            await asyncio.sleep(0.2)

            await self.send_status("processing", "Processing query...")
            await asyncio.sleep(0.2)

            # Replace with real workflow later
            results = await self.simulate_analysis(query, options or {})

            await self.send_status("streaming", "Streaming results...")

            for result_chunk in results:
                await self.send_data_chunk(result_chunk, "analysis_result")
                await asyncio.sleep(0.1)

            await self.send_completion("Analysis completed successfully")

        except Exception as e:
            await self.send_error(f"Analysis failed: {str(e)}", "ANALYSIS_ERROR")

    async def simulate_analysis(self, query: str, options: Dict[str, Any]):
        results = []
        for i in range(5):
            await asyncio.sleep(0.3)  # simulate processing
            result = {
                "chunk_id": i + 1,
                "query": query,
                "result": f"Analysis result {i + 1} for: {query}",
                "confidence": 0.8 + (i * 0.04),
                "metadata": {
                    "processing_time": f"{(i + 1) * 0.3}s",
                    "options": options
                }
            }
            results.append(result)
        return results

    async def handle_message(self, message: Dict[str, Any]):
        print("this is the message", message)
        message_type = message.get("type")

        if message_type == "analyze":
            query = message.get("query", "")
            options = message.get("options", {})
            
            # Store user message in history
            if self.connection_manager:
                self.connection_manager.add_message_to_history(
                    self.conversation_id, "user_message", query, is_user=True
                )
            
            # Check if we have an existing workflow state
            existing_workflow = None
            if self.connection_manager:
                existing_workflow = self.connection_manager.get_workflow_state(self.conversation_id)
            
            # Create or reuse workflow
            if existing_workflow:
                print(f"Resuming existing workflow for conversation {self.conversation_id}")
                wf = existing_workflow
            else:
                print(f"Creating new workflow for conversation {self.conversation_id}")
                lm = dspy.LM('anthropic/claude-sonnet-4-20250514', api_key=os.getenv('ANTHROPIC_API_KEY'))
                wf = Workflow(conversation_id=self.conversation_id, model=lm)
                
                # Store the new workflow state
                if self.connection_manager:
                    self.connection_manager.store_workflow_state(self.conversation_id, wf)
            
            # Process the query
            response_messages = []
            async for response in wf.run(query):
                # every response from workflow is a Response object
                # convert it to dict before sending
                response_dict = response.to_dict()
                await self.send_message(response_dict)
                response_messages.append(response_dict)
            
            # Store AI responses in history
            if self.connection_manager:
                for resp in response_messages:
                    self.connection_manager.add_message_to_history(
                        self.conversation_id, "ai_response", resp, is_user=False
                    )
                
                # Update workflow state after processing
                self.connection_manager.store_workflow_state(self.conversation_id, wf)
                self.connection_manager.update_conversation_status(self.conversation_id, "active")

            await self.send_completion("Analysis completed successfully")

        elif message_type == "ping":
            await self.send_message({
                "type": "pong",
                "conversation_id": self.conversation_id,
                "timestamp": message.get("timestamp")
            })

        else:
            await self.send_error(f"Unknown message type: {message_type}", "INVALID_MESSAGE_TYPE")
