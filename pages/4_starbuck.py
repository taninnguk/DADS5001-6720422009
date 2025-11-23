
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from io import StringIO

st.set_page_config(page_title="Starbuck", page_icon="☕️")
# Minimal ISO 3166-1 alpha-2 to country name map for nicer labels
ISO2_COUNTRY = {
    "AD": "Andorra", "AE": "United Arab Emirates", "AF": "Afghanistan", "AG": "Antigua and Barbuda",
    "AI": "Anguilla", "AL": "Albania", "AM": "Armenia", "AO": "Angola", "AQ": "Antarctica",
    "AR": "Argentina", "AS": "American Samoa", "AT": "Austria", "AU": "Australia", "AW": "Aruba",
    "AX": "Åland Islands", "AZ": "Azerbaijan", "BA": "Bosnia and Herzegovina", "BB": "Barbados",
    "BD": "Bangladesh", "BE": "Belgium", "BF": "Burkina Faso", "BG": "Bulgaria", "BH": "Bahrain",
    "BI": "Burundi", "BJ": "Benin", "BL": "Saint Barthélemy", "BM": "Bermuda", "BN": "Brunei",
    "BO": "Bolivia", "BQ": "Bonaire, Sint Eustatius and Saba", "BR": "Brazil", "BS": "Bahamas",
    "BT": "Bhutan", "BV": "Bouvet Island", "BW": "Botswana", "BY": "Belarus", "BZ": "Belize",
    "CA": "Canada", "CC": "Cocos (Keeling) Islands", "CD": "DR Congo", "CF": "Central African Republic",
    "CG": "Republic of the Congo", "CH": "Switzerland", "CI": "Côte d’Ivoire", "CK": "Cook Islands",
    "CL": "Chile", "CM": "Cameroon", "CN": "China", "CO": "Colombia", "CR": "Costa Rica",
    "CU": "Cuba", "CV": "Cabo Verde", "CW": "Curaçao", "CX": "Christmas Island", "CY": "Cyprus",
    "CZ": "Czechia", "DE": "Germany", "DJ": "Djibouti", "DK": "Denmark", "DM": "Dominica",
    "DO": "Dominican Republic", "DZ": "Algeria", "EC": "Ecuador", "EE": "Estonia", "EG": "Egypt",
    "EH": "Western Sahara", "ER": "Eritrea", "ES": "Spain", "ET": "Ethiopia", "FI": "Finland",
    "FJ": "Fiji", "FK": "Falkland Islands", "FM": "Micronesia", "FO": "Faroe Islands", "FR": "France",
    "GA": "Gabon", "GB": "United Kingdom", "GD": "Grenada", "GE": "Georgia", "GF": "French Guiana",
    "GG": "Guernsey", "GH": "Ghana", "GI": "Gibraltar", "GL": "Greenland", "GM": "The Gambia",
    "GN": "Guinea", "GP": "Guadeloupe", "GQ": "Equatorial Guinea", "GR": "Greece",
    "GS": "South Georgia and the South Sandwich Islands", "GT": "Guatemala", "GU": "Guam",
    "GW": "Guinea-Bissau", "GY": "Guyana", "HK": "Hong Kong", "HM": "Heard Island and McDonald Islands",
    "HN": "Honduras", "HR": "Croatia", "HT": "Haiti", "HU": "Hungary", "ID": "Indonesia",
    "IE": "Ireland", "IL": "Israel", "IM": "Isle of Man", "IN": "India", "IO": "British Indian Ocean Territory",
    "IQ": "Iraq", "IR": "Iran", "IS": "Iceland", "IT": "Italy", "JE": "Jersey", "JM": "Jamaica",
    "JO": "Jordan", "JP": "Japan", "KE": "Kenya", "KG": "Kyrgyzstan", "KH": "Cambodia", "KI": "Kiribati",
    "KM": "Comoros", "KN": "Saint Kitts and Nevis", "KP": "North Korea", "KR": "South Korea",
    "KW": "Kuwait", "KY": "Cayman Islands", "KZ": "Kazakhstan", "LA": "Laos", "LB": "Lebanon",
    "LC": "Saint Lucia", "LI": "Liechtenstein", "LK": "Sri Lanka", "LR": "Liberia", "LS": "Lesotho",
    "LT": "Lithuania", "LU": "Luxembourg", "LV": "Latvia", "LY": "Libya", "MA": "Morocco", "MC": "Monaco",
    "MD": "Moldova", "ME": "Montenegro", "MF": "Saint Martin", "MG": "Madagascar", "MH": "Marshall Islands",
    "MK": "North Macedonia", "ML": "Mali", "MM": "Myanmar", "MN": "Mongolia", "MO": "Macao",
    "MP": "Northern Mariana Islands", "MQ": "Martinique", "MR": "Mauritania", "MS": "Montserrat",
    "MT": "Malta", "MU": "Mauritius", "MV": "Maldives", "MW": "Malawi", "MX": "Mexico", "MY": "Malaysia",
    "MZ": "Mozambique", "NA": "Namibia", "NC": "New Caledonia", "NE": "Niger", "NF": "Norfolk Island",
    "NG": "Nigeria", "NI": "Nicaragua", "NL": "Netherlands", "NO": "Norway", "NP": "Nepal", "NR": "Nauru",
    "NU": "Niue", "NZ": "New Zealand", "OM": "Oman", "PA": "Panama", "PE": "Peru",
    "PF": "French Polynesia", "PG": "Papua New Guinea", "PH": "Philippines", "PK": "Pakistan", "PL": "Poland",
    "PM": "Saint Pierre and Miquelon", "PN": "Pitcairn", "PR": "Puerto Rico", "PS": "Palestine", "PT": "Portugal",
    "PW": "Palau", "PY": "Paraguay", "QA": "Qatar", "RE": "Réunion", "RO": "Romania", "RS": "Serbia",
    "RU": "Russia", "RW": "Rwanda", "SA": "Saudi Arabia", "SB": "Solomon Islands", "SC": "Seychelles",
    "SD": "Sudan", "SE": "Sweden", "SG": "Singapore", "SH": "Saint Helena, Ascension and Tristan da Cunha",
    "SI": "Slovenia", "SJ": "Svalbard and Jan Mayen", "SK": "Slovakia", "SL": "Sierra Leone", "SM": "San Marino",
    "SN": "Senegal", "SO": "Somalia", "SR": "Suriname", "SS": "South Sudan", "ST": "São Tomé and Príncipe",
    "SV": "El Salvador", "SX": "Sint Maarten", "SY": "Syria", "SZ": "Eswatini", "TC": "Turks and Caicos Islands",
    "TD": "Chad", "TF": "French Southern Territories", "TG": "Togo", "TH": "Thailand", "TJ": "Tajikistan",
    "TK": "Tokelau", "TL": "Timor-Leste", "TM": "Turkmenistan", "TN": "Tunisia", "TO": "Tonga",
    "TR": "Turkey", "TT": "Trinidad and Tobago", "TV": "Tuvalu", "TW": "Taiwan", "TZ": "Tanzania",
    "UA": "Ukraine", "UG": "Uganda", "UM": "U.S. Outlying Islands", "US": "United States", "UY": "Uruguay",
    "UZ": "Uzbekistan", "VA": "Vatican City", "VC": "Saint Vincent and the Grenadines", "VE": "Venezuela",
    "VG": "British Virgin Islands", "VI": "U.S. Virgin Islands", "VN": "Vietnam", "VU": "Vanuatu",
    "WF": "Wallis and Futuna", "WS": "Samoa", "XK": "Kosovo", "YE": "Yemen", "YT": "Mayotte",
    "ZA": "South Africa", "ZM": "Zambia", "ZW": "Zimbabwe",
}

