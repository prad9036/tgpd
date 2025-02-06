import streamlit as st

# Title for the page
st.title("Flask Page Inside Streamlit")

# Embed Flask page in an iframe
flask_url = "http://your-flask-app-url:5000"  # Replace with the URL of your Flask app
st.components.v1.iframe(flask_url, width=800, height=600)
