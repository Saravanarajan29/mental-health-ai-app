# Quick Setup Checklist

Use this checklist to run the Streamlit app locally or prepare it for Streamlit Community Cloud.

## Prerequisites

- [ ] Python 3.11 installed for local development
- [ ] pip available
- [ ] Optional: Gemini API key for adaptive interview follow-up questions
- [ ] Optional: OpenAI API key for cloud-generated report text
- [ ] Optional: Google service account credentials for Google Sheets autosave

## Local Installation

1. [ ] Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. [ ] Optional: create `.env` from `.env.example` and fill only the integrations you need.

3. [ ] Run the app:
   ```bash
   streamlit run app.py
   ```

## Streamlit Deployment

1. [ ] Push these files to GitHub: `app.py`, `requirements.txt`, `runtime.txt`, `.streamlit/config.toml`, `config/`, `core/`, `forms/`, `public/`, and `docs/`.
2. [ ] Do not upload `.env`, service-account JSON files, generated Excel files, logs, or `__pycache__` folders.
3. [ ] In Streamlit Cloud, set the app entry point to `app.py`.
4. [ ] Add optional secrets only if those integrations are required.
5. [ ] Verify the deployed app can open the consent page and complete the screening flow.

## Quick Test

- [ ] App opens at `http://localhost:8501`
- [ ] Consent form can be completed
- [ ] Interview can be completed and emotion analysis changes with answers
- [ ] BC-QoL and MMSE sections can be submitted
- [ ] Screening report and PDF can be generated
- [ ] Research save status shows `Record saved successfully.`

## Useful Links

- Gemini API key: https://aistudio.google.com/apikey
- Streamlit secrets: https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management
