from fpdf import FPDF


HEADER_COLOR = (38, 70, 83)
ACCENT_COLOR = (42, 157, 143)
CARD_FILL = (245, 248, 250)
TEXT_DARK = (40, 40, 40)
TEXT_MUTED = (95, 99, 104)


class StyledReportPDF(FPDF):
    def footer(self) -> None:
        self.set_y(-12)
        self.set_font("Helvetica", "I", 9)
        self.set_text_color(*TEXT_MUTED)
        self.cell(0, 8, f"Page {self.page_no()}", align="C")


def _safe_text(value: object) -> str:
    text = str(value or "")
    replacements = {
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2013": "-",
        "\u2014": "-",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    return text


def _section_title(pdf: StyledReportPDF, title: str) -> None:
    pdf.set_fill_color(*ACCENT_COLOR)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 9, _safe_text(title), new_x="LMARGIN", new_y="NEXT", fill=True)
    pdf.ln(2)
    pdf.set_text_color(*TEXT_DARK)


def _body_text(pdf: StyledReportPDF, text: str) -> None:
    pdf.set_font("Helvetica", size=11)
    pdf.set_text_color(*TEXT_DARK)
    pdf.multi_cell(0, 7, _safe_text(text))
    pdf.ln(1)


def _score_card(pdf: StyledReportPDF, title: str, value: str, x: float, y: float, width: float) -> None:
    pdf.set_xy(x, y)
    pdf.set_fill_color(*CARD_FILL)
    pdf.set_draw_color(220, 226, 230)
    pdf.rect(x, y, width, 22, style="DF")
    pdf.set_xy(x + 4, y + 4)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*TEXT_MUTED)
    pdf.cell(width - 8, 5, _safe_text(title))
    pdf.set_xy(x + 4, y + 11)
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(*TEXT_DARK)
    pdf.cell(width - 8, 6, _safe_text(value))


def render_pdf(report_json: dict) -> bytes:
    pdf = StyledReportPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_fill_color(*HEADER_COLOR)
    pdf.rect(0, 0, 210, 30, style="F")
    pdf.set_xy(12, 10)
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 8, _safe_text(report_json.get("headline", "Screening Summary Report")))

    pdf.set_xy(12, 32)
    pdf.set_text_color(*TEXT_DARK)
    pdf.set_font("Helvetica", "", 10)
    meta = report_json.get("meta", {})
    participant_line = (
        f"Anonymous Session ID: {meta.get('session_id', meta.get('participant_id', 'N/A'))}    "
        f"Created UTC: {meta.get('created_utc', 'N/A')}    "
        f"Question Count: {meta.get('question_count', 'N/A')}"
    )
    pdf.multi_cell(0, 6, _safe_text(participant_line))
    pdf.ln(3)

    scores = report_json.get("scores", {})
    card_y = pdf.get_y()
    left_x = pdf.l_margin
    card_width = (pdf.w - pdf.l_margin - pdf.r_margin - 12) / 3
    _score_card(
        pdf,
        "Primary Emotion",
        str(scores.get("emotion_label", "unknown")).replace("_", " ").title(),
        left_x,
        card_y,
        card_width,
    )
    _score_card(
        pdf,
        "BC-QoL Score",
        (
            f"{scores.get('bcqol_score_total', 'N/A')}/100"
            if scores.get("bcqol_score_total") is not None
            else "N/A"
        ),
        left_x + card_width + 8,
        card_y,
        card_width,
    )
    _score_card(
        pdf,
        "MMSE Score",
        (
            f"{scores.get('mmse_score_total', 'N/A')}/30"
            if scores.get("mmse_score_total") is not None
            else "N/A"
        ),
        left_x + (card_width * 2) + 12,
        card_y,
        card_width,
    )
    pdf.set_y(card_y + 28)

    risk_flags = report_json.get("risk_flags", {})
    _section_title(pdf, "Risk Overview")
    risk_summary = (
        f"High Distress: {'Yes' if risk_flags.get('high_distress') else 'No'}\n"
        f"Self-Harm Ideation: {'Yes' if risk_flags.get('self_harm_ideation') else 'No'}\n"
        f"Needs Human Follow-up: {'Yes' if risk_flags.get('needs_human_followup') else 'No'}"
    )
    _body_text(pdf, risk_summary)

    sections = report_json.get("sections", {})
    for heading, key in [
        ("Emotional Summary", "emotional_summary"),
        ("Cognitive Summary", "cognitive_summary"),
        ("Combined Insights", "combined_insights"),
        ("Next Steps", "next_steps"),
    ]:
        _section_title(pdf, heading)
        _body_text(pdf, sections.get(key, ""))

    _section_title(pdf, "Disclaimer")
    _body_text(pdf, report_json.get("disclaimer", ""))

    _section_title(pdf, "Support Resources")
    _body_text(pdf, report_json.get("signposting", ""))

    generation_note = report_json.get("generation_note", "")
    if generation_note:
        _section_title(pdf, "Report Generation Note")
        _body_text(pdf, generation_note)

    output = pdf.output(dest="S")
    if isinstance(output, str):
        return output.encode("latin-1")
    return bytes(output)
