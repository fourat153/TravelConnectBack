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
    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()