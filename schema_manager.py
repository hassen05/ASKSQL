import psycopg2
import logging

# Configure logging for schema manager
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DB_NAME = "pagila"
DB_USER = "postgres"
DB_PASSWORD = "Voodoo/420"
DB_HOST = "localhost"

def get_schema():
    try:
        connection = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST
        )
        cursor = connection.cursor()

        # Get list of tables
        cursor.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public';
        """)
        tables = cursor.fetchall()

        schema = ""
        for table in tables:
            table_name = table[0]
            schema += f"Table: {table_name}\n"

            # Get columns for each table
            cursor.execute("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = %s;
            """, (table_name,))
            columns = cursor.fetchall()

            for column in columns:
                schema += f"  {column[0]} ({column[1]})\n"

        cursor.close()
        connection.close()
        return schema

    except Exception as e:
        logger.error(f"Error retrieving schema: {e}")
        return ""

def save_schema_to_file(filename='database_schema.txt'):
    schema = get_schema()
    try:
        with open(filename, 'w') as file:
            file.write(schema)
        logger.info(f"Schema saved to {filename}")
    except Exception as e:
        logger.error(f"Error saving schema to file: {e}")