def to_country_name(value):
    if pd.isna(value):
        return value
    s = str(value).strip()
    if len(s) == 2 and s.upper() == s:
        return ISO2_COUNTRY.get(s, s)
    return s

def with_country_names(df: pd.DataFrame):
    if "Country" in df.columns:
        return df.assign(CountryName=df["Country"].apply(to_country_name))
    return df

st.set_page_config(page_title="CSV Visualizer", layout="wide")

@st.cache_data(show_spinner=False)
def load_csv(file_like, infer_datetime=True):
    df = pd.read_csv(file_like)
    if infer_datetime:
        for col in df.columns:
            if df[col].dtype == "object":
                try:
                    parsed = pd.to_datetime(df[col], errors="coerce", utc=False, infer_datetime_format=True)
                    valid_ratio = parsed.notna().mean()
                    # Treat as datetime if mostly valid timestamps
                    if valid_ratio > 0.85:
                        df[col] = parsed
                except Exception:
                    pass
    return df

def detect_roles(df: pd.DataFrame):
    num_cols = df.select_dtypes(include=["number"]).columns.tolist()
    dt_cols = df.select_dtypes(include=["datetime64[ns]", "datetimetz"]).columns.tolist()
    cat_cols = df.select_dtypes(include=["object", "category", "bool"]).columns.tolist()
    # Drop overly-unique object columns from categories to avoid huge multiselects
    pruned = []
    for c in cat_cols:
        if df[c].nunique(dropna=True) <= max(2, int(0.5 * len(df))):
            pruned.append(c)
    cat_cols = pruned
    return num_cols, dt_cols, cat_cols

