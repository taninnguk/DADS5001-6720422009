from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Project Management", page_icon="📊", layout="wide")


def fmt_m(value: float) -> str:
    if value is None or pd.isna(value):
        return "0"
    return f"{value/1_000_000:,.2f} M"


def clean_project(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    df.rename(columns={"Q'ty": "Qty"}, inplace=True)
    df = df.dropna(how="all")

    date_cols = [
        "PO Date",
        "Original Delivery Date",
        "Estimated shipdate",
        "Actual shipdate",
        "Waranty end",
    ]
    numeric_cols = [
        "Project year",
        "Order number",
        "Project Value",
        "Balance",
        "Progress",
        "Number of Status",
        "Max LD",
        "Max LD Amount",
        "Extra cost",
        "Change order amount",
        "Storage fee amount",
        "Days late",
        "Qty",
    ]

    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if "Progress" in df.columns:
        df["Progress"] = df["Progress"].clip(lower=0, upper=1)
    return df


def clean_invoice(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    numeric_cols = [
        "Project year",
        "SEQ",
        "Total amount",
        "Percentage of amount",
        "Invoice value",
        "Plan Delayed",
        "Actual Delayed",
        "Claim Plan 2025",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    date_cols = [
        "Invoice plan date",
        "Issued Date",
        "Invoice due date",
        "Plan payment date",
        "Expected Payment date",
        "Actual Payment received date",
    ]
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    return df


@st.cache_data(ttl=300)
def load_sheet_data() -> tuple[pd.DataFrame, pd.DataFrame, str]:
    """Load data from Google Sheets, falling back to the local Excel file if needed."""
    gsheets_error = None

    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        project_raw = conn.read(worksheet="Project", ttl="5m")
        invoice_raw = conn.read(worksheet="Invoice", ttl="5m")
        if project_raw is None or project_raw.empty:
            raise ValueError("Google Sheets returned no rows for 'Project'.")
        if invoice_raw is None:
            invoice_raw = pd.DataFrame()
        return clean_project(project_raw), clean_invoice(invoice_raw), "gsheets"
    except Exception as exc:  # noqa: BLE001
        gsheets_error = exc

    fallback_path = Path(__file__).resolve().parent.parent / "BI Project status_Prototype-2.xlsx"
    absolute_path = Path("/Users/sashimild/Desktop/Nguk/NIDA MASTER DEGREE/5001/DADS5001-6720422009/BI Project status_Prototype-2.xlsx")
    if not fallback_path.exists() and absolute_path.exists():
        fallback_path = absolute_path
    if not fallback_path.exists():
        raise RuntimeError("Unable to load from Google Sheets and fallback Excel file is missing.") from gsheets_error

    try:
        workbook = pd.ExcelFile(fallback_path)
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"Unable to read fallback Excel file: {fallback_path}") from exc

    project_sheet = "Project" if "Project" in workbook.sheet_names else workbook.sheet_names[0]
    invoice_sheet = "Invoice" if "Invoice" in workbook.sheet_names else None

    project_raw = workbook.parse(project_sheet)
    invoice_raw = workbook.parse(invoice_sheet) if invoice_sheet else pd.DataFrame()

    return clean_project(project_raw), clean_invoice(invoice_raw), "excel"


try:
    project_df, invoice_df, data_source = load_sheet_data()
except Exception as exc:  # noqa: BLE001
    data_source = "error"
    st.title("Project Management Dashboard")
    st.error(
        f"Data could not be loaded from Google Sheets or fallback Excel.\n\n{exc}",
        icon="🚫",
    )
    st.stop()

st.title("Project Management Dashboard")
if data_source == "gsheets":
    st.caption("✅ Connected to Google Sheets")
elif data_source == "excel":
    st.caption("📄 Loaded from fallback Excel (Google Sheets unavailable)")
else:
    st.caption("🚫 Data not loaded")

with st.sidebar:
    st.header("Filters")
    engineer_filter = st.multiselect(
        "Project engineer",
        sorted(project_df["Project Engineer"].dropna().unique()),
        default=sorted(project_df["Project Engineer"].dropna().unique()),
    )
    year_filter = st.multiselect(
        "Project year",
        sorted(project_df["Project year"].dropna().unique()),
        default=sorted(project_df["Project year"].dropna().unique()),
    )
    status_filter = st.multiselect(
        "Status",
        sorted(project_df["Status"].dropna().unique()),
        default=sorted(project_df["Status"].dropna().unique()),
    )
    phrase_filter = st.multiselect(
        "Project phrase",
        sorted(project_df["Project Phrase"].dropna().unique()),
    )
    customer_filter = st.multiselect(
        "Customer",
        sorted(project_df["Customer"].dropna().unique()),
    )

filtered = project_df.copy()
if engineer_filter:
    filtered = filtered[filtered["Project Engineer"].isin(engineer_filter)]
if year_filter:
    filtered = filtered[filtered["Project year"].isin(year_filter)]
if status_filter:
    filtered = filtered[filtered["Status"].isin(status_filter)]
if phrase_filter:
    filtered = filtered[filtered["Project Phrase"].isin(phrase_filter)]
if customer_filter:
    filtered = filtered[filtered["Customer"].isin(customer_filter)]

if filtered.empty:
    st.warning("No records match the current filters.")
    st.stop()

total_value = filtered["Project Value"].sum()
balance_sum = filtered["Balance"].sum()
avg_progress_pct = filtered["Progress"].mean()
avg_progress_pct = 0 if pd.isna(avg_progress_pct) else avg_progress_pct * 100
order_count = filtered["Order number"].nunique()

product_counts = {}
for product_name in ["Control Panel", "Heater", "Vessel"]:
    product_counts[product_name] = (
        filtered.loc[filtered["Product"].str.contains(product_name, case=False, na=False), "Qty"]
        .sum()
    )

status_totals = filtered["Status"].value_counts()

st.markdown("### Portfolio overview")
metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
metric_col1.metric("Project value", fmt_m(total_value))
metric_col2.metric("Balance", fmt_m(balance_sum))
metric_col3.metric("Avg. progress", f"{avg_progress_pct:,.0f}%")
metric_col4.metric("Orders", int(order_count))

# Value and delivery at a glance.
st.markdown("### Value and delivery")
chart_col_left, chart_col_right = st.columns([1.35, 0.65])

with chart_col_left:
    st.caption("Project value vs balance by order")
    order_summary = (
        filtered.groupby("Order number", dropna=True)[["Project Value", "Balance"]]
        .sum()
        .reset_index()
        .sort_values("Project Value", ascending=False)
    )
    if not order_summary.empty:
        long_orders = order_summary.melt(
            id_vars="Order number",
            value_vars=["Project Value", "Balance"],
            var_name="Metric",
            value_name="Amount",
        )
        order_fig = px.bar(
            long_orders,
            x="Order number",
            y="Amount",
            color="Metric",
            barmode="group",
            labels={"Amount": "Amount", "Order number": "Order number"},
        )
        order_fig.update_layout(showlegend=True, margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(order_fig, use_container_width=True)
    else:
        st.info("No order number data to display.")

with chart_col_right:
    st.caption("Average progress")
    gauge = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=avg_progress_pct,
            number={"suffix": "%", "valueformat": ".0f"},
            gauge={
                "axis": {"range": [0, 100]},
                "bar": {"color": "#1f77b4"},
                "steps": [
                    {"range": [0, 50], "color": "#f4d6d6"},
                    {"range": [50, 80], "color": "#f9e9c5"},
                    {"range": [80, 100], "color": "#d6f4da"},
                ],
            },
        )
    )
    st.plotly_chart(gauge, use_container_width=True)

    st.caption("Status + units")
    status_cols = st.columns(2)
    status_cols[0].metric("Delayed", int(status_totals.get("Delayed", 0)))
    status_cols[0].metric("On track", int(status_totals.get("On track", 0)))
    status_cols[1].metric("Shipped", int(status_totals.get("Shipped", 0)))
    product_cols = st.columns(3)
    product_cols[0].metric("Control Panel", int(product_counts.get("Control Panel", 0)))
    product_cols[1].metric("Heater", int(product_counts.get("Heater", 0)))
    product_cols[2].metric("Vessel", int(product_counts.get("Vessel", 0)))

# Mix by engineer and customer.
st.markdown("### Portfolio mix")
pie_col1, pie_col2 = st.columns(2)
with pie_col1:
    engineer_value = (
        filtered.groupby("Project Engineer", as_index=False)["Project Value"]
        .sum()
        .sort_values("Project Value", ascending=False)
    )
    st.caption("Project value by engineer")
    if not engineer_value.empty:
        eng_fig = px.pie(
            engineer_value,
            names="Project Engineer",
            values="Project Value",
            hole=0.4,
        )
        st.plotly_chart(eng_fig, use_container_width=True)
    else:
        st.info("No engineer data.")
with pie_col2:
    customer_value = (
        filtered.groupby("Customer", as_index=False)["Project Value"]
        .sum()
        .sort_values("Project Value", ascending=False)
    )
    st.caption("Project value by customer")
    if not customer_value.empty:
        cust_fig = px.pie(
            customer_value,
            names="Customer",
            values="Project Value",
            hole=0.4,
        )
        st.plotly_chart(cust_fig, use_container_width=True)
    else:
        st.info("No customer data.")

# Operations snapshots.
st.markdown("### Operations")
table_col_left, table_col_right = st.columns([1.25, 1])

with table_col_left:
    st.caption("Manufactured by / Product (sum of Qty)")
    qty_by_manu = (
        filtered.groupby(["Manufactured by", "Product"], as_index=False)["Qty"]
        .sum()
        .sort_values("Qty", ascending=False)
    )
    if not qty_by_manu.empty:
        manu_fig = px.bar(
            qty_by_manu,
            x="Qty",
            y="Manufactured by",
            color="Product",
            orientation="h",
            labels={"Qty": "Units", "Manufactured by": "Manufacturer"},
        )
        manu_fig.update_layout(margin=dict(l=10, r=10, t=30, b=10), height=360)
        st.plotly_chart(manu_fig, use_container_width=True)
    else:
        st.info("No manufacturing data.")

with table_col_right:
    st.caption("Status and phrases")
    total_status_rows = len(filtered)
    metric_a, metric_b = st.columns(2)
    metric_a.metric("Status rows", total_status_rows)
    metric_b.metric("Orders", order_count)

    phrase_counts = filtered["Project Phrase"].value_counts().rename_axis("Project Phrase").reset_index(name="Count")
    if not phrase_counts.empty:
        phrase_fig = px.bar(
            phrase_counts.sort_values("Count"),
            x="Count",
            y="Project Phrase",
            orientation="h",
            labels={"Count": "Projects"},
        )
        phrase_fig.update_layout(margin=dict(l=10, r=10, t=30, b=10), height=360)
        st.plotly_chart(phrase_fig, use_container_width=True)
    else:
        st.info("No phrase data.")

st.markdown("### Project details")
display_cols = [
    "Project",
    "Customer",
    "Project Engineer",
    "Project year",
    "Status",
    "Project Phrase",
    "Product",
    "Order number",
    "Progress",
    "Estimated shipdate",
    "Actual shipdate",
    "Balance",
    "Project Value",
]
existing_cols = [c for c in display_cols if c in filtered.columns]
st.dataframe(filtered[existing_cols].sort_values("Project"), use_container_width=True)
