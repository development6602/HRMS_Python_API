import io
import re
from datetime import datetime
from fastapi import HTTPException, status
from pypdf import PdfReader
from docx import Document

MONTH_MAP = {
    'jan': 1, 'january': 1, 'feb': 2, 'february': 2, 'mar': 3, 'march': 3,
    'apr': 4, 'april': 4, 'may': 5, 'jun': 6, 'june': 6, 'jul': 7, 'july': 7,
    'aug': 8, 'august': 8, 'sep': 9, 'sept': 9, 'september': 9, 'oct': 10,
    'october': 10, 'nov': 11, 'november': 11, 'dec': 12, 'december': 12
}

def extract_text_from_pdf(content: bytes) -> str:
    pdf_reader = PdfReader(io.BytesIO(content))
    text_pieces = [page.extract_text() or "" for page in pdf_reader.pages]
    return "\n".join([t for t in text_pieces if t])

def extract_text_from_docx(content: bytes) -> str:
    doc = Document(io.BytesIO(content))
    lines = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    for table in doc.tables:
        for row in table.rows:
            cells = list(dict.fromkeys([c.text.strip() for c in row.cells if c.text.strip()]))
            if cells:
                lines.append(" | ".join(cells))
    return "\n".join(lines)

def extract_text_from_binary_doc(content: bytes) -> str:
    if content.startswith(b'PK\x03\x04'):
        return extract_text_from_docx(content)
    utf16 = [m.decode('utf-16le').strip() for m in re.findall(b'(?:[\x20-\x7E]\x00){3,}', content)]
    return "\n".join([t for t in utf16 if t])

def extract_resume_text(content: bytes, filename: str) -> str:
    lower_name = (filename or "").lower()
    if lower_name.endswith(".pdf") or content.startswith(b'%PDF'):
        return extract_text_from_pdf(content)
    elif lower_name.endswith(".docx") or content.startswith(b'PK\x03\x04'):
        return extract_text_from_docx(content)
    else:
        return extract_text_from_binary_doc(content)

def parse_date_to_month_index(token: str) -> int:
    now = datetime.now()
    clean = token.strip().lower()
    if any(p in clean for p in ['present', 'current', 'continuing', 'continue']):
        return now.year * 12 + now.month
    slash = re.search(r'\b(0?[1-9]|1[0-2])[\/\-](\d{4})\b', clean)
    if slash:
        return int(slash.group(2)) * 12 + int(slash.group(1))
    multi = re.search(r'([a-z]+)[-\/]([a-z]+)\s*(\d{4})', clean)
    if multi and multi.group(2) in MONTH_MAP:
        return int(multi.group(3)) * 12 + MONTH_MAP[multi.group(2)]
    word = re.search(r'([a-z]+)\s*(\d{4})', clean)
    if word and word.group(1) in MONTH_MAP:
        return int(word.group(2)) * 12 + MONTH_MAP[word.group(1)]
    year = re.search(r'\b(20\d{2}|19\d{2})\b', clean)
    if year:
        return int(year.group(1)) * 12 + 6
    return 0

