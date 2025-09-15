from pydantic import AnyHttpUrl
from pytest import fixture, mark

from rana_process_sdk.domain.dataset import RanaDataset, ResourceIdentifier


@fixture
def dataset() -> RanaDataset:
    return RanaDataset(
        id="dataset-123",
        title="Test Dataset",
        resource_identifier=[
            ResourceIdentifier(code="id-1", link=AnyHttpUrl("https://namespace/1")),
            ResourceIdentifier(code="id-2", link=AnyHttpUrl("https://namespace/2")),
        ],
    )


@mark.parametrize(
    "namespace, expected_id",
    [
        (AnyHttpUrl("https://namespace/1"), "id-1"),
        (AnyHttpUrl("https://namespace/2"), "id-2"),
        (AnyHttpUrl("https://namespace/3"), None),
    ],
)
def test_get_id_for_namespace(
    dataset: RanaDataset, namespace: AnyHttpUrl, expected_id: str | None
) -> None:
    assert dataset.get_id_for_namespace(namespace) == expected_id
