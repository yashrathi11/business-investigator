import pandas as pd


# ============================================================
# 1. LOAD RAW DATA
# ============================================================

def load_raw_data(file_path: str) -> pd.DataFrame:
    """
    Load all sheets from the Online Retail II Excel file
    and combine them into a single DataFrame.
    """

    excel_file = pd.ExcelFile(file_path)

    dataframes = []

    for sheet_name in excel_file.sheet_names:
        sheet_df = pd.read_excel(
            file_path,
            sheet_name=sheet_name
        )

        dataframes.append(sheet_df)

    df = pd.concat(
        dataframes,
        ignore_index=True
    )

    return df


# ============================================================
# 2. CLEAN TRANSACTIONS
# ============================================================

def clean_transactions(
    df: pd.DataFrame,
    copy: bool = True,
) -> pd.DataFrame:
    """
    Clean raw transaction data according to the
    project's business rules.

    Parameters
    ----------
    df : pd.DataFrame
        Input transaction DataFrame.

    copy : bool, default=True
        Whether to create a copy of the input DataFrame.
        Upload processing uses copy=False to reduce
        peak memory usage.
    """

    # --------------------------------------------------------
    # Optional copy
    # --------------------------------------------------------

    if copy:
        df = df.copy()

    # --------------------------------------------------------
    # Step 1: Standardize data types
    # --------------------------------------------------------

    df["InvoiceDate"] = pd.to_datetime(
        df["InvoiceDate"],
        errors="coerce"
    )

    df["Quantity"] = pd.to_numeric(
        df["Quantity"],
        errors="coerce"
    )

    df["Price"] = pd.to_numeric(
        df["Price"],
        errors="coerce"
    )

    # --------------------------------------------------------
    # Step 2: Remove exact duplicate rows
    # --------------------------------------------------------

    df.drop_duplicates(
        inplace=True
    )

    # --------------------------------------------------------
    # Step 3: Identify cancelled transactions
    #
    # In this dataset, invoices beginning with "C"
    # represent cancellations.
    # --------------------------------------------------------

    df["is_cancelled"] = (
        df["Invoice"]
        .astype(str)
        .str.startswith("C")
    )

    # --------------------------------------------------------
    # Step 4: Identify returns
    #
    # Negative quantity + NOT cancelled
    # --------------------------------------------------------

    df["is_return"] = (
        (df["Quantity"] < 0)
        & (~df["is_cancelled"])
    )

    # --------------------------------------------------------
    # Step 5: Identify zero-price transactions
    # --------------------------------------------------------

    df["is_zero_price"] = (
        df["Price"] == 0
    )

    # --------------------------------------------------------
    # Step 6: Identify bad-debt accounting adjustments
    # --------------------------------------------------------

    df["is_bad_debt"] = (
        df["Description"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.lower()
        .eq("adjust bad debt")
    )

    # --------------------------------------------------------
    # Step 7: Remove cancelled transactions
    # --------------------------------------------------------

    df = df.loc[
        ~df["is_cancelled"]
    ].copy()

    # --------------------------------------------------------
    # Step 8: Remove bad-debt accounting adjustments
    # --------------------------------------------------------

    df = df.loc[
        ~df["is_bad_debt"]
    ].copy()

    # --------------------------------------------------------
    # Step 9: Calculate revenue
    #
    # Revenue = Quantity × Price
    # --------------------------------------------------------

    df["Revenue"] = (
        df["Quantity"] * df["Price"]
    )

    # --------------------------------------------------------
    # Step 10: Reset index
    # --------------------------------------------------------

    df.reset_index(
        drop=True,
        inplace=True
    )

    return df


# ============================================================
# 3. MAIN PIPELINE
# ============================================================

if __name__ == "__main__":

    input_file = "data/raw/online_retail_II.xlsx"

    output_file = "data/processed/clean_transactions.csv"

    # --------------------------------------------------------
    # Load raw data
    # --------------------------------------------------------

    print("=" * 60)
    print("LOADING RAW DATA")
    print("=" * 60)

    df = load_raw_data(input_file)

    print(
        f"Raw dataset shape: {df.shape}"
    )

    # --------------------------------------------------------
    # Raw dataset statistics
    # --------------------------------------------------------

    duplicate_count = df.duplicated().sum()

    cancelled_count = (
        df["Invoice"]
        .astype(str)
        .str.startswith("C")
        .sum()
    )

    bad_debt_count = (
        df["Description"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.lower()
        .eq("adjust bad debt")
        .sum()
    )

    print(
        f"Duplicate rows found: {duplicate_count}"
    )

    print(
        f"Cancelled rows found: {cancelled_count}"
    )

    print(
        f"Bad-debt rows found: {bad_debt_count}"
    )

    # --------------------------------------------------------
    # Clean data
    # --------------------------------------------------------

    print("\n" + "=" * 60)
    print("CLEANING DATA")
    print("=" * 60)

    clean_df = clean_transactions(df)

    print(
        f"Clean dataset shape: {clean_df.shape}"
    )

    # --------------------------------------------------------
    # Cleaning statistics
    # --------------------------------------------------------

    print(
        f"Returns retained: "
        f"{clean_df['is_return'].sum()}"
    )

    print(
        f"Zero-price rows retained: "
        f"{clean_df['is_zero_price'].sum()}"
    )

    print(
        f"Bad-debt rows remaining: "
        f"{clean_df['is_bad_debt'].sum()}"
    )

    print(
        f"Missing Customer IDs: "
        f"{clean_df['Customer ID'].isna().sum()}"
    )

    print(
        f"Missing Descriptions: "
        f"{clean_df['Description'].isna().sum()}"
    )

    # --------------------------------------------------------
    # Revenue statistics
    # --------------------------------------------------------

    total_revenue = clean_df["Revenue"].sum()

    positive_revenue_rows = (
        clean_df["Revenue"] > 0
    ).sum()

    negative_revenue_rows = (
        clean_df["Revenue"] < 0
    ).sum()

    zero_revenue_rows = (
        clean_df["Revenue"] == 0
    ).sum()

    print("\n" + "=" * 60)
    print("REVENUE SUMMARY")
    print("=" * 60)

    print(
        f"Total revenue: £{total_revenue:,.2f}"
    )

    print(
        f"Positive revenue rows: "
        f"{positive_revenue_rows}"
    )

    print(
        f"Negative revenue rows: "
        f"{negative_revenue_rows}"
    )

    print(
        f"Zero revenue rows: "
        f"{zero_revenue_rows}"
    )

    # --------------------------------------------------------
    # Save cleaned dataset
    # --------------------------------------------------------

    print("\n" + "=" * 60)
    print("SAVING CLEAN DATA")
    print("=" * 60)

    clean_df.to_csv(
        output_file,
        index=False
    )

    print(
        f"Clean dataset saved to: {output_file}"
    )

    print("\nPipeline completed successfully!")