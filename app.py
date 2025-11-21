# UI for asking questions on the knowledge base
import streamlit as st
import os
import re
import sys
from datetime import datetime

# Set USER_AGENT early to prevent warnings from libraries that check for it
if "USER_AGENT" not in os.environ:
    os.environ["USER_AGENT"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"

import google.generativeai as genai
from storage.pg_vector_store import PgVectorStore as MilvusVectorStore
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
from pages.upload_docs import get_vector_store, get_text_chunks
from langchain.chains.combine_documents import create_stuff_documents_chain
from ai.web_search import search_web, format_search_results, is_search_needed, extract_search_query
import boto3

# Add parent directory to path
sys.path.insert(0, '.')
from components.quick_notes import render_quick_notes


genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

def get_prompt_template():
    return PromptTemplate()

def detect_remember_intent(text):
    """
    Detect if the user wants to save/remember information.
    Returns (is_remember_intent, cleaned_text)
    """
    remember_patterns = [
        r'^remember\s+that\s+(.+)',
        r'^remember\s*:\s*(.+)',
        r'^remember\s+(.+)',
        r'^save\s+this\s*:\s*(.+)',
        r'^save\s+that\s+(.+)',
        r'^store\s+this\s*:\s*(.+)',
        r'^store\s+that\s+(.+)',
        r'^keep\s+in\s+mind\s+that\s+(.+)',
        r'^note\s+that\s+(.+)',
    ]

    text_lower = text.lower().strip()

    for pattern in remember_patterns:
        match = re.match(pattern, text_lower, re.IGNORECASE)
        if match:
            # Extract the information to remember
            info = match.group(1).strip()
            return True, info

    return False, text

def enrich_information(text):
    """
    Use LLM to enrich and contextualize information before storing.
    Makes it more searchable and contextual.
    """
    model = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.0)

    enrichment_prompt = f"""You are helping to store information in a knowledge base.

Given the following user information, expand it slightly to make it more searchable and contextual while keeping it concise.
Add relevant context, synonyms, or related terms that might help in future searches.
Keep the core facts unchanged. Return only the enriched version.

User's information: {text}

Enriched version (2-3 sentences maximum):"""

    try:
        response = model.invoke(enrichment_prompt)
        enriched = response.content.strip()
        return enriched
    except Exception as e:
        print(f"Enrichment failed: {e}")
        return text

def save_to_knowledge_base(information, enrich=True):
    """
    Save information directly to the vector store.

    Args:
        information: The text to save
        enrich: Whether to use LLM to enrich the information

    Returns:
        tuple: (success, message)
    """
    try:
        # Optionally enrich the information
        if enrich:
            with st.spinner("Processing information..."):
                enriched_info = enrich_information(information)
        else:
            enriched_info = information

        # Add metadata
        metadata = {
            'source': 'conversational_input',
            'timestamp': datetime.now().isoformat(),
            'original': information if enrich else None
        }

        # Get vector store and add text (user-specific)
        vector_store = MilvusVectorStore()
        text_chunks = get_text_chunks(enriched_info)

        # Add metadata to each chunk
        metadatas = [metadata.copy() for _ in text_chunks]
        vector_store.add_texts(text_chunks, metadatas=metadatas)

        return True, enriched_info
    except Exception as e:
        return False, str(e)

