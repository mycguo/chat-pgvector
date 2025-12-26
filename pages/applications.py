"""
Application Management Page

Manage all job applications in one place.
"""

import streamlit as st
import sys
from datetime import datetime
import json
from typing import Optional

# Add parent directory to path
sys.path.insert(0, '.')

from models.application import Application, ContactLink, create_application
from storage.json_db import JobSearchDB
from ai.job_matcher import JobMatcher, get_default_user_profile
from storage.auth_utils import is_user_logged_in, logout, render_login_button
from pages.resume import fetch_job_description_from_url
from components.quick_notes import render_quick_notes


def build_contact_link(name: str, url: str, email: str = None) -> Optional[ContactLink]:
    """Create a ContactLink object when data is provided"""
    sanitized_name = (name or "").strip()
    sanitized_url = (url or "").strip()
    sanitized_email = (email or "").strip()

    if not sanitized_name and not sanitized_url and not sanitized_email:
        return None

    return ContactLink(
        name=sanitized_name or None,
        url=sanitized_url or None,
        email=sanitized_email or None
    )


def render_contact(label: str, contact: Optional[ContactLink]):
    """Display a contact link if available"""
    if not contact:
        return

    display_name = contact.name or label
    contact_info = []

    if contact.name:
        contact_info.append(display_name)
    
    if contact.email:
        contact_info.append(f"📧 {contact.email}")
    
    if contact.url:
        contact_info.append(f"[Link]({contact.url})")

    if contact_info:
        st.write(f"**{label}:** {' • '.join(contact_info)}")
    else:
        st.write(f"**{label}:** {display_name}")


def show_application_card(app: Application, db: JobSearchDB):
    """Display an application as a card with actions"""

    with st.container():
        col1, col2, col3, col4 = st.columns([3, 2, 2, 1])

        with col1:
            st.markdown(f"### {app.get_status_emoji()} **{app.company}**")
            st.markdown(f"**{app.role}**")
            if app.location:
                st.caption(f"📍 {app.location}")

        with col2:
            st.write("**Applied**")
            st.write(app.applied_date)
            days = app.get_days_since_applied()
            if days > 0:
                st.caption(f"({days} days ago)")

        with col3:
            st.write("**Status**")
            status_colors = {
                "applied": "🔵",
                "screening": "🟡",
                "interview": "🟠",
                "offer": "🟢",
                "accepted": "✅",
                "rejected": "🔴",
                "withdrawn": "⚫"
            }
            st.markdown(f"{status_colors.get(app.status, '⚪')} {app.get_display_status()}")

        with col4:
            if st.button("View", key=f"view_{app.id}"):
                st.session_state['view_application_id'] = app.id
                st.rerun()

        # Expandable details
        with st.expander("📋 Details & AI Analysis"):
            # Basic info
            if app.salary_range:
                st.write(f"**Salary:** {app.salary_range}")

            if app.job_url:
                st.write(f"**Job URL:** [{app.job_url}]({app.job_url})")

            if app.recruiter_contact or app.hiring_manager_contact:
                st.write("**👥 Contacts:**")
                render_contact("Recruiter", app.recruiter_contact)
                render_contact("Hiring Manager", app.hiring_manager_contact)

            # Match score
            if app.match_score and app.match_score > 0:
                st.write(f"**Match Score:** {app.match_score * 100:.0f}%")
                st.progress(app.match_score)

                # Color-coded recommendation
                score_pct = app.match_score * 100
                if score_pct >= 80:
                    st.success("🎯 Excellent match!")
                elif score_pct >= 60:
                    st.info("👍 Good match")
                else:
                    st.warning("⚠️ Moderate match")

            # Job requirements (if analyzed)
            if app.job_requirements:
                st.divider()
                st.write("**🤖 AI-Extracted Requirements:**")

                reqs = app.job_requirements

                col1, col2 = st.columns(2)
                with col1:
                    if reqs.get("required_skills"):
                        st.write("**Required Skills:**")
                        for skill in reqs["required_skills"][:5]:
                            st.write(f"• {skill}")

                    if reqs.get("years_experience"):
                        st.write(f"**Experience:** {reqs['years_experience']}")

                with col2:
                    if reqs.get("preferred_skills"):
                        st.write("**Preferred Skills:**")
                        for skill in reqs["preferred_skills"][:5]:
                            st.write(f"• {skill}")

                    if reqs.get("role_level"):
                        st.write(f"**Level:** {reqs['role_level']}")

            # AI Analysis button (if not already analyzed)
            if not app.match_score or app.match_score == 0:
                has_description = bool(app.job_description and app.job_description.strip())
                has_job_url = bool(app.job_url and app.job_url.strip())

                if has_description or has_job_url:
                    st.divider()
                    if st.button("🤖 Run AI Analysis", key=f"analyze_{app.id}"):
                        st.info("💡 Click 'View' button to go to the Analysis tab for detailed AI analysis")

            # Generate cover letter button
            if app.job_description:
                st.divider()
                cover_letter_key_card = f'cover_letter_card_{app.id}'
                current_cover_letter_card = app.cover_letter or st.session_state.get(cover_letter_key_card, "")
                
                if st.button("✍️ Generate Cover Letter", key=f"coverletter_{app.id}"):
                    with st.spinner("Generating cover letter..."):
                        try:
                            matcher = JobMatcher()
                            profile = get_default_user_profile()

                            cover_letter = matcher.generate_cover_letter(
                                company=app.company,
                                role=app.role,
                                job_requirements=app.job_requirements or {},
                                user_profile=profile,
                                job_description=app.job_description
                            )

                            st.session_state[cover_letter_key_card] = cover_letter
                            current_cover_letter_card = cover_letter
                            st.success("✅ Cover letter generated!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {str(e)}")
                            st.caption("Note: Requires valid Google API key")
                
                # Show cover letter if available
                if current_cover_letter_card:
                    edited_cover_letter_card = st.text_area(
                        "Cover Letter:",
                        value=current_cover_letter_card,
                        height=300,
                        key=f"cover_letter_text_card_{app.id}"
                    )
                    
                    if st.button("💾 Save Cover Letter", key=f"save_cover_card_{app.id}", width="stretch"):
                        db.update_application(app.id, {'cover_letter': edited_cover_letter_card})
                        st.session_state[cover_letter_key_card] = edited_cover_letter_card
                        st.success("✅ Cover letter saved!")
                        st.rerun()
                    
                    if app.cover_letter:
                        st.caption("💾 Saved with this application")

            if app.notes:
                st.write("**Notes:**")
                st.text_area(
                    "Application notes",
                    value=app.notes,
                    height=100,
                    disabled=True,
                    key=f"notes_view_{app.id}",
                    label_visibility="collapsed"
                )

            # Timeline
            if len(app.timeline) > 0:
                st.write("**Timeline:**")
                for event in app.timeline:
                    st.write(f"- {event.date}: {event.event_type.title()}")
                    if event.notes:
                        st.caption(f"  {event.notes}")

            # Add note button
            st.divider()
            new_note = st.text_input("Add a note:", key=f"add_note_{app.id}")
            if st.button("Add Note", key=f"add_note_btn_{app.id}"):
                if new_note:
                    db.add_application_note(app.id, new_note)
                    st.success("Note added!")
                    st.rerun()

        st.divider()


