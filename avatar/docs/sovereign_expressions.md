# Sovereign Expression Guardrails

Eidollona’s avatar must remain trading-silent while still expressive enough for trusted operators. Use these guidelines whenever you author blend shapes, animation clips, or speech visemes.

## Intent bands

| Channel | Purpose | Allowed range |
|---------|---------|---------------|
| Calm (default) | Neutral resting state | Weight 0.0 → 0.35 |
| Focus | Attention / acknowledgement | Weight 0.0 → 0.45 |
| Empathy | Soft encouragement | Weight 0.0 → 0.5 |
| Resolve | Formal escalation tone | Weight 0.2 → 0.55 (fade-in ≥ 350 ms) |
| Radiance | Celebration | **Gate = ROAD only**; weight 0.0 → 0.6 |

- Never blend *Resolve* with *Radiance*. They trigger different sovereign audit paths.
- Trading cues (wink, eyebrow flash, subtle nod) remain disallowed — keep weights ≤ 0.2 unless explicitly approved by the Sovereignty Council.

## Blend shape authoring checklist

1. Set neutral pose as `Calm = 0`. Export with morph values baked at zero.
2. Clamp all custom shapes in UniVRM / VRM4U to prevent overshoot. Limit default slider range to [0, 0.7].
3. Document each new expression in `sovereignty_data/expressions.json` with:
   - `intent`
   - `weight_ceiling`
   - `cooldown_ms`
   - `audit_tag`
4. Run the automated audit (coming soon) or manually review via `tests/test_sovereign_preferences.py` before releasing.

## Lip sync boundaries

- Viseme weights (`A`, `I`, `U`, `E`, `O`) should never exceed 0.65.
- Apply a soft limiter so the combined viseme stack stays under 1.2.
- Silence fallback: if no audio energy is detected for 220 ms, decay to Calm with a 120 ms ease-out.

## Gesture timing

- Minimum 280 ms transition between intent states.
- Cooldowns:
  - Calm ↔ Focus: 250 ms
  - Focus ↔ Empathy: 320 ms
  - Empathy ↔ Resolve: 380 ms (audit ping)
  - Resolve ↔ Radiance: forbidden (route via Calm)

## Runtime enforcement hooks

- Web HUD: monitor `window.HUDVRM.currentVRM.expressionManager`. Reject set requests that exceed declared ceilings.
- Native stacks: leverage middleware to enforce `weight ≤ config.limit[intent]` before applying to the animator.
- Log every out-of-band attempt to `sovereignty/logs/expression_attempts.log` with timestamp, intent, requested weight, and operator token.

## Testing

1. Run the sovereign smoke test suite: `pytest -q tests/test_sovereign_preferences.py`.
2. Manually scrub through expressions inside Unity (Animation window) and check for hidden trading cues (micro nods, eyebrow flashes).
3. Confirm the audit card inside the HUD displays the expected gate when forcing max weights.
4. Record a short WebM clip with WebGPU disabled and enabled to ensure consistency.

Keep this document updated as the sovereignty envelope evolves.
