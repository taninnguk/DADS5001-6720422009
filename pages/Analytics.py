import csv
import json
from io import BytesIO

import pandas as pd
import streamlit as st

try:
    from streamlit_sortables import sort_items

    SORTABLE_READY = True
except Exception:
    # หากยังไม่ติดตั้ง lib นี้ จะแจ้งเตือนใน UI ภายหลัง
    SORTABLE_READY = False


def format_step_label(step: dict, index: int) -> str:
    """สร้างข้อความสั้นๆ ไว้แสดง/ลากเรียงลำดับ"""
    src_filter = step["source"]["filter"]
    tgt_filter = step["target"]["filter"]
    src_kw = src_filter.get("keyword_value") or src_filter.get("keyword_column")
    tgt_kw = tgt_filter.get("keyword_value") or tgt_filter.get("keyword_column")
    op = step["operator_block"]["operator_type"]
    return f"{index}. {step['source']['file_label']}[{src_kw}] -> {step['target']['file_label']}[{tgt_kw}] | {op}"


def build_flow_chart(steps: list[dict]) -> str:
    """สร้าง Graphviz DOT สำหรับภาพรวม flow ของ steps"""
    lines = [
        "digraph rule_flow {",
        "rankdir=LR;",
        'node [shape=box style="rounded,filled" color="#3b82f6" fillcolor="#eef2ff" fontname="Arial"];',
    ]
    for idx, step in enumerate(steps, 1):
        src_filter = step["source"]["filter"]
        tgt_filter = step["target"]["filter"]
        label_parts = [
            f"Step {idx}",
            f"{step['source']['file_label']} ({src_filter.get('keyword_value') or src_filter.get('keyword_column')})",
            f"{step['target']['file_label']} ({tgt_filter.get('keyword_value') or tgt_filter.get('keyword_column')})",
            f"operator: {step['operator_block']['operator_type']}",
        ]
        label = "\\n".join(part for part in label_parts if part)
        label = label.replace('"', '\\"')
        lines.append(f's{idx} [label="{label}"];')
        if idx > 1:
            lines.append(f"s{idx-1} -> s{idx};")
    lines.append("}")
    return "\n".join(lines)


def detect_separator(file_bytes: bytes) -> str:
    """ลองเดา delimiter จาก sample ของไฟล์"""
    sample = file_bytes[:2048].decode("utf-8", errors="ignore")
    common_delims = [",", ";", "\t", "|", ":"]
    try:
        sniff = csv.Sniffer().sniff(sample, delimiters=",".join(common_delims))
        delim = sniff.delimiter
    except Exception:
        delim = ","
    return delim if delim in common_delims else ","


def describe_separator(sep: str) -> str:
    names = {",": "comma (,)", ";": "semicolon (;)", "\t": "tab (\\t)", "|": "pipe (|)", ":": "colon (:)"}
    return names.get(sep, sep)


def get_value_from_df(dfs: dict, file_label: str, filter_cfg: dict, value_column: str):
    """ดึงค่าจาก df ตาม filter (ถ้า value ว่างจะใช้ทั้งตาราง)"""
    if file_label not in dfs:
        return None, f"File '{file_label}' ยังไม่ถูกอัปโหลด"
    df = dfs[file_label]
    key_col = filter_cfg.get("keyword_column")
    key_val = filter_cfg.get("keyword_value")
    if key_col not in df.columns:
        return None, f"ไม่พบคอลัมน์ {key_col} ในไฟล์ {file_label}"
    filtered = df if key_val in (None, "",) else df[df[key_col] == key_val]
    if filtered.empty:
        return None, f"ไม่พบแถวที่ {key_col} = {key_val} ในไฟล์ {file_label}"
    if value_column not in df.columns:
        return None, f"ไม่พบ value column {value_column} ในไฟล์ {file_label}"
    return filtered.iloc[0][value_column], None


def to_number(value):
    if value is None or pd.isna(value):
        return None
    try:
        num = pd.to_numeric(value, errors="coerce")
        if pd.isna(num):
            return None
        return float(num)
    except Exception:
        return None