def show_application_detail(db: JobSearchDB, app_id: str):
    """Show detailed view of an application with edit capability"""
    app = db.get_application(app_id)

    if not app:
        st.error("Application not found!")
        return

    # Header
    col1, col2 = st.columns([4, 1])

    with col1:
        st.title(f"{app.get_status_emoji()} {app.company} - {app.role}")
        st.caption(f"Applied on {app.applied_date} • Status: {app.get_display_status()}")

    with col2:
        if st.button("← Back to List"):
            del st.session_state['view_application_id']
            st.rerun()

    st.divider()

    # Tabs for organization
    tab1, tab2, tab3, tab4 = st.tabs(["📝 Details", "📊 Analysis", "📅 Timeline", "✏️ Edit Application"])

    with tab1:
        st.subheader("Application Details")

        col1, col2 = st.columns(2)

        with col1:
            st.write("**Basic Information:**")
            st.write(f"• Company: {app.company}")
            st.write(f"• Role: {app.role}")
            st.write(f"• Location: {app.location or 'Not specified'}")
            st.write(f"• Applied: {app.applied_date}")
            if app.salary_range:
                st.write(f"• Salary Range: {app.salary_range}")

        with col2:
            st.write("**Links & Resources:**")
            if app.job_url:
                st.markdown(f"• [Job Posting]({app.job_url})")
            else:
                st.write("• No job URL provided")

            days_ago = app.get_days_since_applied()
            st.write(f"• Days since applied: {days_ago}")

            if app.recruiter_contact or app.hiring_manager_contact:
                st.write("**Key Contacts:**")
                render_contact("Recruiter", app.recruiter_contact)
                render_contact("Hiring Manager", app.hiring_manager_contact)

        if app.job_description:
            st.divider()
            st.subheader("Job Description")
            with st.expander("View full job description"):
                st.text_area(
                    "Description",
                    value=app.job_description,
                    height=300,
                    disabled=True,
                    key=f"job_desc_view_{app.id}"
                )

        if app.notes:
            st.divider()
            st.subheader("Notes")
            st.text_area(
                "Your notes",
                value=app.notes,
                height=150,
                disabled=True,
                key=f"notes_view_{app.id}"
            )

    with tab2:
        st.subheader("AI Analysis & Match Score")

        # Determine if we can run analysis (need either job description or job URL)
        has_description = bool(app.job_description and app.job_description.strip())
        has_job_url = bool(app.job_url and app.job_url.strip())
        can_analyze = has_description or has_job_url

        # Button to run/re-run analysis
        if can_analyze:
            analyze_button_label = "🔄 Re-analyze with AI" if (app.match_score and app.match_score > 0) else "🤖 Analyze with AI"

            # Show what will be analyzed
            if has_description and has_job_url:
                st.caption("ℹ️ Will use existing job description for analysis")
            elif has_job_url and not has_description:
                st.caption(f"ℹ️ Will fetch job description from: {app.job_url[:60]}...")

            run_analysis = st.button(analyze_button_label, type="primary", width="stretch")

            if run_analysis:
                job_description_to_analyze = None

                # First, try to use existing job description
                if has_description:
                    job_description_to_analyze = app.job_description
                # Otherwise, fetch from URL
                elif has_job_url:
                    with st.spinner(f"🌐 Fetching job description from URL..."):
                        success, fetched_content = fetch_job_description_from_url(app.job_url)

                        if success:
                            st.success("✅ Job description fetched successfully!")
                            job_description_to_analyze = fetched_content

                            # Save the fetched description to the database
                            db.update_application(app_id, {
                                'job_description': fetched_content
                            })
                            st.info("💾 Job description saved to application")
                        else:
                            st.error(f"❌ Failed to fetch job description: {fetched_content}")
                            st.caption("Please add the job description manually in the Edit tab and try again.")

                # Run AI analysis if we have a description
                if job_description_to_analyze:
                    with st.spinner("🤖 Analyzing job description with AI..."):
                        try:
                            matcher = JobMatcher()

                            # Extract requirements
                            job_requirements = matcher.extract_requirements(job_description_to_analyze)

                            # Calculate match score
                            user_profile = get_default_user_profile()
                            match_analysis = matcher.calculate_match_score(
                                job_requirements,
                                user_profile
                            )

                            match_score = match_analysis.get("match_score", 0)
                            overall_score = match_analysis.get("overall_score", 0)

                            # Update application in database
                            db.update_application(app_id, {
                                'job_requirements': job_requirements,
                                'match_score': match_score
                            })

                            st.success(f"✅ Analysis complete! Match Score: {overall_score}/100")

                            # Show quick preview
                            with st.expander("📋 View Analysis Summary", expanded=True):
                                col1, col2 = st.columns(2)
                                with col1:
                                    st.write("**Matching Skills:**")
                                    for skill in match_analysis.get("matching_skills", [])[:5]:
                                        st.write(f"✅ {skill}")
                                with col2:
                                    st.write("**Missing Skills:**")
                                    for skill in match_analysis.get("missing_skills", [])[:5]:
                                        st.write(f"⚠️ {skill}")

                                st.write("**Recommendation:**",
                                        match_analysis.get("recommendation", "Review manually"))

                            st.rerun()

                        except Exception as e:
                            st.error(f"❌ AI analysis failed: {str(e)}")
                            st.caption("Please check that your Google API key is configured correctly.")
        else:
            st.warning("⚠️ No job description or job URL available. Add either one in the Edit tab to enable AI analysis.")

        st.divider()

        if app.match_score and app.match_score > 0:
            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric(
                    "Match Score",
                    f"{app.match_score * 100:.0f}%",
                    help="AI-calculated match score"
                )

            with col2:
                score_pct = app.match_score * 100
                if score_pct >= 80:
                    st.success("🎯 Excellent match!")
                elif score_pct >= 60:
                    st.info("👍 Good match")
                else:
                    st.warning("⚠️ Moderate match")

            with col3:
                st.metric("Days Active", app.get_days_since_applied())

            st.divider()
            st.progress(app.match_score)
        else:
            st.info("💡 Click the button above to run AI analysis on this application")

        # Job requirements
        if app.job_requirements:
            st.divider()
            st.subheader("Extracted Requirements")

            reqs = app.job_requirements

            col1, col2 = st.columns(2)

            with col1:
                if reqs.get("required_skills"):
                    st.write("**Required Skills:**")
                    for skill in reqs["required_skills"]:
                        st.write(f"• {skill}")

                if reqs.get("years_experience"):
                    st.write(f"**Experience Required:** {reqs['years_experience']}")

            with col2:
                if reqs.get("preferred_skills"):
                    st.write("**Preferred Skills:**")
                    for skill in reqs["preferred_skills"]:
                        st.write(f"• {skill}")

                if reqs.get("role_level"):
                    st.write(f"**Level:** {reqs['role_level']}")

        # Generate and manage cover letter
        if app.job_description:
            st.divider()
            st.subheader("Cover Letter")
            
            # Use saved cover letter if available, otherwise use session state or empty
            cover_letter_key = f'cover_letter_{app.id}'
            current_cover_letter = app.cover_letter or st.session_state.get(cover_letter_key, "")
            
            # Generate button
            if st.button("✍️ Generate Cover Letter", width="stretch"):
                with st.spinner("Generating cover letter..."):
                    try:
                        matcher = JobMatcher()
                        profile = get_default_user_profile()

                        generated_letter = matcher.generate_cover_letter(
                            company=app.company,
                            role=app.role,
                            job_requirements=app.job_requirements or {},
                            user_profile=profile,
                            job_description=app.job_description
                        )

                        # Store in session state
                        st.session_state[cover_letter_key] = generated_letter
                        st.success("✅ Cover letter generated!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
            
            # Display and edit cover letter
            if current_cover_letter:
                edited_cover_letter = st.text_area(
                    "Cover Letter:",
                    value=current_cover_letter,
                    height=400,
                    key=f"cover_letter_text_{app.id}",
                    help="Edit the cover letter as needed, then click Save to store it with this application."
                )
                
                # Save button row
                col1, col2 = st.columns([3, 1])
                with col2:
                    if st.button("💾 Save Cover Letter", type="primary", width="stretch", key=f"save_cover_{app.id}"):
                        # Save to database
                        db.update_application(app_id, {'cover_letter': edited_cover_letter})
                        # Update session state
                        st.session_state[cover_letter_key] = edited_cover_letter
                        st.success("✅ Cover letter saved!")
                        st.rerun()
                
                # Show saved indicator if cover letter is already saved
                if app.cover_letter:
                    st.caption("💾 Cover letter is saved with this application")
            else:
                st.info("💡 Click 'Generate Cover Letter' to create a personalized cover letter for this application.")

    with tab3:
        st.subheader("Application Timeline")

        if app.timeline:
            for event in app.timeline:
                col1, col2 = st.columns([1, 3])
                with col1:
                    st.write(f"**{event.date}**")
                with col2:
                    st.write(f"{event.event_type.title()}")
                    if event.notes:
                        st.caption(event.notes)
                st.divider()
        else:
            st.info("No timeline events yet")

        # Add event
        st.subheader("Add Timeline Event")
        with st.form(f"add_event_{app.id}"):
            col1, col2, col3 = st.columns(3)
            with col1:
                event_type = st.selectbox(
                    "Event Type",
                    ["screening", "interview", "offer", "rejected", "withdrawn", "follow_up", "other"]
                )
            with col2:
                event_date = st.date_input("Event Date", value=datetime.now())
            with col3:
                event_time = st.time_input("Event Time", value=datetime.now().time())

            event_notes = st.text_area("Notes", placeholder="Add details about this event...")

            if st.form_submit_button("Add Event"):
                # Add timeline event with the specified date and time
                event_date_str = event_date.strftime("%Y-%m-%d")
                event_time_str = event_time.strftime("%I:%M %p")
                
                # Include time in notes if provided
                notes_with_time = event_notes
                if event_time_str:
                    if notes_with_time:
                        notes_with_time = f"Time: {event_time_str}\n{notes_with_time}"
                    else:
                        notes_with_time = f"Time: {event_time_str}"
                
                success = db.add_timeline_event(app.id, event_type, event_date_str, notes_with_time)
                
                if success:
                    st.success("✅ Event added to timeline!")
                    st.rerun()
                else:
                    st.error("❌ Failed to add event. Please try again.")

    with tab4:
        # Edit form - shown directly when tab is clicked
        st.markdown("### ✏️ Edit Application Details")
        
        # Control form visibility - automatically expand when tab is active
        # Collapses after save/cancel
        edit_expanded_key = f'edit_expanded_{app.id}'
        collapse_flag_key = f'just_collapsed_{app.id}'
        
        # Check if we just collapsed (from Save/Cancel)
        just_collapsed = st.session_state.get(collapse_flag_key, False)
        
        # If we just collapsed, keep it collapsed for this render
        # The flag will be cleared when user interacts with any widget in the tab
        if just_collapsed:
            st.session_state[edit_expanded_key] = False
        else:
            # Tab is active and we didn't just collapse, so show the form
            st.session_state[edit_expanded_key] = True
        
        edit_expanded = st.session_state.get(edit_expanded_key, True)
        
        # If collapsed, show a button to expand (but make it minimal)
        if not edit_expanded:
            if st.button("✏️ Edit Application", type="primary", key=f"expand_edit_{app.id}"):
                st.session_state[edit_expanded_key] = True
                st.session_state[collapse_flag_key] = False
                st.rerun()
        
        # Render the form
        if edit_expanded:
            col1, col2 = st.columns(2)

            with col1:
                new_company = st.text_input("Company", value=app.company)
                new_role = st.text_input("Role", value=app.role)
                new_location = st.text_input("Location", value=app.location or "")

            with col2:
                new_status = st.selectbox(
                    "Status",
                    ["applied", "screening", "interview", "offer", "accepted", "rejected", "withdrawn"],
                    index=["applied", "screening", "interview", "offer", "accepted", "rejected", "withdrawn"].index(app.status)
                )
                new_applied_date = st.date_input(
                    "Applied Date",
                    value=datetime.strptime(app.applied_date, "%Y-%m-%d")
                )
                new_salary_range = st.text_input("Salary Range", value=app.salary_range or "")

            new_job_url = st.text_input("Job URL", value=app.job_url or "")

            new_job_description = st.text_area(
                "Job Description",
                value=app.job_description or "",
                height=200
            )

            new_notes = st.text_area(
                "Notes",
                value=app.notes or "",
                height=150
            )

            st.markdown("**Key Contacts**")
            edit_contact_col1, edit_contact_col2 = st.columns(2)

            with edit_contact_col1:
                recruiter_name_value = st.text_input(
                    "Recruiter Name",
                    value=app.recruiter_contact.name if app.recruiter_contact and app.recruiter_contact.name else "",
                    key=f"edit_recruiter_name_{app.id}"
                )
                recruiter_email_value = st.text_input(
                    "Recruiter Email",
                    value=app.recruiter_contact.email if app.recruiter_contact and app.recruiter_contact.email else "",
                    key=f"edit_recruiter_email_{app.id}"
                )
                recruiter_link_value = st.text_input(
                    "Recruiter Contact Link",
                    value=app.recruiter_contact.url if app.recruiter_contact and app.recruiter_contact.url else "",
                    key=f"edit_recruiter_link_{app.id}"
                )

            with edit_contact_col2:
                hiring_manager_name_value = st.text_input(
                    "Hiring Manager Name",
                    value=app.hiring_manager_contact.name if app.hiring_manager_contact and app.hiring_manager_contact.name else "",
                    key=f"edit_hiring_manager_name_{app.id}"
                )
                hiring_manager_email_value = st.text_input(
                    "Hiring Manager Email",
                    value=app.hiring_manager_contact.email if app.hiring_manager_contact and app.hiring_manager_contact.email else "",
                    key=f"edit_hiring_manager_email_{app.id}"
                )
                hiring_manager_link_value = st.text_input(
                    "Hiring Manager Contact Link",
                    value=app.hiring_manager_contact.url if app.hiring_manager_contact and app.hiring_manager_contact.url else "",
                    key=f"edit_hiring_manager_link_{app.id}"
                )

            # Action buttons
            col1, col2 = st.columns(2)

            with col1:
                save_clicked = st.button("💾 Save Changes", type="primary", width="stretch", key=f"save_btn_{app.id}")
                if save_clicked:
                    # Collapse the edit form and set flag to prevent immediate re-expansion
                    st.session_state[edit_expanded_key] = False
                    st.session_state[collapse_flag_key] = True
                    
                    # Prepare updates
                    updates = {
                        'company': new_company,
                        'role': new_role,
                        'location': new_location if new_location else None,
                        'status': new_status,
                        'applied_date': new_applied_date.strftime("%Y-%m-%d"),
                        'salary_range': new_salary_range if new_salary_range else None,
                        'job_url': new_job_url if new_job_url else None,
                        'job_description': new_job_description if new_job_description else None,
                        'notes': new_notes if new_notes else None,
                        'recruiter_contact': build_contact_link(recruiter_name_value, recruiter_link_value, recruiter_email_value),
                        'hiring_manager_contact': build_contact_link(hiring_manager_name_value, hiring_manager_link_value, hiring_manager_email_value)
                    }

                    # Update in database
                    db.update_application(app_id, updates)
                    st.success("✅ Application updated successfully!")
                    st.rerun()

            with col2:
                cancel_clicked = st.button("✕ Cancel", width="stretch", key=f"cancel_btn_{app.id}")
                if cancel_clicked:
                    # Collapse the edit form and set flag to prevent immediate re-expansion
                    st.session_state[edit_expanded_key] = False
                    st.session_state[collapse_flag_key] = True
                    st.rerun()

        st.divider()

        # Danger zone
        with st.expander("🗑️ Danger Zone"):
            st.warning("These actions cannot be undone!")

            if st.button("Delete Application", type="secondary"):
                if st.session_state.get('confirm_delete_detail'):
                    db.delete_application(app_id)
                    del st.session_state['view_application_id']
                    st.success("Application deleted!")
                    st.rerun()
                else:
                    st.session_state['confirm_delete_detail'] = True
                    st.warning("Click again to confirm deletion")


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

    st.header("Please log in to access Applications")
    st.subheader("Please log in.")
    render_login_button(type="primary", use_container_width=True)


def main():
    st.set_page_config(page_title="Applications", page_icon="📝", layout="wide")

    # Apply Google blue to all primary buttons
    from components.styles import apply_google_button_style
    apply_google_button_style()

    if not is_user_logged_in():
        login_screen()
        return

    st.title("📝 Job Applications")
    st.markdown("Manage all your job applications in one place")

    # Initialize database
    db = JobSearchDB()

    # Check if viewing detail
    if st.session_state.get('view_application_id'):
        show_application_detail(db, st.session_state['view_application_id'])
        return

    # Sidebar filters and stats
    with st.sidebar:
        st.header("📊 Quick Stats")

        stats = db.get_stats()
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total", stats['total'])
            st.metric("Active", stats['active'])
        with col2:
            st.metric("Response Rate", f"{stats['response_rate']}%")

        st.divider()

        # Filters
        st.header("🔍 Filters")

        company_search = st.text_input("Search Company", placeholder="e.g., Google")

        sort_by = st.selectbox(
            "Sort By",
            ["Applied Date (Newest)", "Applied Date (Oldest)", "Company (A-Z)", "Company (Z-A)"]
        )

    # Render quick notes in sidebar (accessible from anywhere)
    render_quick_notes()

    # Add new application
    st.header("➕ Add New Application")

    with st.expander("Click to add a new application", expanded=False):
        with st.form("new_application", clear_on_submit=True):
            col1, col2 = st.columns(2)

            with col1:
                company = st.text_input("Company *", placeholder="e.g., Google")
                role = st.text_input("Role *", placeholder="e.g., Senior ML Engineer")
                location = st.text_input("Location", placeholder="e.g., San Francisco, CA or Remote")

            with col2:
                status = st.selectbox(
                    "Status",
                    ["applied", "screening", "interview", "offer"]
                )
                applied_date = st.date_input("Applied Date", value=datetime.now())
                salary_range = st.text_input("Salary Range", placeholder="e.g., $150k-$200k")

            job_url = st.text_input("Job URL", placeholder="https://...")
            job_description = st.text_area("Job Description (optional)", height=150,
                                          placeholder="Paste job description here for AI analysis...")

            st.markdown("**Key Contacts (optional)**")
            contact_col1, contact_col2 = st.columns(2)
            with contact_col1:
                recruiter_name = st.text_input(
                    "Recruiter Name",
                    placeholder="e.g., Jane Recruiter",
                    key="new_recruiter_name"
                )
                recruiter_email = st.text_input(
                    "Recruiter Email",
                    placeholder="e.g., jane@company.com",
                    key="new_recruiter_email"
                )
                recruiter_link = st.text_input(
                    "Recruiter Contact Link",
                    placeholder="https://linkedin.com/in/...",
                    key="new_recruiter_link"
                )
            with contact_col2:
                hiring_manager_name = st.text_input(
                    "Hiring Manager Name",
                    placeholder="e.g., Alex Hiring",
                    key="new_hiring_manager_name"
                )
                hiring_manager_email = st.text_input(
                    "Hiring Manager Email",
                    placeholder="e.g., alex@company.com",
                    key="new_hiring_manager_email"
                )
                hiring_manager_link = st.text_input(
                    "Hiring Manager Contact Link",
                    placeholder="https://linkedin.com/in/...",
                    key="new_hiring_manager_link"
                )

            # AI Analysis button
            analyze_job = st.checkbox("🤖 Analyze job with AI", value=False,
                                     help="Use AI to extract requirements and calculate match score")

            notes = st.text_area("Notes (optional)", height=80,
                                placeholder="e.g., Referred by John, team focuses on AI/ML...")

            submit = st.form_submit_button("Add Application", type="primary")

            if submit:
                if not company or not role:
                    st.error("⚠️ Company and Role are required!")
                else:
                    try:
                        # Analyze job if requested
                        job_requirements = None
                        match_score = None

                        if analyze_job and job_description:
                            with st.spinner("🤖 Analyzing job description with AI..."):
                                try:
                                    matcher = JobMatcher()

                                    # Extract requirements
                                    job_requirements = matcher.extract_requirements(job_description)
                                    st.success("✅ Job requirements extracted!")

                                    # Calculate match score
                                    user_profile = get_default_user_profile()
                                    match_analysis = matcher.calculate_match_score(
                                        job_requirements,
                                        user_profile
                                    )

                                    match_score = match_analysis.get("match_score", 0)
                                    overall_score = match_analysis.get("overall_score", 0)

                                    # Show analysis
                                    st.info(f"📊 Match Score: {overall_score}/100")

                                    with st.expander("📋 View Analysis"):
                                        col1, col2 = st.columns(2)
                                        with col1:
                                            st.write("**Matching Skills:**")
                                            for skill in match_analysis.get("matching_skills", [])[:5]:
                                                st.write(f"✅ {skill}")
                                        with col2:
                                            st.write("**Missing Skills:**")
                                            for skill in match_analysis.get("missing_skills", [])[:5]:
                                                st.write(f"⚠️ {skill}")

                                        st.write("**Recommendation:**",
                                                match_analysis.get("recommendation", "Review manually"))

                                except Exception as e:
                                    st.warning(f"⚠️ AI analysis failed: {str(e)}")
                                    st.caption("Continuing without AI analysis...")

                        # Create application
                        recruiter_contact = build_contact_link(recruiter_name, recruiter_link, recruiter_email)
                        hiring_manager_contact = build_contact_link(hiring_manager_name, hiring_manager_link, hiring_manager_email)

                        app = create_application(
                            company=company,
                            role=role,
                            status=status,
                            applied_date=applied_date.strftime("%Y-%m-%d"),
                            location=location or None,
                            salary_range=salary_range or None,
                            job_url=job_url or None,
                            job_description=job_description or None,
                            notes=notes or None,
                            job_requirements=job_requirements,
                            match_score=match_score,
                            recruiter_contact=recruiter_contact,
                            hiring_manager_contact=hiring_manager_contact
                        )

                        db.add_application(app)
                        st.success(f"✅ Added application to {company}!")
                        st.balloons()
                        st.rerun()

                    except ValueError as e:
                        st.error(f"⚠️ {str(e)}")

    # List applications
    st.header("📋 Your Applications")

    # Get all applications
    applications = db.list_applications()

    # Apply company search
    if company_search:
        applications = [app for app in applications
                       if company_search.lower() in app.company.lower()]

    # Apply sorting (within each status column)
    if "Newest" in sort_by:
        applications = sorted(applications, key=lambda x: x.applied_date, reverse=True)
    elif "Oldest" in sort_by:
        applications = sorted(applications, key=lambda x: x.applied_date, reverse=False)
    elif "A-Z" in sort_by:
        applications = sorted(applications, key=lambda x: x.company.lower())
    elif "Z-A" in sort_by:
        applications = sorted(applications, key=lambda x: x.company.lower(), reverse=True)

    # Split applications by status for Kanban view
    active_applications = [app for app in applications if app.status not in ["rejected", "withdrawn", "accepted"]]
    accepted_applications = [app for app in applications if app.status == "accepted"]
    archived_applications = [app for app in applications if app.status in ["rejected", "withdrawn"]]

    # Group active applications by status
    applied_apps = [app for app in active_applications if app.status == "applied"]
    screening_apps = [app for app in active_applications if app.status == "screening"]
    interview_apps = [app for app in active_applications if app.status == "interview"]
    offer_apps = [app for app in active_applications if app.status == "offer"]

    # Kanban board style layout
    if len(active_applications) == 0:
        if len(accepted_applications) > 0:
            st.success(f"🎉 You have {len(accepted_applications)} accepted offer(s)! Check below.")
        else:
            st.info("🎯 No applications yet. Add your first one above!")
    else:
        # Create 4 columns for Kanban board
        col1, col2, col3, col4 = st.columns(4)

        # Applied Column
        with col1:
            st.markdown(f"### 📩 Applied")
            st.markdown(f"<p style='color: #666; font-size: 14px;'>{len(applied_apps)} application(s)</p>", unsafe_allow_html=True)
            st.markdown("---")

            for app in applied_apps:
                with st.container():
                    st.markdown(f"""
                        <div style='background-color: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 12px; border-left: 4px solid #4285F4;'>
                            <p style='margin: 0; font-weight: 600; font-size: 16px;'>{app.company}</p>
                            <p style='margin: 5px 0; color: #666; font-size: 14px;'>{app.role}</p>
                            <p style='margin: 8px 0 0 0; color: #999; font-size: 12px;'>📅 {app.applied_date}</p>
                        </div>
                    """, unsafe_allow_html=True)

                    if st.button("View Details", key=f"view_applied_{app.id}", use_container_width=True):
                        st.session_state['view_application_id'] = app.id
                        st.rerun()

        # Screening Column
        with col2:
            st.markdown(f"### 📧 Screening")
            st.markdown(f"<p style='color: #666; font-size: 14px;'>{len(screening_apps)} application(s)</p>", unsafe_allow_html=True)
            st.markdown("---")

            for app in screening_apps:
                with st.container():
                    st.markdown(f"""
                        <div style='background-color: #fff8e6; padding: 15px; border-radius: 8px; margin-bottom: 12px; border-left: 4px solid #FFA500;'>
                            <p style='margin: 0; font-weight: 600; font-size: 16px;'>{app.company}</p>
                            <p style='margin: 5px 0; color: #666; font-size: 14px;'>{app.role}</p>
                            <p style='margin: 8px 0 0 0; color: #999; font-size: 12px;'>📅 {app.applied_date}</p>
                        </div>
                    """, unsafe_allow_html=True)

                    if st.button("View Details", key=f"view_screening_{app.id}", use_container_width=True):
                        st.session_state['view_application_id'] = app.id
                        st.rerun()

        # Interview Column
        with col3:
            st.markdown(f"### 🎤 Interview")
            st.markdown(f"<p style='color: #666; font-size: 14px;'>{len(interview_apps)} application(s)</p>", unsafe_allow_html=True)
            st.markdown("---")

            for app in interview_apps:
                with st.container():
                    st.markdown(f"""
                        <div style='background-color: #e8f4fd; padding: 15px; border-radius: 8px; margin-bottom: 12px; border-left: 4px solid #00BFFF;'>
                            <p style='margin: 0; font-weight: 600; font-size: 16px;'>{app.company}</p>
                            <p style='margin: 5px 0; color: #666; font-size: 14px;'>{app.role}</p>
                            <p style='margin: 8px 0 0 0; color: #999; font-size: 12px;'>📅 {app.applied_date}</p>
                        </div>
                    """, unsafe_allow_html=True)

                    if st.button("View Details", key=f"view_interview_{app.id}", use_container_width=True):
                        st.session_state['view_application_id'] = app.id
                        st.rerun()

        # Offer Column
        with col4:
            st.markdown(f"### 🎁 Offer")
            st.markdown(f"<p style='color: #666; font-size: 14px;'>{len(offer_apps)} application(s)</p>", unsafe_allow_html=True)
            st.markdown("---")

            for app in offer_apps:
                with st.container():
                    st.markdown(f"""
                        <div style='background-color: #e8f8e8; padding: 15px; border-radius: 8px; margin-bottom: 12px; border-left: 4px solid #28a745;'>
                            <p style='margin: 0; font-weight: 600; font-size: 16px;'>{app.company}</p>
                            <p style='margin: 5px 0; color: #666; font-size: 14px;'>{app.role}</p>
                            <p style='margin: 8px 0 0 0; color: #999; font-size: 12px;'>📅 {app.applied_date}</p>
                        </div>
                    """, unsafe_allow_html=True)

                    if st.button("View Details", key=f"view_offer_{app.id}", use_container_width=True):
                        st.session_state['view_application_id'] = app.id
                        st.rerun()

    # Display accepted offers
    if len(accepted_applications) > 0:
        st.divider()
        with st.expander(f"🎉 Accepted Offers ({len(accepted_applications)})", expanded=False):
            for app in accepted_applications:
                show_application_card(app, db)

    # Display archived applications in a separate section
    if len(archived_applications) > 0:
        st.divider()
        with st.expander(f"📦 Archived Jobs ({len(archived_applications)} applications)", expanded=False):
            st.caption("Applications with 'Rejected' or 'Withdrawn' status")
            for app in archived_applications:
                show_application_card(app, db)

    # Bulk actions
    if len(applications) > 0:
        st.divider()
        with st.expander("⚡ Bulk Actions"):
            st.write("Coming soon: Export to CSV, Bulk status update, etc.")
    
    # Logout button
    st.divider()
    st.button("Log out", on_click=logout)


if __name__ == "__main__":
    main()
