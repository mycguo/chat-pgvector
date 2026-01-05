"""
Quick Notes - Grouped Table Layout

A grouped 2-column table for quick reference information.
Allows multiple entries per label (e.g., multiple referral codes, multiple phone numbers).
Opens in a separate tab for easy side-by-side viewing.
"""

import streamlit as st
import streamlit.components.v1 as components
import sys
from datetime import datetime
import pandas as pd
from collections import defaultdict

# Add parent directory to path
sys.path.insert(0, '.')

from storage.json_db import JobSearchDB
from storage.auth_utils import (
    is_user_logged_in,
    logout,
    render_login_button,
    render_linkedin_login_button,
    handle_linkedin_callback,
    is_linkedin_configured
)


def login_screen():
    # Hide sidebar navigation before login and style the login buttons
    st.markdown("""
        <style>
            [data-testid="stSidebar"] {
                display: none;
            }
            /* Google blue branding for primary login button */
            .stButton > button[kind="primary"] {
                background-color: #4285F4 !important;
                border-color: #4285F4 !important;
            }
            .stButton > button[kind="primary"]:hover {
                background-color: #357ae8 !important;
                border-color: #357ae8 !important;
            }
            .stButton > button[kind="primary"]:active {
                background-color: #2a66c9 !important;
                border-color: #2a66c9 !important;
            }
            /* LinkedIn blue branding for link button */
            div[data-testid="stLinkButton"] {
                width: 100% !important;
                display: block !important;
            }
            div[data-testid="stLinkButton"] > a {
                background-color: #0077B5 !important;
                color: white !important;
                border: 1px solid #0077B5 !important;
                width: 100% !important;
                text-align: center !important;
                display: block !important;
                padding: 0.5rem 0.75rem !important;
                border-radius: 0.5rem !important;
                text-decoration: none !important;
                font-weight: 400 !important;
                font-size: 1rem !important;
                line-height: 1.6 !important;
                min-height: 2.5rem !important;
                box-sizing: border-box !important;
            }
            div[data-testid="stLinkButton"] > a:hover {
                background-color: #006396 !important;
                border-color: #006396 !important;
                color: white !important;
            }
            div[data-testid="stLinkButton"] > a:active {
                background-color: #005077 !important;
                border-color: #005077 !important;
                color: white !important;
            }
        </style>
    """, unsafe_allow_html=True)

    st.header("Please log in to access Quick Notes")
    st.subheader("Please log in.")

    # Google login
    render_login_button(label="🔵 Login with Google", type="primary", use_container_width=True)

    # LinkedIn login (if configured)
    if is_linkedin_configured():
        st.markdown("<div style='margin-top: 12px;'></div>", unsafe_allow_html=True)
        render_linkedin_login_button(label="🔗 Login with LinkedIn")


