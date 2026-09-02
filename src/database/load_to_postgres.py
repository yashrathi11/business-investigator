import pandas as pd
import psycopg2
from pathlib import Path
from io import StringIO


# ============================================================
# CONFIGURATION
# ============================================================

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "business_investigator",
    "user": "postgres",
    "password": "yash@123"
}

PROJECT_ROOT = Path(__file__).resolve().parents[2]

CLEAN_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "clean_transactions.csv"
)

RFM_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "customer_rfm.csv"
)


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_connection():
    return psycopg2.connect(**DB_CONFIG)


# ============================================================
# LOAD CUSTOMERS
# ============================================================

def load_customers(conn, df):

    print("\nLoading customers...")

    customer_df = (
        df[
            df["Customer ID"].notna()
        ]
        .groupby("Customer ID")
        .agg(
            first_purchase_date=(
                "InvoiceDate",
                "min"
            ),
            country=(
                "Country",
                "first"
            )
        )
        .reset_index()
    )

    customer_df.rename(
        columns={
            "Customer ID": "customer_id"
        },
        inplace=True
    )

    customer_df["customer_id"] = (
        customer_df["customer_id"]
        .astype(float)
    )

    customer_df["first_purchase_date"] = pd.to_datetime(
        customer_df["first_purchase_date"]
    )

    buffer = StringIO()

    customer_df.to_csv(
        buffer,
        index=False,
        header=False
    )

    buffer.seek(0)

    cursor = conn.cursor()

    cursor.copy_expert(
        """
        COPY customers
        (
            customer_id,
            first_purchase_date,
            country
        )
        FROM STDIN
        WITH CSV
        """,
        buffer
    )

    conn.commit()

    cursor.close()

    print(
        f"Customers loaded: {len(customer_df):,}"
    )


# ============================================================
# LOAD PRODUCTS
# ============================================================

def load_products(conn, df):

    print("\nLoading products...")

    product_df = (
        df[
            [
                "StockCode",
                "Description"
            ]
        ]
        .dropna(
            subset=["StockCode"]
        )
        .drop_duplicates(
            subset=["StockCode"]
        )
    )

    product_df = product_df.rename(
        columns={
            "StockCode": "stock_code",
            "Description": "description"
        }
    )

    product_df["stock_code"] = (
        product_df["stock_code"]
        .astype(str)
    )

    product_df["description"] = (
        product_df["description"]
        .fillna("")
        .astype(str)
    )

    buffer = StringIO()

    product_df.to_csv(
        buffer,
        index=False,
        header=False
    )

    buffer.seek(0)

    cursor = conn.cursor()

    cursor.copy_expert(
        """
        COPY products
        (
            stock_code,
            description
        )
        FROM STDIN
        WITH CSV
        """,
        buffer
    )

    conn.commit()

    cursor.close()

    print(
        f"Products loaded: {len(product_df):,}"
    )


# ============================================================
# LOAD TRANSACTIONS
# ============================================================

def load_transactions(conn, df):

    print("\nLoading transactions...")

    transaction_df = df[
        [
            "Invoice",
            "StockCode",
            "Description",
            "Quantity",
            "InvoiceDate",
            "Price",
            "Customer ID",
            "Country",
            "is_cancelled",
            "is_return",
            "is_zero_price",
            "Revenue"
        ]
    ].copy()

    transaction_df.rename(
        columns={
            "Invoice": "invoice",
            "StockCode": "stock_code",
            "Description": "description",
            "Quantity": "quantity",
            "InvoiceDate": "invoice_date",
            "Price": "price",
            "Customer ID": "customer_id",
            "Country": "country",
            "Revenue": "revenue"
        },
        inplace=True
    )

    transaction_df["invoice"] = (
        transaction_df["invoice"]
        .astype(str)
    )

    transaction_df["stock_code"] = (
        transaction_df["stock_code"]
        .astype(str)
    )

    transaction_df["description"] = (
        transaction_df["description"]
        .fillna("")
        .astype(str)
    )

    transaction_df["quantity"] = (
        transaction_df["quantity"]
        .fillna(0)
        .astype(int)
    )

    transaction_df["invoice_date"] = pd.to_datetime(
        transaction_df["invoice_date"],
        errors="coerce"
    )

    transaction_df["price"] = pd.to_numeric(
        transaction_df["price"],
        errors="coerce"
    )

    transaction_df["customer_id"] = pd.to_numeric(
        transaction_df["customer_id"],
        errors="coerce"
    )

    transaction_df["country"] = (
        transaction_df["country"]
        .fillna("Unspecified")
        .astype(str)
    )

    transaction_df["revenue"] = pd.to_numeric(
        transaction_df["revenue"],
        errors="coerce"
    )

    # PostgreSQL COPY needs empty values for NaN
    transaction_df = transaction_df.where(
        pd.notnull(transaction_df),
        None
    )

    buffer = StringIO()

    transaction_df.to_csv(
        buffer,
        index=False,
        header=False,
        na_rep="\\N"
    )

    buffer.seek(0)

    cursor = conn.cursor()

    cursor.copy_expert(
        """
        COPY transactions
        (
            invoice,
            stock_code,
            description,
            quantity,
            invoice_date,
            price,
            customer_id,
            country,
            is_cancelled,
            is_return,
            is_zero_price,
            revenue
        )
        FROM STDIN
        WITH (
            FORMAT CSV,
            NULL '\\N'
        )
        """,
        buffer
    )

    conn.commit()

    cursor.close()

    print(
        f"Transactions loaded: "
        f"{len(transaction_df):,}"
    )


