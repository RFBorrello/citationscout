from __future__ import annotations

import hashlib
import io
import re
from collections.abc import Iterable
from typing import Any, Dict, List

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


# Case: handles v/v./vs./versus, multiple reporters, pin cites, court parentheticals
CASE_CITATION_PATTERN = re.compile(
    r"\b([A-Z][A-Za-z0-9.'&\- ]+\s+(?:v\.?|vs\.?|versus)\s+[A-Z][A-Za-z0-9.'&\- ]+,?\s+\d+\s+[A-Za-z. ]+\s*\d+(?:,\s*\d+)?(?:\s+\([^)]+\d{4}\)))\b",
    re.IGNORECASE,
)

# Short form citations (e.g., "Smith, 123 F.3d at 458")
SHORT_FORM_PATTERN = re.compile(
    r"\b([A-Z][A-Za-z0-9.'&\- ]+,?\s+\d+\s+[A-Za-z. ]+\s+at\s+\d+)\b"
)

# Statutes: U.S.C. and state codes
STATUTE_CITATION_PATTERN = re.compile(
    r"\b(\d+\s+(?:U\.?S\.?C\.?|U\.?S\.?C\.?A\.?)(?:\s+\u00A7+\s*|\s+sec\.?\s+|\s+section\s+)\d+[A-Za-z0-9\-\.]*)\b",
    re.IGNORECASE,
)

# State statute patterns
STATE_STATUTE_PATTERN = re.compile(
    r"\b((?:Cal\.?|Calif\.?|N\.?Y\.?|New York|Tex\.?|Texas|Fla\.?|Florida|Ill\.?|Illinois|Pa\.?|Pennsylvania)\.?\s+(?:Penal|Civil|Civ\.?|Fam\.?|Prob\.?|Govt\.?|Gov\.?|Health|Saf\.?|Safety|Bus\.?|Bus\.\s+\u0026\s+Prof\.?|Unif\.?|Commercial|Com\.?|Corr\.?|Ed\.?|Educ\.?|Elec\.?|Fish|Food|Harb\.?|Harbors|Ins\.?|Lab\.?|Labor|Pub\.?|Public|Rev\.?|Revenue|Sts\.?|Sts\.?\s+\u0026\s+High\.?|Unemp\.?|Unemployment|Veh\.?|Vehicle|Wat\.?|Water|Welf\.?|Welfare)\s+(?:Code|Law|Ann\.?|Acts|Stat\.?|Statutes)?(?:\s+\u00A7+\s*|\s+sec\.?\s+|\s+section\s+)\d+[A-Za-z0-9\-\.]*)\b",
    re.IGNORECASE,
)

# Regulations: C.F.R. and state registers
REGULATION_CITATION_PATTERN = re.compile(
    r"\b(\d+\s+(?:C\.?F\.?R\.?)(?:\s+\u00A7+\s*|\s+sec\.?\s+|\s+section\s+)\d+(?:\.\d+)?[A-Za-z0-9\-\.]*)\b",
    re.IGNORECASE,
)

# State regulations
STATE_REG_PATTERN = re.compile(
    r"\b((?:Cal\.?|N\.?Y\.?|Tex\.?|Fla\.?|Ill\.?|Pa\.?)?\.?\s*(?:Code|Comp\.?)?\s*(?:of)?\s*(?:Regs?\.?|Regulations|Administrative|Admin\.?)\.?\s*(?:tit\.?|title)?\s*\.?\s*\d+(?:,\s+)?(?:\s+\u00A7+\s*|\s+sec\.?\s+|\s+section\s+)\d+[A-Za-z0-9\-\.]*)\b",
    re.IGNORECASE,
)

# Law review articles
LAW_REVIEW_PATTERN = re.compile(
    r"\b((?:(?:[A-Z][A-Za-z.'\- ]+(?:,\s*(?:Jr\.?|Sr\.?|II|III|IV|V))?,\s+)?(?:\"[^\"]+\"|[A-Z][^,\n]{3,180}),\s+)?\d{1,3}\s+[A-Z][A-Za-z.&'\- ]+L\.?\s*Rev\.?\s+\d{1,5}(?:,\s*\d{1,5})?(?:\s*\(\d{4}\))?)\b"
)

