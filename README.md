# Mental Health AI Screening App

A Streamlit-based educational prototype for anonymous preliminary mental health and cognitive screening. The website combines a consent flow, a short guided interview, local emotion/risk summarisation, BC-QoL scoring, an MMSE-style cognitive screening wizard, structured report generation, PDF export, and anonymous research feedback capture.

> This project is for education and preliminary screening only. It is not a diagnosis, clinical advice, or a replacement for support from a qualified healthcare professional.

## Current Status

The app is ready for Streamlit deployment from a code/startup perspective.

- Entry point: `app.py`
- Python runtime: `runtime.txt` uses Python 3.11
- Dependencies: `requirements.txt`
- Streamlit config: `.streamlit/config.toml`
- Default operation works without paid API keys
- Optional integrations: Gemini follow-up questions, OpenAI report text, Google Sheets/Apps Script research autosave

## Quick Start

### Prerequisites

- Python 3.11 recommended
- pip

### Install

```bash
pip install -r requirements.txt
```

### Run Locally

```bash
streamlit run app.py
```

On Windows, you can also use:

```powershell
.\run_app.ps1
```

The local app opens at `http://localhost:8501`.

## Environment Variables

The app can run without a `.env` file. To enable optional integrations locally, copy `.env.example` to `.env` and fill only the values you need.

```env
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini
GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.5-flash

ENABLE_GOOGLE_SHEETS_SAVE=false
ENABLE_LOCAL_XLSX_BACKUP=true
GOOGLE_SHEET_ID=
GOOGLE_SERVICE_ACCOUNT_FILE=
GOOGLE_SERVICE_ACCOUNT_JSON=
ENABLE_GOOGLE_APPS_SCRIPT_SAVE=false
GOOGLE_APPS_SCRIPT_WEB_APP_URL=
GOOGLE_APPS_SCRIPT_SHARED_SECRET=
RESEARCH_PRIVACY_NOTICE_VERSION=uk-gdpr-research-v1
APP_VERSION=prototype-feedback-records-v1
```

## Website Flow

### 1. Consent

The website starts with a required consent page before any screening content is shown.

- Generates an anonymous session ID.
- Collects required consent confirmations.
- Collects optional research context such as age group, gender option, preferred language, device type, previous screening experience, and accessibility support needs.
- Stores anonymous consent metadata locally in `outputs/consent_data.xlsx` when local file writing is available.
- Does not request names, email addresses, phone numbers, or other direct identifiers.

### 2. Chatbot Interview

The first tab is a five-question guided interview.

- Opening question: `Tell me about yourself or your current situation.`
- Follow-up intents are:
  - `impact_on_life`
  - `duration_intensity`
  - `coping_support`
  - `gentle_safety_check`
- Gemini can optionally generate adaptive follow-up questions when `GEMINI_API_KEY` is configured.
- If Gemini is unavailable, the app uses local adaptive fallback questions.
- After five answers, the app runs local emotion and risk analysis.
- The transcript is shown in the interface, but raw interview transcripts are not saved in the research workbook by default.

### 3. Clinical Forms

The second tab contains a staged assessment wizard.

1. BC-QoL Form
2. MMSE Start Consent
3. MMSE Orientation
4. MMSE Registration
5. MMSE Attention
6. MMSE Recall
7. MMSE Language Tasks
8. Review and Submit
9. Results Summary

BC-QoL uses 4 Likert-style items and reports a normalized score out of 100.

The MMSE-style section scores up to 30 points across orientation, registration, attention/calculation, delayed recall, and language tasks. It includes remote-screening disclaimers, accessibility review flags, object naming images, a three-step command task, sentence writing, and a copy-design multiple-choice task.

### 4. Results and Report

The third tab summarizes the completed screening.

- Shows consent status.
- Displays the emotion classification, probability-style scores, summary, confidence note, and risk flags.
- Shows BC-QoL and MMSE results after the clinical forms are submitted.
- Generates report content after interview, BC-QoL, and MMSE sections are complete.
- Uses OpenAI report generation if `OPENAI_API_KEY` is configured; otherwise falls back to a local structured report.
- Creates a downloadable PDF report.
- Saves/updates one anonymous screening row in `outputs/research_screening_records.xlsx` when local backup is enabled.
- Shows a research feedback form and updates the same anonymous session row with sanitized feedback.

## Emotion and Risk Analysis

Emotion analysis is local and rule-based by default. It analyzes participant answers only, not the app's own interview questions.

Supported labels:

- `joy`
- `sadness`
- `anger`
- `fear`
- `neutral`
- `stress`
- `anxiety`

Risk flags include high distress, self-harm ideation keyword detection, and whether human follow-up may be appropriate. These flags are screening indicators only and must not be treated as clinical diagnosis.

