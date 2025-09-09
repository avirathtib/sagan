import json
import uuid
import os
from datetime import datetime
from typing import Dict, Optional, List, Any
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

from api.app.websocket_handler import AnalysisWebSocketHandler
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from gmail import GmailService
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials

app = FastAPI(title="AI Data Search API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class NewConversationResponse(BaseModel):
    success: bool
    conversation_id: str = None
    error: str = None

class GmailAuthResponse(BaseModel):
    success: bool
    auth_url: str = None
    error: str = None

class GmailStatusResponse(BaseModel):
    connected: bool
    authenticated: bool
    service_available: bool
    user_email: str = None
    error: str = None

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.handlers: Dict[str, AnalysisWebSocketHandler] = {}
        self.conversations: Dict[str, dict] = {}
        self.workflow_states: Dict[str, Any] = {}  # Store workflow instances

    async def initialize_conversation(self, conversation_id: str):
        """Initialize a new conversation with default settings"""
        self.conversations[conversation_id] = {
            "id": conversation_id,
            "created_at": datetime.now().isoformat(),
            "status": "initialized",
            "metadata": {},
            "history": [],  # Store conversation history
            "workflow_state": None  # Will store serialized workflow state
        }

    async def connect(self, websocket: WebSocket, conversation_id: str):
        await websocket.accept()
        handler = AnalysisWebSocketHandler(websocket, conversation_id, self)
        self.active_connections[conversation_id] = websocket
        self.handlers[conversation_id] = handler
        return handler

    def disconnect(self, conversation_id: str):
        self.active_connections.pop(conversation_id, None)
        self.handlers.pop(conversation_id, None)

    def get_handler(self, conversation_id: str) -> AnalysisWebSocketHandler:
        return self.handlers.get(conversation_id)

    def conversation_exists(self, conversation_id: str) -> bool:
        return conversation_id in self.conversations
    
    def add_message_to_history(self, conversation_id: str, message_type: str, content: Any, is_user: bool = False):
        """Add a message to conversation history"""
        if conversation_id in self.conversations:
            message = {
                "id": str(uuid.uuid4()),
                "type": message_type,
                "content": content,
                "is_user": is_user,
                "timestamp": datetime.now().isoformat()
            }
            self.conversations[conversation_id]["history"].append(message)
    
    def get_conversation_history(self, conversation_id: str) -> List[dict]:
        """Get conversation history"""
        if conversation_id in self.conversations:
            return self.conversations[conversation_id]["history"]
        return []
    
    def store_workflow_state(self, conversation_id: str, workflow_instance: Any):
        """Store workflow state for later retrieval"""
        if conversation_id in self.conversations:
            self.workflow_states[conversation_id] = workflow_instance
            # Also store basic state info in conversation
            self.conversations[conversation_id]["workflow_state"] = {
                "user_id": workflow_instance.user_id,
                "conversation_id": workflow_instance.conversation_id,
                "current_branch": workflow_instance.current_branch,
                "branches_count": len(workflow_instance.branches),
                "tools_count": len(workflow_instance.tools_registry)
            }
    
    def get_workflow_state(self, conversation_id: str) -> Any:
        """Get stored workflow state"""
        return self.workflow_states.get(conversation_id)
    
    def update_conversation_status(self, conversation_id: str, status: str):
        """Update conversation status"""
        if conversation_id in self.conversations:
            self.conversations[conversation_id]["status"] = status
            self.conversations[conversation_id]["updated_at"] = datetime.now().isoformat()
    
    def get_conversation_info(self, conversation_id: str) -> Optional[dict]:
        """Get full conversation information"""
        return self.conversations.get(conversation_id)
    
    def get_all_conversations(self) -> List[dict]:
        """Get list of all conversations with summary info"""
        conversations = []
        for conv_id, conv_data in self.conversations.items():
            # Find first user message for title generation
            first_message = None
            message_count = len(conv_data.get("history", []))
            last_activity = None
            
            for msg in conv_data.get("history", []):
                if msg.get("is_user") and msg.get("type") == "user_message":
                    first_message = msg.get("content", "")
                    break
            
            # Get last activity timestamp
            if conv_data.get("history"):
                last_activity = conv_data["history"][-1].get("timestamp")
            
            conversation_summary = {
                "id": conv_id,
                "created_at": conv_data.get("created_at"),
                "first_message": first_message or "New conversation",
                "status": conv_data.get("status", "initialized"),
                "message_count": message_count,
                "last_activity": last_activity or conv_data.get("updated_at") or conv_data.get("created_at")
            }
            conversations.append(conversation_summary)
        
        # Sort by last activity (most recent first)
        conversations.sort(key=lambda x: x.get("last_activity", ""), reverse=True)
        return conversations


manager = ConnectionManager()

# Gmail service and OAuth configuration
gmail_service = GmailService()
GMAIL_REDIRECT_URI = "http://localhost:8000/auth/callback"
user_sessions = {}  # Store user credentials temporarily


@app.get("/")
async def root():
    return {"message": "AI Data Search API", "status": "running"}

@app.post("/api/new-conversation", response_model=NewConversationResponse)
async def create_new_conversation():
    try:
        conversation_id = str(uuid.uuid4())
        await manager.initialize_conversation(conversation_id)
        
        return NewConversationResponse(
            success=True,
            conversation_id=conversation_id
        )
    except Exception as error:
        print(f"Error initializing conversation: {error}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initialize conversation: {str(error)}"
        )

@app.get("/api/conversation/{conversation_id}")
async def get_conversation(conversation_id: str):
    """Get conversation information and history"""
    try:
        if not manager.conversation_exists(conversation_id):
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        conversation_info = manager.get_conversation_info(conversation_id)
        return {
            "success": True,
            "conversation": conversation_info
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get conversation: {str(e)}")

@app.get("/api/conversation/{conversation_id}/history")
async def get_conversation_history(conversation_id: str):
    """Get conversation history"""
    try:
        if not manager.conversation_exists(conversation_id):
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        history = manager.get_conversation_history(conversation_id)
        return {
            "success": True,
            "history": history,
            "count": len(history)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get conversation history: {str(e)}")

@app.get("/api/conversations")
async def get_all_conversations():
    """Get list of all conversations with summary info"""
    try:
        conversations = manager.get_all_conversations()
        return {
            "success": True,
            "conversations": conversations,
            "count": len(conversations)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get conversations: {str(e)}")


@app.get("/api/gmail/auth", response_model=GmailAuthResponse)
async def gmail_auth():
    """Start Gmail OAuth flow"""
    try:
        flow = Flow.from_client_secrets_file(
            "credentials.json",
            scopes=["https://www.googleapis.com/auth/gmail.compose"],
            redirect_uri=GMAIL_REDIRECT_URI
        )
        
        auth_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true'
        )
        
        # Store state for verification
        user_sessions[state] = {"flow": flow}
        
        return GmailAuthResponse(
            success=True,
            auth_url=auth_url
        )
    except Exception as e:
        return GmailAuthResponse(
            success=False,
            error=str(e)
        )
 
@app.get("/auth/callback")
async def gmail_callback(request: Request):
    """Handle Gmail OAuth callback"""
    try:
        # Get the full URL with query parameters
        authorization_response = str(request.url)
        
        # Extract state from query parameters
        state = request.query_params.get('state')
        
        if not state or state not in user_sessions:
            raise HTTPException(status_code=400, detail="Invalid state parameter")
        
        # Get the flow from session
        flow = user_sessions[state]["flow"]
        
        # Exchange authorization code for credentials
        flow.fetch_token(authorization_response=authorization_response)
        
        # Store credentials in session
        user_sessions[state]["credentials"] = flow.credentials
        
        # Initialize Gmail service with new credentials
        gmail_service.credentials = flow.credentials
        gmail_service.service = None  # Will be rebuilt on next connection check
        
        return RedirectResponse(url="http://localhost:3000")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Authentication failed: {str(e)}")

@app.get("/api/gmail/status", response_model=GmailStatusResponse)
async def gmail_status():
    """Check Gmail connection status"""
    try:
        # Try to authenticate first if not already done
        if not gmail_service.credentials:
            return GmailStatusResponse(
                connected=False,
                authenticated=False,
                service_available=False,
                error="Not authenticated - call /api/gmail/auth first"
            )
        
        # Build service if needed
        if not gmail_service.service:
            from googleapiclient.discovery import build
            gmail_service.service = build("gmail", "v1", credentials=gmail_service.credentials)
        
        # Check connection
        status = gmail_service.check_connection()
        
        return GmailStatusResponse(
            connected=status["connected"],
            authenticated=status["authenticated"],
            service_available=status["service_available"],
            user_email=status["user_email"],
            error=status["error"]
        )
        
    except Exception as e:
        return GmailStatusResponse(
            connected=False,
            authenticated=False,
            service_available=False,
            error=str(e)
        )

# Testing API Routes
@app.post("/api/research-and-mail")
async def research_and_mail(request: dict):
    """Run research and mail tool with authenticated Gmail service"""
    try:
        if not gmail_service.is_connected():
            raise HTTPException(status_code=400, detail="Gmail not authenticated - call /api/gmail/auth first")
        
        # Import and create tool with authenticated service
        from external_tools.research_and_mail_tool import ResearchAndMailTool
        
        research_tool = ResearchAndMailTool(
            model=None,  # You can pass your model here if needed
            gmail_service=gmail_service  # Your authenticated service!
        )
        
        # Get contacts from request
        contacts = request.get("contacts", [])
        
        # Run the tool
        result = await research_tool(
            tree_data=None,
            inputs={"contacts": contacts}
        )
        
        return {
            "success": True, 
            "results": result.data,
            "total_processed": len(result.data)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Research and mail failed: {str(e)}")

@app.websocket("/ws/{conversation_id}")
async def websocket_endpoint(websocket: WebSocket, conversation_id: str):
    handler = await manager.connect(websocket, conversation_id)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            await handler.handle_message(message)
    except WebSocketDisconnect:
        manager.disconnect(conversation_id)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
