"""One asset contract shared with the core registry; no tensor imports here."""

from app.ml_contracts import (  # noqa: F401
    ARCHITECTURE,
    LABELS,
    MAX_WEIGHTS,
    PREPROCESSING,
    AssetError,
    bundle,
    controlled_file,
    digest,
    read_json,
    vocabulary,
)
