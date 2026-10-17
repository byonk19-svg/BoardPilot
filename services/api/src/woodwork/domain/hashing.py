import hashlib
import json

from pydantic import BaseModel


def canonical_json(value) -> str:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def hash_json(value) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def resolved_hash(ledger: dict) -> str:
    return hash_json({k: v for k, v in ledger.items() if k != "resolved_sha256"})
