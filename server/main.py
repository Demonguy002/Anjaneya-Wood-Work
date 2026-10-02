import os
import urllib.parse
import smtplib
import time
import logging
from email.message import EmailMessage
from typing import List

from dotenv import load_dotenv

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware


# =========================================================
# LOGGING
# =========================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger("anjaneya-wood-works")


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
    version="1.3.0"
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


# =========================================================
# REMOVE PLACEHOLDER PASSWORDS
# =========================================================

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
# LIMITS
# =========================================================

MAX_IMAGES = 6

# Maximum size of one image
MAX_IMAGE_SIZE = 10 * 1024 * 1024

# Keep total attachments comfortably below Gmail's
# message-size limit.
MAX_TOTAL_IMAGE_SIZE = 20 * 1024 * 1024

# SMTP connection timeout
SMTP_TIMEOUT = 60

# Number of attempts when SMTP temporarily fails
SMTP_MAX_RETRIES = 3


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
        "version": "1.3.0"
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
# SMTP SEND FUNCTION
# =========================================================

def send_email_with_retry(
    msg: EmailMessage
) -> None:

    last_error = None

    for attempt in range(
        1,
        SMTP_MAX_RETRIES + 1
    ):

        smtp = None

        try:

            logger.info(
                "SMTP attempt %s/%s",
                attempt,
                SMTP_MAX_RETRIES
            )

            # -------------------------------------------------
            # Gmail SSL - Port 465
            # -------------------------------------------------

            if SMTP_PORT == 465:

                smtp = smtplib.SMTP_SSL(
                    SMTP_HOST,
                    SMTP_PORT,
                    timeout=SMTP_TIMEOUT
                )

                smtp.ehlo()

            # -------------------------------------------------
            # STARTTLS - Port 587
            # -------------------------------------------------

            else:

                smtp = smtplib.SMTP(
                    SMTP_HOST,
                    SMTP_PORT,
                    timeout=SMTP_TIMEOUT
                )

                smtp.ehlo()

                smtp.starttls()

                smtp.ehlo()

            # -------------------------------------------------
            # LOGIN
            # -------------------------------------------------

            smtp.login(
                SMTP_USERNAME,
                SMTP_PASSWORD
            )

            # -------------------------------------------------
            # SEND
            # -------------------------------------------------

            smtp.send_message(msg)

            logger.info(
                "Email sent successfully on attempt %s",
                attempt
            )

            return

        except smtplib.SMTPAuthenticationError as exc:

            logger.error(
                "Gmail authentication failed: %s",
                exc
            )

            # Authentication won't be fixed by retrying.
            raise HTTPException(
                status_code=500,
                detail=(
                    "Gmail authentication failed. "
                    "Check the SMTP_USERNAME and Gmail "
                    "App Password in Render."
                )
            )

        except (
            smtplib.SMTPServerDisconnected,
            smtplib.SMTPConnectError,
            smtplib.SMTPException,
            TimeoutError,
            OSError
        ) as exc:

            last_error = exc

            logger.warning(
                "SMTP attempt %s failed: %s",
                attempt,
                exc
            )

            # Close broken connection
            try:

                if smtp:
                    smtp.quit()

            except Exception:

                pass

            # Retry if attempts remain
            if attempt < SMTP_MAX_RETRIES:

                wait_seconds = attempt * 2

                logger.info(
                    "Retrying SMTP in %s seconds...",
                    wait_seconds
                )

                time.sleep(
                    wait_seconds
                )

        except Exception as exc:

            last_error = exc

            logger.exception(
                "Unexpected email error"
            )

            try:

                if smtp:
                    smtp.quit()

            except Exception:

                pass

            break

        finally:

            try:

                if smtp:
                    smtp.quit()

            except Exception:

                pass

    # ---------------------------------------------------------
    # All retries failed
    # ---------------------------------------------------------

    logger.error(
        "All SMTP attempts failed. Last error: %s",
        last_error
    )

    raise HTTPException(
        status_code=503,
        detail=(
            "Email service is temporarily unavailable. "
            "Please try again in a few seconds."
        )
    )


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

    logger.info(
        "New email order received: category=%s customer=%s images=%s",
        category,
        name,
        len(images)
    )

    # =======================================================
    # VALIDATE NUMBER OF IMAGES
    # =======================================================

    if len(images) > MAX_IMAGES:

        raise HTTPException(
            status_code=400,
            detail=(
                f"Maximum {MAX_IMAGES} "
                "reference images are allowed."
            )
        )

    # =======================================================
    # VALIDATE CUSTOMER EMAIL
    # =======================================================

    if not email.strip():

        raise HTTPException(
            status_code=422,
            detail="Customer email is required."
        )

    # =======================================================
    # VALIDATE SMTP CONFIGURATION
    # =======================================================

    if not SMTP_USERNAME:

        raise HTTPException(
            status_code=503,
            detail="SMTP_USERNAME is not configured."
        )

    if not SMTP_PASSWORD:

        raise HTTPException(
            status_code=503,
            detail=(
                "Email service is not configured. "
                "Add SMTP_PASSWORD to Render environment variables."
            )
        )

    if not OWNER_EMAIL:

        raise HTTPException(
            status_code=503,
            detail="OWNER_EMAIL is not configured."
        )

    # =======================================================
    # CREATE EMAIL
    # =======================================================

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

    # =======================================================
    # ATTACH IMAGES
    # =======================================================

    attached_count = 0

    total_image_size = 0

    for upload in images:

        if not upload:
            continue

        data = await upload.read()

        if not data:
            continue

        # ---------------------------------------------------
        # Individual image limit
        # ---------------------------------------------------

        if len(data) > MAX_IMAGE_SIZE:

            filename = (
                upload.filename
                or "Reference image"
            )

            raise HTTPException(
                status_code=413,
                detail=(
                    f"{filename} is larger than "
                    "10 MB. Please choose a smaller image."
                )
            )

        # ---------------------------------------------------
        # Total attachment limit
        # ---------------------------------------------------

        total_image_size += len(data)

        if total_image_size > MAX_TOTAL_IMAGE_SIZE:

            raise HTTPException(
                status_code=413,
                detail=(
                    "The total size of reference images "
                    "must be 20 MB or less. "
                    "Please select fewer or smaller images."
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

    logger.info(
        "Prepared email with %s attachments, total size %.2f MB",
        attached_count,
        total_image_size / (1024 * 1024)
    )

    # =======================================================
    # SEND EMAIL
    # =======================================================

    send_email_with_retry(msg)

    # =======================================================
    # SUCCESS
    # =======================================================

    logger.info(
        "Order email successfully delivered to %s",
        OWNER_EMAIL
    )

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
