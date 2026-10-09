from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import field_validator
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

    # Zona horaria en la que se interpretan y se muestran todas las horas de la
    # aplicación: los horarios de los reportes programados, las fechas de los
    # correos y del Excel, y los límites de los filtros por día.
    app_timezone: str = "America/Mexico_City"

    # Marca y datos de contacto que se muestran en los correos salientes.
    app_base_url: str = "https://www.patiolaesperanza.com.mx"
    # WebP no se renderiza en Outlook de escritorio ni en algunos clientes de
    # Android: si el logo no aparece, sube la versión PNG y cambia esta URL.
    logo_url: str = "https://www.patiolaesperanza.com.mx/assets/img/EsperanzaLogo.webp"
    contacto_telefono: str = "753 537 7838"
    contacto_email: str = "contacto@patiolaesperanza.com.mx"
    sitio_web: str = "www.patiolaesperanza.com.mx"

    @field_validator("app_timezone")
    @classmethod
    def _validar_timezone(cls, value: str) -> str:
        # Una zona inválida haría fallar cada ZoneInfo(settings.app_timezone) del
        # arranque con un error oscuro. Se valida aquí para fallar de una vez y claro.
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError(f"Zona horaria inválida: {value!r}") from exc
        return value

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()


def zona_horaria_app() -> ZoneInfo:
    """Zona horaria configurada en `APP_TIMEZONE`.

    Es una función y no una constante de módulo para que un cambio de
    `settings.app_timezone` en una prueba surta efecto. `ZoneInfo` guarda sus
    instancias en caché, así que llamarla seguido no vuelve a leer el disco.
    """
    return ZoneInfo(settings.app_timezone)
