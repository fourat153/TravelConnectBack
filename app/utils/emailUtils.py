
from typing import List
from fastapi_mail import ConnectionConfig, MessageSchema , FastMail ,MessageType
from ..config import settings
from jinja2 import Environment, select_autoescape, PackageLoader
from ..enums import EmailTemplate

conf = ConnectionConfig(
    MAIL_USERNAME=settings.mail_username,
    MAIL_PASSWORD=settings.mail_password,
    MAIL_FROM=settings.mail_from,
    MAIL_PORT=587,
    MAIL_SERVER=settings.mail_server,
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
)
env = Environment(
    loader=PackageLoader('app', 'templates'),
    autoescape=False 
)

template_name_per_email = {
    EmailTemplate.confirmaccount: "email_confirmation_template.html"

}

async def send_email(subject: str, recipients: List, email_template: EmailTemplate, email: str, code: str,user_id:int = None):
    template_name = template_name_per_email[email_template]
    template = env.get_template(template_name)
    html = template.render(
        name=email,
        code=code,
        user_id = user_id,
        frontend_url=settings.frontend_url.rstrip("/"),
        subject=subject,
    )

    message = MessageSchema(
    subject=subject,
    recipients=recipients,
    body=html,
    subtype=MessageType.html
    )

    fm = FastMail(conf)
    await fm.send_message(message)