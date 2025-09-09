import os.path
import base64
from email.mime.text import MIMEText
from typing import Optional, Dict, Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# NOTE: changed scope so we can create drafts
SCOPES = ["https://www.googleapis.com/auth/gmail.compose"]

class GmailService:
    def __init__(self, credentials_file: str = "credentials.json", token_file: str = "token.json"):
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.service = None
        self.credentials = None
        
    def authenticate(self) -> bool:
        """Authenticate with Gmail API and return True if successful"""
        try:
            creds = None
            if os.path.exists(self.token_file):
                creds = Credentials.from_authorized_user_file(self.token_file, SCOPES)
            
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                    print("✓ Gmail credentials refreshed successfully")
                else:
                    if not os.path.exists(self.credentials_file):
                        print("✗ Gmail credentials file not found. Please add credentials.json")
                        return False
                    
                    flow = InstalledAppFlow.from_client_secrets_file(self.credentials_file, SCOPES)
                    creds = flow.run_local_server(port=0)
                    print("✓ Gmail authentication completed successfully")
                
                with open(self.token_file, "w") as token:
                    token.write(creds.to_json())
            
            self.credentials = creds
            self.service = build("gmail", "v1", credentials=creds)
            print("✓ Gmail service connection established")
            return True
            
        except Exception as e:
            print(f"✗ Gmail authentication failed: {str(e)}")
            return False
    
    def check_connection(self) -> Dict[str, Any]:
        """Check Gmail connection status and return detailed info"""
        status = {
            "connected": False,
            "authenticated": False,
            "service_available": False,
            "user_email": None,
            "error": None
        }
        
        try:
            if not self.credentials:
                status["error"] = "No credentials available"
                return status
            
            status["authenticated"] = True
            
            if not self.service:
                status["error"] = "Gmail service not initialized"
                return status
            
            status["service_available"] = True
            
            # Test connection by getting user profile
            profile = self.service.users().getProfile(userId='me').execute()
            status["connected"] = True
            status["user_email"] = profile.get('emailAddress')
            
            print(f"✓ Gmail connection successful - Connected as: {status['user_email']}")
            return status
            
        except HttpError as e:
            error_msg = f"Gmail API error: {e.status_code} - {e.error_details}"
            status["error"] = error_msg
            print(f"✗ {error_msg}")
            return status
        except Exception as e:
            error_msg = f"Connection check failed: {str(e)}"
            status["error"] = error_msg
            print(f"✗ {error_msg}")
            return status
    
    def is_connected(self) -> bool:
        """Simple boolean check for Gmail connection"""
        return self.check_connection()["connected"]
    
    def create_draft(self, to: str, subject: str, body: str) -> Optional[Dict[str, Any]]:
        """Create a draft email"""
        if not self.service:
            print("✗ Gmail service not available")
            return None
        
        try:
            msg = MIMEText(body)
            msg["to"] = to
            msg["from"] = "me"
            msg["subject"] = subject
            
            raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
            draft_body = {"message": {"raw": raw}}
            draft = self.service.users().drafts().create(userId="me", body=draft_body).execute()
            
            print(f"✓ Draft created successfully - ID: {draft.get('id')}")
            return draft
            
        except Exception as e:
            print(f"✗ Failed to create draft: {str(e)}")
            return None

def main():
    gmail = GmailService()
    
    print("Initializing Gmail service...")
    if gmail.authenticate():
        connection_status = gmail.check_connection()
        
        if connection_status["connected"]:
            print("\n=== Gmail Service Status ===")
            print(f"Status: Connected")
            print(f"Email: {connection_status['user_email']}")
            print(f"Service Available: {connection_status['service_available']}")
        else:
            print(f"\n✗ Connection failed: {connection_status.get('error', 'Unknown error')}")
    else:
        print("✗ Authentication failed")

if __name__ == "__main__":
    main()
