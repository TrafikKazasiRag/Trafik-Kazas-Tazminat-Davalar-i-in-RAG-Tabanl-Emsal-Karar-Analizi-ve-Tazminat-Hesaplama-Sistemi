"""Config dosyasından bileşenleri kurar.

Yeni bir adaptör eklemek için: adapters/<tür>/<ad>.py yazın, içinde build(cfg) olsun,
config'de `type: <ad>` yazın. Başka hiçbir dosyaya dokunmanız gerekmez.
"""
import importlib
from pathlib import Path

import yaml

# config anahtarı -> adaptör paketi
ADAPTER_PACKAGES = {
    "chunker": "chunkers",
    "embedder": "embedders",
    "vector_store": "vector_stores",
    "lexical": "lexical",
    "reranker": "rerankers",
    "llm": "llms",
}


def load_config(path: str | Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_component(kind: str, cfg: dict):
    module = importlib.import_module(f"trafikrag.adapters.{ADAPTER_PACKAGES[kind]}.{cfg['type']}")
    return module.build(cfg)


def build_container(config_path: str | Path) -> dict:
    cfg = load_config(config_path)
    components = {k: build_component(k, cfg[k]) for k in ADAPTER_PACKAGES if k in cfg}
    return {"config": cfg, **components}
