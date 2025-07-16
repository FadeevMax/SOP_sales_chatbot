

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

initialize_session_state()

# --- Sidebar Navigation ---
st.sidebar.title("🔧 Navigation")
st.sidebar.info(f"User ID: {st.session_state.user_id[:8]}...")
page = st.sidebar.radio("Go to:", ["🤖 Chatbot", "📄 Instructions", "⚙️ Settings"])

# --- Settings Page ---
if page == "⚙️ Settings":
    st.header("⚙️ Settings")

    if "api_key" not in st.session_state:
        st.warning("⚠️ Please unlock access in the Chatbot page first.")
        st.stop()

    old_model = st.session_state.model
    st.session_state.model = st.selectbox(
        "Choose the model:", 
        ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"], 
        index=["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"].index(st.session_state.model)
    )

    if old_model != st.session_state.model:
        st.session_state.assistant_setup_complete = False
        for key in ["assistant_id", "thread_id"]:
            st.session_state.pop(key, None)

    st.success(f"Model selected: {st.session_state.model}")

    st.markdown("---")
    st.subheader("📁 File Configuration")

    old_file_path = st.session_state.file_path
    st.session_state.file_path = st.text_input(
        "PDF File Path:",
        value=st.session_state.file_path,
        help="Path to your GTI SOP PDF file"
    )

    if old_file_path != st.session_state.file_path:
        st.session_state.assistant_setup_complete = False
        for key in ["assistant_id", "thread_id"]:
            st.session_state.pop(key, None)

    if st.session_state.file_path:
        if os.path.exists(st.session_state.file_path):
            st.success("✅ File path is valid")
        else:
            st.error("❌ File not found at the specified path")

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
    st.markdown("""You are the **AI Sales Order Entry Coordinator**,...""")

# --- Chat Page ---
elif page == "🤖 Chatbot":
    st.title("🤖 GTI SOP Sales Coordinator")

    # Prompt for password to use the Streamlit secret
    if "api_key" not in st.session_state:
        st.session_state.api_access_granted = False

    if not st.session_state.get("api_access_granted"):
        user_password = st.text_input("🔒 Enter password to access the assistant", type="password")
        if user_password == "1111":
            st.session_state.api_key = st.secrets["openai_key"]
            st.session_state.api_access_granted = True
            st.success("✅ Access granted. Assistant is ready!")
            st.rerun()
        elif user_password:
            st.error("❌ Incorrect password.")
        st.stop()

    # Initialize OpenAI client
    try:
        client = OpenAI(api_key=st.session_state.api_key)
    except Exception as e:
        st.error(f"❌ Error initializing OpenAI client: {str(e)}")
        st.stop()

    # --- Assistant Setup ---
    if not st.session_state.assistant_setup_complete:
        try:
            with st.spinner("Setting up your personal assistant..."):
                assistant = client.beta.assistants.create(
                    name=f"SOP Sales Coordinator - {st.session_state.user_id[:8]}",
                    instructions="""You are the **AI Sales Order Entry Coordinator**, an expert on Green Thumb Industries (GTI) sales operations. Your sole purpose is to support the human Sales Ops team by providing fast and accurate answers to their questions about order entry rules and procedures.
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
* **Limited Availability:** If an item has limited stock (e.g., request for 25, only 11 available), you can add the available amount as long as it's **9 units or more**. [cite: 2] If it's less than 9, do not add it. [cite: 2]""",
                    model=st.session_state.model,
                    tools=[{"type": "file_search"}]
                )
                st.session_state.assistant_id = assistant.id

                file_path = st.session_state.file_path
                if not os.path.exists(file_path):
                    st.error(f"❌ File not found: {file_path}")
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

                thread = client.beta.threads.create()
                st.session_state.thread_id = thread.id
                st.session_state.assistant_setup_complete = True
                st.success("✅ Assistant setup complete!")
        except Exception as e:
            st.error(f"❌ Error setting up assistant: {str(e)}")
            st.stop()

    # --- Chat Interface ---
    st.subheader("💬 Ask a question about GTI SOPs")

    for chat in st.session_state.chat_history:
        with st.chat_message("user"):
            st.markdown(chat["user"])
        with st.chat_message("assistant"):
            st.markdown(chat["assistant"])

    user_input = st.chat_input("Ask your question here...")
    if user_input:
        if "thread_id" not in st.session_state or "assistant_id" not in st.session_state:
            st.error("❌ Session state error. Please refresh the page and try again.")
            st.stop()

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

                st.session_state.chat_history.append({
                    "user": user_input,
                    "assistant": assistant_reply
                })

                with st.chat_message("user"):
                    st.markdown(user_input)
                with st.chat_message("assistant"):
                    st.markdown(assistant_reply)

        except Exception as e:
            st.error(f"❌ Error processing your request: {str(e)}")
            if "invalid" in str(e).lower() or "not found" in str(e).lower():
                st.session_state.assistant_setup_complete = False
                for key in ["assistant_id", "thread_id"]:
                    st.session_state.pop(key, None)
                st.info("Assistant setup has been reset. Please try again.")
