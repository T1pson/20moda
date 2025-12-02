"""Assistive voice control app for accessibility-focused key binding.

This module provides a minimal desktop-oriented voice assistant skeleton
that can be configured to listen for short phrases (including numbers) and
press the corresponding keys for the active game or application. The design
emphasizes low-latency control, microphone flexibility, per-application
profiles, and clear helper text for users.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional


@dataclass
class CommandBinding:
    """Maps a spoken phrase to a keyboard key.

    Attributes:
        phrase: Voice trigger (e.g., "1", "fire", "jump").
        key: Keyboard key to press when the phrase is heard.
        hold_ms: How long to hold the key down before releasing.
        enabled: Whether the binding is currently active.
        allow_everywhere: If True, the binding works in every application even
            when the assistant is scoped to a specific program.
        hint: Short user-facing description shown in the UI.
    """

    phrase: str
    key: str
    hold_ms: int = 50
    enabled: bool = True
    allow_everywhere: bool = False
    hint: str = ""


@dataclass
class MicrophoneProfile:
    """Microphone-specific preferences for latency and monitoring."""

    device_index: Optional[int] = None
    sensitivity: float = 0.5
    auto_gain: bool = True
    monitor: bool = False
    noise_calibration_seconds: float = 1.0
    sidetone_enabled: bool = False


@dataclass
class AppProfile:
    """Groups command bindings for a target application or game."""

    name: str
    process_names: List[str] = field(default_factory=list)
    allow_everywhere: bool = False
    enabled: bool = True
    commands: List[CommandBinding] = field(default_factory=list)

    def binding_lookup(self) -> Dict[str, CommandBinding]:
        return {binding.phrase.lower(): binding for binding in self.commands if binding.enabled}


@dataclass
class AssistantSettings:
    """Top-level configuration for the assistant experience."""

    theme: str = "system"  # "light", "dark", or "system"
    minimize_to_tray: bool = True
    listen_everywhere: bool = False
    base_delay_ms: int = 0
    adaptive_latency: bool = True


@dataclass
class AssistiveVoiceConfig:
    """Full configuration persisted to disk."""

    settings: AssistantSettings = field(default_factory=AssistantSettings)
    microphone: MicrophoneProfile = field(default_factory=MicrophoneProfile)
    apps: List[AppProfile] = field(default_factory=list)

    def default_app(self) -> AppProfile:
        return AppProfile(
            name="Default",
            allow_everywhere=True,
            commands=[
                CommandBinding(phrase="1", key="1", hint="Нажать 1"),
                CommandBinding(phrase="2", key="2", hint="Нажать 2"),
                CommandBinding(phrase="прыжок", key="space", hint="Пробел для прыжка"),
            ],
        )


class AssistiveVoiceApp:
    """Runtime for the accessibility voice assistant.

    The class intentionally separates configuration, microphone handling, and
    key-sending so that UI layers (desktop app, tray menu, or CLI) can reuse the
    same core logic.
    """

    def __init__(self, config: AssistiveVoiceConfig, config_path: Path):
        self.config = config
        self.config_path = config_path

    # Persistence helpers -------------------------------------------------
    @classmethod
    def load(cls, path: Path) -> "AssistiveVoiceApp":
        if not path.exists():
            default_config = AssistiveVoiceConfig()
            default_config.apps.append(default_config.default_app())
            return cls(default_config, path)

        payload = json.loads(path.read_text(encoding="utf-8"))
        config = AssistiveVoiceConfig(
            settings=AssistantSettings(**payload.get("settings", {})),
            microphone=MicrophoneProfile(**payload.get("microphone", {})),
            apps=[cls._deserialize_app(app_data) for app_data in payload.get("apps", [])],
        )
        return cls(config, path)

    @staticmethod
    def _deserialize_app(payload: Dict) -> AppProfile:
        commands = [CommandBinding(**cmd) for cmd in payload.get("commands", [])]
        return AppProfile(
            name=payload.get("name", "Unnamed"),
            process_names=payload.get("process_names", []),
            allow_everywhere=payload.get("allow_everywhere", False),
            enabled=payload.get("enabled", True),
            commands=commands,
        )

    def save(self) -> None:
        payload = {
            "settings": asdict(self.config.settings),
            "microphone": asdict(self.config.microphone),
            "apps": [self._serialize_app(app) for app in self.config.apps],
        }
        self.config_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def _serialize_app(app: AppProfile) -> Dict:
        return {
            "name": app.name,
            "process_names": app.process_names,
            "allow_everywhere": app.allow_everywhere,
            "enabled": app.enabled,
            "commands": [asdict(cmd) for cmd in app.commands],
        }

    # Configuration editing -----------------------------------------------
    def set_theme(self, theme: str) -> None:
        if theme not in {"light", "dark", "system"}:
            raise ValueError("theme must be 'light', 'dark', or 'system'")
        self.config.settings.theme = theme

    def set_delay(self, milliseconds: int) -> None:
        self.config.settings.base_delay_ms = max(0, milliseconds)

    def toggle_tray(self, enabled: bool) -> None:
        self.config.settings.minimize_to_tray = enabled

    def ensure_app(self, name: str) -> AppProfile:
        for app in self.config.apps:
            if app.name == name:
                return app
        new_app = AppProfile(name=name)
        self.config.apps.append(new_app)
        return new_app

    def add_binding(self, app_name: str, binding: CommandBinding) -> None:
        app = self.ensure_app(app_name)
        app.commands.append(binding)

    # Listening and key injection -----------------------------------------
    def listen_forever(self, target_app: Optional[str] = None) -> None:
        """Starts the microphone listener and reacts to speech recognition results.

        Requires the optional SpeechRecognition and PyAudio dependencies. The
        function blocks the current thread; wrap it in a thread if needed for a
        GUI or tray context.
        """

        recognizer = self._build_recognizer()
        microphone = self._build_microphone()

        with microphone as source:
            if self.config.microphone.auto_gain:
                recognizer.adjust_for_ambient_noise(
                    source, duration=self.config.microphone.noise_calibration_seconds
                )

            while True:
                audio = recognizer.listen(source)
                phrase = self._transcribe(recognizer, audio)
                if phrase:
                    self._handle_phrase(phrase, target_app)

    def run_simulation(self, phrases: Iterable[str], target_app: Optional[str] = None) -> None:
        for phrase in phrases:
            self._handle_phrase(phrase, target_app)

    def _build_recognizer(self):
        import speech_recognition as sr

        recognizer = sr.Recognizer()
        recognizer.pause_threshold = 0.05 if self.config.settings.base_delay_ms == 0 else 0.1
        recognizer.energy_threshold = max(100, int(4000 * self.config.microphone.sensitivity))
        return recognizer

    def _build_microphone(self):
        import speech_recognition as sr

        return sr.Microphone(device_index=self.config.microphone.device_index)

    def _transcribe(self, recognizer, audio) -> Optional[str]:
        try:
            return recognizer.recognize_google(audio, language="ru-RU").lower()
        except Exception:
            return None

    def _handle_phrase(self, phrase: str, target_app: Optional[str]) -> None:
        binding = self._find_binding(phrase, target_app)
        if not binding:
            return

        if self.config.settings.base_delay_ms:
            time.sleep(self.config.settings.base_delay_ms / 1000)

        self._press_key(binding.key, hold_ms=binding.hold_ms)

    def _find_binding(self, phrase: str, target_app: Optional[str]) -> Optional[CommandBinding]:
        normalized = phrase.strip().lower()
        candidates: List[AppProfile] = []

        if target_app:
            for app in self.config.apps:
                if app.name == target_app and app.enabled:
                    candidates.append(app)
                    break

        if self.config.settings.listen_everywhere or not candidates:
            candidates.extend(app for app in self.config.apps if app.allow_everywhere and app.enabled)

        for app in candidates:
            binding = app.binding_lookup().get(normalized)
            if binding:
                return binding

        for app in self.config.apps:
            if app.enabled:
                binding = app.binding_lookup().get(normalized)
                if binding and binding.allow_everywhere:
                    return binding
        return None

    def _press_key(self, key: str, hold_ms: int = 50) -> None:
        from pynput.keyboard import Controller, Key

        controller = Controller()
        key_to_press = getattr(Key, key, key)
        controller.press(key_to_press)
        time.sleep(max(0, hold_ms) / 1000)
        controller.release(key_to_press)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Assistive voice control for configurable key binds")
    parser.add_argument("--config", type=Path, default=Path("voice_assistant.json"), help="Path to config file")
    parser.add_argument("--app", type=str, default=None, help="Target application profile")
    parser.add_argument(
        "--simulate",
        nargs="*",
        help="Run without microphone using the provided phrases (e.g. --simulate 1 прыжок)",
    )
    parser.add_argument("--delay", type=int, default=None, help="Override base delay in milliseconds")

    args = parser.parse_args()

    voice_app = AssistiveVoiceApp.load(args.config)
    if args.delay is not None:
        voice_app.set_delay(args.delay)
    voice_app.save()

    if args.simulate:
        voice_app.run_simulation(args.simulate, target_app=args.app)
    else:
        voice_app.listen_forever(target_app=args.app)
