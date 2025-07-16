import streamlit as st
from openai import OpenAI
import time
import os
import uuid
from datetime import datetime
import json
from streamlit_local_storage import LocalStorage

# NEW: Imports for Google Docs API
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# --- Constants & Configuration ---
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
    * **Rule Category:** (eg., Pricing, Substitutions, Splitting Orders, Loose Units, Samples, Invoicing, Case Sizes, Discounts, Leaf Trade procedures).
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
STATE_DIR = "user_data"
# The name of your Google Doc as it appears in Google Drive
GOOGLE_DOC_NAME = "GTI Data Base and SOP"

# --- Functions for User and State Management (No changes here) ---
def get_persistent_user_id(local_storage: LocalStorage) -> str:
    user_id = local_storage.getItem("user_id")
    if user_id is None:
        user_id = str(uuid.uuid4())
        local_storage.setItem("user_id", user_id)
    return user_id

def get_user_state_filepath(user_id: str) -> str:
    if not os.path.exists(STATE_DIR):
        os.makedirs(STATE_DIR)
    return os.path.join(STATE_DIR, f"state_{user_id}.json")

def save_app_state(user_id: str):
    if "user_id" not in st.session_state:
        return
    state_to_save = {
        "user_id": user_id,
        "custom_instructions": st.session_state.custom_instructions,
        "current_instruction_name": st.session_state.current_instruction_name,
        "threads": st.session_state.threads
    }
    filepath = get_user_state_filepath(user_id)
    with open(filepath, "w") as f:
        json.dump(state_to_save, f, indent=4)

def load_app_state(user_id: str):
    filepath = get_user_state_filepath(user_id)
    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            try:
                state = json.load(f)
                st.session_state.custom_instructions = state.get("custom_instructions", {"Default": DEFAULT_INSTRUCTIONS})
                st.session_state.current_instruction_name = state.get("current_instruction_name", "Default")
                st.session_state.threads = state.get("threads", [])
                st.session_state.custom_instructions["Default"] = DEFAULT_INSTRUCTIONS
                return True
            except (json.JSONDecodeError, KeyError):
                return False
    return False

# ======================================================================
# --- NEW: Google Docs Integration ---
# ======================================================================
def read_structural_elements(elements):
    """Recursively parses the structured elements of a Google Doc to extract text."""
    text = ''
    for value in elements:
        if 'paragraph' in value:
            para_elements = value.get('paragraph').get('elements')
            for elem in para_elements:
                text += elem.get('textRun', {}).get('content', '')
        elif 'table' in value:
            table = value.get('table')
            for row in table.get('tableRows'):
                for cell in row.get('tableCells'):
                    text += read_structural_elements(cell.get('content'))
                text += '\n'
    return text

@st.cache_data(ttl=600) # Cache for 10 minutes
def fetch_google_doc_content(doc_name: str) -> str:
    """Connects to Google Docs API, finds a doc by name, and returns its text content."""
    try:
        scopes = [
            'https://www.googleapis.com/auth/drive.readonly',
            'https://www.googleapis.com/auth/documents.readonly'
        ]
        creds_dict = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)

        drive_service = build('drive', 'v3', credentials=creds)
        docs_service = build('docs', 'v1', credentials=creds)

        # Find the document by name
        query = f"name='{doc_name}' and mimeType='application/vnd.google-apps.document'"
        response = drive_service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
        files = response.get('files', [])

        if not files:
            st.error(f"No Google Doc found with the name: '{doc_name}'. Please check the name and sharing settings.")
            return None
        
        doc_id = files[0]['id']
        
        # Retrieve the document content
        document = docs_service.documents().get(documentId=doc_id).execute()
        doc_content = document.get('body').get('content', [])
        
        full_text = read_structural_elements(doc_content)
        
        st.success(f"✅ Successfully fetched content from Google Doc: '{doc_name}'")
        return full_text

    except Exception as e:
        st.error(f"❌ Failed to fetch Google Doc: {e}")
        return None

