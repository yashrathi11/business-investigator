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

    # Use a filtered view instead of making a full DataFrame copy.
    customer_mask = df["Customer ID"].notna()

    customer_data = df.loc[
        customer_mask,
        [
            "Customer ID",
            "Revenue",
            "Invoice",
            "InvoiceDate",
        ],
    ]

    total_customers = (
        customer_data["Customer ID"].nunique()
    )

    revenue_per_customer = (
        customer_data["Revenue"].sum() / total_customers
        if total_customers > 0
        else 0.0
    )

    # Number of unique orders per customer
    order_frequency = (
        customer_data
        .groupby(
            "Customer ID",
            observed=True,
        )["Invoice"]
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
            [
                "StockCode",
                "Description",
            ],
            dropna=False,
            observed=True,
        )
        .agg(
            revenue=("Revenue", "sum"),
            units_sold=("Quantity", "sum"),
            orders=("Invoice", "nunique"),
        )
        .reset_index()
    )

    top_products_by_revenue = (
        product_metrics
        .nlargest(
            top_n,
            "revenue",
        )
        .reset_index(drop=True)
    )

    top_products_by_units = (
        product_metrics
        .nlargest(
            top_n,
            "units_sold",
        )
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

    Units sold is defined as net quantity:
    positive sales quantity minus returned quantity.
    """

    # Convert the existing column without creating
    # another full DataFrame.
    invoice_dates = pd.to_datetime(
        df["InvoiceDate"],
        errors="coerce",
    )

    daily = (
        df
        .groupby(
            invoice_dates.dt.date
        )
        .agg(
            revenue=("Revenue", "sum"),
            orders=("Invoice", "nunique"),
            customers=("Customer ID", "nunique"),
            units_sold=("Quantity", "sum"),
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

    invoice_dates = pd.to_datetime(
        df["InvoiceDate"],
        errors="coerce",
    )

    month_values = (
        invoice_dates
        .dt.to_period("M")
        .astype(str)
    )

    monthly = (
        df
        .groupby(
            month_values
        )
        .agg(
            revenue=("Revenue", "sum"),
            orders=("Invoice", "nunique"),
            customers=("Customer ID", "nunique"),
            units_sold=(
                "Quantity",
                lambda x: x[x > 0].sum(),
            ),
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