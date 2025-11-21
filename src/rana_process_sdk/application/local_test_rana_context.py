import json
import shutil
from functools import cached_property
from pathlib import Path
from types import TracebackType
from typing import ClassVar, Generic, TypeVar

from rana_process_sdk.settings import LocalTestSettings

from ..domain import (
    Json,
    ProcessUserError,
    RanaDataset,
    RanaDatasetLizardRaster,
    RanaProcessParameters,
    ThreediApiKey,
)
from ..infrastructure import (
    LizardApiProvider,
    LizardRasterLayerGateway,
    LocalTestRanaApiProvider,
    LocalTestRanaRuntime,
    LocalTestRanaSchematisationGateway,
    RanaSchematisationGateway,
)
from .rana_context import RanaContext, transfer_extension
from .types import RanaPath, ThreediSchematisation

__all__ = ["LocalTestRanaContext"]


T = TypeVar("T", bound=RanaProcessParameters)


class LocalTestRanaContext(RanaContext[T], Generic[T]):
    runtime_override: ClassVar[LocalTestRanaRuntime]

    @cached_property
    def _rana_runtime(self) -> LocalTestRanaRuntime:
        return self.runtime_override

    def download(self, rana_path: RanaPath) -> Path:
        source = self._rana_runtime.project_dir / rana_path.id
        if not source.exists():
            raise FileNotFoundError(
                f"File at {rana_path} does not exist in the local project directory"
            )
        target = self.job_working_dir / rana_path.id
        if target.exists():
            raise FileExistsError(
                f"File at {rana_path} already exists in the local working directory"
            )
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        self.logger.info(
            f"                  | Reading file at path '{rana_path.id}'..."
        )
        return Path(target)

    def upload(
        self,
        local_path: Path,
        rana_path: str,
        data_type: str | None = None,
        description: str = "",
        meta: Json | None = None,
    ) -> RanaPath:
        if not local_path.is_file():
            raise FileNotFoundError(f"File at {local_path} does not exist")
        rana_path = transfer_extension(local_path, rana_path)
        self.logger.info(
            f"                  | Writing file to '{rana_path}' (local test mode)"
        )
        target_path = self._rana_runtime.project_dir / rana_path
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(local_path, target_path)
        if data_type or description or meta:
            metadata_path = Path(str(target_path) + ".json")
            self.logger.info(
                f"                  | Writing file metadata to '{metadata_path}' (local test mode)"
            )
            with metadata_path.open("w") as f:
                json.dump(
                    {"data_type": data_type, "description": description, "meta": meta},
                    f,
                    indent=2,
                )
        return RanaPath(id=rana_path, ref="local-test-ref")

    def __enter__(self) -> None:
        self.job_working_dir.mkdir(mode=0o0700, exist_ok=True)

    def __exit__(
        self, exc_type: type, exc_value: TypeError, traceback: TracebackType
    ) -> None:
        if self._rana_runtime._cleanup_working_dir and self.job_working_dir.is_dir():
            shutil.rmtree(self.job_working_dir)
        self._rana_runtime.set_progress(100, "Completed", True)

    @property
    def _rana_schematisation_gateway(self) -> RanaSchematisationGateway:
        provider = LocalTestRanaApiProvider(self._rana_runtime)
        return LocalTestRanaSchematisationGateway(provider)

    def _settings(self) -> LocalTestSettings:
        assert self._rana_runtime.settings, "Settings must be provided in the runtime"
        return self._rana_runtime.settings

    @property
    def lizard_raster_layer_gateway(self) -> LizardRasterLayerGateway:
        provider = LizardApiProvider(lizard_settings=self._settings().lizard)
        return LizardRasterLayerGateway(provider)

    def get_dataset(self, id: str) -> RanaDataset:
        return self._settings().datasets[id]

    def get_lizard_raster_dataset(self, id: str) -> RanaDatasetLizardRaster:
        dataset = self._settings().datasets[id]
        if lizard_id := dataset.get_id_for_namespace(
            self.lizard_raster_layer_gateway.namespace
        ):
            return RanaDatasetLizardRaster(
                **dataset.model_dump(exclude_none=True),
                lizard_raster=self.get_lizard_raster(lizard_id),
            )
        raise ProcessUserError(
            "Given dataset is not recognized as a Lizard raster",
            description=(
                f"The selected dataset '{dataset.title}' dataset does not have a "
                f"Lizard raster layer associated with it "
                f"(dataset id={dataset.id}, lizard_id={lizard_id or 'null'})."
            ),
        )

    def _threedi_api_key_add(self) -> ThreediApiKey:
        raise NotImplementedError("Set `threedi_api_key` in `local_test/config.yaml`")

    def setup_logger(self) -> None:
        pass  # no Sentry for local test context

    def schematisation_id(self, schematisation: ThreediSchematisation) -> int:
        with open(
            self._rana_runtime.project_dir / schematisation.id
        ) as schematisation_file:
            return int(schematisation_file.read().strip())
