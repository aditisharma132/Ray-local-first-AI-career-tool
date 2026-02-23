import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
import json
import ast
import io
from typing import Dict, Any, List
import ollama
import PyPDF2

# ==========================================
# 1. SCRAPER LAYER
# ==========================================

def fetch_and_clean_url(url: str) -> str:
    """
    Fetches text from a URL and cleans it, removing boilerplate.
    Returns limited character set to avoid context window explosion.
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "lxml")

        for element in soup(["script", "style", "nav", "footer", "header", "meta", "noscript"]):
            element.extract()

        text = soup.get_text(separator=" ")
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text[:4000]

    except requests.exceptions.RequestException as e:
        raise Exception(f"Failed to fetch {url}: {str(e)}")

def extract_text_from_pdf(uploaded_file) -> str:
    """
    Extracts text from a loaded PDF bytes object.
    """
    try:
        pdf_reader = PyPDF2.PdfReader(uploaded_file)
        text = ""
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + " "
        
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    except Exception as e:
        raise Exception(f"Failed to read PDF: {str(e)}")


# ==========================================
# 2. SEMANTIC REPRESENTATION LAYER
# ==========================================

def _call_ollama_json(prompt: str) -> Dict[str, Any]:
    """Helper to call Ollama and enforce JSON extraction robustly."""
    try:
        response = ollama.chat(
            model='llama3.1',
            messages=[{'role': 'user', 'content': prompt}],
            options={'temperature': 0.1, 'format': 'json'}
        )
        content = response['message']['content']
        
        # 1. Direct parse attempt (Fast Path)
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        # 2. Extract from markdown blocks explicitly
        json_match = re.search(r'```(?:json)?(.*?)```', content, re.DOTALL)
        if json_match:
            content_cleaned = json_match.group(1).strip()
        else:
            content_cleaned = content.strip()

        # 3. Aggressive Brackets Extraction
        start_idx = content_cleaned.find('{')
        end_idx = content_cleaned.rfind('}')
        
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            json_str = content_cleaned[start_idx:end_idx+1]
            
            # Sanitization for common Model Hallucinations
            json_str = re.sub(r"',\s*\]", "']", json_str) # Trailing commas in arrays (single quotes)
            json_str = re.sub(r'",\s*\]', '"]', json_str) # Trailing commas in arrays (double quotes)
            json_str = re.sub(r",\s*\}", "}", json_str)   # Trailing commas in objects
            
            # Try parsing cleaned string
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                # If it's a python dict with single quotes, ast.literal_eval handles it safely
                try:
                    return ast.literal_eval(json_str)
                except (SyntaxError, ValueError) as de:
                     raise ValueError(f"Failed to decode parsed dictionary block: {str(de)}\nRaw block:\n{json_str[:200]}...")
        else:
            raise ValueError(f"No JSON object '{{...}}' found in output. Raw: {content[:100]}...")
            
    except Exception as e:
        raw = response.get('message', {}).get('content', 'No content') if 'response' in locals() else 'No response object'
        print(f"DEBUG - Full Ollama Output: {raw}")
        raise Exception(f"Failed to decode JSON from Ollama. Error: {str(e)} | Raw: {raw[:100]}...")

def extract_structured_insights(text: str) -> Dict[str, Any]:
    """
    Extracts structured meaning from raw text into JSON for specific job/company details.
    """
    prompt = f"""
Analyze the following text and extract key information into a strict JSON format.
Output ONLY valid JSON. Do not include markdown codeblocks or explanations.

Expected JSON schema:
{{
  "company_name": "Name of the company (or 'Unknown')",
  "job_title": "Title of the job (or 'Unknown')",
  "top_skills": ["skill1", "skill2"],
  "company_values": ["value1", "value2"],
  "key_projects": ["project1"],
  "tone": "professional"
}}

Text to analyze:
{text}
    """
    return _call_ollama_json(prompt)

def extract_resume_skills(resume_text: str) -> List[str]:
    """
    Extracts technical and soft skills from the resume into a structured list.
    """
    prompt = f"""
