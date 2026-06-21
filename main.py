import io
import json
import os
import time
import uuid
import smtplib
import asyncio
from datetime import datetime
from typing import Dict, Any, List
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pypdf import PdfReader
from pydantic import BaseModel
import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted, ServiceUnavailable

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-2.5-flash')

CHUNK_SIZE_CHARS = 12000
CHUNK_OVERLAP = 500
MAX_RETRIES = 5
BASE_BACKOFF = 5

# ---------- In-memory job store ----------
# NOTE: this resets if Render restarts/sleeps the instance.
# For real production, swap this dict for Redis or a DB table.
JOBS: Dict[str, Dict[str, Any]] = {}


class SubmitRequest(BaseModel):
    user_name: str
    company_name: str
    compliance_name: str
    filename: str
    edited_data: Dict[str, Any]


def extract_pdf_text(file_bytes: bytes, first_pages_only: bool = False) -> str:
    reader = PdfReader(io.BytesIO(file_bytes))
    limit = min(10 if first_pages_only else len(reader.pages), len(reader.pages))
    content = [reader.pages[i].extract_text() for i in range(limit) if reader.pages[i].extract_text()]
    return "\n".join(content)


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE_CHARS, overlap: int = CHUNK_OVERLAP) -> List[str]:
    chunks = []
    start = 0
    text_len = len(text)
    while start < text_len:
        end = min(start + chunk_size, text_len)
        chunks.append(text[start:end])
        if end == text_len:
            break
        start = end - overlap
    return chunks


def call_gemini_with_retry(prompt: str, json_mode: bool = False) -> str:
    last_err = None
    for attempt in range(MAX_RETRIES):
        try:
            if json_mode:
                resp = model.generate_content(
                    prompt,
                    generation_config={"response_mime_type": "application/json"}
                )
            else:
                resp = model.generate_content(prompt)
            return resp.text
        except (ResourceExhausted, ServiceUnavailable) as e:
            last_err = e
            time.sleep(BASE_BACKOFF * (2 ** attempt))
    raise RuntimeError(f"Rate limit exceeded after {MAX_RETRIES} retries: {last_err}")


def safe_json_parse(raw: str) -> Dict[str, Any]:
    cleaned = raw.replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1:
            return json.loads(cleaned[start:end + 1])
        raise


def merge_framework_chunks(chunk_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    merged: Dict[str, Any] = {"domains": []}
    seen_names = {}
    for result in chunk_results:
        for domain in result.get("domains", []):
            name = domain.get("name") or domain.get("domain_name")
            if name in seen_names:
                merged["domains"][seen_names[name]].setdefault("sub_domains", []).extend(domain.get("sub_domains", []))
            else:
                seen_names[name] = len(merged["domains"])
                merged["domains"].append(domain)
    return merged


def run_decode_job(job_id: str, file_bytes: bytes, compliance_name: str, filename: str):
    """Runs in the background — NOT inside the original HTTP request, so Render's
    request timeout can't kill it. Updates JOBS[job_id] as it progresses."""
    try:
        JOBS[job_id]["status"] = "verifying"

        ver_text = extract_pdf_text(file_bytes, first_pages_only=True)
        ver_prompt = f"Does this text match '{compliance_name}'? Return JSON {{\"is_match\": true}}. Text: {ver_text[:2000]}"
        ver_raw = call_gemini_with_retry(ver_prompt, json_mode=False)
        ver_json = safe_json_parse(ver_raw)

        if not ver_json.get("is_match"):
            JOBS[job_id]["status"] = "failed"
            JOBS[job_id]["error"] = "Document does not match selected compliance framework."
            return

        JOBS[job_id]["status"] = "extracting"
        full_text = extract_pdf_text(file_bytes, first_pages_only=False)
        chunks = chunk_text(full_text)
        JOBS[job_id]["total_chunks"] = len(chunks)

        base_prompt = (
            "Extract the compliance hierarchy (domain -> sub-domain -> clause -> policy text, "
            "preserving Arabic or English text as it appears in the source) to JSON with key 'domains'."
        )

        chunk_results = []
        for i, chunk in enumerate(chunks):
            prompt = f"{base_prompt}\n\nChunk {i+1}/{len(chunks)}.\n\nText:\n{chunk}"
            raw = call_gemini_with_retry(prompt, json_mode=True)
            chunk_results.append(safe_json_parse(raw))
            JOBS[job_id]["processed_chunks"] = i + 1
            time.sleep(1.5)

        merged = merge_framework_chunks(chunk_results)

        JOBS[job_id]["status"] = "done"
        JOBS[job_id]["result"] = {
            "filename": filename,
            "framework_data": merged
        }

    except Exception as e:
        JOBS[job_id]["status"] = "failed"
        JOBS[job_id]["error"] = str(e)


@app.post("/api/decode")
async def decode_document(
    background_tasks: BackgroundTasks,
    compliance_name: str = Form(...),
    file: UploadFile = File(...)
):
    """Returns immediately with a job_id. Actual processing happens in the background
    so the HTTP request never sits open long enough for Render to kill it."""
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Invalid file type.")

    file_bytes = await file.read()
    job_id = str(uuid.uuid4())

    JOBS[job_id] = {
        "status": "queued",
        "processed_chunks": 0,
        "total_chunks": 0,
        "result": None,
        "error": None,
    }

    background_tasks.add_task(run_decode_job, job_id, file_bytes, compliance_name, file.filename)

    return {"status": "accepted", "job_id": job_id}


@app.get("/api/decode/status/{job_id}")
async def get_job_status(job_id: str):
    """Frontend polls this every 3-5 seconds until status is 'done' or 'failed'."""
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job


def notify_via_email(data: SubmitRequest):
    sender = os.environ.get("SMTP_USER")
    password = os.environ.get("SMTP_PASS")
    msg = MIMEMultipart()
    msg['From'], msg['To'] = sender, "product@getsahl.io"
    msg['Subject'] = f"Compliance Decoded: {data.company_name}"
    body = f"User: {data.user_name}\nData: {json.dumps(data.edited_data, indent=4)}"
    msg.attach(MIMEText(body, 'plain', 'utf-8'))
    with smtplib.SMTP('smtp.gmail.com', 587) as server:
        server.starttls()
        server.login(sender, password)
        server.send_message(msg)


@app.post("/api/submit-to-sahl")
async def submit_data(request: SubmitRequest):
    try:
        notify_via_email(request)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))