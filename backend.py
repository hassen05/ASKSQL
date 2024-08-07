import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import openai
import os
import re


# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI()

class QueryRequest(BaseModel):
    user_input: str

# Database connection parameters
DB_NAME = "pagila"
DB_USER = "postgres"
DB_PASSWORD = "Voodoo/420"
DB_HOST = "localhost"

def extract_sql_code(response):
    # Adjust regex pattern based on the expected format of the SQL code
    match = re.search(r'```sql(.*?)```', response, re.DOTALL)
    if match:
        return match.group(1).strip()
    return response.strip()

def connect_to_db():
    connection = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST
    )
    return connection

@app.get("/")
async def read_root():
    return {"message": "Hello World"}

@app.post("/generate_query/")
async def generate_query(request: QueryRequest):
    user_input = request.user_input
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.error("OpenAI API key not found")
        raise HTTPException(status_code=500, detail="OpenAI API key not found")

    openai.api_key = api_key

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o",  # Ensure this is the correct model
            messages=[
                {"role": "system", "content": "You are a helpful assistant that converts natural language requests into SQL queries."},
                {"role": "user", "content": f"Generate an SQL query for the following request: {user_input}"}
            ]
        )
        raw_response = response.choices[0].message["content"].strip()
        
        # Extract SQL code using regex
        sql_query = extract_sql_code(raw_response)
        
        return {"sql_query": sql_query}
    
    except Exception as e:
        logger.error(f"Error generating query: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate SQL query: {e}")
    

@app.post("/execute_query/")
async def execute_query(query: QueryRequest):
    sql_query = query.user_input
    connection = connect_to_db()
    cursor = connection.cursor(cursor_factory=RealDictCursor)
    try:
        logger.info(f"Executing SQL Query: {sql_query}")
        cursor.execute(sql_query)
        result = cursor.fetchall()
        logger.info(f"Query Result: {result}")
        return {"result": result}
    except Exception as e:
        connection.rollback()
        logger.error(f"Error executing SQL query: {e}")
        raise HTTPException(status_code=500, detail="Failed to execute SQL query")
    finally:
        cursor.close()
        connection.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