# ============================================================
# LOAD DAILY METRICS
# ============================================================

def load_daily_metrics(conn, df):

    print("\nCalculating daily metrics...")

    df = df.copy()

    df["InvoiceDate"] = pd.to_datetime(
        df["InvoiceDate"],
        errors="coerce"
    )

    daily = (
        df
        .groupby(
            df["InvoiceDate"].dt.date
        )
        .agg(
            revenue=("Revenue", "sum"),
            orders=("Invoice", "nunique"),
            customers=("Customer ID", "nunique"),
            units_sold=(
                "Quantity",
                lambda x: x[x > 0].sum()
            )
        )
        .reset_index()
    )

    daily.rename(
        columns={
            "InvoiceDate": "metric_date"
        },
        inplace=True
    )

    daily["aov"] = (
        daily["revenue"]
        / daily["orders"]
    )

    buffer = StringIO()

    daily.to_csv(
        buffer,
        index=False,
        header=False
    )

    buffer.seek(0)

    cursor = conn.cursor()

    cursor.copy_expert(
        """
        COPY daily_metrics
        (
            metric_date,
            revenue,
            orders,
            customers,
            units_sold,
            aov
        )
        FROM STDIN
        WITH CSV
        """,
        buffer
    )

    conn.commit()

    cursor.close()

    print(
        f"Daily metric rows loaded: "
        f"{len(daily):,}"
    )


# ============================================================
# VERIFY DATABASE
# ============================================================

def verify_database(conn):

    print("\n" + "=" * 60)
    print("DATABASE VERIFICATION")
    print("=" * 60)

    cursor = conn.cursor()

    tables = [
        "customers",
        "products",
        "transactions",
        "daily_metrics"
    ]

    for table in tables:

        cursor.execute(
            f"SELECT COUNT(*) FROM {table};"
        )

        count = cursor.fetchone()[0]

        print(
            f"{table:<20} {count:,} rows"
        )

    cursor.execute(
        """
        SELECT
            COUNT(*) AS rows,
            SUM(revenue) AS revenue
        FROM transactions;
        """
    )

    rows, revenue = cursor.fetchone()

    print("\nTransaction Revenue:")
    print(f"Rows   : {rows:,}")
    print(f"Revenue: £{revenue:,.2f}")

    cursor.close()


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 60)
    print("BUSINESS INVESTIGATOR")
    print("POSTGRESQL DATA LOADER")
    print("=" * 60)

    print(f"\nProject root:")
    print(PROJECT_ROOT)

    print(f"\nClean file:")
    print(CLEAN_FILE)

    if not CLEAN_FILE.exists():

        raise FileNotFoundError(
            f"Clean transaction file not found:\n{CLEAN_FILE}"
        )

    print("\nReading cleaned transaction data...")

    df = pd.read_csv(
        CLEAN_FILE,
        low_memory=False
    )

    print(
        f"Dataset loaded: "
        f"{len(df):,} rows"
    )

    print("\nConnecting to PostgreSQL...")

    conn = get_connection()

    print("Database connection successful.")

    try:

        load_customers(
            conn,
            df
        )

        load_products(
            conn,
            df
        )

        load_transactions(
            conn,
            df
        )

        load_daily_metrics(
            conn,
            df
        )

        verify_database(
            conn
        )

    except Exception as error:

        conn.rollback()

        print("\nERROR:")
        print(error)

        raise

    finally:

        conn.close()

        print(
            "\nDatabase connection closed."
        )


if __name__ == "__main__":
    main()