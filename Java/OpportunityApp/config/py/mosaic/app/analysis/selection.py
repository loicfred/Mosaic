"""Validated, request-local analysis windows. Never changes global rules or source data."""
from contextlib import contextmanager
from contextvars import ContextVar
import json
import math

import pandas as pd
from fastapi import HTTPException, Query

from app.analysis.populations import purchase_month
from app.config import DATA_RANGE

ACTIVE_WINDOWS = ContextVar('analysis_windows', default=None)


class Selection:
    def __init__(self, recent_start=None, recent_end=None, previous_start=None, previous_end=None,
                 category=None, customer_state=None, thresholds=None):
        self.category, self.customer_state = category, customer_state
        self.thresholds = thresholds or {}
        self.periods = None
        bounds = [recent_start, recent_end, previous_start, previous_end]
        if any(bounds):
            if not all(bounds):
                raise ValueError('Choose both start and end months for both periods.')
            if not (DATA_RANGE[0] <= previous_start <= previous_end < recent_start <= recent_end <= DATA_RANGE[1]):
                raise ValueError('Periods must be inside the dataset range, ordered and non-overlapping.')
            self.periods = ([str(m) for m in pd.period_range(recent_start, recent_end, freq='M')],
                            [str(m) for m in pd.period_range(previous_start, previous_end, freq='M')])

    def filter(self, frame):
        selected = frame
        for key, value in [('category', self.category), ('customer_state', self.customer_state)]:
            if value:
                selected = selected[selected[key] == value]
        return selected

    @contextmanager
    def activate(self):
        token = ACTIVE_WINDOWS.set(self.periods)
        try:
            yield
        finally:
            ACTIVE_WINDOWS.reset(token)

    def describe(self):
        return {'category': self.category, 'customer_state': self.customer_state,
                'recent_months': self.periods[0] if self.periods else None,
                'previous_months': self.periods[1] if self.periods else None,
                'thresholds': self.thresholds}


def select_windows(months, n=3):
    explicit = ACTIVE_WINDOWS.get()
    if explicit is not None:
        return explicit
    ordered = sorted(set(months))
    return ordered[-n:], ordered[-2*n:-n]


def row_windows(monthly, n=3):
    recent, previous = select_windows([r['month'] for r in monthly], n)
    return ([r for r in monthly if r['month'] in recent], [r for r in monthly if r['month'] in previous])


MONTH = r'^20\d{2}-(0[1-9]|1[0-2])$'


def selection_params(recent_start: str | None = Query(None, pattern=MONTH),
                     recent_end: str | None = Query(None, pattern=MONTH),
                     previous_start: str | None = Query(None, pattern=MONTH),
                     previous_end: str | None = Query(None, pattern=MONTH),
                     category: str | None = Query(None, max_length=120),
                     customer_state: str | None = Query(None, max_length=2),
                     thresholds: str | None = Query(None, max_length=4000)):
    try:
        rules = json.loads(thresholds) if thresholds else {}
        if not isinstance(rules, dict) or any(not isinstance(k, str) or isinstance(v, bool)
                or not isinstance(v, (int, float)) or not math.isfinite(v) or not 0 <= v <= 100
                for k, v in rules.items()):
            raise ValueError('Thresholds must be a JSON object of finite numbers from 0 to 100.')
        return Selection(recent_start, recent_end, previous_start, previous_end, category, customer_state, rules)
    except (ValueError, TypeError) as error:
        raise HTTPException(422, str(error)) from error
