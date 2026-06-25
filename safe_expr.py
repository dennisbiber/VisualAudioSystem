import ast
import math
import operator as op


OPS = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.Pow: op.pow,
    ast.USub: op.neg,
}


ALLOWED_FUNCS = {
    "sin": math.sin,
    "cos": math.cos,
    "abs": abs,
    "min": min,
    "max": max,
}


class SafeExpr:
    def __init__(self, expr):
        self.node = ast.parse(expr, mode="eval").body

    def eval(self, ctx):
        return self._eval(self.node, ctx)

    def _eval(self, node, ctx):

        if isinstance(node, ast.Constant):
            return node.value

        if isinstance(node, ast.Name):
            return ctx[node.id]

        if isinstance(node, ast.BinOp):
            return OPS[type(node.op)](
                self._eval(node.left, ctx),
                self._eval(node.right, ctx)
            )

        if isinstance(node, ast.UnaryOp):
            return OPS[type(node.op)](
                self._eval(node.operand, ctx)
            )

        if isinstance(node, ast.Call):
            func = ALLOWED_FUNCS[node.func.id]
            args = [self._eval(a, ctx) for a in node.args]
            return func(*args)

        raise ValueError("Unsafe expression")