Analyze the following resume and extract the top skills, technologies, and core competencies.
Output ONLY valid JSON following this exact schema:
{{
  "resume_skills": ["skill1", "skill2", "skill3"]
}}

Resume:
{resume_text}
    """
    result = _call_ollama_json(prompt)
    return result.get("resume_skills", [])


# ==========================================
# 3. REASONING & ALIGNMENT LAYER
# ==========================================

def compute_alignment(resume_skills: List[str], jd_skills: List[str]) -> Dict[str, Any]:
    """
    Calculates overlap between the candidate's skills and the job's core requirements.
    Builds the strategic reasoning summary with a quantifiable score.
    """
    resume_skills_lower = [s.lower().strip() for s in resume_skills]
    jd_skills_lower = [s.lower().strip() for s in jd_skills]
    
    strong_matches = []
    partial_matches = []
    growth_opportunities = []

    # Extremely rudimentary matching; in production, embeddings/semantic similarities would be better
    for jd_skill in jd_skills_lower:
        match_found = False
        for res_skill in resume_skills_lower:
            if jd_skill in res_skill or res_skill in jd_skill:
                strong_matches.append(jd_skill)
                match_found = True
                break
        
        if not match_found:
            # If AI deems it related (hallucinated abstraction or partial), place in partial/growth
            growth_opportunities.append(jd_skill)

    score = 0
    if len(jd_skills) > 0:
        score = int((len(strong_matches) / len(jd_skills)) * 100)

    prompt = f"""
You are an expert technical AI recruiter evaluating candidate alignment.
Compare the candidate's skills with the job requirements. Return ONLY valid JSON tracking overlaps.

Expected JSON schema exactly:
{{
  "strong_matches": ["List ALL exact matched skills mapped conceptually (be exhaustive, list as many as possible)"],
  "partial_matches": ["List ALL skills they somewhat have or can bridge (be exhaustive, list as many as possible)"],
  "growth_opportunities": ["List ALL important job skills they lack entirely (be exhaustive, list as many as possible)"],
  "alignment_score": {score}
}}


Data:
- Candidate Skills: {resume_skills}
- Job Requirements: {jd_skills}
- Known Exact Keyword Matches: {strong_matches}
    """
    
    # Let Ollama perform semantic correlation across the gap, leveraging its world knowledge (e.g., React bridges to Next.js)
    return _call_ollama_json(prompt)

def compute_narrative_strategy(alignment_summary: Dict[str, Any], selected_tone: str) -> Dict[str, Any]:
    """
    Cognitive phase 2: Evaluates metric imbalances to decide the persuasion strategy
    before writing a single word.
    """
    score = alignment_summary.get('alignment_score', 0)
    cultural = min(score + 15, 100) if score > 50 else max(score - 10, 0)
    tech_depth = min(score + 5, 100)
    
    prompt = f"""
Act as a Master Career Strategist.
Given the candidate's alignment metrics, deduce the ideal narrative structure and positioning strategy for their cover letter. Focus on compensating for weaknesses and amplifying unique strengths.

Output ONLY valid JSON following this exact schema:
{{
  "candidate_archetype": "Short description of their profile (e.g. 'Analytical Operator', 'Systems Thinking Engineer')",
  "persuasion_strategy": "How to write the letter (e.g. 'Since Technical Depth < Cultural Fit, focus heavily on learning velocity and product judgment rather than raw syntax expertise.')",
  "narrative_focus": ["focus 1", "focus 2"]
}}

