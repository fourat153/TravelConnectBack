from app.schema.ourBaseModel import OurBaseModel
from app.enums.code_status import CodeStatus

class ConfirmationCodeCreate(OurBaseModel):
    user_id: int
    email: str
    code: str
    status: CodeStatus
    expires_at: str

class CodeDeactivate(OurBaseModel):
    status: CodeStatus
