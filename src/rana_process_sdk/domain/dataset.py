from pydantic import AnyHttpUrl, BaseModel, ConfigDict

from .lizard_raster import LizardRaster

__all__ = ["RanaDataset", "RanaDatasetLizardRaster"]


class ResourceIdentifier(BaseModel):
    model_config = ConfigDict(frozen=True)

    code: str
    link: AnyHttpUrl | None


class DatasetLink(BaseModel):
    model_config = ConfigDict(frozen=True)

    protocol: str
    name: str | None = None
    url: AnyHttpUrl | None = None


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

    def get_wcs_link(self) -> DatasetLink | None:
        """Returns the WCS link if available, otherwise None."""
        for link in self.links:
            if link.protocol == "OGC:WCS":
                return link
        return None

    def get_wfs_link(self) -> DatasetLink | None:
        """Returns the WFS link if available, otherwise None."""
        for link in self.links:
            if link.protocol == "OGC:WFS":
                return link
        return None


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
