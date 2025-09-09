# planner_signature.py
import dspy
import json
from typing import Dict, Any, List, Optional
from utils import ContextAndCall
from objects import Tool, Response
import inspect
from collections.abc import Awaitable
from dspy import PythonInterpreter  # requires Deno installed locally

class PythonSnippetSignature(dspy.Signature):
    """
    Plan a safe Python snippet to compute any value/values as required to be produced according to the guidance given to you. 
    Optimize to do in the best way possible without computing with extra variables and output only what's asked and not anything more than that.
    """
    context: str = dspy.InputField(desc="DB/business schema, column names, metric definitions, units, etc.")
    user_prompt: str = dspy.InputField(desc="User's original request")
    memory: str = dspy.InputField(desc="Formatted memory with previous tool outputs (tables, aggregates)")
    conversation_history: List[Dict[str, str]] = dspy.InputField(desc="[{role, content}, ...]")
    available_branches: Dict[str, str] = dspy.InputField(desc="{'branch_name': 'what it handles'}")
    available_tools: Dict[str, Dict[str, Any]] = dspy.InputField(desc="{'tool': {'description': str, 'inputs': dict}}")
    previous_errors: str = dspy.InputField(desc="Failures from prior turns to avoid")
    guidance: str = dspy.InputField(desc="What to compute (e.g., 'gross margin % for July 2025')")

    python_code: str = dspy.OutputField(desc=(
        "Executable Python snippet. It must read required variables from the injected namespace. "
        "The *last expression* should evaluate to the final result (scalar/array/dict). "
        "Raise ValueError with a helpful message for invalid inputs."
        "The values being returned and usable by the python snippet here must be same as those in the output variables headers"
    ))
    expected_variables: Dict[str, Any] = dspy.OutputField(desc="Ordered dictionary of all the variable names and values that are referenced in the python code - only use if python code doesn't already have absolute values")
    output_variables: List[str] = dspy.OutputField(desc="List of all the variable names/headers that can be subscriptable from the result variable")
    purpose: str = dspy.OutputField(desc="Short rationale of how this snippet fulfills the guidance.")

# python_interpreter_tool.py


class PythonInterpreterTool(Tool):
    """
    Plans a Python computation with a DSPy Signature, then executes it inside
    dspy.PythonInterpreter (Pyodide sandbox) and returns the result. Very useful to do any kind of computation work like basic 
    arithmetic and complex mathematical work on top of that too.

    Inputs:
      - guidance: natural language instruction of what to compute
    """
    def __init__(self, model, tree_data=None):
        super().__init__(
            name="run_python_interpreter",
            description="Plan a Python snippet from guidance and execute it in a sandboxed interpreter.",
            inputs={
                "guidance": {"type": str, "description": "What to compute", "required": True},
            }
        )
        self.model = model
        self.tree_data = tree_data  # whatever you pass to ContextAndCall in your stack
        # self.planner_signature_cls = planner_signature_cls
    

    async def __call__(self, tree_data, inputs: Dict[str, Any], **kwargs):
        print("🚀 DEBUG: PythonInterpreterTool start")
        print(f"🔍 DEBUG: Inputs: {inputs}")
        try:
            result = None
            guidance: str = inputs["guidance"]
            interp_generation_module = ContextAndCall(PythonSnippetSignature, tree_data)
            prediction = await interp_generation_module.aforward(
                    available_tools={},  # No tools needed for SQL generation
                    available_branches={},  # No branches needed
                    guidance=guidance,
                    lm=self.model
                )
            # print("prediction", prediction)
            metadata = {"description": prediction.purpose}
            with PythonInterpreter() as interp:
                    # Execute the snippet with injected variables
                    result = interp(prediction.python_code, variables=prediction.expected_variables)
                    print("rsult is ", result)
                    print("type", type(result))
                    if inspect.isawaitable(result) or isinstance(result, Awaitable):
                        result = await result
                    else:
                        result = result
                    
                    if isinstance(result, str):
                        try:
                            parsed = json.loads(result)
                            result = parsed
                            print("Parsed JSON result into Python object.")
                        except Exception:
                            # not JSON — keep string but surface a clear error instead of TypeError
                            raise ValueError(
                                "Interpreter returned a string (not dict/list). "
                                "Either return a Python dict/list from the snippet or return JSON that can be parsed."
                            )

                    # If result is a list (e.g., list of records) and prediction.output_variables expects multiple keys,
                    # wrap it under a single name so downstream code can access it.
                    if isinstance(result, list):
                        # prefer a canonical key name that matches planner expectations, e.g. 'final_result'
                        result = {"final_result": result}

                    # Now ensure it's a mapping for the following loop
                    if not isinstance(result, dict):
                        raise ValueError(f"Interpreter returned unsupported type {type(result)}; expected dict or list-of-dicts.")

                    for variable in prediction.output_variables:
                        if variable not in result:
                            raise KeyError(f"Expected output variable '{variable}' not present in interpreter result keys: {list(result.keys())}")
                        print(result[variable], f"this is {variable}")
                    
            if result is not None:
                for variable in prediction.output_variables:
                        print(result[variable], f"this is {variable}")
                response = Response(
                    type="interpreter",
                    data = result,
                    frontend=False,
                    metadata=metadata,
                    description=prediction.purpose

                )
                yield response
        except Exception as e:
            print("thesee are the exceptions:", e)
             
            yield Response(
                type="text",
                data=[{"text": f"Interpreter execution failed: {str(e)}"}],
                frontend=True,
                metadata={"error": True, "guidance": guidance},
                description="Interpreter tool execution failed"
            )


