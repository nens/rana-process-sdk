import logging
from pathlib import Path
from typing import cast
from uuid import UUID

from prefect import get_run_logger
from prefect.artifacts import (
    create_progress_artifact,
    create_table_artifact,
    update_progress_artifact,
)
from prefect.context import EngineContext, SettingsContext
from pydantic import SecretStr

from ..domain import Json
from .rana_runtime import RanaRuntime

__all__ = ["PrefectRanaRuntime"]


class PrefectRanaRuntime(RanaRuntime):
    _progress_artifact_id: UUID | None = None

    def __init__(self) -> None:
        x = EngineContext.get()
        if x is None or x.flow_run is None:
            raise RuntimeError("Not in a Prefect flow run context")
        self._flow_run = x.flow_run
        settings_context = SettingsContext.get()
        assert settings_context
        self.settings_home = settings_context.settings.home
        super().__init__()

    @property
    def job_working_dir(self) -> Path:
        return self.settings_home / str(self.job_id)

    @property
    def _job_variables(self) -> Json:
        return self._flow_run.job_variables or {}

    @property
    def job_id(self) -> UUID:
        return self._flow_run.id

    @property
    def process_id(self) -> UUID:
        assert self._flow_run.deployment_id
        return self._flow_run.deployment_id

    @property
    def job_name(self) -> str:
        return self._flow_run.name

    @property
    def job_parameters(self) -> Json:
        return self._flow_run.parameters

    @property
    def job_secret(self) -> SecretStr:
        return SecretStr(self._job_variables["job_secret"])

    @property
    def tenant_id(self) -> str:
        return self._job_variables["tenant_id"]

    @property
    def logger(self) -> logging.Logger:
        return cast(logging.Logger, get_run_logger())

    def set_result(self, result: Json) -> None:
        create_table_artifact([result], key="results")

    def create_progress(self) -> None:
        progress_artifect_id = create_progress_artifact(0.0, "progress", "Job started")
        assert isinstance(progress_artifect_id, UUID)
        self._progress_artifact_id = progress_artifect_id

    def set_progress(self, progress: float, description: str, log: bool) -> None:
        if log:
            self.logger.info(description)
        assert self._progress_artifact_id is not None
        update_progress_artifact(self._progress_artifact_id, progress, description)
