import logging
import threading
from django.conf import settings

logger = logging.getLogger(__name__)


def send_invite_email(invite):
    def _send():
        try:
            import resend
            resend.api_key = settings.RESEND_API_KEY
            frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:3000")
            resend.Emails.send({
                "from": "Analytics Platform <onboarding@resend.dev>",
                "to": [invite.email],
                "subject": f"You've been invited to join {invite.organization.name}",
                "text": f"""Hi,

You've been invited to join {invite.organization.name} as {invite.role}.

Accept your invite here:
{frontend_url}/invite/{invite.token}

This invite expires in 7 days.

Analytics Platform
""",
            })
            logger.info(f"invite_email_sent email={invite.email}")
        except Exception as e:
            logger.error(f"invite_email_failed email={invite.email} error={e}")

    threading.Thread(target=_send, daemon=True).start()
