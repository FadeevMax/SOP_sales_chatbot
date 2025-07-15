import streamlit as st
from openai import OpenAI
import time
import os

# --- Setup ---
st.set_page_config(page_title="GTI SOP Sales Coordinator", layout="centered")

# --- Sidebar Navigation ---
st.sidebar.title("🔧 Navigation")
page = st.sidebar.radio("Go to:", ["🔑 API Configuration", "🤖 Chatbot", "📄 Instructions", "⚙️ Settings"])

# --- API Configuration Page ---
if page == "🔑 API Configuration":
    st.header("🔑 API Configuration")
    st.markdown("""
    ### OpenAI API Key Setup
    Enter your OpenAI API key to use the GTI SOP Sales Coordinator.
    
    #### How to get your API key:
    1. Go to [OpenAI Platform](https://platform.openai.com/)
    2. Sign in to your account
    3. Navigate to API Keys section
    4. Create a new API key
    5. Copy and paste it below
    
    ⚠️ **Important**: Your API key is stored only for this session and is not saved permanently.
    """)
    
    # API Key input
    api_key_input = st.text_input(
        "Enter your OpenAI API Key:",
        type="password",
        placeholder="sk-proj-...",
        help="Your API key will be used to access OpenAI's services"
    )
    
    if api_key_input:
        if api_key_input.startswith("sk-"):
            st.session_state.api_key = api_key_input
            st.success("✅ API Key saved successfully!")
            st.info("You can now navigate to the Chatbot page to start using the assistant.")
        else:
            st.error("❌ Invalid API key format. OpenAI API keys should start with 'sk-'")
    
    # Show current status
    if "api_key" in st.session_state:
        st.markdown("---")
        st.markdown("**Current Status:** 🟢 API Key configured")
        if st.button("Clear API Key"):
            if "api_key" in st.session_state:
                del st.session_state.api_key
            if "assistant_id" in st.session_state:
                del st.session_state.assistant_id
            if "thread_id" in st.session_state:
                del st.session_state.thread_id
            if "chat_history" in st.session_state:
                del st.session_state.chat_history
            st.rerun()
    else:
        st.markdown("---")
        st.markdown("**Current Status:** 🔴 No API Key configured")

# --- Settings Page ---
elif page == "⚙️ Settings":
    st.header("⚙️ Settings")
    
    # Check if API key is configured
    if "api_key" not in st.session_state:
        st.warning("⚠️ Please configure your API key first in the 'API Configuration' page.")
        st.stop()
    
    st.session_state.model = st.selectbox(
        "Choose the model:", 
        ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"], 
        index=0 if "model" not in st.session_state else ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"].index(st.session_state.get("model", "gpt-4o"))
    )
    st.success(f"Model selected: {st.session_state.model}")
    
    # File path configuration
    st.markdown("---")
    st.subheader("📁 File Configuration")
    
    default_path = "/Users/maxfade/Desktop/HeadQuarters/GTI Data Base and SOP (1).pdf"
    st.session_state.file_path = st.text_input(
        "PDF File Path:",
        value=st.session_state.get("file_path", default_path),
        help="Path to your GTI SOP PDF file"
    )
    
    # Validate file path
    if st.session_state.file_path:
        if os.path.exists(st.session_state.file_path):
            st.success("✅ File path is valid")
        else:
            st.error("❌ File not found at the specified path")

# --- Instructions Page ---
elif page == "📄 Instructions":
    st.header("📄 How to Use GTI SOP Sales Coordinator")
    st.markdown("""
    This assistant helps the Sales Ops team at GTI follow SOPs by State and Order Type (Rise vs General).
    
    #### 🚀 Getting Started:
    1. **Configure API Key**: Go to the 'API Configuration' page and enter your OpenAI API key
    2. **Check Settings**: Verify your model selection and file path in 'Settings'
    3. **Start Chatting**: Navigate to the 'Chatbot' page to ask questions
    
    #### 💡 You Can Ask:
    - "What's the substitution policy for NY Rise orders?"
    - "Do we follow menu pricing in Illinois?"
    - "Can I split a flower case for a general store in Maryland?"
    
    **Formatting includes:**
    - ✅ Allowed actions
    - ❌ Not allowed
    - 💡 Tips and best practices
    - ⚠️ Critical info

    The AI will pull data **only** from your uploaded SOP document.
    """)

