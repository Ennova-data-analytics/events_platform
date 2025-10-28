from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str

    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int

    S3_ENDPOINT_URL: str
    S3_BUCKET_NAME: str
    S3_ACCESS_KEY_ID: str
    S3_SECRET_ACCESS_KEY: str
    R2_API_TOKEN_VALUE: str
    ACCOUNT_ID: str 

    R2_PUBLIC_DOMAIN: str

    RESEND_API_KEY: str
    RESEND_FROM_EMAIL: str
    RESEND_FROM_NAME: str = "Ennova Events"
    EMAIL_NOTIFICATIONS_ENABLED: bool = True 

    STRIPE_SECRET_KEY: str 
    STRIPE_PUBLISHABLE_KEY: str 
    STRIPE_WEBHOOK_SECRET: str
    FRONTEND_URL: str = "https://ennova-events.com"

    OPENAI_API_KEY: str

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()