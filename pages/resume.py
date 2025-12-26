"""
Resume Management

Upload, view, and manage your resumes.
Future: AI-powered resume tailoring for specific jobs.
"""

import streamlit as st
import sys
from datetime import datetime
import io
import re

# Add parent directory to path
sys.path.insert(0, '.')

from storage.resume_db import ResumeDB
from storage.auth_utils import is_user_logged_in, logout, render_login_button
from models.resume import create_resume, extract_skills_from_text, create_tailored_resume
from PyPDF2 import PdfReader
import docx
from langchain_google_genai import ChatGoogleGenerativeAI
import requests
from bs4 import BeautifulSoup
from components.quick_notes import render_quick_notes
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.enums import TA_LEFT, TA_CENTER


def generate_pdf_from_text(text: str, filename: str = "resume.pdf") -> bytes:
    """
    Generate a PDF from text content, preserving newlines.

    Args:
        text: The resume text content
        filename: Output filename (optional)

    Returns:
        PDF bytes
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter,
                           rightMargin=0.75*inch, leftMargin=0.75*inch,
                           topMargin=0.75*inch, bottomMargin=0.75*inch)

    # Container for the 'Flowable' objects
    elements = []

    # Define styles
    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor='black',
        spaceAfter=12,
        alignment=TA_LEFT
    )

    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=12,
        textColor='black',
        spaceAfter=4,
        spaceBefore=12,
        alignment=TA_LEFT,
        fontName='Helvetica-Bold'
    )

    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=10,
        textColor='black',
        spaceAfter=3,
        alignment=TA_LEFT,
        leading=14
    )

    bullet_style = ParagraphStyle(
        'CustomBullet',
        parent=styles['Normal'],
        fontSize=10,
        textColor='black',
        spaceAfter=3,
        alignment=TA_LEFT,
        leading=14,
        leftIndent=20,
        firstLineIndent=-10
    )

    # Parse text line by line, preserving the structure
    lines = text.split('\n')

    for line in lines:
        line_stripped = line.strip()

        # Skip completely empty lines but add small spacer
        if not line_stripped:
            elements.append(Spacer(1, 4))
            continue

        # Check if this looks like a heading
        is_heading = (
            len(line_stripped) < 60 and
            (line_stripped.isupper() or
             line_stripped.endswith(':') or
             any(keyword in line_stripped.lower() for keyword in [
                 'experience', 'education', 'skills', 'summary', 'objective',
                 'projects', 'certifications', 'professional experience',
                 'work experience', 'technical skills', 'contact'
             ]))
        )

        # Check if it's a bullet point
        is_bullet = line_stripped.startswith('•') or line_stripped.startswith('-') or line_stripped.startswith('*')

        # Escape special characters for ReportLab
        line_escaped = line_stripped.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

        if is_heading:
            # Add as heading
            elements.append(Paragraph(line_escaped, heading_style))
        elif is_bullet:
            # Add as bullet point with proper indentation
            # Remove the bullet character and add it back in the style
            bullet_text = line_stripped.lstrip('•-* ').strip()
            bullet_text_escaped = bullet_text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            elements.append(Paragraph(f"• {bullet_text_escaped}", bullet_style))
        else:
            # Add as normal paragraph
            elements.append(Paragraph(line_escaped, normal_style))

    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()


def extract_text_from_resume_file(file_bytes, filename):
    """Extract text content from resume file"""
    try:
        file_lower = filename.lower()

        if file_lower.endswith('.pdf'):
            pdf = PdfReader(io.BytesIO(file_bytes))
            text = ""
            for page in pdf.pages:
                text += page.extract_text()
            return text, 'pdf'

        elif file_lower.endswith('.docx'):
            doc = docx.Document(io.BytesIO(file_bytes))
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text, 'docx'

        elif file_lower.endswith('.txt'):
            text = file_bytes.decode('utf-8')
            return text, 'txt'

        else:
            return None, None

    except Exception as e:
        st.error(f"Error extracting text: {str(e)}")
        return None, None


def fetch_job_description_from_url(url: str) -> tuple:
    """Fetch job description from URL"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')

        # Extract text from common job description containers
        # Try to find the main content area
        job_content = None

        # Common selectors for job descriptions
        selectors = [
            'div[class*="job-description"]',
            'div[class*="description"]',
            'div[id*="job-description"]',
            'article',
            'main',
            'div[class*="posting"]'
        ]

        for selector in selectors:
            job_content = soup.select_one(selector)
            if job_content:
                break

        if not job_content:
            # Fallback to body
            job_content = soup.find('body')

        # Extract text
        if job_content:
            # Remove script and style elements
            for script in job_content(["script", "style"]):
                script.decompose()

            text = job_content.get_text(separator='\n', strip=True)

            # Clean up extra whitespace
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            text = '\n'.join(lines)

            return True, text
        else:
            return False, "Could not extract job description from URL"

    except requests.exceptions.Timeout:
        return False, "Request timed out. Please try again or paste the job description manually."
    except requests.exceptions.RequestException as e:
        return False, f"Error fetching URL: {str(e)}"
    except Exception as e:
        return False, f"Error: {str(e)}"


