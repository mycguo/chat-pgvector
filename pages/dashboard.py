"""
Dashboard & Analytics

Visualize your job search progress with metrics, charts, and insights.
"""

import streamlit as st
import sys
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from collections import Counter

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
from models.application import Application


def calculate_metrics(db: JobSearchDB):
    """Calculate key metrics for the dashboard"""
    apps = db.list_applications()
    stats = db.get_stats()

    # Calculate additional metrics
    total = len(apps)
    active = len([a for a in apps if a.status in ['tracking', 'applied', 'screening', 'interview']])
    offers = len([a for a in apps if a.status == 'offer'])
    accepted = len([a for a in apps if a.status == 'accepted'])
    rejected = len([a for a in apps if a.status == 'rejected'])
    withdrawn = len([a for a in apps if a.status == 'withdrawn'])

    # Response rate (applications that progressed past "applied")
    responded = len([a for a in apps if a.status not in ['tracking', 'applied']])
    response_rate = (responded / total * 100) if total > 0 else 0

    # Interview rate (got to interview stage)
    interviews = len([a for a in apps if a.status in ['interview', 'offer', 'accepted']])
    interview_rate = (interviews / total * 100) if total > 0 else 0

    # Offer rate
    offer_rate = ((offers + accepted) / total * 100) if total > 0 else 0

    # Average time to response (for apps with timeline)
    time_to_response_days = []
    for app in apps:
        if len(app.timeline) > 1:
            applied_event = app.timeline[0]
            first_response = next((e for e in app.timeline[1:] if e.event_type != 'applied'), None)
            if first_response:
                try:
                    applied_date = datetime.fromisoformat(applied_event.date)
                    response_date = datetime.fromisoformat(first_response.date)
                    days = (response_date - applied_date).days
                    if days >= 0:
                        time_to_response_days.append(days)
                except:
                    pass

    avg_response_time = sum(time_to_response_days) / len(time_to_response_days) if time_to_response_days else 0

    return {
        'total': total,
        'active': active,
        'offers': offers,
        'accepted': accepted,
        'rejected': rejected,
        'withdrawn': withdrawn,
        'response_rate': response_rate,
        'interview_rate': interview_rate,
        'offer_rate': offer_rate,
        'avg_response_days': avg_response_time,
        'by_status': stats['by_status']
    }


def create_pipeline_chart(metrics):
    """Create funnel chart for application pipeline"""
    tracking = metrics['by_status'].get('tracking', 0)
    applied = metrics['by_status'].get('applied', 0)
    screening = metrics['by_status'].get('screening', 0)
    interview = metrics['by_status'].get('interview', 0)
    offer = metrics['by_status'].get('offer', 0)
    accepted = metrics['by_status'].get('accepted', 0)

    stages = ['Tracking', 'Applied', 'Screening', 'Interview', 'Offer', 'Accepted']
    counts = [
        tracking + applied + screening + interview + offer + accepted,
        applied + screening + interview + offer + accepted,
        screening + interview + offer + accepted,
        interview + offer + accepted,
        offer + accepted,
        accepted
    ]

    fig = go.Figure(go.Funnel(
        y=stages,
        x=counts,
        textinfo="value+percent initial",
        marker=dict(
            color=['#5c6ac4', '#3498db', '#9b59b6', '#e74c3c', '#2ecc71', '#27ae60']
        )
    ))

    fig.update_layout(
        title="Application Pipeline",
        height=400,
        showlegend=False
    )

    return fig


def create_status_distribution_chart(metrics):
    """Create pie chart for status distribution"""
    statuses = []
    counts = []

    for status, count in metrics['by_status'].items():
        if count > 0:
            statuses.append(status.title())
            counts.append(count)

    fig = px.pie(
        values=counts,
        names=statuses,
        title="Application Status Distribution",
        color_discrete_sequence=px.colors.qualitative.Set3
    )

    fig.update_traces(textposition='inside', textinfo='percent+label')
    fig.update_layout(height=400)

    return fig


