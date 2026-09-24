"""Translate Olist product categories while preserving unknown values for model features."""

import pandas as pd


def with_category_name(products: pd.DataFrame, translation: pd.DataFrame) -> pd.DataFrame:
    products = products.merge(translation, on="product_category_name", how="left")
    products["category"] = products["product_category_name_english"].fillna(products["product_category_name"])
    return products
