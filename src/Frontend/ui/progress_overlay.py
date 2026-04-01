from __future__ import annotations

import tkinter as tk
import customtkinter as ctk

from pathlib import Path
from PIL import Image, ImageTk


class FloatingProgressOverlay(ctk.CTkToplevel):
    def __init__(
        self,
        master,
        outline_image_path: str | Path,
        full_image_path: str | Path,
        width: int = 320,
        height: int = 260,
    ) -> None:
        super().__init__(master)

        self.outline_image_path = Path(outline_image_path)
        self.full_image_path = Path(full_image_path)

        self.overlay_width = width
        self.overlay_height = height
        self.image_width = width
        self.image_height = height - 55

        self._progress = 0
        self._status_text = "Preparando descarga..."
        self._photo = None

        self._build_window()
        self._load_assets()
        self._build_ui()
        self._position_window()
        self._redraw()

    def _build_window(self) -> None:
        self.overrideredirect(True)
        self.attributes("-topmost", True)

        # Fondo negro para usar transparentcolor en Windows
        self.config(bg="black")
        try:
            self.wm_attributes("-transparentcolor", "black")
        except tk.TclError:
            # Si alguna máquina no soporta esto, simplemente no será transparente
            pass

    def _load_assets(self) -> None:
        self.outline_image_original = Image.open(self.outline_image_path).convert("RGBA")
        self.full_image_original = Image.open(self.full_image_path).convert("RGBA")

        self.outline_image = self.outline_image_original.resize(
            (self.image_width, self.image_height),
            Image.LANCZOS,
        )
        self.full_image = self.full_image_original.resize(
            (self.image_width, self.image_height),
            Image.LANCZOS,
        )

    def _build_ui(self) -> None:
        self.container = tk.Frame(self, bg="black", bd=0, highlightthickness=0)
        self.container.pack(fill="both", expand=True)

        self.image_label = tk.Label(
            self.container,
            bg="black",
            bd=0,
            highlightthickness=0,
        )
        self.image_label.pack(padx=0, pady=(0, 0))

        self.text_label = tk.Label(
            self.container,
            text=self._status_text,
            font=("Segoe UI", 10, "bold"),
            fg="white",
            bg="black",
            bd=0,
            highlightthickness=0,
        )
        self.text_label.pack(pady=(0, 2))

        self.percent_label = tk.Label(
            self.container,
            text="0%",
            font=("Segoe UI", 11, "bold"),
            fg="#00b3ad",
            bg="black",
            bd=0,
            highlightthickness=0,
        )
        self.percent_label.pack()

    def _position_window(self) -> None:
        self.update_idletasks()

        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()

        x = screen_w - self.overlay_width - 30
        y = screen_h - self.overlay_height - 60

        self.geometry(f"{self.overlay_width}x{self.overlay_height}+{x}+{y}")

    def set_status(self, text: str) -> None:
        self._status_text = text
        self.text_label.configure(text=text)

    def set_progress(self, percent: int) -> None:
        percent = max(0, min(100, int(percent)))
        self._progress = percent
        self.percent_label.configure(text=f"{percent}%")
        self._redraw()

    def close_overlay(self) -> None:
        self.destroy()

    def _redraw(self) -> None:
        composed = self._compose_progress_image(self._progress)
        self._photo = ImageTk.PhotoImage(composed)
        self.image_label.configure(image=self._photo)

    def _compose_progress_image(self, percent: int) -> Image.Image:
        """
        Rellena de abajo hacia arriba usando la imagen completa,
        y deja encima la imagen de contorno.
        """
        base = Image.new("RGBA", (self.image_width, self.image_height), (0, 0, 0, 0))

        if percent > 0:
            reveal_height = int(self.image_height * (percent / 100.0))
            top_y = self.image_height - reveal_height

            colored_crop = self.full_image.crop((0, top_y, self.image_width, self.image_height))
            base.paste(colored_crop, (0, top_y), colored_crop)

        base.alpha_composite(self.outline_image)
        return base