"""
Interview Schedule Page

Shows all scheduled interviews organized by time, linked to applications.
"""

import streamlit as st
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import re

# Add parent directory to path
sys.path.insert(0, '.')

from storage.json_db import JobSearchDB
from models.application import Application, ApplicationEvent
from storage.auth_utils import is_user_logged_in, login, logout


def parse_interview_from_event(event: ApplicationEvent, app: Application) -> Optional[Dict]:
    """
    Parse interview information from a timeline event.
    
    Returns:
        Dictionary with interview details or None if not an interview event
    """
    # Check if this is an interview-related event
    interview_types = ['interview', 'screening', 'phone_screen', 'technical', 'behavioral', 'onsite']
    
    event_type_lower = event.event_type.lower()
    if not any(it in event_type_lower for it in interview_types):
        return None
    
    # Parse date
    interview_date = event.date
    
    # Try to extract time from notes
    time_match = re.search(r'(\d{1,2}:\d{2}\s*(?:AM|PM|am|pm))|(\d{1,2}:\d{2})|at\s+(\d{1,2}:\d{2}\s*(?:AM|PM|am|pm))', event.notes or "")
    interview_time = None
    if time_match:
        interview_time = time_match.group(0).replace('at ', '').strip()
    
    # Try to extract interview type
    interview_type = None
    type_keywords = {
        'phone': 'phone',
        'video': 'video',
        'technical': 'technical',
        'behavioral': 'behavioral',
        'onsite': 'onsite',
        'virtual': 'video',
        'screen': 'screening'
    }
    notes_lower = (event.notes or "").lower()
    for keyword, itype in type_keywords.items():
        if keyword in notes_lower:
            interview_type = itype
            break
    
    # Try to extract interviewer name
    interviewer = None
    interviewer_match = re.search(r'(?:with|interviewer|by)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)', event.notes or "")
    if interviewer_match:
        interviewer = interviewer_match.group(1)
    
    return {
        'date': interview_date,
        'time': interview_time,
        'type': interview_type or event_type_lower,
        'interviewer': interviewer,
        'notes': event.notes,
        'application_id': app.id,
        'company': app.company,
        'role': app.role,
        'event': event
    }


def get_all_interviews(db: JobSearchDB) -> List[Dict]:
    """
    Get all interviews from all applications.
    
    Returns:
        List of interview dictionaries sorted by date and time
    """
    applications = db.list_applications()
    interviews = []
    
    for app in applications:
        for event in app.timeline:
            interview = parse_interview_from_event(event, app)
            if interview:
                interviews.append(interview)
    
    # Sort by date and time
    def sort_key(interview):
        date_str = interview['date']
        time_str = interview.get('time', '00:00')
        
        try:
            # Parse date
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            
            # Parse time if available
            if time_str:
                try:
                    # Try different time formats
                    if 'AM' in time_str.upper() or 'PM' in time_str.upper():
                        time_obj = datetime.strptime(time_str, "%I:%M %p").time()
                    else:
                        time_obj = datetime.strptime(time_str, "%H:%M").time()
                    date_obj = datetime.combine(date_obj.date(), time_obj)
                except:
                    pass
            
            return date_obj
        except:
            # Fallback to date only
            try:
                return datetime.strptime(date_str, "%Y-%m-%d")
            except:
                return datetime.min
    
    interviews.sort(key=sort_key)
    return interviews


def group_interviews_by_date(interviews: List[Dict]) -> Dict[str, List[Dict]]:
    """Group interviews by date"""
    grouped = {}
    today = datetime.now().date()
    
    for interview in interviews:
        date_str = interview['date']
        try:
            interview_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            
            # Categorize date
            if interview_date < today:
                category = "Past"
            elif interview_date == today:
                category = "Today"
            elif interview_date == today + timedelta(days=1):
                category = "Tomorrow"
            elif interview_date <= today + timedelta(days=7):
                category = "This Week"
            elif interview_date <= today + timedelta(days=30):
                category = "This Month"
            else:
                category = "Upcoming"
            
            if category not in grouped:
                grouped[category] = []
            grouped[category].append(interview)
        except:
            # Invalid date format
            if "Other" not in grouped:
                grouped["Other"] = []
            grouped["Other"].append(interview)
    
    return grouped


