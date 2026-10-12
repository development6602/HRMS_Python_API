import os
import requests
from fastapi import HTTPException, status
from dotenv import load_dotenv

load_dotenv()

HRMS_BASE_URL = os.getenv("HRMS_BASE_URL", "http://localhost:5000/api")
HRMS_AUTH_TOKEN = os.getenv("HRMS_AUTH_TOKEN", "")

def fetch_candidate_from_nodejs(application_id: str) -> dict:
    """
    Node.js backend se candidate ka complete data fetch karta hai.
    """
    url = f"{HRMS_BASE_URL}/job-applications/{application_id}"
    headers = {"Content-Type": "application/json"}
    
    if HRMS_AUTH_TOKEN:
        headers["Authorization"] = f"Bearer {HRMS_AUTH_TOKEN}"
        
    try:
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 404:
            raise HTTPException(status_code=404, detail="Candidate not found in Node.js HRMS")
        elif response.status_code == 401:
            raise HTTPException(status_code=401, detail="Invalid or expired HRMS_AUTH_TOKEN")
        elif response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code, 
                detail=f"Node.js API Error: {response.text}"
            )
            
        return response.json()
        
    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to connect to Node.js backend: {str(e)}"
        )
