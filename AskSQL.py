import streamlit as st
import requests
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Define the URL of your backend API
API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")

# Define the path for the history file
HISTORY_FILE = "history.json"

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as file:
            return json.load(file)
    return []

def save_history(history):
    with open(HISTORY_FILE, "w") as file:
        json.dump(history, file)

# Initialize session state to keep track of history
if 'history' not in st.session_state:
    st.session_state.history = load_history()

# Set the page title and icon
st.set_page_config(
    page_title="AI SQL Query Generator",
    page_icon="🧠"  # Using an emoji as a page icon
)
st.logo("logo2.png")  # Path to the logo file

# Sidebar for navigation
st.sidebar.title("Navigation")
selection = st.sidebar.radio("Go to", ["Home", "History"])

if selection == "Home":
    st.title("AI SQL Query Generator")
    
    user_input = st.text_input("What would you like me to do?")
    
    if st.button("Generate and Execute Query"):
        if not user_input.strip():
            st.warning("Please enter a query description.")
        else:
            with st.spinner("Generating SQL query..."):
                try:
                    # Generate SQL query
                    generate_response = requests.post(
                        f"{API_URL}/generate_query/", 
                        json={"user_input": user_input},
                        timeout=60
                    )
                    generate_response.raise_for_status()
                    
                    sql_query = generate_response.json().get("sql_query")
                    
                    st.write("Generated SQL Query:")
                    st.code(sql_query, language="sql")
                    
                    # Show confirmation before executing
                    if st.button("Execute this query"):
                        with st.spinner("Executing query..."):
                            # Execute SQL query
                            execute_response = requests.post(
                                f"{API_URL}/execute_query/", 
                                json={"user_input": sql_query},
                                timeout=30
                            )
                            execute_response.raise_for_status()
                            
                            result = execute_response.json()
                            
                            if "result" in result:
                                st.write("Query Result:")
                                st.dataframe(result["result"])
                                if "rows_affected" in result:
                                    st.info(f"{result['rows_affected']} rows returned")
                            elif "message" in result:
                                st.success(result["message"])
                            
                            # Add to history
                            new_entry = {"prompt": user_input, "query": sql_query, "result": result}
                            st.session_state.history.append(new_entry)
                            save_history(st.session_state.history)
                            st.success("Query added to history!")
                    
                except requests.exceptions.Timeout:
                    st.error("Request timed out. The AI model may be taking too long to respond.")
                except requests.exceptions.HTTPError as http_err:
                    error_detail = http_err.response.json().get("detail", str(http_err)) if http_err.response else str(http_err)
                    st.error(f"HTTP error occurred: {error_detail}")
                except requests.exceptions.RequestException as req_err:
                    st.error(f"Request error occurred: {req_err}")
                    st.info("Make sure the backend server is running (run: fastapi uvicorn backend:app --reload)")
                except ValueError as json_err:
                    st.error(f"JSON decode error: {json_err}")
                except Exception as e:
                    st.error(f"An unexpected error occurred: {e}")

elif selection == "History":
    st.title("History")

    if st.session_state.history:
        # Dropdown or radio button to select history item
        options = [entry["prompt"][:50] + ("..." if len(entry["prompt"]) > 50 else "") for entry in st.session_state.history]
        selected_option = st.selectbox("Select a prompt", options)

        # Display selected history item
        index = options.index(selected_option)
        entry = st.session_state.history[index]

        st.subheader("Prompt")
        st.write(entry["prompt"])
        st.subheader("Generated SQL Query")
        st.code(entry["query"])
        st.subheader("Query Result")
        st.write(entry["result"])
    else:
        st.write("No history available.")
