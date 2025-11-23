# CSV Visualizer (Streamlit)

A ready-to-run Streamlit app to explore your CSV (auto-detects datetimes, builds filters, and supports multiple chart types).

## Quickstart

```bash
python -m venv .venv && source .venv/bin/activate  # on Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

By default the app tries to open `/mnt/data/directory.csv`. Turn that toggle off in the sidebar to upload a file.

## Features
- Auto type detection (numeric / datetime / categorical)
- Sidebar filters (multiselects, sliders, date ranges)
- Chart types: Line, Area, Bar (with group-by aggregation), Scatter, Histogram, Box, Pie, Correlation Heatmap, Map (lat/lon)
- Download filtered data
