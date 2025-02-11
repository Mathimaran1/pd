import streamlit as st
import google.generativeai as genai
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import base64
import os
import re
import json

# Configure Gemini API
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-pro')

# Gmail API Setup
SCOPES = ['https://www.googleapis.com/auth/gmail.send',
          'https://www.googleapis.com/auth/gmail.readonly']

def get_gmail_service():
    """Get Gmail service using OAuth 2.0"""
    creds = None
    if 'gmail_creds' in st.session_state:
        creds = st.session_state.gmail_creds

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Use the secret directly as a dict (no json.loads needed)
            flow = InstalledAppFlow.from_client_config(
                st.secrets["GMAIL_OAUTH_CREDS"],
                SCOPES
            )
            creds = flow.run_local_server(port=0)
        st.session_state.gmail_creds = creds

    return build('gmail', 'v1', credentials=creds)

# Streamlit UI
st.title("📧 Gmail AI Assistant")
st.write("HEY DUDE!Chat with your email assistant!")

# Authentication Check
if 'gmail_creds' not in st.session_state:
    st.warning("Please authenticate with Google to continue.")
    if st.button("Authenticate with Google"):
        try:
            gmail_service = get_gmail_service()
            st.success("Authentication successful!")
            st.experimental_rerun()
        except Exception as e:
            st.error(f"Authentication failed: {str(e)}")
    st.stop()

# Chat history initialization
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Function to parse email commands using Gemini
def parse_email_command(prompt):
    response = model.generate_content(
        f"""Parse this email command: "{prompt}". Return JSON format with:
        {{
            "subject": "email subject",
            "body": "email content",
            "recipient": "recipient@example.com",
            "summary_request": boolean
        }}
        Handle both email composition and summary requests."""
    )
    return json.loads(response.text)

# Email sending function
def send_email(recipient, subject, body):
    try:
        service = get_gmail_service()
        message = MIMEMultipart()
        message['to'] = recipient
        message['subject'] = subject
        message.attach(MIMEText(body, 'plain'))
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        service.users().messages().send(userId='me', body={'raw': raw}).execute()
        return True
    except Exception as e:
        st.error(f"Error sending email: {str(e)}")
        return False

# Email summary function
def get_and_summarize_emails():
    try:
        service = get_gmail_service()
        results = service.users().messages().list(userId='me', maxResults=5).execute()
        messages = results.get('messages', [])
        
        summaries = []
        for message in messages:
            msg = service.users().messages().get(userId='me', id=message['id']).execute()
            payload = msg['payload']
            headers = payload['headers']
            subject = next(h['value'] for h in headers if h['name'] == 'Subject')
            snippet = msg['snippet']
            
            # Generate summary using Gemini
            summary = model.generate_content(
                f"Summarize this email: Subject: {subject}\nContent: {snippet}"
            ).text
            summaries.append(f"📌 {subject}\n📝 {summary}")
        
        return "\n\n".join(summaries)
    except Exception as e:
        return f"Error retrieving emails: {str(e)}"

# Chat input
if prompt := st.chat_input("How can I help with your emails?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        try:
            # Parse user command
            parsed = parse_email_command(prompt)
            
            if parsed.get('summary_request'):
                summary = get_and_summarize_emails()
                response = f"📧 Email Summary:\n{summary}"
            else:
                success = send_email(
                    parsed['recipient'],
                    parsed['subject'],
                    parsed['body']
                )
                response = (f"✅ Email sent to {parsed['recipient']}!\n"
                            f"Subject: {parsed['subject']}\n"
                            f"Content: {parsed['body']}")
            
            st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})
            
        except Exception as e:
            error_msg = f"❌ Error processing request: {str(e)}"
            st.markdown(error_msg)
            st.session_state.messages.append({"role": "assistant", "content":error_msg})
