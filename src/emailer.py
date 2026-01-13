"""SMTP email helper for sending HTML reports."""
from __future__ import annotations

import logging
import os
import smtplib
from email.message import EmailMessage


def _get_env(name: str, default: str | None = None) -> str:
    value = os.getenv(name, default)
    if value is None or value == "":
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def send_email(subject: str, html_body: str) -> None:
    recipient = _get_env("EMAIL_TO")
    smtp_host = _get_env("SMTP_HOST")
    smtp_port = int(_get_env("SMTP_PORT"))
    smtp_user = _get_env("SMTP_USER")
    smtp_pass = _get_env("SMTP_PASS")
    sender = os.getenv("EMAIL_FROM", smtp_user)

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = sender
    message["To"] = recipient
    message.set_content("This email requires an HTML-capable client.")
    message.add_alternative(html_body, subtype="html")

    logging.info("Sending email to %s", recipient)

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.send_message(message)
