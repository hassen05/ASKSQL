import logging
import os
import re
from typing import Optional, List
from dotenv import load_dotenv
import httpx
import psycopg2
from psycopg2 import sql as psycopg_sql
from psycopg2.extras import RealDictCursor
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from schema_manager import save_schema_to_file  # Import the schema management function

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AskSQL API",
    description="Natural Language to SQL Query Generator using Ollama",
    version="1.0.0"
)

class QueryRequest(BaseModel):
    user_input: str = Field(..., min_length=1, max_length=5000, description="Natural language query or SQL statement")

class QueryResponse(BaseModel):
    sql_query: str
    model_used: Optional[str] = None

class ExecuteResponse(BaseModel):
    result: Optional[List[dict]] = None
    message: Optional[str] = None
    status: Optional[str] = None
    rows_affected: Optional[int] = None

# Database connection parameters from environment variables
DB_NAME = os.getenv("DB_NAME", "pagila")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")

# Ollama configuration
OLLAMA_API_URL = os.getenv("OLLAMA_API_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1")

# Dangerous SQL statements that should be blocked
DANGEROUS_STATEMENTS = [
    'DROP', 'DELETE FROM', 'TRUNCATE', 'ALTER TABLE', 
    'CREATE USER', 'GRANT', 'REVOKE', 'COPY'
]

def extract_sql_code(response):
    """Extract SQL code from LLM response, handling markdown code blocks."""
    match = re.search(r'```sql\s*(.*?)\s*```', response, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    # Try without language specifier
    match = re.search(r'```\s*(.*?)\s*```', response, re.DOTALL)
    if match:
        return match.group(1).strip()
    # Return the whole response if no code blocks found
    return response.strip()

def validate_sql_query(sql_query: str) -> bool:
    """Validate SQL query to prevent dangerous operations."""
    sql_upper = sql_query.upper().strip()
    
    # Check for dangerous statements
    for dangerous in DANGEROUS_STATEMENTS:
        if sql_upper.startswith(dangerous):
            logger.warning(f"Blocked dangerous SQL statement: {dangerous}")
            return False
    
    # Additional validation: check for multiple statements (potential SQL injection)
    if ';' in sql_query.rstrip(';').split(';')[-1] or sql_query.count(';') > 1:
        logger.warning("Blocked query with multiple statements")
        return False
    
    return True

def get_schema_from_file(filename='database_schema.txt'):
    """Read database schema from file."""
    try:
        with open(filename, 'r') as file:
            schema = file.read()
        if not schema.strip():
            logger.warning("Schema file is empty")
        return schema
    except FileNotFoundError:
        logger.error(f"Schema file not found: {filename}")
        raise HTTPException(status_code=500, detail="Schema file not found. Please run schema update first.")
    except Exception as e:
        logger.error(f"Error reading schema file: {e}")
        raise HTTPException(status_code=500, detail="Failed to read schema file")

def connect_to_db():
    """Create a database connection using parameters from environment variables."""
    try:
        connection = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        return connection
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise HTTPException(status_code=503, detail=f"Database connection failed: {str(e)}")

@app.get("/")
async def read_root():
    """Root endpoint with API information."""
    return {
        "message": "Welcome to AskSQL API",
        "description": "Natural Language to SQL Query Generator using Ollama",
        "endpoints": {
            "generate_query": "POST /generate_query/",
            "execute_query": "POST /execute_query/",
            "health": "GET /health/"
        }
    }

@app.get("/health/")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "model": OLLAMA_MODEL}

@app.post("/generate_query/", response_model=QueryResponse)
async def generate_query(request: QueryRequest):
    """Generate SQL query from natural language using Ollama."""
    user_input = request.user_input
    schema = get_schema_from_file()

    # Build the prompt for Ollama
    system_prompt = """You are a helpful assistant that converts natural language requests into SQL queries.
Rules:
1. Only generate SELECT queries (no DELETE, DROP, UPDATE, INSERT, or schema modifications)
2. Use proper SQL syntax for PostgreSQL
3. Include only the SQL query in your response, wrapped in ```sql code blocks
4. Do not include explanations outside the code block
5. Use appropriate JOINs and WHERE clauses based on the schema"""

    user_prompt = f"""Based on the following database schema, generate an SQL query for this request: {user_input}

Schema:
{schema}

Generate only the SQL query:"""

    try:
        # Call Ollama API
        async with httpx.AsyncClient(timeout=60.0) as client:
            ollama_request = {
                "model": OLLAMA_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "stream": False,
                "options": {
                    "temperature": 0.1,  # Low temperature for more deterministic SQL generation
                    "top_p": 0.9
                }
            }
            
            response = await client.post(
                f"{OLLAMA_API_URL}/api/chat",
                json=ollama_request
            )
            response.raise_for_status()
            response_data = response.json()
        
        raw_response = response_data.get("message", {}).get("content", "")
        
        if not raw_response:
            logger.error("Empty response from Ollama")
            raise HTTPException(status_code=500, detail="Empty response from AI model")
        
        # Extract SQL code using regex
        sql_query = extract_sql_code(raw_response)
        
        logger.info(f"Generated SQL query: {sql_query}")
        
        return {"sql_query": sql_query, "model_used": OLLAMA_MODEL}
    
    except httpx.HTTPError as e:
        logger.error(f"HTTP error calling Ollama API: {e}")
        raise HTTPException(status_code=503, detail=f"Failed to connect to Ollama API: {str(e)}")
    except Exception as e:
        logger.error(f"Error generating query: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate SQL query: {str(e)}")
    

@app.post("/execute_query/", response_model=ExecuteResponse)
async def execute_query(query: QueryRequest):
    """Execute SQL query with validation and safety checks."""
    # Update the schema before executing the query
    save_schema_to_file('database_schema.txt')

    sql_query = query.user_input.strip()
    
    # Validate the SQL query for safety
    if not validate_sql_query(sql_query):
        logger.warning(f"Query blocked due to safety validation: {sql_query}")
        raise HTTPException(
            status_code=400, 
            detail="Query contains potentially dangerous operations. Only SELECT queries are allowed."
        )
    
    connection = None
    cursor = None
    try:
        connection = connect_to_db()
        cursor = connection.cursor(cursor_factory=RealDictCursor)
        
        logger.info(f"Executing SQL Query: {sql_query}")
        cursor.execute(sql_query)
        
        # Handle different types of queries
        if sql_query.lower().startswith(('select', 'show', 'explain')):
            result = cursor.fetchall()
            rows_count = len(result)
            logger.info(f"Query returned {rows_count} rows")
            return {"result": result, "rows_affected": rows_count}
        else:
            # For non-SELECT queries that passed validation (e.g., CREATE TEMP TABLE)
            connection.commit()
            rows_affected = cursor.rowcount
            logger.info(f"Query executed successfully, rows affected: {rows_affected}")
            return {"message": "Query executed successfully", "status": "Done", "rows_affected": rows_affected}
    
    except psycopg2.Error as e:
        if connection:
            connection.rollback()
        logger.error(f"Database error executing SQL query: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        if connection:
            connection.rollback()
        logger.error(f"Error executing SQL query: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to execute SQL query: {str(e)}")
    
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
