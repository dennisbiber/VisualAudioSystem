import yaml
from safe_expr import SafeExpr
from mod_primitives import LFO, Envelope
import math


class Modulator:

    def __init__(self, config_path="controls.yml"):

        with open(config_path) as f:
            self.cfg = yaml.safe_load(f)

        self.state = dict(self.cfg["variables"])

        self.exprs = [
            (k, SafeExpr(v))
            for k, v in self.cfg.get("expressions", {}).items()
        ]

        self.lfos = {}
        for name, c in self.cfg.get("lfos", {}).items():
            self.lfos[name] = LFO(**c)

        self.envs = {}
        for name, c in self.cfg.get("envelopes", {}).items():
            self.envs[name] = Envelope(**c)

    # ----------------------------------

    def __getattr__(self, k):
        if k in self.state:
            return self.state[k]
        raise AttributeError(k)

    def __setattr__(self, k, v):
        if k in ("cfg","state","exprs","lfos","envs"):
            super().__setattr__(k,v)
        else:
            self.state[k] = v

    # ----------------------------------

    def trigger(self, name, *args):
        actions = self.cfg.get("triggers", {}).get(name, [])

        local_ctx = {
            **self.state,
            "args": args,
            "math": math
        }

        for expr in actions:
            exec(expr, {}, local_ctx)

        for k in self.state:
            self.state[k] = local_ctx[k]
        if name in self.envs:
            self.envs[name].trigger()

    # ----------------------------------

    def update_from_audio(self, audio, dt):

        ctx = {
            **self.state,
            "dt": dt,
            "audio": audio
        }

        # LFO must run before rules
        for k, lfo in self.lfos.items():
            ctx[k] = lfo.update(dt)

        for k, env in self.envs.items():
            ctx[k] = env.update(dt)

        for rule in self.cfg.get("rules", []):
            exec(rule, {}, ctx)

        for k in self.state:
            self.state[k] = ctx[k]

        for name, expr in self.exprs:
            self.state[name] = expr.eval(ctx)
