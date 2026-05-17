from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import base64
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

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
    app_password: str  # This will now correctly take your Gmail App Password
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

    try:
        final_body = request.body.replace("{{name}}", request.receiver_name or "Hiring Manager")

        # Create MIME Message container
        msg = MIMEMultipart()
        msg['From'] = f"Sujal Koli <{request.sender_email}>"
        msg['To'] = request.receiver_email
        msg['Subject'] = request.subject
        msg.attach(MIMEText(final_body, 'plain'))

        # 1. Process Attachments
        if request.resume_status == "default":
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
                msg.attach(part)

        elif request.resume_status == "custom":
            if not request.custom_resume_data:
                raise HTTPException(
                    status_code=400, 
                    detail="Data Corruption: Custom attachment requested but content data stream parameter is null."
                )
            # Decode the base64 string provided from the client side
            file_data = base64.b64decode(request.custom_resume_data)
            part = MIMEBase("application", "octet-stream")
            part.set_payload(file_data)
            encoders.encode_base64(part)
            filename = request.custom_resume_name or "Uploaded_Resume.pdf"
            part.add_header("Content-Disposition", f"attachment; filename={filename}")
            msg.attach(part)

        # 2. Deliver via SMTP (Using Gmail servers)
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()  # Upgrade connection to secure
            server.login(request.sender_email, request.app_password)
            server.sendmail(request.sender_email, request.receiver_email, msg.as_string())

        return {"status": "success", "message": f"Mission accomplished. Email successfully sent to {request.receiver_email}"}

    except HTTPException as http_ex:
        raise http_ex
    except smtplib.SMTPAuthenticationError:
        raise HTTPException(status_code=401, detail="Gmail Authentication failed. Check your sender email or App Password.")
    except Exception as e:
        print(f"ERROR: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)