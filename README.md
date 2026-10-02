# Anjaneya Wood Works

Vite + React frontend and FastAPI backend for Anjaneya Wood Works.

## Customer order workflow

1. Customer signs up/logs in with name, email, phone, gender and password.
2. The logged-in email is reused in the custom-order form.
3. **Send to WhatsApp Chat** opens the configured owner WhatsApp number directly with the order text prefilled.
4. **Email Order + Image** sends the order to the owner's email through the FastAPI backend, with uploaded reference images as real email attachments. The customer's login email is used as `Reply-To`, so the owner can reply directly to the customer.

## Local development

### Frontend
```bash
cd client
npm install
npm run dev
```

Set `client/.env`:
```env
VITE_API_URL=http://localhost:8000
```

### Backend

Create a virtual environment and install:
```bash
cd server
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

## Email configuration

Copy `.env.example` to `.env` for local use, or configure these variables on Render:

- `OWNER_EMAIL=krishnamurthy9632816901@gmail.com`
- `SMTP_HOST=smtp.gmail.com`
- `SMTP_PORT=465`
- `SMTP_USERNAME=krishnamurthy9632816901@gmail.com`
- `SMTP_PASSWORD=<Gmail App Password>`
- `WHATSAPP_NUMBER=918296317492`

**Do not use or publish the normal Gmail password.** Create a Gmail App Password after enabling 2-Step Verification on the sending Google account.

The website does not spoof the customer's email as the sender. SMTP authentication uses the workshop's configured email account; the customer's login email is placed in `Reply-To` and in the order body.

## Deployment

- `client/` → Vercel
- `server/` → Render
- Set the Render environment variables above.
- Set Vercel `VITE_API_URL` to the deployed Render API URL.

## Final local email setup

The project includes `.env` files for local development. The Gmail password must be a Google App Password, not the normal account password. Replace `PUT_GMAIL_APP_PASSWORD_HERE` in `server/.env` with the App Password for `krishnamurthy9632816901@gmail.com`.

Run the backend from `server`:

```bash
python -m pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Run the frontend from `client`:

```bash
npm install
npm run dev
```

For Render, set the same SMTP variables as Render environment variables; do not rely on a checked-in `.env` file in production.