def filter_ui(df: pd.DataFrame):
    st.sidebar.subheader("🔎 Filters")
    working = df.copy()

    num_cols, dt_cols, cat_cols = detect_roles(working)

    # Categorical filters
    with st.sidebar.expander("Categorical filters", expanded=False):
        for c in cat_cols:
            vals = working[c].dropna().unique().tolist()
            vals = sorted(vals, key=lambda x: str(x))
            selected = st.multiselect(f"{c}", options=vals, default=vals if len(vals) <= 25 else [])
            if selected:
                working = working[working[c].isin(selected)]

    # Numeric filters
    with st.sidebar.expander("Numeric filters", expanded=False):
        for c in num_cols:
            col_min, col_max = float(working[c].min()), float(working[c].max())
            if np.isfinite(col_min) and np.isfinite(col_max) and col_min != col_max:
                lo, hi = st.slider(f"{c}", min_value=col_min, max_value=col_max, value=(col_min, hi := col_max))
                working = working[(working[c] >= lo) & (working[c] <= hi)]

    # Datetime filters
    with st.sidebar.expander("Datetime filters", expanded=False):
        for c in dt_cols:
            if working[c].notna().any():
                min_dt, max_dt = working[c].min(), working[c].max()
                try:
                    start, end = st.date_input(
                        f"{c} range",
                        value=(min_dt.date(), max_dt.date()),
                        min_value=min_dt.date(),
                        max_value=max_dt.date(),
                    )
                    if isinstance(start, tuple) or isinstance(end, tuple):
                        # Streamlit sometimes returns tuples on first render; skip until proper values exist
                        pass
                    else:
                        working = working[(working[c].dt.date >= start) & (working[c].dt.date <= end)]
                except Exception:
                    pass

    return working

def agg_df(df: pd.DataFrame, groupby_cols, y_col, agg_fn):
    if not groupby_cols:
        return df
    if y_col is None:
        return df
    grouped = df.groupby(groupby_cols, dropna=False, as_index=False).agg({y_col: agg_fn})
    grouped.columns = groupby_cols + [f"{y_col} ({agg_fn})"]
    return grouped

