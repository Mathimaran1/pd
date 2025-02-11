import streamlit as st

# Testing secret retrieval
st.write(f"GEMINI API Key: {st.secrets['GEMINI_API_KEY']}")
st.write(f"Gmail Client ID: {st.secrets['GMAIL_OAUTH_CREDS']['client_id']}")
