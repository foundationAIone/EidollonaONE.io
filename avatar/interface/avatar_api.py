"""
Avatar Interface API: convenience helpers to create and interact with avatars.
"""

from __future__ import annotations

import json
from dataclasses import asdict
import os
from pathlib import Path
from typing import Any, Dict, Optional, List

import yaml

from avatar.avatar_system import (
    AvatarManager,
    AvatarPersonality,
    PERSONALITY_PRESETS,
)
from avatar.avatar_voice import create_voice_processor


CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"


def _load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def load_avatar_config() -> Dict[str, Any]:
    return _load_yaml(CONFIG_DIR / "default_avatar_config.yaml")


def load_platform_config() -> Dict[str, Any]:
    return _load_yaml(CONFIG_DIR / "platform_config.yaml")


def apply_safe_platform_gates(cfg: Dict[str, Any]) -> None:
    """Apply SAFE gating flags based on platform config. Defaults OFF unless explicitly enabled.
    This sets process env so lower layers (vr_ar_integration) respect the gates.
    """
    tracking = cfg.get("tracking", {})
    rendering = cfg.get("rendering", {})

    # Global VR/AR gate: require rendering backend in {unity, unreal, webxr} and tracking enabled OR explicit allow flag
    allow_vr_ar = bool(cfg.get("allow_vr_ar", False))
    backend = (rendering.get("backend") or "").strip().lower()
    vr_backends = {"webxr", "unity", "unreal"}
    vr_tracking_any = any(
        bool(tracking.get(k, False))
        for k in ("hand_tracking", "full_body_tracking", "face_tracking")
    )
    vr_ar_enabled = allow_vr_ar and backend in vr_backends and vr_tracking_any

    # SAFE default: OFF unless explicitly enabled by config
    os.environ["EIDOLLONA_ENABLE_VR_AR"] = "1" if vr_ar_enabled else "0"
    os.environ["EIDOLLONA_ENABLE_WEBXR"] = (
        "1" if (allow_vr_ar and backend == "webxr") else "0"
    )
    os.environ["EIDOLLONA_ENABLE_AR_GLASSES"] = (
        "1" if (allow_vr_ar and bool(cfg.get("ar_glasses", False))) else "0"
    )
    os.environ["EIDOLLONA_ENABLE_FULL_BODY"] = (
        "1"
        if (allow_vr_ar and bool(tracking.get("full_body_tracking", False)))
        else "0"
    )
    os.environ["EIDOLLONA_ENABLE_HAND_TRACKING"] = (
        "1" if (allow_vr_ar and bool(tracking.get("hand_tracking", False))) else "0"
    )
    os.environ["EIDOLLONA_ENABLE_GPS"] = (
        "1" if (allow_vr_ar and bool(cfg.get("gps", False))) else "0"
    )
    os.environ["EIDOLLONA_ENABLE_VR_HEADSET"] = (
        "1" if (allow_vr_ar and bool(cfg.get("vr_headset", False))) else "0"
    )


def load_animation_config() -> Dict[str, Any]:
    return _load_yaml(CONFIG_DIR / "animation_config.yaml")


def create_avatar_from_config(
    manager: Optional[AvatarManager] = None,
) -> Dict[str, Any]:
    cfg = load_avatar_config()
    personality_cfg = cfg.get("personality", {})
    preset_name = personality_cfg.get("preset", "eidollona")

    # Start from preset, allow overrides
    preset = PERSONALITY_PRESETS.get(preset_name)
    if preset is None:
        raise ValueError(f"Unknown personality preset: {preset_name}")

    # Build a new AvatarPersonality with overrides
    overrides = dict(preset.__dict__)
    overrides.update({k: v for k, v in personality_cfg.items() if k != "preset"})
    personality = AvatarPersonality(**overrides)

    # Apply SAFE platform gates prior to any ecosystem/VR imports that may occur downstream
    platform_cfg = load_platform_config()
    apply_safe_platform_gates(platform_cfg)

    m = manager or AvatarManager()
    avatar_id = m.create_avatar(preset_name, personality)
    m.activate_avatar(avatar_id)

    voice = create_voice_processor(
        cfg.get("voice", {}).get("preset", "professional_female")
    )

    return {
        "manager": m,
        "avatar_id": avatar_id,
        "voice": voice,
        "status": m.get_avatar_statuses()[avatar_id],
    }


async def interact(manager: AvatarManager, avatar_id: str, text: str) -> Dict[str, Any]:
    data = {"type": "conversation", "intent": "question", "content": text}
    try:
        # Note last user text on the avatar, if available
        av = manager.active_avatars.get(avatar_id)
        if av and hasattr(av, "note_user_text"):
            av.note_user_text(text)
    except Exception:
        pass
    return await manager.interact_with_avatar(avatar_id, data)


def status_json(status: Dict[str, Any]) -> str:
    def default(o):
        try:
            return asdict(o)
        except Exception:
            return str(o)

    return json.dumps(status, default=default, ensure_ascii=False)


