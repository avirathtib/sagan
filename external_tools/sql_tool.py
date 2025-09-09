import os
import re
from unittest import result
import asyncpg
import dspy
from utils import ContextAndCall
from typing import List, Dict, Any
from objects import Tool, Response
from dotenv import load_dotenv
load_dotenv()

class SQLGenerationSignature(dspy.Signature):
    """Generate SQL query and predict result structure based on user guidance"""
    
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
    guidance: str = dspy.InputField(desc="Specific guidance for SQL generation")

    sql_query: str = dspy.OutputField(desc="Generated SQL query (SELECT only)")
    expected_columns: List[str] = dspy.OutputField(desc="Expected column names in the result")
    column_descriptions: Dict[str, str] = dspy.OutputField(desc="Description of what each column represents")
    query_purpose: str = dspy.OutputField(desc="Brief description of what this query accomplishes and why this query is being run in response to guidance provided by the Decision Node")

class SQLTool(Tool):
    def __init__(self, model):
        super().__init__(
            name="run_sql",
            description="Generate and execute SQL queries based on natural language guidance",
            inputs={
                "guidance": {
                    "type": str,
                    "description": "What you want to calculate or retrieve from the database",
                    "required": True
                }
            }
        )
        self.model = model
        self.connection_pool = None
    
    async def _get_connection(self):
        """Initialize connection pool if not exists"""
        print("🔍 DEBUG: Attempting to create connection pool...")
        
        # Debug environment variables
        host = os.getenv("PG_HOST")
        port = int(os.getenv("PG_PORT", 5432))
        database = os.getenv("PG_DB")
        user = os.getenv("PG_RO_USER")
        password = os.getenv("PG_RO_PW")
        
        print(f"🔍 DEBUG: Connection params - Host: {host}, Port: {port}, DB: {database}, User: {user}")
        print(f"🔍 DEBUG: Password set: {'Yes' if password else 'No'}")
        
        if self.connection_pool is None:
            try:
                self.connection_pool = await asyncpg.create_pool(
                    host=host,
                    port=port,
                    database=database,
                    user=user,
                    password=password,
                    ssl="require",
                    max_size=20,
                    command_timeout=30
                )
                print("✅ DEBUG: Connection pool created successfully")
            except Exception as e:
                print(f"❌ DEBUG: Failed to create connection pool: {e}")
                raise
        return self.connection_pool
    
    
    async def __call__(self, tree_data, inputs: Dict[str, Any], **kwargs) -> Response:
        print("🚀 DEBUG: Starting SQL tool execution...")
        print(f"🔍 DEBUG: Inputs received: {inputs}")
        
        try:
            guidance = inputs["guidance"]
            print(f"🔍 DEBUG: Guidance: {guidance}")
            
            # Use ContextAndCall for SQL generation with full context
            print("🔍 DEBUG: Creating SQL generation module...")
            sql_generation_module = ContextAndCall(SQLGenerationSignature, tree_data)
            
            print("🔍 DEBUG: Calling SQL generation forward...")
            prediction = await sql_generation_module.aforward(
                available_tools={},  # No tools needed for SQL generation
                available_branches={},  # No branches needed
                guidance=guidance,
                lm=self.model
            )
            print(f"✅ DEBUG: SQL generation completed. Prediction: {prediction}")
            
            sql_query = prediction.sql_query
            print(f"🔍 DEBUG: Generated SQL query: {sql_query}")
            
            # Execute query
            print("🔍 DEBUG: Getting database connection...")
            pool = await self._get_connection()
            print("✅ DEBUG: Got connection pool")
            
            print("🔍 DEBUG: Acquiring connection from pool...")
            async with pool.acquire() as connection:
                print("✅ DEBUG: Connection acquired, executing query...")
                
                # Test connection first
                try:
                    test_result = await connection.fetch("SELECT 1 as test")
                    print(f"✅ DEBUG: Connection test successful: {test_result}")
                except Exception as test_e:
                    print(f"❌ DEBUG: Connection test failed: {test_e}")
                    raise
                
                print(f"🔍 DEBUG: Executing main query: {sql_query}")
                rows = await connection.fetch(sql_query)
                print(f"✅ DEBUG: Query executed successfully. Row count: {len(rows)}")
                
                result_data = [dict(row) for row in rows]
                print(f"🔍 DEBUG: Converted to dict format. Sample: {result_data[:2] if result_data else 'No data'}")
                
                actual_columns = list(result_data[0].keys()) if result_data else prediction.expected_columns
                print(f"🔍 DEBUG: Actual columns: {actual_columns}")
                
                metadata = {
                    "query": sql_query,
                    "headers": actual_columns,
                    "column_descriptions": prediction.column_descriptions,
                    "row_count": len(result_data),
                    "query_purpose": prediction.query_purpose,
                }
                
                response = Response(
                    type="table",
                    data=result_data,
                    frontend=True,
                    metadata=metadata,
                    description=f"{prediction.query_purpose}."
                )
                print(f"✅ DEBUG: Response created: {response}")
                print(f"🔍 DEBUG: Response data sample: {response.data[:2] if response.data else 'No data'}")

                print("🔍 DEBUG: About to yield response...")
                yield response
                print("✅ DEBUG: Response yielded successfully")
                
        except Exception as e:
            print(f"❌ DEBUG: Exception occurred: {type(e).__name__}: {str(e)}")
            import traceback
            print(f"❌ DEBUG: Full traceback: {traceback.format_exc()}")
            
            yield Response(
                type="text",
                data=[{"text": f"SQL execution failed: {str(e)}"}],
                frontend=True,
                metadata={"error": True, "guidance": guidance},
                description="SQL tool execution failed"
            )