import pandas as pd
from pathlib import Path

SOURCE = Path("data/processed/clean_transactions.csv")
OUTPUT = Path("data/demo/transactions_demo.csv")

TARGET_ROWS = 100_000
RANDOM_STATE = 42

print("Loading dataset...")
df = pd.read_csv(
    SOURCE,
    parse_dates=["InvoiceDate"],
)

print(f"Original rows: {len(df):,}")
print(f"Original dates: {df['InvoiceDate'].dt.date.nunique():,}")

df["_date"] = df["InvoiceDate"].dt.date

rows_per_day = max(1, TARGET_ROWS // df["_date"].nunique())

parts = []

for _, group in df.groupby("_date", sort=False):
    n = min(len(group), rows_per_day)
    parts.append(
        group.sample(
            n=n,
            random_state=RANDOM_STATE,
        )
    )

demo = pd.concat(parts, ignore_index=True)

remaining = TARGET_ROWS - len(demo)

if remaining > 0:
    selected_indices = pd.Index(
        [idx for part in parts for idx in part.index]
    )

    remaining_df = df.drop(
        index=selected_indices,
        errors="ignore",
    )

    if len(remaining_df) > 0:
        extra = remaining_df.sample(
            n=min(remaining, len(remaining_df)),
            random_state=RANDOM_STATE,
        )
        demo = pd.concat([demo, extra], ignore_index=True)

demo = demo.drop(columns=["_date"])

demo = demo.sort_values(
    "InvoiceDate"
).reset_index(drop=True)

OUTPUT.parent.mkdir(
    parents=True,
    exist_ok=True,
)

demo.to_csv(
    OUTPUT,
    index=False,
)

print(f"Demo rows: {len(demo):,}")
print(f"Demo dates: {demo['InvoiceDate'].dt.date.nunique():,}")
print(f"Output: {OUTPUT}")




