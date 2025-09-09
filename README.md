# AI Data Search & Analysis Tool

An intelligent data analysis, search system and agentic workflow system built with Python that combines workflow automation, database querying, charting capabilities, and AI-powered insights.

## 🚀 Features

- **AI-Powered Workflow System**: Dynamic decision-making with branching workflows
- **Database Integration**: PostgreSQL connectivity with intelligent SQL generation
- **Interactive Charts**: Data visualization and charting tools
- **Gmail Integration**: Email automation and communication features
- **WebSocket API**: Real-time data streaming and analysis
- **Modular Tool System**: Extensible architecture for adding custom tools
- **Multi-LLM Support**: Works with OpenAI GPT and Anthropic Claude models

## 📁 Project Structure

```
├── api/                          # FastAPI web application
│   ├── app/
│   │   ├── main.py              # FastAPI application entry point
│   │   └── websocket_handler.py # WebSocket communication handler
│   ├── requirements.txt         # API dependencies
│   └── run.py                   # Server startup script
├── external_tools/              # Custom tool implementations
│   ├── charting_tool.py         # Data visualization tool
│   ├── python_interpreter_tool.py # Python code execution
│   ├── output_formatter_tool.py  # Result formatting
│   └── sql_tool.py              # Database query tool
├── workflow/                    # Workflow management system
│   ├── workflow.py              # Core workflow orchestration
│   ├── helper_objects.py        # Data structures and helpers
│   ├── prompt_decision.py       # AI decision making
│   └── utils.py                 # Workflow utilities
├── preprocessing/               # Data preprocessing
│   └── context.json            # Database schema definitions
├── objects.py                   # Core classes and data structures
├── helper_functions.py          # Utility functions
├── gmail.py                     # Gmail API integration
├── utils.py                     # General utilities
├── debug_test.py               # Testing and debugging
├── credentials.json            # Google OAuth credentials (template)
└── .env                        # Environment variables (template)
```

## 🛠️ Installation

### Prerequisites
- Python 3.8+
- PostgreSQL database (optional)
- Gmail API credentials (optional)

### Setup

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd ai-data-search-py
   ```

2. **Install dependencies**
   ```bash
   # Install API dependencies
   pip install -r api/requirements.txt
   
   # Install additional dependencies
   pip install dspy-ai openai anthropic google-api-python-client google-auth-httplib2 google-auth-oauthlib psycopg2-binary
   ```

3. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your actual values
   ```

4. **Set up Gmail integration (optional)**
   - Create a Google Cloud Project
   - Enable Gmail API
   - Download credentials and save as `credentials.json`

## ⚙️ Configuration

### Environment Variables

Create a `.env` file with the following variables:

```bash
# AI Model API Keys
export OPENAI_API_KEY=your_openai_api_key_here
export ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Database Configuration (optional)
export PG_HOST=your_postgres_host
export PG_RO_PW=your_postgres_password
export PG_RO_USER=your_postgres_user
export PG_DB=your_database_name
export PG_PORT=5432

# Email Service (optional)
export RESEND_API_KEY=your_resend_api_key_here
```

### Google OAuth Setup (for Gmail features)

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable Gmail API
4. Create OAuth 2.0 credentials
5. Download the credentials file and save as `credentials.json`

## 🚀 Usage

### Starting the API Server

```bash
# Start the FastAPI server
python api/run.py

# Or run directly with uvicorn
uvicorn api.app.main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at `http://localhost:8000`

### Using the Workflow System

```python
import asyncio
import dspy
from workflow.workflow import Workflow

# Initialize the workflow
lm = dspy.LM('anthropic/claude-sonnet-4-20250514', api_key=os.getenv('ANTHROPIC_API_KEY'))
workflow = Workflow(model=lm)

# Run a query
async def run_analysis():
    async for response in workflow.run("Analyze sales data for Q1 2024"):
        print(response.to_dict())

asyncio.run(run_analysis())
```

### Adding Custom Tools

Create a custom tool by subclassing the `Tool` class:

```python
from objects import Tool, Response
from typing import Dict, Any

class CustomTool(Tool):
    def __init__(self, model):
        super().__init__(
            name="custom_tool",
            description="Description of what your tool does",
            inputs={
                "parameter": {"type": str, "description": "Parameter description", "required": True}
            }
        )
        self.model = model

    async def __call__(self, tree_data, inputs: Dict[str, Any], **kwargs) -> Response:
        # Your tool logic here
        result = f"Processed: {inputs['parameter']}"
        
        return Response(
            type="text",
            data=[{"text": result}],
            description="Custom tool result"
        )

# Add to workflow
workflow.add_tool(CustomTool(model), branch_id="base")
```

### WebSocket API Usage

Connect to the WebSocket endpoint for real-time communication:

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/analyze');

ws.onopen = function() {
    // Send analysis request
    ws.send(JSON.stringify({
        type: "analyze",
        query: "Show me sales trends for this month",
        options: {}
    }));
};

ws.onmessage = function(event) {
    const response = JSON.parse(event.data);
    console.log('Response:', response);
};
```

## 🔧 Available Tools

### Core Tools

1. **SQL Tool** (`sql_tool.py`)
   - Execute database queries
   - Generate SQL from natural language
   - Handle complex analytical queries

2. **Charting Tool** (`charting_tool.py`)
   - Create data visualizations
   - Generate charts and graphs
   - Export visual data representations

3. **Python Interpreter Tool** (`python_interpreter_tool.py`)
   - Execute Python code snippets
   - Perform calculations and data processing
   - Handle complex computational tasks

4. **Output Formatter Tool** (`output_formatter_tool.py`)
   - Format and structure results
   - Convert data to different formats
   - Prepare data for presentation

### Adding New Tools

1. Create your tool class inheriting from `Tool`
2. Implement the `__call__` method
3. Define tool inputs and description
4. Add to workflow using `workflow.add_tool()`

Example tool structure:

```python
class YourCustomTool(Tool):
    def __init__(self, model):
        super().__init__(
            name="your_tool_name",
            description="What your tool does",
            inputs={
                "input_param": {
                    "type": str, 
                    "description": "Description", 
                    "required": True
                }
            }
        )

    async def __call__(self, tree_data, inputs: Dict[str, Any], **kwargs):
        # Tool implementation
        return Response(data=result, type="your_result_type")
```

## 🧪 Testing

Run the debug test to verify your setup:

```bash
python debug_test.py
```

## 📝 API Endpoints

### WebSocket Endpoints
- `ws://localhost:8000/ws/analyze` - Real-time analysis and data streaming

### HTTP Endpoints
- `GET /` - Health check
- `GET /auth/google` - Google OAuth initiation
- `GET /auth/callback` - OAuth callback handler

## 🔐 Security Notes

- Never commit actual API keys or credentials
- Use environment variables for sensitive configuration
- The `.env` file should not be tracked in version control
- Credentials files are templates and need your actual values

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License
This project is licensed under the MIT License - see the file for details.


## 🐛 Troubleshooting

### Common Issues

1. **Missing API Keys**: Ensure all required environment variables are set
2. **Database Connection**: Verify PostgreSQL credentials and connectivity
3. **Gmail Integration**: Check Google OAuth setup and credentials file
4. **Dependencies**: Make sure all required packages are installed

### Getting Help

- Check the debug output from `debug_test.py`
- Verify your `.env` configuration
- Ensure all dependencies are installed correctly

## 🚧 Development Status

This is an active development project. Features and APIs may change as the project evolves.