def try_latlon(df: pd.DataFrame):
    # Try common latitude/longitude column names (case-insensitive), with a few forgiving variants
    lat_candidates = [
        c for c in df.columns
        if str(c).lower() in {"lat", "latitude", "y_lat", "y", "geo_lat"}
    ]
    lon_candidates = [
        c for c in df.columns
        if str(c).lower() in {"lon", "long", "lng", "longitude", "longtitude", "x_lon", "x", "geo_lon"}
    ]
    lat = lat_candidates[0] if lat_candidates else None
    lon = lon_candidates[0] if lon_candidates else None
    return lat, lon

def chart_builder(df: pd.DataFrame, filtered: pd.DataFrame):
    # Sidebar: chart builder
    st.sidebar.header("📈 Chart builder")
    num_cols, dt_cols, cat_cols = detect_roles(df)
    chart_type = st.sidebar.selectbox(
        "Chart type",
        ["Line", "Area", "Bar", "Scatter", "Histogram", "Box", "Pie", "Heatmap (corr)", "Map (lat/lon)"],
    )

    # Column selectors based on chart type
    agg_fn = st.sidebar.selectbox("Aggregation", ["sum", "mean", "median", "count"], index=0)

    if chart_type in {"Line", "Area", "Bar", "Scatter"}:
        x_candidates = dt_cols + cat_cols + num_cols
        y_candidates = num_cols

        x_col = st.sidebar.selectbox("X axis", x_candidates if x_candidates else df.columns.tolist())
        multi_y = chart_type in {"Line", "Area"}
        if multi_y:
            y_col = st.sidebar.multiselect("Y axis (choose one or more)", y_candidates, default=y_candidates[:1])
        else:
            y_col = st.sidebar.selectbox("Y axis", y_candidates if y_candidates else df.columns.tolist())

        color = st.sidebar.selectbox("Color / Group", ["(none)"] + cat_cols + dt_cols)
        groupby_cols = []
        if color and color != "(none)":
            groupby_cols.append(color)

        if chart_type in {"Bar"} and y_col and not isinstance(y_col, list):
            # allow optional groupby aggregation for bar
            group_by_on = st.sidebar.multiselect("Group by", cat_cols + dt_cols, default=groupby_cols)
            groupby_cols = group_by_on
            view_df = agg_df(filtered, groupby_cols, y_col, agg_fn) if groupby_cols else filtered
        else:
            view_df = filtered

        # Make chart
        if chart_type == "Line":
            if isinstance(y_col, list) and len(y_col) >= 1:
                fig = px.line(view_df, x=x_col, y=y_col)
            else:
                fig = px.line(view_df, x=x_col, y=y_col, color=color if color != "(none)" else None)
        elif chart_type == "Area":
            if isinstance(y_col, list) and len(y_col) >= 1:
                fig = px.area(view_df, x=x_col, y=y_col)
            else:
                fig = px.area(view_df, x=x_col, y=y_col, color=color if color != "(none)" else None)
        elif chart_type == "Bar":
            fig = px.bar(view_df, x=x_col if x_col in view_df.columns else groupby_cols[0] if groupby_cols else None,
                         y=view_df.columns[-1] if groupby_cols and view_df.columns[-1].startswith(str(y_col)) else y_col,
                         color=color if color != "(none)" else None, barmode="group")
        elif chart_type == "Scatter":
            size_opt = st.sidebar.selectbox("Bubble size (optional)", ["(none)"] + num_cols)
            fig = px.scatter(view_df, x=x_col, y=y_col,
                             color=color if color != "(none)" else None,
                             size=size_opt if size_opt != "(none)" else None,
                             trendline=None)
        st.plotly_chart(fig, use_container_width=True)

    elif chart_type == "Histogram":
        target = st.sidebar.selectbox("Column", num_cols + cat_cols)
        nbins = st.sidebar.slider("Bins", min_value=5, max_value=200, value=40)
        color = st.sidebar.selectbox("Color / Group", ["(none)"] + cat_cols)
        fig = px.histogram(filtered, x=target, nbins=nbins, color=color if color != "(none)" else None, barmode="overlay")
        st.plotly_chart(fig, use_container_width=True)

    elif chart_type == "Box":
        y_col = st.sidebar.selectbox("Y (numeric)", num_cols)
        x_col = st.sidebar.selectbox("X (category/date, optional)", ["(none)"] + cat_cols + dt_cols)
        color = st.sidebar.selectbox("Color / Group", ["(none)"] + cat_cols)
        fig = px.box(filtered, y=y_col, x=None if x_col == "(none)" else x_col, color=None if color == "(none)" else color)
        st.plotly_chart(fig, use_container_width=True)

    elif chart_type == "Pie":
        names = st.sidebar.selectbox("Names (category)", cat_cols if cat_cols else df.columns.tolist())
        values = st.sidebar.selectbox("Values (numeric)", num_cols if num_cols else df.columns.tolist())
        fig = px.pie(filtered, names=names, values=values, hole=0.25)
        st.plotly_chart(fig, use_container_width=True)

    elif chart_type == "Heatmap (corr)":
        nums = filtered.select_dtypes(include=["number"])
        if nums.shape[1] < 2:
            st.info("Need at least 2 numeric columns for a correlation heatmap.")
        else:
            corr = nums.corr(numeric_only=True)
            fig = px.imshow(corr, text_auto=True, aspect="auto", origin="lower", title="Correlation Heatmap")
            st.plotly_chart(fig, use_container_width=True)

    elif chart_type == "Map (lat/lon)":
        lat, lon = try_latlon(filtered)

        # Allow manual selection if auto-detection fails
        if not lat or not lon:
            st.info("Choose your latitude/longitude columns below (auto-detect failed).")
            numeric_cols = filtered.select_dtypes(include=["number"]).columns.tolist()
            lat = st.selectbox("Latitude column", ["(select)"] + numeric_cols, index=0)
            lon = st.selectbox("Longitude column", ["(select)"] + numeric_cols, index=0)
            if lat == "(select)" or lon == "(select)":
                st.stop()

        size_opt = st.sidebar.selectbox("Bubble size (optional)", ["(none)"] + detect_roles(filtered)[0])
        color = st.sidebar.selectbox("Color / Group", ["(none)"] + detect_roles(filtered)[2])

        # Option to render with Plotly or Streamlit's native map
        map_engine = st.sidebar.radio("Map engine", ["Plotly (OSM)", "Streamlit (st.map)"], index=0, help="Choose plotting backend for the map.")

        if map_engine == "Plotly (OSM)":
            fig = px.scatter_mapbox(
                filtered,
                lat=lat,
                lon=lon,
                color=None if color == "(none)" else color,
                size=None if size_opt == "(none)" else size_opt,
                zoom=3,
                height=600,
            )
            fig.update_layout(mapbox_style="open-street-map", margin=dict(l=0, r=0, t=40, b=0))
            st.plotly_chart(fig, use_container_width=True)
        else:
            # Streamlit's st.map expects 'lat' and 'lon' columns
            map_df = filtered.rename(columns={lat: "lat", lon: "lon"})
            st.map(map_df[["lat", "lon"]], zoom=3, use_container_width=True)

