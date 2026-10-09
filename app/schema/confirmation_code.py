from datetime import datetime
from app.schema.our_base_model import OurBaseModel
from app.enums.code_status import CodeStatus

class ConfirmationCodeCreate(OurBaseModel):
    user_id: int
    email: str
    code: str
    status: CodeStatus
    expires_at: datetime

class CodeDeactivate(OurBaseModel):
    status: CodeStatus
