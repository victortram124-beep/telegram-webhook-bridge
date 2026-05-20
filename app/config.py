"""Integration config loaded from integrations.yaml."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml


_ENV_REF = re.compile(r"\$\{([A-Z0-9_]+)\}")


def _expand_env(value):
    if isinstance(value, str):
        return _ENV_REF.sub(lambda m: os.environ.get(m.group(1), ""), value)
    if isinstance(value, dict):
        return {k: _expand_env(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_expand_env(x) for x in value]
    return value


@dataclass
class Integration:
    name: str
    path: str
    telegram_chat_id: str
    signature_method: str = "none"   # none | hmac | github | stripe
    signing_secret: Optional[str] = None
    templates: dict = field(default_factory=dict)
    events_allowlist: list[str] = field(default_factory=list)
    default_template: str = "*{name}* webhook received\n```\n{summary}\n```"


def load_integrations(path: str = "integrations.yaml") -> list[Integration]:
    if not Path(path).exists():
        raise FileNotFoundError(f"{path} not found — copy integrations.example.yaml first")
    with open(path) as f:
        raw = yaml.safe_load(f)
    raw = _expand_env(raw)
    return [Integration(**i) for i in raw.get("integrations", [])]
