from dataclasses import is_dataclass, asdict


def to_jsonable(x):
    if is_dataclass(x):
        return asdict(x)
    # fallback for non-dataclass objects
    return {k: getattr(x, k) for k in dir(x)
            if not k.startswith("_") and isinstance(getattr(x, k),
                                                    (str, int, float, bool, list, dict, type(None)))}