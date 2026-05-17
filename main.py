from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import base64
import os
import httpx

app = FastAPI()

origins = [
    "http://localhost:3000",
    "https://sujal-os-frontend.vercel.app", 
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class EmailRequest(BaseModel):
    sender_email: str
    app_password: str  # We will use this field to pass your Resend API Key (re_...) from the frontend
    receiver_email: str
    receiver_name: str
    subject: str
    body: str
    resume_status: str  
    custom_resume_data: Optional[str] = None  
    custom_resume_name: Optional[str] = None  

@app.post("/send-email")
async def send_email(request: EmailRequest):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    default_filename = "Sujal_Koli_Latest_Resume.pdf"
    default_resume_path = os.path.join(current_dir, default_filename)

    # Prepare list for attachments
    attachments = []

    try:
        final_body = request.body.replace("{{name}}", request.receiver_name or "Hiring Manager")

        # 1. Process Attachments based on Matrix Routing
        if request.resume_status == "default":
            if not os.path.exists(default_resume_path):
                raise HTTPException(
                    status_code=404, 
                    detail=f"Base Document Profile Missing: '{default_filename}' not found on server filesystem."
                )
            with open(default_resume_path, "rb") as attachment:
                encoded_content = base64.b64encode(attachment.read()).decode("utf-8")
                attachments.append({
                    "content": encoded_content,
                    "filename": default_filename
                })

        elif request.resume_status == "custom":
            if not request.custom_resume_data:
                raise HTTPException(
                    status_code=400, 
                    detail="Data Corruption: Custom attachment requested but content data stream parameter is null."
                )
            attachments.append({
                "content": request.custom_resume_data,
                "filename": request.custom_resume_name or "Uploaded_Resume.pdf"
            })

        # 2. Build Resend API Request Payload
        # Resend Free Tier uses onboarding@resend.dev unless you verify a domain
        from_email = "onboarding@resend.dev" if "re_" in request.app_password else request.sender_email

        payload = {
            "from": f"Sujal Koli <{from_email}>",
            "to": [request.receiver_email],
            "subject": request.subject,
            "text": final_body,
        }

        if attachments:
            payload["attachments"] = attachments

        # 3. Deliver via HTTP POST (Bypasses all Render network bans!)
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.resend.com/emails",
                json=payload,
                headers={
                    "Authorization": f"Bearer {request.app_password}",
                    "Content-Type": "application/json"
                },
                timeout=15.0
            )
            
        if response.status_code not in [200, 201]:
            error_data = response.json()
            raise HTTPException(
                status_code=response.status_code, 
                detail=error_data.get("message", "Failed to send email via HTTP gateway.")
            )

        return {"status": "success", "message": f"Mission accomplished. Email successfully sent to {request.receiver_email}"}

    except HTTPException as http_ex:
        raise http_ex
    except Exception as e:
        print(f"ERROR: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)