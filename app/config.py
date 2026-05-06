from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_hostname: str
    database_port: str
    database_password: str
    database_name: str
    database_username: str
    mail_username: str | None 
    mail_password: str | None 
    mail_from: str | None 
    mail_server: str | None 
    secret_key: str
    algorithm: str
    access_token_expire_min: int
    CLOUDINARY_CLOUD_NAME: str
    CLOUDINARY_API_KEY: str
    CLOUDINARY_API_SECRET: str
    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()