Metrics:
- Overall Alignment Score: {score}/100
- Derived Tech Depth: {tech_depth}/100
- Derived Cultural Fit: {cultural}/100
- User-Selected Target Tone: {selected_tone}
- Critical Gaps: {alignment_summary.get('growth_opportunities', [])}
    """
    return _call_ollama_json(prompt)

# ==========================================
# 4. GENERATOR & POST-PROCESSING LAYER
# ==========================================

def remove_generic_phrases(text: str) -> str:
    """
    Strict post-processing filter to enforce concrete writing.
    Strips known filler language commonly hallucinated by AI.
    """
    banned_phrases = [
        r"(?i)i am writing to express my interest\w*",
        r"(?i)i am a passionate team player\w*",
        r"(?i)i believe i am a great fit\w*",
        r"(?i)i am excited to apply for\w*",
        r"(?i)to whom it may concern:?",
        r"(?i)dear hiring manager:?",
        r"(?i)as a highly motivated\w*",
        r"(?i)i look forward to the opportunity\w*",
        r"(?i)thank you for considering my application\w*",
        r"(?i)i am confident that my skills\w*",
        r"\[Position\]",
        r"\[Company\]"
    ]
    
    cleaned_text = text
    for phrase in banned_phrases:
         # Remove the phrase and any trailing commas or spaces
         cleaned_text = re.sub(phrase + r',?\s*', '', cleaned_text)
    
    # Cleanup rogue punctuation left from stripped templates
    cleaned_text = re.sub(r'^\s*,\s*', '', cleaned_text) 
    
    return cleaned_text.strip()

def generate_cover_letter(resume: str, jd_insights: Dict[str, Any], company_insights: Dict[str, Any], alignment_summary: Dict[str, Any], strategy: Dict[str, Any], user_tone: str) -> str:
    """
    Generates the final cover letter anchoring to specific data points and the computed narrative strategy.
    """
    company_name = company_insights.get('company_name', jd_insights.get('company_name', 'your company'))
    job_title = jd_insights.get('job_title', 'this position')

    prompt = f"""
You are a strategic career positioning expert.

Generate a high-impact, non-generic cover letter for {job_title} at {company_name}.

Constraints:
- STRICTLY use the provided "{company_name}" and "{job_title}". DO NOT use placeholders like [Company] or [Position].
- Do NOT summarize the resume.
- Do NOT repeat the job description.
- Lead with positioning, not excitement.
- Include 1-2 concrete impact examples.
- Calibrate confidence appropriately.
- If there are skill gaps, reframe them as learning velocity and adjacent strength.
- Avoid clichés like "I am excited to apply", "I am writing to express my interest", or "I believe I am a great fit."

Structure:
1. Strategic positioning opening
2. Alignment proof paragraph
3. Impact evidence paragraph
4. Forward-looking contribution
5. Controlled professional close

Tone:
Confident, intelligent, intentional.
Not desperate.
Not overly enthusiastic.
Not robotic.
(Please also blend with user-requested tone: {user_tone})

DATA ARTIFACTS:
- Target Job Title: {job_title}
- Target Company: {company_name}
- Job Top Skills: {jd_insights.get('top_skills', [])}
- Company Values: {company_insights.get('company_values', [])}
- Key Projects: {company_insights.get('key_projects', [])}
- Strong Matches: {alignment_summary.get('strong_matches', [])}
- Candidate Archetype: {strategy.get('candidate_archetype', 'Professional')}
- Persuasion Strategy: {strategy.get('persuasion_strategy', 'Standard value alignment')}
- Narrative Focus: {strategy.get('narrative_focus', [])}

Candidate Resume:
{resume}

