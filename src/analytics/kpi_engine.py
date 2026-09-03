import pandas as pd

# ============================================================
# REVENUE
# ============================================================

def calculate_revenue(df):
    """
    Calculate total revenue from transactions.
    """

    return df["Revenue"].sum()


# ============================================================
# AVERAGE ORDER VALUE
# ============================================================

def calculate_aov(df):
    """
    Calculate Average Order Value (AOV).

    AOV = Total Revenue / Number of Unique Orders
    """

    total_revenue = calculate_revenue(df)

    total_orders = df["Invoice"].nunique()

    if total_orders == 0:
        return 0.0

    return total_revenue / total_orders


# ============================================================
# CUSTOMER METRICS
# ============================================================

def calculate_customer_metrics(df):
    """
    Calculate customer-level business metrics.

    Returns:
        total_customers
        new_customers
        repeat_customers
        repeat_customer_rate
        revenue_per_customer
    """

    customer_df = df[
        df["Customer ID"].notna()
    ].copy()

    total_customers = customer_df["Customer ID"].nunique()

    revenue_per_customer = (
        customer_df["Revenue"].sum() / total_customers
        if total_customers > 0
        else 0.0
    )

    # First purchase date for every customer
    first_purchase = (
        customer_df
        .groupby("Customer ID")["InvoiceDate"]
        .min()
    )

    # Number of unique orders per customer
    order_frequency = (
        customer_df
        .groupby("Customer ID")["Invoice"]
        .nunique()
    )

    new_customers = (
        order_frequency.eq(1).sum()
    )

    repeat_customers = (
        order_frequency.gt(1).sum()
    )

    repeat_customer_rate = (
        repeat_customers / total_customers * 100
        if total_customers > 0
        else 0.0
    )

    return {
        "total_customers": int(total_customers),
        "new_customers": int(new_customers),
        "repeat_customers": int(repeat_customers),
        "repeat_customer_rate": float(
            repeat_customer_rate
        ),
        "revenue_per_customer": float(
            revenue_per_customer
        ),
    }


# ============================================================
# PRODUCT METRICS
# ============================================================

def calculate_product_metrics(df, top_n=10):
    """
    Calculate product-level revenue and unit metrics.

    Returns:
        top_products_by_revenue
        top_products_by_units
    """

    product_metrics = (
        df
        .groupby(
            ["StockCode", "Description"],
            dropna=False
        )
        .agg(
            revenue=("Revenue", "sum"),
            units_sold=("Quantity", "sum"),
            orders=("Invoice", "nunique")
        )
        .reset_index()
    )

    top_products_by_revenue = (
        product_metrics
        .sort_values(
            "revenue",
            ascending=False
        )
        .head(top_n)
        .reset_index(drop=True)
    )

    top_products_by_units = (
        product_metrics
        .sort_values(
            "units_sold",
            ascending=False
        )
        .head(top_n)
        .reset_index(drop=True)
    )

    return {
        "top_products_by_revenue":
            top_products_by_revenue,

        "top_products_by_units":
            top_products_by_units,
    }


# ============================================================
# GROWTH
# ============================================================

def calculate_growth(current_value, previous_value):
    """
    Calculate percentage growth.

    Growth % =
        ((Current - Previous) / Previous) * 100
    """

    if previous_value == 0:
        return None

    return (
        (current_value - previous_value)
        / previous_value
    ) * 100


# ============================================================
# DAILY METRICS
# ============================================================

def calculate_daily_metrics(df):
    """
    Calculate daily business metrics.
    """

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

    daily["aov"] = (
        daily["revenue"]
        / daily["orders"]
    )

    return daily


# ============================================================
# MONTHLY METRICS
# ============================================================

def calculate_monthly_metrics(df):
    """
    Calculate monthly business metrics.
    """

    temp = df.copy()

    temp["InvoiceDate"] = pd.to_datetime(
        temp["InvoiceDate"],
        errors="coerce"
    )

    temp["month"] = (
        temp["InvoiceDate"]
        .dt.to_period("M")
        .astype(str)
    )

    monthly = (
        temp
        .groupby("month")
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

    monthly["aov"] = (
        monthly["revenue"]
        / monthly["orders"]
    )

    monthly["growth_pct"] = (
        monthly["revenue"]
        .pct_change()
        * 100
    )

    return monthly