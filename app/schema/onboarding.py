from app.schema.our_base_model import OurBaseModel, OurBaseOut
from app.enums import PrivacyType , Onboarding

class OnboardingData(OurBaseModel):
    lat: float
    lon: float
    privacy: PrivacyType

class OnboardingOut(OurBaseOut):
    has_completed_onboarding: Onboarding | None = None
