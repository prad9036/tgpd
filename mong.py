import streamlit as st
import streamlit.components.v1 as components

# Title of the page
st.title("Embed External Page in Streamlit")

# URL to embed (can be changed to any other URL)
url = "http://localhost:8080"  # Or "https://filestreambot.streamlit.app/"

# Embed the URL within an iframe in the Streamlit app
components.iframe(url, width=800, height=600)