def detect_application_intent(text):
    """
    Detect if user is reporting a job application.
    Returns (is_application, extracted_text)

    Examples:
    - "Applied to Google for ML Engineer"
    - "I applied to Meta for Senior SWE today"
    - "Just submitted application to Amazon for Data Scientist"
    """
    application_patterns = [
        r'applied\s+to\s+([A-Za-z0-9\s&.]+?)\s+for\s+([A-Za-z0-9\s/\-.]+?)(?:\s+(?:today|yesterday|on\s+[\w\s,]+))?$',
        r'applied\s+at\s+([A-Za-z0-9\s&.]+?)\s+(?:for|as)\s+(?:a\s+)?([A-Za-z0-9\s/\-.]+?)(?:\s+(?:today|yesterday|on\s+[\w\s,]+))?$',
        r'submitted\s+application\s+to\s+([A-Za-z0-9\s&.]+?)\s+for\s+([A-Za-z0-9\s/\-.]+?)(?:\s+(?:today|yesterday|on\s+[\w\s,]+))?$',
        r'applying\s+to\s+([A-Za-z0-9\s&.]+?)\s+for\s+([A-Za-z0-9\s/\-.]+?)(?:\s+(?:today|yesterday|on\s+[\w\s,]+))?$',
        r'just\s+applied\s+(?:to|at)\s+([A-Za-z0-9\s&.]+?)\s+(?:for|as)\s+(?:a\s+)?([A-Za-z0-9\s/\-.]+?)(?:\s+(?:today|yesterday|on\s+[\w\s,]+))?$',
    ]

    text_clean = text.strip()

    for pattern in application_patterns:
        match = re.search(pattern, text_clean, re.IGNORECASE)
        if match:
            return True, text_clean

    return False, text

def parse_application_details(text):
    """
    Use LLM to extract structured application details from natural language.

    Args:
        text: Natural language text about a job application

    Returns:
        dict with company, role, date, and any additional context
    """
    model = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.1)

    prompt = f"""Extract job application details from this text in JSON format.

Text: "{text}"

Extract these fields:
- company: Company name (required)
- role: Job title/role (required)
- date: Application date (use today's date if not specified: {datetime.now().strftime('%Y-%m-%d')})
- location: Location if mentioned (optional)
- salary_range: Salary if mentioned (optional)
- notes: Any additional context or notes (optional)

Return ONLY valid JSON with these exact keys. Be precise and concise.
Example: {{"company": "Google", "role": "ML Engineer", "date": "2025-11-06", "notes": "Applied through referral"}}"""

    try:
        response = model.invoke(prompt)
        content = response.content.strip()

        # Extract JSON
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        import json
        details = json.loads(content)

        # Ensure required fields
        if 'company' not in details or 'role' not in details:
            return None

        # Set default date if missing
        if 'date' not in details or not details['date']:
            details['date'] = datetime.now().strftime('%Y-%m-%d')

        return details

    except Exception as e:
        print(f"Error parsing application: {e}")
        return None

def detect_interview_intent(text):
    """
    Detect if user is mentioning an interview.
    Returns (is_interview, extracted_text)

    Examples:
    - "Interview with Jane at Google tomorrow at 2pm"
    - "Phone screen with Meta on Nov 10"
    - "Technical interview scheduled for Friday"
    """
    interview_patterns = [
        r'interview\s+(?:with|at)\s+',
        r'phone\s+screen\s+(?:with|at)\s+',
        r'(?:technical|behavioral|onsite|virtual)\s+interview',
        r'interviewing\s+(?:with|at)\s+',
        r'scheduled\s+interview',
    ]

    text_lower = text.lower().strip()

    for pattern in interview_patterns:
        if re.search(pattern, text_lower):
            return True, text

    return False, text

def parse_interview_details(text):
    """
    Use LLM to extract interview details from natural language.

    Args:
        text: Natural language text about an interview

    Returns:
        dict with company, date, time, type, interviewer, and notes
    """
    model = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.1)

    prompt = f"""Extract interview details from this text in JSON format.

Text: "{text}"

Extract these fields:
- company: Company name (required)
- date: Interview date (required, format: YYYY-MM-DD)
- time: Time if mentioned (e.g., "2:00 PM")
- interview_type: phone/video/technical/behavioral/onsite (if mentioned)
- interviewer: Interviewer name if mentioned
- notes: Any additional context

Return ONLY valid JSON. If date uses relative terms (tomorrow, Friday), calculate the actual date based on today being {datetime.now().strftime('%A, %Y-%m-%d')}.
Example: {{"company": "Google", "date": "2025-11-10", "time": "2:00 PM", "interview_type": "technical", "notes": "Bring ID"}}"""

    try:
        response = model.invoke(prompt)
        content = response.content.strip()

        # Extract JSON
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        import json
        details = json.loads(content)

        # Ensure required fields
        if 'company' not in details or 'date' not in details:
            return None

        return details

    except Exception as e:
        print(f"Error parsing interview: {e}")
        return None