## Research Records

The app stores anonymous structured research data using the anonymous `session_id` as the primary key.

Local workbook:

- `outputs/research_screening_records.xlsx`

Worksheets:

- `screening_records`: one wide row per anonymous screening session
- `feedback_records`: one row per feedback submission
- `save_audit`: save attempts and safe error summaries

The app upserts by `session_id`, so repeated saves in the same browser session update the existing row rather than creating duplicates.

## Google Autosave

Google autosave is optional. The website still works when Google saving is disabled or unavailable.

Supported options:

- Direct Google Sheets save with `gspread` and service-account credentials
- Google Apps Script web app save with a shared secret
- Local Excel backup through `ENABLE_LOCAL_XLSX_BACKUP=true`

For Streamlit deployment, add the service-account JSON in Streamlit secrets:

```toml
[google_service_account]
type = "service_account"
project_id = "your-project"
private_key_id = "..."
private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
client_email = "your-service-account@your-project.iam.gserviceaccount.com"
client_id = "..."
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "..."
```

Never commit service-account JSON files, `.env`, generated Excel files, or logs.

## Streamlit Deployment

Deploy with these files and folders:

```text
app.py
requirements.txt
runtime.txt
.streamlit/config.toml
config/
core/
forms/
public/
docs/
README.md
SETUP_CHECKLIST.md
```

Do not deploy generated/runtime files:

```text
.env
outputs/*.xlsx
outputs/*.csv
outputs/*.log
__pycache__/
*.pyc
*service-account*.json
*google*credentials*.json
```

Streamlit Cloud settings:

- Main file path: `app.py`
- Python version: from `runtime.txt`
- Secrets: optional, only for OpenAI/Gemini/Google integrations

## Project Structure

```text
mental_health_ai_app/
+-- app.py                         # Main Streamlit application
+-- requirements.txt               # Python package list
+-- runtime.txt                    # Streamlit/Python runtime pin
+-- run_app.ps1                    # Windows helper script
+-- .env.example                   # Optional environment template
+-- .streamlit/
|   +-- config.toml                # Streamlit browser config
+-- config/
|   +-- settings.py                # Environment/config loading
+-- core/
|   +-- interview.py               # Five-question adaptive interview flow
|   +-- emotion_classifier.py      # Local emotion summary and risk flags
|   +-- report_generator.py        # OpenAI/local structured report generation
|   +-- pdf_generator.py           # PDF rendering
|   +-- record_store.py            # Anonymous local/Google research record saving
|   +-- safety.py                  # Crisis keyword checks and signposting
|   +-- state.py                   # Streamlit session-state defaults
|   +-- cloud_llm.py               # Optional OpenAI JSON helper
|   +-- prompts.py                 # Gemini interview and report prompts
+-- forms/
|   +-- consent_form.py            # Consent and anonymous metadata capture
|   +-- feedback_form.py           # Anonymous research feedback form
|   +-- bcqol_form.py              # BC-QoL questions and scoring
|   +-- mmse_form.py               # MMSE-style state, validation, and scoring
+-- docs/
|   +-- uk_gdpr_research_checklist.md
+-- public/
|   +-- assets/mmse/               # SVG assets for MMSE visual tasks
+-- outputs/                       # Local generated files, ignored for deployment
```

## Technology Stack

- Streamlit
- Requests
- Pydantic
- fpdf2
- python-dotenv
- openpyxl
- OpenAI Python SDK
- gspread and google-auth

## Troubleshooting

### Streamlit Does Not Start

- Run `pip install -r requirements.txt`.
- Run `python -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501`.
- Check the terminal for missing package or syntax errors.

### Report Button Is Disabled

- Complete the interview.
- Submit the BC-QoL form.
- Complete and submit the MMSE-style wizard.
- Return to `Results and Report`.

### PDF Download Is Missing

- Generate the report content first.
- Click `Create PDF Download`.
- Then use the `Download PDF Report` button.

### Google Save Fails

- Confirm Google saving is enabled.
- Confirm the service account credentials are configured through Streamlit secrets or environment variables.
- Share the target Google Sheet with the service-account `client_email`.
- The app will still continue with local backup if enabled.

### Local Excel Save Fails

- Make sure `outputs/` is writable.
- Close any open Excel workbook in `outputs/`.
- Keep `ENABLE_LOCAL_XLSX_BACKUP=true`.

## Safety, Ethics, and Privacy

- Screening outputs are educational indicators only.
- The app is not a diagnostic medical device.
- Users are warned not to enter personally identifying information.
- Self-harm keyword detection triggers signposting language.
- A qualified professional should interpret any mental health or cognitive concern.
- UK GDPR and ethics review should be completed before real participant data collection.

See `docs/uk_gdpr_research_checklist.md` for the research governance checklist.
