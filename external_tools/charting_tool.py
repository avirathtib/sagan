import os
import asyncpg
import dspy
from utils import ContextAndCall
from typing import List, Dict, Any
from objects import Tool, Response
from dotenv import load_dotenv
from pydantic import BaseModel
from pydantic.fields import Field
load_dotenv()

class BarChartData(BaseModel):
    x_labels: list[str | int | float] = Field(description="Labels for the x-axis")
    y_values: dict[str, list[int | float]] = Field(description="Values for the y-axis which should match the length of the x_labels")

class BarChart(BaseModel):
    title: str = Field(description="Title of the bar chart")
    data: BarChartData = Field(description="Data for the bar chart")
    label_for_x_axis: str = Field(description="Label for the x-axis")
    label_for_y_axis: str = Field(description="Label for the y-axis")
    description: str = Field(description="Description of the bar chart")

class BarChartSignature(dspy.Signature):
    """Generate a bar chart based on user guidance"""
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
    previous_errors: str = dspy.InputField(
        desc="Previous failures by agent/tool name to avoid repeating mistakes"
    )
    guidance: str = dspy.InputField(desc="Specific guidance for chart generation")

    charts: List[BarChart] = dspy.OutputField(desc="List of bar charts to be generated - create multiple charts only if it would suit the user's needs")
    overall_description: str = dspy.OutputField(desc="Overall description of the charts that will be generated")

class LineChartData(BaseModel):
    x_labels: list[str | int | float] = Field(description="Labels for the x-axis")
    y_values: Dict[str, list[int | float]] = Field(
        description="Dictionary where each key is the name of a line, "
                    "and the value is the list of y-values aligned with x_labels"
    )

class LineChart(BaseModel):
    title: str = Field(description="Title of the line chart")
    data: LineChartData = Field(description="Data for the line chart")
    label_for_x_axis: str = Field(description="Label for the x-axis")
    label_for_y_axis: str = Field(description="Label for the y-axis")
    description: str = Field(description="Description of the line chart")


class LineChartSignature(dspy.Signature):
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
    previous_errors: str = dspy.InputField(
        desc="Previous failures by agent/tool name to avoid repeating mistakes"
    )
    guidance: str = dspy.InputField(desc="Specific guidance for chart generation")

    charts: List[LineChart] = dspy.OutputField(desc="List of line charts to be generated - create multiple charts only if it would suit the user's needs")
    overall_description: str = dspy.OutputField(desc="Overall description of the charts that will be generated")


class ChartTool(Tool):
    def __init__(self, model):
        super().__init__(
            name="run_chart",
            description="Visualise data that exists in the environment - this tool can only output charts and needs to have some data in the environment to visualise. Picking it without data being available in the environment will usually lead to failure of the task.",
            inputs={
                "chart_type": {
                    "type": str,
                    "description": "Type of chart to generate - can output only 'bar' or 'line'",
                    "required": True
                },
                "guidance": {
                    "type": str,
                    "description": "Specific guidance as to how the char should be generated including some guidance on useful data that should be included",
                    "required": True
                }
            }
        )
        self.model = model
        
    async def __call__(self, tree_data, inputs, **kwargs):
        try:
            chart_type = inputs["chart_type"]
            guidance = inputs["guidance"]

            chart_generation_module = ContextAndCall(BarChartSignature if chart_type == "bar" else LineChartSignature, tree_data)
            prediction = await chart_generation_module.aforward(
                guidance=guidance,
                lm = self.model
            )

            metadata = {
                "chart_type": chart_type,
                "overall_description": prediction.overall_description,
            }

            response = Response(
                    type="chart",
                    data=prediction.charts,
                    frontend=True,
                    metadata=metadata,
                    description=f"{prediction.overall_description}."
                )
            print(f"this is the response that i got from the chart generation module {response}")
            yield response    


        except Exception as e:
            yield Response(
                type="text",
                data=[{"text": f"Chart generation failed: {str(e)}"}],
                frontend=True,
                metadata={"error": True},
                description="Chart tool execution failed"
            )

