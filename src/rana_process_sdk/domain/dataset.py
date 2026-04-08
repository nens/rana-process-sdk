from pydantic import AnyHttpUrl, AwareDatetime, BaseModel, ConfigDict

from .lizard_raster import LizardRaster

__all__ = [
    "RanaDataset",
    "RanaDatasetLizardRaster",
    "DatasetLink",
    "DatasetFile",
    "DatasetLayer",
]


class ResourceIdentifier(BaseModel):
    model_config = ConfigDict(frozen=True)

    code: str
    link: AnyHttpUrl | None


class DatasetLayer(BaseModel):
    id: str
    title: str | None = None


class DatasetFile(BaseModel):
    href: AnyHttpUrl
    size: int
    title: str | None = None
    envelope: tuple[float, float, float, float] | None = None
    time: AwareDatetime | None = None


class DatasetLink(BaseModel):
    model_config = ConfigDict(frozen=True)

    protocol: str
    title: str | None = None
    url: AnyHttpUrl | None = None
    layers: list[DatasetLayer] = []
    files: list[DatasetFile] = []


class RanaDataset(BaseModel):
    """Subset of fields of the Dataset get and search response"""

    model_config = ConfigDict(frozen=True)

    id: str
    title: str  # mapped from resourceTitleObject.default
    resource_identifier: list[ResourceIdentifier] = []
    links: list[DatasetLink] = []

    def get_id_for_namespace(self, namespace: AnyHttpUrl) -> str | None:
        """Returns the id of given namespace, otherwise None."""
        for identifier in self.resource_identifier:
            if identifier.link == namespace:
                return identifier.code
        return None

    def _get_link_by_protocol(self, protocol: str) -> DatasetLink | None:
        """Returns the link with given protocol if available, otherwise None."""
        for link in self.links:
            if link.protocol == protocol:
                return link
        return None

    def get_wcs_link(self) -> DatasetLink | None:
        return self._get_link_by_protocol("OGC:WCS")

    def get_wfs_link(self) -> DatasetLink | None:
        return self._get_link_by_protocol("OGC:WFS")

    def get_ogc_api_features_link(self) -> DatasetLink | None:
        return self._get_link_by_protocol("OGC:API features")


class RanaDatasetLizardRaster(RanaDataset):
    id: str
    title: str  # mapped from resourceTitleObject.default
    resource_identifier: list[ResourceIdentifier] = []
    lizard_raster: LizardRaster

    def get_id_for_namespace(self, namespace: AnyHttpUrl) -> str | None:
        """Returns the id of given namespace, otherwise None."""
        for identifier in self.resource_identifier:
            if identifier.link == namespace:
                return identifier.code
        return None
