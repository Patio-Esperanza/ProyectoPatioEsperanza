from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    migrations_database_url: str
    jwt_secret: str
    jwt_expires_minutes: int = 240
    cors_origins: str = "http://localhost:3000"
    sendgrid_api_key: str
    sendgrid_from_email: str

    # Marca y datos de contacto que se muestran en los correos salientes.
    app_base_url: str = "https://www.patiolaesperanza.com.mx"
    # WebP no se renderiza en Outlook de escritorio ni en algunos clientes de
    # Android: si el logo no aparece, sube la versión PNG y cambia esta URL.
    logo_url: str = "https://www.patiolaesperanza.com.mx/assets/img/EsperanzaLogo.webp"
    contacto_telefono: str = "753 537 7838"
    contacto_email: str = "contacto@patiolaesperanza.com.mx"
    sitio_web: str = "www.patiolaesperanza.com.mx"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
