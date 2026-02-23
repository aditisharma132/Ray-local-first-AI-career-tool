from fastapi import FastAPI, UploadFile, File, Form, WebSocket
from fastapi.middleware.cors import CORSMiddleware
import json
import asyncio
import io

from tools.scrapers import fetch_and_clean_url_async
from tools.parsers import extract_text_from_pdf
from agents.intelligence import (
    extract_structured_insights, 
    extract_resume_skills, 
    compute_alignment, 
    compute_narrative_strategy, 
    generate_cover_letter
)

app = FastAPI(title="ResumeBot Intelligence Gateway", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/generate")
async def generate_artifact(
    resume: UploadFile = File(...),
    jd_url: str = Form(...),
    company_url: str = Form(...),
    target_tone: str = Form("Strategic (Default)")
):
    """
    Standard Blocking REST API.
    Use WebSockets for real-time agent streaming.
    """
    def _log(msg):
        with open("api_trace.log", "a") as f:
            f.write(msg + "\n")

    _log("1. Starting generate_artifact")
    resume_bytes = await resume.read()
    resume_text = extract_text_from_pdf(io.BytesIO(resume_bytes))
    _log("2. PDF extracted")
    
    _log("3. Fetching company text via MCP...")
    company_text = await fetch_and_clean_url_async(company_url)
    _log(f"4. Fetched company text len: {len(company_text)}")
    company_insights = await asyncio.to_thread(extract_structured_insights, company_text)
    _log("5. Extracted company insights via LLM")

    _log("6. Fetching JD text via MCP...")
    jd_text = await fetch_and_clean_url_async(jd_url)
    _log(f"7. Fetched JD text len: {len(jd_text)}")
    jd_insights = await asyncio.to_thread(extract_structured_insights, jd_text)
    _log("8. Extracted JD insights via LLM")

    _log("9. Extracting resume skills...")
    resume_skills = await asyncio.to_thread(extract_resume_skills, resume_text)
    
    _log("10. Computing alignment...")
    alignment_summary = await asyncio.to_thread(compute_alignment, resume_skills, jd_insights.get('top_skills', []))
    _log("11. Computing strategy...")
    strategy = await asyncio.to_thread(compute_narrative_strategy, alignment_summary, target_tone)
    
    _log("12. Generating cover letter...")
    cover_letter = await asyncio.to_thread(
        generate_cover_letter, resume_text, jd_insights, company_insights, alignment_summary, strategy, target_tone
    )
    _log("13. Done!")
    
    return {
        "alignment_summary": alignment_summary,
        "strategy": strategy,
        "cover_letter": cover_letter
    }

@app.websocket("/ws/generate")
async def websocket_generate(websocket: WebSocket):
    """
    Real-time streaming channel for the UI to monitor agent thoughts and progress.
    """
    await websocket.accept()
    try:
        data = await websocket.receive_json()
        jd_url = data.get("jd_url")
        company_url = data.get("company_url")
        target_tone = data.get("target_tone", "Strategic (Default)")
        resume_text = data.get("resume_text")
        await websocket.send_json({"type": "status", "message": "Scraping Company Ontology via MCP..."})
        company_text = await fetch_and_clean_url_async(company_url)
        company_insights = await asyncio.to_thread(extract_structured_insights, company_text)
        
        await websocket.send_json({"type": "status", "message": "Analyzing Target Domain via MCP..."})
        jd_text = await fetch_and_clean_url_async(jd_url)
        jd_insights = await asyncio.to_thread(extract_structured_insights, jd_text)
        
        await websocket.send_json({"type": "status", "message": "Extracting Candidate Vectors..."})
        resume_skills = await asyncio.to_thread(extract_resume_skills, resume_text)
        
        await websocket.send_json({"type": "status", "message": "Computing Algorithmic Alignment Scores..."})
        alignment_summary = await asyncio.to_thread(compute_alignment, resume_skills, jd_insights.get('top_skills', []))
        
        # Flush the computed metrics to the frontend
        await websocket.send_json({"type": "metrics", "data": alignment_summary})
        
        await websocket.send_json({"type": "status", "message": "Formulating Narrative Strategy Pipeline..."})
        strategy = await asyncio.to_thread(compute_narrative_strategy, alignment_summary, target_tone)
        
        # Flush the computed strategy to the frontend
        await websocket.send_json({"type": "strategy", "data": strategy})
        
        await websocket.send_json({"type": "status", "message": "Anchoring Generative Evidence..."})
        cover_letter = await asyncio.to_thread(
            generate_cover_letter, resume_text, jd_insights, company_insights, alignment_summary, strategy, target_tone
        )
        
        await websocket.send_json({"type": "complete", "data": cover_letter})
        
    except Exception as e:
        await websocket.send_json({"type": "error", "message": str(e)})
    finally:
        await websocket.close()