def evaluate_step(step: dict, dfs: dict) -> dict:
    """ประเมิน step เดียวแล้วคืนผลลัพธ์ pass/fail/error"""
    src_val, src_err = get_value_from_df(
        dfs,
        step["source"]["file_label"],
        step["source"]["filter"],
        step["source"]["value_column"],
    )
    if src_err:
        return {"step_id": step["step_id"], "status": "error", "reason": src_err, "source_value": None, "target_value": None}

    tgt_val, tgt_err = get_value_from_df(
        dfs,
        step["target"]["file_label"],
        step["target"]["filter"],
        step["target"]["value_column"],
    )
    if tgt_err:
        return {"step_id": step["step_id"], "status": "error", "reason": tgt_err, "source_value": src_val, "target_value": None}

    op = step["operator_block"]["operator_type"]
    if op == "equal":
        ok = src_val == tgt_val
        reason = "ค่าเท่ากัน" if ok else "ค่าไม่เท่ากัน"
    elif op == "not_equal":
        ok = src_val != tgt_val
        reason = "ค่าไม่เท่ากัน" if ok else "ค่าเท่ากัน"
    elif op == "abs_diff_pct_max":
        max_pct = step["operator_block"].get("max_pct")
        src_num = to_number(src_val)
        tgt_num = to_number(tgt_val)
        if max_pct is None:
            return {"step_id": step["step_id"], "status": "error", "reason": "ไม่ได้กำหนด max_pct", "source_value": src_val, "target_value": tgt_val}
        if src_num is None or tgt_num is None:
            return {"step_id": step["step_id"], "status": "error", "reason": "ค่าไม่สามารถแปลงเป็นตัวเลขได้", "source_value": src_val, "target_value": tgt_val}
        denom = max(abs(tgt_num), 1e-9)
        diff_pct = abs(src_num - tgt_num) / denom
        ok = diff_pct <= max_pct
        reason = f"diff {diff_pct*100:.2f}% (limit {max_pct*100:.2f}%)"
    else:
        return {"step_id": step["step_id"], "status": "error", "reason": f"ไม่รู้จัก operator {op}", "source_value": src_val, "target_value": tgt_val}

    return {
        "step_id": step["step_id"],
        "status": "pass" if ok else "fail",
        "reason": reason,
        "source_value": src_val,
        "target_value": tgt_val,
    }


st.set_page_config(page_title="Rule-based Mapping Builder", layout="wide")
st.title("Rule-based Mapping Builder")

# --------- Block 1: Upload Files ---------
st.subheader("1. Upload files")

uploaded_files = st.file_uploader(
    "Upload one or more CSV files",
    type=["csv"],
    accept_multiple_files=True,
    help="ลากหรือเลือกไฟล์ CSV ที่ต้องการใช้เปรียบเทียบ",
)

# เก็บ DataFrame ไว้ใน dict
dfs: dict[str, pd.DataFrame] = {}
file_meta: dict[str, dict] = {}
if "csv_options" not in st.session_state:
    st.session_state.csv_options = {}

SEPARATOR_CHOICES = [",", ";", "\t", "|", ":"]

if uploaded_files:
    for f in uploaded_files:
        name = f.name
        file_bytes = f.getvalue()
        detected_sep = detect_separator(file_bytes)
        opts = st.session_state.csv_options.setdefault(
            name,
            {
                "sep": detected_sep,
                "header": True,
                "set_index": False,
                "index_col": None,
            },
        )

        with st.expander(f"📄 {name} — file settings", expanded=True):
            sep_choice = st.selectbox(
                "Separator",
                options=SEPARATOR_CHOICES,
                format_func=describe_separator,
                index=SEPARATOR_CHOICES.index(opts["sep"])
                if opts["sep"] in SEPARATOR_CHOICES
                else 0,
                key=f"sep_{name}",
                help=f"Auto-detected: {describe_separator(detected_sep)}",
            )
            opts["sep"] = sep_choice

            use_header = st.checkbox(
                "Use first row as header",
                value=opts["header"],
                key=f"header_{name}",
            )
            opts["header"] = use_header
            header_arg = 0 if use_header else None

            # Read once with current sep/header to get columns
            df_temp = pd.read_csv(BytesIO(file_bytes), sep=sep_choice, header=header_arg)
            columns = list(df_temp.columns)

            set_index_flag = st.checkbox(
                "Set index column",
                value=opts["set_index"],
                key=f"set_index_{name}",
            )
            opts["set_index"] = set_index_flag

            if set_index_flag and columns:
                current_index = opts.get("index_col")
                if current_index not in columns:
                    current_index = columns[0]
                index_col_val = st.selectbox(
                    "Index column",
                    options=columns,
                    index=columns.index(current_index) if current_index in columns else 0,
                    key=f"index_col_{name}",
                    format_func=lambda x: str(x),
                )
                opts["index_col"] = index_col_val
                df_temp = df_temp.set_index(index_col_val, drop=False)
            else:
                opts["index_col"] = None

            dfs[name] = df_temp
            file_meta[name] = {
                "separator": sep_choice,
                "header": "with header" if use_header else "no header",
                "index": opts["index_col"] if set_index_flag else None,
            }

            st.caption(
                f"Separator: {describe_separator(sep_choice)} | Header: {file_meta[name]['header']} | "
                f"Index: {file_meta[name]['index'] if file_meta[name]['index'] is not None else '-'}"
            )
            st.dataframe(df_temp.head(), use_container_width=True)

