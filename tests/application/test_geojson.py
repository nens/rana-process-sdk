from prefect.utilities.callables import parameter_schema
from pytest import mark

from rana_process_sdk import (
    Geometry,
    GeometryCollection,
    LineString,
    MultiLineString,
    MultiPoint,
    MultiPolygon,
    Point,
    Polygon,
)


@mark.parametrize(
    "_type,expected",
    [
        (Geometry, "https://geojson.org/schema/Geometry.json"),
        (Point, "https://geojson.org/schema/Point.json"),
        (LineString, "https://geojson.org/schema/LineString.json"),
        (Polygon, "https://geojson.org/schema/Polygon.json"),
        (MultiPoint, "https://geojson.org/schema/MultiPoint.json"),
        (MultiLineString, "https://geojson.org/schema/MultiLineString.json"),
        (MultiPolygon, "https://geojson.org/schema/MultiPolygon.json"),
        (GeometryCollection, "https://geojson.org/schema/GeometryCollection.json"),
    ],
)
def test_geometry_schema(_type: type, expected: str):
    def f(g: _type):
        pass

    schema = parameter_schema(f)

    assert schema.properties["g"] == {
        "$ref": expected,
        "position": 0,
        "title": "g",
        "rana_widget": {"id": "draw_geometry"},
    }
    assert schema.required == ["g"]
