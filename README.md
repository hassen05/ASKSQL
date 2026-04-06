# AskSQL - AI-Powered SQL Query Generator

A Streamlit + FastAPI application that converts natural language questions into SQL queries using **Ollama** (local LLM).

## Features

- 🧠 Natural language to SQL conversion using Ollama (Llama 3.1 or other local models)
- 🔒 Security-focused: Blocks dangerous SQL operations (DROP, DELETE, etc.)
- 📊 Interactive Streamlit UI with query history
- 🗄️ PostgreSQL database support (Pagila sample database)
- 🔄 Auto-generates and updates database schema
- 💾 Query history saved locally

## Prerequisites

1. **Python 3.8+**
2. **PostgreSQL** with the Pagila sample database installed
3. **Ollama** installed and running locally
   - Install from: https://ollama.ai
   - Pull a model: `ollama pull llama3.1`

## Installation

### 1. Clone and Setup

```bash
cd /workspace
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Copy the example environment file and configure it:

```bash
cp .env.example .env
```

Edit `.env` with your settings:

```env
# Database Configuration
DB_NAME=pagila
DB_USER=postgres
DB_PASSWORD=your_password_here
DB_HOST=localhost
DB_PORT=5432

# Ollama Configuration
OLLAMA_API_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1

# API URL for frontend
API_URL=http://127.0.0.1:8000
```

### 3. Start Ollama

Make sure Ollama is running:

```bash
ollama serve
```

In another terminal, verify your model is available:

```bash
ollama list
```

## Running the Application

### Terminal 1: Start the FastAPI Backend

```bash
uvicorn backend:app --reload --host 127.0.0.1 --port 8000
```

The API will be available at: http://127.0.0.1:8000
API docs at: http://127.0.0.1:8000/docs

### Terminal 2: Start the Streamlit Frontend

```bash
streamlit run AskSQL.py
```

The UI will open in your browser at: http://localhost:8501

## Usage

1. Open the Streamlit app in your browser
2. Enter a natural language question (e.g., "Show me all customers who rented movies last month")
3. Click "Generate and Execute Query"
4. Review the generated SQL query
5. Click "Execute this query" to run it against the database
6. View results and save to history

## API Endpoints

- `GET /` - API information
- `GET /health/` - Health check endpoint
- `POST /generate_query/` - Generate SQL from natural language
- `POST /execute_query/` - Execute a SQL query

## Security Features

- ❌ Blocked operations: DROP, DELETE FROM, TRUNCATE, ALTER TABLE, CREATE USER, GRANT, REVOKE, COPY
- ✅ Only SELECT queries are allowed by default
- ✅ Input validation and sanitization
- ✅ No hardcoded credentials (uses environment variables)
- ✅ Protection against multiple statement injection

## Project Structure

```
/workspace
├── AskSQL.py           # Streamlit frontend
├── backend.py          # FastAPI backend
├── schema_manager.py   # Database schema extraction utility
├── requirements.txt    # Python dependencies
├── .env.example        # Example environment configuration
├── .gitignore         # Git ignore rules
├── README.md          # This file
└── database_schema.txt # Auto-generated schema file
```

## Troubleshooting

### Ollama Connection Error
- Ensure Ollama is running: `ollama serve`
- Check the model is pulled: `ollama pull llama3.1`
- Verify OLLAMA_API_URL in `.env`

### Database Connection Error
- Verify PostgreSQL is running
- Check credentials in `.env`
- Ensure Pagila database exists

### Backend Not Responding
- Check if uvicorn is running on port 8000
- Verify API_URL in frontend matches backend address

## License

MIT License
