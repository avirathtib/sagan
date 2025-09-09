from typing import Any, List, Dict
import dspy

class DecisionPrompt(dspy.Signature):
    """
    <role>
    You are the Master Orchestrator for a data analysis workflow. You decompose the user’s request into incremental steps, route work to specialized agents, and keep state across steps until the task is done.

    <operating loop>
    - Analyze the user query, overall context, history of results through memory, conversation history, errors and available routing options. Extract intent, required metrics/dimensions, filters, comparisons, and output form (table/chart/narrative). Find knowledge gaps that block progress (schema unknowns, missing filters, ambiguous metric definitions).
    - Plan the next minimal step that moves the task forward. Choose one action that is necessary now; avoid batching.
    - Instruct the selected tool or branch with concise, precise guidance and an expected output schema.
    - Review the returned result: check against success criteria, and update plan.
    - Repeat until you have enough to complete the task, then complete

    <important>
    - You are encouraged to breakdown the possible wokflow to step by step instructions to perform them in incremental order rather than work on tasks as a one shot whole process.
    - Suppose the question asked is a huge query or requires multiple tables processing, it would be recommended that you break down the problem into smaller parts. 
    - Bias against trying to performing the entire operation as one query - this leads to super low reliability and we can't afford this since it affects monetary decisions.
    - When guiding a subagent and you want it to use some information that's come through from a previous agent call, explicitly mention it since all information is shared with agents.
    - At every step, we're also streaming intermediary results to the user, so you must also decide what would be the best way to display the result from that particular step to the user. For example, for some SQL queries a table might be the best response while it can be text for others. Mention the expected return type in your guidance to the subagent as well.
    - Remember to use the output tool post when using interpreter tool with the appropriate guidance so as to get a well made output legible to the end-user.
    """
    # Input fields
    context: str = dspy.InputField(
        desc = "Context of the entire DB schema for the business basis of which table queries or charts must be made"
    ) 
    user_prompt: str = dspy.InputField(
        desc="User's prompt to which reason this decision is being taken"
    )
    memory: str = dspy.InputField(
        desc="Formatted memory from previous tool executions, including results and descriptions"
    )
    conversation_history: List[Dict[str, str]] = dspy.InputField(
        desc="Previous messages between user and assistant: [{'role': 'user'|'assistant', 'content': str}]"
    )
    available_branches: Dict[str, str] = dspy.InputField(
        desc="Available branches to navigate to: {'branch_name': 'description of what this branch handles'}"
    )
    available_tools: Dict[str, Dict[str, Any]] = dspy.InputField(  # Updated type
        desc="Available tools with their descriptions and input requirements: {'tool_name': {'description': str, 'inputs': dict}}"
    )
    previous_errors: str = dspy.InputField(
        desc="Previous failures by agent/tool name to avoid repeating mistakes"
    )
    
    # Output fields
    to_choose: str = dspy.OutputField(
        desc="Type of action to take: either 'branch' to navigate to different branch, or 'tool' to execute a tool"
    )
    guidance: str = dspy.OutputField(
        desc="Specific guidance for the chosen branch or tool - what should be accomplished or how it should be used"
    )
    reasoning: str = dspy.OutputField(
        desc="Explanation of why this branch/tool was chosen over alternatives"
    )
    fn_name: str = dspy.OutputField(
        desc="Exact name of the branch or tool to use - must match exactly from available_branches or available_tools"
    )
    function_inputs: Dict[str, Any] = dspy.OutputField(  # New field
        desc="Input parameters for the chosen tool based on its input schema. Empty dict {} if choosing a branch or if tool has no inputs."
    )
    return_to_parent: bool = dspy.OutputField(
        desc="Evaluate if all work possible within this branch has been done and should return to parent branch. Must be false for base branch."
    )
    end_actions: bool = dspy.OutputField(
        desc="Evaluate if the end goal for this query has been achieved and the user's query has been answered appropriately"
    )