def create_timeline_chart(apps):
    """Create timeline chart showing application activity"""
    if not apps:
        return None

    # Group applications by date
    dates = []
    for app in apps:
        try:
            date = datetime.strptime(app.applied_date, '%Y-%m-%d')
            dates.append(date)
        except:
            pass

    if not dates:
        return None

    # Count applications per day
    date_counts = Counter(d.strftime('%Y-%m-%d') for d in dates)
    sorted_dates = sorted(date_counts.keys())
    counts = [date_counts[d] for d in sorted_dates]

    # Create cumulative count
    cumulative = []
    total = 0
    for count in counts:
        total += count
        cumulative.append(total)

    fig = go.Figure()

    # Applications per day (bar)
    fig.add_trace(go.Bar(
        x=sorted_dates,
        y=counts,
        name='Applications per Day',
        marker_color='lightblue',
        yaxis='y'
    ))

    # Cumulative total (line)
    fig.add_trace(go.Scatter(
        x=sorted_dates,
        y=cumulative,
        name='Total Applications',
        mode='lines+markers',
        marker_color='darkblue',
        yaxis='y2'
    ))

    fig.update_layout(
        title="Application Activity Over Time",
        xaxis_title="Date",
        yaxis=dict(title="Applications per Day", side='left'),
        yaxis2=dict(title="Total Applications", side='right', overlaying='y'),
        height=400,
        hovermode='x unified',
        showlegend=True
    )

    return fig


def get_action_items(apps):
    """Generate action items based on application status"""
    items = []

    for app in apps:
        days_since_applied = app.get_days_since_applied()

        # Encourage action on tracked roles
        if app.status == 'tracking':
            items.append({
                'type': 'next_step',
                'priority': 'high',
                'message': f"Apply to {app.company} for {app.role}",
                'app_id': app.id
            })

        # Follow-up needed (applied > 7 days ago)
        if app.status == 'applied' and days_since_applied > 7:
            items.append({
                'type': 'follow_up',
                'priority': 'medium',
                'message': f"Follow up on {app.company} application ({days_since_applied} days ago)",
                'app_id': app.id
            })

        # Interview preparation (interview status)
        if app.status == 'interview':
            items.append({
                'type': 'prepare',
                'priority': 'high',
                'message': f"Prepare for {app.company} interview",
                'app_id': app.id
            })

        # Offer decision (offer pending)
        if app.status == 'offer':
            items.append({
                'type': 'decision',
                'priority': 'high',
                'message': f"Review offer from {app.company}",
                'app_id': app.id
            })

    # Sort by priority
    priority_order = {'high': 0, 'medium': 1, 'low': 2}
    items.sort(key=lambda x: priority_order[x['priority']])

    return items


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

    st.header("Please log in to access Dashboard")
    st.subheader("Please log in.")
    render_login_button(type="primary", use_container_width=True)
    
    # LinkedIn login (if configured)
    if is_linkedin_configured():
        st.markdown("<div style='margin-top: 12px;'></div>", unsafe_allow_html=True)
        render_linkedin_login_button(label="🔗 Login with LinkedIn")


