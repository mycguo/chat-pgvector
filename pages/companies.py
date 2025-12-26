"""
Companies Page

Track companies you've applied to and companies you want to target.
"""

import streamlit as st
import sys
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, '.')

from storage.json_db import JobSearchDB
from storage.auth_utils import is_user_logged_in, logout, render_login_button
from models.company import Company, create_company


def login_screen():
    # Hide sidebar navigation before login and style the login button with Google blue
    st.markdown("""
        <style>
            [data-testid="stSidebar"] {
                display: none;
            }
            /* Google blue branding for login button */
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
        </style>
    """, unsafe_allow_html=True)

    st.header("Please log in to access Companies")
    st.subheader("Please log in.")
    render_login_button(type="primary", use_container_width=True)


def show_company_card(company_dict: dict, db: JobSearchDB):
    """Display a company as a card"""
    company = Company.from_dict(company_dict)

    with st.container():
        col1, col2, col3, col4 = st.columns([3, 2, 1, 1])

        with col1:
            st.markdown(f"**{company.get_status_emoji()} {company.name}**")

            # Info badges
            badges = []
            if company.industry:
                badges.append(f"🏢 {company.industry}")
            if company.size:
                badges.append(f"{company.get_size_emoji()} {company.size.title()}")
            if company.location:
                badges.append(f"📍 {company.location}")

            if badges:
                st.caption(" • ".join(badges))

        with col2:
            st.write(f"**Priority:** {company.get_priority_emoji()} {company.priority}/10")
            if company.application_ids:
                st.caption(f"📝 {len(company.application_ids)} application(s)")

        with col3:
            st.caption(f"**{company.status.title()}**")

        with col4:
            if st.button("View", key=f"view_company_{company.id}", width="stretch"):
                st.session_state['view_company_id'] = company.id
                st.rerun()

        st.divider()