# --------- Block 2: Create Rule-set with + Steps ---------
st.markdown("---")
st.subheader("2. Create Rule-set")

rule_set_name = st.text_input("Rule-set name", value="My Rule-set")
rule_set_desc = st.text_area("Description", value="", height=60)

if "steps" not in st.session_state:
    st.session_state.steps = []
if "step_label_cache" not in st.session_state:
    st.session_state.step_label_cache = []
if "last_run_results" not in st.session_state:
    st.session_state.last_run_results = []

st.markdown("### Steps")
st.caption("กดปุ่ม **Add Step** เพื่อสร้างกติกา แล้วสามารถลากเรียงลำดับ module action ได้")

# ปุ่มล้าง step
if st.session_state.steps:
    clear_col, _ = st.columns([1, 5])
    if clear_col.button("ล้าง Steps ทั้งหมด", type="secondary"):
        st.session_state.steps = []
        st.session_state.step_label_cache = []
        st.success("ล้าง Steps แล้ว")

builder_col, flow_col = st.columns([1.3, 1])

# Add Step Form
if dfs:
    with builder_col:
        with st.expander("➕ Add Step", expanded=True):
            step_type = st.selectbox(
                "Step type",
                options=["compare_two_files"],  # เผื่ออนาคตเพิ่ม type อื่น
                format_func=lambda x: "Compare between 2 files"
                if x == "compare_two_files"
                else x,
            )

            file_names = list(dfs.keys())

            # Source side
            st.markdown("**Source (ด้านซ้าย)**")
            src_file = st.selectbox("Source file", options=file_names, key="src_file")
            src_cols = list(dfs[src_file].columns)
            src_keyword_col = st.selectbox(
                "Source keyword column", options=src_cols, key="src_keyword_col"
            )
            src_keyword_val = st.text_input(
                "Source keyword value (e.g. RS001)", key="src_keyword_val"
            )
            src_value_col = st.selectbox(
                "Source value column", options=src_cols, key="src_value_col"
            )

            st.markdown("---")

            # Target side
            st.markdown("**Target (ด้านขวา)**")
            tgt_file = st.selectbox("Target file", options=file_names, key="tgt_file")
            tgt_cols = list(dfs[tgt_file].columns)
            tgt_keyword_col = st.selectbox(
                "Target keyword column", options=tgt_cols, key="tgt_keyword_col"
            )
            tgt_keyword_val = st.text_input(
                "Target keyword value (e.g. SW001)", key="tgt_keyword_val"
            )
            tgt_value_col = st.selectbox(
                "Target value column", options=tgt_cols, key="tgt_value_col"
            )

            st.markdown("---")
            st.markdown("**Operator / Rule**")
            operator_type = st.selectbox(
                "Operator type",
                options=["equal", "not_equal", "abs_diff_pct_max"],
            )
            max_pct = None
            if operator_type == "abs_diff_pct_max":
                max_pct = st.number_input(
                    "Max allowed difference (%)", min_value=0.0, value=1.0, step=0.1
                )

            if st.button("➕ Add this Step"):
                step = {
                    "step_id": len(st.session_state.steps) + 1,
                    "step_type": step_type,
                    "source": {
                        "file_label": src_file,
                        "filter": {
                            "keyword_column": src_keyword_col,
                            "keyword_value": src_keyword_val,
                        },
                        "value_column": src_value_col,
                    },
                    "target": {
                        "file_label": tgt_file,
                        "filter": {
                            "keyword_column": tgt_keyword_col,
                            "keyword_value": tgt_keyword_val,
                        },
                        "value_column": tgt_value_col,
                    },
                    "operator_block": {
                        "operator_type": operator_type,
                    },
                }
                if max_pct is not None:
                    step["operator_block"]["max_pct"] = max_pct / 100.0  # เก็บเป็น 0.xx

                st.session_state.steps.append(step)
                st.session_state.step_label_cache = []
                st.success("เพิ่ม Step ใหม่แล้ว ✅")
