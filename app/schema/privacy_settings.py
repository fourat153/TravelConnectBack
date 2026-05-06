from typing import Optional
from app.enums import PrivacyEntityType, PrivacyType
from app.schema.our_base_model import OurBaseModel, OurBaseOut

class PrivacySettingsCreate(OurBaseModel):
    entity_type:  PrivacyEntityType
    entity_id:    int
    privacy_type: PrivacyType = PrivacyType.public

class PrivacySettingsUpdate(OurBaseModel):
    privacy_type: PrivacyType

class PrivacySettingsOut(OurBaseOut):
    id:           Optional[int] = None
    entity_type:  Optional[PrivacyEntityType] = None
    entity_id:    Optional[int] = None
    privacy_type: Optional[PrivacyType] = None