"""DataFrame → JSON-safe list of dicts (NaN → None, timestamps → ISO strings)."""
import pandas as pd


def records(frame: pd.DataFrame) -> list[dict]:
    safe = frame.copy()
    for column in safe.columns:
        if pd.api.types.is_datetime64_any_dtype(safe[column]):
            safe[column] = safe[column].dt.strftime("%Y-%m-%dT%H:%M:%S")
    safe = safe.astype(object).where(safe.notna(), None)
    return safe.to_dict(orient="records")