else:
    builder_col.info("ต้องอัปโหลด CSV ก่อน ถึงจะตั้งค่า Step ได้")

# Drag & drop + overview
with flow_col:
    st.markdown("### Flow / Drag & drop")
    if not st.session_state.steps:
        st.info("ยังไม่มี Step ให้จัดเรียง ลองสร้าง Step ก่อน")
    else:
        drag_items = [
            format_step_label(step, idx + 1)
            for idx, step in enumerate(st.session_state.steps)
        ]
        if SORTABLE_READY:
            reordered = sort_items(
                drag_items,
                header="ลากการ์ดเพื่อจัดเรียงลำดับ",
                direction="vertical",
                key="step_sortable",
            )
            if reordered != st.session_state.step_label_cache:
                label_to_step = {
                    label: step
                    for label, step in zip(drag_items, st.session_state.steps)
                }
                new_steps = []
                for new_idx, label in enumerate(reordered):
                    step = label_to_step[label]
                    step["step_id"] = new_idx + 1
                    new_steps.append(step)
                st.session_state.steps = new_steps
                st.session_state.step_label_cache = reordered
        else:
            st.warning(
                "ติดตั้งแพ็กเกจ `streamlit-sortables` เพื่อเปิด drag & drop (`pip install streamlit-sortables`)."
            )

        # ตารางสรุป step แบบอ่านง่าย
        summary_rows = []
        for idx, step in enumerate(st.session_state.steps, 1):
            summary_rows.append(
                {
                    "Order": idx,
                    "Source": f"{step['source']['file_label']} [{step['source']['filter']['keyword_value']}]",
                    "Target": f"{step['target']['file_label']} [{step['target']['filter']['keyword_value']}]",
                    "Operator": step["operator_block"]["operator_type"],
                }
            )
        st.dataframe(
            pd.DataFrame(summary_rows),
            use_container_width=True,
            hide_index=True,
        )

# แสดง Flow Diagram
if st.session_state.steps:
    st.markdown("#### Flow overview")
    dot_graph = build_flow_chart(st.session_state.steps)
    st.graphviz_chart(dot_graph, use_container_width=True)

    st.markdown("#### Current Steps (JSON)")
    st.json(st.session_state.steps)

# --------- Block 3: Run rule-set ---------
st.markdown("---")
st.subheader("3. Run rule-set on uploaded data")

if not dfs:
    st.info("ต้องอัปโหลด CSV ก่อน ถึงจะรัน rule-set ได้")
elif not st.session_state.steps:
    st.info("ยังไม่มี Step ให้รัน กด ➕ Add Step ก่อน")
else:
    run_col, _ = st.columns([1, 3])
    if run_col.button("▶️ Run rules now"):
        st.session_state.last_run_results = [
            evaluate_step(step, dfs) for step in st.session_state.steps
        ]
        st.success("รันกติกาเสร็จแล้ว ✅")

    results = st.session_state.last_run_results
    if results:
        pass_count = sum(r["status"] == "pass" for r in results)
        fail_count = sum(r["status"] == "fail" for r in results)
        err_count = sum(r["status"] == "error" for r in results)
        total = len(results)

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Pass", pass_count)
        m2.metric("Fail", fail_count)
        m3.metric("Error", err_count)
        m4.metric("Total steps", total)

        rows = []
        for step, res in zip(st.session_state.steps, results):
            rows.append(
                {
                    "Step": step["step_id"],
                    "Status": res["status"],
                    "Reason": res.get("reason", ""),
                    "Source value": res.get("source_value"),
                    "Target value": res.get("target_value"),
                    "Operator": step["operator_block"]["operator_type"],
                }
            )
        st.dataframe(
            pd.DataFrame(rows),
            use_container_width=True,
            hide_index=True,
        )

# --------- Block 4: Save Rule-set ---------
st.markdown("---")
st.subheader("4. Save Rule-set")

if st.session_state.steps:
    rule_set = {
        "rule_set_name": rule_set_name,
        "description": rule_set_desc,
        "steps": st.session_state.steps,
    }

    json_bytes = json.dumps(rule_set, ensure_ascii=False, indent=2).encode("utf-8")
    st.download_button(
        "💾 Download Rule-set JSON",
        data=json_bytes,
        file_name=f"{rule_set_name.replace(' ', '_')}.json",
        mime="application/json",
    )
else:
    st.info("ยังไม่มี Step ให้สร้าง Rule-set เลย กด ➕ Add Step ก่อนน้า")