def show_company_detail(db: JobSearchDB, company_id: str):
    """Show detailed company view"""
    company_dict = db.get_company(company_id)
    if not company_dict:
        st.error(f"Company not found (ID: {company_id})")

        # Debug: Show what user_id we're using
        from storage.user_utils import get_user_id
        current_user = get_user_id()
        st.warning(f"Debug: Looking for company with user_id: {current_user}")

        # Debug: Check if company exists under different user_id
        try:
            from storage.pg_connection import get_connection
            with get_connection() as conn:
                cursor = conn.cursor()
                # Query the vector_documents table directly
                cursor.execute(
                    """
                    SELECT user_id, metadata
                    FROM vector_documents
                    WHERE collection_name = 'companies'
                    AND metadata->>'record_id' = %s
                    LIMIT 1
                    """,
                    (company_id,)
                )
                result = cursor.fetchone()
                if result:
                    stored_user_id, metadata = result
                    st.warning(f"Found company in DB but with different user_id: {stored_user_id}")
                    st.info("💡 This is a data migration issue. The company was saved with a different user ID.")

                    # Show migration button
                    if st.button("🔧 Fix this company (update user_id)"):
                        with get_connection() as conn2:
                            cursor2 = conn2.cursor()
                            cursor2.execute(
                                """
                                UPDATE vector_documents
                                SET user_id = %s
                                WHERE collection_name = 'companies'
                                AND metadata->>'record_id' = %s
                                """,
                                (current_user, company_id)
                            )
                            conn2.commit()
                        st.success("✅ Company user_id updated! Refresh the page.")
                        st.rerun()
                else:
                    st.warning("Company ID not found in database at all")
        except Exception as e:
            st.error(f"Debug error: {e}")

        if st.button("← Back to Companies"):
            del st.session_state['view_company_id']
            st.rerun()
        return

    company = Company.from_dict(company_dict)

    # Header
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        st.title(f"{company.get_status_emoji()} {company.name}")
    with col2:
        if st.button("✏️ Edit", width="stretch"):
            st.session_state['edit_company_id'] = company_id
            st.rerun()
    with col3:
        if st.button("← Back", width="stretch"):
            del st.session_state['view_company_id']
            st.rerun()

    # Basic Info
    st.markdown("### 📋 Basic Information")
    col1, col2 = st.columns(2)

    with col1:
        st.write(f"**Status:** {company.get_status_emoji()} {company.status.title()}")
        st.write(f"**Priority:** {company.get_priority_emoji()} {company.priority}/10")
        if company.industry:
            st.write(f"**Industry:** {company.industry}")
        if company.size:
            st.write(f"**Size:** {company.get_size_emoji()} {company.size.title()}")

    with col2:
        if company.location:
            st.write(f"**Location:** 📍 {company.location}")
        if company.website:
            st.write(f"**Website:** [{company.website}]({company.website})")
        if company.tags:
            st.write(f"**Tags:** {', '.join([f'`{tag}`' for tag in company.tags])}")

    # Description
    if company.description:
        st.markdown("### 📝 Description")
        st.write(company.description)

    # Culture Notes
    if company.culture_notes:
        st.markdown("### 🏛️ Culture Notes")
        st.write(company.culture_notes)

    # Tech Stack
    if company.tech_stack:
        st.markdown("### 💻 Tech Stack")
        st.write(", ".join([f"`{tech}`" for tech in company.tech_stack]))

    # Pros/Cons
    col1, col2 = st.columns(2)
    with col1:
        if company.pros:
            st.markdown("### ✅ Pros")
            for pro in company.pros:
                st.write(f"• {pro}")

    with col2:
        if company.cons:
            st.markdown("### ❌ Cons")
            for con in company.cons:
                st.write(f"• {con}")

    # Contacts
    if company.contacts:
        st.markdown("### 👥 Contacts")
        for contact in company.contacts:
            st.write(f"• {contact}")

    # Notes
    if company.notes:
        st.markdown("### 📝 Notes")
        st.write(company.notes)

    # Applications
    if company.application_ids:
        st.markdown("### 📝 Related Applications")
        st.write(f"{len(company.application_ids)} application(s) for this company")

    # Metadata
    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        st.caption(f"Created: {company.created_at[:10]}")
    with col2:
        st.caption(f"Updated: {company.updated_at[:10]}")