# --- Session State Initialization Function ---
def initialize_session_state():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if st.session_state.authenticated and "state_loaded" not in st.session_state:
        if load_app_state(st.session_state.user_id):
            st.session_state.state_loaded = True
        else:
            st.session_state.threads = []
            st.session_state.custom_instructions = {"Default": DEFAULT_INSTRUCTIONS}
            st.session_state.current_instruction_name = "Default"
            st.session_state.state_loaded = True

    if "model" not in st.session_state:
        st.session_state.model = "gpt-4o"
    if "file_path" not in st.session_state:
        st.session_state.file_path = None # Will be set dynamically
    if "instructions" not in st.session_state:
        custom_instructions = st.session_state.get("custom_instructions", {"Default": DEFAULT_INSTRUCTIONS})
        current_instruction_name = st.session_state.get("current_instruction_name", "Default")
        st.session_state.instructions = custom_instructions.get(current_instruction_name, DEFAULT_INSTRUCTIONS)
    if "assistant_setup_complete" not in st.session_state:
        st.session_state.assistant_setup_complete = False
    if "instruction_edit_mode" not in st.session_state:
        st.session_state.instruction_edit_mode = "view"

# ======================================================================
# --- Main Application Function ---
# ======================================================================
def run_main_app():
    st.sidebar.title("🔧 Navigation")
    st.sidebar.info(f"User ID: {st.session_state.user_id[:8]}...")
    page = st.sidebar.radio("Go to:", ["🤖 Chatbot", "📄 Instructions", "⚙️ Settings"])

    if page == "📄 Instructions":
        st.header("📄 Chatbot Instructions Manager")

        if st.session_state.instruction_edit_mode == "create":
            st.subheader("➕ Create New Instruction")
            with st.form("new_instruction_form"):
                new_name = st.text_input("Instruction Name:")
                new_content = st.text_area("Instruction Content:", height=300)
                submitted = st.form_submit_button("💾 Save New Instruction")
                if submitted:
                    if new_name and new_content:
                        if new_name not in st.session_state.custom_instructions:
                            st.session_state.custom_instructions[new_name] = new_content
                            st.session_state.current_instruction_name = new_name
                            st.session_state.instruction_edit_mode = "view"
                            st.session_state.assistant_setup_complete = False
                            save_app_state(st.session_state.user_id)
                            st.success(f"✅ Instruction '{new_name}' saved.")
                            st.rerun()
                        else:
                            st.error("❌ An instruction with this name already exists.")
                    else:
                        st.error("❌ Please provide both a name and content.")
            if st.button("✖️ Cancel"):
                st.session_state.instruction_edit_mode = "view"
                st.rerun()
        else:
            col1, col2 = st.columns([3, 1])
            with col1:
                instruction_names = list(st.session_state.custom_instructions.keys())
                if st.session_state.current_instruction_name not in instruction_names:
                    st.session_state.current_instruction_name = "Default"
                selected_instruction = st.selectbox(
                    "Select instruction to view or edit:",
                    instruction_names,
                    index=instruction_names.index(st.session_state.current_instruction_name)
                )
                st.session_state.current_instruction_name = selected_instruction
            with col2:
                st.write("")
                st.write("")
                if st.button("➕ Create New Instruction"):
                    st.session_state.instruction_edit_mode = "create"
                    st.rerun()

            st.subheader(f"Editing: '{selected_instruction}'")
            is_default = selected_instruction == "Default"
            instruction_content = st.text_area(
                "Instruction Content:",
                value=st.session_state.custom_instructions[selected_instruction],
                height=320,
                disabled=is_default,
                key=f"editor_{selected_instruction}"
            )
            if not is_default:
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("💾 Save Changes"):
                        st.session_state.custom_instructions[selected_instruction] = instruction_content
                        st.session_state.instructions = instruction_content
                        st.session_state.assistant_setup_complete = False
                        save_app_state(st.session_state.user_id)
                        st.success(f"✅ '{selected_instruction}' instructions saved.")
                with c2:
                    if st.button("🗑️ Delete Instruction"):
                        del st.session_state.custom_instructions[selected_instruction]
                        st.session_state.current_instruction_name = "Default"
                        st.session_state.instructions = DEFAULT_INSTRUCTIONS
                        st.session_state.assistant_setup_complete = False
                        save_app_state(st.session_state.user_id)
                        st.success(f"✅ '{selected_instruction}' deleted.")
                        st.rerun()
            else:
                st.info("ℹ️ The 'Default' instruction cannot be edited or deleted.")

    elif page == "⚙️ Settings":
        st.header("⚙️ Settings")
        st.info("File configuration is now managed automatically via Google Docs.")
        st.markdown("---")
        st.subheader("🧹 Clear Threads")
        if st.button("🗑️ Clear All Threads & Conversations"):
            st.session_state.threads = []
            st.session_state.assistant_setup_complete = False
            save_app_state(st.session_state.user_id)
            st.success("✅ All threads cleared.")

    elif page == "🤖 Chatbot":
        st.title("🤖 GTI SOP Sales Coordinator")
        col1, col2 = st.columns(2)
        with col1:
            models = ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-4.1"]
            old_model = st.session_state.model
            new_model = st.selectbox("Choose model:", models, index=models.index(old_model))
        with col2:
            instruction_names = list(st.session_state.custom_instructions.keys())
            old_instruction = st.session_state.current_instruction_name
            new_instruction = st.selectbox("Choose instructions:", instruction_names, index=instruction_names.index(old_instruction))

        settings_changed = (old_model != new_model) or (old_instruction != new_instruction)
        if settings_changed:
            st.warning("⚠️ Settings changed. You need to start a new thread to apply these changes.")
            if st.button("🆕 Start New Thread with New Settings"):
                st.session_state.model = new_model
                st.session_state.current_instruction_name = new_instruction
                st.session_state.instructions = st.session_state.custom_instructions[new_instruction]
                st.session_state.assistant_setup_complete = False
                client = OpenAI(api_key=st.session_state.api_key)
                thread = client.beta.threads.create()
                new_thread_obj = {"thread_id": thread.id, "messages": [], "start_time": datetime.now().isoformat(), "model": new_model, "instruction_name": new_instruction}
                st.session_state.threads.append(new_thread_obj)
                st.session_state.thread_id = thread.id
                save_app_state(st.session_state.user_id)
                st.success("✅ New thread created with updated settings!")
                st.rerun()
        else:
            st.session_state.model = new_model
            st.session_state.current_instruction_name = new_instruction
            st.session_state.instructions = st.session_state.custom_instructions[new_instruction]

        # --- MODIFIED: Assistant Setup with Google Docs ---
        if not st.session_state.get('assistant_setup_complete', False):
            try:
                with st.spinner("Fetching latest SOP from Google Docs..."):
                    live_sop_content = fetch_google_doc_content(GOOGLE_DOC_NAME)
                    
                    if live_sop_content:
                        temp_file_path = f"temp_sop_{st.session_state.user_id}.txt"
                        with open(temp_file_path, "w", encoding="utf-8") as f:
                            f.write(live_sop_content)
                        st.session_state.file_path = temp_file_path
                    else:
                        st.error("Could not fetch SOP from Google Docs. Assistant setup failed.")
                        st.stop()

                with st.spinner("Setting up AI assistant with the latest data..."):
                    client = OpenAI(api_key=st.session_state.api_key)
                    
                    file_response = client.files.create(file=open(st.session_state.file_path, "rb"), purpose="assistants")
                    
                    vector_store = client.vector_stores.create(name=f"SOP Vector Store - {st.session_state.user_id[:8]}")
                    
                    client.vector_stores.file_batches.create_and_poll(
                        vector_store_id=vector_store.id, file_ids=[file_response.id]
                    )
                    
                    assistant = client.beta.assistants.create(
                        name=f"SOP Sales Coordinator - {st.session_state.user_id[:8]}",
                        instructions=st.session_state.instructions,
                        model=st.session_state.model,
                        tools=[{"type": "file_search"}],
                        tool_resources={"file_search": {"vector_store_ids": [vector_store.id]}}
                    )
                    st.session_state.assistant_id = assistant.id
                    
                    if not st.session_state.threads:
                        thread = client.beta.threads.create()
                        st.session_state.threads.append({"thread_id": thread.id, "messages": [], "start_time": datetime.now().isoformat(), "model": st.session_state.model, "instruction_name": st.session_state.current_instruction_name})
                        st.session_state.thread_id = thread.id
                        save_app_state(st.session_state.user_id)
                        
                    st.session_state.assistant_setup_complete = True
                    st.success("✅ Assistant is ready with the latest information!")
            except Exception as e:
                st.error(f"❌ Error setting up assistant: {str(e)}")
                st.stop()
        
        client = OpenAI(api_key=st.session_state.api_key)
        st.sidebar.subheader("🧵 Your Threads")
        thread_options = [f"{i+1}: {t['start_time'].split('T')[0]} | {t.get('model', 'N/A')} | {t.get('instruction_name', 'N/A')}" for i, t in enumerate(st.session_state.threads)]
        thread_ids = [t['thread_id'] for t in st.session_state.threads]
        selected_thread_info = None
        if thread_options:
            current_idx = thread_ids.index(st.session_state.thread_id) if 'thread_id' in st.session_state and st.session_state.thread_id in thread_ids else 0
            selected_idx = st.sidebar.selectbox("Select Thread", range(len(thread_options)), format_func=lambda x: thread_options[x], index=current_idx)
            selected_thread_info = st.session_state.threads[selected_idx]
            st.session_state.thread_id = selected_thread_info['thread_id']

        if st.sidebar.button("➕ Start New Thread"):
            thread = client.beta.threads.create()
            new_thread_obj = {"thread_id": thread.id, "messages": [], "start_time": datetime.now().isoformat(), "model": st.session_state.model, "instruction_name": st.session_state.current_instruction_name}
            st.session_state.threads.append(new_thread_obj)
            st.session_state.thread_id = thread.id
            save_app_state(st.session_state.user_id)
            st.rerun()

        st.subheader("💬 Ask your question about the GTI SOP")
        if selected_thread_info:
            st.info(f"🔧 Current: {selected_thread_info.get('model', 'unknown')} | {selected_thread_info.get('instruction_name', 'unknown')}")
            for msg in selected_thread_info['messages']:
                with st.chat_message("user"): st.markdown(msg["user"])
                with st.chat_message("assistant"): st.markdown(msg["assistant"])

            user_input = st.chat_input("Ask your question here...")
            if user_input:
                try:
                    selected_thread_info["messages"].append({"user": user_input, "assistant": ""})
                    with st.chat_message("user"): st.markdown(user_input)
                    client.beta.threads.messages.create(thread_id=selected_thread_info["thread_id"], role="user", content=user_input)
                    run = client.beta.threads.runs.create_and_poll(thread_id=selected_thread_info["thread_id"], assistant_id=st.session_state.assistant_id)
                    if run.status == 'completed':
                        messages = client.beta.threads.messages.list(thread_id=selected_thread_info["thread_id"])
                        assistant_reply = next((m.content[0].text.value for m in messages.data if m.role == "assistant"), "Sorry, I couldn't get a response.")
                        selected_thread_info["messages"][-1]["assistant"] = assistant_reply
                        with st.chat_message("assistant"): st.markdown(assistant_reply)
                        save_app_state(st.session_state.user_id)
                    else:
                        st.error(f"❌ Run failed with status: {run.status}")
                        selected_thread_info["messages"].pop()
                except Exception as e:
                    st.error(f"❌ Error processing your request: {str(e)}")
                    st.session_state.assistant_setup_complete = False
                    if selected_thread_info["messages"]: selected_thread_info["messages"].pop()
        else:
            st.info("Start a new thread to begin chatting.")


# ======================================================================
# --- SCRIPT EXECUTION STARTS HERE ---
# ======================================================================

localS = LocalStorage()
user_id = get_persistent_user_id(localS)
st.session_state.user_id = user_id

initialize_session_state()

if not st.session_state.authenticated:
    st.title("🔐 GTI SOP Sales Coordinator Login")
    pwd = st.text_input("Enter password or full API key:", type="password")
    if st.button("Submit"):
        if pwd == "111":
            try:
                st.session_state.api_key = st.secrets["openai_key"]
                st.session_state.authenticated = True
                st.success("✅ Correct password—welcome!")
                time.sleep(1)
                st.rerun()
            except (KeyError, FileNotFoundError):
                st.error("OpenAI key not found in Streamlit Secrets. Please add it to your deployment.")
        elif pwd.startswith("sk-"):
            st.session_state.api_key = pwd
            st.session_state.authenticated = True
            st.success("✅ API key accepted!")
            time.sleep(1)
            st.rerun()
        else:
            st.error("❌ Incorrect password or API key.")
    st.stop()
else:
    run_main_app()
