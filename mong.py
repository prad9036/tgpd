import streamlit as st
import subprocess
import platform
import os
import requests

# Custom CSS for styling the page
st.markdown(
    """
    <style>
    body {
        background-color: #f0f2f6;
        font-family: Arial, sans-serif;
    }
    .stButton>button {
        background-color: #3474A8;
        color: white;
        font-size: 18px;
        font-weight: bold;
    }
    .stButton>button:hover {
        background-color: #2e5d88;
    }
    .stTextArea textarea {
        font-family: "Courier New", monospace;
    }
    .stTextInput input {
        font-size: 18px;
    }
    .stSubheader {
        font-size: 20px;
        font-weight: bold;
    }
    .stWarning {
        background-color: #fff3cd;
    }
    .stError {
        background-color: #f8d7da;
    }
    .stSuccess {
        background-color: #d4edda;
    }
    </style>
    """, unsafe_allow_html=True
)

# Streamlit App Title
st.title("Simple Command Executor with Shell & URL Features")

# Detect operating system
os_type = platform.system()
st.write(f"Operating System: {os_type}")

# Sidebar for environment variables
st.sidebar.header("Environment Variables Setup")
variables = st.sidebar.text_area(
    "Enter your environment variables here (key=value format, one per line):",
    "",
    placeholder="API_ID=123456\nAPI_HASH=abcdef...\nBOT_TOKEN=xyz...",
    height=200
)

# Sidebar for URL and Port
st.sidebar.header("Port and URL Settings")
port = st.sidebar.text_input("Enter Port (e.g., 8080):", "")
url = st.sidebar.text_input("Enter URL to view:", "")

# Command History
if 'command_history' not in st.session_state:
    st.session_state.command_history = []

st.subheader("Shell Command Executor")

# Command input area
command = st.text_input("Enter your shell command:", "")

# Show Command History
if st.session_state.command_history:
    st.subheader("Command History")
    for idx, cmd in enumerate(st.session_state.command_history, 1):
        if st.button(f"Run Command {idx}: {cmd}"):
            command = cmd
            st.experimental_rerun()

# Display the entered URL content if URL is provided
if url:
    st.subheader(f"Content from {url}:")
    try:
        response = requests.get(url)
        st.text(response.text)
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching URL: {e}")

# Button to execute the command
if st.button("Run Command"):
    if command:
        try:
            # Parse and set environment variables from input
            env_vars = {}
            for line in variables.strip().split("\n"):
                if "=" in line:
                    key, value = line.split("=", 1)
                    env_vars[key.strip()] = value.strip()

            # Execute the shell command with environment variables
            result = subprocess.run(
                command,
                shell=True,  # Use shell=True for compatibility
                text=True,
                capture_output=True,
                env={**env_vars, **os.environ},  # Combine custom vars with system env
            )

            # Display the output
            st.subheader("Output:")
            st.text(result.stdout)

            # Display errors if any
            if result.stderr:
                st.subheader("Error:")
                st.text(result.stderr)

            # Add to Command History
            if command not in st.session_state.command_history:
                st.session_state.command_history.append(command)
            
        except Exception as e:
            st.error(f"An error occurred: {e}")
    else:
        st.warning("Please enter a command to run.")

# Display the entered port if provided
if port:
    st.markdown(f"### Port Info: \nYou entered port: **{port}**")

# Display Port URL if applicable
if port:
    st.markdown(f"### Server Running at: [http://localhost:{port}](http://localhost:{port})")