def clean_resume_text(text: str, company_name: str = "") -> str:
    """
    Remove introductory text and prefixes from AI-generated resume.
    
    Args:
        text: The raw text from AI
        company_name: Company name to help identify intro text
    
    Returns:
        Cleaned resume text
    """
    # Common patterns to remove
    intro_patterns = [
        r"^Here is the tailored resume[^:]*:",
        r"^Here's the tailored resume[^:]*:",
        r"^Below is the tailored resume[^:]*:",
        r"^The tailored resume[^:]*:",
        r"^Tailored resume[^:]*:",
        r"^Resume[^:]*:",
        r"^---+\s*$",  # Remove standalone separator lines at start
        r"^=+\s*$",  # Remove standalone separator lines at start
    ]
    
    cleaned = text
    
    # Remove intro patterns
    for pattern in intro_patterns:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE | re.MULTILINE)
    
    # Remove leading separators and whitespace
    cleaned = re.sub(r"^[-=]+\s*", "", cleaned, flags=re.MULTILINE)
    cleaned = cleaned.strip()
    
    # Only remove obvious AI intro text from the beginning
    # Be conservative - don't remove actual resume content
    lines = cleaned.split('\n')
    start_idx = 0

    # Only skip lines that are clearly AI intro/explanation text
    # These are typically long sentences explaining what was done
    for i, line in enumerate(lines):
        line_stripped = line.strip()
        line_lower = line.lower()

        # Skip empty lines at the start
        if not line_stripped:
            continue

        # Skip lines that are clearly AI explanations (contain phrases like "tailored", "emphasizing", etc.)
        # But only if they're reasonably long (actual resume headers are usually short)
        is_explanation = (
            len(line_stripped) > 100 and
            any(phrase in line_lower for phrase in [
                "tailored", "emphasizing", "highlighting", "rewritten",
                "here is", "here's", "below is", "the resume"
            ])
        )

        if is_explanation:
            start_idx = i + 1
        else:
            # Found actual resume content, stop here
            break

    if start_idx > 0:
        cleaned = '\n'.join(lines[start_idx:])

    return cleaned.strip()


def tailor_resume_with_ai(resume_text: str, job_description: str, company_name: str = "") -> tuple:
    """Use AI to tailor resume for specific job"""
    try:
        model = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.0)

        prompt = f"""You are an expert resume writer. Tailor the following resume to match the job description below.

IMPORTANT INSTRUCTIONS:
1. ALWAYS START with the candidate's full name and contact information (email, phone, location, LinkedIn, etc.) - this is MANDATORY
2. Keep the same overall structure and format
3. Emphasize relevant experience and skills that match the job requirements
4. Add or highlight keywords from the job description
5. Quantify achievements where possible
6. Keep it concise and impactful
7. Maintain professional tone
8. Do NOT fabricate experience or skills
9. Only reframe and emphasize what's already in the resume
10. Return ONLY the tailored resume text - no introductory text, no explanations, no prefixes

ORIGINAL RESUME:
{resume_text}

JOB DESCRIPTION:
{job_description}

COMPANY: {company_name if company_name else "Not specified"}

CRITICAL: Your response must begin with the candidate's name and contact information. Return ONLY the tailored resume text. Do not include any introductory text, explanations, or prefixes."""

        response = model.invoke(prompt)
        tailored_text = response.content.strip()
        
        # Clean up any introductory text that might have been added
        tailored_text = clean_resume_text(tailored_text, company_name)

        # Extract any additional insights
        insights_prompt = f"""Based on the resume and job description, provide a brief analysis of the tailoring.

Include:
1. Top 3-5 keywords/skills from the job description that were emphasized
2. A brief note about what was changed (2-3 sentences)

Format your response as a concise paragraph with the following structure:

**KEYWORDS:** keyword1, keyword2, keyword3, keyword4, keyword5

**CHANGES:** The resume's summary was rewritten to directly address the job description's emphasis on [specific aspects]. Bullet points under experience were rephrased to highlight achievements in [relevant areas], using language from the job description. Quantifiable results related to [specific metrics] were also added.

Keep it concise and use this exact formatting."""

        insights_response = model.invoke(insights_prompt)
        insights_raw = insights_response.content.strip()

        # Format insights to avoid large headings
        # Remove any markdown headers that the AI might have added
        insights = insights_raw.replace("# ", "").replace("## ", "").replace("### ", "")

        # Replace any standalone "KEYWORDS:" or "CHANGES:" with properly formatted text
        insights = insights.replace("KEYWORDS:", "**Keywords:**")
        insights = insights.replace("CHANGES:", "\n\n**Changes:**")
        insights = insights.replace("**KEYWORDS:**", "**Keywords:**")
        insights = insights.replace("**CHANGES:**", "\n\n**Changes:**")

        return True, tailored_text, insights

    except Exception as e:
        return False, str(e), ""


