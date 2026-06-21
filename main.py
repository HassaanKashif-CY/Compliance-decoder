import io
import json
import os
import re
import time
import uuid
import smtplib
import threading
from typing import Dict, Any, List
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import fitz  # PyMuPDF — pip install pymupdf
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
MAX_RETRIES = 5
BASE_BACKOFF = 5

JOBS: Dict[str, Dict[str, Any]] = {}


class SubmitRequest(BaseModel):
    user_name: str
    company_name: str
    compliance_name: str
    filename: str
    edited_data: Dict[str, Any]


# ---------------------------------------------------------------------
# 1) CLEAN TEXT EXTRACTION (fixes corrupted/reversed Arabic from pypdf)
# ---------------------------------------------------------------------
def extract_pdf_text(file_bytes: bytes, first_pages_only: bool = False) -> str:
    """PyMuPDF handles Arabic/RTL shaping far more reliably than pypdf."""
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    limit = min(10, len(doc)) if first_pages_only else len(doc)
    pages_text = []
    for i in range(limit):
        page = doc[i]
        # "text" mode with sort=True keeps reading order sane for RTL content
        text = page.get_text("text", sort=True)
        if text.strip():
            pages_text.append(text)
    doc.close()
    return "\n".join(pages_text)


# ---------------------------------------------------------------------
# 2) HEADING-AWARE CHUNKING (fixes domains getting cut in half)
# ---------------------------------------------------------------------
# Matches Arabic/English numbered headings like "1-1", "٢-٣", "Domain 2", etc.
HEADING_PATTERN = re.compile(
    r'(?m)^\s*(?:[\u0660-\u0669\d]+[-–][\u0660-\u0669\d]+(?:[-–][\u0660-\u0669\d]+)?|[\u0660-\u0669\d]+\.)\s'
)

def chunk_text_by_headings(text: str, max_chunk_size: int = CHUNK_SIZE_CHARS) -> List[str]:
    """
    Try to split on heading boundaries so a domain/sub-domain never gets
    split mid-way across two chunks. Falls back to char-based splitting
    only when a single section is itself larger than max_chunk_size.
    """
    matches = list(HEADING_PATTERN.finditer(text))
    if not matches:
        # no headings detected — fall back to plain char chunking with overlap
        return _char_chunk_fallback(text, max_chunk_size)

    sections = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        sections.append(text[start:end])

    # pack sections into chunks up to max_chunk_size, never splitting a section
    chunks = []
    current = ""
    for section in sections:
        if len(section) > max_chunk_size:
            # section itself too big (rare) — flush current, char-split this one
            if current:
                chunks.append(current)
                current = ""
            chunks.extend(_char_chunk_fallback(section, max_chunk_size))
            continue
        if len(current) + len(section) > max_chunk_size:
            chunks.append(current)
            current = section
        else:
            current += section
    if current:
        chunks.append(current)
    return chunks


def _char_chunk_fallback(text: str, chunk_size: int, overlap: int = 300) -> List[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])
        if end == len(text):
            break
        start = end - overlap
    return chunks


# ---------------------------------------------------------------------
# 3) STRICT SCHEMA (fixes Gemini using different keys per chunk)
# ---------------------------------------------------------------------
EXTRACTION_SCHEMA_PROMPT = """You are extracting a compliance framework document into structured JSON.

You MUST follow this EXACT schema for every object — do not rename, omit, or add keys.
Preserve Arabic text exactly as written in the source; do not translate unless the source itself has both languages.
If a field is not present in this chunk, use an empty string "" or empty array [], never omit the key.

{
  "domains": [
    {
      "domain_id": "string, e.g. '1'",
      "domain_name": "string",
      "sub_domains": [
        {
          "sub_domain_id": "string, e.g. '1-1'",
          "sub_domain_name": "string",
          "goal": "string",
          "clauses": [
            {
              "clause_id": "string, e.g. '1-1-1'",
              "policy_text": "string",
              "applicability_category_a": "string or null",
              "applicability_category_b": "string or null"
            }
          ]
        }
      ]
    }
  ]
}

Return ONLY valid JSON matching this schema. No markdown, no commentary, no extra keys.
"""


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


