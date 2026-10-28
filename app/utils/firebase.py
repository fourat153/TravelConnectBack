import logging
from pathlib import Path

import firebase_admin
from firebase_admin import credentials

from app.config import settings

logger = logging.getLogger(__name__)


def _load_credentials() -> credentials.Base | None:
    credentials_path = settings.google_application_credentials
    if credentials_path and Path(credentials_path).is_file():
        return credentials.Certificate(credentials_path)

    return None


def initialize_firebase() -> None:
    if firebase_admin._apps:
        return

    cred = _load_credentials()
    if cred is None:
        logger.warning(
        )
        return

    firebase_admin.initialize_app(cred)


initialize_firebase()
