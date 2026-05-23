from fastapi import APIRouter, status
from fastapi.params import Depends
from sqlalchemy.orm import Session
from Dbengin import get_db
from app.enums import PrivacyEntityType
from app.models import PrivacySettings
from app.schema.privacy_settings import PrivacySettingsCreate, PrivacySettingsUpdate, PrivacySettingsOut
from app.utils import oauth2

router = APIRouter()

@router.post('/privacy-settings', response_model=PrivacySettingsOut, status_code=status.HTTP_201_CREATED)
def create_privacy_setting(
    entry: PrivacySettingsCreate,
    db: Session = Depends(get_db),
    current_user=Depends(oauth2.get_current_user)
):
    existing = db.query(PrivacySettings).filter(
        PrivacySettings.entity_type == entry.entity_type,
        PrivacySettings.entity_id == entry.entity_id
    ).first()
    if existing:
        return PrivacySettingsOut(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Privacy setting already exists for this entity"
        )
    try:
        setting = PrivacySettings(
            entity_type=entry.entity_type,
            entity_id=entry.entity_id,
            privacy_type=entry.privacy_type
        )
        db.add(setting)
        db.commit()
        db.refresh(setting)
    except Exception as e:
        db.rollback()
        error = exception_handler(e, db)
        return PrivacySettingsOut(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Failed to create privacy setting"
        )
    return PrivacySettingsOut(
        id=setting.id,
        entity_type=setting.entity_type,
        entity_id=setting.entity_id,
        privacy_type=setting.privacy_type,
        status_code=status.HTTP_201_CREATED,
        message="Privacy setting created"
    )


@router.put('/privacy-settings/{entity_type}/{entity_id}', response_model=PrivacySettingsOut, status_code=status.HTTP_200_OK)
def update_privacy_setting(
    entity_type: PrivacyEntityType,
    entity_id: int,
    entry: PrivacySettingsUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(oauth2.get_current_user)
):
    entity_setting = db.query(PrivacySettings).filter(PrivacySettings.entity_id == entity_id , 
    PrivacySettings.entity_type == entity_type
    ).first()
    if not entity_setting:
        return PrivacySettingsOut(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Privacy setting not found"
        )
    try:
        entity_setting.privacy_type = entry.privacy_type
        db.commit()
        db.refresh(entity_setting)
    except Exception as e:
        db.rollback()
        return PrivacySettingsOut(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Failed to update privacy setting"
        )
    return PrivacySettingsOut(
        id=entity_setting.id,
        entity_type=entity_setting.entity_type,
        entity_id=entity_setting.entity_id,
        privacy_type=entity_setting.privacy_type,
        status_code=status.HTTP_200_OK,
        message="Privacy setting updated"
    )


@router.get('/privacy-settings/{entity_type}/{entity_id}', response_model=PrivacySettingsOut, status_code=status.HTTP_200_OK)
def get_privacy_setting(
    entity_type: PrivacyEntityType,
    entity_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(oauth2.get_current_user)
):
    entity_setting = db.query(PrivacySettings).filter(PrivacySettings.entity_id == entity_id , 
    PrivacySettings.entity_type == entity_type
    ).first()
    if not entity_setting:
        return PrivacySettingsOut(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Privacy setting not found"
        )
    return PrivacySettingsOut(
        id=entity_setting.id,
        entity_type=entity_setting.entity_type,
        entity_id=entity_setting.entity_id,
        privacy_type=entity_setting.privacy_type,
        status_code=status.HTTP_200_OK,
        message="Privacy setting found"
    )