# Agency publications (Federal Register, SEC/FDA/EPA docs)
AGENCY_PUBLICATION_PATTERN = re.compile(
    r"\b((?:\d+\s+Fed\.?\s+Reg\.?\s+\d+)|"
    r"(?:(?:SEC|S\.?E\.?C\.?)\s+(?:Release|Rel\.?|No\.?)\s*(?:No\.?\s*)?[A-Za-z0-9\-\/]+)|"
    r"(?:(?:FDA|Food and Drug Administration)\s+Guidance(?:\s+for\s+Industry)?(?:[:\-]\s*[A-Z][^.;\n]+)?)|"
    r"(?:(?:EPA|Environmental Protection Agency)\s+(?:Guidance|Final Rule|Report|Technical Document|Notice)(?:[:\-]\s*[A-Z][^.;\n]+)?))\b",
    re.IGNORECASE,
)

# Foreign law (UK, EU, Canada, Australia)
FOREIGN_LAW_PATTERN = re.compile(
    r"(?<!\w)((?:\[\d{4}\]\s+UKSC\s+\d+)|"
    r"(?:\[\d{4}\]\s+\d+\s+AC\s+\d+)|"
    r"(?:Case\s+C-\d+\/\d+)|"
    r"(?:Directive\s+\d{4}\/\d+\/EU)|"
    r"(?:\[\d{4}\]\s+\d+\s+SCR\s+\d+)|"
    r"(?:\[\d{4}\]\s+HCA\s+\d+))(?!\w)",
    re.IGNORECASE,
)

# Constitutional citations (federal and state)
CONSTITUTIONAL_PATTERN = re.compile(
    r"\b((?:U\.?S\.?\s+Const\.?|"
    r"(?:Ala\.?|Alaska|Ariz\.?|Ark\.?|Cal\.?|Calif\.?|Colo\.?|Conn\.?|Del\.?|Fla\.?|Ga\.?|Haw\.?|Idaho|Ill\.?|Ind\.?|Iowa|Kan\.?|Ky\.?|La\.?|Maine|Md\.?|Mass\.?|Mich\.?|Minn\.?|Miss\.?|Mo\.?|Mont\.?|Neb\.?|Nev\.?|N\.?H\.?|N\.?J\.?|N\.?M\.?|N\.?Y\.?|N\.?C\.?|N\.?D\.?|Ohio|Okla\.?|Or\.?|Pa\.?|R\.?I\.?|S\.?C\.?|S\.?D\.?|Tenn\.?|Tex\.?|Utah|Vt\.?|Va\.?|Wash\.?|W\.?Va\.?|Wis\.?|Wyo\.?)\s+Const\.?)"
    r"(?:\s*,?\s*(?:amend\.?\s*[IVXLC]+|art\.?\s*[IVXLC]+|sec\.?\s*\d+[A-Za-z\-]*|cl\.?\s*\d+|pt\.?\s*[IVXLC]+|para\.?\s*\d+))+)\b",
    re.IGNORECASE,
)

PATTERN_SPECS = [
    ("case", CASE_CITATION_PATTERN),
    ("case_short", SHORT_FORM_PATTERN),
    ("statute", STATUTE_CITATION_PATTERN),
    ("statute_state", STATE_STATUTE_PATTERN),
    ("regulation", REGULATION_CITATION_PATTERN),
    ("regulation_state", STATE_REG_PATTERN),
    ("law_review", LAW_REVIEW_PATTERN),
    ("agency_publication", AGENCY_PUBLICATION_PATTERN),
    ("foreign_law", FOREIGN_LAW_PATTERN),
    ("constitutional", CONSTITUTIONAL_PATTERN),
]


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


def build_pattern_diagnostics(
    text: str, pattern_specs: List[tuple[str, re.Pattern[str]]], sample_limit: int = 5
) -> List[Dict[str, object]]:
    diagnostics: List[Dict[str, object]] = []
    for citation_type, pattern in pattern_specs:
        matches = find_citations(text, citation_type, pattern)
        diagnostics.append(
            {
                "type": citation_type,
                "match_count": len(matches),
                "samples": [item["text"] for item in matches[:sample_limit]],
            }
        )
    return diagnostics


def _extract_non_empty_paragraphs(paragraphs: Iterable[object]) -> List[str]:
    texts = []
    for paragraph in paragraphs:
        value = getattr(paragraph, "text", "")
        if not isinstance(value, str):
            continue
        cleaned = value.strip()
        if cleaned:
            texts.append(cleaned)
    return texts