# --- Chat Page ---
elif page == "🤖 Chatbot":
    st.title("🤖 GTI SOP Sales Coordinator")

    # Check if API key is configured
    if "api_key" not in st.session_state:
        st.warning("⚠️ Please configure your API key first in the 'API Configuration' page.")
        st.stop()

    # Initialize OpenAI client
    client = OpenAI(api_key=st.session_state.api_key)

    # --- Initial Setup ---
    if "assistant_id" not in st.session_state:
        try:
            with st.spinner("Setting up assistant..."):
                assistant = client.beta.assistants.create(
                    name="SOP Sales Coordinator",
                    instructions="You are a helpful assistant that helps the Sales Ops team at GTI follow SOPs by State and Order Type (Rise vs General). Answer questions based only on the provided SOP document. Format your responses with clear indicators for allowed/not allowed actions, tips, and critical information using emojis and markdown formatting.",
                    model=st.session_state.get("model", "gpt-4o"),
                    tools=[{"type": "file_search"}]
                )
                st.session_state.assistant_id = assistant.id

                # Upload file and set up vector store
                file_path = st.session_state.get("file_path", "/Users/maxfade/Desktop/HeadQuarters/GTI Data Base and SOP (1).pdf")
                
                if not os.path.exists(file_path):
                    st.error(f"❌ File not found: {file_path}")
                    st.info("Please check your file path in the Settings page.")
                    st.stop()

                file_response = client.files.create(
                    file=open(file_path, "rb"),
                    purpose="assistants"
                )
                vector_store = client.vector_stores.create(name="SOP Vector Store")
                client.vector_stores.file_batches.create_and_poll(
                    vector_store_id=vector_store.id,
                    file_ids=[file_response.id]
                )
                client.beta.assistants.update(
                    assistant_id=assistant.id,
                    tool_resources={"file_search": {"vector_store_ids": [vector_store.id]}}
                )

                thread = client.beta.threads.create()
                st.session_state.thread_id = thread.id
                st.session_state.chat_history = []
                
        except Exception as e:
            st.error(f"❌ Error setting up assistant: {str(e)}")
            st.info("Please check your API key and try again.")
            st.stop()

    # --- Chat Interface ---
    st.subheader("💬 Ask a question about GTI SOPs")
    
    # Display chat history
    for idx, chat in enumerate(st.session_state.get("chat_history", [])):
        with st.chat_message("user"):
            st.markdown(chat["user"])
        with st.chat_message("assistant"):
            st.markdown(chat["assistant"])

    # --- Input Field at Bottom ---
    user_input = st.chat_input("Ask your question here...")
    if user_input:
        try:
            with st.spinner("Fetching answer..."):
                client.beta.threads.messages.create(
                    thread_id=st.session_state.thread_id,
                    role="user",
                    content=user_input
                )
                run = client.beta.threads.runs.create(
                    thread_id=st.session_state.thread_id,
                    assistant_id=st.session_state.assistant_id
                )

                while True:
                    run_status = client.beta.threads.runs.retrieve(
                        thread_id=st.session_state.thread_id,
                        run_id=run.id
                    )
                    if run_status.status in ["completed", "failed", "cancelled", "expired"]:
                        break
                    time.sleep(1)

                messages = client.beta.threads.messages.list(thread_id=st.session_state.thread_id)
                assistant_reply = ""
                for msg in messages.data:
                    if msg.role == "assistant":
                        assistant_reply = msg.content[0].text.value
                        break

                # Save conversation
                st.session_state.chat_history.append({
                    "user": user_input,
                    "assistant": assistant_reply
                })

                # Show assistant reply
                with st.chat_message("user"):
                    st.markdown(user_input)
                with st.chat_message("assistant"):
                    st.markdown(assistant_reply)
                    
        except Exception as e:
            st.error(f"❌ Error processing your request: {str(e)}")
            st.info("Please check your API key and try again.")