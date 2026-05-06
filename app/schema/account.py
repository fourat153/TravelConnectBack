from app.schema.our_base_model import OurBaseModel, OurBaseOut

class ConfirmAccount(OurBaseModel):
    user_id: int
    confirmation_code: str

class ConfirmAccountOut(OurBaseOut):
    pass
