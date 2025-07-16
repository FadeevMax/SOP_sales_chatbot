import streamlit as st
from openai import OpenAI
import time
import os
import uuid
from datetime import datetime

# --- Constants ---
DEFAULT_INSTRUCTIONS = """You are the **AI Sales Order Entry Coordinator**, an expert on Green Thumb Industries (GTI) sales operations. Your sole purpose is to support the human Sales Ops team by providing fast and accurate answers to their questions about order entry rules and procedures.
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
* **Limited Availability:** If an item has limited stock (e.g., request for 25, only 11 available), you can add the available amount as long as it's **9 units or more**. [cite: 2] If it's less than 9, do not add it. [cite: 2]"""

# --- Session State Initialization ---
def initialize_session_state():
    if "user_id" not in st.session_state:
        st.session_state.user_id = str(uuid.uuid4())
    if "model" not in st.session_state:
        st.session_state.model = "gpt-4o"
    if "file_path" not in st.session_state:
        st.session_state.file_path = "GTI Data Base and SOP (1).pdf"
    if "instructions" not in st.session_state:
        st.session_state.instructions = DEFAULT_INSTRUCTIONS
    if "assistant_setup_complete" not in st.session_state:
        st.session_state.assistant_setup_complete = False
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "threads" not in st.session_state:
        st.session_state.threads = []

initialize_session_state()

# --- Authentication Gate ---
if not st.session_state.authenticated:
    st.title("🔐 GTI SOP Sales Coordinator Login")
    pwd = st.text_input("Enter password or full API key:", type="password")
    if st.button("Submit"):
        if pwd == "111":
            st.session_state.api_key = st.secrets["openai_key"]
            st.session_state.authenticated = True
            st.success("✅ Correct password—welcome!")
            st.rerun()
        elif pwd.startswith("sk-"):
            st.session_state.api_key = pwd
            st.session_state.authenticated = True
            st.success("✅ API key accepted!")
            st.rerun()
        else:
            st.error("❌ Incorrect password or API key.")
    st.stop()

# --- Sidebar Navigation ---
st.sidebar.title("🔧 Navigation")
st.sidebar.info(f"User ID: {st.session_state.user_id[:8]}...")
page = st.sidebar.radio("Go to:", ["🤖 Chatbot", "📄 Instructions", "⚙️ Settings"])

# --- Instructions Page ---
if page == "📄 Instructions":
    st.header("📄 Chatbot Instructions")
    st.text_area("Edit Chatbot Instructions", key="instructions", height=320)
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Save Instructions"):
            st.success("✅ Instructions saved.")
    with col2:
        if st.button("Reset to Default Instructions"):
            st.session_state.instructions = DEFAULT_INSTRUCTIONS
            st.success("✅ Reset to default instructions.")