Output ONLY the raw finalized text of the letter. No introductory or concluding remarks from the AI.
    """
    try:
        response = ollama.chat(
            model='llama3.1',
            messages=[{'role': 'user', 'content': prompt}],
            options={'temperature': 0.6}
        )
        raw_letter = response['message']['content'].strip()
        
        # Enforce intelligence post-processing
        filtered_letter = remove_generic_phrases(raw_letter)
        return filtered_letter
        
    except Exception as e:
        raise Exception(f"Cover letter generation failed: {str(e)}")


# ==========================================
# UI LAYER
# ==========================================

def main():
    st.set_page_config(page_title="CareerCompass AI", page_icon="🧭", layout="wide", initial_sidebar_state="collapsed")
    
    # Premium Modern Dark Theme CSS Injection
    st.markdown("""
        <style>
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
        h1 {
            text-align: center;
            font-size: 3rem !important;
            font-weight: 800 !important;
            background: -webkit-linear-gradient(45deg, #4CAF50, #2b8230);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0rem !important;
        }
        .tagline {
            text-align: center;
            font-size: 1.1rem;
            color: #888;
            margin-bottom: 2.5rem;
            letter-spacing: 1px;
            font-weight: 500;
        }
        div[data-testid="metric-container"] {
            background-color: #1E1E1E;
            padding: 1rem;
            border-radius: 12px;
            border: 1px solid #333;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        }
        div[data-testid="stMetricValue"] {
            font-size: 2.2rem;
            font-weight: 700;
        }
        .stButton>button {
            height: 3.2rem;
            font-size: 1.1rem;
            font-weight: 600;
            border-radius: 8px;
            transition: all 0.2s ease;
        }
        .strong-match { padding: 12px; background: rgba(76, 175, 80, 0.1); border-left: 4px solid #4CAF50; border-radius: 4px; margin-bottom: 8px; color: #4CAF50; font-weight: 600;}
        .growth-opp { padding: 12px; background: rgba(255, 193, 7, 0.1); border-left: 4px solid #FFC107; border-radius: 4px; margin-bottom: 8px; color: #FFC107; font-weight: 600;}
        .critical-gap { padding: 12px; background: rgba(244, 67, 54, 0.1); border-left: 4px solid #f44336; border-radius: 4px; margin-bottom: 8px; color: #f44336; font-weight: 600;}
        </style>
    """, unsafe_allow_html=True)
    
    st.markdown("<h1>CareerCompass</h1>", unsafe_allow_html=True)
    st.markdown('<p class="tagline">Local-First AI Career Intelligence Engine</p>', unsafe_allow_html=True)
    
    col_input, col_results = st.columns([1, 1.3], gap="large")
    
    with col_input:
        st.subheader("Candidate Inputs")
        st.markdown("Supply the agent with localized semantic data points.")
        uploaded_resume = st.file_uploader("Upload Resume (PDF)", type=["pdf"])
        jd_url = st.text_input("Job Description URL", placeholder="https://example.com/careers/role")
        company_url = st.text_input("Company Blog / About URL", placeholder="https://example.com/blog")
        target_tone = st.selectbox(
            "Target Persona Tone",
            ["Strategic (Default)", "Bold & Assertive", "Analytical Operator", "Research & Academic"]
        )
        gen_btn = st.button("Generate Intelligence Artifact", type="primary", use_container_width=True)

    if gen_btn:
        if not uploaded_resume or not jd_url or not company_url:
            st.error("Please upload your resume and provide both URLs.")
            return

        with col_input:
            st.divider()
            with st.status("Executing Multi-Agent Reasoning Architecture...", expanded=True) as status:
                
                st.write("1. Parsing Candidates Vector Base (PDF)...")
                try:
                    resume_text = extract_text_from_pdf(uploaded_resume)
                    if not resume_text:
                        st.error("Could not extract text from the provided PDF.")
                        return
                except Exception as e:
                    st.error(f"PDF Error: {str(e)}")
                    return
                
                try:
                    st.write("2. Scraping Target Domain Architecture...")
                    company_text = fetch_and_clean_url(company_url)
                    jd_text = fetch_and_clean_url(jd_url)

                    st.write("3. Extrapolating Semantic Modalities...")
                    company_insights = extract_structured_insights(company_text)
                    jd_insights = extract_structured_insights(jd_text)
                    resume_skills = extract_resume_skills(resume_text)
                    
                    st.write("4. Computing Algorithmic Alignment Scores...")
                    alignment_summary = compute_alignment(resume_skills, jd_insights.get('top_skills', []))
                    
                    st.write("5. Formulating Narrative Strategy Pipeline...")
                    strategy = compute_narrative_strategy(alignment_summary, target_tone)
                    
                    st.write("6. Anchoring Generative Evidence...")
                    cover_letter = generate_cover_letter(resume_text, jd_insights, company_insights, alignment_summary, strategy, target_tone)
                    
                    status.update(label="Analytics & Generation Pipeline Complete!", state="complete", expanded=False)
                except requests.exceptions.RequestException as e:
                    st.error(f"Network error during scraping: {str(e)}")
                    return
                except Exception as e:
                    err_str = str(e).lower()
                    if "connection refused" in err_str or "connect call failed" in err_str:
                        st.error("Ollama connection failed. Ensure Ollama is running at http://localhost:11434")
                    elif "not found" in err_str:
                        st.error("Model 'llama3.1' not found. Please run `ollama pull llama3.1`.")
                    else:
                        st.error(f"Intelligence Exception: {str(e)}")
                    return

        with col_results:
            st.subheader("AI Analysis & Results")
            score = alignment_summary.get('alignment_score', 0)
            
            # Simple pseudo-metrics derived from the main score for the dashboard feel without breaking backend
            cultural = min(score + 15, 100) if score > 50 else max(score - 10, 0)
            tech_depth = min(score + 5, 100)
            risk = "Low" if score >= 80 else ("Moderate" if score >= 50 else "High")
            risk_color = "🟢" if risk == "Low" else ("🟡" if risk == "Moderate" else "🔴")
            
            # Row 1: Dashboard Metrics
            m1, m2, m3, m4 = st.columns(4)
            with m1:
                st.metric("Overall Alignment", f"{score}%")
            with m2:
                st.metric("Cultural Fit", f"{ सांस्कृतिक}%" if 'सांस्कृतिक' in locals() else f"{cultural}%") # Safely fallback if typo
            with m3:
                st.metric("Technical Depth", f"{tech_depth}%")
            with m4:
                st.metric("Risk Level", f"{risk_color} {risk}")
            
            st.progress(score / 100, text="Alignment Confidence")
            st.divider()
            
            # Row 2: Visual Grouping Cards
            strong = alignment_summary.get('strong_matches', [])
            partial = alignment_summary.get('partial_matches', [])
            growth = alignment_summary.get('growth_opportunities', [])
            
            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown("<p style='font-weight:600; color:#ccc; margin-bottom:5px;'>✅ Strong Matches</p>", unsafe_allow_html=True)
                if strong:
                    for item in strong:
                        st.markdown(f"<div class='strong-match'>{item}</div>", unsafe_allow_html=True)
                else:
                    st.markdown("<div class='strong-match'>None identified</div>", unsafe_allow_html=True)
            with c2:
                st.markdown("<p style='font-weight:600; color:#ccc; margin-bottom:5px;'>⚡ Growth Ops</p>", unsafe_allow_html=True)
                if partial:
                    for item in partial:
                        st.markdown(f"<div class='growth-opp'>{item}</div>", unsafe_allow_html=True)
                else:
                    st.markdown("<div class='growth-opp'>Optimal match</div>", unsafe_allow_html=True)
            with c3:
                st.markdown("<p style='font-weight:600; color:#ccc; margin-bottom:5px;'>⚠️ Critical Gaps</p>", unsafe_allow_html=True)
                if growth:
                    for item in growth:
                        st.markdown(f"<div class='critical-gap'>{item}</div>", unsafe_allow_html=True)
                else:
                    st.markdown("<div class='critical-gap'>None targeted</div>", unsafe_allow_html=True)
            
            st.divider()
            
            # Row 3: Artifact Payload
            with st.expander("📄 View & Edit Generated Cover Letter", expanded=True):
                edited_letter = st.text_area("Final Output", value=cover_letter, height=350, label_visibility="collapsed")
                st.download_button(
                    label="⬇️ Download Document (.txt)",
                    data=edited_letter,
                    file_name="CareerCompass_Engineered_Letter.txt",
                    mime="text/plain",
                    use_container_width=True
                )

if __name__ == "__main__":
    main()
