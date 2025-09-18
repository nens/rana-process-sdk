from os import environ
from uuid import UUID

from pydantic import BaseModel, SecretStr
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)
from pydantic_settings_yaml.base_settings import YamlConfigSettingsSource

from ..domain import RanaDataset
from .settings import LizardSettings

__all__ = ["get_local_test_settings", "LocalTestSettings"]


class TestThreediSettings(BaseModel):
    host: str  # AnyHttpUrl adds a trailing "/"
    api_key: SecretStr
    organisation: UUID


class LocalTestSettings(BaseSettings):
    lizard: LizardSettings | None = None
    threedi: TestThreediSettings | None = None
    datasets: dict[str, RanaDataset] = {}

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
        yaml_file="local_test/config.yaml",
        env_prefix="RANA_",
        env_nested_delimiter="__",
    )


def get_local_test_settings() -> LocalTestSettings:
    return LocalTestSettings()  # type: ignore
