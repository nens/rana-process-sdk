import logging
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING, Generic, TypeVar, cast, get_args
from uuid import UUID

from pydantic import BaseModel, Field, SecretStr, field_validator, model_validator
from threedi_api_client import ThreediApi

from ..domain import (
    FileStat,
    Json,
    LizardRaster,
    ProcessInternalError,
    ProcessUserError,
    RanaDataset,
    RanaDatasetLizardRaster,
    RanaProcessParameters,
    ThreediApiKey,
)
from ..infrastructure import (
    LizardRasterLayerGateway,
    RanaDatasetGateway,
    RanaRuntime,
    RanaSchematisationGateway,
    is_optional,
    unpack_optional,
)
from ..settings import get_settings
from .types import RanaPath, ThreediSchematisation, path_picker_from_json_prop
from .widgets import DirectoryPickerWidget, PathPickerWidget

if TYPE_CHECKING:
    from rana_process_sdk import PrefectRanaContext

__all__ = ["RanaContext", "transfer_extension"]


T = TypeVar("T", bound=RanaProcessParameters)


class FileOutput(BaseModel):
    is_optional: bool
    data_type: str | None = None
    meta_values: Json = Field(default_factory=dict)


class DirectoryOutput(BaseModel):
    is_optional: bool
    expected_files: dict[str, FileOutput] = Field(default_factory=dict)


OutputPaths = dict[str, FileOutput | DirectoryOutput]


def transfer_extension(local_path: Path, rana_path: str) -> str:
    # Do nothing if the local path has no extension
    # or if the rana path already has the same extension
    if not local_path.suffix or rana_path.lower().endswith(local_path.suffix.lower()):
        return rana_path
    return rana_path + local_path.suffix


def expected_files(path_picker: PathPickerWidget) -> dict[str, FileOutput]:
    expected_files: dict[str, FileOutput] = {}
    for path, expected_file in cast(
        DirectoryPickerWidget, path_picker
    ).expected_files.items():
        expected_files[path] = FileOutput(is_optional=True)
        if expected_file:
            expected_files[path] = FileOutput(
                is_optional=True,
                data_type=expected_file.data_type,
                meta_values=expected_file.meta,
            )
    return expected_files


