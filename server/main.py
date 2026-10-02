import os
import urllib.parse
import smtplib
from email.message import EmailMessage
from typing import List

from dotenv import load_dotenv

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware


# =========================================================
# LOAD ENVIRONMENT
# =========================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

load_dotenv(
    os.path.join(BASE_DIR, ".env")
)


# =========================================================
# APP
# =========================================================

app = FastAPI(
    title="Anjaneya Wood Works API",
    version="1.2.0"
)


# =========================================================
# CORS
# =========================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# CONFIGURATION
# =========================================================

WA_NUMBER = os.getenv(
    "WHATSAPP_NUMBER",
    "918296317492"
)

OWNER_EMAIL = os.getenv(
    "OWNER_EMAIL",
    "krishnamurthy9632816901@gmail.com"
)

SMTP_HOST = os.getenv(
    "SMTP_HOST",
    "smtp.gmail.com"
)

SMTP_PORT = int(
    os.getenv(
        "SMTP_PORT",
        "465"
    )
)

SMTP_USERNAME = os.getenv(
    "SMTP_USERNAME",
    OWNER_EMAIL
)

SMTP_PASSWORD = os.getenv(
    "SMTP_PASSWORD",
    ""
).strip()


# Remove placeholder values automatically
PLACEHOLDER_PASSWORDS = {
    "PUT_GMAIL_APP_PASSWORD_HERE",
    "YOUR_GMAIL_APP_PASSWORD",
    "YOUR_16_CHARACTER_GMAIL_APP_PASSWORD",
    "YOUR_APP_PASSWORD",
}

if SMTP_PASSWORD.upper() in {
    value.upper()
    for value in PLACEHOLDER_PASSWORDS
}:
    SMTP_PASSWORD = ""


# =========================================================
# ORDER MESSAGE
# =========================================================

def create_order_message(
    category: str,
    name: str,
    email: str,
    phone: str,
    location: str,
    description: str
) -> str:

    return (
        "ANJANEYA WOOD WORKS — CUSTOM ORDER\n\n"
        f"Category: {category}\n"
        f"Customer: {name}\n"
        f"Email: {email or 'Not provided'}\n"
        f"Phone: {phone}\n"
        f"Location: {location or 'Not provided'}\n\n"
        "Requirement:\n"
        f"{description}"
    )


# =========================================================
# WHATSAPP DIRECT LINK
# =========================================================

def create_whatsapp_link(
    message_text: str
) -> str:

    encoded_message = urllib.parse.quote(
        message_text
    )

    return (
        f"https://wa.me/"
        f"{WA_NUMBER}"
        f"?text={encoded_message}"
    )


# =========================================================
# ROOT
# =========================================================

@app.get("/")
async def root():

    return {
        "status": "online",
        "service": "Anjaneya Wood Works API",
        "version": "1.2.0"
    }


# =========================================================
# HEALTH
# =========================================================

@app.get("/health")
@app.get("/api/health")
async def health():

    return {
        "status": "ok",
        "whatsapp_number": WA_NUMBER,
        "owner_email": OWNER_EMAIL,
        "email_configured": bool(
            SMTP_PASSWORD
        ),
        "workflow": (
            "direct WhatsApp chat + "
            "email with actual image attachment"
        )
    }


# =========================================================
# WHATSAPP INFO
# =========================================================

@app.get("/api/whatsapp")
async def whatsapp_info():

    return {
        "success": True,
        "number": WA_NUMBER,
        "url": (
            f"https://wa.me/"
            f"{WA_NUMBER}"
        )
    }


# =========================================================
# NORMAL ORDER
# =========================================================

@app.post("/api/orders")
async def orders(

    category: str = Form(...),

    name: str = Form(...),

    email: str = Form(""),

    phone: str = Form(...),

    location: str = Form(""),

    description: str = Form(...),
):

    text = create_order_message(
        category=category,
        name=name,
        email=email,
        phone=phone,
        location=location,
        description=description
    )

    whatsapp_url = create_whatsapp_link(
        text
    )

    return {
        "ok": True,
        "whatsapp_url": whatsapp_url,
        "message": text,
        "owner_whatsapp": WA_NUMBER,
        "note": (
            "The owner WhatsApp chat opens "
            "directly with the order message "
            "pre-filled. Image attachments "
            "are handled through the email button."
        )
    }


# =========================================================
# EMAIL ORDER WITH ACTUAL IMAGE ATTACHMENTS
# =========================================================

