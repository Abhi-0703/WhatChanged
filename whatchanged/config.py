"""Configuration management for What Changed?."""

from dataclasses import dataclass, field
import os
from typing import Literal
from dotenv import load_dotenv

# Automatically load environment variables from .env file if present
load_dotenv()


@dataclass
class Settings:
    backend: Literal["ollama", "gemini"] = "ollama"
    ollama_model: str = "gemma4:e4b"
    ollama_host: str = "http://localhost:11434"
    gemini_api_key: str = ""
    gemini_model: str = "gemma-4-31b-it"
    interval: float = 5.0
    sensitivity: float = 2.0
    max_calls_per_min: int = 6
    image_mode: Literal["two_images", "side_by_side"] = "side_by_side"
    max_side: int = 768
    jpeg_quality: int = 85
    default_rules: list[str] = field(default_factory=lambda: ["notify me if the door is opened"])

    @classmethod
    def from_env(cls) -> "Settings":
        backend_env = os.getenv("WC_BACKEND", "ollama").lower()
        backend = "gemini" if backend_env == "gemini" else "ollama"

        image_mode_env = os.getenv("WC_IMAGE_MODE", "side_by_side").lower()
        image_mode = "two_images" if image_mode_env == "two_images" else "side_by_side"

        return cls(
            backend=backend,
            ollama_model=os.getenv("OLLAMA_MODEL", "gemma4:e4b"),
            ollama_host=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
            gemini_api_key=os.getenv("GEMINI_API_KEY", ""),
            gemini_model=os.getenv("GEMINI_MODEL", "gemma-4-31b-it"),
            interval=float(os.getenv("WC_INTERVAL", "5.0")),
            sensitivity=float(os.getenv("WC_SENSITIVITY", "2.0")),
            max_calls_per_min=int(os.getenv("WC_MAX_CALLS_PER_MIN", "6")),
            image_mode=image_mode,
            max_side=int(os.getenv("WC_MAX_SIDE", "768")),
            jpeg_quality=int(os.getenv("WC_JPEG_QUALITY", "85")),
        )
