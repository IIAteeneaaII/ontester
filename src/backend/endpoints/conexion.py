from pathlib import Path

def load_users_txt(path: str | Path) -> dict[str, str]:
    users = {}
    path = Path(path)
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            k, v = line.split("=", 1)
            users[k.strip()] = v.strip()
    return users

def load_default_users() -> dict[str, str]:
    base_utils = Path(__file__).resolve().parents[1]   # -> backend
    txt_path = base_utils / "utils" / "empleados.txt"
    return load_users_txt(txt_path)