# ---------------------------------------------------------------------
# 4) ID-BASED MERGE (fixes duplicate domains from inconsistent keys)
# ---------------------------------------------------------------------
def merge_framework_chunks(chunk_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Merge by domain_id / sub_domain_id / clause_id, not by name, so
    near-identical domain names from different chunks don't create dupes,
    and the same domain_id appearing in two chunks gets combined cleanly."""
    domains_by_id: Dict[str, Dict[str, Any]] = {}
    domain_order: List[str] = []

    for result in chunk_results:
        for domain in result.get("domains", []):
            d_id = str(domain.get("domain_id") or domain.get("domain_name") or "").strip()
            if not d_id:
                continue

            if d_id not in domains_by_id:
                domains_by_id[d_id] = {
                    "domain_id": d_id,
                    "domain_name": domain.get("domain_name", ""),
                    "sub_domains_by_id": {},
                    "sub_domain_order": []
                }
                domain_order.append(d_id)

            dom_entry = domains_by_id[d_id]
            if not dom_entry["domain_name"] and domain.get("domain_name"):
                dom_entry["domain_name"] = domain["domain_name"]

            for sub in domain.get("sub_domains", []):
                s_id = str(sub.get("sub_domain_id") or sub.get("sub_domain_name") or "").strip()
                if not s_id:
                    continue

                if s_id not in dom_entry["sub_domains_by_id"]:
                    dom_entry["sub_domains_by_id"][s_id] = {
                        "sub_domain_id": s_id,
                        "sub_domain_name": sub.get("sub_domain_name", ""),
                        "goal": sub.get("goal", ""),
                        "clauses_by_id": {},
                        "clause_order": []
                    }
                    dom_entry["sub_domain_order"].append(s_id)

                sub_entry = dom_entry["sub_domains_by_id"][s_id]
                if not sub_entry["goal"] and sub.get("goal"):
                    sub_entry["goal"] = sub["goal"]

                for clause in sub.get("clauses", []):
                    c_id = str(clause.get("clause_id") or "").strip()
                    if not c_id:
                        continue
                    # last non-empty policy_text wins (handles partial entries)
                    if c_id not in sub_entry["clauses_by_id"] or clause.get("policy_text"):
                        sub_entry["clauses_by_id"][c_id] = clause
                        if c_id not in sub_entry["clause_order"]:
                            sub_entry["clause_order"].append(c_id)

    # flatten back into plain lists, preserving first-seen order
    final_domains = []
    for d_id in domain_order:
        dom_entry = domains_by_id[d_id]
        sub_domains = []
        for s_id in dom_entry["sub_domain_order"]:
            sub_entry = dom_entry["sub_domains_by_id"][s_id]
            clauses = [sub_entry["clauses_by_id"][c_id] for c_id in sub_entry["clause_order"]]
            sub_domains.append({
                "sub_domain_id": sub_entry["sub_domain_id"],
                "sub_domain_name": sub_entry["sub_domain_name"],
                "goal": sub_entry["goal"],
                "clauses": clauses
            })
        final_domains.append({
            "domain_id": dom_entry["domain_id"],
            "domain_name": dom_entry["domain_name"],
            "sub_domains": sub_domains
        })

    return {"domains": final_domains}


def run_decode_job(job_id: str, file_bytes: bytes, compliance_name: str, filename: str):
    try:
        JOBS[job_id]["status"] = "extracting"
        full_text = extract_pdf_text(file_bytes, first_pages_only=False)
        chunks = chunk_text_by_headings(full_text)
        JOBS[job_id]["total_chunks"] = len(chunks)

        chunk_results = []
        for i, chunk in enumerate(chunks):
            try:
                prompt = f"{EXTRACTION_SCHEMA_PROMPT}\n\nThis is part {i+1} of {len(chunks)} of the document. Extract only what appears in this portion.\n\nText:\n{chunk}"
                raw = call_gemini_with_retry(prompt, json_mode=True)
                chunk_results.append(safe_json_parse(raw))
                print(f"[Job {job_id}] chunk {i+1}/{len(chunks)} done")
            except Exception as chunk_err:
                print(f"[Job {job_id}] chunk {i+1}/{len(chunks)} FAILED: {chunk_err}")
                JOBS[job_id].setdefault("chunk_errors", []).append({"chunk": i + 1, "error": str(chunk_err)})
            JOBS[job_id]["processed_chunks"] = i + 1
            time.sleep(1.5)

        merged = merge_framework_chunks(chunk_results)

        JOBS[job_id]["status"] = "done"
        JOBS[job_id]["result"] = {"filename": filename, "framework_data": merged}

    except Exception as e:
        JOBS[job_id]["status"] = "failed"
        JOBS[job_id]["error"] = str(e)


@app.post("/api/decode")
async def decode_document(
    background_tasks: BackgroundTasks,
    compliance_name: str = Form(...),
    file: UploadFile = File(...)
):
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

    thread = threading.Thread(
        target=run_decode_job,
        args=(job_id, file_bytes, compliance_name, file.filename),
        daemon=True
    )
    thread.start()

    return {"status": "accepted", "job_id": job_id}


@app.get("/api/decode/status/{job_id}")
async def get_job_status(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job


@app.get("/")
async def health_check():
    return {"status": "ok"}


def notify_via_email(data: SubmitRequest):
    sender = os.environ.get("SMTP_USER")
    password = os.environ.get("SMTP_PASS")
    msg = MIMEMultipart()
    msg['From'], msg['To'] = sender, "product@getsahl.io"
    msg['Subject'] = f"Compliance Decoded: {data.company_name}"
    body = f"User: {data.user_name}\nData: {json.dumps(data.edited_data, indent=4, ensure_ascii=False)}"
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