# # CI/CD Pipeline Active

# from fastapi import FastAPI, File, UploadFile
# from services.candidate_service import fetch_candidate_from_nodejs
# from services.extractor_service import get_candidate_and_extract_resume_data, extract_text_from_resume_url
# from services.scoring_engine import evaluate_candidate_resume
# from services.resume_parser import parse_uploaded_resume_file
# from fastapi import FastAPI, HTTPException, status, File, UploadFile, Body
# from typing import Dict, Any


# app = FastAPI(
#     title="HRMS AI Resume Screening API",
#     description="Python Sidecar Service to fetch, evaluate and parse candidate resumes",
#     version="1.0.0"
# )

# # 1. Candidate Details API
# @app.get("/candidate/{application_id}")
# def get_candidate(application_id: str):
#     """The Node.js backend fetches candidate details."""
#     return fetch_candidate_from_nodejs(application_id)


# # 2. Extract Resume API
# @app.get("/candidate/{application_id}/extract-resume")
# def extract_resume(application_id: str):
#     """Extracts text from the resume URL (PDF & DOCX)."""
#     return get_candidate_and_extract_resume_data(application_id)


# # 3. Candidate Evaluation & 50-Marks Scoring API
# @app.get("/candidate/{application_id}/evaluate")
# def evaluate_candidate(application_id: str):
#     """Evaluates the candidate in detail based on a 50-mark criterion."""
#     raw_response = fetch_candidate_from_nodejs(application_id)
#     candidate_data = raw_response.get("data") or {}
    
#     extracted_data = get_candidate_and_extract_resume_data(application_id)
#     resume_text = extracted_data.get("resume", {}).get("rawExtractedText", "")
    
#     position = candidate_data.get("position") or "AI-ML Engineer"
#     candidate_exp = candidate_data.get("experience") or ""
    
#     evaluation_result = evaluate_candidate_resume(position, resume_text, candidate_exp)
    
#     return {
#         "success": True,
#         "applicationId": candidate_data.get("applicationId"),
#         "candidateName": candidate_data.get("name"),
#         "appliedPosition": position,
#         "matchedRoleCriteria": evaluation_result["matchedRole"],
#         "totalScore": evaluation_result["totalScore"],
#         "maxTotalScore": evaluation_result["maxTotalScore"],
#         "breakdown": evaluation_result["breakdown"],
#         "message": evaluation_result["message"]
#     }


# # 4. Direct Upload & Resume Parsing API
# @app.post("/parse-resume")
# async def parse_resume(file: UploadFile = File(...)):
#     """Uploads PDF, DOC, and DOCX files and parses Name, Email, Phone, Role, and Experience."""
#     content = await file.read()
#     return parse_uploaded_resume_file(content, file.filename)

# # ==============================================================================
# # ✨ NEW API: Direct JSON Payload Candidate Evaluation (Stage 1 Bypassed)
# # ==============================================================================
# @app.post("/candidate/evaluate")
# def evaluate_candidate_from_payload(payload: Dict[str, Any] = Body(...)):
#     """
#     Direct Candidate Evaluation API:
#     - Evaluates candidates directly using a JSON payload without calling the Node.js backend.
#     - Supports both Cloudinary URLs (https://) and Local Storage URLs (/api/files/...).
#     """
#     # 1. Unpack candidate data (chahe direct ho ya {"data": {...}} me wrapped ho)
#     candidate_data = payload.get("data") if "data" in payload and isinstance(payload.get("data"), dict) else payload
    
#     position = candidate_data.get("position") or "AI-ML Engineer"
#     candidate_exp = candidate_data.get("experience") or ""
#     app_id = candidate_data.get("applicationId") or candidate_data.get("_id") or "DIRECT_EVAL"
#     candidate_name = candidate_data.get("name") or candidate_data.get("candidateName") or "Candidate"
    
#     # 2. Resume URL / Text nikaalein
#     resume_text = candidate_data.get("resumeText") or candidate_data.get("rawExtractedText") or ""
    
#     # Agar direct resumeText nahi diya hai, toh fileUrl se extract karein (Stage 2)
#     if not resume_text:
#         resume_info = candidate_data.get("resume") or {}
#         resume_url = resume_info.get("resumeDisplayUrl") or resume_info.get("fileUrl") or candidate_data.get("fileUrl")
#         file_name = resume_info.get("fileName") or "resume.pdf"
        
#         if not resume_url:
#             raise HTTPException(
#                 status_code=400,
#                 detail="Payload me 'resume.fileUrl' ya 'resumeText' provide karna zaroori hai."
#             )
        
#         # 🚀 Stage 2: Resume text extract karein
#         extracted_data = extract_text_from_resume_url(resume_url, file_name)
#         resume_text = extracted_data.get("fullText", "")
    
#     if not resume_text.strip():
#         raise HTTPException(
#             status_code=422,
#             detail="Resume se readable text extract nahi ho paya."
#         )

#     # 3. 🎯 Stage 3 & 4: Scoring Engine Run karein (50 Marks)
#     evaluation_result = evaluate_candidate_resume(position, resume_text, candidate_exp)
    
#     # 4. Standard Response Return karein
#     return {
#         "success": True,
#         "applicationId": app_id,
#         "candidateName": candidate_name,
#         "appliedPosition": position,
#         "matchedRoleCriteria": evaluation_result["matchedRole"],
#         "totalScore": evaluation_result["totalScore"],
#         "maxTotalScore": evaluation_result["maxTotalScore"],
#         "breakdown": evaluation_result["breakdown"],
#         "message": evaluation_result["message"]
#     }


# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
# CI/CD Pipeline Active

from fastapi import FastAPI, HTTPException, status, File, UploadFile, Body
from typing import Dict, Any
from services.candidate_service import fetch_candidate_from_nodejs
from services.extractor_service import get_candidate_and_extract_resume_data, extract_text_from_resume_url
from services.scoring_engine import evaluate_candidate_resume
from services.resume_parser import parse_uploaded_resume_file
import uvicorn

# 1. AI Application definition
ai_app = FastAPI(
    title="HRMS AI Resume Screening API",
    description="Python Sidecar Service to fetch, evaluate and parse candidate resumes",
    version="1.0.0"
)

# 1. Candidate Details API
@ai_app.get("/candidate/{application_id}")
def get_candidate(application_id: str):
    """The Node.js backend fetches candidate details."""
    return fetch_candidate_from_nodejs(application_id)


# 2. Extract Resume API
@ai_app.get("/candidate/{application_id}/extract-resume")
def extract_resume(application_id: str):
    """Extracts text from the resume URL (PDF & DOCX)."""
    return get_candidate_and_extract_resume_data(application_id)


# 3. Candidate Evaluation & 50-Marks Scoring API
@ai_app.get("/candidate/{application_id}/evaluate")
def evaluate_candidate(application_id: str):
    """Evaluates the candidate in detail based on a 50-mark criterion."""
    raw_response = fetch_candidate_from_nodejs(application_id)
    candidate_data = raw_response.get("data") or {}
    
    extracted_data = get_candidate_and_extract_resume_data(application_id)
    resume_text = extracted_data.get("resume", {}).get("rawExtractedText", "")
    
    position = candidate_data.get("position") or "AI-ML Engineer"
    candidate_exp = candidate_data.get("experience") or ""
    
    evaluation_result = evaluate_candidate_resume(position, resume_text, candidate_exp)
    
    return {
        "success": True,
        "applicationId": candidate_data.get("applicationId"),
        "candidateName": candidate_data.get("name"),
        "appliedPosition": position,
        "matchedRoleCriteria": evaluation_result["matchedRole"],
        "totalScore": evaluation_result["totalScore"],
        "maxTotalScore": evaluation_result["maxTotalScore"],
        "breakdown": evaluation_result["breakdown"],
        "message": evaluation_result["message"]
    }


# 4. Direct Upload & Resume Parsing API
@ai_app.post("/parse-resume")
async def parse_resume(file: UploadFile = File(...)):
    """Uploads PDF, DOC, and DOCX files and parses Name, Email, Phone, Role, and Experience."""
    content = await file.read()
    return parse_uploaded_resume_file(content, file.filename)


# ==============================================================================
# 5. Direct JSON Payload Candidate Evaluation (Stage 1 Bypassed)
# ==============================================================================
@ai_app.post("/candidate/evaluate")
def evaluate_candidate_from_payload(payload: Dict[str, Any] = Body(...)):
    """
    Direct Candidate Evaluation API:
    - Evaluates candidates directly using a JSON payload without calling the Node.js backend.
    - Supports both Cloudinary URLs (https://) and Local Storage URLs (/api/files/...).
    """
    candidate_data = payload.get("data") if "data" in payload and isinstance(payload.get("data"), dict) else payload
    
    position = candidate_data.get("position") or "AI-ML Engineer"
    candidate_exp = candidate_data.get("experience") or ""
    app_id = candidate_data.get("applicationId") or candidate_data.get("_id") or "DIRECT_EVAL"
    candidate_name = candidate_data.get("name") or candidate_data.get("candidateName") or "Candidate"
    
    resume_text = candidate_data.get("resumeText") or candidate_data.get("rawExtractedText") or ""
    
    if not resume_text:
        resume_info = candidate_data.get("resume") or {}
        resume_url = resume_info.get("resumeDisplayUrl") or resume_info.get("fileUrl") or candidate_data.get("fileUrl")
        file_name = resume_info.get("fileName") or "resume.pdf"
        
        if not resume_url:
            raise HTTPException(
                status_code=400,
                detail="Payload me 'resume.fileUrl' ya 'resumeText' provide karna zaroori hai."
            )
        
        extracted_data = extract_text_from_resume_url(resume_url, file_name)
        resume_text = extracted_data.get("fullText", "")
    
    if not resume_text.strip():
        raise HTTPException(
            status_code=422,
            detail="Resume se readable text extract nahi ho paya."
        )

    evaluation_result = evaluate_candidate_resume(position, resume_text, candidate_exp)
    
    return {
        "success": True,
        "applicationId": app_id,
        "candidateName": candidate_name,
        "appliedPosition": position,
        "matchedRoleCriteria": evaluation_result["matchedRole"],
        "totalScore": evaluation_result["totalScore"],
        "maxTotalScore": evaluation_result["maxTotalScore"],
        "breakdown": evaluation_result["breakdown"],
        "message": evaluation_result["message"]
    }


# ==============================================================================
# Main Mount: Har URL ko /api/ai ke sath chalayega
# ==============================================================================
app = FastAPI(docs_url=None, redoc_url=None)
app.mount("/api/ai", ai_app)


if __name__ == "__main__":
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
