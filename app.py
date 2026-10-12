from fastapi import FastAPI, File, UploadFile
from services.candidate_service import fetch_candidate_from_nodejs
from services.extractor_service import get_candidate_and_extract_resume_data
from services.scoring_engine import evaluate_candidate_resume
from services.resume_parser import parse_uploaded_resume_file

app = FastAPI(
    title="HRMS AI Resume Screening API",
    description="Python Sidecar Service to fetch, evaluate and parse candidate resumes",
    version="1.0.0"
)

# 1. Candidate Details API
@app.get("/candidate/{application_id}")
def get_candidate(application_id: str):
    """The Node.js backend fetches candidate details."""
    return fetch_candidate_from_nodejs(application_id)


# 2. Extract Resume API
@app.get("/candidate/{application_id}/extract-resume")
def extract_resume(application_id: str):
    """Extracts text from the resume URL (PDF & DOCX)."""
    return get_candidate_and_extract_resume_data(application_id)


# 3. Candidate Evaluation & 50-Marks Scoring API
@app.get("/candidate/{application_id}/evaluate")
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
@app.post("/parse-resume")
async def parse_resume(file: UploadFile = File(...)):
    """Uploads PDF, DOC, and DOCX files and parses Name, Email, Phone, Role, and Experience."""
    content = await file.read()
    return parse_uploaded_resume_file(content, file.filename)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
