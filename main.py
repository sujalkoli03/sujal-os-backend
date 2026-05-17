from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import base64
import os

app = FastAPI()

# FIXED: Explicitly allow your live Vercel frontend domain alongside localhost
# Replace the placeholder URL with your exact Vercel deployment URL
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
    app_password: str
    receiver_email: str
    receiver_name: str
    subject: str
    body: str
    resume_status: str  
    custom_resume_data: Optional[str] = None  
    custom_resume_name: Optional[str] = None  

@app.post("/send-email")
async def send_email(request: EmailRequest):
    # FIXED: Cleaned up relative path handling for hosting environments like Render
    current_dir = os.path.dirname(os.path.abspath(__file__))
    default_filename = "Sujal_Koli_Latest_Resume.pdf"
    default_resume_path = os.path.join(current_dir, default_filename)

    try:
        # 1. Setup Email Structural Base
        message = MIMEMultipart()
        message["From"] = request.sender_email
        message["To"] = request.receiver_email
        message["Subject"] = request.subject
        
        final_body = request.body.replace("{{name}}", request.receiver_name or "Hiring Manager")
        message.attach(MIMEText(final_body, "plain"))

        # 2. Dynamic Attachment Routing Logic Matrix
        if request.resume_status == "default":
            print(f"DEBUG: Mapping Default Attachment Route: {default_resume_path}")
            if not os.path.exists(default_resume_path):
                raise HTTPException(
                    status_code=404, 
                    detail=f"Base Document Profile Missing: '{default_filename}' not found on server filesystem."
                )
            
            with open(default_resume_path, "rb") as attachment:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(attachment.read())
                encoders.encode_base64(part)
                part.add_header("Content-Disposition", f"attachment; filename={default_filename}")
                message.attach(part)

        elif request.resume_status == "custom":
            print("DEBUG: Processing incoming custom base64 file data buffer...")
            if not request.custom_resume_data:
                raise HTTPException(
                    status_code=400, 
                    detail="Data Corruption: Custom attachment requested but content data stream parameter is null."
                )
            
            try:
                raw_pdf_bytes = base64.b64decode(request.custom_resume_data)
            except Exception:
                raise HTTPException(
                    status_code=400,
                    detail="Stream Error: Content data field failed to parse back into base64 binary formatting."
                )

            attachment_name = request.custom_resume_name or "Uploaded_Resume.pdf"
            part = MIMEBase("application", "octet-stream")
            part.set_payload(raw_pdf_bytes)
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", f"attachment; filename={attachment_name}")
            message.attach(part)

        elif request.resume_status == "none":
            print("DEBUG: Operating in raw text pipeline execution mode. No document attached.")

        else:
            raise HTTPException(
                status_code=400, 
                detail="Routing Error: Incompatible resume status type parameter submitted."
            )

        # 3. SMTP Gateway Core Connection Execution
        print(f"DEBUG: Connecting to SMTP server matrix for {request.sender_email}...")
        
        # FIXED: Added an explicit 15-second timeout parameter. 
        # Without this, if Google blocks Render's IP, the server hangs forever until Render kills it with a 500.
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=15) as server:
            server.starttls()
            server.login(request.sender_email, request.app_password)
            server.send_message(message)
            
        print("DEBUG: Email payload transaction successfully completed!")
        return {"status": "success", "message": f"Mission accomplished. Email successfully sent to {request.receiver_email}"}

    except HTTPException as http_ex:
        raise http_ex
    except smtplib.SMTPAuthenticationError:
        raise HTTPException(status_code=401, detail="Authentication failed. Check your 16-digit App Password.")
    except smtplib.SMTPConnectError:
        raise HTTPException(status_code=503, detail="SMTP Gateway Connection Timeout. Google mail servers rejected the connection.")
    except Exception as e:
        print(f"ERROR: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    # Render manages the port dynamically via an environment variable; fallback to 8000 locally
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)