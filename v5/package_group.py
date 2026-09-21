from __future__ import annotations

from decimal import Decimal

MASS_UNITS = {"g": Decimal("1"), "kg": Decimal("1000")}
VOLUME_UNITS = {"ml": Decimal("1"), "l": Decimal("1000")}

def normalize_amount(value: float | int | str, unit: str) -> tuple[Decimal, str]:
    unit = (unit or "").strip().lower()
    amount = Decimal(str(value))
    if unit in MASS_UNITS:
        return amount * MASS_UNITS[unit], "g"
    if unit in VOLUME_UNITS:
        return amount * VOLUME_UNITS[unit], "ml"
    raise ValueError(f"Unsupported package unit: {unit!r}")

def package_group(value: float | int | str, unit: str) -> str | None:
    amount, _ = normalize_amount(value, unit)
    if amount <= Decimal("50"):
        return "small"
    if Decimal("100") <= amount <= Decimal("1000"):
        return "medium"
    if amount >= Decimal("5000"):
        return "large"
    return None