def show_add_edit_form(db: JobSearchDB, company_id: str = None):
    """Show add/edit company form"""
    is_edit = company_id is not None

    if is_edit:
        company_dict = db.get_company(company_id)
        if not company_dict:
            st.error("Company not found")
            return
        company = Company.from_dict(company_dict)

        # Header with back button
        col1, col2 = st.columns([4, 1])
        with col1:
            st.title(f"✏️ Edit {company.name}")
        with col2:
            if st.button("← Back", width="stretch"):
                del st.session_state['edit_company_id']
                st.session_state['view_company_id'] = company_id
                st.rerun()
    else:
        # Header with back button
        col1, col2 = st.columns([4, 1])
        with col1:
            st.title("➕ Add New Company")
        with col2:
            if st.button("← Back", width="stretch"):
                if 'add_company_mode' in st.session_state:
                    del st.session_state['add_company_mode']
                st.rerun()
        company = None

    with st.form("company_form"):
        # Basic Info
        st.markdown("### 📋 Basic Information")

        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input(
                "Company Name *",
                value=company.name if company else "",
                placeholder="e.g., Google, Microsoft"
            )

            status = st.selectbox(
                "Status *",
                ["target", "applied", "interviewing", "offer", "rejected", "accepted"],
                index=["target", "applied", "interviewing", "offer", "rejected", "accepted"].index(company.status) if company else 0
            )

            industry = st.text_input(
                "Industry",
                value=company.industry if company else "",
                placeholder="e.g., Technology, Finance, Healthcare"
            )

        with col2:
            priority = st.slider(
                "Priority",
                min_value=1,
                max_value=10,
                value=company.priority if company else 5,
                help="How interested are you in this company?"
            )

            size = st.selectbox(
                "Company Size",
                ["", "startup", "small", "medium", "large", "enterprise"],
                index=["", "startup", "small", "medium", "large", "enterprise"].index(company.size) if company and company.size else 0
            )

            location = st.text_input(
                "Location",
                value=company.location if company else "",
                placeholder="e.g., San Francisco, CA"
            )

        col1, col2 = st.columns(2)
        with col1:
            website = st.text_input(
                "Website",
                value=company.website if company else "",
                placeholder="https://company.com"
            )
        with col2:
            tags_input = st.text_input(
                "Tags (comma-separated)",
                value=", ".join(company.tags) if company and company.tags else "",
                placeholder="e.g., AI, Remote, Series B"
            )

        # Description
        st.markdown("### 📝 Details")

        description = st.text_area(
            "Company Description",
            value=company.description if company else "",
            placeholder="What does this company do?",
            height=100
        )

        culture_notes = st.text_area(
            "Culture Notes",
            value=company.culture_notes if company else "",
            placeholder="Notes about company culture, values, work environment...",
            height=100
        )

        # Tech Stack
        tech_stack_input = st.text_area(
            "Tech Stack (one per line)",
            value="\n".join(company.tech_stack) if company and company.tech_stack else "",
            placeholder="Python\nReact\nAWS",
            height=100
        )

        # Pros/Cons
        col1, col2 = st.columns(2)
        with col1:
            pros_input = st.text_area(
                "Pros (one per line)",
                value="\n".join(company.pros) if company and company.pros else "",
                placeholder="Great culture\nCompetitive salary\nRemote-friendly",
                height=100
            )

        with col2:
            cons_input = st.text_area(
                "Cons (one per line)",
                value="\n".join(company.cons) if company and company.cons else "",
                placeholder="Long hours\nLimited growth",
                height=100
            )

        # Contacts
        contacts_input = st.text_area(
            "Contacts (one per line)",
            value="\n".join(company.contacts) if company and company.contacts else "",
            placeholder="John Doe - Engineering Manager\nhttps://linkedin.com/in/...",
            height=100
        )

        # Notes
        notes = st.text_area(
            "Additional Notes",
            value=company.notes if company else "",
            placeholder="Any other notes about this company...",
            height=100
        )

        # Submit buttons
        col1, col2, col3 = st.columns([1, 1, 3])
        with col1:
            submit = st.form_submit_button("💾 Save" if is_edit else "➕ Add Company", type="primary", width="stretch")
        with col2:
            cancel = st.form_submit_button("✕ Cancel", width="stretch")

        if cancel:
            if is_edit:
                del st.session_state['edit_company_id']
                st.session_state['view_company_id'] = company_id
            else:
                # Clear add mode
                if 'add_company_mode' in st.session_state:
                    del st.session_state['add_company_mode']
            st.rerun()

        if submit:
            if not name:
                st.error("Please enter a company name")
            else:
                # Parse lists
                tags = [t.strip() for t in tags_input.split(",") if t.strip()]
                tech_stack = [t.strip() for t in tech_stack_input.split("\n") if t.strip()]
                pros = [p.strip() for p in pros_input.split("\n") if p.strip()]
                cons = [c.strip() for c in cons_input.split("\n") if c.strip()]
                contacts = [c.strip() for c in contacts_input.split("\n") if c.strip()]

                if is_edit:
                    # Update existing company
                    company.name = name
                    company.status = status
                    company.priority = priority
                    company.industry = industry
                    company.size = size
                    company.location = location
                    company.website = website
                    company.description = description
                    company.culture_notes = culture_notes
                    company.tech_stack = tech_stack
                    company.pros = pros
                    company.cons = cons
                    company.contacts = contacts
                    company.tags = tags
                    company.notes = notes

                    db.update_company(company.to_dict())
                    st.success(f"✅ Updated {name}")
                    del st.session_state['edit_company_id']
                    st.session_state['view_company_id'] = company_id
                    st.rerun()
                else:
                    # Create new company
                    try:
                        from storage.user_utils import get_user_id
                        current_user = get_user_id()

                        # Log to Python console (visible in Streamlit Cloud logs)
                        import sys
                        print(f"[COMPANY ADD] Starting to add company: {name}", file=sys.stderr)
                        print(f"[COMPANY ADD] Current user_id: {current_user}", file=sys.stderr)

                        new_company = create_company(
                            name=name,
                            status=status,
                            website=website,
                            industry=industry,
                            size=size,
                            location=location,
                            description=description,
                            priority=priority
                        )
                        new_company.culture_notes = culture_notes
                        new_company.tech_stack = tech_stack
                        new_company.pros = pros
                        new_company.cons = cons
                        new_company.contacts = contacts
                        new_company.tags = tags
                        new_company.notes = notes

                        print(f"[COMPANY ADD] Generated company ID: {new_company.id}", file=sys.stderr)
                        print(f"[COMPANY ADD] Calling db.add_company()...", file=sys.stderr)

                        company_id = db.add_company(new_company.to_dict())

                        print(f"[COMPANY ADD] db.add_company() returned: {company_id}", file=sys.stderr)

                        # Verify it was saved
                        from storage.pg_connection import get_connection
                        with get_connection() as conn:
                            cursor = conn.cursor()
                            cursor.execute(
                                """
                                SELECT COUNT(*)
                                FROM vector_documents
                                WHERE collection_name = 'companies'
                                AND metadata->>'record_id' = %s
                                """,
                                (company_id,)
                            )
                            count = cursor.fetchone()[0]
                            print(f"[COMPANY ADD] Verification query returned: {count} records", file=sys.stderr)

                        st.success(f"✅ Added {name}")
                        st.info(f"**Debug Info:**")
                        st.code(f"""
Company ID: {company_id}
User ID: {current_user}
Records saved: {count}
                        """)

                        st.warning("**Don't click anything yet!** Check the info above, then click 'View Company' below.")

                        # Don't auto-redirect - let user see the debug info
                        if st.button("👁️ View Company", type="primary"):
                            if 'add_company_mode' in st.session_state:
                                del st.session_state['add_company_mode']
                            st.session_state['view_company_id'] = company_id
                            st.rerun()

                        if st.button("← Back to List"):
                            if 'add_company_mode' in st.session_state:
                                del st.session_state['add_company_mode']
                            st.rerun()

                    except Exception as e:
                        print(f"[COMPANY ADD ERROR] {e}", file=sys.stderr)
                        import traceback
                        traceback.print_exc(file=sys.stderr)
                        st.error(f"❌ Error adding company: {e}")
                        st.code(traceback.format_exc())


