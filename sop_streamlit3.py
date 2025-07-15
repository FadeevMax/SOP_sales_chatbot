import streamlit as st
from openai import OpenAI
import time
import os
import uuid

# --- Setup ---
st.set_page_config(page_title="GTI SOP Sales Coordinator", layout="centered")

# --- Initialize Session State ---
def initialize_session_state():
    """Initialize all required session state variables"""
    if "user_id" not in st.session_state:
        st.session_state.user_id = str(uuid.uuid4())
    
    if "model" not in st.session_state:
        st.session_state.model = "gpt-4o"
    
    if "file_path" not in st.session_state:
        st.session_state.file_path = "GTI Data Base and SOP (1).pdf"
    
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    
    if "assistant_setup_complete" not in st.session_state:
        st.session_state.assistant_setup_complete = False

# Call initialization
initialize_session_state()

# --- Sidebar Navigation ---
st.sidebar.title("🔧 Navigation")
st.sidebar.info(f"User ID: {st.session_state.user_id[:8]}...")  # Show first 8 chars of user ID
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
            # Reset assistant setup when API key changes
            st.session_state.assistant_setup_complete = False
            if "assistant_id" in st.session_state:
                del st.session_state.assistant_id
            if "thread_id" in st.session_state:
                del st.session_state.thread_id
            st.success("✅ API Key saved successfully!")
            st.info("You can now navigate to the Chatbot page to start using the assistant.")
        else:
            st.error("❌ Invalid API key format. OpenAI API keys should start with 'sk-'")
    
    # Show current status
    if "api_key" in st.session_state:
        st.markdown("---")
        st.markdown("**Current Status:** 🟢 API Key configured")
        if st.button("Clear API Key"):
            # Clear all related session state
            keys_to_clear = ["api_key", "assistant_id", "thread_id", "assistant_setup_complete"]
            for key in keys_to_clear:
                if key in st.session_state:
                    del st.session_state[key]
            st.session_state.chat_history = []
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
    
    # Model selection
    old_model = st.session_state.model
    st.session_state.model = st.selectbox(
        "Choose the model:", 
        ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"], 
        index=["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"].index(st.session_state.model)
    )
    
    # If model changed, reset assistant setup
    if old_model != st.session_state.model:
        st.session_state.assistant_setup_complete = False
        if "assistant_id" in st.session_state:
            del st.session_state.assistant_id
        if "thread_id" in st.session_state:
            del st.session_state.thread_id
    
    st.success(f"Model selected: {st.session_state.model}")
    
    # File path configuration
    st.markdown("---")
    st.subheader("📁 File Configuration")
    
    old_file_path = st.session_state.file_path
    st.session_state.file_path = st.text_input(
        "PDF File Path:",
        value=st.session_state.file_path,
        help="Path to your GTI SOP PDF file"
    )
    
    # If file path changed, reset assistant setup
    if old_file_path != st.session_state.file_path:
        st.session_state.assistant_setup_complete = False
        if "assistant_id" in st.session_state:
            del st.session_state.assistant_id
        if "thread_id" in st.session_state:
            del st.session_state.thread_id
    
    # Validate file path
    if st.session_state.file_path:
        if os.path.exists(st.session_state.file_path):
            st.success("✅ File path is valid")
        else:
            st.error("❌ File not found at the specified path")
    
    # Session info
    st.markdown("---")
    st.subheader("🔍 Session Information")
    st.info(f"Your User ID: {st.session_state.user_id}")
    st.info(f"Chat History: {len(st.session_state.chat_history)} messages")
    
    if st.button("🗑️ Clear Chat History"):
        st.session_state.chat_history = []
        st.success("Chat history cleared!")
        st.rerun()

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
    
    #### 🔄 Multi-User Support:
    - Each user gets their own unique session and chat history
    - Your conversations are private to your session
    - You can clear your chat history in the Settings page
    """)

# --- Chat Page ---
elif page == "🤖 Chatbot":
    st.title("🤖 GTI SOP Sales Coordinator")

    # Check if API key is configured
    if "api_key" not in st.session_state:
        st.warning("⚠️ Please configure your API key first in the 'API Configuration' page.")
        st.stop()

    # Initialize OpenAI client
    try:
        client = OpenAI(api_key=st.session_state.api_key)
    except Exception as e:
        st.error(f"❌ Error initializing OpenAI client: {str(e)}")
        st.info("Please check your API key in the 'API Configuration' page.")
        st.stop()

    # --- Assistant Setup ---
    if not st.session_state.assistant_setup_complete:
        try:
            with st.spinner("Setting up your personal assistant..."):
                # Create assistant
                assistant = client.beta.assistants.create(
                    name=f"SOP Sales Coordinator - {st.session_state.user_id[:8]}",
                    instructions="You are a helpful assistant that helps the Sales Ops team at GTI follow SOPs by State and Order Type (Rise vs General). Answer questions based only on the provided SOP document. Format your responses with clear indicators for allowed/not allowed actions, tips, and critical information using emojis and markdown formatting.",
                    model=st.session_state.model,
                    tools=[{"type": "file_search"}]
                )
                st.session_state.assistant_id = assistant.id

                # Upload file and set up vector store
                file_path = st.session_state.file_path
                
                if not os.path.exists(file_path):
                    st.error(f"❌ File not found: {file_path}")
                    st.info("Please check your file path in the Settings page.")
                    st.stop()

                file_response = client.files.create(
                    file=open(file_path, "rb"),
                    purpose="assistants"
                )
                vector_store = client.vector_stores.create(
                    name=f"SOP Vector Store - {st.session_state.user_id[:8]}"
                )
                client.vector_stores.file_batches.create_and_poll(
                    vector_store_id=vector_store.id,
                    file_ids=[file_response.id]
                )
                client.beta.assistants.update(
                    assistant_id=assistant.id,
                    tool_resources={"file_search": {"vector_store_ids": [vector_store.id]}}
                )

                # Create thread for this user
                thread = client.beta.threads.create()
                st.session_state.thread_id = thread.id
                st.session_state.assistant_setup_complete = True
                
                st.success("✅ Assistant setup complete!")
                
        except Exception as e:
            st.error(f"❌ Error setting up assistant: {str(e)}")
            st.info("Please check your API key and file path, then try again.")
            st.stop()

    # --- Chat Interface ---
    st.subheader("💬 Ask a question about GTI SOPs")
    
    # Display chat history
    for idx, chat in enumerate(st.session_state.chat_history):
        with st.chat_message("user"):
            st.markdown(chat["user"])
        with st.chat_message("assistant"):
            st.markdown(chat["assistant"])

    # --- Input Field at Bottom ---
    user_input = st.chat_input("Ask your question here...")
    if user_input:
        # Ensure we have all required session state variables
        if "thread_id" not in st.session_state or "assistant_id" not in st.session_state:
            st.error("❌ Session state error. Please refresh the page and try again.")
            st.stop()
            
        try:
            with st.spinner("Fetching answer..."):
                # Add user message to thread
                client.beta.threads.messages.create(
                    thread_id=st.session_state.thread_id,
                    role="user",
                    content=user_input
                )
                
                # Create run
                run = client.beta.threads.runs.create(
                    thread_id=st.session_state.thread_id,
                    assistant_id=st.session_state.assistant_id
                )

                # Wait for completion
                while True:
                    run_status = client.beta.threads.runs.retrieve(
                        thread_id=st.session_state.thread_id,
                        run_id=run.id
                    )
                    if run_status.status in ["completed", "failed", "cancelled", "expired"]:
                        break
                    time.sleep(1)

                # Get assistant response
                messages = client.beta.threads.messages.list(thread_id=st.session_state.thread_id)
                assistant_reply = ""
                for msg in messages.data:
                    if msg.role == "assistant":
                        assistant_reply = msg.content[0].text.value
                        break

                # Save conversation to session history
                st.session_state.chat_history.append({
                    "user": user_input,
                    "assistant": assistant_reply
                })

                # Display the new messages
                with st.chat_message("user"):
                    st.markdown(user_input)
                with st.chat_message("assistant"):
                    st.markdown(assistant_reply)
                    
        except Exception as e:
            st.error(f"❌ Error processing your request: {str(e)}")
            st.info("Please check your API key and try again.")
            
            # If there's an error, we might need to reset the assistant setup
            if "invalid" in str(e).lower() or "not found" in str(e).lower():
                st.session_state.assistant_setup_complete = False
                if "assistant_id" in st.session_state:
                    del st.session_state.assistant_id
                if "thread_id" in st.session_state:
                    del st.session_state.thread_id
                st.info("Assistant setup has been reset. Please try again.")
