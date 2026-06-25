import yaml
import pygame
import operator


# -----------------------------
# small helpers
# -----------------------------

OPS = {
    "add": operator.add,
    "sub": operator.sub,
    "mul": operator.mul,
    "set": lambda a, b: b,
    "toggle01": lambda a, _: 1.0 - a,
    "op": "call",
}


def clamp(value, minv=None, maxv=None):
    if minv is not None:
        value = max(minv, value)
    if maxv is not None:
        value = min(maxv, value)
    return value


# -----------------------------
# Control Engine
# -----------------------------

class ControlEngine:
    """
    Generic event → action → parameter mapper.
    Works for keyboard now, MIDI later.
    """

    def __init__(self, config_path, context):
        """
        context = {
            "mod": mod,
            "audio": audio,
            "renderer": renderer
            ...
        }
        """
        self.held_keys = set()

        with open(config_path, "r") as f:
            self.cfg = yaml.safe_load(f)

        self.ctx = context
        self.keymap = {}

        self._build_keymap()

    # -------------------------

    def _build_keymap(self):
        keys = self.cfg.get("keyboard", {})

        for key_name, action_name in keys.items():
            pygame_key = getattr(pygame, key_name)
            self.keymap[pygame_key] = action_name

    # -------------------------

    def handle_event(self, event):

        if event.type == pygame.KEYDOWN:
            self.held_keys.add(event.key)

            action_name = self.keymap.get(event.key)
            if action_name:
                action = self.cfg["actions"][action_name]

                # only execute immediately if not continuous
                if not action.get("continuous"):
                    self.execute(action_name)

        elif event.type == pygame.KEYUP:
            if event.key in self.held_keys:
                self.held_keys.remove(event.key)

    def update(self, dt):
        """
        Call this once per frame from your main loop.
        """

        for key in self.held_keys:
            action_name = self.keymap.get(key)
            if not action_name:
                continue

            action = self.cfg["actions"][action_name]

            if not action.get("continuous"):
                continue

            self.execute_continuous(action_name, dt)

    def execute_continuous(self, action_name, dt):
        action = self.cfg["actions"][action_name]

        target_path = action["target"]
        op_name = action.get("op", "add")

        obj_name, attr = target_path.split(".")
        obj = self.ctx[obj_name]

        rate = action.get("rate", action.get("value", 0))

        minv = action.get("min")
        maxv = action.get("max")

        current = getattr(obj, attr)

        # scale by dt
        delta = rate * dt

        new_value = OPS[op_name](current, delta)
        new_value = clamp(new_value, minv, maxv)

        setattr(obj, attr, new_value)



    # -------------------------

    def execute(self, action_name):
        action = self.cfg["actions"][action_name]

        target_path = action["target"]
        op_name = action.get("op", "set")

        obj_name, attr = target_path.split(".")
        obj = self.ctx[obj_name]

        # -----------------------------
        # CALL TYPE (functions)
        # -----------------------------
        if op_name == "call":
            args = action.get("value", [])
            getattr(obj, attr)(*args)
            return

        # -----------------------------
        # VALUE TYPE (attributes)
        # -----------------------------
        value = action.get("value", 0)
        minv = action.get("min")
        maxv = action.get("max")

        current = getattr(obj, attr)
        new_value = OPS[op_name](current, value)
        new_value = clamp(new_value, minv, maxv)

        setattr(obj, attr, new_value)

        if action.get("print"):
            print(action["print"], new_value)