def main():
    st.set_page_config(page_title="Companies", page_icon="🏢", layout="wide")

    if not is_user_logged_in():
        login_screen()
        return

    # Initialize database
    db = JobSearchDB()

    # Check for add mode
    if st.session_state.get('add_company_mode'):
        show_add_edit_form(db)
        return

    # Check for edit mode
    if st.session_state.get('edit_company_id'):
        show_add_edit_form(db, st.session_state['edit_company_id'])
        return

    # Check for detail view
    if st.session_state.get('view_company_id'):
        show_company_detail(db, st.session_state['view_company_id'])
        return

    # Main companies list view
    st.title("🏢 Companies")
    st.markdown("Track companies you've applied to and companies you want to target")

    # Get all companies
    companies = db.get_companies()

    # Top actions
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        search_query = st.text_input(
            "🔍 Search companies",
            placeholder="Search by name, industry, or notes...",
        )
    with col2:
        st.write("")  # Spacer
    with col3:
        st.write("")  # Spacer
        if st.button("➕ Add Company", type="primary", width="stretch", key="add_company_top"):
            st.session_state['add_company_mode'] = True
            st.rerun()

    # Filters
    with st.sidebar:
        st.header("🔍 Filters")

        # Status filter
        all_statuses = ["All", "target", "applied", "interviewing", "offer", "rejected", "accepted"]
        filter_status = st.selectbox("Status", all_statuses)

        # Priority filter
        filter_priority = st.selectbox(
            "Priority",
            ["All", "High (8-10)", "Medium (4-7)", "Low (1-3)"]
        )

        # Sort
        st.divider()
        st.header("📊 Sort By")
        sort_by = st.selectbox(
            "Sort",
            [
                "Priority (High to Low)",
                "Priority (Low to High)",
                "Name (A-Z)",
                "Name (Z-A)",
                "Created (Newest)",
                "Created (Oldest)",
            ]
        )

        st.divider()
        st.header("📈 Stats")
        st.metric("Total Companies", len(companies))

        # Count by status
        status_counts = {}
        for company in companies:
            status = company.get('status', 'target')
            status_counts[status] = status_counts.get(status, 0) + 1

        if status_counts:
            for status, count in sorted(status_counts.items()):
                st.caption(f"{status.title()}: {count}")

    # Apply filters
    filtered_companies = companies.copy()

    # Status filter
    if filter_status != "All":
        filtered_companies = [c for c in filtered_companies if c.get('status') == filter_status]

    # Priority filter
    if filter_priority == "High (8-10)":
        filtered_companies = [c for c in filtered_companies if c.get('priority', 5) >= 8]
    elif filter_priority == "Medium (4-7)":
        filtered_companies = [c for c in filtered_companies if 4 <= c.get('priority', 5) <= 7]
    elif filter_priority == "Low (1-3)":
        filtered_companies = [c for c in filtered_companies if c.get('priority', 5) <= 3]

    # Search filter
    if search_query:
        search_lower = search_query.lower()
        filtered_companies = [
            c for c in filtered_companies
            if search_lower in c.get('name', '').lower() or
               search_lower in c.get('industry', '').lower() or
               search_lower in c.get('notes', '').lower() or
               search_lower in c.get('description', '').lower()
        ]

    # Apply sorting
    if sort_by == "Priority (High to Low)":
        filtered_companies.sort(key=lambda x: x.get('priority', 5), reverse=True)
    elif sort_by == "Priority (Low to High)":
        filtered_companies.sort(key=lambda x: x.get('priority', 5))
    elif sort_by == "Name (A-Z)":
        filtered_companies.sort(key=lambda x: x.get('name', '').lower())
    elif sort_by == "Name (Z-A)":
        filtered_companies.sort(key=lambda x: x.get('name', '').lower(), reverse=True)
    elif sort_by == "Created (Newest)":
        filtered_companies.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    elif sort_by == "Created (Oldest)":
        filtered_companies.sort(key=lambda x: x.get('created_at', ''))

    # Display results
    st.write(f"**Showing {len(filtered_companies)} of {len(companies)} companies**")

    if len(filtered_companies) == 0:
        st.info("🔍 No companies found. Add your first company to get started!")
        if st.button("➕ Add Company", type="primary", key="add_company_empty"):
            st.session_state['add_company_mode'] = True
            st.rerun()
    else:
        for company_dict in filtered_companies:
            show_company_card(company_dict, db)

    # Bottom navigation
    st.divider()
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("🏠 Home", width="stretch"):
            st.switch_page("app.py")

    with col2:
        if st.button("📝 Applications", width="stretch"):
            st.switch_page("pages/applications.py")

    with col3:
        if st.button("🎯 Interview Prep", width="stretch"):
            st.switch_page("pages/interview_prep.py")

    with col4:
        if st.button("➕ Add Company", width="stretch", type="primary", key="add_company_bottom"):
            st.session_state['add_company_mode'] = True
            st.rerun()

    # Logout button
    st.divider()
    st.button("Log out", on_click=logout)


if __name__ == "__main__":
    main()
