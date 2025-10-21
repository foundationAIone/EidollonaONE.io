# VRM Pipeline & Integration Guide

This guide walks through the avatar upgrade path end-to-end — from DCC export to the SAFE HUD. It pairs native engine setup (Unity, Unreal) with the web rendering pipeline that now powers the `Throne Room` viewer.

## 1. Source of truth

- Author characters as VRM 1.0 or glTF 2.0 rigs. Keep neutral A-pose as the master pose.
- Store working meshes, textures, and animation clips in `avatar_data/` — do **not** commit binary masters into `web_interface/static`.
- Before export, lock down **sovereign expressions** (see `sovereign_expressions.md`) so no trading cues slip into default visemes or gesture loops.

## 2. Unity (UniVRM) workflow

1. Install [UniVRM 0.118+](https://github.com/vrm-c/UniVRM/releases) into your Unity project.
2. Drag the source humanoid FBX into Unity and confirm the **Humanoid** avatar mapping in the Rig tab.
3. Use **VRM > Export VRM 1.0**:
   - Fill meta fields (author, contact, allowed uses) — match Eidollona sovereignty policy.
   - Enable *Use Experimental Exporter* for spring bone 1.0 compatibility.
   - Include blend shape clips for speech visemes (``A``, ``I``, ``U``, ``E``, ``O``) and sovereignty gestures (``Calm``, ``Focus``).
4. Lip sync setup:
   - Add an `AudioSource` and `OVRLipSync` or `Crosstale RT-Voice` component to generate blend shape weights at runtime.
   - Map the viseme output to `VRMBlendShapeProxy`. Make sure baseline expression remains neutral below 0.15 weight.
5. Inverse kinematics:
   - Attach Unity's `TwoBoneIKConstraint` to arms and legs.
   - Limit pole vector swing to ±35° to preserve sovereign posture.
   - Export baked animation clips for idle, talk, and bow gestures alongside the VRM.
6. Export using UniVRM; Unity writes a `.vrm` asset. Place the final file under `web_interface/static/webview/assets/avatars/` for HUD consumption.

## 3. Unreal Engine (UE 5.3+) retargeting

1. Import the VRM file via the [VRM4U plugin](https://github.com/ruyo/VRM4U). Enable *VRM Importer* in the project plugins panel.
2. When prompted, generate the humanoid IK rig. Use the built-in UE *IK Retargeter* to map VRM bones to your control rig.
3. Retargeting steps:
   - Create **IK Retargeter** asset using `SK_Mannequin` → `SK_VRM`. Align hips and shoulders in the retarget pose.
   - Bake locomotion clips (walk, turn, bow). Keep upper-body gestures subtle per sovereignty policy.
4. Lip sync:
   - Use the `LipSyncMorphTarget` component or [Metasounds-based viseme solver](https://docs.unrealengine.com/) to drive VRM blend shapes.
   - Clamp viseme weight to 0.65 to avoid exaggerated cues.
5. Package retargeted animations as `.anim` assets and export any additional FBX for archive. The VRM file itself remains identical and can be reused on the web side.

## 4. Web delivery pipeline (Three.js + @pixiv/three-vrm)

We now load VRM avatars inside `throne_room.html` by appending query flags:

```text
http://127.0.0.1:8000/static/webview/throne_room.html?vrm=1&vrmUrl=/static/webview/assets/avatars/eidollona_idle.vrm
```

To keep payloads lean:

| Step | Tool | Command |
|------|------|---------|
| Mesh simplification | [glTF-Transform](https://gltf-transform.donmccurdy.com/) | `npx gltf-transform weld input.vrm tmp.glb --tolerance=1e-3` |
| Texture compression | KTX2 (BasisU) | `npx gltf-transform etc1s tmp.glb tmp_etc1s.glb --quality 128` |
| Meshopt compression | [gltfpack](https://github.com/zeux/meshoptimizer) | `gltfpack -i tmp_etc1s.glb -o eidollona_idle.vrm --vrm` |

> ⚠️ `gltfpack` can output VRM 0.x metadata; validate with `npx @pixiv/vrm-validator eidollona_idle.vrm` before shipping.

Place the optimized file under `web_interface/static/webview/assets/avatars/` and reference it via the `vrmUrl` query parameter. The new loader automatically instantiates `KTX2Loader` and Meshopt decoders.

## 5. Lip sync on the web

- Audio-driven lip sync is optional in the HUD. When needed, stream viseme weights via websocket and call:

   ```js
  if (window.HUDVRM?.currentVRM?.expressionManager) {
    window.HUDVRM.currentVRM.expressionManager.setValue('A', weight);
  }
  ```

- The loader ensures meshes are not frustum-culled so blend shapes remain stable even off-screen.
- Keep viseme cadence under 60 FPS to avoid flooding sovereign channels.

## 6. IK samples & retargeting hooks

- Include `humanoid_idle.anim` and `humanoid_talk.anim` in `avatar_data/` as source references. Use Unity's Animation Rigging to bake contact points.
- For UE, export control rig presets (`CR_VRMArm`, `CR_VRMLeg`) and document pole vectors. Store JSON snapshots in `avatar_data/rig_presets/` if you need automated build steps.
- In the web HUD, listen for the custom event emitted when WebGPU toggles (see below) to decide whether to enable experimental PQRE IK solvers.

## 7. PQRE WebGPU toggle

The HUD now exposes an optional WebGPU path. By default it stays on WebGL to respect SAFE boundaries. To opt in, either press **Enable WebGPU** in the PQRE Visuals card or open the HUD with `?webgpu=1`.

The toggle broadcasts a `pqre:webgpu-change` event so downstream modules can initialize heavier shaders only when approved.

## 8. Quick validation checklist

- [ ] `npx @pixiv/vrm-validator` returns **no errors** (warnings about first-person mesh visibility are acceptable).
- [ ] File size under 15 MB (after meshopt + KTX2) — ensures snappy HUD loads.
- [ ] Sovereign expressions remain within mandated ranges (see companion guide).
- [ ] Test in Chromium-based browsers (WebGL + WebGPU) and Firefox (WebGL fallback).
- [ ] Confirm the HUD message updates to “VRM avatar loaded”. Errors are logged to the console with the `HUDVRM` namespace.

Stay mindful that every avatar shipped through this pipeline must pass compliance before being exposed to operators.
