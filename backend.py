import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import openai
import os
import re
from schema_manager import save_schema_to_file  # Import the schema management function

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
    # If no SQL code is detected, return the whole response (or handle accordingly)
    return response.strip()

def get_schema_from_file(filename='database_schema.txt'):
    try:
        with open(filename, 'r') as file:
            schema = file.read()
        return schema
    except Exception as e:
        logger.error(f"Error reading schema file: {e}")
        raise HTTPException(status_code=500, detail="Failed to read schema file")
    

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
    schema = get_schema_from_file()

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",  # Ensure this is the correct model
            messages=[
                {"role": "system", "content": "You are a helpful assistant that converts natural language requests into SQL queries."},
                {"role": "user", "content": f"Based on the following database schema, generate an SQL query for this request: {user_input}\n\nSchema:\n{schema}"}
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
    # Update the schema before executing the query
    save_schema_to_file('database_schema.txt')

    sql_query = query.user_input
    connection = connect_to_db()
    cursor = connection.cursor(cursor_factory=RealDictCursor)
    try:
        logger.info(f"Executing SQL Query: {sql_query}")
        cursor.execute(sql_query)
        
        # Handle different types of queries
        if sql_query.strip().lower().startswith(('select', 'show')):
            result = cursor.fetchall()
            logger.info(f"Query Result: {result}")
            return {"result": result}
        else:
            connection.commit()  # Commit changes for non-SELECT queries
            logger.info("Query executed successfully")
            return {"message": "Success", "status": "Done"}
    
    except Exception as e:
        connection.rollback()
        logger.error(f"Error executing SQL query: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to execute SQL query: {e}")
    
    finally:
        cursor.close()
        connection.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
