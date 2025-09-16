from pydantic import AnyHttpUrl
from pytest import fixture, mark

from rana_process_sdk.domain.dataset import DatasetLink, RanaDataset, ResourceIdentifier


@fixture
def dataset() -> RanaDataset:
    return RanaDataset(
        id="dataset-123",
        title="Test Dataset",
        resource_identifier=[
            ResourceIdentifier(code="id-1", link=AnyHttpUrl("https://namespace/1")),
            ResourceIdentifier(code="id-2", link=AnyHttpUrl("https://namespace/2")),
        ],
        links=[
            DatasetLink(
                protocol="OGC:WCS",
                name="example",
                url=AnyHttpUrl("https://example.com/wcs"),
            ),
            DatasetLink(
                protocol="OGC:WFS",
                name="other",
                url=AnyHttpUrl("https://example.com/wfs"),
            ),
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


def test_get_wcs_link(dataset: RanaDataset) -> None:
    assert dataset.get_wcs_link() == dataset.links[0]


def test_get_wfs_link(dataset: RanaDataset) -> None:
    assert dataset.get_wfs_link() == dataset.links[1]


def test_get_wcs_link_no_links(dataset: RanaDataset) -> None:
    del dataset.links[0]
    assert dataset.get_wcs_link() is None


def test_get_wfs_link_no_links(dataset: RanaDataset) -> None:
    del dataset.links[1]
    assert dataset.get_wfs_link() is None
