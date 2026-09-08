from pathlib import Path
from uuid import uuid4

import pandas as pd

from src.cleaning.clean_transactions import (
    load_raw_data,
    clean_transactions,
)


ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls"}


def load_uploaded_file(file_path: str) -> pd.DataFrame:
    """
    Load an uploaded CSV or Excel file.
    """

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(
            f"File not found: {file_path}"
        )

    if path.suffix.lower() not in ALLOWED_EXTENSIONS:
        raise ValueError(
            "Unsupported file type. "
            "Allowed formats: CSV, XLSX, XLS."
        )

    # --------------------------------------------------------
    # CSV memory optimization
    # --------------------------------------------------------

    if path.suffix.lower() == ".csv":
        return pd.read_csv(
            path,
            dtype={
                "StockCode": "category",
                "Country": "category",
            },
            parse_dates=["InvoiceDate"],
        )

    # --------------------------------------------------------
    # Excel files
    # --------------------------------------------------------

    return load_raw_data(str(path))


def process_uploaded_file(
    file_path: str,
    output_path: str,
) -> dict:
    """
    Load, clean, validate, and save an uploaded dataset.
    """

    df = load_uploaded_file(file_path)

    # --------------------------------------------------------
    # Validate required columns
    # --------------------------------------------------------

    required_columns = {
        "Invoice",
        "StockCode",
        "Description",
        "Quantity",
        "InvoiceDate",
        "Price",
        "Customer ID",
        "Country",
    }

    missing_columns = required_columns - set(df.columns)

    if missing_columns:
        raise ValueError(
            f"Missing required columns: "
            f"{sorted(missing_columns)}"
        )

    # --------------------------------------------------------
    # Clean without creating the initial full DataFrame copy
    # --------------------------------------------------------

    clean_df = clean_transactions(
        df,
        copy=False,
    )

    # --------------------------------------------------------
    # Save processed dataset
    # --------------------------------------------------------

    output = Path(output_path)

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    clean_df.to_csv(
        output,
        index=False,
    )

    # --------------------------------------------------------
    # Return processing metadata
    # --------------------------------------------------------

    return {
        "input_rows": int(len(df)),
        "output_rows": int(len(clean_df)),
        "output_path": str(output),
        "total_revenue": float(
            clean_df["Revenue"].sum()
        ),
    }


def create_dataset_id() -> str:
    """
    Generate a unique identifier for an uploaded dataset.
    """

    return uuid4().hex