def create_application_from_text(details):
    """
    Create a job application from parsed details.

    Args:
        details: Dictionary with application details

    Returns:
        tuple: (success, message)
    """
    try:
        from storage.json_db import JobSearchDB
        from models.application import create_application

        db = JobSearchDB()

        # Create application
        app = create_application(
            company=details['company'],
            role=details['role'],
            status='applied',
            applied_date=details.get('date', datetime.now().strftime('%Y-%m-%d')),
            location=details.get('location'),
            salary_range=details.get('salary_range'),
            notes=details.get('notes')
        )

        db.add_application(app)

        return True, f"✅ Created application: {details['company']} - {details['role']}"

    except ValueError as e:
        # Duplicate or validation error
        return False, f"⚠️ {str(e)}"
    except Exception as e:
        return False, f"❌ Error creating application: {str(e)}"

def add_interview_to_application(details):
    """
    Add interview details to an existing application or create note.

    Args:
        details: Dictionary with interview details

    Returns:
        tuple: (success, message)
    """
    try:
        from storage.json_db import JobSearchDB

        db = JobSearchDB()

        # Find matching application
        applications = db.list_applications()
        matching_app = None

        for app in applications:
            if app.company.lower() == details['company'].lower():
                # Prefer active applications
                if app.status not in ['rejected', 'withdrawn', 'accepted']:
                    matching_app = app
                    break

        if not matching_app and applications:
            # Fall back to any matching company
            for app in applications:
                if app.company.lower() == details['company'].lower():
                    matching_app = app
                    break

        if matching_app:
            # Add interview as note
            interview_note = f"Interview scheduled: {details.get('date', 'TBD')}"
            if details.get('time'):
                interview_note += f" at {details['time']}"
            if details.get('interview_type'):
                interview_note += f" ({details['interview_type']})"
            if details.get('interviewer'):
                interview_note += f" with {details['interviewer']}"
            if details.get('notes'):
                interview_note += f". {details['notes']}"

            db.add_application_note(matching_app.id, interview_note)

            # Update status to interview if currently just applied or screening
            if matching_app.status in ['applied', 'screening']:
                db.update_status(matching_app.id, 'interview', interview_note)
                return True, f"✅ Interview added to {details['company']} application and status updated to 'interview'"
            else:
                return True, f"✅ Interview details added to {details['company']} application"
        else:
            # No matching application - save to knowledge base
            interview_info = f"Interview at {details['company']} on {details.get('date', 'TBD')}"
            if details.get('time'):
                interview_info += f" at {details['time']}"
            success, _ = save_to_knowledge_base(interview_info, enrich=False)

            if success:
                return True, f"💾 Interview details saved (no matching application found for {details['company']})"
            else:
                return False, "❌ Failed to save interview details"

    except Exception as e:
        return False, f"❌ Error adding interview: {str(e)}"

