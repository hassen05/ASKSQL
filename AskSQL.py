import streamlit as st
import requests

# Define the URL of your backend API
API_URL = "http://127.0.0.1:8000"

# Set the page title and icon
st.set_page_config(
    page_title="AI SQL Query Generator",
    page_icon="🧠"  # Using an emoji as a page icon
)

st.logo("logo2.png")  # Path to the logo file

st.title("AI SQL Query Generator")

user_input = st.text_input("What would you like me to do?")

if st.button("Generate and Execute Query"):
    try:
        # Generate SQL query
        generate_response = requests.post(f"{API_URL}/generate_query/", json={"user_input": user_input})
        generate_response.raise_for_status()  # Raise an HTTPError if the HTTP request returned an unsuccessful status code
        st.write("Raw generate response:")
        st.write(generate_response.text)  # Log the raw response content

        sql_query = generate_response.json().get("sql_query")
        st.write("Generated SQL Query:")
        st.code(sql_query)

        # Execute SQL query
        execute_response = requests.post(f"{API_URL}/execute_query/", json={"user_input": sql_query})
        execute_response.raise_for_status()
        st.write("Raw execute response:")
        st.write(execute_response.text)  # Log the raw response content

        result = execute_response.json().get("result")
        st.write("Query Result:")
        st.write(result)
    except requests.exceptions.HTTPError as http_err:
        st.error(f"HTTP error occurred: {http_err}")
    except requests.exceptions.RequestException as req_err:
        st.error(f"Request error occurred: {req_err}")
    except ValueError as json_err:
        st.error(f"JSON decode error: {json_err}")
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")