def show_tailor_resume_form(db: ResumeDB):
    """Show form to tailor an existing resume for a specific job"""
    st.subheader("🎯 Tailor Resume for Job")
    st.markdown("Create a customized version of your resume tailored to a specific job posting")

    # Get all master resumes
    master_resumes = db.get_master_resumes()

    if not master_resumes:
        st.warning("No master resumes found. Please upload a master resume first!")
        return

    # Check if we should show the form or the results
    if 'tailored_resume_data' in st.session_state:
        # Skip form display - will show results below
        pass
    else:
        # Initialize input method in session state if not set
        if 'tailor_input_method' not in st.session_state:
            st.session_state['tailor_input_method'] = "Paste Description"

        # Job description input method (outside form so it triggers rerun)
        st.markdown("### Job Description")
        input_method = st.radio(
            "Input Method",
            ["Paste Description", "Fetch from URL"],
            horizontal=True,
            key="tailor_input_method"
        )

        with st.form("tailor_resume_form", clear_on_submit=False):
            # Select master resume
            resume_options = {r.name: r for r in master_resumes}
            selected_resume_name = st.selectbox(
                "Select Master Resume *",
                options=list(resume_options.keys()),
                help="Choose the master resume to tailor"
            )

            selected_resume = resume_options[selected_resume_name]

            # Company and job info
            col1, col2 = st.columns(2)

            with col1:
                company_name = st.text_input(
                    "Company Name *",
                    placeholder="e.g., Google, Microsoft, etc.",
                    help="Company you're applying to"
                )

            with col2:
                job_title = st.text_input(
                    "Job Title (optional)",
                    placeholder="e.g., Senior Software Engineer",
                    help="Position title"
                )

            # Job description input based on selected method
            job_description = ""
            job_url = ""
            
            if input_method == "Paste Description":
                job_description = st.text_area(
                    "Job Description *",
                    placeholder="Paste the full job description here...",
                    height=300,
                    help="Paste the complete job posting",
                    key="tailor_job_description"
                )
            elif input_method == "Fetch from URL":
                job_url = st.text_input(
                    "Job Posting URL *",
                    placeholder="https://...",
                    help="URL to the job posting",
                    key="tailor_job_url"
                )

            # Additional notes
            tailoring_notes = st.text_area(
                "Tailoring Notes (optional)",
                placeholder="Any specific aspects you want to emphasize...",
                height=100
            )

            submit = st.form_submit_button("🎯 Tailor Resume", type="primary")

            if submit:
                if not company_name:
                    st.error("⚠️ Please provide the company name!")
                    return

                # Get job description
                if input_method == "Fetch from URL":
                    if not job_url:
                        st.error("⚠️ Please provide a job posting URL!")
                        return

                    with st.spinner("Fetching job description from URL..."):
                        success, result = fetch_job_description_from_url(job_url)

                        if not success:
                            st.error(f"❌ {result}")
                            return

                        job_description = result
                        st.success("✅ Job description fetched successfully!")

                        with st.expander("📄 Fetched Job Description"):
                            st.text(job_description[:1000] + "..." if len(job_description) > 1000 else job_description)

                if not job_description:
                    st.error("⚠️ Please provide a job description!")
                    return

                # Tailor the resume
                with st.spinner("✨ AI is tailoring your resume... This may take 15-30 seconds"):
                    success, tailored_text, insights = tailor_resume_with_ai(
                        selected_resume.full_text,
                        job_description,
                        company_name
                    )

                    if not success:
                        st.error(f"❌ Error tailoring resume: {tailored_text}")
                        return

                    # Create tailored resume
                    tailored_resume = create_tailored_resume(
                        master_resume=selected_resume,
                        job_id="",  # Optional: link to job application
                        company=company_name,
                        tailoring_notes=tailoring_notes
                    )

                    # Update with tailored content
                    tailored_resume.full_text = tailored_text
                    tailored_resume.skills = extract_skills_from_text(tailored_text)

                    if job_title:
                        tailored_resume.name = f"{company_name} - {job_title}"
                    else:
                        tailored_resume.name = f"{company_name} Resume"

                    # Save to database (no file bytes for tailored resumes)
                    resume_id = db.add_resume(tailored_resume, None)

                    # Store tailored resume data in session state for display outside form
                    st.session_state['tailored_resume_data'] = {
                        'text': tailored_text,
                        'insights': insights,
                        'company_name': company_name,
                        'resume_id': resume_id
                    }
                    
                    st.success(f"✅ Resume tailored successfully! (ID: {resume_id})")
                    st.rerun()
    
    # Display tailored resume results outside the form (after successful submission)
    if 'tailored_resume_data' in st.session_state:
        tailored_data = st.session_state['tailored_resume_data']
        tailored_text = tailored_data['text']
        insights = tailored_data['insights']
        company_name = tailored_data['company_name']
        
        # Show insights
        if insights:
            with st.expander("💡 Tailoring Insights"):
                st.caption("EXAMPLE (Hypothetical):")
                st.markdown(insights)

        # Generate PDF
        pdf_filename = f"{company_name.replace(' ', '_')}_Resume.pdf"
        pdf_bytes = generate_pdf_from_text(tailored_text, pdf_filename)
        
        # Display preview and download options
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown("### 📄 Tailored Resume Preview")
            # Improved display with better formatting
            st.markdown("---")
            # Display formatted text
            formatted_text = tailored_text.replace('\n\n', '\n').replace('\n', '  \n')
            st.markdown(formatted_text)
            st.markdown("---")
        
        with col2:
            st.markdown("### 📥 Download Options")
            # Download PDF button
            st.download_button(
                label="📄 Download as PDF",
                data=pdf_bytes,
                file_name=pdf_filename,
                mime="application/pdf",
                type="primary",
                width="stretch"
            )
            
            # Download as text button
            st.download_button(
                label="📝 Download as Text",
                data=tailored_text.encode('utf-8'),
                file_name=f"{company_name.replace(' ', '_')}_Resume.txt",
                mime="text/plain",
                width="stretch"
            )
            
            st.info("💡 PDF format is recommended for job applications")
            
            # Clear button to reset and show form again
            if st.button("🔄 Create Another Tailored Resume", width="stretch"):
                del st.session_state['tailored_resume_data']
                st.rerun()

        st.balloons()
        st.info("💡 You can also view and download the tailored resume from the resume list")


