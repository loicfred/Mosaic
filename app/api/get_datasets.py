"""The dataset files the API reads, with their columns, for the website's Help page."""

import csv

from fastapi import APIRouter, Request

from app.config import ALL_DATASET_FILES

router = APIRouter()


@router.get("/api/datasets")
def datasets(request: Request):
    folder = request.app.state.datasets_dir
    files = []
    for name in ALL_DATASET_FILES:
        with open(folder / name, encoding="utf-8-sig", newline="") as handle:
            files.append({"file": name, "columns": next(csv.reader(handle), [])})
    return {"source": "Olist Brazilian e-commerce public dataset", "files": files}
