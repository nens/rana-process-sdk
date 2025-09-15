from typing import Annotated, Literal

from pydantic import WithJsonSchema

from ..widgets import UsingWidget, Widget

__all__ = [
    "Geometry",
    "Point",
    "LineString",
    "Polygon",
    "MultiPoint",
    "MultiLineString",
    "MultiPolygon",
    "GeometryCollection",
]


class DrawGeometryWidget(Widget):
    id: Literal["draw_geometry"] = "draw_geometry"


Geometry = Annotated[
    dict,
    WithJsonSchema({"$ref": "https://geojson.org/schema/Geometry.json"}),
    UsingWidget(DrawGeometryWidget()),
]

Point = Annotated[
    dict,
    WithJsonSchema({"$ref": "https://geojson.org/schema/Point.json"}),
    UsingWidget(DrawGeometryWidget()),
]

LineString = Annotated[
    dict,
    WithJsonSchema({"$ref": "https://geojson.org/schema/LineString.json"}),
    UsingWidget(DrawGeometryWidget()),
]

Polygon = Annotated[
    dict,
    WithJsonSchema({"$ref": "https://geojson.org/schema/Polygon.json"}),
    UsingWidget(DrawGeometryWidget()),
]

MultiPoint = Annotated[
    dict,
    WithJsonSchema({"$ref": "https://geojson.org/schema/MultiPoint.json"}),
    UsingWidget(DrawGeometryWidget()),
]

MultiLineString = Annotated[
    dict,
    WithJsonSchema({"$ref": "https://geojson.org/schema/MultiLineString.json"}),
    UsingWidget(DrawGeometryWidget()),
]

MultiPolygon = Annotated[
    dict,
    WithJsonSchema({"$ref": "https://geojson.org/schema/MultiPolygon.json"}),
    UsingWidget(DrawGeometryWidget()),
]

GeometryCollection = Annotated[
    dict,
    WithJsonSchema({"$ref": "https://geojson.org/schema/GeometryCollection.json"}),
    UsingWidget(DrawGeometryWidget()),
]