def show_upload_resume_form(db: ResumeDB):
    """Show form to upload new resume"""
    st.subheader("📤 Upload Resume")

    with st.form("upload_resume_form", clear_on_submit=True):
        col1, col2 = st.columns([2, 1])

        with col1:
            uploaded_file = st.file_uploader(
                "Choose your resume file",
                type=['pdf', 'docx', 'txt'],
                help="Upload your resume in PDF, Word, or Text format"
            )

        with col2:
            resume_name = st.text_input(
                "Resume Name *",
                placeholder="e.g., Software Engineer Resume",
                help="Give this resume a descriptive name"
            )

        col1, col2 = st.columns(2)

        with col1:
            is_master = st.checkbox(
                "Master Resume",
                value=True,
                help="Check if this is your master/template resume"
            )

        with col2:
            is_active = st.checkbox(
                "Set as Active",
                value=True,
                help="Use this resume for new applications"
            )

        notes = st.text_area(
            "Notes (optional)",
            placeholder="Any notes about this resume...",
            height=80
        )

        submit = st.form_submit_button("Upload Resume", type="primary")

        if submit:
            if not uploaded_file or not resume_name:
                st.error("⚠️ Please provide both a file and resume name!")
                return

            with st.spinner("Processing resume..."):
                # Read file
                file_bytes = uploaded_file.read()

                # Extract text
                text_content, file_type = extract_text_from_resume_file(
                    file_bytes,
                    uploaded_file.name
                )

                if not text_content:
                    st.error("Could not extract text from file. Please check the file format.")
                    return

                # Extract skills
                skills = extract_skills_from_text(text_content)

                # Create resume
                resume = create_resume(
                    name=resume_name,
                    full_text=text_content,
                    original_filename=uploaded_file.name,
                    file_type=file_type,
                    skills=skills,
                    is_master=is_master
                )

                resume.is_active = is_active

                # Save to database
                resume_id = db.add_resume(resume, file_bytes)

                st.success(f"✅ Resume uploaded successfully! (ID: {resume_id})")

                if skills:
                    with st.expander("🔍 Detected Skills"):
                        st.write(", ".join(skills))

                with st.expander("📄 Resume Preview"):
                    st.text(text_content[:1000] + "..." if len(text_content) > 1000 else text_content)

                st.balloons()
                st.rerun()


