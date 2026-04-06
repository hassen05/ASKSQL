import psycopg2
import logging
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging for schema manager
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DB_NAME = os.getenv("DB_NAME", "pagila")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")

def get_schema():
    """Retrieve database schema from PostgreSQL information_schema."""
    connection = None
    cursor = None
    try:
        connection = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        cursor = connection.cursor()

        # Get list of tables
        cursor.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        tables = cursor.fetchall()

        schema = ""
        for table in tables:
            table_name = table[0]
            schema += f"Table: {table_name}\n"

            # Get columns for each table with more details
            cursor.execute("""
                SELECT column_name, data_type, is_nullable, character_maximum_length
                FROM information_schema.columns
                WHERE table_name = %s
                ORDER BY ordinal_position;
            """, (table_name,))
            columns = cursor.fetchall()

            for column in columns:
                col_name = column[0]
                col_type = column[1]
                nullable = "NULL" if column[2] == "YES" else "NOT NULL"
                max_length = f"({column[3]})" if column[3] else ""
                schema += f"  - {col_name}: {col_type}{max_length} {nullable}\n"
            
            # Get primary keys
            cursor.execute("""
                SELECT a.attname
                FROM pg_index i
                JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
                WHERE i.indrelid = %s::regclass
                AND i.indisprimary;
            """, (table_name,))
            primary_keys = cursor.fetchall()
            
            if primary_keys:
                pk_names = [pk[0] for pk in primary_keys]
                schema += f"  Primary Key: {', '.join(pk_names)}\n"
            
            schema += "\n"

        return schema

    except Exception as e:
        logger.error(f"Error retrieving schema: {e}")
        return ""
    
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

def save_schema_to_file(filename='database_schema.txt'):
    schema = get_schema()
    try:
        with open(filename, 'w') as file:
            file.write(schema)
        logger.info(f"Schema saved to {filename}")
    except Exception as e:
        logger.error(f"Error saving schema to file: {e}")

