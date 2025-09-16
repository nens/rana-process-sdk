from functools import lru_cache
from os import environ

from pydantic import AnyHttpUrl, AnyUrl, BaseModel, SecretStr
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)
from pydantic_settings_yaml.base_settings import YamlConfigSettingsSource

__all__ = ["get_settings", "LizardSettings"]


class LizardSettings(BaseModel):
    host: AnyHttpUrl
    api_key: SecretStr


class ThreediSettings(BaseModel):
    host: str  # AnyHttpUrl adds a trailing "/"


class Settings(BaseSettings):
    environment: str
    sentry_url: AnyUrl | None = None
    rana_api_url: AnyHttpUrl
    lizard: LizardSettings
    threedi: ThreediSettings

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Define the sources and their order for loading the settings values.

        We use the following priority for loading settings:

        1. Arguments passed to the Settings class initialiser.
        2. Environment variables prefixed with "RANA_" (use "__" as a nested delimiter).
           for example: RANA_LIZARD__API_KEY
        3. Variables from Config.yaml_file (replacing <file:path-to-secret> with the contents of the file).

        Returns:
            A tuple containing the sources and their order for
            loading the settings values.
        """
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            YamlConfigSettingsSource(settings_cls),
            file_secret_settings,
        )

    model_config = SettingsConfigDict(
        secrets_dir=environ.get("SETTINGS_SECRETS_DIR", "/etc/secrets"),
        yaml_file=environ.get("SETTINGS_YAML_FILE", "/etc/config.yaml"),
        env_file="/code/.env",
        env_prefix="RANA_",
        env_nested_delimiter="__",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