def detect_data_query_intent(text):
    """
    Detect if user is asking a question about their application/interview data.
    Returns (is_data_query, query_type)
    
    Query types: 'interview', 'application', 'stats', 'general'
    """
    text_lower = text.lower().strip()
    
    # Interview-related queries
    interview_patterns = [
        r'when\s+is\s+my\s+next\s+interview',
        r'what\s+interviews\s+do\s+i\s+have',
        r'when\s+are\s+my\s+interviews',
        r'show\s+me\s+my\s+interviews',
        r'upcoming\s+interviews',
        r'next\s+interview',
        r'interview\s+schedule',
        r'when\s+is\s+my\s+interview',
    ]
    
    # Application-related queries
    application_patterns = [
        r'what\s+companies\s+have\s+i\s+applied\s+to',
        r'what\s+applications\s+do\s+i\s+have',
        r'show\s+me\s+my\s+applications',
        r'list\s+my\s+applications',
        r'active\s+applications',
        r'application\s+status',
        r'how\s+many\s+applications',
    ]
    
    # Stats queries
    stats_patterns = [
        r'response\s+rate',
        r'how\s+many\s+interviews',
        r'application\s+stats',
        r'job\s+search\s+stats',
    ]
    
    for pattern in interview_patterns:
        if re.search(pattern, text_lower):
            return True, 'interview'
    
    for pattern in application_patterns:
        if re.search(pattern, text_lower):
            return True, 'application'
    
    for pattern in stats_patterns:
        if re.search(pattern, text_lower):
            return True, 'stats'
    
    return False, None


def answer_data_query(question: str, query_type: str):
    """
    Answer questions about application/interview data by querying the database.
    
    Args:
        question: The user's question
        query_type: 'interview', 'application', or 'stats'
    
    Returns:
        Formatted answer string
    """
    try:
        from storage.json_db import JobSearchDB
        from pages.interview_schedule import get_all_interviews
        from datetime import datetime, timedelta
        
        db = JobSearchDB()
        
        if query_type == 'interview':
            interviews = get_all_interviews(db)
            
            if not interviews:
                return "📅 You don't have any interviews scheduled yet. Add interview events to your applications to track them!"
            
            # Filter upcoming interviews
            today = datetime.now().date()
            upcoming_interviews = []
            for interview in interviews:
                try:
                    interview_date = datetime.strptime(interview['date'], "%Y-%m-%d").date()
                    if interview_date >= today:
                        upcoming_interviews.append(interview)
                except:
                    pass
            
            if not upcoming_interviews:
                return "📅 You don't have any upcoming interviews. All your interviews are in the past."
            
            # Get the next interview
            next_interview = upcoming_interviews[0]
            interview_date = datetime.strptime(next_interview['date'], "%Y-%m-%d")
            
            # Format the answer
            date_str = interview_date.strftime("%B %d, %Y")
            time_str = next_interview.get('time', 'Time TBD')
            company = next_interview['company']
            role = next_interview['role']
            interview_type = next_interview.get('type', 'interview').title()
            
            answer = f"📅 **Your next interview:**\n\n"
            answer += f"🏢 **Company:** {company}\n"
            answer += f"💼 **Role:** {role}\n"
            answer += f"📅 **Date:** {date_str}\n"
            answer += f"🕐 **Time:** {time_str}\n"
            answer += f"📝 **Type:** {interview_type}\n"
            
            if next_interview.get('interviewer'):
                answer += f"👤 **Interviewer:** {next_interview['interviewer']}\n"
            
            if len(upcoming_interviews) > 1:
                answer += f"\n💡 You have {len(upcoming_interviews)} upcoming interviews total."
            
            return answer
        
        elif query_type == 'application':
            applications = db.list_applications()
            
            if not applications:
                return "📝 You haven't applied to any companies yet. Start tracking your applications!"
            
            # Get unique companies
            companies = set()
            active_count = 0
            for app in applications:
                companies.add(app.company)
                if app.status.lower() in ['applied', 'interview', 'offer']:
                    active_count += 1
            
            answer = f"📝 **Your Applications:**\n\n"
            answer += f"🏢 **Companies applied to:** {', '.join(sorted(companies))}\n"
            answer += f"📊 **Total applications:** {len(applications)}\n"
            answer += f"✅ **Active applications:** {active_count}\n"
            
            # Show recent applications
            recent_apps = sorted(applications, key=lambda x: x.applied_date or '', reverse=True)[:5]
            if recent_apps:
                answer += f"\n📋 **Recent applications:**\n"
                for app in recent_apps:
                    status_emoji = {
                        'applied': '📝',
                        'interview': '📅',
                        'offer': '🎉',
                        'rejected': '❌',
                        'withdrawn': '🚫'
                    }.get(app.status.lower(), '📄')
                    answer += f"  {status_emoji} {app.company} - {app.role} ({app.status})\n"
            
            return answer
        
        elif query_type == 'stats':
            applications = db.list_applications()
            stats = db.get_stats()
            interviews = get_all_interviews(db)
            
            today = datetime.now().date()
            upcoming_interviews = [i for i in interviews 
                                 if datetime.strptime(i['date'], "%Y-%m-%d").date() >= today]
            
            answer = f"📊 **Your Job Search Stats:**\n\n"
            answer += f"📝 **Total Applications:** {stats['total']}\n"
            answer += f"✅ **Active Applications:** {stats['active']}\n"
            answer += f"📈 **Response Rate:** {stats['response_rate']}%\n"
            answer += f"📅 **Total Interviews:** {len(interviews)}\n"
            answer += f"🔜 **Upcoming Interviews:** {len(upcoming_interviews)}\n"
            
            return answer
        
        return "❌ Could not answer that question."
        
    except Exception as e:
        return f"❌ Error querying data: {str(e)}"


