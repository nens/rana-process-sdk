from ..domain import Json

__all__ = ["is_optional", "unpack_optional", "lookup_ref", "maybe_follow_ref"]


def is_optional(prop: Json) -> bool:
    # given a 'property' element in a JSONSchema, return whether it is an optional field
    return (
        "anyOf" in prop
        and len(prop["anyOf"]) == 2
        and prop["anyOf"][1] == {"type": "null"}
    )


def unpack_optional(prop: Json) -> Json | None:
    # given a 'property' element in a JSONSchema, return the non-null option
    if not is_optional(prop):
        return None
    return prop["anyOf"][0]


def lookup_ref(schema: Json, ref: str) -> Json:
    _hash, definitions, name = ref.split("/")
    assert _hash == "#"
    return schema[definitions][name]


def maybe_follow_ref(schema: Json, prop: Json) -> Json:
    if "$ref" in prop:
        return lookup_ref(schema, prop["$ref"])
    return prop