def parse_candidate_email(text: str) -> str:
    m = re.search(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', text)
    return m.group(0).rstrip('.,;:') if m else ""

def parse_candidate_phone(text: str) -> str:
    matches = re.findall(r'(?:\+?\d{1,3}[\s\-]?)?(?:\(?\d{2,5}\)?[\s\-]?)?\d{4,5}[\s\-]?\d{4,5}', text)
    for m in matches:
        digits = re.sub(r'\D', '', m)
        if 10 <= len(digits) <= 12:
            return m.strip()
    return ""

def parse_candidate_name(text: str) -> tuple[str, str]:
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    blacklist = {'resume', 'cv', 'curriculum', 'contact', 'summary', 'profile', 'education', 'experience', 'projects', 'skills'}
    for line in lines[:10]:
        clean = re.sub(r'[^a-zA-Z\s]', '', line).strip()
        words = clean.split()
        if 2 <= len(words) <= 4 and not any(b in clean.lower() for b in blacklist):
            if '@' not in line and '+' not in line and not any(ch.isdigit() for ch in line):
                return words[0].title(), " ".join(words[1:]).title()
    for line in lines[:5]:
        clean = re.sub(r'[^a-zA-Z\s]', '', line).strip()
        words = clean.split()
        if len(words) == 1 and words[0].lower() not in blacklist:
            return words[0].title(), ""
    return "", ""

def parse_candidate_position(text: str) -> str:
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    exp_title = re.search(r'(?:PROFESSIONAL\s+EXPERIENCE|WORK\s+EXPERIENCE|EXPERIENCE)[\s\S]*?\n\s*([A-Za-z\/\-\s\&]{4,35})\s*\|', text, re.I)
    if exp_title:
        role = exp_title.group(1).strip()
        if not any(b in role.lower() for b in ['company', 'solution', 'experience', 'client']):
            return role
    for line in lines[1:5]:
        clean = re.sub(r'[^a-zA-Z\/\-\s\&]', '', line).strip()
        lower = line.lower()
        if '@' not in line and '+' not in line and 'http' not in lower and 'github' not in lower and 'linkedin' not in lower:
            if any(k in lower for k in ['developer', 'engineer', 'analyst', 'scientist', 'executive', 'lead', 'intern', 'ai/ml', 'full stack', 'python']):
                if 3 <= len(clean) <= 40:
                    return clean
    common = [
        "Full Stack Developer", "Full Stack Engineer", "MERN Stack Developer", "AI/ML Developer", "AI-ML Developer",
        "AI/ML Engineer", "AI-ML Engineer", "Machine Learning Developer", "Machine Learning Engineer", "Data Scientist",
        "Python Developer", "Python Engineer", "Frontend Developer", "Backend Developer", "Software Engineer",
        "Software Developer", "Web Developer", "Data Analyst", "DevOps Engineer", "React Developer", "BDE"
    ]
    for r in common:
        if re.search(r'(?<!\w)' + r'\s+'.join(re.escape(w) for w in r.split()) + r'(?!\w)', text[:1500], re.I):
            return r
    return ""

# def parse_candidate_experience(text: str) -> str:
#     exp_match = re.search(
#         r'(?:WORK\s+EXPERIENCE|PROFESSIONAL\s+EXPERIENCE|EMPLOYMENT\s+HISTORY|INTERNSHIPS?|EXPERIENCE)\s*[:\n\r]+'
#         r'([\s\S]+?)'
#         r'(?=(?:PROJECTS?|PROJECT\s+DETAILS|ACADEMIC\s+QUALIFICATIONS|EDUCATION|TECHNICAL\s+SKILLS|SKILLS|CERTIFICATIONS|ACHIEVEMENTS|AWARDS|LANGUAGES|DECLARATION|$))',
#         text, re.I
#     )
#     if exp_match:
#         ranges = re.findall(
#             r'((?:(?:\d{1,2}[\/\-])?(?:[a-zA-Z]+(?:-[a-zA-Z]+)?\s*)?\d{4}|present|current|continuing))\s*[-–to~]+\s*'
#             r'((?:(?:\d{1,2}[\/\-])?(?:[a-zA-Z]+(?:-[a-zA-Z]+)?\s*)?\d{4}|present|current|continuing))',
#             exp_match.group(1), re.I
#         )
#         intervals = []
#         for s_str, e_str in ranges:
#             s_idx = parse_date_to_month_index(s_str)
#             e_idx = parse_date_to_month_index(e_str)
#             if s_idx > 0 and e_idx >= s_idx and (e_idx - s_idx) <= 180:
#                 intervals.append((s_idx, max(s_idx + 1, e_idx)))
#         if intervals:
#             intervals.sort(key=lambda x: x[0])
#             merged = []
#             for s, e in intervals:
#                 if not merged or s > merged[-1][1]:
#                     merged.append([s, e])
#                 else:
#                     merged[-1][1] = max(merged[-1][1], e)
#             total = sum(e - s for s, e in merged)
#             if total >= 12:
#                 y = round(total / 12, 1)
#                 return f"{int(y) if y.is_integer() else y} Years"
#             elif total > 0:
#                 return f"{total} Months"

#     lower = text.lower()
#     tenure = re.search(r'(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?)', text, re.I)
#     if tenure: return f"{tenure.group(1)} Years"
#     months = re.search(r'(\d+)\+?\s*(?:months?|mos?)', text, re.I)
#     if months:
#         m = int(months.group(1))
#         return f"{round(m / 12, 1)} Years" if m >= 12 else f"{m} Months"
#     if "fresher" in lower or "entry level" in lower: return "Fresher"
#     years = [int(y) for y in re.findall(r'\b(20[12]\d)\b', text)]
#     if years and max(years) >= datetime.now().year: return "Fresher"
#     return "Fresher"
def parse_candidate_experience(text: str) -> str:
    """
    Tier 1: WORK EXPERIENCE / INTERNSHIPS section se exact date duration calculate karta hai.
            (Interval Merging ke saath taaki parallel projects double-count na hon).
    Tier 2 (Fallback): Text-based "X years experience" ya "Fresher" check karta hai.
    """
    # ========================================================
    # TIER 1: EXPERIENCE SECTION DATES CALCULATION
    # ========================================================
    # ✨ Fix 1: Chipke huye month words ko alag karein (e.g. TechnologiesJan -> Technologies Jan)
    normalized_text = re.sub(
        r'([a-zA-Z])(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\b',
        r'\1 \2',
        text,
        flags=re.IGNORECASE
    )

    # ✨ Fix 2: Lookahead ko sirf nayi line (\n\s*) wale section headers par match karein
    # (Taaki "within project timelines" jaisa sentence beech me section ko cut na kare)
    exp_section_match = re.search(
        r'(?:WORK\s+EXPERIENCE|PROFESSIONAL\s+EXPERIENCE|EMPLOYMENT\s+HISTORY|INTERNSHIPS?|EXPERIENCE)\s*[:\n\r]+'
        r'([\s\S]+?)'
        r'(?=\n\s*(?:PROJECTS?|PROJECT\s+DETAILS|ACADEMIC\s+QUALIFICATIONS|EDUCATION|TECHNICAL\s+SKILLS|SKILLS|CERTIFICATIONS|ACHIEVEMENTS|AWARDS|LANGUAGES|DECLARATION)\s*[:\n\r]|$)',
        normalized_text,
        re.IGNORECASE
    )

    if exp_section_match:
        exp_text = exp_section_match.group(1)
        token_rx = r'(?:(?:\d{1,2}[\/\-])?(?:[a-zA-Z]+(?:-[a-zA-Z]+)?\s*)?\d{4}|present|current|continuing|continue)'
        # Dash, En-dash, Em-dash (- – —) sabhi support karein
        date_range_pattern = rf'({token_rx})\s*[-–—to~]+\s*({token_rx})'
        ranges = re.findall(date_range_pattern, exp_text, re.IGNORECASE)

        intervals = []
        for start_str, end_str in ranges:
            start_idx = parse_date_to_month_index(start_str)
            end_idx = parse_date_to_month_index(end_str)
            
            if start_idx > 0 and end_idx >= start_idx:
                duration = end_idx - start_idx
                if 0 <= duration <= 180:
                    # Interval store karein (start_month, end_month)
                    intervals.append((start_idx, max(start_idx + 1, end_idx)))

        # ✨ Overlapping Date Intervals ko Merge karein
        if intervals:
            intervals.sort(key=lambda x: x[0])
            merged = []
            for s, e in intervals:
                if not merged or s > merged[-1][1]:
                    merged.append([s, e])
                else:
                    merged[-1][1] = max(merged[-1][1], e)

            # Merged continuous working months ka sum
            total_months = sum(e - s for s, e in merged)

            if total_months >= 12:
                years = round(total_months / 12, 1)
                return f"{int(years) if years.is_integer() else years} Years"
            elif total_months > 0:
                return f"{total_months} Months"

    # ========================================================
    # TIER 2: FALLBACK (AGAR DATES NA MILEIN TO PURANA LOGIC)
    # ========================================================
    lower_text = text.lower()

    # 1. Direct explicit tenure mention (e.g. "2.5 years of experience")
    tenure_match = re.search(
        r'(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?)(?:\s*(?:of)?\s*experience)?',
        text,
        re.IGNORECASE
    )
    if tenure_match:
        return f"{tenure_match.group(1)} Years"

    # 2. Months mention (e.g. "6 months experience")
    month_match = re.search(
        r'(\d+)\+?\s*(?:months?|mos?)(?:\s*(?:of)?\s*experience)?',
        text,
        re.IGNORECASE
    )
    if month_match:
        m_val = int(month_match.group(1))
        return f"{round(m_val / 12, 1)} Years" if m_val >= 12 else f"{m_val} Months"

    # 3. Direct Fresher keywords
    if "fresher" in lower_text or "entry level" in lower_text or "recent graduate" in lower_text:
        return "Fresher"

    # 4. College pursuing student check
    year_matches = [int(y) for y in re.findall(r'\b(20[12]\d)\b', text)]
    if year_matches and max(year_matches) >= datetime.now().year:
        return "Fresher"

    return "Fresher"

def parse_uploaded_resume_file(content: bytes, filename: str) -> dict:
    lower_name = (filename or "").lower()
    if not any(lower_name.endswith(ext) for ext in (".pdf", ".docx", ".doc")):
        raise HTTPException(status_code=400, detail=f"Unsupported format '{filename}'. Allowed: .pdf, .docx, .doc")
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    resume_text = extract_resume_text(content, filename).strip()
    if not resume_text:
        raise HTTPException(status_code=422, detail="Could not extract readable text from uploaded file.")
    first_name, last_name = parse_candidate_name(resume_text)
    return {
        "success": True,
        "data": {
            "firstName": first_name,
            "lastName": last_name,
            "email": parse_candidate_email(resume_text),
            "phone": parse_candidate_phone(resume_text),
            "position": parse_candidate_position(resume_text),
            "experience": parse_candidate_experience(resume_text)
        },
        "message": "Resume parsed successfully"
    }
