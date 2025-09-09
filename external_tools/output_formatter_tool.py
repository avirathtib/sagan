import dspy
from typing import List, Dict, Any
from objects import Tool, Response
from utils import ContextAndCall

class OutputFormattingSignature(dspy.Signature):
    """Turn agent state + guidance into a clean, user-facing text reply.

    The model should:
      1) Read the business/DB context and the conversation so far
      2) Consider prior tool results in `memory` and avoid repeating past mistakes in `previous_errors`
      3) Follow the `guidance` about what to present and in which style
      4) Produce a single, well-structured, markdown-safe text answer for the UI
    """

    # --- Rich inputs mirrored from your SQL tool pattern ---
    context: str = dspy.InputField(
        desc="Full business/domain context or DB schema summary relevant to this turn"
    )
    user_prompt: str = dspy.InputField(
        desc="The user's most recent natural-language request"
    )
    memory: str = dspy.InputField(
        desc="Formatted memory from previous tool executions, including results and descriptions"
    )
    conversation_history: List[Dict[str, str]] = dspy.InputField(
        desc="Previous messages between user and assistant: [{'role': 'user'|'assistant', 'content': str}]"
    )
    # available_branches: Dict[str, str] = dspy.InputField(
    #     desc="Available branches to navigate to: {'branch_name': 'what this branch handles'}"
    # )
    # available_tools: Dict[str, Dict[str, Any]] = dspy.InputField(
    #     desc="Available tools with their descriptions and input requirements: {'tool': {'description': str, 'inputs': dict}}"
    # )
    previous_errors: str = dspy.InputField(
        desc="Failures by agent/tool name to avoid repeating mistakes"
    )

    # --- The key steering signal for the formatter ---
    guidance: str = dspy.InputField(
        desc=(
            "Specific guidance for formatting: tone, target audience, key bullets to include, "
            "what to summarize/emphasize, whether to use markdown, and any callouts."
        )
    )

    # --- What this module should produce ---
    output_text: str = dspy.OutputField(
        desc="Single, polished text explaining data/input as guidance provided by input."
    )


class OutputFormatterTool(Tool):
    """Formats a clean natural-language response from the agent state and guidance.

    Usage: downstream branches can call this to turn raw results or reasoning
    into a single user-facing message with consistent style and structure.
    """

    def __init__(self, model):
        super().__init__(
            name="format_output",
            description=(
                "Generate a polished, markdown-friendly text response based on the current context, "
                "memory, conversation history, and explicit formatting guidance."
            ),
            inputs={
                "guidance": {
                    "type": str,
                    "description": "How to present the answer (tone, audience, sections, bullets, etc.)",
                    "required": True,
                }
            },
        )
        self.model = model

    async def __call__(self, tree_data, inputs: Dict[str, Any], **kwargs) -> Response:
        print("DEBUG: Starting OutputFormatterTool...")
        print(f"DEBUG: Inputs received: {inputs}")
        try:
            guidance = inputs["guidance"]
            print(f" DEBUG: Guidance: {guidance}")

            # Build the DSPy module with full tree_data (which should contain context, memory, etc.)
            print(" DEBUG: Creating output formatting module...")
            formatter_module = ContextAndCall(OutputFormattingSignature, tree_data)

            print("DEBUG: Calling formatter forward...")
            prediction = await formatter_module.aforward(
                available_tools={},
                available_branches={},
                guidance=guidance,
                lm=self.model,
            )
            print(f"✅ DEBUG: Formatting completed. Prediction: {prediction}")

            # formatted_text = prediction.formatted_text or ""
            # title = getattr(prediction, "title", "") or "Response"
            # tone = getattr(prediction, "tone", "") or "unspecified"
            # highlights = getattr(prediction, "highlights", None) or []

            # Create a frontend-friendly text Response
            # metadata = {
            #     "title": title,
            #     "tone": tone,
            #     "highlights": highlights,
            #     "formatter_guidance": guidance,
            # }

            response = Response(
                type="text",
                data=[{"text": prediction.output_text}],
                frontend=True,
                metadata={},
                description="",
            )

            # print(f"✅ DEBUG: Response created with title '{title}', tone '{tone}'.")
            # print("\U0001F4AC DEBUG: About to yield formatted response...")
            yield response
            print("✅ DEBUG: Formatted response yielded successfully")

        except Exception as e:
            import traceback
            print(f"❌ DEBUG: Exception occurred in OutputFormatterTool: {type(e).__name__}: {e}")
            print(f"❌ DEBUG: Traceback: {traceback.format_exc()}")

            # Provide a graceful fallback so the agent can still show something in UI
            fallback_text = (
                "I couldn't format the output just now. Here's what I attempted based on the guidance: \n\n"
                f"**Guidance provided:** {inputs.get('guidance', '')}\n\n"
                "Please try again or adjust the guidance."
            )

            yield Response(
                type="text",
                data=[{"text": fallback_text}],
                frontend=True,
                metadata={"error": True, "formatter_guidance": inputs.get("guidance", "")},
                description="Output formatting failed",
            )