def main():
    st.title("📊 CSV Visualizer (Streamlit)")

    st.sidebar.header("📁 Data source")
    default_path = "directory.csv"
    use_default = st.sidebar.toggle("Use default CSV path", value=True, help="If off, upload your own CSV.")

    df = None
    if use_default:
        try:
            df = load_csv(default_path)
            st.success(f"Loaded default CSV: {default_path}")
        except Exception as e:
            st.warning(f"Could not load default path. Error: {e}. Please upload a file below.")
    if df is None:
        up = st.sidebar.file_uploader("Upload a CSV", type=["csv"])
        if up:
            df = load_csv(up)

    if df is None or df.empty:
        st.info("Upload a CSV or enable the default path to begin.")
        st.stop()

    st.caption(f"Rows: {len(df):,} | Columns: {len(df.columns)}")
    st.dataframe(df.head(200), use_container_width=True)

    # View selector and filters
    st.sidebar.header("🧭 View")
    view_mode = st.sidebar.radio("Select view", ["Executive Summary", "Chart builder"], index=0)
    filtered = filter_ui(df)

    if filtered.empty:
        st.warning("No data after filters. Adjust your filters.")
        st.stop()

    if view_mode == "Executive Summary":
        st.subheader("Executive Summary")
        # Prepare enriched view with full country names
        summary = with_country_names(filtered)

        # Key metrics
        total = len(summary)
        countries = summary["CountryName"].nunique(dropna=True) if "CountryName" in summary.columns else None
        cities = summary["City"].nunique(dropna=True) if "City" in summary.columns else None
        ownerships = summary["Ownership Type"].nunique(dropna=True) if "Ownership Type" in summary.columns else None
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Locations", f"{total:,}")
        if countries is not None:
            c2.metric("Countries", f"{countries:,}")
        if cities is not None:
            c3.metric("Cities", f"{cities:,}")
        if ownerships is not None:
            c4.metric("Ownership Types", f"{ownerships:,}")

        # Top countries
        if "CountryName" in summary.columns:
            st.markdown("**Top Countries by Locations**")
            top_c = (
                summary.groupby("CountryName", dropna=False)
                .size()
                .reset_index(name="count").sort_values("count", ascending=False).head(15)
            )
            fig_c = px.bar(top_c, x="CountryName", y="count")
            st.plotly_chart(fig_c, use_container_width=True)

        # Top cities (optionally within a country)
        if "City" in summary.columns:
            scope_df = summary
            if "CountryName" in summary.columns:
                country_options = ["(All)"] + sorted(summary["CountryName"].dropna().unique().tolist())
                sel_country = st.selectbox("Focus country (optional)", country_options)
                if sel_country != "(All)":
                    scope_df = summary[summary["CountryName"] == sel_country]
            st.markdown("**Top Cities by Locations**")
            top_city = (
                scope_df.groupby("City", dropna=False)
                .size()
                .reset_index(name="count").sort_values("count", ascending=False).head(15)
            )
            fig_city = px.bar(top_city, x="City", y="count")
            st.plotly_chart(fig_city, use_container_width=True)

        # Map overview
        lat, lon = try_latlon(summary)
        if lat and lon:
            st.markdown("**Location Map**")
            color_col = None
            if "Ownership Type" in summary.columns:
                color_col = "Ownership Type"
            elif "CountryName" in summary.columns:
                color_col = "CountryName"
            fig_map = px.scatter_mapbox(
                summary,
                lat=lat,
                lon=lon,
                color=color_col,
                zoom=1.2,
                height=520,
            )
            fig_map.update_layout(mapbox_style="open-street-map", margin=dict(l=0, r=0, t=30, b=0))
            st.plotly_chart(fig_map, use_container_width=True)
        else:
            st.info("No latitude/longitude columns found for the map.")

        # Light textual highlights
        if "CountryName" in summary.columns:
            by_country = summary["CountryName"].value_counts().head(5)
            highlights = ", ".join([f"{idx} ({val})" for idx, val in by_country.items()])
            st.caption(f"Top markets by location count: {highlights}.")

    else:
        chart_builder(df, filtered)

    # Data download
    st.divider()
    st.subheader("📥 Download filtered data")
    csv_bytes = filtered.to_csv(index=False).encode("utf-8")
    st.download_button("Download CSV", data=csv_bytes, file_name="filtered_data.csv", mime="text/csv")

    # Basic profile
    with st.expander("ℹ️ Data profile (quick)"):
        st.write("**Column types**")
        st.write(pd.DataFrame({
            "column": df.columns,
            "dtype": [str(df[c].dtype) for c in df.columns],
            "n_unique": [df[c].nunique(dropna=True) for c in df.columns],
            "nulls": [int(df[c].isna().sum()) for c in df.columns],
        }))

if __name__ == "__main__":
    main()
