import streamlit as st
from pymongo import MongoClient
import requests

# Custom styling to make Streamlit look like a normal webpage
st.markdown("""
    <style>
    body {
        font-family: 'Arial', sans-serif;
        background-color: #f4f4f4;
        text-align: center;
        margin: 0;
        padding: 0;
    }
    .iframe-container {
        margin: 0;
        padding: 0;
        height: 100vh;  /* Full viewport height */
        width: 100vw;   /* Full viewport width */
        border: none;
    }
    </style>
""", unsafe_allow_html=True)

# Title and instructions
st.title("MongoDB File Search")
st.write("Enter your MongoDB URI to start searching for files.")

# Input field for MongoDB URI
mongo_uri = st.text_input("Enter MongoDB URI:", "")

if mongo_uri:
    try:
        # Attempt to connect to MongoDB
        client = MongoClient(mongo_uri)
        db = client.get_database()
        collection = db.get_collection("files")  # Assume the collection name is 'files'
        
        # Display success message
        st.success("Connected to MongoDB successfully!")

        # Search bar to search for files
        search_term = st.text_input("Search for a file:")

        if search_term:
            # Query MongoDB for files matching the search term
            files = collection.find({"name": {"$regex": search_term, "$options": "i"}})

            # Display files as a list in the Streamlit UI
            files_list = [file['name'] for file in files]

            if len(files_list) > 0:
                file_name = st.selectbox("Select a file", files_list)

                if file_name:
                    # Find the selected file in MongoDB
                    selected_file = collection.find_one({"name": file_name})
                    file_id = selected_file["_id"]

                    # Button to show file contents
                    if st.button("Show File Content"):
                        url = f"http://localhost:8080/watch/{file_id}"

                        # Make a request to localhost to get the file details
                        response = requests.get(url)

                        if response.status_code == 200:
                            # Show the response content (Assume it's HTML or JSON)
                            st.write(response.text)
                        else:
                            st.error(f"Failed to load file from {url}. Status code: {response.status_code}")
            else:
                st.write("No files found for your search term.")
        else:
            st.write("Enter a search term to find files.")
        
    except Exception as e:
        st.error(f"Failed to connect to MongoDB. Error: {e}")

else:
    st.write("Please enter your MongoDB URI to start.")