def get_chat_chain():
    """
    Get chat chain for answering questions.
    Note: Web search results are combined with context before passing to chain.
    """
    prompt_template="""
    Answer the questions based on the provided context honestly.
    
    The context may include:
    - Local knowledge base information
    - Web search results (if available)
    
    When web search results are included, cite the source URLs when relevant.
    If information conflicts between local knowledge and web results, prioritize more recent web information for time-sensitive queries.

    Context:\n {context} \n
    Questions: \n {questions} \n

    Provide a comprehensive answer. If web search results are included, mention source URLs when referencing them.
    Answers:
"""
    model=ChatGoogleGenerativeAI(model="gemini-2.5-flash",temperature=0.0)
    prompt=PromptTemplate(
        template=prompt_template, 
        input_variables=["context", "questions"], 
        output_variables=["answers"]
    )
    chain = create_stuff_documents_chain(llm=model, prompt=prompt, document_variable_name="context")
    return chain

def user_input(user_question):
    """
    Process user input - handle job applications, interviews, remember commands, or answer questions.
    """
    # Check for job application intent
    is_application, app_text = detect_application_intent(user_question)

    if is_application:
        st.info(f"📝 Detected job application: '{app_text}'")
        with st.spinner("Parsing application details..."):
            details = parse_application_details(app_text)

            if details:
                # Show what we extracted
                st.write("**Extracted details:**")
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"🏢 Company: {details['company']}")
                    st.write(f"💼 Role: {details['role']}")
                with col2:
                    st.write(f"📅 Date: {details['date']}")
                    if details.get('location'):
                        st.write(f"📍 Location: {details['location']}")

                # Create application
                success, message = create_application_from_text(details)
                if success:
                    st.success(message)
                    st.balloons()
                    st.info("💡 View all applications in the **Manage Applications** page")
                else:
                    st.warning(message)
            else:
                st.error("❌ Could not parse application details. Please try again or use the manual form.")
        return

    # Check for interview intent
    is_interview, interview_text = detect_interview_intent(user_question)

    if is_interview:
        st.info(f"📅 Detected interview mention: '{interview_text}'")
        with st.spinner("Parsing interview details..."):
            details = parse_interview_details(interview_text)

            if details:
                # Show what we extracted
                st.write("**Extracted details:**")
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"🏢 Company: {details['company']}")
                    st.write(f"📅 Date: {details['date']}")
                with col2:
                    if details.get('time'):
                        st.write(f"⏰ Time: {details['time']}")
                    if details.get('interview_type'):
                        st.write(f"📝 Type: {details['interview_type']}")

                # Add to application
                success, message = add_interview_to_application(details)
                if success:
                    st.success(message)
                else:
                    st.warning(message)
            else:
                st.error("❌ Could not parse interview details. Please add manually.")
        return

    # Check if this is a "remember" command
    is_remember, extracted_info = detect_remember_intent(user_question)

    if is_remember:
        # User wants to save information
        st.info(f"💾 Saving information: '{extracted_info}'")
        success, result = save_to_knowledge_base(extracted_info, enrich=True)

        if success:
            st.success("✅ Information saved to knowledge base!")
            with st.expander("📝 What was saved (enriched version)"):
                st.write(result)
        else:
            st.error(f"❌ Failed to save: {result}")
    else:
        # Check if this is a data query (about interviews/applications)
        is_data_query, query_type = detect_data_query_intent(user_question)
        
        if is_data_query:
            # Answer from database
            with st.spinner("Querying your data..."):
                answer = answer_data_query(user_question, query_type)
                st.markdown(answer)
        else:
            # Normal question answering (user-specific) - use vector store
            vector_store = MilvusVectorStore()
            docs = vector_store.similarity_search(user_question)
            
            # Check if web search is needed
            needs_web_search = is_search_needed(user_question)
            web_results_text = ""
            web_results = []
            
            if needs_web_search:
                # Perform web search
                search_query = extract_search_query(user_question)
                with st.spinner(f"🌐 Searching the web for: {search_query}..."):
                    web_results = search_web(search_query, max_results=5)
                    if web_results:
                        web_results_text = format_search_results(web_results)
                        # Show search sources
                        with st.expander("🔍 Web Search Sources", expanded=False):
                            for i, result in enumerate(web_results, 1):
                                st.markdown(f"**[{i}] [{result['title']}]({result['url']})**")
                                st.caption(result['snippet'][:200] + "...")
                    else:
                        st.info("⚠️ No web search results found. Answering from local knowledge base only.")
            
            # Combine local knowledge and web results
            # Create a combined context by adding web results as a document-like string
            combined_context = docs.copy()
            if web_results_text:
                # Add web results as additional context
                # We'll create a simple document-like object or just prepend to context
                from langchain.docstore.document import Document
                web_doc = Document(page_content=web_results_text, metadata={"source": "web_search"})
                combined_context = [web_doc] + docs
            
            # Get chain and invoke
            chain = get_chat_chain()
            response = chain.invoke({"context": combined_context, "questions": user_question})

            print(response)
            st.write("Reply: ", response)


