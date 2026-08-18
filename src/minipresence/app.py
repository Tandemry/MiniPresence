from __future__ import annotations

import ctypes
import queue
import sys
import threading
import tkinter as tk
from pathlib import Path

import customtkinter as ctk
import pystray
from PIL import Image

from minipresence.config import load_settings, save_settings
from minipresence.detector import AppChoice, available_apps
from minipresence.monitor import PresenceMonitor
from minipresence.startup import is_startup_enabled, set_startup_enabled

ASSET_DIR = Path(__file__).with_name("assets")
APP_ICON_PATH = ASSET_DIR / "MiniPresence.png"
APP_ICON_ICO_PATH = ASSET_DIR / "MiniPresence.ico"
MP_LOGO_PATH = ASSET_DIR / "MP-text-icon.png"

BG = "#131316"
TITLE_BG = "#0f0f12"
SURFACE = "#1a1a1f"
SURFACE_DARK = "#111114"
SURFACE_HOVER = "#26262d"
BORDER = "#2c2c35"
BORDER_SUBTLE = "#222228"
TEXT = "#ededf0"
TEXT_SECONDARY = "#8a8a97"
TEXT_MUTED = "#5c5c6a"
TEXT_FAINT = "#3c3c48"
ACCENT = "#e07060"
ACCENT_HOVER = "#e88070"
GREEN = "#5cb87a"
AMBER = "#e8a84c"
RED = "#e85a5a"
GREY = "#52525e"
FONT = "Inter"

ctk.set_appearance_mode("dark")

if sys.platform == "win32":
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("MiniPresence.Desktop")
    except (AttributeError, OSError):
        pass