def main():
    st.set_page_config(page_title="Quick Notes", page_icon="📝", layout="wide")

    # Handle LinkedIn OAuth callback
    query_params = st.query_params

    # Check if this is a LinkedIn callback (has code and state parameters)
    if 'code' in query_params and 'state' in query_params and query_params.get('state', '').startswith('linkedin_'):
        # This is a LinkedIn OAuth callback
        code = query_params['code']
        state = query_params['state']

        # Only process if not already processed (check session state flag)
        if not st.session_state.get('linkedin_callback_processed'):
            # Show processing message
            with st.spinner("Processing LinkedIn login..."):
                # Handle the callback
                success = handle_linkedin_callback(code, state)

            if success:
                # Mark as processed to prevent re-processing on rerun
                st.session_state['linkedin_callback_processed'] = True

                # Clear query parameters
                try:
                    st.query_params.clear()
                except:
                    # Fallback for older Streamlit versions
                    pass

                # Small delay to ensure session state is saved
                import time
                time.sleep(0.5)

                # Rerun to show the main app (user is now logged in)
                st.rerun()
            else:
                st.error("Failed to complete LinkedIn login. Please try again.")
                # Clear login state
                if 'linkedin_login_initiated' in st.session_state:
                    del st.session_state['linkedin_login_initiated']
                if 'linkedin_oauth_state' in st.session_state:
                    del st.session_state['linkedin_oauth_state']

                # Clear query parameters
                try:
                    st.query_params.clear()
                except:
                    pass

                st.rerun()
        else:
            # Already processed, just clear params and continue
            try:
                st.query_params.clear()
            except:
                pass

    if not is_user_logged_in():
        login_screen()
        return

    # Header with compact layout
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.title("📝 Quick Notes")
    with col2:
        if st.button("🔄 Refresh", width="stretch"):
            st.rerun()
    with col3:
        if st.button("📥 Export CSV", width="stretch"):
            st.session_state['show_export'] = not st.session_state.get('show_export', False)

    # Initialize database
    db = JobSearchDB()

    # Get existing notes
    notes = db.get_quick_notes()

    # Display notes grouped by label - MOVED TO TOP FOR QUICK REFERENCE
    if notes:
        # Group notes by label
        grouped_notes = defaultdict(list)
        for note in notes:
            grouped_notes[note['label']].append(note)

        st.markdown("### 📋 Quick Reference")
        st.caption(f"{len(notes)} items · {len(grouped_notes)} categories")

        # Display each category - compact with inline category labels
        for label, label_notes in sorted(grouped_notes.items()):
            # Check if this category is being edited
            category_key = f"edit_category_{label}"
            is_editing_category = st.session_state.get(category_key, False)

            # Edit mode for this category
            if is_editing_category:
                # Show compact header when editing
                col1, col2 = st.columns([6, 0.5])
                with col1:
                    st.markdown(f"**✏️ Editing: {label}**")
                with col2:
                    pass
                with st.container():
                    with st.form(f"edit_category_form_{label}"):
                        # Category name (can be changed to move all items to different category)
                        new_category_name = st.text_input("Category Name", value=label, key=f"cat_name_{label}")

                        st.markdown("**Existing Content Entries:**")

                        # Show all existing entries with ability to edit or delete
                        entries_to_update = []
                        entries_to_delete = []

                        for idx, note in enumerate(label_notes):
                            note_id = note['id']
                            content = note['content']

                            col1, col2 = st.columns([5, 1])
                            with col1:
                                edited_content = st.text_input(
                                    f"Entry {idx+1}",
                                    value=content,
                                    key=f"edit_cat_content_{note_id}",
                                    label_visibility="collapsed"
                                )
                                entries_to_update.append({'id': note_id, 'content': edited_content})

                            with col2:
                                # Delete checkbox for this entry
                                delete_entry = st.checkbox("🗑️", key=f"delete_entry_{note_id}", label_visibility="collapsed")
                                if delete_entry:
                                    entries_to_delete.append(note_id)

                        # Add new content rows
                        st.markdown("**Add More Entries:**")
                        if f'edit_add_count_{label}' not in st.session_state:
                            st.session_state[f'edit_add_count_{label}'] = 0

                        # Create input fields for new content
                        for i in range(st.session_state[f'edit_add_count_{label}']):
                            st.text_input(
                                f"New {i+1}",
                                placeholder="New content entry...",
                                key=f"new_content_edit_{label}_{i}",
                                label_visibility="collapsed"
                            )

                        # Buttons
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            add_row = st.form_submit_button("➕ Add Row")

                        with col2:
                            save = st.form_submit_button("💾 Save", type="primary")

                        with col3:
                            cancel = st.form_submit_button("✕ Cancel")

                        # Handle button actions
                        if add_row:
                            st.session_state[f'edit_add_count_{label}'] += 1
                            st.rerun()

                        if save:
                            # Update existing entries
                            for entry in entries_to_update:
                                if entry['id'] not in entries_to_delete and entry['content'].strip():
                                    db.update_quick_note(entry['id'], new_category_name, entry['content'], note_type="text")

                            # Delete marked entries
                            for note_id in entries_to_delete:
                                db.delete_quick_note(note_id)

                            # Add new entries - read from session state after form submission
                            for i in range(st.session_state[f'edit_add_count_{label}']):
                                key = f"new_content_edit_{label}_{i}"
                                if key in st.session_state:
                                    new_content = st.session_state[key]
                                    if new_content and new_content.strip():
                                        db.add_quick_note(new_category_name, new_content, note_type="text")

                            # Reset state and clear input keys
                            for i in range(st.session_state[f'edit_add_count_{label}']):
                                key = f"new_content_edit_{label}_{i}"
                                if key in st.session_state:
                                    del st.session_state[key]

                            st.session_state[category_key] = False
                            st.session_state[f'edit_add_count_{label}'] = 0
                            st.success(f"✅ Updated category '{label}'")
                            st.rerun()

                        if cancel:
                            # Clear input keys
                            for i in range(st.session_state[f'edit_add_count_{label}']):
                                key = f"new_content_edit_{label}_{i}"
                                if key in st.session_state:
                                    del st.session_state[key]

                            st.session_state[category_key] = False
                            st.session_state[f'edit_add_count_{label}'] = 0
                            st.rerun()

            # Display mode - show category and content on one line
            else:
                for idx, note in enumerate(label_notes):
                    note_id = note['id']
                    content = note['content']

                    # Check if this individual note is being edited
                    note_edit_key = f"edit_note_{note_id}"
                    is_editing_note = st.session_state.get(note_edit_key, False)

                    col1, col2, col3, col4 = st.columns([1.5, 4, 0.35, 0.35])

                    with col1:
                        # Category label - show edit button only on first item
                        if idx == 0:
                            if st.button(f"📌 {label}", key=f"cat_label_{label}", width="stretch", help="Click to edit category"):
                                st.session_state[category_key] = True
                                st.rerun()
                        else:
                            # Empty space for subsequent items to align with first item
                            st.write("")

                    with col2:
                        if is_editing_note:
                            # Edit mode for individual entry
                            with st.form(f"edit_note_form_{note_id}"):
                                edited_content = st.text_input(
                                    "Edit content",
                                    value=content,
                                    key=f"edit_content_{note_id}",
                                    label_visibility="collapsed"
                                )

                                # Option to add new row
                                add_new_key = f"add_new_{note_id}"
                                if add_new_key not in st.session_state:
                                    st.session_state[add_new_key] = False

                                if st.session_state[add_new_key]:
                                    new_content = st.text_input(
                                        "New entry",
                                        placeholder="Enter new content...",
                                        key=f"new_entry_{note_id}",
                                        label_visibility="collapsed"
                                    )

                                col_save, col_delete, col_add, col_cancel = st.columns(4)
                                with col_save:
                                    save_clicked = st.form_submit_button("💾 Save", width="stretch")
                                    if save_clicked:
                                        if edited_content.strip():
                                            # Update the existing note
                                            db.update_quick_note(note_id, label, edited_content, note_type="text")
                                            
                                            # Add new row if provided
                                            if st.session_state[add_new_key]:
                                                new_entry_key = f"new_entry_{note_id}"
                                                new_val = st.session_state.get(new_entry_key, "")
                                                if new_val and new_val.strip():
                                                    db.add_quick_note(label, new_val.strip(), note_type="text")
                                            
                                            st.session_state[note_edit_key] = False
                                            st.session_state[add_new_key] = False
                                            st.success("✅ Updated!")
                                            st.rerun()
                                        else:
                                            st.error("Content cannot be empty")

                                with col_delete:
                                    if st.form_submit_button("🗑️ Delete", width="stretch"):
                                        db.delete_quick_note(note_id)
                                        st.session_state[note_edit_key] = False
                                        st.session_state[add_new_key] = False
                                        st.success("✅ Deleted!")
                                        st.rerun()

                                with col_add:
                                    if st.form_submit_button("➕ Add", width="stretch"):
                                        st.session_state[add_new_key] = True
                                        st.rerun()

                                with col_cancel:
                                    if st.form_submit_button("✕ Cancel", width="stretch"):
                                        st.session_state[note_edit_key] = False
                                        st.session_state[add_new_key] = False
                                        st.rerun()
                        else:
                            # Display mode - Show content
                            st.write(content)

                    with col3:
                        if not is_editing_note:
                            # Copy button using HTML component
                            import base64
                            encoded_content = base64.b64encode(content.encode('utf-8')).decode('utf-8')
                            button_id = f"copy_{note_id}"

                            copy_html = f"""
                            <!DOCTYPE html>
                            <html>
                            <head>
                                <style>
                                    body {{
                                        margin: 0;
                                        padding: 0;
                                        display: flex;
                                        align-items: center;
                                        justify-content: center;
                                        height: 100%;
                                    }}
                                    button {{
                                        width: 100%;
                                        height: 38px;
                                        padding: 0.25rem 0.75rem;
                                        background-color: rgb(255, 255, 255);
                                        color: rgb(49, 51, 63);
                                        border: 1px solid rgba(49, 51, 63, 0.2);
                                        border-radius: 0.5rem;
                                        cursor: pointer;
                                        font-size: 1rem;
                                        transition: all 0.3s;
                                    }}
                                    button:hover {{
                                        border-color: rgb(255, 75, 75);
                                        color: rgb(255, 75, 75);
                                    }}
                                </style>
                            </head>
                            <body>
                                <button id="{button_id}" title="Copy">📋</button>
                                <script>
                                    document.getElementById('{button_id}').addEventListener('click', function() {{
                                        const text = atob('{encoded_content}');
                                        const textarea = document.createElement('textarea');
                                        textarea.value = text;
                                        textarea.style.position = 'fixed';
                                        textarea.style.opacity = '0';
                                        document.body.appendChild(textarea);
                                        textarea.select();
                                        try {{
                                            document.execCommand('copy');
                                            this.textContent = '✓';
                                            setTimeout(() => {{ this.textContent = '📋'; }}, 1000);
                                        }} catch (err) {{
                                            console.error('Copy failed:', err);
                                        }}
                                        document.body.removeChild(textarea);
                                    }});
                                </script>
                            </body>
                            </html>
                            """
                            components.html(copy_html, height=38)
                        else:
                            st.write("")

                    with col4:
                        if not is_editing_note:
                            # Edit button - only show on first line of category
                            if idx == 0:
                                if st.button("✏️", key=f"edit_btn_{note_id}", width="stretch", help="Edit"):
                                    st.session_state[note_edit_key] = True
                                    st.rerun()
                            else:
                                # Empty space for subsequent items
                                st.write("")
                        else:
                            # Empty space when editing
                            st.write("")

    # Compact add form in expander with multiple content rows - MOVED TO BOTTOM
    st.markdown("---")
    with st.expander("➕ Add New Category", expanded=False):
        # Initialize number of content rows in session state
        if 'add_content_count' not in st.session_state:
            st.session_state['add_content_count'] = 1

        with st.form("add_note_form", clear_on_submit=False):
            # Get existing labels for autocomplete suggestions
            existing_labels = sorted(list(set([note['label'] for note in notes]))) if notes else []

            new_label = st.text_input(
                "Category Name",
                placeholder="e.g., Referral Codes, Phone Numbers, LinkedIn",
            )
            if existing_labels:
                st.caption(f"📌 Existing: {', '.join(existing_labels[:5])}")

            st.markdown("**Content Entries:**")

            # Display content input rows
            content_values = []
            for i in range(st.session_state['add_content_count']):
                col1, col2 = st.columns([5, 1])
                with col1:
                    content_val = st.text_input(
                        f"Content {i+1}",
                        placeholder=f"e.g., Company A: REF123 or https://linkedin.com/in/...",
                        key=f"add_content_{i}",
                        label_visibility="collapsed"
                    )
                    content_values.append(content_val)
                with col2:
                    # Only show remove button if more than 1 row
                    if st.session_state['add_content_count'] > 1:
                        if st.form_submit_button("✕", key=f"remove_add_{i}"):
                            st.session_state['add_content_count'] -= 1
                            st.rerun()

            # Add row button and Submit
            col1, col2 = st.columns(2)
            with col1:
                if st.form_submit_button("➕ Add Another Row"):
                    st.session_state['add_content_count'] += 1
                    st.rerun()

            with col2:
                submit = st.form_submit_button("💾 Save All", type="primary", width="stretch")

            if submit:
                if not new_label:
                    st.error("Please enter a category name")
                else:
                    # Filter out empty content entries
                    valid_contents = [c for c in content_values if c.strip()]

                    if not valid_contents:
                        st.error("Please enter at least one content entry")
                    else:
                        # Add all content entries
                        for content in valid_contents:
                            db.add_quick_note(new_label, content, note_type="text")

                        st.success(f"✅ Added {len(valid_contents)} items to '{new_label}'")
                        # Reset form
                        st.session_state['add_content_count'] = 1
                        st.rerun()

    # Show example if no notes
    if not notes:
        with st.expander("💡 Example entries"):
            st.markdown("""
            **LinkedIn**
            - https://linkedin.com/in/yourprofile
            - https://linkedin.com/company/target

            **Referral Codes**
            - Company A: REF123
            - Company B: REF456

            **Phone Numbers**
            - (555) 123-4567
            - (555) 987-6543
            """)

    # Export section - only show if button clicked
    if st.session_state.get('show_export', False) and notes:
        with st.container():
            df = pd.DataFrame([{'Label': n['label'], 'Content': n['content']} for n in notes])
            csv = df.to_csv(index=False)
            st.download_button(
                label="📥 Download CSV",
                data=csv,
                file_name="quick_notes.csv",
                mime="text/csv",
                width="stretch"
            )
            if st.button("✕ Close", width="stretch"):
                st.session_state['show_export'] = False
                st.rerun()


if __name__ == "__main__":
    main()
