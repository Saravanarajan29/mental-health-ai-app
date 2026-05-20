# UK GDPR Research Handling Checklist

This prototype is designed to support UK GDPR-aligned research data handling; it must be reviewed before real participant testing.

## Project Governance Placeholders

- Data controller: `[Confirm university or project data controller]`
- Researcher contact: `[Add researcher name and university email]`
- Supervisor/DPO review: `[Confirm supervisor and/or Data Protection Officer review]`
- Lawful basis: `[Confirm with university before participant testing]`
- Article 9 special category condition: `[Confirm with university before participant testing]`

## Data Minimisation Checklist

- Collect anonymous session ID only.
- Do not request name, email, phone number, address, exact date of birth, IP address, NHS number, or clinical record number.
- Do not save full raw chat transcripts by default.
- Save only structured screening completion status, scores, non-diagnostic labels, risk flag summaries, and feedback ratings.
- Redact optional comments before saving.

## Pseudonymisation and Anonymisation Checklist

- Use a random anonymous session ID as the primary key.
- Keep any consent workflow separate from direct identifiers.
- Do not combine records with external identifiable datasets.
- Treat free-text feedback as potentially identifying and automatically redact it.
- Record withdrawal limitations where a participant cannot provide their anonymous session ID.

## DPIA and Ethics Review Checklist

- Confirm whether a Data Protection Impact Assessment is required.
- Confirm university ethics review requirements before real participant testing.
- Confirm participant information sheet wording.
- Confirm risk and safeguarding escalation wording.
- Confirm whether Google Sheets is approved for the research context.

## Security Checklist

- Keep the Google Sheet private/restricted.
- Share the Sheet only with the service account `client_email` using Editor permission.
- Never commit service account JSON keys.
- Keep `.env` and credentials out of version control.
- Keep local Excel backups in a restricted project folder.
- Avoid printing secrets or raw credential errors in Streamlit.

## Retention and Deletion Checklist

- Confirm the exact retention period with supervisor/DPO.
- Placeholder retention wording: retained until dissertation assessment is complete and then deleted or anonymised further according to university policy.
- Delete service account credentials when no longer required.
- Delete local and Google Sheet research data at the approved retention endpoint.
- Document deletion completion for dissertation records.
