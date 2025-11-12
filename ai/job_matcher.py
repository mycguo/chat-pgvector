"""
Job Matching and Analysis AI

Uses LLM to:
- Extract requirements from job descriptions
- Calculate match scores
- Identify skills gaps
- Provide recommendations
"""

from langchain_google_genai import ChatGoogleGenerativeAI
from typing import Dict, List, Optional
import json
import re


class JobMatcher:
    """AI-powered job analysis and matching"""

    def __init__(self, model_name: str = "gemini-2.5-flash", temperature: float = 0.3):
        """
        Initialize job matcher.

        Args:
            model_name: LLM model to use
            temperature: Model temperature
        """
        self.model = ChatGoogleGenerativeAI(
            model=model_name,
            temperature=temperature
        )

    def extract_requirements(self, job_description: str) -> Dict:
        """
        Extract structured requirements from job description.

        Args:
            job_description: Raw job description text

        Returns:
            Dictionary with extracted requirements
        """
        prompt = f"""Analyze this job description and extract the following information in JSON format:

1. required_skills: List of must-have technical skills
2. preferred_skills: List of nice-to-have skills
3. years_experience: Minimum years of experience (number or "Entry Level")
4. education: Education requirements
5. responsibilities: Top 3-5 key responsibilities
6. company_culture: Keywords about company culture/values
7. location: Work location (Remote/Hybrid/Onsite + city)
8. role_level: Entry/Mid/Senior/Staff/Principal

Job Description:
{job_description}

Return ONLY valid JSON with these exact keys. Be concise and accurate.
"""

        try:
            response = self.model.invoke(prompt)
            content = response.content.strip()

            # Extract JSON from response (handle markdown code blocks)
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            requirements = json.loads(content)

            # Ensure all keys exist
            default_structure = {
                "required_skills": [],
                "preferred_skills": [],
                "years_experience": "Not specified",
                "education": "Not specified",
                "responsibilities": [],
                "company_culture": [],
                "location": "Not specified",
                "role_level": "Not specified"
            }

            for key in default_structure:
                if key not in requirements:
                    requirements[key] = default_structure[key]

            return requirements

        except Exception as e:
            print(f"Error extracting requirements: {e}")
            return {
                "required_skills": [],
                "preferred_skills": [],
                "years_experience": "Error parsing",
                "education": "Error parsing",
                "responsibilities": ["Could not extract"],
                "company_culture": [],
                "location": "Not specified",
                "role_level": "Not specified",
                "error": str(e)
            }

    def calculate_match_score(
        self,
        job_requirements: Dict,
        user_profile: Dict
    ) -> Dict:
        """
        Calculate match score between job and candidate profile.

        Args:
            job_requirements: Extracted job requirements
            user_profile: User's profile (skills, experience, etc.)

        Returns:
            Dictionary with score and analysis
        """
        prompt = f"""Calculate a match score (0-100) between this job and candidate.

Job Requirements:
{json.dumps(job_requirements, indent=2)}

Candidate Profile:
{json.dumps(user_profile, indent=2)}

Provide analysis in JSON format:
{{
  "overall_score": 0-100,
  "skill_match_score": 0-100,
  "experience_match_score": 0-100,
  "matching_skills": ["skill1", "skill2"],
  "missing_skills": ["skill3", "skill4"],
  "strengths": ["What makes candidate a good fit"],
  "gaps": ["What candidate is missing"],
  "recommendation": "Apply/Consider/Skip with brief reason"
}}

Be honest and analytical. Return ONLY valid JSON.
"""

        try:
            response = self.model.invoke(prompt)
            content = response.content.strip()

            # Extract JSON
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            analysis = json.loads(content)

            # Ensure score is 0-1 for storage
            if "overall_score" in analysis:
                analysis["match_score"] = analysis["overall_score"] / 100.0

            return analysis

        except Exception as e:
            print(f"Error calculating match: {e}")
            return {
                "overall_score": 0,
                "skill_match_score": 0,
                "experience_match_score": 0,
                "matching_skills": [],
                "missing_skills": [],
                "strengths": [],
                "gaps": ["Could not analyze"],
                "recommendation": "Manual review needed",
                "match_score": 0.0,
                "error": str(e)
            }

    def generate_cover_letter(
        self,
        company: str,
        role: str,
        job_requirements: Dict,
        user_profile: Dict,
        job_description: Optional[str] = None
    ) -> str:
        """
        Generate personalized cover letter.

        Args:
            company: Company name
            role: Job role
            job_requirements: Extracted requirements
            user_profile: User's profile
            job_description: Original job description (optional)

        Returns:
            Generated cover letter
        """
        prompt = f"""Write a professional cover letter for this job application.

Company: {company}
Role: {role}

Job Requirements:
{json.dumps(job_requirements, indent=2)}

Candidate Profile:
{json.dumps(user_profile, indent=2)}

Guidelines:
1. Professional but authentic tone
2. 3-4 paragraphs
3. Highlight relevant experience and skills
4. Show enthusiasm for company/role
5. Mention specific requirements you meet
6. Keep concise (250-300 words)

Write the cover letter now:
"""

        try:
            response = self.model.invoke(prompt)
            return response.content.strip()

        except Exception as e:
            print(f"Error generating cover letter: {e}")
            return f"Error generating cover letter: {str(e)}"

    def suggest_resume_tailoring(
        self,
        job_requirements: Dict,
        user_profile: Dict
    ) -> Dict:
        """
        Suggest how to tailor resume for this job.

        Args:
            job_requirements: Extracted requirements
            user_profile: User's profile

        Returns:
            Dictionary with tailoring suggestions
        """
        prompt = f"""Provide resume tailoring advice for this job application.

Job Requirements:
{json.dumps(job_requirements, indent=2)}

Candidate Profile:
{json.dumps(user_profile, indent=2)}

Provide suggestions in JSON format:
{{
  "keywords_to_add": ["keyword1", "keyword2"],
  "skills_to_highlight": ["skill1", "skill2"],
  "experience_to_emphasize": ["Which past roles/projects to highlight"],
  "order_recommendation": "How to reorder sections for impact",
  "summary_suggestion": "Suggested professional summary",
  "action_items": ["Specific changes to make"]
}}

Return ONLY valid JSON.
"""

        try:
            response = self.model.invoke(prompt)
            content = response.content.strip()

            # Extract JSON
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            suggestions = json.loads(content)
            return suggestions

        except Exception as e:
            print(f"Error generating suggestions: {e}")
            return {
                "keywords_to_add": [],
                "skills_to_highlight": [],
                "experience_to_emphasize": [],
                "order_recommendation": "Standard order is fine",
                "summary_suggestion": "",
                "action_items": ["Could not generate suggestions"],
                "error": str(e)
            }

    def analyze_company(self, company_name: str, additional_context: str = "") -> Dict:
        """
        Provide company analysis and insights.

        Args:
            company_name: Company name
            additional_context: Any additional context (job description, etc.)

        Returns:
            Dictionary with company insights
        """
        prompt = f"""Provide a concise company analysis for: {company_name}

Additional Context: {additional_context}

Provide in JSON format:
{{
  "company_overview": "Brief description",
  "known_for": ["What they're known for"],
  "tech_stack": ["Technologies they commonly use"],
  "culture": "Culture description",
  "interview_tips": ["Tips for interviewing"],
  "questions_to_ask": ["Good questions to ask them"]
}}

Use your knowledge. If uncertain, say so. Return ONLY valid JSON.
"""

        try:
            response = self.model.invoke(prompt)
            content = response.content.strip()

            # Extract JSON
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            analysis = json.loads(content)
            return analysis

        except Exception as e:
            print(f"Error analyzing company: {e}")
            return {
                "company_overview": f"Could not analyze {company_name}",
                "known_for": [],
                "tech_stack": [],
                "culture": "Unknown",
                "interview_tips": [],
                "questions_to_ask": [],
                "error": str(e)
            }


