"""Consistent number formatting for narratives (UI formats numbers itself)."""

from __future__ import annotations

CURRENCY = "MUR"


def mur(x: float | None, signed: bool = False) -> str:
    if x is None:
        return "n/a"
    sign = ""
    if signed:
        sign = "+" if x > 0 else ("-" if x < 0 else "")
        x = abs(x)
    elif x < 0:
        sign, x = "-", abs(x)
    return f"{sign}{CURRENCY} {x:,.0f}"


def pct(x: float | None, signed: bool = True, digits: int = 1) -> str:
    if x is None:
        return "n/a"
    return f"{x:+.{digits}f}%" if signed else f"{x:.{digits}f}%"


def pp(x: float | None) -> str:
    if x is None:
        return "n/a"
    return f"{x:+.1f} pp"


def days(x: float | None) -> str:
    if x is None:
        return "n/a"
    return f"{x:.0f} days"


def date_label(iso: str) -> str:
    from datetime import date

    d = date.fromisoformat(iso[:10])
    return d.strftime("%d %b %Y")
