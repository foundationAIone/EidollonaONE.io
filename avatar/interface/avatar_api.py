"""
Avatar Interface API: convenience helpers to create and interact with avatars.

- SAFE by default: no GPU/Unity/WebXR is touched unless explicitly allowed in config.
- Headless-friendly exporters: thumbnail PNG, pose PNG, and small animated GIF
  are generated with Pillow if available; otherwise tiny placeholders are written.
- Voice processor is optional; a local stub is used if the module is missing.

Expected layout:
  avatar/
    interface/avatar_api.py  (this file)
    avatar_system.py
    avatar_voice.py          (optional, for TTS/ASR stub)
    config/
      default_avatar_config.yaml
      platform_config.yaml
      animation_config.yaml
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# --- Optional deps (yaml, Pillow) guarded imports ---------------------------
try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None  # type: ignore

try:
    from PIL import Image, ImageDraw, ImageFont  # type: ignore
except Exception:  # pragma: no cover
    Image = ImageDraw = ImageFont = None  # type: ignore

# --- Local imports ----------------------------------------------------------
from avatar.avatar_system import (
    AvatarManager,
    AvatarPersonality,
    PERSONALITY_PRESETS,
)

# Voice processor: prefer relative import, fallback to absolute path
try:
    from ..avatar_voice import create_voice_processor  # type: ignore
except Exception:  # pragma: no cover
    try:
        from avatar.avatar_voice import create_voice_processor  # type: ignore
    except Exception:  # pragma: no cover

        def create_voice_processor(preset: str = "professional_female") -> Dict[str, Any]:
            """Minimal SAFE stub when voice pipeline is absent."""

            return {"ok": True, "preset": preset, "mode": "tone440_stub"}


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"


def _load_yaml(path: Path) -> Dict[str, Any]:
    """Safe YAML loader (returns empty dict if file or yaml unavailable)."""

    try:
        if yaml is None or not path.exists():
            return {}
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        return data or {}
    except Exception:
        return {}


def load_avatar_config() -> Dict[str, Any]:
    return _load_yaml(CONFIG_DIR / "default_avatar_config.yaml")


def load_platform_config() -> Dict[str, Any]:
    return _load_yaml(CONFIG_DIR / "platform_config.yaml")


def load_animation_config() -> Dict[str, Any]:
    return _load_yaml(CONFIG_DIR / "animation_config.yaml")


def apply_safe_platform_gates(cfg: Dict[str, Any]) -> None:
    """Apply SAFE gating flags from platform config to process env.

    Defaults are OFF unless explicitly enabled:
      allow_vr_ar: true
      rendering.backend in {unity, unreal, webxr}
      tracking.{hand_tracking|full_body_tracking|face_tracking}: true
    """

    tracking = cfg.get("tracking", {}) or {}
    rendering = cfg.get("rendering", {}) or {}

    allow_vr_ar = bool(cfg.get("allow_vr_ar", False))
    backend = str(rendering.get("backend", "")).strip().lower()
    vr_backends = {"webxr", "unity", "unreal"}

    vr_tracking_any = any(
        bool(tracking.get(k, False))
        for k in ("hand_tracking", "full_body_tracking", "face_tracking")
    )
    vr_ar_enabled = allow_vr_ar and backend in vr_backends and vr_tracking_any

    os.environ["EIDOLLONA_ENABLE_VR_AR"] = "1" if vr_ar_enabled else "0"
    os.environ["EIDOLLONA_ENABLE_WEBXR"] = "1" if (allow_vr_ar and backend == "webxr") else "0"
    os.environ["EIDOLLONA_ENABLE_AR_GLASSES"] = "1" if (allow_vr_ar and bool(cfg.get("ar_glasses", False))) else "0"
    os.environ["EIDOLLONA_ENABLE_FULL_BODY"] = "1" if (allow_vr_ar and bool(tracking.get("full_body_tracking", False))) else "0"
    os.environ["EIDOLLONA_ENABLE_HAND_TRACKING"] = "1" if (allow_vr_ar and bool(tracking.get("hand_tracking", False))) else "0"
    os.environ["EIDOLLONA_ENABLE_GPS"] = "1" if (allow_vr_ar and bool(cfg.get("gps", False))) else "0"
    os.environ["EIDOLLONA_ENABLE_VR_HEADSET"] = "1" if (allow_vr_ar and bool(cfg.get("vr_headset", False))) else "0"


# ---------------------------------------------------------------------------
# Avatar creation / interaction
# ---------------------------------------------------------------------------

def create_avatar_from_config(
    manager: Optional[AvatarManager] = None,
) -> Dict[str, Any]:
    """Create an avatar from YAML config + presets, activate, and ready a voice stub."""

    cfg = load_avatar_config()
    personality_cfg = cfg.get("personality", {}) or {}
    preset_name = str(personality_cfg.get("preset", "eidollona"))

    preset = PERSONALITY_PRESETS.get(preset_name)
    if preset is None:
        raise ValueError(f"Unknown personality preset: {preset_name}")

    overrides = dict(preset.__dict__)
    overrides.update({k: v for k, v in personality_cfg.items() if k != "preset"})
    personality = AvatarPersonality(**overrides)

    platform_cfg = load_platform_config()
    apply_safe_platform_gates(platform_cfg)

    m = manager or AvatarManager()
    avatar_id = m.create_avatar(preset_name, personality)
    m.activate_avatar(avatar_id)

    voice = create_voice_processor(cfg.get("voice", {}).get("preset", "professional_female"))

    return {
        "manager": m,
        "avatar_id": avatar_id,
        "voice": voice,
        "status": m.get_avatar_statuses().get(avatar_id, {}),
    }


async def interact(manager: AvatarManager, avatar_id: str, text: str) -> Dict[str, Any]:
    """Asynchronously send a conversational turn to the avatar through the manager."""

    data = {"type": "conversation", "intent": "question", "content": text}
    try:
        av = manager.active_avatars.get(avatar_id)
        if av and hasattr(av, "note_user_text"):
            av.note_user_text(text)
    except Exception:
        pass
    return await manager.interact_with_avatar(avatar_id, data)


def status_json(status: Dict[str, Any]) -> str:
    """JSON serializer tolerant of dataclasses nested in status dicts."""

    def default(o: Any) -> Any:
        try:
            return asdict(o)
        except Exception:
            return str(o)

    return json.dumps(status, default=default, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Live session helpers (SAFE no-op shims if avatar lacks methods)
# ---------------------------------------------------------------------------

def live_set_state(
    manager: AvatarManager,
    avatar_id: str,
    *,
    active: Optional[bool] = None,
    listening: Optional[bool] = None,
    muted: Optional[bool] = None,
) -> None:
    try:
        av = manager.active_avatars.get(avatar_id)
        if av and hasattr(av, "set_live_state"):
            av.set_live_state(active=active, listening=listening, muted=muted)
    except Exception:
        pass


def live_update_gaze(
    manager: AvatarManager,
    avatar_id: str,
    nx: float,
    ny: float,
    confidence: float = 1.0,
) -> None:
    try:
        av = manager.active_avatars.get(avatar_id)
        if av and hasattr(av, "update_gaze"):
            av.update_gaze(nx, ny, confidence)
    except Exception:
        pass


def live_note_bot(manager: AvatarManager, avatar_id: str, text: str) -> None:
    try:
        av = manager.active_avatars.get(avatar_id)
        if av and hasattr(av, "note_bot_text"):
            av.note_bot_text(text)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Headless-safe “artifact” exporters (Pillow optional)
# ---------------------------------------------------------------------------

def _load_font(size: int) -> Any:
    """Try truetype; fallback to default; returns a font-like object or None."""

    if ImageFont is None:
        return None
    try:
        return ImageFont.truetype("arial.ttf", size)
    except Exception:
        try:
            return ImageFont.truetype("DejaVuSans.ttf", size)
        except Exception:
            return ImageFont.load_default()


def _measure_text(draw: Any, text: str, font: Any) -> Tuple[int, int]:
    """Robust text measurement across Pillow versions."""

    if draw is None or font is None:
        return (len(text) * 8, 16)
    if hasattr(draw, "textbbox"):
        left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
        return right - left, bottom - top
    try:
        return draw.textsize(text, font=font)  # type: ignore[attr-defined]
    except Exception:
        return (len(text) * 8, 16)


def load_avatar(config_path: str) -> Dict[str, Any]:
    """Load high-level avatar config (YAML). Returns a minimal handle for exporters."""

    try:
        text = Path(config_path).read_text(encoding="utf-8")
        cfg = yaml.safe_load(text) if yaml else {}
    except Exception:
        cfg = {}
    return {"ok": True, "cfg": cfg or {}, "config_path": str(config_path)}


def export_avatar(avatar: Any, out_dir: str, kind: str = "thumbnail") -> str:
    """Export a thumbnail PNG (headless-safe). Uses Pillow when present; else writes a stub."""

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    p = out / f"eidollona_{kind}.png"

    if Image is None or ImageDraw is None:
        if not p.exists():
            p.write_bytes(b"artifact:thumbnail")
        return str(p)

    W, H = 640, 640
    im = Image.new("RGBA", (W, H), (11, 15, 20, 255))
    dr = ImageDraw.Draw(im)

    for i in range(0, 320, 8):
        c = int(30 + 50 * (1 - i / 320))
        dr.ellipse(
            [(W // 2 - i, H // 3 - i), (W // 2 + i, H // 3 + i)],
            outline=(c, c + 10, c + 20, 40),
        )

    gold = (212, 175, 55, 255)
    for k in range(0, 5):
        dr.rectangle([(10 + k, 10 + k), (W - 10 - k, H - 10 - k)], outline=gold)

    dr.ellipse(
        [(W // 2 - 70, H // 3 - 70), (W // 2 + 70, H // 3 + 70)],
        fill=(255, 236, 179, 90),
        outline=gold,
        width=3,
    )

    font_big = _load_font(40)
    font_sm = _load_font(20)

    title = "Eidollona"
    sub = f"Artifact: {kind}"
    tw, th = _measure_text(dr, title, font_big)
    dr.text(((W - tw) // 2, int(H * 0.62)), title, fill=(255, 215, 0, 255), font=font_big)
    sw, sh = _measure_text(dr, sub, font_sm)
    dr.text(((W - sw) // 2, int(H * 0.62) + th + 8), sub, fill=(230, 221, 212, 255), font=font_sm)

    im.save(p, format="PNG")
    return str(p)


def pose_avatar(pose: str, out_dir: str) -> str:
    """Export a simple pose PNG. Uses Pillow when present; else writes a stub."""

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    p = out / f"pose_{pose}.png"

    if Image is None or ImageDraw is None:
        if not p.exists():
            p.write_bytes(f"pose:{pose}".encode("utf-8"))
        return str(p)

    W, H = 640, 360
    im = Image.new("RGBA", (W, H), (12, 18, 26, 255))
    dr = ImageDraw.Draw(im)
    gold = (212, 175, 55, 255)

    dr.rectangle([(8, 8), (W - 8, H - 8)], outline=gold, width=3)
    dr.ellipse(
        [(W // 2 - 30, H // 2 - 60), (W // 2 + 30, H // 2)],
        fill=(40, 60, 92, 255),
        outline=(90, 120, 150, 255),
    )
    dr.rectangle(
        [(W // 2 - 20, H // 2), (W // 2 + 20, H // 2 + 70)],
        fill=(40, 60, 92, 255),
    )

    font = _load_font(22)
    txt = f"Pose: {pose}"
    tw, _ = _measure_text(dr, txt, font)
    dr.text(((W - tw) // 2, 16), txt, fill=(255, 215, 0, 255), font=font)

    im.save(p, format="PNG")
    return str(p)


def animate_avatar(clip: str, seconds: int, out_dir: str) -> str:
    """Export a small animated GIF representing the requested clip.

    Avoids external ffmpeg; suitable for SAFE/headless environments.
    """

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    p = out / f"anim_{clip}_{int(seconds)}s.gif"

    if Image is None or ImageDraw is None:
        if not p.exists():
            p.write_bytes(f"anim:{clip}:{seconds}s".encode("utf-8"))
        return str(p)

    W, H = 480, 270
    fps = 8
    total_frames = max(8, min(5 * fps, int(seconds * fps)))
    frames: List[Any] = []

    for i in range(total_frames):
        im = Image.new("RGBA", (W, H), (10, 14, 20, 255))
        dr = ImageDraw.Draw(im)
        dr.rectangle([(6, 6), (W - 6, H - 6)], outline=(212, 175, 55, 255), width=2)
        t = i / max(1, total_frames - 1)
        cx = int(W * (0.2 + 0.6 * t))
        cy = int(H * (0.45 + 0.1 * (0.5 - abs(t - 0.5)) * 2))
        dr.ellipse(
            [(cx - 20, cy - 20), (cx + 20, cy + 20)],
            fill=(255, 236, 179, 120),
            outline=(212, 175, 55, 255),
            width=2,
        )
        dr.text((12, 10), f"Clip: {clip}", fill=(230, 221, 212, 255))
        frames.append(im.convert("P"))

    if frames:
        frames[0].save(
            p,
            save_all=True,
            append_images=frames[1:],
            duration=int(1000 / fps),
            loop=0,
            optimize=True,
        )
    else:
        if not p.exists():
            p.write_bytes(b"gif")

    return str(p)


__all__ = [
    "create_avatar_from_config",
    "interact",
    "status_json",
    "live_set_state",
    "live_update_gaze",
    "live_note_bot",
    "load_avatar",
    "export_avatar",
    "pose_avatar",
    "animate_avatar",
    "load_avatar_config",
    "load_platform_config",
    "load_animation_config",
    "apply_safe_platform_gates",
]
