import logging
import sympy
from sympy.parsing.sympy_parser import (
    parse_expr,
    standard_transformations,
    implicit_multiplication_application,
    convert_xor,
)

logger = logging.getLogger(__name__)

_TRANSFORMS = standard_transformations + (
    implicit_multiplication_application,
    convert_xor,
)


class MathValidator:
    """
    SymPy-based equivalence check between two math answers.

    Used by the verified-answer cache to confirm that a freshly generated
    answer matches the cached one *symbolically* (e.g. "2(x+1)" ≡ "2x+2").
    Fails closed: parse errors return False so we don't accept a non-match
    as equivalent.
    """

    def _parse(self, text: str):
        cleaned = text.strip().replace("$", "").replace("\\", "")
        return parse_expr(cleaned, transformations=_TRANSFORMS, evaluate=True)

    def validate_equivalence(self, generated_answer: str, cached_answer: str) -> bool:
        if not generated_answer or not cached_answer:
            return False
        if generated_answer.strip() == cached_answer.strip():
            return True

        try:
            a = self._parse(generated_answer)
            b = self._parse(cached_answer)
        except Exception as e:
            logger.info(f"Math parse failed: {e}")
            return False

        try:
            if sympy.simplify(a - b) == 0:
                return True
        except Exception as e:
            logger.info(f"Symbolic simplify failed: {e}")

        try:
            return bool(sympy.Eq(a, b).simplify() is sympy.true)
        except Exception as e:
            logger.info(f"Equation simplify failed: {e}")
            return False
