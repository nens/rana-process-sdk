import logging
from pathlib import Path
from uuid import UUID

from pydantic import SecretStr

import rana_process_sdk
from rana_process_sdk.settings import LocalTestSettings

from ..domain import Json, ThreediApiKey
from .rana_runtime import RanaRuntime

__all__ = ["LocalTestRanaRuntime"]


class LocalTestRanaRuntime(RanaRuntime):
    project_dir: Path
    settings: LocalTestSettings | None
    threedi_api_key: ThreediApiKey | None = None
    _job_working_dir: Path
    _cleanup_working_dir: bool

    def __init__(
        self,
        working_dir: Path | str,
        project_dir: Path | str,
        settings: LocalTestSettings | None = None,
        cleanup_workdir: bool = False,
    ) -> None:
        working_dir_path = (
            Path(working_dir) if not isinstance(working_dir, Path) else working_dir
        )
        assert working_dir_path.parent.exists(), (
            f"Workdir must be placed in a existing directory {working_dir_path.parent}"
        )
        self._job_working_dir = working_dir_path
        project_dir_path = (
            Path(project_dir) if not isinstance(project_dir, Path) else project_dir
        )
        assert project_dir_path.exists(), (
            f"Project directory {project_dir_path} does not exist"
        )
        self.project_dir = project_dir_path
        self.settings = settings
        if settings and settings.threedi:
            self.threedi_api_key = ThreediApiKey(
                prefix=settings.threedi.api_key.get_secret_value().split(".")[0],
                key=settings.threedi.api_key,
                organisations=[settings.threedi.organisation],
            )
        self._cleanup_working_dir = cleanup_workdir

    @property
    def job_working_dir(self) -> Path:
        return self._job_working_dir

    @property
    def _job_variables(self) -> Json:
        raise NotImplementedError("_job_variables must be implemented in subclasses")

    @property
    def job_id(self) -> UUID:
        raise NotImplementedError("job_id must be implemented in subclasses")

    @property
    def process_id(self) -> UUID:
        raise NotImplementedError("process_id must be implemented in subclasses")

    @property
    def job_name(self) -> str:
        raise NotImplementedError("job_name must be implemented in subclasses")

    @property
    def job_parameters(self) -> Json:
        raise NotImplementedError("job_parameters must be implemented in subclasses")

    @property
    def job_secret(self) -> SecretStr:
        raise NotImplementedError("job_secret must be implemented in subclasses")

    @property
    def tenant_id(self) -> str:
        raise NotImplementedError("tenant_id must be implemented in subclasses")

    @property
    def logger(self) -> logging.Logger:
        logger = logging.getLogger(rana_process_sdk.__name__)
        logger.setLevel(logging.INFO)
        logger.propagate = True
        return logger

    def set_progress(self, progress: float, description: str, log: bool) -> None:
        progress_bar = "█" * int(progress // 10) + " " * (10 - int(progress // 10))
        self.logger.info(f"[{progress_bar}] {progress:3.0f}% | {description}")

    def set_result(self, result: Json) -> None:
        self.logger.info("result            | value")
        self.logger.info(
            "----------------- | -------------------------------------------------"
        )
        for item in result.items():
            self.logger.info(f"{item[0]: <17} | {item[1]}")
        self.logger.info(
            "---------------   | -------------------------------------------------"
        )
