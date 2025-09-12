"""Unity Platform Avatar Controller (canonical role-based module).

Unity-specific control & animation bridge previously in `avatar_controller.py`.
Legacy module name re-exports this module. Prefer importing from
`avatar_controller_unity` moving forward.
"""

from typing import Dict, Any
from dataclasses import dataclass


@dataclass
class UnityAvatarConfig:
    movement_speed: float = 5.0
    rotation_speed: float = 180.0
    jump_force: float = 10.0
    gravity_scale: float = 1.0
    ground_check_distance: float = 0.1
    animation_blend_time: float = 0.1
    vr_enabled: bool = False
    hand_tracking: bool = False


class UnityAvatarController:
    def __init__(self, ecosystem_manager):
        self.ecosystem = ecosystem_manager
        self.config = UnityAvatarConfig()
        self.animation_states = self._define_animation_states()
        self.input_mappings = self._define_input_mappings()

        self.character_controller = None
        self.animator = None
        self.rigidbody = None
        self.transform = None
        self.camera_controller = None

        self.current_animation_state = "Idle"
        self.is_grounded = True
        self.movement_velocity = {"x": 0.0, "y": 0.0, "z": 0.0}
        self.rotation_velocity = 0.0

        if self.ecosystem and getattr(self.ecosystem, "logger", None):
            self.ecosystem.logger.info("🎮 Unity Avatar Controller initialized")

    def _define_animation_states(self) -> Dict[str, Dict[str, Any]]:
        return {
            "Idle": {
                "animation_clip": "Idle_01",
                "loop": True,
                "transitions": ["Walk", "Run", "Jump", "Dance", "Wave"],
            },
            "Walk": {
                "animation_clip": "Walk_Forward",
                "loop": True,
                "speed_multiplier": 1.0,
                "transitions": ["Idle", "Run", "Jump"],
            },
            "Run": {
                "animation_clip": "Run_Forward",
                "loop": True,
                "speed_multiplier": 1.5,
                "transitions": ["Idle", "Walk", "Jump"],
            },
            "Jump": {
                "animation_clip": "Jump_Up",
                "loop": False,
                "duration": 1.0,
                "transitions": ["Idle", "Walk", "Run"],
            },
            "Dance": {
                "animation_clip": "Dance_01",
                "loop": True,
                "duration": 10.0,
                "transitions": ["Idle"],
            },
            "Wave": {
                "animation_clip": "Wave_Hand",
                "loop": False,
                "duration": 2.0,
                "transitions": ["Idle"],
            },
            "Sit": {
                "animation_clip": "Sit_Down",
                "loop": True,
                "transitions": ["Idle"],
            },
            "Emote_Happy": {
                "animation_clip": "Emote_Celebrate",
                "loop": False,
                "duration": 3.0,
                "transitions": ["Idle"],
            },
            "Emote_Sad": {
                "animation_clip": "Emote_Disappointed",
                "loop": False,
                "duration": 2.5,
                "transitions": ["Idle"],
            },
        }

    def _define_input_mappings(self) -> Dict[str, Dict[str, Any]]:
        return {
            "keyboard_mouse": {
                "move_forward": {"key": "W", "axis": "Vertical", "value": 1.0},
                "move_backward": {"key": "S", "axis": "Vertical", "value": -1.0},
                "move_left": {"key": "A", "axis": "Horizontal", "value": -1.0},
                "move_right": {"key": "D", "axis": "Horizontal", "value": 1.0},
                "jump": {"key": "Space"},
                "run": {"key": "LeftShift", "hold": True},
                "dance": {"key": "T"},
                "wave": {"key": "G"},
                "sit": {"key": "X"},
                "camera_rotate": {"mouse": "Mouse X/Y"},
            },
            "gamepad": {
                "move": {"stick": "Left Stick"},
                "camera": {"stick": "Right Stick"},
                "jump": {"button": "A"},
                "run": {"trigger": "Right Trigger"},
                "dance": {"button": "Y"},
                "wave": {"button": "X"},
                "sit": {"button": "B"},
            },
            "vr_controllers": {
                "move": {"controller": "Left", "input": "Thumbstick"},
                "teleport": {"controller": "Right", "input": "Trigger"},
                "grab": {"controller": "Both", "input": "Grip"},
                "point": {"controller": "Right", "input": "Index Trigger"},
                "wave": {"controller": "Right", "gesture": "Wave"},
                "thumbs_up": {"controller": "Right", "gesture": "Thumbs Up"},
            },
        }

    def initialize_unity_components(self, component_refs: Dict[str, Any]):
        self.character_controller = component_refs.get("character_controller")
        self.animator = component_refs.get("animator")
        self.rigidbody = component_refs.get("rigidbody")
        self.transform = component_refs.get("transform")
        self.camera_controller = component_refs.get("camera_controller")
        if self.animator:
            self._setup_animator_parameters()
        if self.character_controller:
            self._setup_character_controller()

    def _setup_animator_parameters(self):  # pragma: no cover - logging only
        params = [
            "Speed",
            "IsGrounded",
            "IsJumping",
            "IsRunning",
            "TriggerDance",
            "TriggerWave",
            "TriggerSit",
            "EmotionState",
            "BlendShapeWeight",
        ]
        if self.ecosystem and getattr(self.ecosystem, "logger", None):
            for p in params:
                self.ecosystem.logger.debug(f"Animator param configured: {p}")

    def _setup_character_controller(self):  # pragma: no cover - logging only
        if self.ecosystem and getattr(self.ecosystem, "logger", None):
            self.ecosystem.logger.debug("CharacterController configured (placeholder)")

    def handle_movement_input(self, input_data: Dict[str, Any]):
        scheme = input_data.get("control_scheme", "keyboard_mouse")
        if scheme == "keyboard_mouse":
            self._handle_keyboard_mouse_input(input_data)
        elif scheme == "gamepad":
            self._handle_gamepad_input(input_data)
        elif scheme == "vr_controllers":
            self._handle_vr_input(input_data)

    def _handle_keyboard_mouse_input(self, input_data: Dict[str, Any]):
        horizontal = input_data.get("horizontal", 0.0)
        vertical = input_data.get("vertical", 0.0)
        is_running = input_data.get("run_pressed", False)
        speed = self.config.movement_speed * (1.5 if is_running else 1.0)
        self.movement_velocity.update({"x": horizontal * speed, "z": vertical * speed})
        if input_data.get("jump_pressed", False) and self.is_grounded:
            self.movement_velocity["y"] = self.config.jump_force
            self.is_grounded = False
            self._trigger_animation("Jump")
        if input_data.get("dance_pressed", False):
            self._trigger_animation("Dance")
        elif input_data.get("wave_pressed", False):
            self._trigger_animation("Wave")
        elif input_data.get("sit_pressed", False):
            self._trigger_animation("Sit")
        self._update_movement_animation(horizontal, vertical, is_running)

    def _handle_gamepad_input(self, input_data: Dict[str, Any]):
        lx = input_data.get("left_stick_x", 0.0)
        ly = input_data.get("left_stick_y", 0.0)
        is_running = input_data.get("right_trigger", 0.0) > 0.5
        speed = self.config.movement_speed * (1.5 if is_running else 1.0)
        self.movement_velocity.update({"x": lx * speed, "z": ly * speed})
        if input_data.get("button_a_pressed", False) and self.is_grounded:
            self.movement_velocity["y"] = self.config.jump_force
            self._trigger_animation("Jump")
        self._update_movement_animation(lx, ly, is_running)

    def _handle_vr_input(self, input_data: Dict[str, Any]):
        lx = input_data.get("left_thumbstick_x", 0.0)
        ly = input_data.get("left_thumbstick_y", 0.0)
        if input_data.get("locomotion_mode") == "smooth":
            speed = self.config.movement_speed * 0.8
            self.movement_velocity.update({"x": lx * speed, "z": ly * speed})
        gesture = input_data.get("right_controller_gesture")
        if gesture == "wave":
            self._trigger_animation("Wave")
        elif gesture == "thumbs_up":
            self._trigger_animation("Emote_Happy")
        if self.config.hand_tracking and input_data.get("hand_tracking_data"):
            self._handle_hand_tracking(input_data["hand_tracking_data"])

    def _handle_hand_tracking(
        self, hand_data: Dict[str, Any]
    ):  # pragma: no cover - illustrative
        right_hand = hand_data.get("right_hand", {})
        if self._detect_wave_gesture(right_hand):
            self._trigger_animation("Wave")
        elif self._detect_thumbs_up_gesture(right_hand):
            self._trigger_animation("Emote_Happy")
        elif self._detect_pointing_gesture(right_hand):
            self._handle_pointing_interaction(right_hand.get("pointing_direction", {}))

    def _detect_wave_gesture(self, hand_data: Dict[str, Any]) -> bool:
        return abs(hand_data.get("velocity", {}).get("x", 0)) > 2.0

    def _detect_thumbs_up_gesture(self, hand_data: Dict[str, Any]) -> bool:
        states = hand_data.get("finger_states", {})
        thumb_up = states.get("thumb", 0.0) > 0.8
        others_down = all(
            states.get(f, 1.0) < 0.2 for f in ["index", "middle", "ring", "pinky"]
        )
        return thumb_up and others_down

    def _detect_pointing_gesture(self, hand_data: Dict[str, Any]) -> bool:
        states = hand_data.get("finger_states", {})
        index_ext = states.get("index", 0.0) > 0.8
        others_curled = all(
            states.get(f, 1.0) < 0.3 for f in ["middle", "ring", "pinky"]
        )
        return index_ext and others_curled

    def _update_movement_animation(
        self, horizontal: float, vertical: float, is_running: bool
    ):
        mag = (horizontal**2 + vertical**2) ** 0.5
        if mag > 0.1:
            new_state = "Run" if is_running else "Walk"
        else:
            new_state = "Idle"
        if new_state != self.current_animation_state:
            self._transition_to_animation_state(new_state)
        if self.animator:
            self._set_animator_parameter("Speed", mag)
            self._set_animator_parameter("IsRunning", is_running)
            self._set_animator_parameter("IsGrounded", self.is_grounded)

    def _trigger_animation(self, animation_name: str):
        if animation_name in self.animation_states:
            if self.ecosystem and getattr(self.ecosystem, "logger", None):
                self.ecosystem.logger.info(f"🎭 Trigger animation: {animation_name}")
            if animation_name in ["Dance", "Wave", "Sit"]:
                self._set_animator_trigger(f"Trigger{animation_name}")
            if self.animation_states[animation_name].get("loop", False):
                self.current_animation_state = animation_name

    def _transition_to_animation_state(self, new_state: str):
        if new_state in self.animation_states:
            if new_state in self.animation_states[self.current_animation_state].get(
                "transitions", []
            ):
                if self.ecosystem and getattr(self.ecosystem, "logger", None):
                    self.ecosystem.logger.debug(
                        f"State: {self.current_animation_state} → {new_state}"
                    )
                self.current_animation_state = new_state

    def _set_animator_parameter(self, param_name: str, value: Any):  # pragma: no cover
        if self.ecosystem and getattr(self.ecosystem, "logger", None):
            self.ecosystem.logger.debug(f"Animator param {param_name}={value}")

    def _set_animator_trigger(self, trigger_name: str):  # pragma: no cover
        if self.ecosystem and getattr(self.ecosystem, "logger", None):
            self.ecosystem.logger.debug(f"Animator trigger {trigger_name}")

    def update_physics(self, delta_time: float):
        if not self.is_grounded:
            self.movement_velocity["y"] -= 9.81 * self.config.gravity_scale * delta_time
        self.is_grounded = self._check_ground_collision()
        # Movement application hooks would go here (Unity side)

    def _check_ground_collision(self) -> bool:
        return True

    def handle_emotion_update(self, emotion_data: Dict[str, Any]):  # pragma: no cover
        emotion_type = emotion_data.get("primary_emotion")
        intensity = emotion_data.get("intensity", 0.5)
        mapping = {
            "joy": "Emote_Happy",
            "sadness": "Emote_Sad",
            "surprise": "Jump",
            "trust": "Wave",
        }
        if emotion_type in mapping and intensity > 0.7:
            self._trigger_animation(mapping[emotion_type])

    def _handle_pointing_interaction(
        self, pointing_direction: Dict[str, float]
    ):  # pragma: no cover
        if self.ecosystem and getattr(self.ecosystem, "logger", None):
            self.ecosystem.logger.info(f"👉 Pointing: {pointing_direction}")

    def get_unity_avatar_status(self) -> Dict[str, Any]:
        return {
            "current_animation_state": self.current_animation_state,
            "movement_velocity": self.movement_velocity,
            "is_grounded": self.is_grounded,
            "position": getattr(self.transform, "position", {"x": 0, "y": 0, "z": 0}),
            "rotation": getattr(
                self.transform, "rotation", {"x": 0, "y": 0, "z": 0, "w": 1}
            ),
            "animator_parameters": {
                "Speed": (
                    self.movement_velocity["x"] ** 2 + self.movement_velocity["z"] ** 2
                )
                ** 0.5,
                "IsGrounded": self.is_grounded,
                "IsRunning": abs(self.movement_velocity["x"])
                > self.config.movement_speed,
                "EmotionState": 0,
            },
        }


__all__ = ["UnityAvatarController", "UnityAvatarConfig"]