def download_s3_bucket(bucket_name, download_dir):
    s3 = boto3.client('s3')
    
    # Ensure the download directory exists
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)
    
    # Pagination in case the bucket has many objects
    paginator = s3.get_paginator('list_objects_v2')
    for page in paginator.paginate(Bucket=bucket_name):
        for obj in page.get('Contents', []):
            key = obj['Key']
            local_file_path = os.path.join(download_dir, key)
            
            # Create local directories if they don't exist
            if not os.path.exists(os.path.dirname(local_file_path)):
                os.makedirs(os.path.dirname(local_file_path))
                
            print(f"Downloading {key} to {local_file_path}")
            s3.download_file(bucket_name, key, local_file_path)

def download_faiss_from_s3():
    # Legacy function - no longer needed with PostgreSQL backend
    print("Vector data is now stored in PostgreSQL. Migration from FAISS/S3 is no longer supported.")

from storage.auth_utils import is_user_logged_in, login, logout


def login_screen():
    st.header("Please log in to access Job Search Agent")
    st.subheader("Please log in.")
    
    # Only show login button if login hasn't been attempted yet
    # This prevents showing the button during OAuth flow
    if 'login_attempted' not in st.session_state:
        st.button("Log in with Google", on_click=login)
        # Note: After logout → login, OAuth redirect clears session state
        # User will need to click login button again after OAuth completes
    else:
        st.info("🔄 Login in progress... Please complete the authentication.")
        # Add a button to reset if stuck
        if st.button("Reset login state"):
            if 'login_attempted' in st.session_state:
                del st.session_state['login_attempted']
            st.rerun()


