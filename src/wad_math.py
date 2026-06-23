from decimal import Decimal, getcontext

# Set global precision context for 10¹⁸ fixed-point math
getcontext().prec = 50
W = Decimal(10**18)  # WAD precision baseline
ZERO = Decimal(0)
ONE = Decimal(1)

def wad(x: float) -> Decimal:
    """Convert float to WAD (10¹⁸ precision)."""
    return Decimal(str(x)) * W

def wad_from_str(s: str) -> Decimal:
    """Parse string to WAD."""
    return Decimal(s) * W

def wad_to_float(w: Decimal) -> float:
    """Convert WAD to float."""
    return float(w / W)

def wad_mul(a: Decimal, b: Decimal) -> Decimal:
    """Multiply two WAD numbers (a*b)/W."""
    return (a * b) / W

def wad_div(a: Decimal, b: Decimal) -> Decimal:
    """Divide two WAD numbers (a/b)*W."""
    return (a / b) * W if b != ZERO else ZERO

def wad_abs(a: Decimal) -> Decimal:
    """Absolute value."""
    return -a if a < ZERO else a

def wad_min(a: Decimal, b: Decimal) -> Decimal:
    """Minimum."""
    return a if a < b else b

def wad_max(a: Decimal, b: Decimal) -> Decimal:
    """Maximum."""
    return a if a > b else b
