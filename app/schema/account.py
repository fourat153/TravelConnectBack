from app.schema.ourBaseModel import OurBaseModel, OurBaseOut

class ConfirmAccount(OurBaseModel):
    user_id: int
    confirmation_code: str

class ConfirmAccountOut(OurBaseOut):
    pass
