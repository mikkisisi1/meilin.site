"""
Notification senders for transactional messages (magic links, etc.).

Currently STUBBED: writes the rendered link to the backend log so the user can
copy it during development. Swap `_send_email_stub` / `_send_whatsapp_stub` for
real Resend / Twilio calls once the API keys land in `.env` — the public
`send_magic_link()` API stays the same.
"""
import os
import logging

logger = logging.getLogger(__name__)


def _send_email_stub(*, to: str, subject: str, link: str) -> None:
    # TODO: when RESEND_API_KEY arrives, replace with:
    #   import resend; resend.api_key = os.environ["RESEND_API_KEY"]
    #   await asyncio.to_thread(resend.Emails.send, {...})
    logger.warning(
        "MAGIC_LINK_EMAIL_STUB | to=%s | subject=%s | link=%s",
        to, subject, link,
    )


def _send_whatsapp_stub(*, to: str, body: str) -> None:
    # TODO: when TWILIO_ACCOUNT_SID/AUTH_TOKEN arrive, replace with:
    #   from twilio.rest import Client
    #   Client(sid, token).messages.create(
    #       from_=os.environ["TWILIO_WHATSAPP_FROM"], to=f"whatsapp:{to}", body=body
    #   )
    logger.warning("MAGIC_LINK_WHATSAPP_STUB | to=%s | body=%s", to, body)


async def send_magic_link(*, channel: str, destination: str, link: str) -> None:
    """Dispatch a magic-link to the user's chosen channel.

    `channel` is "email" or "whatsapp"; `destination` is the email / E.164 phone.
    Real senders should replace the *_stub helpers above; signature stays stable.
    """
    if channel == "email":
        _send_email_stub(
            to=destination,
            subject="Your Slim You sign-in link",
            link=link,
        )
    elif channel == "whatsapp":
        _send_whatsapp_stub(
            to=destination,
            body=f"Slim You — tap to continue your session: {link}",
        )
    else:
        raise ValueError(f"Unknown channel: {channel}")


def is_real_sender_configured(channel: str) -> bool:
    """Returns True when the env keys for a real sender are present."""
    if channel == "email":
        return bool(os.environ.get("RESEND_API_KEY"))
    if channel == "whatsapp":
        return bool(os.environ.get("TWILIO_ACCOUNT_SID") and os.environ.get("TWILIO_AUTH_TOKEN"))
    return False
