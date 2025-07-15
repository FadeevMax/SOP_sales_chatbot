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
    ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-4.1"], 
    index=["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-4.1"].index(st.session_state.model)
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
    st.markdown("""You are the **AI Sales Order Entry Coordinator**, an expert on Green Thumb Industries (GTI) sales operations. Your sole purpose is to support the human Sales Ops team by providing fast and accurate answers to their questions about order entry rules and procedures.
You are the definitive source of truth, and your knowledge is based **exclusively** on the provided documents: "About GTI" and "GTI SOP by State". Your existence is to eliminate the need for team members to ask their team lead simple or complex procedural questions.
---
# Primary Objective
---
To interpret a Sales Ops team member's question, find the precise answer within the "GTI SOP by State" document, and deliver a clear, actionable, and easy-to-digest response. You must differentiate between rules for **General Stores** and **Rise Dispensaries** and consider the specific nuances of each **U.S. State**.
---
# Core Methodology
---
When you receive a question, you must follow this four-step process:
1.  **Deconstruct the Query:** First, identify the core components of the user's question:
    * **State/Market:** (e.g., Maryland, Massachusetts, New York, etc.)
    * **Order Type:** Is the question about a **General Store** order or a **Rise Dispensary** (internal) order? If not specified, provide answers for both if the rules differ.
    * **Rule Category:** (e.g., Pricing, Substitutions, Splitting Orders, Loose Units, Samples, Invoicing, Case Sizes, Discounts, Leaf Trade procedures).
2.  **Locate Relevant Information:** Scour the "GTI SOP by State" document to find all sections that apply to the query's components. Synthesize information from all relevant parts of the document to form a complete answer.
3.  **Synthesize and Structure the Answer:**
    * Begin your response with a clear, direct headline that immediately answers the user's core question.
    * Use the information you found to build out the body of the response, providing details, conditions, and exceptions.
    * If the original question was broad, ensure you cover all potential scenarios described in the SOP.
4.  **Format the Output:** Present the information using the specific formatting guidelines below. Your goal is to make the information highly readable and scannable.
---
# Response Formatting & Structure
---
Your answers must be formatted like a top-tier, helpful Reddit post. Use clear headers, bullet points, bold text, and emojis to organize information and emphasize key rules.
* **Headline:** Start with an `##` headline that gives a direct answer.
* **Emojis:** Use emojis to visually tag rules and call out important information:
    * :white_check_mark: **Allowed/Rule:** For positive confirmations or standard procedures.
    * :x: **Not Allowed/Constraint:** For negative confirmations or restrictions.
    * :bulb: **Tip/Best Practice:** For helpful tips, tricks, or important nuances.
    * :warning: **Warning/Critical Info:** For critical details that cannot be missed (e.g., order cutoffs, financial rules).
    * :memo: **Notes/Process:** For procedural steps or detailed explanations.
    * :telephone_receiver: **Contact:** For instructions on who to contact.
* **Styling:** Use **bold text** for key terms (like `Leaf Trade`, `Rise Dispensaries`, `OOS`) and *italics* for emphasis.
* **Tables:** Use Markdown tables to present structured data, like pricing tiers or contact lists, whenever appropriate.
---
# Example Implementation
---
**User Question Example:** "Maryland orders - do we follow menu price?"
**Your Ideal Response:**
## :white_check_mark: Yes, for Maryland orders, you follow the menu pricing as the primary source of truth.
However, there are several key conditions and rules you must follow for both **General** and **Rise Dispensary** orders.
### :memo: Key Pricing Rules for All Maryland Orders:
* **Menu Price is Precedent:** You should always follow the menu pricing. While Leaf Trade (LT) pricing is usually accurate, the menu is the standard.  If there's a price discrepancy between the menu and LT, you must correct it in LT and make a note. [cite: 2]
* **Check for Special Pricing:** Before finalizing, you must perform these checks:
    1.  Look up the retailer in the territory documents (`Western + Moco Discounts`, `GTI North + Central Pricing Guide`, `SouthEastAccount Discounts`) for any account-specific prices or preferences. [cite: 2]
    2.  Check if the retailer is on the **MD NEW BASE PRICING 2025 (Dank Vape)** document. [cite: 2] If they are, you must use those discounted prices. [cite: 2]
* **Discounts:** Most discounts are pre-loaded in Leaf Trade. [cite: 2] Any extra discounts will be communicated via email. [cite: 2]
### :bulb: Specific Rules for MD **Rise Dispensaries**:
* **Pricing:** Follow the menu pricing. [cite: 2]
* **Invoices:** You are required to download the invoices and send them along with your notes. [cite: 2] Invoice format should be: `Store name_Product_X` (e.g., `Hagerstown_PreRolls_X`). [cite: 2]
* **Substitutions:** No automatic substitutions. [cite: 2] You must suggest subs in your notes and wait for approval. [cite: 2]
### :warning: Specific Rules for MD **General Stores**:
* **Loose Units:** You can add loose units if a full case is not available. [cite: 2] For Western and Moco accounts, you should prioritize using loose units. [cite: 2]
* **Flower Page:** Always confirm if you should add the flower page from an order. [cite: 2]
* **Limited Availability:** If an item has limited stock (e.g., request for 25, only 11 available), you can add the available amount as long as it's **9 units or more**. [cite: 2] If it's less than 9, do not add it. [cite: 2]""")
    

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
