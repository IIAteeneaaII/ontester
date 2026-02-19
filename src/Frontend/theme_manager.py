# src/Frontend/theme_manager.py
import json
from pathlib import Path
import customtkinter as ctk


class ThemeManager:
    """
    ThemeManager único (sin __init__ duplicados).
    - Persiste 'appearance' (light/dark) en config_ui.json
    - Expone palette() con TODAS las llaves que usan tus vistas.
    """

    def __init__(self, config_path: str = "config_ui.json"):
        self.config_path = Path(config_path)
        self.mode = self._load_mode()  # "light" o "dark"

        self.colors = {
            "light": {
                "bg": "#E8F4F8",
                "panel": "#E9F5FF",
                "card": "#FFFFFF",
                "card_shadow": "#BFD3DD",
                "header": "#62A8E8",
                "deco1": "#A8DADC",
                "deco3": "#DFF1F2",
                "test_panel_bg": "#0E1A2A",
                "test_panel_border": "#243244",
                "test_panel_bg": "#D4E7D7",
                "test_panel_border": "#6B9080",
                "text": "#2C3E50",
                "muted": "#37474F",
                "border": "#8FA3B0",
                "entry_bg": "#FFFFFF",
                "entry_border": "#2C3E50",
                "primary": "#4EA5D9",
                "primary_hover": "#3B8CC2",
                "primary2": "#457B9D",
                "primary2_hover": "#1D3557",
                "danger": "#C1666B",
                "danger_hover": "#A4161A",
                "ok": "#48FF00", #22C55E
                "titulos": "#6B9080",
            },
            "dark": {
                "bg": "#0B1220",
                "panel": "#111827",
                "card": "#0F172A",
                "card_shadow": "#0A0F1A",
                "header": "#1F2937",
                "deco1": "#122338",
                "deco3": "#0E1A2A",
                "text": "#E5E7EB",
                "muted": "#9CA3AF",
                "border": "#243244",
                "entry_bg": "#0B1220",
                "entry_border": "#3B4A63",
                "primary": "#60A5FA",
                "primary_hover": "#3B82F6",
                "primary2": "#93C5FD",
                "primary2_hover": "#60A5FA",
                "danger": "#F87171",
                "danger_hover": "#EF4444",
                "ok": "#018A1E",
                "titulos": "#48FF00",
            },
        }

    def apply(self):
        ctk.set_appearance_mode(self.mode)
        ctk.set_default_color_theme("blue")

    def set_mode(self, mode: str):
        self.mode = (mode or "light").lower().strip()
        if self.mode not in ("light", "dark"):
            self.mode = "light"
        self.apply()
        self._save_mode()

    def toggle(self):
        self.set_mode("dark" if self.mode == "light" else "light")

    def palette(self) -> dict:
        return self.colors[self.mode]

    def _load_mode(self) -> str:
        if self.config_path.exists():
            try:
                data = json.loads(self.config_path.read_text(encoding="utf-8"))
                v = data.get("appearance")
                if v in ("light", "dark"):
                    return v
            except Exception:
                pass
        return "light"

    def _save_mode(self):
        try:
            self.config_path.write_text(
                json.dumps({"appearance": self.mode}, indent=2),
                encoding="utf-8",
            )
        except Exception:
            pass