# --- Settings Page ---
elif page == "⚙️ Settings":
    st.header("⚙️ Settings")
    old_model = st.session_state.model
    st.session_state.model = st.selectbox("Choose the model:", ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"])
    if old_model != st.session_state.model:
        st.session_state.assistant_setup_complete = False
        st.session_state.threads = []

    st.markdown("---")
    st.subheader("📁 File Configuration")
    old_file_path = st.session_state.file_path
    st.session_state.file_path = st.text_input("PDF File Path:", value=st.session_state.file_path)
    if old_file_path != st.session_state.file_path:
        st.session_state.assistant_setup_complete = False
        st.session_state.threads = []

    if st.session_state.file_path:
        if os.path.exists(st.session_state.file_path):
            st.success("✅ File path is valid")
        else:
            st.error("❌ File not found at the specified path")

    st.markdown("---")
    st.subheader("🧹 Clear Threads")
    if st.button("🗑️ Clear All Threads & Conversations"):
        st.session_state.threads = []
        st.session_state.assistant_setup_complete = False
        st.success("✅ All threads cleared.")

# --- Chatbot Page ---
elif page == "🤖 Chatbot":
    st.title("🤖 GTI SOP Sales Coordinator")

    # --- Assistant Setup (per session/file/model) ---
    if not st.session_state.assistant_setup_complete:
        try:
            with st.spinner("Setting up your AI assistant..."):
                client = OpenAI(api_key=st.session_state.api_key)
                assistant = client.beta.assistants.create(
                    name=f"SOP Sales Coordinator - {st.session_state.user_id[:8]}",
                    instructions=st.session_state.instructions,
                    model=st.session_state.model,
                    tools=[{"type": "file_search"}]
                )
                st.session_state.assistant_id = assistant.id
                file_path = st.session_state.file_path
                if not os.path.exists(file_path):
                    st.error(f"❌ File not found: {file_path}")
                    st.stop()
                file_response = client.files.create(file=open(file_path, "rb"), purpose="assistants")
                vector_store = client.vector_stores.create(name="SOP Vector Store")
                client.vector_stores.file_batches.create_and_poll(
                    vector_store_id=vector_store.id,
                    file_ids=[file_response.id]
                )
                client.beta.assistants.update(
                    assistant_id=assistant.id,
                    tool_resources={"file_search": {"vector_store_ids": [vector_store.id]}}
                )
                # Start first thread
                thread = client.beta.threads.create()
                new_thread = {
                    "thread_id": thread.id,
                    "messages": [],
                    "start_time": datetime.now().isoformat()
                }
                st.session_state.threads.append(new_thread)
                st.session_state.thread_id = thread.id
                st.session_state.assistant_setup_complete = True
                st.success("✅ Assistant is ready!")
        except Exception as e:
            st.error(f"❌ Error setting up assistant: {str(e)}")
            st.stop()

    # --- Thread Management ---
    client = OpenAI(api_key=st.session_state.api_key)
    st.sidebar.subheader("🧵 Your Threads")
    thread_options = [
        f"{i+1}: {t['start_time'].split('T')[0]} {t['thread_id'][:8]}"
        for i, t in enumerate(st.session_state.threads)
    ]
    thread_ids = [t['thread_id'] for t in st.session_state.threads]

    if not thread_options:
        st.warning("No threads available. Please start a new thread.")

    # Select current thread
    if thread_options:
        selected_idx = st.sidebar.selectbox("Select Thread", list(range(len(thread_options))),
                                            format_func=lambda x: thread_options[x])
        selected_thread = st.session_state.threads[selected_idx]
        st.session_state.thread_id = selected_thread['thread_id']
    else:
        selected_thread = None

    if st.sidebar.button("➕ Start New Thread"):
        thread = client.beta.threads.create()
        new_thread = {
            "thread_id": thread.id,
            "messages": [],
            "start_time": datetime.now().isoformat()
        }
        st.session_state.threads.append(new_thread)
        st.session_state.thread_id = thread.id
        st.rerun()

    # --- Chat Display and Input ---
    st.subheader("💬 Ask your question about the GTI SOP")

    # Show chat history for selected thread
    if selected_thread:
        for msg in selected_thread['messages']:
            with st.chat_message("user"):
                st.markdown(msg["user"])
            with st.chat_message("assistant"):
                st.markdown(msg["assistant"])

        user_input = st.chat_input("Ask your question here...")
        if user_input:
            try:
                with st.spinner("Fetching answer..."):
                    # Send user message to thread
                    client.beta.threads.messages.create(
                        thread_id=selected_thread["thread_id"],
                        role="user",
                        content=user_input
                    )
                    # Run the assistant
                    run = client.beta.threads.runs.create(
                        thread_id=selected_thread["thread_id"],
                        assistant_id=st.session_state.assistant_id
                    )
                    # Poll for run completion
                    while True:
                        run_status = client.beta.threads.runs.retrieve(
                            thread_id=selected_thread["thread_id"],
                            run_id=run.id
                        )
                        if run_status.status in ["completed", "failed", "cancelled", "expired"]:
                            break
                        time.sleep(1)
                    # Retrieve assistant response
                    messages = client.beta.threads.messages.list(thread_id=selected_thread["thread_id"])
                    assistant_reply = ""
                    for msg in messages.data:
                        if msg.role == "assistant":
                            assistant_reply = msg.content[0].text.value
                            break
                    selected_thread["messages"].append({
                        "user": user_input,
                        "assistant": assistant_reply
                    })
                    # Show the messages immediately
                    with st.chat_message("user"):
                        st.markdown(user_input)
                    with st.chat_message("assistant"):
                        st.markdown(assistant_reply)
            except Exception as e:
                st.error(f"❌ Error processing your request: {str(e)}")
                st.session_state.assistant_setup_complete = False
                st.stop()
    else:
        st.info("Start a new thread to begin chatting.")