def get_default_user_profile() -> Dict:
    """
    Get default user profile.
    TODO: Load from actual user profile storage.

    Returns:
        User profile dictionary
    """
    return {
        "skills": {
            "primary": [
                "Python",
                "AI/ML",
                "LangChain",
                "RAG Systems",
                "Streamlit",
                "LLM Applications"
            ],
            "secondary": [
                "JavaScript",
                "React",
                "Docker",
                "Git",
                "REST APIs"
            ],
            "learning": [
                "System Design",
                "Kubernetes",
                "Microservices"
            ]
        },
        "experience": {
            "years_total": 5,
            "current_role": "Software Engineer",
            "highlights": [
                "Built AI-powered knowledge assistant with RAG",
                "Developed job search agent with LLM integration",
                "Experience with vector databases and embeddings"
            ]
        },
        "education": "Bachelor's in Computer Science",
        "preferences": {
            "roles": ["AI Engineer", "ML Engineer", "Senior Backend Engineer"],
            "locations": ["San Francisco", "Remote"],
            "company_size": ["startup", "mid-size"],
            "min_salary": 150000
        }
    }


# Quick test function
def test_job_matcher():
    """Test the job matcher with sample data"""
    matcher = JobMatcher()

    sample_job_desc = """
    Senior ML Engineer at Google

    We're looking for an experienced ML Engineer to join our team.

    Requirements:
    - 5+ years of Python experience
    - Strong background in machine learning and deep learning
    - Experience with production ML systems
    - Knowledge of LangChain, vector databases
    - Bachelor's degree in CS or related field

    Nice to have:
    - Experience with LLMs and RAG systems
    - Kubernetes/Docker
    - System design experience

    Location: San Francisco or Remote
    Salary: $180k-$250k
    """

    print("Extracting requirements...")
    requirements = matcher.extract_requirements(sample_job_desc)
    print(json.dumps(requirements, indent=2))

    print("\nCalculating match score...")
    profile = get_default_user_profile()
    match = matcher.calculate_match_score(requirements, profile)
    print(json.dumps(match, indent=2))

    print("\nMatch score:", match.get("overall_score", 0))


if __name__ == "__main__":
    test_job_matcher()
