import psycopg2

def get_schema():
    connection = psycopg2.connect(
        dbname="pagila",
        user="postgres",
        password="Voodoo/420",
        host="localhost"
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

print(get_schema())

def save_schema_to_file(filename):
    schema = get_schema()
    with open(filename, 'w') as file:
        file.write(schema)

# Call the function to save the schema to a file
save_schema_to_file('database_schema.txt')