def main():
    st.set_page_config(page_title="Job Search Agent", page_icon="🎯", layout="wide")

    if not is_user_logged_in():
        login_screen()
        return

    st.title("🎯 Job Search Agent")
    st.markdown("Your AI-powered career companion")

    # Render quick notes in sidebar (accessible from anywhere)
    render_quick_notes()

    # Sidebar for quick actions
    with st.sidebar:
        # Quick save section
        st.header("💾 Quick Save")
        st.markdown("Save information without uploading documents")

        with st.form(key="manual_save_form", clear_on_submit=True):
            info_to_save = st.text_area(
                "Information to save:",
                placeholder="Example: Remember that my favorite color is blue",
                height=200,
                help="This will be added to your knowledge base immediately"
            )

            enrich_option = st.checkbox(
                "Enhance with AI",
                value=True,
                help="Use AI to make the information more searchable"
            )

            submit_button = st.form_submit_button("💾 Save to Knowledge Base")

            if submit_button and info_to_save.strip():
                with st.spinner("Saving information..."):
                    success, result = save_to_knowledge_base(info_to_save, enrich=enrich_option)

                if success:
                    st.success("✅ Saved successfully!")
                    if enrich_option:
                        with st.expander("📝 Enhanced version"):
                            st.write(result)
                else:
                    st.error(f"❌ Error: {result}")

    # Initialize vector store if empty (to avoid errors on first query)
    try:
        vector_store = MilvusVectorStore()
        # Only add initialization document if vector store is completely empty
        stats = vector_store.get_collection_stats()
        if stats.get("document_count", 0) == 0:
            get_vector_store(get_text_chunks("Job Search Agent knowledge base initialized"))
    except Exception:
        pass  # Vector store initialization will happen on first document upload

    # Main chat interface
    st.header("💬 AI Assistant")
    st.markdown("Ask questions, track applications, or save information naturally")

    # Quick action buttons
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        if st.button("📊 Dashboard", width="stretch"):
            st.switch_page("pages/dashboard.py")
    with col2:
        if st.button("📅 Interviews", width="stretch"):
            st.switch_page("pages/interview_schedule.py")
    with col3:
        if st.button("🎯 Interview Prep", width="stretch"):
            st.switch_page("pages/interview_prep.py")
    with col4:
        if st.button("📄 Resume", width="stretch"):
            st.switch_page("pages/resume.py")
    with col5:
        if st.button("📋 View All Apps", width="stretch"):
            st.switch_page("pages/applications.py")

    st.divider()

    user_question = st.text_input(
        "Ask anything or track your job search:",
        placeholder="Examples: 'Applied to Google today' or 'What companies should I target?'",
        help="Natural language - the system understands job search commands"
    )
    if user_question:
        user_input(user_question)
    
    
    # Help section
    with st.expander("💡 How to use Job Search Agent"):
        st.markdown("""
        ### Quick Start

        **Track Applications Naturally:**
        - "Applied at Amazon for Data Scientist today"
        - "Interview with Meta tomorrow at 2pm"
        - "Google offers $200k for this role"

        **Ask Questions:**
        - "What companies have I applied to?"
        - "When is my next interview?"
        - "Show me all active applications"

        **Save Information:**
        - "Remember that I prefer remote work"
        - "Note: Google uses Go and Python"

        ### Features
        - 📊 **Dashboard** - Visualize your progress with charts and metrics
        - 🎯 **Interview Prep** - Build your personal interview toolkit
        - 📄 **Resume Manager** - Upload and manage your resumes
        - 📝 **Track applications** - Natural language or manual entry
        - 🤖 **AI-powered matching** - Job analysis and scoring
        - 💾 **Natural language** - Just talk to track your search
        - 📅 **Interview scheduling** - Auto-detect and schedule
        - 📈 **Analytics** - Response rates, pipeline stats, timeline
        """)

    st.markdown("<div style='height:200px;'></div>", unsafe_allow_html=True)
    st.markdown("---")
    st.button("Log out", on_click=logout, width="stretch")

if __name__ == "__main__":
    main()