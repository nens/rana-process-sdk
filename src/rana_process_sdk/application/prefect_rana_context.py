import shutil
from functools import cached_property
from pathlib import Path
from typing import Generic, TypeVar
from uuid import UUID

from pydantic import SecretStr
from threedi_api_client.files import download_file, upload_file

from ..domain import (
    FileStat,
    History,
    Json,
    ProcessUserError,
    RanaDataset,
    RanaDatasetLizardRaster,
    RanaProcessParameters,
    ThreediApiKey,
)
from ..infrastructure import (
    SENTRY_BLOCK_NAME,
    LizardRasterLayerGateway,
    PrefectRanaRuntime,
    PrefectRanaSchematisationGateway,
    RanaDatasetGateway,
    RanaFileGateway,
    RanaSchematisationGateway,
    SentryBlock,
    ThreediApiKeyGateway,
)
from .rana_context import RanaContext, transfer_extension
from .types import RanaPath, ThreediSchematisation

__all__ = ["PrefectRanaContext"]

T = TypeVar("T", bound=RanaProcessParameters)


class PrefectRanaContext(RanaContext[T], Generic[T]):
    @cached_property
    def _rana_runtime(self) -> PrefectRanaRuntime:
        return PrefectRanaRuntime()

    @property
    def job_id(self) -> UUID:
        return self._rana_runtime.job_id

    @property
    def job_secret(self) -> SecretStr:
        return self._rana_runtime.job_secret

    @property
    def tenant_id(self) -> str:
        return self._rana_runtime.tenant_id

    @property
    def _file_gateway(self) -> RanaFileGateway:
        return RanaFileGateway()

    @property
    def _rana_schematisation_gateway(self) -> RanaSchematisationGateway:
        return PrefectRanaSchematisationGateway()

    @property
    def _rana_dataset_gateway(self) -> RanaDatasetGateway:
        return RanaDatasetGateway()

    @property
    def _threedi_api_key_gateway(self) -> ThreediApiKeyGateway:
        return ThreediApiKeyGateway()

    def _threedi_api_key_add(self) -> ThreediApiKey:
        return self._threedi_api_key_gateway.add()

    def threedi_remove_api_key(self, key: ThreediApiKey) -> None:
        self._threedi_api_key_gateway.remove(key.prefix)

    @property
    def lizard_raster_layer_gateway(self) -> LizardRasterLayerGateway:
        return LizardRasterLayerGateway()

    def get_file_stat(self, rana_path: RanaPath) -> FileStat:
        stat = self._file_gateway.stat(rana_path.id, rana_path.ref)
        if stat is None:
            raise ValueError(f"File at {rana_path.id} does not exist in Rana")
        return stat

    def get_file_history(self, rana_path: RanaPath) -> list[History]:
        history = self._file_gateway.history(rana_path.id, rana_path.ref, 1)
        if not history:
            raise ValueError(
                f"Could not find latest ref for file on path {rana_path.id}"
            )
        return history

    def download(self, rana_path: RanaPath) -> Path:
        # Check if path exists in project history
        rana_path = rana_path.model_copy(
            update={"ref": self.get_file_history(rana_path)[0].ref}
        )
        target = self.job_working_dir / rana_path.id
        if target.exists():
            raise FileExistsError(
                f"File at {rana_path} already exists in the local working directory"
            )
        # ensure directory existence
        target.parent.mkdir(parents=True, exist_ok=True)
        self.logger.info(
            f"Reading file at path '{rana_path.id}' from ref '{rana_path.ref}'..."
        )
        return download_file(
            str(self._file_gateway.get_download_url(rana_path.id, rana_path.ref)),
            target,
        )[0]

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
        upload_obj = self._file_gateway.upload_start(rana_path)
        self.logger.info(f"Writing file to '{rana_path}'...")
        upload_file(upload_obj["urls"][0], local_path)
        return RanaPath(
            id=rana_path,
            ref=self._file_gateway.upload_complete(
                upload_obj, data_type=data_type, description=description, meta=meta
            ).ref,
        )

    def __enter__(self) -> None:
        self._rana_runtime.create_progress()
        self.job_working_dir.mkdir(mode=0o0700, exist_ok=True)

    def __exit__(self, exc_type, exc_value, traceback) -> None:  # type: ignore
        if self.job_working_dir.is_dir():
            shutil.rmtree(self.job_working_dir)
        if key := self._rana_runtime.threedi_api_key:
            self.threedi_remove_api_key(key)
        self._rana_runtime.set_progress(100, "Completed", True)

    def setup_logger(self) -> None:
        try:
            sentry_block = SentryBlock.load(name=SENTRY_BLOCK_NAME)
        except ValueError:
            pass
        else:
            sentry_block.init()
            sentry_block.set_tags_and_context(self._rana_runtime._flow_run)

    def schematisation_id(self, schematisation: ThreediSchematisation) -> int:
        file_stat = self.get_file_stat(schematisation)
        # TODO: Descriptor will be removed from file_stat in the future: see #1685
        if file_stat.descriptor is None:
            raise RuntimeError(
                f"Could not retrieve descriptor information for file: `{schematisation.id}` from the API"
            )
        if file_stat.descriptor.get("data_type", "") != "threedi_schematisation":
            raise ProcessUserError(
                "Schematisation input file does not have correct data type",
                f"The descriptor.data_type for file `{schematisation.id}`is not `threedi_schematisation`",
            )
        if schematisation_id := file_stat.descriptor.get("meta", {}).get("id", None):
            return int(schematisation_id)
        raise RuntimeError(
            "Schematisation does not exit, Could not retrieve the 3Di schematisation id for file: `{schematisation.id}`",
        )

    def get_dataset(self, id: str) -> RanaDataset:
        """Retrieve a dataset by its id in Rana."""
        dataset = self._rana_dataset_gateway.get(id)
        links = self._rana_dataset_gateway.get_data_links(id)
        # Temporary situation; WCS and WFS are not included in the data links yet
        # so we add them here to ensure they are always present
        if not any(link.protocol == "OGC:WCS" for link in links):
            if wcs_link := dataset.get_wcs_link():
                links.append(wcs_link)
        if not any(link.protocol == "OGC:WFS" for link in links):
            if wfs_link := dataset.get_wfs_link():
                links.append(wfs_link)
        return dataset.model_copy(update={"links": links})

    def get_lizard_raster_dataset(self, id: str) -> RanaDatasetLizardRaster:
        dataset = self._rana_dataset_gateway.get(id)
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
