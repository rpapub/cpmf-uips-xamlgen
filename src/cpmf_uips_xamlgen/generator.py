from typing import Any

SUPPORTED_CATALOG_SCHEMA_VERSION = "v0.2"


def generate(
    ast_doc: dict[str, Any],
    catalogs: list[dict[str, Any]],
    policy_file: str | None = None,
    verbose: bool = False,
) -> dict[str, Any] | None:
    """Generate XAML from an input AST document and activity catalogs.

    Returns an output envelope. Null-op stub — generation not yet implemented.

    Raises ValueError if any catalog does not match SUPPORTED_CATALOG_SCHEMA_VERSION.
    """
    for catalog in catalogs:
        version = catalog.get("schema", {}).get("version")
        if version != SUPPORTED_CATALOG_SCHEMA_VERSION:
            raise ValueError(
                f"Unsupported catalog schema version: {version!r}. "
                f"Expected {SUPPORTED_CATALOG_SCHEMA_VERSION!r}."
            )
    return None
