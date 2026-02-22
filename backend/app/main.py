from __future__ import annotations

import hashlib
import io
import re
from typing import Dict, List

from docx import Document
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Citation Scout API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Improved patterns for law review citations
# Case: handles v/v./vs./versus, multiple reporters, pin cites, court parentheticals
CASE_CITATION_PATTERN = re.compile(
    r"\b([A-Z][A-Za-z0-9.'&\- ]+\s+(?:v\.?|vs\.?|versus)\s+[A-Z][A-Za-z0-9.'&\- ]+,?\s+\d+\s+[A-Za-z. ]+\s*\d+(?:,\s*\d+)?(?:\s+\([^)]+\d{4}\)))\b",
    re.IGNORECASE
)

# Short form citations (e.g., "Smith, 123 F.3d at 458")
SHORT_FORM_PATTERN = re.compile(
    r"\b([A-Z][A-Za-z0-9.'&\- ]+,?\s+\d+\s+[A-Za-z. ]+\s+at\s+\d+)\b"
)

# Statutes: U.S.C. and state codes
STATUTE_CITATION_PATTERN = re.compile(
    r"\b(\d+\s+(?:U\.?S\.?C\.?|U\.?S\.?C\.?A\.?)(?:\s+§+\s*|\s+sec\.?\s+|\s+section\s+)\d+[A-Za-z0-9\-\.]*)\b",
    re.IGNORECASE
)

# State statute patterns
STATE_STATUTE_PATTERN = re.compile(
    r"\b((?:Cal\.?|Calif\.?|N\.?Y\.?|New York|Tex\.?|Texas|Fla\.?|Florida|Ill\.?|Illinois|Pa\.?|Pennsylvania)\.?\s+(?:Penal|Civil|Civ\.?|Fam\.?|Prob\.?|Govt\.?|Gov\.?|Health|Saf\.?|Safety|Bus\.?|Bus\.\s+\u0026\s+Prof\.?|Unif\.?|Commercial|Com\.?|Corr\.?|Ed\.?|Educ\.?|Elec\.?|Fish|Food|Harb\.?|Harbors|Ins\.?|Ins\.?|Lab\.?|Labor|Pub\.?|Public|Rev\.?|Revenue|Sts\.?|Sts\.?\s+\u0026\s+High\.?|Unemp\.?|Unemployment|Veh\.?|Vehicle|Wat\.?|Water|Welf\.?|Welfare)\s+(?:Code|Law|Ann\.?|Acts|Stat\.?|Statutes)?(?:\s+§+\s*|\s+sec\.?\s+|\s+section\s+)\d+[A-Za-z0-9\-\.]*)\b",
    re.IGNORECASE
)

# Regulations: C.F.R. and state registers
REGULATION_CITATION_PATTERN = re.compile(
    r"\b(\d+\s+(?:C\.?F\.?R\.?|C\.?F\.?R\.?)(?:\s+§+\s*|\s+sec\.?\s+|\s+section\s+)\d+(?:\.\d+)?[A-Za-z0-9\-\.]*)\b",
    re.IGNORECASE
)

# State regulations
STATE_REG_PATTERN = re.compile(
    r"\b((?:Cal\.?|N\.?Y\.?|Tex\.?|Fla\.?|Ill\.?|Pa\.?)?\.?\s*(?:Code|Comp\.?)?\s*(?:of)?\s*(?:Regs?\.?|Regulations|Administrative|Admin\.?)\.?\s*(?:tit\.?|title)?\s*\.?\s*\d+(?:,\s+)?(?:\s+§+\s*|\s+sec\.?\s+|\s+section\s+)\d+[A-Za-z0-9\-\.]*)\b",
    re.IGNORECASE
)


def mock_validation_status(citation_text: str) -> str:
    digest = hashlib.md5(citation_text.encode("utf-8")).hexdigest()
    bucket = int(digest[-1], 16) % 3
    if bucket == 0:
        return "valid"
    if bucket == 1:
        return "review"
    return "invalid"


def find_citations(text: str, citation_type: str, pattern: re.Pattern[str]) -> List[Dict[str, str]]:
    matches = []
    seen = set()

    for match in pattern.finditer(text):
        value = match.group(1).strip()
        if value not in seen:
            seen.add(value)
            matches.append(
                {
                    "type": citation_type,
                    "text": value,
                    "status": mock_validation_status(value),
                }
            )

    return matches


def extract_docx_text(file_bytes: bytes) -> str:
    try:
        document = Document(io.BytesIO(file_bytes))
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Unable to parse .docx file.") from exc

    paragraphs = [p.text.strip() for p in document.paragraphs if p.text.strip()]
    return "\n".join(paragraphs)


@app.get("/health")
def health_check() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/upload")
async def upload_docx(file: UploadFile = File(...)) -> Dict[str, object]:
    if not file.filename.lower().endswith(".docx"):
        raise HTTPException(status_code=400, detail="Only .docx files are supported.")

    payload = await file.read()
    if not payload:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    text = extract_docx_text(payload)

    citations = []
    citations.extend(find_citations(text, "case", CASE_CITATION_PATTERN))
    citations.extend(find_citations(text, "case_short", SHORT_FORM_PATTERN))
    citations.extend(find_citations(text, "statute", STATUTE_CITATION_PATTERN))
    citations.extend(find_citations(text, "statute_state", STATE_STATUTE_PATTERN))
    citations.extend(find_citations(text, "regulation", REGULATION_CITATION_PATTERN))
    citations.extend(find_citations(text, "regulation_state", STATE_REG_PATTERN))

    return {
        "filename": file.filename,
        "citation_count": len(citations),
        "citations": citations,
        "extracted_text_preview": text[:2000] + "..." if len(text) > 2000 else text,
    }