def main():
    st.set_page_config(page_title="Dashboard", page_icon="📊", layout="wide")

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
                    pass

                # Small delay to ensure session state is saved
                import time
                time.sleep(0.5)

                # Rerun to show the main app (user is now logged in)
                st.rerun()
            else:
                st.error("Failed to complete LinkedIn login. Please try again.")
                if 'linkedin_login_initiated' in st.session_state:
                    del st.session_state['linkedin_login_initiated']
                if 'linkedin_oauth_state' in st.session_state:
                    del st.session_state['linkedin_oauth_state']

                try:
                    st.query_params.clear()
                except:
                    pass

                st.rerun()
        else:
            try:
                st.query_params.clear()
            except:
                pass



    # Apply Google blue to all primary buttons
    from components.styles import apply_google_button_style
    apply_google_button_style()

    if not is_user_logged_in():
        login_screen()
        return

    st.title("📊 Job Search Dashboard")
    st.markdown("Track your job search progress with real-time analytics")

    # Initialize database
    db = JobSearchDB()
    apps = db.list_applications()

    if len(apps) == 0:
        st.info("📝 No applications yet! Add your first application to see your dashboard.")
        if st.button("➕ Add Application", type="primary"):
            st.switch_page("pages/applications.py")
        return

    # Calculate metrics
    metrics = calculate_metrics(db)

    # Key Metrics Row
    st.header("📈 Key Metrics")
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric(
            "Total Applications",
            metrics['total'],
            delta=None
        )

    with col2:
        st.metric(
            "Active",
            metrics['active'],
            delta=None,
            help="Applications in applied, screening, or interview stages"
        )

    with col3:
        st.metric(
            "Response Rate",
            f"{metrics['response_rate']:.1f}%",
            delta=None,
            help="Percentage of applications that got a response"
        )

    with col4:
        st.metric(
            "Interview Rate",
            f"{metrics['interview_rate']:.1f}%",
            delta=None,
            help="Percentage of applications that reached interview stage"
        )

    with col5:
        st.metric(
            "Offers",
            metrics['offers'] + metrics['accepted'],
            delta=None,
            help="Total offers received"
        )

    st.divider()

    # Second row - more detailed metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Offer Rate",
            f"{metrics['offer_rate']:.1f}%",
            help="Percentage of applications that resulted in offers"
        )

    with col2:
        st.metric(
            "Avg Response Time",
            f"{metrics['avg_response_days']:.0f} days" if metrics['avg_response_days'] > 0 else "N/A",
            help="Average days until first response"
        )

    with col3:
        st.metric(
            "Rejected",
            metrics['rejected'],
            help="Applications that were rejected"
        )

    with col4:
        st.metric(
            "Accepted",
            metrics['accepted'],
            help="Offers you accepted"
        )

    st.divider()

    # Charts Row
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🔄 Application Pipeline")
        pipeline_chart = create_pipeline_chart(metrics)
        st.plotly_chart(pipeline_chart, width="stretch")

    with col2:
        st.subheader("📊 Status Distribution")
        status_chart = create_status_distribution_chart(metrics)
        st.plotly_chart(status_chart, width="stretch")

    # Timeline Chart
    st.subheader("📅 Application Timeline")
    timeline_chart = create_timeline_chart(apps)
    if timeline_chart:
        st.plotly_chart(timeline_chart, width="stretch")
    else:
        st.info("No timeline data available yet")

    st.divider()

    # Action Items
    st.header("🔥 Action Items")
    action_items = get_action_items(apps)

    if action_items:
        for item in action_items:
            priority_colors = {
                'high': '🔴',
                'medium': '🟡',
                'low': '🟢'
            }
            priority_emoji = priority_colors.get(item['priority'], '⚪')

            st.markdown(f"{priority_emoji} **{item['message']}**")
    else:
        st.success("✅ No pending action items! Great job staying on top of your applications.")

    st.divider()

    # Recent Activity
    st.header("📋 Recent Activity")

    # Sort by most recent
    sorted_apps = sorted(apps, key=lambda x: x.updated_at, reverse=True)[:10]

    for app in sorted_apps:
        with st.container():
            col1, col2, col3 = st.columns([3, 2, 2])

            with col1:
                st.markdown(f"**{app.get_status_emoji()} {app.company}** - {app.role}")

            with col2:
                st.write(f"📅 Applied: {app.applied_date}")

            with col3:
                st.write(f"Status: {app.get_display_status()}")

            # Show latest activity
            if len(app.timeline) > 0:
                latest_event = app.timeline[-1]
                st.caption(f"Latest: {latest_event.event_type.title()} on {latest_event.date}")

        st.divider()

    # Quick Actions
    st.header("⚡ Quick Actions")
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("➕ Add New Application", width="stretch"):
            st.switch_page("pages/applications.py")

    with col2:
        if st.button("📝 View All Applications", width="stretch"):
            st.switch_page("pages/applications.py")

    with col3:
        if st.button("🏠 Back to Home", width="stretch"):
            st.switch_page("app.py")
    
    # Logout button
    st.divider()
    st.button("Log out", on_click=logout)


if __name__ == "__main__":
    main()