def show_resume_list(db: ResumeDB):
    """Show list of all resumes"""
    resumes = db.list_resumes()

    if not resumes:
        st.info("No resumes yet. Upload your first one above!")
        return

    # Sort by created_at (most recent first)
    resumes.sort(key=lambda x: x.created_at, reverse=True)

    st.subheader(f"📋 Your Resumes ({len(resumes)})")

    # Filters
    col1, col2, col3 = st.columns(3)

    with col1:
        show_master = st.checkbox("Show Master Only", value=False)

    with col2:
        show_tailored = st.checkbox("Show Tailored Only", value=False)

    with col3:
        show_active_only = st.checkbox("Show Active Only", value=False)

    # Apply filters
    filtered_resumes = resumes
    if show_master:
        filtered_resumes = [r for r in filtered_resumes if r.is_master]
    if show_tailored:
        filtered_resumes = [r for r in filtered_resumes if not r.is_master]
    if show_active_only:
        filtered_resumes = [r for r in filtered_resumes if r.is_active]

    if not filtered_resumes:
        st.info("No resumes match the selected filters.")
        return

    # Display resumes
    for resume in filtered_resumes:
        with st.container():
            col1, col2, col3, col4 = st.columns([3, 2, 2, 1])

            with col1:
                st.markdown(f"**{resume.get_status_emoji()} {resume.name}**")
                badges = f"v{resume.version}"
                if resume.is_master:
                    badges += " • Master"
                if resume.tailored_for_company:
                    badges += f" • {resume.tailored_for_company}"
                st.caption(badges)

            with col2:
                st.write(f"📁 {resume.file_type.upper() if resume.file_type else 'N/A'}")
                if resume.skills:
                    st.caption(f"Skills: {len(resume.skills)}")

            with col3:
                st.write(f"📊 {resume.applications_count} applications")
                if resume.success_rate > 0:
                    st.caption(f"Success: {resume.success_rate:.0f}%")

            with col4:
                if st.button("View", key=f"view_{resume.id}"):
                    st.session_state['view_resume_id'] = resume.id
                    st.rerun()

            st.divider()