class RanaContext(BaseModel, Generic[T], validate_assignment=True):
    output: T | None = None  # for the JSONSchema and for after-process validation
    output_paths: dict[str, str] = {}  # maps output field name -> path in project

    def to_prefect_context(self) -> "PrefectRanaContext[T]":
        from rana_process_sdk import PrefectRanaContext

        output_type = cast(type[T], get_args(self.model_fields["output"].annotation)[0])
        return PrefectRanaContext[output_type](
            output=self.output, output_paths=self.output_paths
        )  # type: ignore

    @classmethod
    def get_output_schema(cls) -> Json:
        # returns the JSONSchema of the 'output' field
        result = get_args(cls.model_fields["output"].annotation)[0]
        assert issubclass(result, RanaProcessParameters)
        return result.model_json_schema()

    @classmethod
    def expected_output_paths(cls) -> OutputPaths:
        # list all 'file' output field + whether they are required
        result: OutputPaths = {}
        schema = cls.get_output_schema()

        for key, prop in schema["properties"].items():
            _optional = is_optional(prop)
            if _optional:
                if "default" not in prop:
                    raise ValueError(
                        f"Optional output field '{key}' must have a default value"
                    )
                prop = unpack_optional(prop)
                assert prop is not None
            if path_picker := path_picker_from_json_prop(prop):
                if isinstance(path_picker, DirectoryPickerWidget):
                    result[key] = DirectoryOutput(
                        is_optional=_optional,
                        expected_files=expected_files(path_picker),
                    )
                else:
                    result[key] = FileOutput(
                        is_optional=_optional,
                        data_type=path_picker.output_datatype,
                        meta_values=path_picker.output_meta_values,
                    )
                continue
        return result

    def set_output(
        self,
        output: T | Json,
        *,
        data_type_override: dict[str, str] = {},
        meta_override: dict[str, Json] = {},
    ) -> None:
        self.output = cast(T, output)
        assert self.output is not None
        for key, path_details in self.expected_output_paths().items():
            if key in self.output_paths:
                output_value = getattr(self.output, key).id
                if isinstance(path_details, DirectoryOutput):
                    rana_path = self.upload_dir(
                        Path(output_value),
                        self.output_paths[key],
                        path_details.expected_files,
                    )
                else:
                    if path_details.data_type == "threedi_schematisation":
                        rana_path = self.upload_schematisation(
                            output_value, self.output_paths[key]
                        )
                    else:
                        rana_path = self.upload(
                            Path(output_value),
                            self.output_paths[key],
                            data_type=data_type_override.get(
                                key, path_details.data_type
                            ),
                            meta=meta_override.get(key, path_details.meta_values),
                        )
            else:
                rana_path = None
            setattr(self.output, key, rana_path)
        self._rana_runtime.set_result(self.output.model_dump(mode="json"))

    @field_validator("output_paths", mode="after")
    @classmethod
    def validate_output_paths(cls, value: dict[str, str]) -> dict[str, str]:
        expected = cls.expected_output_paths()
        required = {x for x, path in expected.items() if not path.is_optional}
        # remove empty values
        value = {k: v for (k, v) in value.items() if v}
        missing = required - set(value.keys())
        if missing:
            raise ValueError(f"output_paths must contain {required}")
        unexpected = set(value.keys()) - set(expected)
        if unexpected:
            raise ValueError(f"received unexpected output paths {unexpected}")
        # check if paths are actual file paths
        for key, path in value.items():
            if isinstance(expected[key], DirectoryOutput) and not str(path).endswith(
                "/"
            ):
                raise ValueError(f"output path for '{key}' is not a directory")
            elif not isinstance(expected[key], DirectoryOutput) and str(path).endswith(
                "/"
            ):
                raise ValueError(f"output path for '{key}' is not a file")
        paths = list(value.values())
        if len(paths) != len(set(paths)):
            raise ValueError("Output paths parameters should be unique")
        return value

    @model_validator(mode="after")
    def clean_output(self) -> "RanaContext[T]":
        if self.output is None:
            return self
        # all queried outputs are required to be present
        for key in self.output_paths:
            if getattr(self.output, key) is None:
                raise ValueError(
                    f"Process did not create a file for output field '{key}'"
                )
        return self

    def log_exception(self, exception: Exception) -> None:
        if isinstance(exception, ProcessUserError):
            self.logger.error(exception.format().model_dump_json())
        else:
            self.logger.error(
                ProcessInternalError(exception).format().model_dump_json()
            )

    def get_lizard_raster(self, id: str) -> LizardRaster:
        """Retrieve a lizard raster from Lizard by its dataset id in Rana."""
        return self.lizard_raster_layer_gateway.get(id)

    @property
    def job_working_dir(self) -> Path:
        return self._rana_runtime.job_working_dir

    @property
    def logger(self) -> logging.Logger:
        return self._rana_runtime.logger

    def set_progress(self, progress: int, description: str, log: bool = True) -> None:
        self._rana_runtime.set_progress(progress, description, log)

    @cached_property
    def _rana_runtime(self) -> RanaRuntime:
        raise NotImplementedError("RanaRuntime must be implemented in a subclass")

    @property
    def _rana_dataset_gateway(self) -> RanaDatasetGateway:
        raise NotImplementedError(
            "rana_dataset_gateway must be implement in a subclass"
        )

    @property
    def job_id(self) -> UUID:
        raise NotImplementedError("job_id must be implemented in a subclass")

    @property
    def job_secret(self) -> SecretStr:
        raise NotImplementedError("job_secret must be implemented in a subclass")

    @property
    def tenant_id(self) -> str:
        raise NotImplementedError("tenant_id must be implemented in a subclass")

    @property
    def lizard_raster_layer_gateway(self) -> LizardRasterLayerGateway:
        raise NotImplementedError(
            "lizard_raster_layer_gateway must be implemented in a subclass"
        )

    @property
    def _rana_schematisation_gateway(self) -> RanaSchematisationGateway:
        raise NotImplementedError(
            "rana_schematisation_gateway must be implemented in a subclass"
        )

    def get_file_stat(self, rana_path: RanaPath) -> FileStat:
        raise NotImplementedError(
            "get_file_stat method must be implemented in a subclass"
        )

    def download(self, rana_path: RanaPath) -> Path:
        raise NotImplementedError("Download method must be implemented in a subclass")

    def upload(
        self,
        local_path: Path,
        rana_path: str,
        data_type: str | None = None,
        description: str = "",
        meta: Json | None = None,
    ) -> RanaPath:
        raise NotImplementedError("Upload method must be implemented in a subclass")

    def upload_schematisation(self, schematisation_id: str, rana_path: str) -> RanaPath:
        self.logger.info(f"Writing schematisation to '{rana_path}'...")
        file_upload = self._rana_schematisation_gateway.upload(
            rana_path, schematisation_id
        )
        return RanaPath(id=rana_path, ref=file_upload.ref)

    def upload_dir(
        self,
        local_path: Path,
        rana_path: str,
        expected_files: dict[str, FileOutput] = {},
    ) -> RanaPath:
        if not local_path.is_dir():
            raise FileNotFoundError(f"Directory at {local_path} does not exist")
        root = Path(rana_path)
        # recursively iterate through all files in the directory
        for file in local_path.rglob("*"):
            if file.is_file():
                relative_path = str(file.relative_to(local_path))
                expected_file = expected_files.get(
                    relative_path, FileOutput(is_optional=True)
                )
                self.upload(
                    local_path=file,
                    rana_path=str(root / relative_path),
                    data_type=expected_file.data_type,
                    meta=expected_file.meta_values,
                )
        return RanaPath(id=rana_path)  # TODO put the actual ref here

    def get_dataset(self, id: str) -> RanaDataset:
        """Retrieve a dataset by its id in Rana."""
        raise NotImplementedError(
            "get_dataset method must be implemented in a subclass"
        )

    def get_lizard_raster_dataset(self, id: str) -> RanaDatasetLizardRaster:
        """Retrieve a dataset with associated lizard raster by Rana dataset id."""
        raise NotImplementedError(
            "get_lizard_raster_dataset method must be implemented in a subclass"
        )

    def __enter__(self) -> None:
        raise NotImplementedError("Context manager must be implemented in a subclass")

    def __exit__(self, exc_type, exc_value, traceback) -> None:  # type: ignore
        raise NotImplementedError("Context manager must be implemented in a subclass")

    def _threedi_api_key_add(self) -> ThreediApiKey:
        raise NotImplementedError(
            "Threedi api key add must be implemented in a subclass"
        )

    def threedi_api_key(self) -> ThreediApiKey:
        if not self._rana_runtime.threedi_api_key:
            self._rana_runtime.threedi_api_key = self._threedi_api_key_add()
        return self._rana_runtime.threedi_api_key

    def threedi_api(self) -> ThreediApi:
        return ThreediApi(
            config={
                "THREEDI_API_HOST": get_settings().threedi.host,
                "THREEDI_API_PERSONAL_API_TOKEN": self.threedi_api_key().key.get_secret_value(),
            }
        )

    def setup_logger(self) -> None:
        raise NotImplementedError(
            "setup_logger method must be implemented in a subclass"
        )

    def schematisation_id(self, schematisation: ThreediSchematisation) -> int:
        raise NotImplementedError(
            "schematisation_id method must be implemented in a subclass"
        )