class MiniPresenceApp(ctk.CTk):
    def __init__(self, background: bool = False) -> None:
        super().__init__(fg_color=BG)
        self.withdraw()
        self.title("MiniPresence")
        self.geometry("480x450")
        self.resizable(False, False)
        self.overrideredirect(True)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self.settings = load_settings()
        self.events: queue.SimpleQueue[tuple[str, str]] = queue.SimpleQueue()
        self.app_discovery_results: queue.SimpleQueue[
            tuple[int, list[AppChoice]]
        ] = queue.SimpleQueue()
        self.monitor = PresenceMonitor(self._queue_status)
        self.tray_icon: pystray.Icon | None = None
        self.startup_enabled = tk.BooleanVar(value=is_startup_enabled())
        self.status = "ready"
        self.status_message = "Ready"
        self._drag_x = 0
        self._drag_y = 0
        self._overlay: ctk.CTkToplevel | None = None
        self._discovering_apps = False
        self._app_discovery_generation = 0

        self._app_icon = tk.PhotoImage(file=str(APP_ICON_PATH))
        self._apply_window_icon()
        with Image.open(MP_LOGO_PATH) as logo:
            logo_image = logo.convert("RGBA")
            self._logo_image = ctk.CTkImage(logo_image, logo_image, size=(36, 36))
            self._tiny_logo_image = ctk.CTkImage(logo_image, logo_image, size=(14, 14))

        self._build_shell()
        self._build_content()
        self._start_tray_icon()
        self.after(150, self._drain_events)
        self.after(30, self._apply_windows_rounding)

        if not background:
            self.after(60, self._show_window)
        if self.settings.has_target:
            self.after(350, self._start)
        elif background:
            self.after(350, self._show_window)

    def _build_shell(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        titlebar = ctk.CTkFrame(self, height=32, corner_radius=0, fg_color=TITLE_BG)
        titlebar.grid(row=0, column=0, sticky="ew")
        titlebar.grid_propagate(False)
        titlebar.grid_columnconfigure(1, weight=1)
        titlebar.bind("<ButtonPress-1>", self._start_drag)
        titlebar.bind("<B1-Motion>", self._drag_window)

        ctk.CTkLabel(titlebar, text="", image=self._tiny_logo_image, width=14).grid(
            row=0, column=0, padx=(12, 6)
        )
        title = ctk.CTkLabel(
            titlebar,
            text="MiniPresence",
            font=(FONT, 12),
            text_color="#6a6a78",
            anchor="w",
        )
        title.grid(row=0, column=1, sticky="ew")
        title.bind("<ButtonPress-1>", self._start_drag)
        title.bind("<B1-Motion>", self._drag_window)

        controls = ctk.CTkFrame(titlebar, fg_color="transparent", corner_radius=0)
        controls.grid(row=0, column=2, sticky="e")
        self._title_button(controls, "−", self._minimize, 0)
        self._title_button(controls, "□", lambda: None, 1)
        self._title_button(controls, "✕", self._on_close, 2, danger=True)

        self.content = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        self.content.grid(row=1, column=0, sticky="nsew")

    def _title_button(
        self,
        parent: ctk.CTkFrame,
        label: str,
        command: object,
        column: int,
        danger: bool = False,
    ) -> None:
        ctk.CTkButton(
            parent,
            text=label,
            command=command,
            width=46,
            height=32,
            corner_radius=0,
            border_width=0,
            fg_color="transparent",
            hover_color="#c42b1c" if danger else "#1d1d22",
            text_color="#5a5a68",
            font=("Segoe UI", 13),
        ).grid(row=0, column=column)

    def _build_content(self) -> None:
        for child in self.content.winfo_children():
            child.destroy()
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(6, weight=1)

        header = ctk.CTkFrame(self.content, fg_color="transparent", height=36)
        header.grid(row=0, column=0, sticky="ew", padx=22, pady=(20, 0))
        header.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(header, text="", image=self._logo_image, width=36, height=36).grid(
            row=0, column=0, rowspan=2, padx=(0, 10)
        )
        ctk.CTkLabel(
            header,
            text="MiniPresence",
            font=(FONT, 15, "bold"),
            text_color=TEXT,
            anchor="w",
        ).grid(row=0, column=1, sticky="sw")
        ctk.CTkLabel(
            header,
            text="Show any app on Discord.",
            font=(FONT, 12),
            text_color=TEXT_MUTED,
            anchor="w",
        ).grid(row=1, column=1, sticky="nw")

        ctk.CTkFrame(self.content, height=1, corner_radius=0, fg_color="#1e1e24").grid(
            row=1, column=0, sticky="ew", padx=22, pady=(16, 0)
        )
        self._build_app_card()
        self._build_status_controls()
        self._build_startup_card()
        ctk.CTkLabel(
            self.content,
            text="Keep Discord or Discord Canary open.",
            font=(FONT, 11),
            text_color=TEXT_FAINT,
        ).grid(row=6, column=0, sticky="s", pady=(0, 14))

    def _build_app_card(self) -> None:
        card = ctk.CTkFrame(
            self.content,
            fg_color=SURFACE,
            border_color="#252530",
            border_width=1,
            corner_radius=10,
        )
        card.grid(row=2, column=0, sticky="ew", padx=22, pady=(16, 0))
        if not self.settings.has_target:
            card.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(
                card,
                text="＋",
                width=44,
                height=44,
                corner_radius=10,
                fg_color=SURFACE_DARK,
                text_color="#3a3a46",
                font=(FONT, 18),
            ).grid(row=0, column=0, pady=(12, 6))
            ctk.CTkLabel(
                card,
                text="No app selected",
                font=(FONT, 13),
                text_color="#6a6a78",
            ).grid(row=1, column=0)
            ctk.CTkLabel(
                card,
                text="Choose an open app to share on Discord",
                font=(FONT, 11),
                text_color=TEXT_FAINT,
            ).grid(row=2, column=0, pady=(1, 7))
            self._button(card, "Choose app", self._choose_app, small=True).grid(
                row=3, column=0, pady=(0, 12)
            )
            return

        card.grid_columnconfigure(1, weight=1)
        glyph = "🌐" if self.settings.target_type == "pwa" else "◆"
        ctk.CTkLabel(
            card,
            text=glyph,
            width=40,
            height=40,
            corner_radius=8,
            fg_color=SURFACE_DARK,
            text_color=TEXT_SECONDARY,
            font=("Segoe UI Emoji", 18),
        ).grid(row=0, column=0, rowspan=2, padx=(16, 12), pady=14)
        ctk.CTkLabel(
            card,
            text=self.settings.app_name,
            font=(FONT, 14, "bold"),
            text_color=TEXT,
            anchor="w",
        ).grid(row=0, column=1, sticky="sw", pady=(14, 0))
        app_type = (
            "Desktop app"
            if self.settings.target_type == "process"
            else f"{self.settings.browser} web app"
        )
        ctk.CTkLabel(
            card,
            text=app_type,
            font=(FONT, 11),
            text_color=TEXT_MUTED,
            anchor="w",
        ).grid(row=1, column=1, sticky="nw", pady=(1, 14))
        actions = ctk.CTkFrame(card, fg_color="transparent")
        actions.grid(row=0, column=2, rowspan=2, padx=(10, 14), pady=10)
        self._button(actions, "Change app", self._choose_app, small=True).grid(row=0, column=0)
        self._button(
            actions, "Customize status", self._customize, small=True, variant="ghost"
        ).grid(row=1, column=0, pady=(3, 0))

    def _build_status_controls(self) -> None:
        row = ctk.CTkFrame(self.content, fg_color="transparent")
        row.grid(row=3, column=0, sticky="ew", padx=22, pady=(16, 0))
        row.grid_columnconfigure(0, weight=1)
        color = {"active": GREEN, "watching": AMBER, "error": RED}.get(self.status, GREY)
        pill = ctk.CTkFrame(
            row,
            fg_color={
                "active": "#18251d",
                "watching": "#292219",
                "error": "#29191b",
            }.get(self.status, SURFACE),
            border_color={GREEN: "#294f35", AMBER: "#59421f", RED: "#5b2929", GREY: BORDER}[
                color
            ],
            border_width=1,
            corner_radius=20,
            height=28,
        )
        pill.grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(pill, text="●", width=14, font=(FONT, 11), text_color=color).pack(
            side="left", padx=(7, 1)
        )
        ctk.CTkLabel(
            pill,
            text=self.status_message,
            font=(FONT, 12),
            text_color=color,
        ).pack(side="left", padx=(0, 10), pady=4)

        actions = ctk.CTkFrame(row, fg_color="transparent")
        actions.grid(row=0, column=1)
        self.stop_button = self._button(
            actions, "Stop", self._stop, variant="secondary", enabled=self.monitor.running
        )
        self.stop_button.grid(row=0, column=0, padx=(0, 8))
        self.start_button = self._button(
            actions,
            "▶  Start",
            self._start,
            enabled=self.settings.has_target and not self.monitor.running,
        )
        self.start_button.grid(row=0, column=1)

    def _build_startup_card(self) -> None:
        card = ctk.CTkFrame(
            self.content,
            fg_color=SURFACE,
            border_color=BORDER_SUBTLE,
            border_width=1,
            corner_radius=8,
        )
        card.grid(row=4, column=0, sticky="ew", padx=22, pady=(16, 0))
        card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            card,
            text="Start with Windows",
            font=(FONT, 13),
            text_color="#c0c0cc",
            anchor="w",
        ).grid(row=0, column=0, sticky="sw", padx=14, pady=(9, 0))
        ctk.CTkLabel(
            card,
            text="Launch MiniPresence when you log in",
            font=(FONT, 11),
            text_color="#4a4a58",
            anchor="w",
        ).grid(row=1, column=0, sticky="nw", padx=14, pady=(0, 9))
        ctk.CTkSwitch(
            card,
            text="",
            switch_width=36,
            switch_height=20,
            variable=self.startup_enabled,
            command=self._toggle_startup,
            fg_color="#2c2c38",
            progress_color=ACCENT,
            button_color="#ffffff",
            button_hover_color="#ffffff",
        ).grid(row=0, column=1, rowspan=2, padx=14)

    def _button(
        self,
        parent: ctk.CTkFrame,
        text: str,
        command: object,
        *,
        variant: str = "primary",
        small: bool = False,
        enabled: bool = True,
    ) -> ctk.CTkButton:
        palette = {
            "primary": (ACCENT, ACCENT_HOVER, "#ffffff", ACCENT),
            "secondary": ("#242428", "#2e2e38", "#a0a0b0", BORDER),
            "ghost": ("transparent", "#2a2a32", "#7a7a88", SURFACE),
        }
        fg, hover, text_color, border = palette[variant]
        return ctk.CTkButton(
            parent,
            text=text,
            command=command,
            height=28 if small else 34,
            width=0,
            corner_radius=6,
            border_width=1 if variant == "secondary" else 0,
            border_color=border,
            fg_color=fg,
            hover_color=hover,
            text_color=text_color,
            text_color_disabled="#53535e",
            font=(FONT, 12 if small else 13),
            state="normal" if enabled else "disabled",
        )

    def _choose_app(self) -> None:
        if self._discovering_apps:
            return
        self._discovering_apps = True
        self._app_discovery_generation += 1
        request_id = self._app_discovery_generation
        self._show_app_loading()

        def discover() -> None:
            try:
                apps = available_apps()
            except Exception:
                apps = []
            self.app_discovery_results.put((request_id, apps))

        threading.Thread(target=discover, name="app-discovery", daemon=True).start()

    def _show_app_loading(self) -> None:
        overlay = self._show_overlay(height=180)
        card = ctk.CTkFrame(
            overlay,
            width=440,
            height=140,
            fg_color=SURFACE,
            border_color=BORDER,
            border_width=1,
            corner_radius=12,
        )
        card.place(relx=0.5, rely=0.5, anchor="center")
        card.grid_propagate(False)
        ctk.CTkLabel(
            card,
            text="Finding open apps…",
            font=(FONT, 14, "bold"),
            text_color=TEXT,
        ).pack(pady=(34, 5))
        ctk.CTkLabel(
            card,
            text="This should only take a moment.",
            font=(FONT, 11),
            text_color=TEXT_MUTED,
        ).pack()

    def _show_overlay(self, *, height: int = 382) -> ctk.CTkToplevel:
        self._close_overlay()
        self.update_idletasks()
        width = 470
        x = self.winfo_x() + (self.winfo_width() - width) // 2
        y = self.winfo_y() + (self.winfo_height() - height) // 2
        overlay = ctk.CTkToplevel(self, fg_color="#0a0a0d")
        overlay.withdraw()
        overlay.overrideredirect(True)
        overlay.geometry(f"{width}x{height}+{x}+{y}")
        overlay.resizable(False, False)
        overlay.transient(self)
        overlay.protocol("WM_DELETE_WINDOW", self._close_overlay)
        self._overlay = overlay
        overlay.deiconify()
        overlay.lift()
        overlay.grab_set()
        return overlay

    def _show_app_picker(self, apps: list[AppChoice]) -> None:
        overlay = self._show_overlay()
        card = ctk.CTkFrame(
            overlay,
            width=470,
            height=382,
            fg_color=SURFACE,
            border_color=BORDER,
            border_width=1,
            corner_radius=12,
        )
        card.place(relx=0.5, rely=0.5, anchor="center")
        card.grid_propagate(False)
        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(
            card,
            text="Choose an open app",
            font=(FONT, 14, "bold"),
            text_color=TEXT,
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=20, pady=(16, 10))
        search_value = tk.StringVar()
        search = ctk.CTkEntry(
            card,
            textvariable=search_value,
            placeholder_text="Search apps…",
            height=34,
            corner_radius=6,
            border_width=1,
            fg_color=BG,
            border_color=BORDER,
            text_color=TEXT,
            placeholder_text_color=TEXT_MUTED,
            font=(FONT, 13),
        )
        search.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 6))
        list_frame = ctk.CTkScrollableFrame(
            card,
            fg_color="transparent",
            corner_radius=0,
            scrollbar_button_color=BORDER,
            scrollbar_button_hover_color="#3a3a44",
        )
        list_frame.grid(row=2, column=0, sticky="nsew", padx=12, pady=8)
        list_frame.grid_columnconfigure(0, weight=1)

        selected: list[AppChoice | None] = [self._matching_choice(apps)]
        row_widgets: list[ctk.CTkButton] = []
        footer = ctk.CTkFrame(card, fg_color=SURFACE, corner_radius=0)
        footer.grid(row=3, column=0, sticky="ew", padx=16, pady=12)
        footer.grid_columnconfigure(0, weight=1)
        choose_button = self._button(
            footer,
            "Choose",
            lambda: self._confirm_app_choice(selected[0]),
            enabled=selected[0] is not None,
        )
        choose_button.grid(row=0, column=2)
        self._button(footer, "Cancel", self._close_overlay, variant="secondary").grid(
            row=0, column=1, padx=(0, 8)
        )

        def render(_value: str = "") -> None:
            for widget in list_frame.winfo_children():
                widget.destroy()
            row_widgets.clear()
            query = search_value.get().strip().casefold()
            filtered = [item for item in apps if query in item.name.casefold()]
            if not filtered:
                ctk.CTkLabel(
                    list_frame,
                    text="⌕\n\nNo open apps match your search.\nOpen an app and try again.",
                    font=(FONT, 12),
                    text_color=TEXT_MUTED,
                    justify="center",
                ).grid(row=0, column=0, pady=40)
                return

            def select(item: AppChoice, button: ctk.CTkButton) -> None:
                selected[0] = item
                for candidate in row_widgets:
                    candidate.configure(fg_color="transparent", border_width=0, text_color=TEXT)
                button.configure(
                    fg_color="#34201f",
                    border_width=1,
                    border_color="#683a35",
                    text_color=ACCENT,
                )
                choose_button.configure(state="normal")

            for index, item in enumerate(filtered):
                is_selected = self._same_choice(item, selected[0])
                glyph = "🌐" if item.target_type == "pwa" else "◆"
                label = f"{glyph}    {item.name}\n       {item.type_label}"
                button = ctk.CTkButton(
                    list_frame,
                    text=label,
                    anchor="w",
                    height=48,
                    corner_radius=6,
                    border_width=1 if is_selected else 0,
                    border_color="#683a35",
                    fg_color="#34201f" if is_selected else "transparent",
                    hover_color=SURFACE_HOVER,
                    text_color=ACCENT if is_selected else TEXT,
                    font=(FONT, 12),
                )
                button.configure(command=lambda item=item, button=button: select(item, button))
                button.grid(row=index, column=0, sticky="ew", pady=1)
                row_widgets.append(button)

        search_value.trace_add("write", lambda *_args: render())
        render()
        search.focus_set()

    def _matching_choice(self, apps: list[AppChoice]) -> AppChoice | None:
        identifier = (
            self.settings.process_name
            if self.settings.target_type == "process"
            else self.settings.pwa_app_id
        )
        return next(
            (
                item
                for item in apps
                if item.target_type == self.settings.target_type
                and item.identifier.casefold() == identifier.casefold()
            ),
            None,
        )

    @staticmethod
    def _same_choice(left: AppChoice, right: AppChoice | None) -> bool:
        return bool(
            right
            and left.target_type == right.target_type
            and left.identifier.casefold() == right.identifier.casefold()
        )

    def _confirm_app_choice(self, app: AppChoice | None) -> None:
        if app is not None:
            self._close_overlay()
            self._select_app(app)

    def _select_app(self, app: AppChoice) -> None:
        was_running = self.monitor.running
        if was_running:
            self.monitor.stop()
        self.settings.app_name = app.name
        self.settings.target_type = app.target_type
        if app.target_type == "process":
            self.settings.process_name = app.identifier
            self.settings.pwa_app_id = ""
            self.settings.browser = "Any"
        else:
            self.settings.process_name = ""
            self.settings.pwa_app_id = app.identifier
            self.settings.browser = app.browser
        self.settings.details = "Using {app_name}"
        self.settings.state = "App open"
        save_settings(self.settings)
        self.status = "ready"
        self.status_message = "Ready"
        self._build_content()
        if was_running:
            self._start()

    def _customize(self) -> None:
        if not self.settings.has_target:
            self._choose_app()
            return
        overlay = self._show_overlay(height=418)
        card = ctk.CTkFrame(
            overlay,
            width=440,
            height=400,
            fg_color=SURFACE,
            border_color=BORDER,
            border_width=1,
            corner_radius=12,
        )
        card.place(relx=0.5, rely=0.5, anchor="center")
        card.grid_propagate(False)
        card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            card,
            text="Customize status",
            font=(FONT, 14, "bold"),
            text_color=TEXT,
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=20, pady=(16, 12))

        details_value = tk.StringVar(value=self.settings.details)
        self._field(card, "First line", 1, details_value)
        ctk.CTkLabel(
            card,
            text="{app_name} inserts the selected app's name",
            font=(FONT, 11),
            text_color=TEXT_MUTED,
            anchor="w",
        ).grid(row=2, column=0, sticky="ew", padx=20, pady=(4, 7))
        state_value = tk.StringVar(value=self.settings.state)
        self._field(card, "Second line", 3, state_value)
        ctk.CTkLabel(
            card,
            text="PREVIEW",
            font=(FONT, 11, "bold"),
            text_color=TEXT_MUTED,
            anchor="w",
        ).grid(row=4, column=0, sticky="ew", padx=20, pady=(12, 6))
        preview = ctk.CTkLabel(
            card,
            text="",
            justify="left",
            anchor="w",
            height=62,
            corner_radius=8,
            fg_color=SURFACE_DARK,
            text_color=TEXT_SECONDARY,
            font=(FONT, 12),
        )
        preview.grid(row=5, column=0, sticky="ew", padx=20)

        def update_preview(_value: str = "") -> None:
            line1 = details_value.get().replace("{app_name}", self.settings.app_name)
            line2 = state_value.get().replace("{app_name}", self.settings.app_name)
            preview.configure(text=f"   MINIPRESENCE\n   {line1}\n   {line2}")

        details_value.trace_add("write", lambda *_args: update_preview())
        state_value.trace_add("write", lambda *_args: update_preview())
        update_preview()
        footer = ctk.CTkFrame(card, fg_color="transparent")
        footer.grid(row=6, column=0, sticky="e", padx=20, pady=14)

        def save() -> None:
            self.settings.details = details_value.get().strip() or "Using {app_name}"
            self.settings.state = state_value.get().strip() or "App open"
            save_settings(self.settings)
            self._close_overlay()

        self._button(footer, "Cancel", self._close_overlay, variant="secondary").grid(
            row=0, column=0, padx=(0, 8)
        )
        self._button(footer, "Save", save).grid(row=0, column=1)

    def _field(
        self,
        parent: ctk.CTkFrame,
        label: str,
        row: int,
        value: tk.StringVar,
    ) -> ctk.CTkEntry:
        wrapper = ctk.CTkFrame(parent, fg_color="transparent")
        wrapper.grid(row=row, column=0, sticky="ew", padx=20)
        wrapper.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            wrapper,
            text=label,
            font=(FONT, 12),
            text_color=TEXT_SECONDARY,
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", pady=(0, 5))
        entry = ctk.CTkEntry(
            wrapper,
            textvariable=value,
            height=34,
            corner_radius=6,
            border_color=BORDER,
            fg_color=BG,
            text_color=TEXT,
            font=(FONT, 13),
        )
        entry.grid(row=1, column=0, sticky="ew")
        return entry

    def _close_overlay(self) -> None:
        if self._overlay is not None:
            try:
                self._overlay.grab_release()
            except tk.TclError:
                pass
            self._overlay.destroy()
            self._overlay = None
            self._build_content()

    def _start(self) -> None:
        if self.monitor.running:
            return
        if not self.settings.has_target:
            self._choose_app()
            return
        save_settings(self.settings)
        self.monitor.start(self.settings)
        self.status = "watching"
        self.status_message = f"Waiting for {self.settings.app_name}"
        self._build_content()

    def _stop(self) -> None:
        self.monitor.stop()
        self.status = "ready"
        self.status_message = "Ready"
        self._build_content()

    def _toggle_startup(self) -> None:
        enabled = self.startup_enabled.get()
        try:
            set_startup_enabled(enabled)
        except OSError as exc:
            self.startup_enabled.set(not enabled)
            self.status = "error"
            self.status_message = f"Startup setting failed: {exc}"
            self._build_content()
            return
        self.settings.start_minimized = enabled
        save_settings(self.settings)

    @staticmethod
    def _tray_image() -> Image.Image:
        with Image.open(APP_ICON_PATH) as image:
            return image.convert("RGBA").resize((64, 64), Image.Resampling.LANCZOS)

    def _start_tray_icon(self) -> None:
        menu = pystray.Menu(
            pystray.MenuItem("Open MiniPresence", self._tray_open, default=True),
            pystray.MenuItem("Quit", self._tray_quit),
        )
        self.tray_icon = pystray.Icon(
            "MiniPresence", self._tray_image(), "MiniPresence", menu=menu
        )
        try:
            self.tray_icon.run_detached()
        except Exception:
            self.tray_icon = None

    def _tray_open(self, _icon: pystray.Icon, _item: pystray.MenuItem) -> None:
        self.after(0, self._show_window)

    def _tray_quit(self, _icon: pystray.Icon, _item: pystray.MenuItem) -> None:
        self.after(0, self._quit)

    def _queue_status(self, status: str, message: str) -> None:
        self.events.put((status, message))

    def _drain_events(self) -> None:
        changed = False
        while not self.events.empty():
            self.status, self.status_message = self.events.get()
            changed = True
        if changed:
            self._build_content()
        while not self.app_discovery_results.empty():
            request_id, apps = self.app_discovery_results.get()
            if request_id != self._app_discovery_generation:
                continue
            self._discovering_apps = False
            self._close_overlay()
            self._show_app_picker(apps)
        self.after(150, self._drain_events)

    def _start_drag(self, event: tk.Event) -> None:
        self._drag_x = event.x_root - self.winfo_x()
        self._drag_y = event.y_root - self.winfo_y()

    def _drag_window(self, event: tk.Event) -> None:
        self.geometry(f"+{event.x_root - self._drag_x}+{event.y_root - self._drag_y}")

    def _minimize(self) -> None:
        self.overrideredirect(False)
        self.iconify()
        self.bind("<Map>", self._restore_borderless, add="+")

    def _restore_borderless(self, _event: tk.Event) -> None:
        def restore() -> None:
            self.overrideredirect(True)
            self._set_taskbar_style()
            self._apply_window_icon()

        self.after(10, restore)

    def _show_window(self) -> None:
        self.overrideredirect(True)
        self.update_idletasks()
        self._set_taskbar_style()
        self.deiconify()
        self._apply_window_icon()
        self.lift()
        self.focus_force()

    def _apply_window_icon(self) -> None:
        self.iconphoto(True, self._app_icon)
        if sys.platform == "win32":
            try:
                self.iconbitmap(str(APP_ICON_ICO_PATH))
            except tk.TclError:
                pass

    def _set_taskbar_style(self) -> None:
        if sys.platform != "win32":
            return
        try:
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
            current = ctypes.windll.user32.GetWindowLongW(hwnd, -20)
            app_window = 0x00040000
            tool_window = 0x00000080
            ctypes.windll.user32.SetWindowLongW(
                hwnd,
                -20,
                (current & ~tool_window) | app_window,
            )
        except (AttributeError, OSError):
            pass

    def _apply_windows_rounding(self) -> None:
        if sys.platform != "win32":
            return
        try:
            self.update_idletasks()
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
            preference = ctypes.c_int(2)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, 33, ctypes.byref(preference), ctypes.sizeof(preference)
            )
        except (AttributeError, OSError):
            pass

    def _on_close(self) -> None:
        self._app_discovery_generation += 1
        self._discovering_apps = False
        self._close_overlay()
        if self.monitor.running or self.startup_enabled.get():
            self.withdraw()
        else:
            self._quit()

    def _quit(self) -> None:
        self._app_discovery_generation += 1
        self._discovering_apps = False
        self.monitor.stop()
        if self.tray_icon is not None:
            self.tray_icon.stop()
            self.tray_icon = None
        self.destroy()


def main() -> None:
    MiniPresenceApp(background="--background" in sys.argv[1:]).mainloop()


if __name__ == "__main__":
    main()