def show_resume_detail(db: ResumeDB, resume_id: str):
    """Show detailed view of a resume"""
    resume = db.get_resume(resume_id)

    if not resume:
        st.error("Resume not found!")
        return

    # Header
    col1, col2 = st.columns([4, 1])

    with col1:
        st.title(f"{resume.get_status_emoji()} {resume.name}")
        st.caption(f"Version {resume.version} • Created {resume.created_at[:10]}")

    with col2:
        if st.button("← Back to List"):
            del st.session_state['view_resume_id']
            if 'edit_mode' in st.session_state:
                del st.session_state['edit_mode']
            st.rerun()

    st.divider()

    # Metadata tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📄 Content", "ℹ️ Info", "📊 Analytics", "⚙️ Actions"])

    with tab1:
        st.subheader("Resume Content")

        # Download button
        col1, col2 = st.columns([1, 4])

        with col1:
            if resume.file_path and db.get_file_bytes(resume_id):
                # Original file exists - download original
                file_bytes = db.get_file_bytes(resume_id)
                st.download_button(
                    label="📥 Download Original",
                    data=file_bytes,
                    file_name=resume.original_filename or f"{resume.name}.{resume.file_type}",
                    mime=f"application/{resume.file_type}"
                )
            else:
                # No file - download as text (for tailored resumes)
                st.download_button(
                    label="📥 Download as Text",
                    data=resume.full_text.encode('utf-8'),
                    file_name=f"{resume.name}.txt",
                    mime="text/plain",
                    help="Download tailored resume content as text file"
                )

        with col2:
            if resume.original_filename:
                st.caption(f"Original file: {resume.original_filename}")
            elif not resume.is_master:
                st.caption("Tailored resume (text only)")

        if resume.skills:
            st.subheader("🔧 Detected Skills")
            st.write(", ".join(resume.skills))

    with tab2:
        st.subheader("Resume Information")

        col1, col2 = st.columns(2)

        with col1:
            st.write("**Status:**")
            st.write(f"- Master Resume: {'Yes' if resume.is_master else 'No'}")
            st.write(f"- Active: {'Yes' if resume.is_active else 'No'}")

            if resume.parent_id:
                st.write(f"- Parent Resume ID: {resume.parent_id}")

        with col2:
            st.write("**Details:**")
            st.write(f"- File Type: {resume.file_type.upper() if resume.file_type else 'N/A'}")
            st.write(f"- Skills: {len(resume.skills)} detected")
            st.write(f"- Last Used: {resume.last_used[:10] if resume.last_used else 'Never'}")

        if resume.tailored_for_company:
            st.write("**Tailoring:**")
            st.write(f"- Company: {resume.tailored_for_company}")
            if resume.tailored_for_job:
                st.write(f"- Job ID: {resume.tailored_for_job}")
            if resume.tailoring_notes:
                st.write(f"- Notes: {resume.tailoring_notes}")

    with tab3:
        st.subheader("Resume Analytics")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(
                "Applications",
                resume.applications_count,
                help="Number of applications using this resume"
            )

        with col2:
            st.metric(
                "Success Rate",
                f"{resume.success_rate:.1f}%",
                help="Interview rate with this resume"
            )

        with col3:
            days_old = (datetime.now() - datetime.fromisoformat(resume.created_at)).days
            st.metric(
                "Age",
                f"{days_old} days",
                help="Days since resume was created"
            )

    with tab4:
        st.subheader("Resume Actions")

        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("✏️ Edit Resume", width="stretch"):
                st.session_state['edit_mode'] = not st.session_state.get('edit_mode', False)
                st.rerun()

        with col2:
            if st.button("🎯 Tailor for Job", width="stretch"):
                # Go back to main page and show tailor form
                del st.session_state['view_resume_id']
                st.session_state['show_tailor'] = True
                st.rerun()

        with col3:
            if not resume.is_active:
                if st.button("✅ Set as Active", width="stretch"):
                    db.set_active_resume(resume_id)
                    st.success("Resume set as active!")
                    st.rerun()

        st.divider()

        # Edit form
        if st.session_state.get('edit_mode', False):
            st.markdown("### ✏️ Edit Resume")

            with st.expander("Edit Form", expanded=True):
                # Resume name
                new_name = st.text_input(
                    "Resume Name",
                    value=resume.name,
                    help="Descriptive name for this resume"
                )

                # Full text content
                new_full_text = st.text_area(
                    "Resume Content",
                    value=resume.full_text,
                    height=400,
                    help="Full text content of your resume"
                )

                # Skills (comma-separated)
                skills_str = ", ".join(resume.skills) if resume.skills else ""
                new_skills_str = st.text_input(
                    "Skills (comma-separated)",
                    value=skills_str,
                    help="List of skills, separated by commas"
                )

                # Status flags
                col1, col2 = st.columns(2)

                with col1:
                    new_is_master = st.checkbox(
                        "Master Resume",
                        value=resume.is_master,
                        help="Is this a master/template resume?"
                    )

                with col2:
                    new_is_active = st.checkbox(
                        "Active",
                        value=resume.is_active,
                        help="Is this resume currently active?"
                    )

                # Optional fields
                if not resume.is_master:
                    new_company = st.text_input(
                        "Tailored for Company",
                        value=resume.tailored_for_company or "",
                        help="Company this resume is tailored for"
                    )

                    new_tailoring_notes = st.text_area(
                        "Tailoring Notes",
                        value=resume.tailoring_notes or "",
                        height=100,
                        help="Notes about how this resume was tailored"
                    )

                # Action buttons
                col1, col2 = st.columns(2)

                with col1:
                    if st.button("💾 Save Changes", type="primary", width="stretch"):
                        # Update resume
                        resume.name = new_name
                        resume.full_text = new_full_text

                        # Parse skills
                        if new_skills_str.strip():
                            resume.skills = [s.strip() for s in new_skills_str.split(',') if s.strip()]
                        else:
                            resume.skills = []

                        resume.is_master = new_is_master
                        resume.is_active = new_is_active

                        if not resume.is_master:
                            resume.tailored_for_company = new_company
                            resume.tailoring_notes = new_tailoring_notes

                        # Update timestamp
                        resume.updated_at = datetime.now().isoformat()

                        # Save to database
                        db.update_resume(resume)

                        st.success("✅ Resume updated successfully!")
                        st.session_state['edit_mode'] = False
                        st.rerun()

                with col2:
                    if st.button("✕ Cancel", width="stretch"):
                        st.session_state['edit_mode'] = False
                        st.rerun()

            st.divider()

        # Danger zone
        with st.expander("🗑️ Danger Zone"):
            st.warning("These actions cannot be undone!")

            col1, col2 = st.columns(2)

            with col1:
                if st.button("Deactivate Resume", type="secondary"):
                    resume.is_active = False
                    db.update_resume(resume)
                    st.success("Resume deactivated")
                    st.rerun()

            with col2:
                if st.button("Delete Resume", type="secondary"):
                    if st.session_state.get('confirm_delete'):
                        db.delete_resume(resume_id)
                        del st.session_state['view_resume_id']
                        st.success("Resume deleted!")
                        st.rerun()
                    else:
                        st.session_state['confirm_delete'] = True
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

    st.header("Please log in to access Resume Management")
    st.subheader("Please log in.")
    render_login_button(type="primary", use_container_width=True)


