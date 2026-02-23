import re
from typing import Dict, Any, List
from models.llm_client import call_ollama_json, call_ollama_text

def extract_structured_insights(text: str) -> Dict[str, Any]:
    prompt = f"""
Analyze the following text and extract key information into a strict JSON format.
Output ONLY valid JSON. Do not include markdown codeblocks or explanations.

Expected JSON schema:
{{
  "company_name": "Company name if discernible, otherwise 'this company'",
  "job_title": "Target job title if discernible",
  "top_skills": ["skill1", "skill2"],
  "company_values": ["value1", "value2"],
  "key_projects": ["project1"],
  "tone": "professional"
}}

Text to analyze:
{text}
    """
    return call_ollama_json(prompt)

def extract_resume_skills(resume_text: str) -> List[str]:
    prompt = f"""
You are an expert technical recruiter analyzing a candidate's resume.
Extract the top core technical skills, frameworks, and methodologies.

Output ONLY valid JSON following this array schema:
{{
  "resume_skills": ["skill1", "skill2", "skill3"]
}}

Resume:
{resume_text}
    """
    res = call_ollama_json(prompt)
    return res.get("resume_skills", [])

def compute_alignment(resume_skills: List[str], jd_skills: List[str]) -> Dict[str, Any]:
    prompt = f"""
You are an advanced matching algorithm. 
Compare the Candidate Skills against the Target Job Skills.

Target Job Skills: {jd_skills}
Candidate Skills: {resume_skills}

Output ONLY valid JSON following this schema:
{{
  "alignment_score": [0-100 integer representing technical overlap],
  "strong_matches": ["list ALL exact or highly relevant matches exhaustively"],
  "partial_matches": ["list ALL skills that are adjacent but not exact exhaustively"],
  "growth_opportunities": ["list ALL required target skills the candidate lacks exhaustively"]
}}
    """
    return call_ollama_json(prompt)

def compute_narrative_strategy(alignment_summary: Dict[str, Any], selected_tone: str) -> Dict[str, Any]:
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
    return call_ollama_json(prompt)

def generate_cover_letter(resume: str, jd_insights: Dict[str, Any], company_insights: Dict[str, Any], alignment_summary: Dict[str, Any], strategy: Dict[str, Any], user_tone: str) -> str:
    company_name = company_insights.get('company_name', jd_insights.get('company_name', 'your company'))
    job_title = jd_insights.get('job_title', 'this position')

    prompt = f"""
You are a strategic career positioning expert.

Generate a high-impact, non-generic cover letter for {job_title} at {company_name}.

Constraints:
- STRICTLY use the provided "{company_name}" and "{job_title}". DO NOT use placeholders like [Company] or [Position].
- Produce a concise, high-impact and detailed cover letter of approximately 500-1000 words.
- Do NOT summarize the resume.
- Do NOT repeat the job description.
- Lead with positioning, not excitement.
- NEVER start the letter with "As a [Archetype]..." or explicitly state the Archetype. The Archetype is for your internal strategy context only. The letter must sound natural and human.
- MUST explicitly mention the company's background, values, or recent accomplishments based on the Company Values and Key Projects data artifacts to demonstrate deep domain understanding.
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
    
    cleaned_text = call_ollama_text(prompt, temperature=0.7)
    
    for phrase in ["I am excited to apply", "I am writing to express my interest", "I believe I am a great fit", "I am a passionate team player"]:
        cleaned_text = re.sub(phrase, "", cleaned_text, flags=re.IGNORECASE)
        
    # Strip robotic AI openings like "As a Strategic Systems Thinker, ..."
    cleaned_text = re.sub(r'^As a [^,\n]+,?\s*', '', cleaned_text, flags=re.IGNORECASE)
    
    cleaned_text = re.sub(r'^\s*,\s*', '', cleaned_text) 
    
    return cleaned_text.strip()