@app.post("/api/orders/email")
async def email_order(

    category: str = Form(...),

    name: str = Form(...),

    email: str = Form(...),

    phone: str = Form(...),

    location: str = Form(""),

    description: str = Form(...),

    images: List[UploadFile] = File(
        default=[]
    ),
):

    # -----------------------------------------------------
    # Validate number of images
    # -----------------------------------------------------

    if len(images) > 6:

        raise HTTPException(
            status_code=400,
            detail=(
                "Maximum 6 reference images "
                "are allowed."
            )
        )


    # -----------------------------------------------------
    # Validate customer email
    # -----------------------------------------------------

    if not email.strip():

        raise HTTPException(
            status_code=422,
            detail=(
                "Customer email is required."
            )
        )


    # -----------------------------------------------------
    # Validate SMTP configuration
    # -----------------------------------------------------

    if not SMTP_USERNAME:

        raise HTTPException(
            status_code=503,
            detail=(
                "SMTP_USERNAME is not configured."
            )
        )


    if not SMTP_PASSWORD:

        raise HTTPException(
            status_code=503,
            detail=(
                "Email service is not configured. "
                "Add SMTP_PASSWORD to your server .env "
                "or Render environment variables."
            )
        )


    if not OWNER_EMAIL:

        raise HTTPException(
            status_code=503,
            detail=(
                "OWNER_EMAIL is not configured."
            )
        )


    # -----------------------------------------------------
    # Create email
    # -----------------------------------------------------

    msg = EmailMessage()

    msg["Subject"] = (
        f"New Custom Order — "
        f"{category} — "
        f"{name}"
    )

    msg["From"] = SMTP_USERNAME

    msg["To"] = OWNER_EMAIL

    msg["Reply-To"] = email

    msg.set_content(
        "ANJANEYA WOOD WORKS — NEW CUSTOM ORDER\n\n"

        f"Work category:\n"
        f"{category}\n\n"

        f"Customer name:\n"
        f"{name}\n\n"

        f"Customer email:\n"
        f"{email}\n\n"

        f"Phone:\n"
        f"{phone}\n\n"

        f"City / area:\n"
        f"{location or 'Not provided'}\n\n"

        "Requirement:\n"
        f"{description}\n\n"

        f"Reference images attached: "
        f"{len(images)}\n\n"

        "----------------------------------------\n"

        "This order was submitted through "
        "the Anjaneya Wood Works website.\n\n"

        "Reply directly to this email to "
        "contact the customer."
    )


    # -----------------------------------------------------
    # Attach images
    # -----------------------------------------------------

    attached_count = 0

    for upload in images:

        if not upload:
            continue


        data = await upload.read()


        if not data:
            continue


        # 10 MB maximum per image
        if len(data) > 10 * 1024 * 1024:

            filename = (
                upload.filename
                or "Reference image"
            )

            raise HTTPException(
                status_code=413,
                detail=(
                    f"{filename} is larger "
                    "than 10 MB."
                )
            )


        filename = (
            upload.filename
            or "reference-image.jpg"
        )


        content_type = (
            upload.content_type
            or "application/octet-stream"
        )


        if "/" in content_type:

            maintype, subtype = (
                content_type.split(
                    "/",
                    1
                )
            )

        else:

            maintype = "application"
            subtype = "octet-stream"


        msg.add_attachment(
            data,
            maintype=maintype,
            subtype=subtype,
            filename=filename
        )


        attached_count += 1


    # -----------------------------------------------------
    # Send email
    # -----------------------------------------------------

    try:

        if SMTP_PORT == 465:

            with smtplib.SMTP_SSL(
                SMTP_HOST,
                SMTP_PORT,
                timeout=25
            ) as smtp:

                smtp.login(
                    SMTP_USERNAME,
                    SMTP_PASSWORD
                )

                smtp.send_message(
                    msg
                )

        else:

            with smtplib.SMTP(
                SMTP_HOST,
                SMTP_PORT,
                timeout=25
            ) as smtp:

                smtp.ehlo()

                smtp.starttls()

                smtp.ehlo()

                smtp.login(
                    SMTP_USERNAME,
                    SMTP_PASSWORD
                )

                smtp.send_message(
                    msg
                )


    except smtplib.SMTPAuthenticationError:

        raise HTTPException(
            status_code=502,
            detail=(
                "Gmail authentication failed. "
                "Use the Gmail App Password, "
                "not your normal Gmail password."
            )
        )


    except smtplib.SMTPException as exc:

        raise HTTPException(
            status_code=502,
            detail=(
                "Email provider rejected "
                f"the message: {exc}"
            )
        )


    except Exception as exc:

        raise HTTPException(
            status_code=502,
            detail=(
                f"Email sending failed: {exc}"
            )
        )


    # -----------------------------------------------------
    # Success
    # -----------------------------------------------------

    return {
        "ok": True,
        "message": (
            "Order email sent successfully."
        ),
        "recipient": OWNER_EMAIL,
        "reply_to": email,
        "attachments": attached_count
    }


# =========================================================
# RUN DIRECTLY
# =========================================================

if __name__ == "__main__":

    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