def format_interview_time(interview: Dict) -> str:
    """Format interview time for display"""
    time_str = interview.get('time', '')
    if time_str:
        return time_str
    return "Time TBD"


def format_interview_type(interview: Dict) -> str:
    """Format interview type for display"""
    itype = interview.get('type', 'interview')
    type_emojis = {
        'phone': '📞',
        'video': '📹',
        'technical': '💻',
        'behavioral': '🗣️',
        'onsite': '🏢',
        'screening': '🔍'
    }
    emoji = type_emojis.get(itype.lower(), '💼')
    return f"{emoji} {itype.title()}"


def login_screen():
    st.header("Please log in to access Interview Schedule")
    st.subheader("Please log in.")
    st.button("Log in with Google", on_click=login)


def main():
    st.set_page_config(page_title="Interview Schedule", page_icon="📅", layout="wide")
    
    if not is_user_logged_in():
        login_screen()
        return
    
    st.title("📅 Interview Schedule")
    st.markdown("View all your scheduled interviews organized by time")
    
    # Initialize database
    db = JobSearchDB()
    
    # Get all interviews
    interviews = get_all_interviews(db)
    
    if not interviews:
        st.info("🎯 No interviews scheduled yet. Add interview events to your applications to see them here!")
        st.markdown("""
        ### How to add interviews:
        1. Go to **Applications** page
        2. Click on an application to view details
        3. Go to the **Timeline** tab
        4. Add a timeline event with type "interview" or "screening"
        5. Include date and time in the notes (e.g., "Interview scheduled: 2025-11-15 at 2:00 PM")
        """)
        return
    
    # Group interviews by date
    grouped_interviews = group_interviews_by_date(interviews)
    
    # Display stats
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Interviews", len(interviews))
    with col2:
        upcoming = len(grouped_interviews.get("Today", [])) + len(grouped_interviews.get("Tomorrow", [])) + len(grouped_interviews.get("This Week", []))
        st.metric("Upcoming (7 days)", upcoming)
    with col3:
        st.metric("This Week", len(grouped_interviews.get("This Week", [])))
    with col4:
        st.metric("Past", len(grouped_interviews.get("Past", [])))
    
    st.divider()
    
    # Display interviews by category (excluding Past)
    display_order = ["Today", "Tomorrow", "This Week", "This Month", "Upcoming", "Other"]
    
    for category in display_order:
        if category not in grouped_interviews or not grouped_interviews[category]:
            continue
        
        st.subheader(f"📅 {category}")
        
        for idx, interview in enumerate(grouped_interviews[category]):
            interview_key = f"{interview['application_id']}_{interview['date']}_{idx}"
            
            with st.container():
                col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
                
                with col1:
                    st.markdown(f"### {interview['company']}")
                    st.caption(f"{interview['role']}")
                
                with col2:
                    st.write("**Date & Time**")
                    date_display = datetime.strptime(interview['date'], "%Y-%m-%d").strftime("%B %d, %Y")
                    st.write(f"📅 {date_display}")
                    st.write(f"🕐 {format_interview_time(interview)}")
                
                with col3:
                    st.write("**Type**")
                    st.write(format_interview_type(interview))
                    if interview.get('interviewer'):
                        st.caption(f"👤 {interview['interviewer']}")
                
                with col4:
                    if st.button("View App", key=f"view_{interview_key}", width="stretch"):
                        st.session_state['view_application_id'] = interview['application_id']
                        st.switch_page("pages/applications.py")
                
                # Edit/Delete actions
                with st.expander("✏️ Edit Interview"):
                    # Get the event index in the application's timeline
                    app = db.get_application(interview['application_id'])
                    if app:
                        # Find the event in the timeline
                        event_index = None
                        for i, event in enumerate(app.timeline):
                            if event.date == interview['date'] and event.event_type == interview['event'].event_type:
                                event_index = i
                                break
                        
                        if event_index is not None:
                            col_edit1, col_edit2, col_edit3 = st.columns(3)
                            
                            with col_edit1:
                                new_event_type = st.selectbox(
                                    "Type",
                                    ["interview", "screening", "technical", "behavioral", "onsite", "phone", "video"],
                                    index=["interview", "screening", "technical", "behavioral", "onsite", "phone", "video"].index(interview['event'].event_type) if interview['event'].event_type in ["interview", "screening", "technical", "behavioral", "onsite", "phone", "video"] else 0,
                                    key=f"type_{interview_key}"
                                )
                            
                            with col_edit2:
                                new_event_date = st.date_input(
                                    "Date",
                                    value=datetime.strptime(interview['date'], "%Y-%m-%d"),
                                    key=f"date_{interview_key}"
                                )
                            
                            with col_edit3:
                                # Extract current time if available
                                current_time = None
                                if interview.get('time'):
                                    try:
                                        if 'AM' in interview['time'].upper() or 'PM' in interview['time'].upper():
                                            current_time = datetime.strptime(interview['time'], "%I:%M %p").time()
                                        else:
                                            current_time = datetime.strptime(interview['time'], "%H:%M").time()
                                    except:
                                        current_time = datetime.now().time()
                                else:
                                    current_time = datetime.now().time()
                                
                                new_event_time = st.time_input(
                                    "Time",
                                    value=current_time,
                                    key=f"time_{interview_key}"
                                )
                            
                            new_notes = st.text_area(
                                "Notes",
                                value=interview.get('notes', ''),
                                height=100,
                                key=f"notes_{interview_key}"
                            )
                            
                            col_btn1, col_btn2 = st.columns(2)
                            
                            with col_btn1:
                                if st.button("💾 Save Changes", key=f"save_{interview_key}", width="stretch"):
                                    # Format time and include in notes
                                    time_str = new_event_time.strftime("%I:%M %p")
                                    updated_notes = new_notes
                                    if not updated_notes.startswith("Time:"):
                                        updated_notes = f"Time: {time_str}\n{updated_notes}" if updated_notes else f"Time: {time_str}"
                                    else:
                                        # Replace existing time
                                        updated_notes = re.sub(r'^Time:.*?\n', f'Time: {time_str}\n', updated_notes)
                                    
                                    success = db.update_timeline_event(
                                        interview['application_id'],
                                        event_index,
                                        event_type=new_event_type,
                                        event_date=new_event_date.strftime("%Y-%m-%d"),
                                        notes=updated_notes
                                    )
                                    
                                    if success:
                                        st.success("✅ Interview updated!")
                                        st.rerun()
                                    else:
                                        st.error("❌ Failed to update interview")
                            
                            with col_btn2:
                                if st.button("🗑️ Delete", key=f"delete_{interview_key}", width="stretch"):
                                    if st.session_state.get(f'confirm_delete_{interview_key}'):
                                        success = db.delete_timeline_event(interview['application_id'], event_index)
                                        if success:
                                            st.success("✅ Interview deleted!")
                                            st.rerun()
                                        else:
                                            st.error("❌ Failed to delete interview")
                                    else:
                                        st.session_state[f'confirm_delete_{interview_key}'] = True
                                        st.warning("Click again to confirm deletion")
                
                st.divider()
    
    # Display archived (past) interviews in a separate collapsed section
    if "Past" in grouped_interviews and grouped_interviews["Past"]:
        st.divider()
        with st.expander(f"📦 Archived Interviews ({len(grouped_interviews['Past'])} interviews)", expanded=False):
            st.caption("Past interviews that have already occurred")
            
            for idx, interview in enumerate(grouped_interviews["Past"]):
                interview_key = f"archived_{interview['application_id']}_{interview['date']}_{idx}"
                
                with st.container():
                    col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
                    
                    with col1:
                        st.markdown(f"### {interview['company']}")
                        st.caption(f"{interview['role']}")
                    
                    with col2:
                        st.write("**Date & Time**")
                        date_display = datetime.strptime(interview['date'], "%Y-%m-%d").strftime("%B %d, %Y")
                        st.write(f"📅 {date_display}")
                        st.write(f"🕐 {format_interview_time(interview)}")
                    
                    with col3:
                        st.write("**Type**")
                        st.write(format_interview_type(interview))
                        if interview.get('interviewer'):
                            st.caption(f"👤 {interview['interviewer']}")
                    
                    with col4:
                        if st.button("View App", key=f"view_{interview_key}", width="stretch"):
                            st.session_state['view_application_id'] = interview['application_id']
                            st.switch_page("pages/applications.py")
                    
                    # Edit/Delete actions
                    with st.expander("✏️ Edit Interview"):
                        # Get the event index in the application's timeline
                        app = db.get_application(interview['application_id'])
                        if app:
                            # Find the event in the timeline
                            event_index = None
                            for i, event in enumerate(app.timeline):
                                if event.date == interview['date'] and event.event_type == interview['event'].event_type:
                                    event_index = i
                                    break
                            
                            if event_index is not None:
                                col_edit1, col_edit2, col_edit3 = st.columns(3)
                                
                                with col_edit1:
                                    new_event_type = st.selectbox(
                                        "Type",
                                        ["interview", "screening", "technical", "behavioral", "onsite", "phone", "video"],
                                        index=["interview", "screening", "technical", "behavioral", "onsite", "phone", "video"].index(interview['event'].event_type) if interview['event'].event_type in ["interview", "screening", "technical", "behavioral", "onsite", "phone", "video"] else 0,
                                        key=f"type_{interview_key}"
                                    )
                                
                                with col_edit2:
                                    new_event_date = st.date_input(
                                        "Date",
                                        value=datetime.strptime(interview['date'], "%Y-%m-%d"),
                                        key=f"date_{interview_key}"
                                    )
                                
                                with col_edit3:
                                    # Extract current time if available
                                    current_time = None
                                    if interview.get('time'):
                                        try:
                                            if 'AM' in interview['time'].upper() or 'PM' in interview['time'].upper():
                                                current_time = datetime.strptime(interview['time'], "%I:%M %p").time()
                                            else:
                                                current_time = datetime.strptime(interview['time'], "%H:%M").time()
                                        except:
                                            current_time = datetime.now().time()
                                    else:
                                        current_time = datetime.now().time()
                                    
                                    new_event_time = st.time_input(
                                        "Time",
                                        value=current_time,
                                        key=f"time_{interview_key}"
                                    )
                                
                                new_notes = st.text_area(
                                    "Notes",
                                    value=interview.get('notes', ''),
                                    height=100,
                                    key=f"notes_{interview_key}"
                                )
                                
                                col_btn1, col_btn2 = st.columns(2)
                                
                                with col_btn1:
                                    if st.button("💾 Save Changes", key=f"save_{interview_key}", width="stretch"):
                                        # Format time and include in notes
                                        time_str = new_event_time.strftime("%I:%M %p")
                                        updated_notes = new_notes
                                        if not updated_notes.startswith("Time:"):
                                            updated_notes = f"Time: {time_str}\n{updated_notes}" if updated_notes else f"Time: {time_str}"
                                        else:
                                            # Replace existing time
                                            updated_notes = re.sub(r'^Time:.*?\n', f'Time: {time_str}\n', updated_notes)
                                        
                                        success = db.update_timeline_event(
                                            interview['application_id'],
                                            event_index,
                                            event_type=new_event_type,
                                            event_date=new_event_date.strftime("%Y-%m-%d"),
                                            notes=updated_notes
                                        )
                                        
                                        if success:
                                            st.success("✅ Interview updated!")
                                            st.rerun()
                                        else:
                                            st.error("❌ Failed to update interview")
                                
                                with col_btn2:
                                    if st.button("🗑️ Delete", key=f"delete_{interview_key}", width="stretch"):
                                        if st.session_state.get(f'confirm_delete_{interview_key}'):
                                            success = db.delete_timeline_event(interview['application_id'], event_index)
                                            if success:
                                                st.success("✅ Interview deleted!")
                                                st.rerun()
                                            else:
                                                st.error("❌ Failed to delete interview")
                                        else:
                                            st.session_state[f'confirm_delete_{interview_key}'] = True
                                            st.warning("Click again to confirm deletion")
                    
                    st.divider()
    
    # Quick actions
    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📝 Go to Applications", width="stretch"):
            st.switch_page("pages/applications.py")
    with col2:
        if st.button("🎯 Go to Interview Prep", width="stretch"):
            st.switch_page("pages/interview_prep.py")
    
    # Logout button
    st.divider()
    st.button("Log out", on_click=logout)


if __name__ == "__main__":
    main()

