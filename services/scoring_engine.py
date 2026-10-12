import json
import re
import os
from datetime import datetime

CRITERIA_FILE_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "criteria", "roles_criteria.json")
    if os.path.basename(os.path.dirname(__file__)) == "services"
    else os.path.join(os.path.dirname(__file__), "criteria", "roles_criteria.json")
)


def load_criteria():
    """
    JSON file se criteria dynamically load karta hai.
    """
    if not os.path.exists(CRITERIA_FILE_PATH):
        raise FileNotFoundError(f"Criteria file not found at {CRITERIA_FILE_PATH}")
    with open(CRITERIA_FILE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def check_keyword_in_text(text: str, keywords: list) -> bool:
    """
    Case-insensitive aur smart boundary matching.
    """
    for kw in keywords:
        pattern = r"(?<!\w)" + re.escape(kw) + r"(?!\w)"
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


def evaluate_tech_stack(text: str, role_tech_criteria: dict) -> dict:
    """
    Tech stack score evaluate karta hai (Out of 20).
    """
    total_tech_score = 0
    max_tech_score = role_tech_criteria.get("max_score", 20)
    matched_skills = []
    missing_skills = []
    skill_breakdown = []

    # 1. Core Skills Check
    for skill in role_tech_criteria.get("core_skills", []):
        name = skill["name"]
        keywords = skill["keywords"]
        points = skill["points"]
        
        is_matched = check_keyword_in_text(text, keywords)
        if is_matched:
            total_tech_score += points
            matched_skills.append(name)
            skill_breakdown.append({
                "skill": name,
                "category": "Core Skill",
                "status": "Matched",
                "scoreEarned": points,
                "maxPoints": points
            })
        else:
            missing_skills.append(name)
            skill_breakdown.append({
                "skill": name,
                "category": "Core Skill",
                "status": "Not Matched",
                "scoreEarned": 0,
                "maxPoints": points
            })

    # 2. Good-to-have Skills Check
    for skill in role_tech_criteria.get("good_to_have", []):
        name = skill["name"]
        keywords = skill["keywords"]
        points = skill["points"]
        
        is_matched = check_keyword_in_text(text, keywords)
        if is_matched:
            total_tech_score += points
            matched_skills.append(name)
            skill_breakdown.append({
                "skill": name,
                "category": "Good to Have",
                "status": "Matched",
                "scoreEarned": points,
                "maxPoints": points
            })
        else:
            missing_skills.append(name)
            skill_breakdown.append({
                "skill": name,
                "category": "Good to Have",
                "status": "Not Matched",
                "scoreEarned": 0,
                "maxPoints": points
            })

    final_tech_score = min(total_tech_score, max_tech_score)

    return {
        "score": final_tech_score,
        "maxScore": max_tech_score,
        "matchedCount": len(matched_skills),
        "missingCount": len(missing_skills),
        "matchedSkills": matched_skills,
        "missingSkills": missing_skills,
        "details": skill_breakdown
    }


def evaluate_education(text: str, role_edu_criteria: dict) -> dict:
    """
    Education qualification evaluate karta hai (Out of 15).
    Supports:
    1. Standalone Degrees (MCA, BCA)
    2. Degree + Branch Proximity (B.Tech in CSE)
    3. Technical Branch directly in Education section (e.g. SCET - Artificial Intelligence and Data Science)
    4. Standalone Engineering Degree (e.g. Bachelor of Technology / B.Tech from university)
    """
    max_score = role_edu_criteria.get("max_score", 15)
    matched_degree_info = None

    # Fix: LaTeX font kerning glitches normalize karein
    normalized_text = re.sub(r'\bB\s*\.\s*T\s+ech\b', 'B.Tech', text, flags=re.IGNORECASE)
    normalized_text = re.sub(r'\bM\s*\.\s*T\s+ech\b', 'M.Tech', normalized_text, flags=re.IGNORECASE)

    # Education Section extract karein (Focused Search ke liye)
    edu_section_match = re.search(
        r'(?:EDUCATION|ACADEMIC\s+QUALIFICATIONS?|ACADEMICS?)\s*[:\n\r]+'
        r'([\s\S]+?)'
        r'(?=(?:PROJECTS?|EXPERIENCE|WORK\s+EXPERIENCE|SKILLS|TECHNICAL\s+SKILLS|CERTIFICATIONS|ACHIEVEMENTS|LEADERSHIP|$))',
        normalized_text,
        re.IGNORECASE
    )
    edu_section_text = edu_section_match.group(1) if edu_section_match else normalized_text

    # -------------------------------------------------------------
    # Step 1: Standalone degrees check karein (MCA, BCA)
    # -------------------------------------------------------------
    for degree in role_edu_criteria.get("standalone_degrees", []):
        if check_keyword_in_text(normalized_text, degree["keywords"]):
            matched_degree_info = degree["name"]
            break

    # -------------------------------------------------------------
    # Step 2: Degree + Branch Proximity check karein (e.g. B.Tech in IT)
    # -------------------------------------------------------------
    if not matched_degree_info:
        degree_levels = role_edu_criteria.get("degree_levels", [])
        qualifying_branches = role_edu_criteria.get("qualifying_branches", [])

        for deg in degree_levels:
            for deg_kw in deg["keywords"]:
                for branch in qualifying_branches:
                    pat1 = r"(?<!\w)" + re.escape(deg_kw) + r"(?!\w)[\s\S]{0,60}?(?<!\w)" + re.escape(branch) + r"(?!\w)"
                    pat2 = r"(?<!\w)" + re.escape(branch) + r"(?!\w)[\s\S]{0,60}?(?<!\w)" + re.escape(deg_kw) + r"(?!\w)"

                    if re.search(pat1, normalized_text, re.IGNORECASE) or re.search(pat2, normalized_text, re.IGNORECASE):
                        matched_degree_info = f"{deg['name']} in {branch.title()}"
                        break
                if matched_degree_info:
                    break
            if matched_degree_info:
                break

    # -------------------------------------------------------------
    # Step 3: Direct Technical Branch in Education Section (Kunj Desai Case)
    # -------------------------------------------------------------
    if not matched_degree_info:
        qualifying_branches = role_edu_criteria.get("qualifying_branches", [])
        for branch in qualifying_branches:
            branch_pat = r"(?<!\w)" + re.escape(branch) + r"(?!\w)"
            if re.search(branch_pat, edu_section_text, re.IGNORECASE):
                matched_degree_info = f"Degree in {branch.title()}"
                break

    # -------------------------------------------------------------
    # Step 4: Standalone Engineering Degree check (Reshma Sri Case)
    # -------------------------------------------------------------
    if not matched_degree_info:
        engg_patterns = [
            r'\bb\.?\s*tech\b', r'\bbtech\b', r'\bbachelor\s+of\s+technology\b',
            r'\bb\.?\s*e\.?\b', r'\bbachelor\s+of\s+engineering\b',
            r'\bm\.?\s*tech\b', r'\bmtech\b', r'\bmaster\s+of\s+technology\b'
        ]
        for pat in engg_patterns:
            if re.search(pat, edu_section_text, re.IGNORECASE):
                matched_degree_info = "Bachelor of Technology / Engineering (Technical Degree)"
                break

    # -------------------------------------------------------------
    # Final Result
    # -------------------------------------------------------------
    if matched_degree_info:
        return {
            "score": max_score,
            "maxScore": max_score,
            "status": "Matched",
            "matchedDegree": matched_degree_info,
            "note": "Candidate holds a qualifying technical degree."
        }
    else:
        return {
            "score": 0,
            "maxScore": max_score,
            "status": "Not Matched",
            "matchedDegree": None,
            "note": "No matching qualifying degree/branch found in resume."
        }

# ==========================================
# 🕒 CAREER GAP & EXPERIENCE EVALUATOR
# ==========================================

MONTH_MAP = {
    'jan': 1, 'january': 1, 'feb': 2, 'february': 2, 'mar': 3, 'march': 3,
    'apr': 4, 'april': 4, 'may': 5, 'jun': 6, 'june': 6, 'jul': 7, 'july': 7,
    'aug': 8, 'august': 8, 'sep': 9, 'september': 9, 'oct': 10, 'october': 10,
    'nov': 11, 'november': 11, 'dec': 12, 'december': 12
}

def parse_date_token_to_month_index(token: str) -> int:
    """
    Universal Date Parser:
    Har tarah ke formats ko absolute month number me convert karta hai:
    - Slash/Dash numbers: '02/2024', '2/2024', '08-2023'
    - Words + Year: 'Jun 2025', 'August 2023'
    - Multi-month: 'July-Sep 2024'
    - Pure Year: '2024', '2026'
    - Ongoing: 'Present', 'Current', 'Continuing'
    """
    clean = token.strip().lower()
    now = datetime.now()
    current_index = now.year * 12 + now.month

    if clean in ['present', 'current', 'continuing', 'continue', 'till date']:
        return current_index

    # 1. Numeric Slash / Dash format: "02/2024", "07-2023", "2/2024"
    slash_match = re.search(r'\b(\d{1,2})[\/\-](\d{4})\b', clean)
    if slash_match:
        m = int(slash_match.group(1))
        y = int(slash_match.group(2))
        if 1 <= m <= 12:
            return y * 12 + m

    # 2. Multi-month: "July-Sep 2024" (End month consider karein)
    multi_match = re.search(r'([a-z]+)[-\s]+([a-z]+)\s*(\d{4})', clean)
    if multi_match and multi_match.group(2) in MONTH_MAP:
        m = MONTH_MAP[multi_match.group(2)]
        y = int(multi_match.group(3))
        return y * 12 + m

    # 3. Words + Year: "Jun 2025", "August 2023"
    m_match = re.search(r'([a-z]+)\s*(\d{4})', clean)
    if m_match and m_match.group(1) in MONTH_MAP:
        m = MONTH_MAP[m_match.group(1)]
        y = int(m_match.group(2))
        return y * 12 + m

    # 4. Pure Year: "2024", "2026"
    y_match = re.search(r'\b(20\d{2}|19\d{2})\b', clean)
    if y_match:
        y = int(y_match.group(1))
        return y * 12 + 6  # Mid-year estimate

    return current_index


def extract_college_graduation_end_month(text: str) -> int:
    """
    Education section se dekhta hai ki candidate ka college kab khatam hua / hoga.
    Jaise Sapan: 05/2024, Banala: 2026.
    """
    edu_match = re.search(
        r'EDUCATION\s*[:\n\r]+([\s\S]+?)(?=(?:WORK\s+EXPERIENCE|PROFESSIONAL\s+EXPERIENCE|EMPLOYMENT\s+HISTORY|INTERNSHIPS?|EXPERIENCE|PROJECTS|SKILLS|CERTIFICATIONS|$))',
        text,
        re.IGNORECASE
    )
    edu_text = edu_match.group(1) if edu_match else text
    
    # Education section se dates/years nikaalein
    dates_found = re.findall(r'(?:\d{1,2}[\/\-])?\d{4}|present|current|continuing', edu_text, re.IGNORECASE)
    latest_month_idx = 0
    for d in dates_found:
        idx = parse_date_token_to_month_index(d)
        if idx > latest_month_idx:
            latest_month_idx = idx
            
    return latest_month_idx


def evaluate_experience(text: str, role_exp_criteria: dict, candidate_exp_status: str = "") -> dict:
    """
    Smart Experience & Career Gap Evaluator:
    - Universal Date Formats (02/2024, Jun 2024, 2024) support karta hai.
    - College Shield: College study ke dauran huye gap ko ZERO penalty deta hai.
    """
    max_score = role_exp_criteria.get("max_score", 5)
    now = datetime.now()
    now_idx = now.year * 12 + now.month

    # 1. College Graduation End Date pata karein
    college_end_idx = extract_college_graduation_end_month(text)
    is_currently_enrolled = (college_end_idx >= now_idx)  # College chal raha hai (e.g. 2026 passout)

    # 2. Experience & INTERNSHIPS sections isolate karein
    exp_section_match = re.search(
        r'(?:WORK\s+EXPERIENCE|PROFESSIONAL\s+EXPERIENCE|EMPLOYMENT\s+HISTORY|INTERNSHIPS?|EXPERIENCE)\s*[:\n\r]+([\s\S]+?)(?=(?:PROJECTS|EDUCATION|TECHNICAL\s+SKILLS|SKILLS|CERTIFICATIONS|ACHIEVEMENTS|AWARDS|LANGUAGES|DECLARATION|$))',
        text,
        re.IGNORECASE
    )

    # Agar Experience/Internship section nahi mila
    if not exp_section_match:
        has_internship = bool(re.search(r'\b(intern|internship|trainee)\b', text, re.IGNORECASE))
        if is_currently_enrolled or has_internship or candidate_exp_status.lower() == "fresher":
            return {
                "score": max_score,
                "maxScore": max_score,
                "hasGap": False,
                "maxGapMonths": 0,
                "detectedGaps": [],
                "status": "No Career Gap (Fresher / Student)",
                "message": "Student/Fresher candidate with continuous learning."
            }
        else:
            return {
                "score": 1,
                "maxScore": max_score,
                "hasGap": True,
                "maxGapMonths": 0,
                "detectedGaps": [],
                "status": "No Verifiable Experience",
                "message": "No work experience or internship section found."
            }

    exp_text = exp_section_match.group(1)

    # 3. Universal Date Range Pattern (Supports: 02/2024 - 04/2024, Jun 2024 - Aug 2025, 2021 - 2024)
    token_rx = r'(?:(?:\d{1,2}[\/\-])?(?:[a-zA-Z]+(?:-[a-zA-Z]+)?\s*)?\d{4}|present|current|continuing|continue)'
    date_range_pattern = rf'({token_rx})\s*[-–to~]+\s*({token_rx})'
    ranges = re.findall(date_range_pattern, exp_text, re.IGNORECASE)

    intervals = []
    for start_str, end_str in ranges:
        start_idx = parse_date_token_to_month_index(start_str)
        end_idx = parse_date_token_to_month_index(end_str)
        if start_idx <= end_idx:
            intervals.append((start_idx, end_idx, start_str.strip(), end_str.strip()))

    intervals.sort(key=lambda x: x[0])

    # 4. Gaps Calculate karein (College Shield ke sath)
    detected_gaps = []
    max_gap_months = 0

    if len(intervals) > 1:
        for i in range(1, len(intervals)):
            prev_end = intervals[i-1][1]
            curr_start = intervals[i][0]
            gap = curr_start - prev_end
            
            # Agar gap 3 mahine se zyada hai
            if gap > 3:
                # 🎓 COLLEGE SHIELD CHECK:
                # Kya yeh gap college chalte waqt aaya tha?
                was_during_college = (college_end_idx > 0 and curr_start <= college_end_idx)
                
                if was_during_college:
                    # College study time tha -> ZERO PENALTY!
                    continue
                else:
                    detected_gaps.append({
                        "from": intervals[i-1][3],
                        "to": intervals[i][2],
                        "gapMonths": gap,
                        "type": "Post-Graduation Career Gap"
                    })
                    if gap > max_gap_months:
                        max_gap_months = gap

    # 5. Score Calculation
    gap_rules = role_exp_criteria.get("gap_rules", [])

    if len(detected_gaps) == 0:
        score = max_score
        status_label = "No Career Gap Detected (Continuous)"
        message = "Candidate maintains consistent career continuity (College study gaps protected)."
    else:
        matched_rule = None
        for rule in gap_rules:
            if rule["min_months"] < max_gap_months <= rule["max_months"]:
                matched_rule = rule
                break
        if matched_rule:
            score = matched_rule["score"]
            status_label = matched_rule["status"]
        else:
            score = 1
            status_label = "Significant Career Gap"
        message = f"Career gap of ~{max_gap_months} months detected between roles."

    return {
        "score": score,
        "maxScore": max_score,
        "hasGap": len(detected_gaps) > 0,
        "maxGapMonths": max_gap_months,
        "detectedGaps": detected_gaps,
        "status": status_label,
        "message": message
    }

def evaluate_projects(text: str, role_projects_criteria: dict, is_fresher: bool = True) -> dict:
    """
    Projects evaluate karta hai (Out of 5).
    Adaptive Rule:
    - Fresher: >= 1 relevant project = 5/5
    - Experienced: >= 2 relevant projects = 5/5, 1 project = 3/5
    """
    max_score = role_projects_criteria.get("max_score", 5)
    relevant_keywords = role_projects_criteria.get("relevant_keywords", [])

    # 1. Projects Section isolate karein
    proj_match = re.search(
        r'(?:PROJECTS|PERSONAL\s+PROJECTS|KEY\s+PROJECTS|ACADEMIC\s+PROJECTS|TECHNICAL\s+PROJECTS)\s*[:\n\r]+([\s\S]+?)(?=(?:WORK\s+EXPERIENCE|PROFESSIONAL\s+EXPERIENCE|EMPLOYMENT\s+HISTORY|INTERNSHIPS?|EXPERIENCE|EDUCATION|TECHNICAL\s+SKILLS|SKILLS|CERTIFICATIONS|ACHIEVEMENTS|AWARDS|LANGUAGES|DECLARATION|$))',
        text,
        re.IGNORECASE
    )

    proj_text = proj_match.group(1).strip() if proj_match else ""

    if not proj_text:
        return {
            "score": 0,
            "maxScore": max_score,
            "totalProjectsFound": 0,
            "relevantProjectsCount": 0,
            "matchedProjects": [],
            "status": "No Projects Found",
            "message": "No project section found in resume."
        }

    # 2. Individual Projects me split karein (bullet points '•' ya double newline se)
    raw_projects = re.split(r'\n\s*[•\-\*]\s*', '\n' + proj_text)
    raw_projects = [p.strip() for p in raw_projects if len(p.strip()) > 15]

    matched_projects = []
    other_projects = []

    for p in raw_projects:
        # Pehli line title hoti hai
        title_line = p.splitlines()[0].strip()
        
        # Check karein kya is project me role ke keywords use huye hain
        matched_kws = [kw for kw in relevant_keywords if re.search(r'(?<!\w)' + re.escape(kw) + r'(?!\w)', p, re.IGNORECASE)]
        
        if matched_kws:
            matched_projects.append({
                "title": title_line,
                "matchedTechnologies": list(dict.fromkeys(matched_kws))[:5]
            })
        else:
            other_projects.append({
                "title": title_line
            })

    relevant_count = len(matched_projects)
    total_count = len(raw_projects)

    # 3. Adaptive Scoring Logic (Fresher vs Experienced)
    if is_fresher:
        if relevant_count >= 1:
            score = max_score
            status_label = "Matched (Fresher: 1+ Relevant Project)"
            message = f"Fresher candidate has {relevant_count} relevant project(s) matching the required stack."
        elif total_count > 0:
            score = 2
            status_label = "Partial (Projects in Other Tech)"
            message = "Candidate has projects, but they are not in the primary required tech stack."
        else:
            score = 0
            status_label = "No Projects Found"
            message = "No relevant projects found."
    else:
        if relevant_count >= 2:
            score = max_score
            status_label = "Matched (Experienced: 2+ Relevant Projects)"
            message = f"Experienced candidate has {relevant_count} relevant projects matching the required stack."
        elif relevant_count == 1:
            score = 3
            status_label = "Moderate (Experienced: 1 Relevant Project)"
            message = "Candidate has 1 relevant project; minimum 2 expected for experienced candidates."
        elif total_count > 0:
            score = 1.5
            status_label = "Partial (Projects in Other Tech)"
            message = "Candidate has projects, but they are not in the primary required tech stack."
        else:
            score = 0
            status_label = "No Projects Found"
            message = "No relevant projects found."

    return {
        "score": score,
        "maxScore": max_score,
        "isFresherRuleApplied": is_fresher,
        "totalProjectsFound": total_count,
        "relevantProjectsCount": relevant_count,
        "matchedProjects": matched_projects,
        "status": status_label,
        "message": message
    }

def evaluate_certifications_and_achievements(text: str, role_cert_criteria: dict) -> dict:
    """
    Certifications, Awards aur Achievements evaluate karta hai (Out of 5).
    Multi-section support:
    - CERTIFICATIONS / LICENSES / COURSES
    - ACHIEVEMENTS / HONORS & AWARDS / AWARDS
    """
    max_score = role_cert_criteria.get("max_score", 5)
    reputed_issuers = role_cert_criteria.get("reputed_issuers", [])
    achievement_keywords = role_cert_criteria.get("achievement_keywords", [])

    # 1. Certifications & Achievements ke saare sections extract karein
    section_pattern = (
        r'(?:CERTIFICATIONS?|CERTIFICATES?|LICENSES?\s*(?:&|AND)?\s*CERTIFICATIONS?|'
        r'CERTIFICATION\s+COURSES?|ONLINE\s+COURSES?|TRAININGS?\s*(?:&|AND)?\s*CERTIFICATIONS?|'
        r'ACHIEVEMENTS?|KEY\s+ACHIEVEMENTS?|HONORS?\s*(?:&|AND)?\s*AWARDS?|'
        r'AWARDS?\s*(?:&|AND)?\s*(?:RECOGNITIONS?|ACHIEVEMENTS?|CERTIFICATES?)|'
        r'AWARDS?|ACADEMIC\s+ACHIEVEMENTS?)\s*[:\n\r]+'
        r'([\s\S]+?)'
        r'(?=(?:WORK\s+EXPERIENCE|PROFESSIONAL\s+EXPERIENCE|EMPLOYMENT\s+HISTORY|INTERNSHIPS?|'
        r'EXPERIENCE|EDUCATION|PROJECTS|TECHNICAL\s+SKILLS|SKILLS|LANGUAGES|DECLARATION|HOBBIES|$))'
    )

    matches = list(re.finditer(section_pattern, text, re.IGNORECASE))
    combined_text = "\n".join([m.group(1).strip() for m in matches])

    # 2. Individual items me split karein
    raw_items = re.split(r'\n\s*[•\-\*●\?]\s*|\n\n+', '\n' + combined_text)
    raw_items = [item.strip() for item in raw_items if len(item.strip()) > 8]

    # Global search fallback agar sections me direct na mile
    if not raw_items:
        for line in text.splitlines():
            l = line.strip()
            if len(l) > 15 and any(k in l.lower() for k in ["hackathon", "certified", "winner", "ieee", "coursera"]):
                raw_items.append(l)

    matched_certifications = []
    matched_achievements = []

    for item in raw_items:
        clean_title = re.sub(r'^[•\-\*●\?\s]+', '', item).splitlines()[0].strip()[:100]
        matched_issuers = [iss for iss in reputed_issuers if re.search(r'(?<!\w)' + re.escape(iss) + r'(?!\w)', item, re.IGNORECASE)]
        matched_achs = [ach for ach in achievement_keywords if re.search(r'(?<!\w)' + re.escape(ach) + r'(?!\w)', item, re.IGNORECASE)]

        if matched_achs:
            matched_achievements.append({
                "title": clean_title,
                "matchedKeywords": list(dict.fromkeys(matched_achs))
            })
        elif matched_issuers:
            matched_certifications.append({
                "title": clean_title,
                "matchedIssuer": matched_issuers[0].title()
            })

    total_valid_items = len(matched_certifications) + len(matched_achievements)

    # 3. Dynamic Scoring Logic (0 / 5 Marks)
    has_high_impact = any(
        any(k in ach["matchedKeywords"] for k in ["winner", "1st place", "2nd place", "second place", "research paper", "ieee", "patent"])
        for ach in matched_achievements
    ) or any(
        c["matchedIssuer"].lower() in ["aws", "azure", "google cloud", "gcp", "deeplearning.ai", "oracle", "nvidia", "coursera", "ibm", "microsoft"]
        for c in matched_certifications
    )

    # 3. Dynamic Scoring Logic (0 to 2 Marks)
    if has_high_impact or total_valid_items >= 2:
        score = 2.0
        status_label = "Strong Profile (High Impact / Multiple Items)"
        message = f"Found {len(matched_certifications)} certification(s) and {len(matched_achievements)} achievement(s)."
    elif total_valid_items == 1:
        score = 1.5
        status_label = "Good Profile (1 Verified Item)"
        message = "Candidate holds 1 verified technical certification or achievement."
    elif len(raw_items) > 0:
        score = 1.0
        status_label = "Basic (General Participation)"
        message = "General participation or unverified items mentioned."
    else:
        score = 0
        status_label = "No Certifications or Achievements Found"
        message = "No relevant certifications or achievements detected."

    return {
        "score": score,
        "maxScore": max_score,
        "totalItemsFound": total_valid_items,
        "matchedCertifications": matched_certifications,
        "matchedAchievements": matched_achievements,
        "status": status_label,
        "message": message
    }

# ==========================================
# 📍 LOCATION EVALUATOR (Max 3 Marks)
# ==========================================

def evaluate_location(text: str, role_location_criteria: dict) -> dict:
    """
    Candidate ki residential location scan karta hai:
    - Surat -> 3 Marks
    - Ahmedabad / Gandhinagar / Vadodara -> 2 Marks
    - Other / Not Found -> 0 Marks
    """
    max_score = role_location_criteria.get("max_score", 3)
    tier_1 = role_location_criteria.get("tier_1", {"keywords": ["surat"], "score": 3, "name": "Surat (Local)"})
    tier_2 = role_location_criteria.get("tier_2", {"keywords": ["ahmedabad", "gandhinagar", "vadodara", "baroda"], "score": 2, "name": "Ahmedabad / Gandhinagar / Vadodara"})

    # 1. Target Text zone: Top 15 lines (Header) + Address label scan
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    header_text = "\n".join(lines[:15])

    address_match = re.search(
        r'(?:address|current\s+location|residential\s+address|location)\s*[:\-\–]\s*([^\n\r]+)',
        text,
        re.IGNORECASE
    )
    address_snippet = address_match.group(1) if address_match else ""

    search_pool = f"{header_text}\n{address_snippet}".lower()

    # 2. Check Tier 1 (Surat) -> 3 Marks
    for kw in tier_1.get("keywords", []):
        pattern = r"(?<!\w)" + re.escape(kw) + r"(?!\w)"
        if re.search(pattern, search_pool, re.IGNORECASE):
            return {
                "score": tier_1.get("score", 3),
                "maxScore": max_score,
                "detectedCity": kw.title(),
                "tier": tier_1.get("name"),
                "status": "Matched (Local)",
                "note": f"Candidate is from {kw.title()} (Preferred Local Candidate)."
            }

    # 3. Check Tier 2 (Ahmedabad / Gandhinagar / Vadodara) -> 2 Marks
    for kw in tier_2.get("keywords", []):
        pattern = r"(?<!\w)" + re.escape(kw) + r"(?!\w)"
        if re.search(pattern, search_pool, re.IGNORECASE):
            return {
                "score": tier_2.get("score", 2),
                "maxScore": max_score,
                "detectedCity": kw.title(),
                "tier": tier_2.get("name"),
                "status": "Matched (Preferred Region)",
                "note": f"Candidate is from {kw.title()} (Regional Candidate)."
            }

    # 4. Fallback: Other / Not Mentioned -> 0 Marks
    return {
        "score": 0,
        "maxScore": max_score,
        "detectedCity": None,
        "tier": "Other / Not Mentioned",
        "status": "Not Matched",
        "note": "Candidate location is outside preferred cities or not specified in header."
    }

def evaluate_candidate_resume(position: str, resume_text: str, candidate_exp_status: str = "") -> dict:
    """
    Main evaluation function: Strict role matching karta hai.
    """
    all_criteria = load_criteria()
    clean_position = (position or "").strip()
    
    matched_role = None
    for role_name in all_criteria.keys():
        if role_name.lower() == clean_position.lower() or \
           role_name.lower() in clean_position.lower() or \
           clean_position.lower() in role_name.lower():
            if all_criteria[role_name].get("tech_stack", {}).get("core_skills"):
                matched_role = role_name
                break

    if not matched_role:
        return {
            "matchedRole": "Not Configured",
            "totalScore": 0,
            "maxTotalScore": 50,
            "message": f"Evaluation criteria for position '{clean_position}' is not configured yet.",
            "breakdown": {
                "techStack": {"score": 0, "maxScore": 20, "status": "Not Configured"},
                "education": {"score": 0, "maxScore": 15, "status": "Not Configured"},
                "experience": {"score": 0, "maxScore": 5, "status": "Not Configured"},
                "projects": {"score": 0, "maxScore": 5, "status": "Not Configured"},
                "certifications": {"score": 0, "maxScore": 5, "status": "Not Configured"}
            }
        }

    role_rules = all_criteria[matched_role]
    
    # 1. Tech Stack Evaluation (Out of 20)
    tech_eval = evaluate_tech_stack(resume_text, role_rules.get("tech_stack", {}))
    
    # 2. Education Evaluation (Out of 15)
    education_eval = evaluate_education(resume_text, role_rules.get("education", {}))

    # 3. Experience & Career Gap Evaluation (Out of 5)
    experience_eval = evaluate_experience(resume_text, role_rules.get("experience", {}), candidate_exp_status)

    # 4. Projects Evaluation (Out of 5)
    now = datetime.now()
    now_idx = now.year * 12 + now.month
    college_end_idx = extract_college_graduation_end_month(resume_text)
    is_fresher = (
        candidate_exp_status.lower() == "fresher" or 
        "0." in candidate_exp_status or 
        college_end_idx >= now_idx
    )
    projects_eval = evaluate_projects(resume_text, role_rules.get("projects", {}), is_fresher)

    # 5. Certifications (Out of 2)
    certifications_eval = evaluate_certifications_and_achievements(
        resume_text,
        role_rules.get("certifications", {})
    )

    # 6. ✨ NEW: Location Evaluation (Out of 3)
    location_eval = evaluate_location(
        resume_text,
        role_rules.get("location", {})
    )

    # Total Score: 20 + 15 + 5 + 5 + 2 + 3 = 50 Marks
    current_total_score = (
        tech_eval["score"] + 
        education_eval["score"] + 
        experience_eval["score"] + 
        projects_eval["score"] + 
        certifications_eval["score"] +
        location_eval["score"]
    )

    return {
        "matchedRole": matched_role,
        "totalScore": current_total_score,
        "maxTotalScore": 50,
        "message": "Candidate resume evaluated successfully",
        "breakdown": {
            "techStack": tech_eval,
            "education": education_eval,
            "experience": experience_eval,
            "projects": projects_eval,
            "certifications": certifications_eval,
            "location": location_eval
        }
    }
