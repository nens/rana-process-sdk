__all__ = ["RanaDatasetGateway"]


from ..domain import DatasetLayer, DatasetLink, DoesNotExist, Json, RanaDataset
from .rana_api_provider import PrefectRanaApiProvider


class RanaDatasetMapper:
    def _map_link_field(self, link: dict) -> DatasetLink:
        name = link["nameObject"].get("default") or ""
        return DatasetLink(
            protocol=link["protocol"],
            url=link["urlObject"].get("default") or None,
            layers=[DatasetLayer(id=name, title=None)],
        )

    def _map_link_detail_response(self, link: dict) -> DatasetLink:
        return DatasetLink(
            protocol=link["protocol"],
            title=link.get("title"),
            url=link.get("url"),
            layers=link.get("layers", []),
            files=link.get("files", []),
        )

    def to_internal(self, external: Json) -> RanaDataset:
        """Map external dataset representation to internal RanaDataset."""
        return RanaDataset(
            id=external["id"],
            title=external["resourceTitleObject"]["default"],
            resource_identifier=external["resourceIdentifier"],
            links=[
                self._map_link_field(x)
                for x in external["link"]
                if x.get("protocol") in {"OGC:WFS", "OGC:WCS"}
            ],
        )


class RanaDatasetGateway:
    path = "datasets/{id}"
    data_links_path = "datasets/{id}/data-links"
    mapper = RanaDatasetMapper()

    def __init__(self, provider_override: PrefectRanaApiProvider | None = None):
        self.provider_override = provider_override

    @property
    def provider(self) -> PrefectRanaApiProvider:
        return self.provider_override or PrefectRanaApiProvider()

    def get(self, id: str) -> RanaDataset:
        """Get dataset by prefix."""
        response = self.provider.job_request("GET", self.path.format(id=id))
        if response is None:
            raise DoesNotExist("dataset", id)
        return self.mapper.to_internal(response)

    def get_data_links(self, id: str) -> list[DatasetLink]:
        """Get dataset links by prefix."""
        response = self.provider.job_request("GET", self.data_links_path.format(id=id))
        if response is None:
            raise DoesNotExist("dataset", id)
        return [self.mapper._map_link_detail_response(x) for x in response]