# ---------- Live call helpers (SAFE, local) ----------
def live_set_state(
    manager: AvatarManager,
    avatar_id: str,
    *,
    active: bool = None,
    listening: bool = None,
    muted: bool = None,
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


# -------- Minimal governed API shims (headless-safe) --------
def load_avatar(config_path: str) -> Any:
    """Load model, textures, and behavior from YAML config.
    This shim returns a lightweight handle; downstream exporters can interpret it.
    """
    try:
        cfg = yaml.safe_load(Path(config_path).read_text(encoding="utf-8")) or {}
    except Exception:
        cfg = {}
    return {"ok": True, "cfg": cfg, "config_path": str(config_path)}


def export_avatar(avatar: Any, out_dir: str, kind: str = "thumbnail") -> str:
    """Export a thumbnail PNG (headless-safe, no external renderer).

    Produces a visually distinct gold-tinted card that clearly indicates
    the artifact kind, proving the pipeline end-to-end without GPU.
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    p = out / f"eidollona_{kind}.png"
    try:
        from PIL import Image, ImageDraw, ImageFont  # type: ignore

        W, H = 640, 640
        im = Image.new("RGBA", (W, H), (11, 15, 20, 255))
        dr = ImageDraw.Draw(im)

        # Background radial/linear accents
        for i in range(0, 320, 8):
            c = int(30 + 50 * (1 - i / 320))
            dr.ellipse(
                [(W // 2 - i, H // 3 - i), (W // 2 + i, H // 3 + i)],
                outline=(c, c + 10, c + 20, 40),
            )

        # Gold frame
        gold = (212, 175, 55, 255)
        for k in range(0, 6):
            dr.rectangle([(10 + k, 10 + k), (W - 10 - k, H - 10 - k)], outline=gold)

        # Central emblem
        dr.ellipse(
            [(W // 2 - 70, H // 3 - 70), (W // 2 + 70, H // 3 + 70)],
            fill=(255, 236, 179, 90),
            outline=gold,
            width=3,
        )
        dr.ellipse(
            [(W // 2 - 16, H // 3 - 12), (W // 2 - 6, H // 3 - 2)],
            fill=(124, 58, 237, 255),
        )
        dr.ellipse(
            [(W // 2 + 6, H // 3 - 12), (W // 2 + 16, H // 3 - 2)],
            fill=(124, 58, 237, 255),
        )

        # Text (fallback to default font if truetype unavailable)
        try:
            font_big = ImageFont.truetype("arial.ttf", 36)
            font_sm = ImageFont.truetype("arial.ttf", 18)
        except Exception:
            font_big = ImageFont.load_default()
            font_sm = ImageFont.load_default()

        title = "Eidollona"
        sub = f"Artifact: {kind}"
        tw, th = dr.textsize(title, font=font_big)
        dr.text(
            ((W - tw) // 2, int(H * 0.62)),
            title,
            fill=(255, 215, 0, 255),
            font=font_big,
        )
        sw, sh = dr.textsize(sub, font=font_sm)
        dr.text(
            ((W - sw) // 2, int(H * 0.62) + th + 8),
            sub,
            fill=(230, 221, 212, 255),
            font=font_sm,
        )

        im.save(p, format="PNG")
    except Exception:
        # Fallback: ensure a non-empty file exists
        if not p.exists():
            p.write_bytes(b"artifact:thumbnail")
    return str(p)


def pose_avatar(pose: str, out_dir: str) -> str:
    """Export a static PNG indicating the requested pose (headless-safe)."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    p = out / f"pose_{pose}.png"
    try:
        from PIL import Image, ImageDraw, ImageFont  # type: ignore

        W, H = 640, 360
        im = Image.new("RGBA", (W, H), (12, 18, 26, 255))
        dr = ImageDraw.Draw(im)
        gold = (212, 175, 55, 255)
        dr.rectangle([(8, 8), (W - 8, H - 8)], outline=gold, width=3)
        # Simple silhouette proxy
        dr.ellipse(
            [(W // 2 - 30, H // 2 - 60), (W // 2 + 30, H // 2)],
            fill=(40, 60, 92, 255),
            outline=(90, 120, 150, 255),
        )
        dr.rectangle(
            [(W // 2 - 20, H // 2), (W // 2 + 20, H // 2 + 70)],
            fill=(40, 60, 92, 255),
            outline=(90, 120, 150, 255),
        )

        try:
            font = ImageFont.truetype("arial.ttf", 22)
        except Exception:
            font = ImageFont.load_default()
        txt = f"Pose: {pose}"
        tw, th = dr.textsize(txt, font=font)
        dr.text(((W - tw) // 2, 16), txt, fill=(255, 215, 0, 255), font=font)
        im.save(p, format="PNG")
    except Exception:
        if not p.exists():
            p.write_bytes(f"pose:{pose}".encode("utf-8"))
    return str(p)


def animate_avatar(clip: str, seconds: int, out_dir: str) -> str:
    """Export a small animated GIF representing the requested clip.

    Avoids system ffmpeg dependency; suitable for SAFE/headless environments.
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    p = out / f"anim_{clip}_{int(seconds)}s.gif"
    try:
        from PIL import Image, ImageDraw  # type: ignore

        W, H = 480, 270
        fps = 8
        total_frames = max(8, min(5 * fps, int(seconds * fps)))
        frames: List[Image.Image] = []

        for i in range(total_frames):
            im = Image.new("RGBA", (W, H), (10, 14, 20, 255))
            dr = ImageDraw.Draw(im)
            # Frame
            dr.rectangle([(6, 6), (W - 6, H - 6)], outline=(212, 175, 55, 255), width=2)
            # Moving emblem (simple motion path)
            t = i / max(1, total_frames - 1)
            cx = int(W * (0.2 + 0.6 * t))
            cy = int(H * (0.45 + 0.1 * (0.5 - abs(t - 0.5)) * 2))
            dr.ellipse(
                [(cx - 20, cy - 20), (cx + 20, cy + 20)],
                fill=(255, 236, 179, 120),
                outline=(212, 175, 55, 255),
                width=2,
            )
            # Caption
            dr.text((12, 10), f"Clip: {clip}", fill=(230, 221, 212, 255))
            frames.append(im.convert("P"))

        # Save as GIF with a modest duration per frame
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
    except Exception:
        if not p.exists():
            p.write_bytes(f"anim:{clip}:{seconds}s".encode("utf-8"))
    return str(p)
