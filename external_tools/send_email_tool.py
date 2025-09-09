import dspy
from typing import List, Dict, Any
from objects import Tool, Response
from utils import ContextAndCall

class EmailCompositionSignature(dspy.Signature):
    """Compose a professional email based on user intent and context.
    
    The model should:
      1) Understand the user's email intent from their request
      2) Create appropriate subject line and body
      3) Determine recipient(s) from context or user specification
      4) Format as a professional, clear email
    """
    
    context: str = dspy.InputField(
        desc="Business context and any relevant background information"
    )
    user_prompt: str = dspy.InputField(
        desc="User's request for what email to send"
    )
    memory: str = dspy.InputField(
        desc="Previous conversation context and tool results"
    )
    conversation_history: List[Dict[str, str]] = dspy.InputField(
        desc="Previous messages between user and assistant"
    )
    previous_errors: str = dspy.InputField(
        desc="Previous email sending failures to avoid"
    )
    
    # Email-specific inputs
    recipient_hint: str = dspy.InputField(
        desc="Any hints about who should receive this email"
    )
    email_purpose: str = dspy.InputField(
        desc="The purpose/type of email (follow-up, request, notification, etc.)"
    )
    
    # Outputs
    recipient_email: str = dspy.OutputField(
        desc="Email address of the recipient"
    )
    subject: str = dspy.OutputField(
        desc="Clear, professional email subject line"
    )
    body: str = dspy.OutputField(
        desc="Well-formatted email body text"
    )
    reasoning: str = dspy.OutputField(
        desc="Brief explanation of email composition choices"
    )