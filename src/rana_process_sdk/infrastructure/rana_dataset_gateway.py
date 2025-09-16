__all__ = ["RanaDatasetGateway"]


from ..domain import DoesNotExist, Json, RanaDataset
from .rana_api_provider import PrefectRanaApiProvider


class RanaDatasetMapper:
    def _map_link(self, link: dict) -> dict | None:
        return {
            "protocol": link["protocol"],
            "name": link["nameObject"].get("default") or None,
            "url": link["urlObject"].get("default") or None,
        }
        return None

    def to_internal(self, external: Json) -> RanaDataset:
        """Map external dataset representation to internal RanaDataset."""
        return RanaDataset(
            id=external["id"],
            title=external["resourceTitleObject"]["default"],
            resource_identifier=external["resourceIdentifier"],
            links=[self._map_link(x) for x in external["link"]],
        )


class RanaDatasetGateway:
    path = "datasets/{id}"
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