def main():
    st.set_page_config(page_title="Resume Management", page_icon="📄", layout="wide")

    # Apply Google blue to all primary buttons
    from components.styles import apply_google_button_style
    apply_google_button_style()

    if not is_user_logged_in():
        login_screen()
        return

    st.title("📄 Resume Management")
    st.markdown("Upload, view, and manage your resumes")

    # Render quick notes in sidebar (accessible from anywhere)
    render_quick_notes()

    # Initialize database
    db = ResumeDB()

    # Get stats
    stats = db.get_stats()

    # Key Metrics
    st.header("📊 Resume Stats")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Total Resumes",
            stats['total_resumes'],
            help="All resumes in your library"
        )

    with col2:
        st.metric(
            "Master Resumes",
            stats['master_resumes'],
            help="Base template resumes"
        )

    with col3:
        st.metric(
            "Tailored Resumes",
            stats['tailored_resumes'],
            help="Job-specific versions"
        )

    st.divider()

    # Check if viewing detail
    if st.session_state.get('view_resume_id'):
        show_resume_detail(db, st.session_state['view_resume_id'])
        return

    # Quick Actions
    st.header("⚡ Quick Actions")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("📤 Upload Resume", width="stretch"):
            st.session_state['show_upload'] = True

    with col2:
        if st.button("📋 View All Resumes", width="stretch"):
            st.session_state['show_upload'] = False

    with col3:
        if st.button("🎯 Tailor Resume", width="stretch"):
            st.session_state['show_tailor'] = True
            st.session_state['show_upload'] = False

    st.divider()

    # Show upload form if requested
    if st.session_state.get('show_upload', False):
        show_upload_resume_form(db)

        if st.button("✕ Close Upload"):
            st.session_state['show_upload'] = False
            st.rerun()

        st.divider()

    # Show tailor form if requested
    if st.session_state.get('show_tailor', False):
        show_tailor_resume_form(db)

        if st.button("✕ Close Tailor Form"):
            st.session_state['show_tailor'] = False
            st.rerun()

        st.divider()

    # Show resume list
    show_resume_list(db)

    # Navigation
    st.divider()
    st.header("🧭 Navigation")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("🏠 Home", width="stretch"):
            st.switch_page("app.py")

    with col2:
        if st.button("📊 Dashboard", width="stretch"):
            st.switch_page("pages/dashboard.py")

    with col3:
        if st.button("📝 Applications", width="stretch"):
            st.switch_page("pages/applications.py")
    
    # Logout button
    st.divider()
    st.button("Log out", on_click=logout)


if __name__ == "__main__":
    main()