def _extract_text_from_part_xml(part: Any) -> List[str]:
    """Extract visible text runs from a DOCX XML part."""
    if not hasattr(part, "element"):
        return []

    chunks = []
    for text_node in part.element.xpath(".//w:t"):
        value = getattr(text_node, "text", None)
        if not isinstance(value, str):
            continue
        cleaned = value.strip()
        if cleaned:
            chunks.append(cleaned)
    return chunks


def _extract_related_part_text(document: Document) -> List[str]:
    """Collect text from related parts (headers, footers, notes, comments)."""
    texts = []
    rel_suffixes = ("/header", "/footer", "/footnotes", "/endnotes", "/comments")

    for rel in document.part.rels.values():
        if not rel.reltype.endswith(rel_suffixes):
            continue
        texts.extend(_extract_text_from_part_xml(rel.target_part))

    return texts


def normalize_extracted_text(text: str) -> str:
    # Normalize uncommon whitespace so regex matching remains reliable.
    replacements = {
        "\u00a0": " ",
        "\u2007": " ",
        "\u2009": " ",
        "\u200a": " ",
        "\u202f": " ",
        "\u2060": "",
        "\ufeff": "",
    }
    normalized = text.translate(str.maketrans(replacements))
    # DOCX runs frequently introduce line breaks mid-citation; collapse all whitespace.
    return re.sub(r"\s+", " ", normalized).strip()


def _extract_footnote_paragraphs(document: Document) -> List[str]:
    """Extract footnote text directly from DOCX relationships/XML."""
    paragraphs = []

    for rel in document.part.rels.values():
        if not rel.reltype.endswith("/footnotes"):
            continue

        footnotes_part = rel.target_part
        if not hasattr(footnotes_part, "element"):
            continue

        for footnote in footnotes_part.element.xpath(".//w:footnote"):
            # Skip separator/continuation entries and keep only user-authored footnotes.
            footnote_type = footnote.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}type")
            if footnote_type:
                continue

            for paragraph in footnote.xpath(".//w:p"):
                runs = [node.text for node in paragraph.xpath(".//w:t") if node.text]
                text = "".join(runs).strip()
                if text:
                    paragraphs.append(text)

    return paragraphs


def extract_docx_text(file_bytes: bytes) -> str:
    try:
        document = Document(io.BytesIO(file_bytes))
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Unable to parse .docx file.") from exc

    extracted_chunks = []

    # Pull all visible text runs from the main document XML (captures tables too).
    extracted_chunks.extend(_extract_text_from_part_xml(document.part))

    # Main body paragraphs retained as a fallback for odd DOCX encodings.
    extracted_chunks.extend(_extract_non_empty_paragraphs(document.paragraphs))

    # Include footnotes explicitly; law review citations are frequently contained there.
    extracted_chunks.extend(_extract_footnote_paragraphs(document))

    # Include related text-bearing parts (headers, footers, endnotes, comments).
    extracted_chunks.extend(_extract_related_part_text(document))

    joined = "\n".join(extracted_chunks)
    return normalize_extracted_text(joined)


@app.get("/health")
def health_check() -> Dict[str, str]:
    return {"status": "ok"}


async def read_docx_upload(file: UploadFile) -> str:
    if not file.filename.lower().endswith(".docx"):
        raise HTTPException(status_code=400, detail="Only .docx files are supported.")

    payload = await file.read()
    if not payload:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    return extract_docx_text(payload)


@app.post("/upload")
async def upload_docx(file: UploadFile = File(...)) -> Dict[str, object]:
    text = await read_docx_upload(file)

    citations = []
    for citation_type, pattern in PATTERN_SPECS:
        citations.extend(find_citations(text, citation_type, pattern))

    return {
        "filename": file.filename,
        "citation_count": len(citations),
        "citations": citations,
        "extracted_text_preview": text[:2000] + "..." if len(text) > 2000 else text,
    }


@app.post("/debug")
async def debug_docx(file: UploadFile = File(...)) -> Dict[str, object]:
    text = await read_docx_upload(file)
    pattern_diagnostics = build_pattern_diagnostics(text, PATTERN_SPECS)
    return {
        "filename": file.filename,
        "raw_extracted_text": text,
        "character_count": len(text),
        "pattern_diagnostics": pattern_diagnostics,
    }
