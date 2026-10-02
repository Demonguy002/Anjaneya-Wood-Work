import os
import urllib.parse
import logging
import base64
import requests
from typing import List

from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("anjaneya-wood-works")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

app = FastAPI(title="Anjaneya Wood Works API", version="1.4.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

WA_NUMBER = os.getenv("WHATSAPP_NUMBER", "918296317492")
OWNER_EMAIL = os.getenv("OWNER_EMAIL", "krishnamurthy9632816901@gmail.com")
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "").strip()
RESEND_FROM = os.getenv("RESEND_FROM", "Anjaneya Wood Works <onboarding@resend.dev>")

MAX_IMAGES = 6
MAX_IMAGE_SIZE = 10 * 1024 * 1024
MAX_TOTAL_IMAGE_SIZE = 20 * 1024 * 1024
RESEND_API_URL = "https://api.resend.com/emails"
RESEND_TIMEOUT = 60


def create_order_message(category, name, email, phone, location, description):
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


def create_whatsapp_link(message_text):
    return f"https://wa.me/{WA_NUMBER}?text={urllib.parse.quote(message_text)}"


@app.get("/")
async def root():
    return {
        "status": "online",
        "service": "Anjaneya Wood Works API",
        "version": "1.4.0",
        "email_provider": "Resend HTTPS API",
    }


@app.get("/health")
@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "whatsapp_number": WA_NUMBER,
        "owner_email": OWNER_EMAIL,
        "email_configured": bool(RESEND_API_KEY),
        "email_provider": "Resend HTTPS API",
        "workflow": "direct WhatsApp chat + email with actual image attachment",
    }


@app.get("/api/whatsapp")
async def whatsapp_info():
    return {
        "success": True,
        "number": WA_NUMBER,
        "url": f"https://wa.me/{WA_NUMBER}",
    }


@app.post("/api/orders")
async def orders(
    category: str = Form(...),
    name: str = Form(...),
    email: str = Form(""),
    phone: str = Form(...),
    location: str = Form(""),
    description: str = Form(...),
):
    text = create_order_message(category, name, email, phone, location, description)
    return {
        "ok": True,
        "whatsapp_url": create_whatsapp_link(text),
        "message": text,
        "owner_whatsapp": WA_NUMBER,
        "note": "The owner WhatsApp chat opens directly with the order message pre-filled. Image attachments are handled through the email button.",
    }


def send_email_with_resend(subject, text_body, customer_email, attachments):
    if not RESEND_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="Email service is not configured. Add RESEND_API_KEY to the Render environment.",
        )

    payload = {
        "from": RESEND_FROM,
        "to": [OWNER_EMAIL],
        "reply_to": customer_email,
        "subject": subject,
        "text": text_body,
    }

    if attachments:
        payload["attachments"] = attachments

    headers = {
        "Authorization": f"Bearer {RESEND_API_KEY}",
        "Content-Type": "application/json",
        "User-Agent": "Anjaneya-Wood-Works/1.4.0",
    }

    try:
        logger.info("Sending order email through Resend HTTPS API")
        response = requests.post(
            RESEND_API_URL,
            headers=headers,
            json=payload,
            timeout=RESEND_TIMEOUT,
        )
    except requests.Timeout:
        logger.error("Resend request timed out")
        raise HTTPException(status_code=503, detail="Email service timed out. Please try again.")
    except requests.RequestException as exc:
        logger.exception("Could not connect to Resend: %s", exc)
        raise HTTPException(status_code=503, detail="Email service is temporarily unavailable. Please try again.")

    try:
        result = response.json()
    except ValueError:
        result = {"message": response.text[:500]}

    if 200 <= response.status_code < 300:
        logger.info("Resend accepted email. id=%s", result.get("id", "unknown"))
        return result

    logger.error("Resend rejected email. status=%s response=%s", response.status_code, result)
    message = result.get("message") or result.get("error") or "Email provider rejected the message."
    raise HTTPException(status_code=502, detail=f"Email provider rejected the message: {message}")


@app.post("/api/orders/email")
async def email_order(
    category: str = Form(...),
    name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    location: str = Form(""),
    description: str = Form(...),
    images: List[UploadFile] = File(default=[]),
):
    logger.info(
        "New email order received: category=%s customer=%s images=%s",
        category,
        name,
        len(images),
    )

    if len(images) > MAX_IMAGES:
        raise HTTPException(status_code=400, detail=f"Maximum {MAX_IMAGES} reference images are allowed.")

    if not email.strip():
        raise HTTPException(status_code=422, detail="Customer email is required.")

    if not RESEND_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="Email service is not configured. Add RESEND_API_KEY to Render environment variables.",
        )

    if not OWNER_EMAIL:
        raise HTTPException(status_code=503, detail="OWNER_EMAIL is not configured.")

    email_text = (
        "ANJANEYA WOOD WORKS — NEW CUSTOM ORDER\n\n"
        f"Work category:\n{category}\n\n"
        f"Customer name:\n{name}\n\n"
        f"Customer email:\n{email}\n\n"
        f"Phone:\n{phone}\n\n"
        f"City / area:\n{location or 'Not provided'}\n\n"
        "Requirement:\n"
        f"{description}\n\n"
        f"Reference images attached: {len(images)}\n\n"
        "----------------------------------------\n"
        "This order was submitted through the Anjaneya Wood Works website.\n\n"
        "Reply directly to this email to contact the customer."
    )

    attachments = []
    attached_count = 0
    total_image_size = 0

    for upload in images:
        if not upload:
            continue

        data = await upload.read()
        if not data:
            continue

        if len(data) > MAX_IMAGE_SIZE:
            filename = upload.filename or "Reference image"
            raise HTTPException(
                status_code=413,
                detail=f"{filename} is larger than 10 MB. Please choose a smaller image.",
            )

        total_image_size += len(data)
        if total_image_size > MAX_TOTAL_IMAGE_SIZE:
            raise HTTPException(
                status_code=413,
                detail="The total size of reference images must be 20 MB or less. Please select fewer or smaller images.",
            )

        filename = upload.filename or "reference-image.jpg"
        encoded_content = base64.b64encode(data).decode("utf-8")
        attachments.append({"filename": filename, "content": encoded_content})
        attached_count += 1

    logger.info(
        "Prepared email with %s attachments, total raw size %.2f MB",
        attached_count,
        total_image_size / (1024 * 1024),
    )

    result = send_email_with_resend(
        subject=f"New Custom Order — {category} — {name}",
        text_body=email_text,
        customer_email=email,
        attachments=attachments,
    )

    resend_id = result.get("id", "unknown")
    logger.info(
        "Order email successfully submitted through Resend. id=%s recipient=%s",
        resend_id,
        OWNER_EMAIL,
    )

    return {
        "ok": True,
        "message": "Order email sent successfully.",
        "recipient": OWNER_EMAIL,
        "reply_to": email,
        "attachments": attached_count,
        "email_id": resend_id,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
