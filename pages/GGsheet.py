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
def load_sheet_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    conn = st.connection("gsheets", type=GSheetsConnection)
    project_raw = conn.read(worksheet="Project", ttl="5m")
    invoice_raw = conn.read(worksheet="Invoice", ttl="5m")
    if project_raw is None or project_raw.empty:
        raise ValueError("Google Sheets returned no rows for 'Project'.")
    if invoice_raw is None:
        invoice_raw = pd.DataFrame()
    return clean_project(project_raw), clean_invoice(invoice_raw)


try:
    project_df, invoice_df = load_sheet_data()
    connection_ok = True
except Exception as exc:
    connection_ok = False
    st.title("Project Management Dashboard")
    st.error("Not connected to Google Sheets. Please verify access and the 'Project'/'Invoice' tabs.", icon="🚫")
    st.stop()

st.title("Project Management Dashboard")
st.caption("✅ Connected to Google Sheets" if connection_ok else "🚫 Not connected")

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

product_counts = {}
for product_name in ["Control Panel", "Heater", "Vessel"]:
    product_counts[product_name] = (
        filtered.loc[filtered["Product"].str.contains(product_name, case=False, na=False), "Qty"]
        .sum()
    )

status_totals = filtered["Status"].value_counts()

metric_col1, metric_col2, metric_col3, metric_col4 = st.columns([1, 1, 1.2, 1])
metric_col1.metric("Sum of Project Value", fmt_m(total_value))
metric_col2.metric("Sum of Balance", fmt_m(balance_sum))
with metric_col3:
    st.markdown("**Product units**")
    p1, p2, p3 = st.columns(3)
    p1.metric("Control Panel", int(product_counts.get("Control Panel", 0)))
    p2.metric("Heater", int(product_counts.get("Heater", 0)))
    p3.metric("Vessel", int(product_counts.get("Vessel", 0)))
with metric_col4:
    st.markdown("**Status counts**")
    st.metric("Delayed", int(status_totals.get("Delayed", 0)))
    st.metric("On track", int(status_totals.get("On track", 0)))
    st.metric("Shipped", int(status_totals.get("Shipped", 0)))

chart_col_left, chart_col_right = st.columns([1.4, 1])

with chart_col_left:
    st.subheader("Sum of Project Value and Balance by order number")
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
        order_fig.update_layout(showlegend=True)
        st.plotly_chart(order_fig, use_container_width=True)
    else:
        st.info("No order number data to display.")

with chart_col_right:
    st.subheader("Average of Progress")
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

    pie_col1, pie_col2 = st.columns(2)
    with pie_col1:
        engineer_value = (
            filtered.groupby("Project Engineer", as_index=False)["Project Value"]
            .sum()
            .sort_values("Project Value", ascending=False)
        )
        st.caption("Sum of Project Value by Project Engineer")
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
        st.caption("Sum of Project Value by Customer")
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

table_col_left, table_col_right = st.columns([1.2, 1])

with table_col_left:
    st.subheader("Manufactured by / Product (sum of Qty)")
    qty_by_manu = (
        filtered.groupby(["Manufactured by", "Product"], as_index=False)["Qty"]
        .sum()
        .sort_values("Qty", ascending=False)
    )
    st.dataframe(qty_by_manu, use_container_width=True, height=320)

with table_col_right:
    st.subheader("Status and orders")
    total_status_rows = len(filtered)
    order_count = filtered["Order number"].nunique()
    metric_a, metric_b = st.columns(2)
    metric_a.metric("Status", total_status_rows)
    metric_b.metric("Amount of order", order_count)

    st.subheader("Project phrases")
    phrase_counts = filtered["Project Phrase"].value_counts()
    st.dataframe(
        phrase_counts.rename_axis("Project Phrase").reset_index(name="Count"),
        use_container_width=True,
        height=240,
    )

st.subheader("Project details")
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

