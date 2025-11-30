# streamlit_app.py

import pydeck as pdk
import streamlit as st
import pymongo

st.set_page_config(page_title="MongoDB CRUD Demo", layout="wide")

# -------------------------
# 1) Connect MongoDB
# -------------------------
@st.cache_resource
def init_connection():
    # ใน .streamlit/secrets.toml ต้องมีส่วนนี้ เช่น
    # [mongo]
    # host = "localhost"
    # port = 27017
    # username = "..."
    # password = "..."
    return pymongo.MongoClient(**st.secrets["mongo"])

client = init_connection()
db = client["test_db"]            # ปรับชื่อ DB ตามจริง
collection = db["users"]   # ปรับชื่อ collection ตามจริง

# -------------------------
# 2) Helper: load data
# -------------------------
def get_data():
    items = list(collection.find())
    return items


def trigger_rerun():
    # Prefer the stable rerun API, but fall back to the old experimental name if needed.
    rerun_fn = getattr(st, "rerun", None) or getattr(st, "experimental_rerun", None)
    if rerun_fn is None:
        raise RuntimeError("Streamlit rerun function is unavailable in this version.")
    rerun_fn()


@st.cache_data(show_spinner=False)
def load_thai_cities():
    """Return a static list of Thai provinces for selection."""
    provinces = [
        "Bangkok",
        "Krabi",
        "Kanchanaburi",
        "Kalasin",
        "Kamphaeng Phet",
        "Khon Kaen",
        "Chanthaburi",
        "Chachoengsao",
        "Chai Nat",
        "Chaiyaphum",
        "Chumphon",
        "Chiang Rai",
        "Chiang Mai",
        "Trang",
        "Trat",
        "Tak",
        "Nakhon Nayok",
        "Nakhon Pathom",
        "Nakhon Phanom",
        "Nakhon Ratchasima",
        "Nakhon Si Thammarat",
        "Nan",
        "Nonthaburi",
        "Buriram",
        "Pathum Thani",
        "Prachuap Khiri Khan",
        "Prachin Buri",
        "Pattani",
        "Phra Nakhon Si Ayutthaya",
        "Phang Nga",
        "Phatthalung",
        "Phichit",
        "Phitsanulok",
        "Phetchaburi",
        "Phetchabun",
        "Phuket",
        "Maha Sarakham",
        "Mukdahan",
        "Mae Hong Son",
        "Yasothon",
        "Yala",
        "Roi Et",
        "Ranong",
        "Rayong",
        "Ratchaburi",
        "Lopburi",
        "Lampang",
        "Lamphun",
        "Loei",
        "Si Sa Ket",
        "Sakon Nakhon",
        "Songkhla",
        "Satun",
        "Samut Prakan",
        "Samut Songkhram",
        "Samut Sakhon",
        "Sa Kaeo",
        "Saraburi",
        "Sing Buri",
        "Sukhothai",
        "Suphan Buri",
        "Surat Thani",
        "Surin",
        "Nong Khai",
        "Nong Bua Lamphu",
        "Ang Thong",
        "Udon Thani",
        "Uttaradit",
        "Uthai Thani",
        "Ubon Ratchathani",
        "Amnat Charoen",
    ]
    return ["Select a city"] + provinces


city_options = load_thai_cities()

# Approximate lat/lon for Thai provinces (used for geo visualization)
THAI_CITY_COORDS = {
    "Bangkok": (13.7563, 100.5018),
    "Krabi": (8.0863, 98.9063),
    "Kanchanaburi": (14.0228, 99.5328),
    "Kalasin": (16.4380, 103.5060),
    "Kamphaeng Phet": (16.4827, 99.5228),
    "Khon Kaen": (16.4419, 102.8350),
    "Chanthaburi": (12.6114, 102.1038),
    "Chachoengsao": (13.6904, 101.0779),
    "Chai Nat": (15.1859, 100.1250),
    "Chaiyaphum": (15.8106, 102.0280),
    "Chumphon": (10.4930, 99.1800),
    "Chiang Rai": (19.9105, 99.8406),
    "Chiang Mai": (18.7883, 98.9853),
    "Trang": (7.5590, 99.6110),
    "Trat": (12.2420, 102.5170),
    "Tak": (16.8840, 99.1250),
    "Nakhon Nayok": (14.2030, 101.2130),
    "Nakhon Pathom": (13.8196, 100.0622),
    "Nakhon Phanom": (17.4100, 104.7830),
    "Nakhon Ratchasima": (14.9799, 102.0977),
    "Nakhon Si Thammarat": (8.4304, 99.9631),
    "Nan": (18.7750, 100.7730),
    "Nonthaburi": (13.8621, 100.5144),
    "Buriram": (14.9940, 103.1039),
    "Pathum Thani": (14.0208, 100.5250),
    "Prachuap Khiri Khan": (11.8110, 99.7970),
    "Prachin Buri": (14.0490, 101.3700),
    "Pattani": (6.8697, 101.2510),
    "Phra Nakhon Si Ayutthaya": (14.3692, 100.5877),
    "Phang Nga": (8.4510, 98.5252),
    "Phatthalung": (7.6167, 100.0734),
    "Phichit": (16.4419, 100.3488),
    "Phitsanulok": (16.8210, 100.2627),
    "Phetchaburi": (13.1110, 99.9380),
    "Phetchabun": (16.4180, 101.1540),
    "Phuket": (7.8804, 98.3923),
    "Maha Sarakham": (16.1846, 103.3007),
    "Mukdahan": (16.5453, 104.7236),
    "Mae Hong Son": (19.3013, 97.9654),
    "Yasothon": (15.7927, 104.1453),
    "Yala": (6.5410, 101.2800),
    "Roi Et": (16.0538, 103.6520),
    "Ranong": (9.9529, 98.6085),
    "Rayong": (12.6814, 101.2780),
    "Ratchaburi": (13.5283, 99.8134),
    "Lopburi": (14.7995, 100.6534),
    "Lampang": (18.2888, 99.4928),
    "Lamphun": (18.5745, 99.0087),
    "Loei": (17.4860, 101.7223),
    "Si Sa Ket": (15.1143, 104.3290),
    "Sakon Nakhon": (17.1546, 104.1476),
    "Songkhla": (7.1898, 100.5951),
    "Satun": (6.6238, 100.0674),
    "Samut Prakan": (13.5991, 100.5990),
    "Samut Songkhram": (13.4094, 100.0020),
    "Samut Sakhon": (13.5475, 100.2744),
    "Sa Kaeo": (13.8176, 102.0680),
    "Saraburi": (14.5289, 100.9106),
    "Sing Buri": (14.8920, 100.3960),
    "Sukhothai": (17.0050, 99.8260),
    "Suphan Buri": (14.4730, 100.1220),
    "Surat Thani": (9.1382, 99.3215),
    "Surin": (14.8818, 103.4937),
    "Nong Khai": (17.8783, 102.7413),
    "Nong Bua Lamphu": (17.2040, 102.4390),
    "Ang Thong": (14.5913, 100.4550),
    "Udon Thani": (17.3647, 102.8150),
    "Uttaradit": (17.6233, 100.0993),
    "Uthai Thani": (15.3794, 100.0245),
    "Ubon Ratchathani": (15.2287, 104.8560),
    "Amnat Charoen": (15.8581, 104.6288),
}


def compute_stats(users):
    total = len(users)
    ages = [u.get("age") for u in users if isinstance(u.get("age"), (int, float))]
    avg_age = round(sum(ages) / len(ages), 1) if ages else 0
    unique_cities = len({(u.get("city") or "").strip().lower() for u in users if u.get("city")})
    return total, avg_age, unique_cities


def build_geo_points(users):
    """Aggregate users by city and attach lat/lon for mapping."""
    by_city = {}
    for user in users:
        city = (user.get("city") or "").split(",")[0].strip()
        if not city:
            continue
        coords = THAI_CITY_COORDS.get(city)
        if not coords:
            continue
        entry = by_city.setdefault(city, {"city": city, "lat": coords[0], "lon": coords[1], "count": 0})
        entry["count"] += 1
    return list(by_city.values())

# -------------------------
# 3) หน้า UI หลัก
# -------------------------
st.title("👥 MongoDB + Streamlit")
st.caption("จัดการ users ได้ไวขึ้น: ฟอร์มด้านซ้าย, ตารางค้นหา, และส่วนแก้ไข/ลบแบบแยกชัดเจน")

items = get_data()
total_users, avg_age, unique_cities = compute_stats(items)

col_m1, col_m2, col_m3 = st.columns(3)
col_m1.metric("Users", total_users)
col_m2.metric("Avg. age", avg_age)
col_m3.metric("Unique city", unique_cities)

tab_create, tab_browse, tab_map, tab_manage = st.tabs(
    ["➕ เพิ่มผู้ใช้", "📖 ดู/ค้นหา", "🗺️ แผนที่", "✏️ แก้ไข / 🗑 ลบ"]
)

with tab_create:
    with st.form("create_user_form", clear_on_submit=True):
        c1, c2, c3 = st.columns((2, 1, 2))
        new_name = c1.text_input("Name", placeholder="สมชาย")
        new_age = c2.number_input("Age", min_value=0, max_value=120, step=1, value=25)
        new_city = c3.selectbox("City (จังหวัด)", options=city_options, index=0)

        submitted = st.form_submit_button("Add User")

        if submitted:
            if new_name.strip() == "" or new_city == "Select a city":
                st.error("กรุณากรอกชื่อและเลือกเมืองก่อนน้า 🥺")
            else:
                doc = {"name": new_name.strip(), "age": int(new_age), "city": new_city}
                collection.insert_one(doc)
                st.success(f"เพิ่ม {new_name} เรียบร้อยแล้ว ✅")
                trigger_rerun()

with tab_browse:
    search_term = st.text_input("ค้นหาชื่อหรือเมือง", placeholder="เช่น 'Bangkok' หรือ 'สมชาย'", label_visibility="collapsed")
    if search_term:
        lowered = search_term.lower()
        filtered = [
            u for u in items
            if lowered in (u.get("name") or "").lower() or lowered in (u.get("city") or "").lower()
        ]
    else:
        filtered = items

    if not filtered:
        st.info("ยังไม่มีข้อมูลใน collection เลย ลองเพิ่มด้านบนก่อน 👆")
    else:
        for item in filtered:
            item["_id_str"] = str(item["_id"])
        st.dataframe(
            [
                {"id": i["_id_str"], "name": i.get("name"), "age": i.get("age"), "city": i.get("city")}
                for i in filtered
            ],
            use_container_width=True,
            height=360,
        )

with tab_map:
    points = build_geo_points(items)
    if not points:
        st.info("ยังไม่มีข้อมูลเมืองที่จับคู่พิกัดได้")
    else:
        # Bubble size grows with number of users in that city
        for p in points:
            p["radius"] = 2000 + p["count"] * 500
        # Centered and zoomed to Thailand only
        view_state = pdk.ViewState(
            latitude=15.8700,
            longitude=100.9925,
            zoom=6.2,
            min_zoom=5.5,
            max_zoom=8.5,
            pitch=30,
            bearing=0,
        )
        layer = pdk.Layer(
            "ScatterplotLayer",
            data=points,
            get_position="[lon, lat]",
            get_fill_color="[0, 180, 255, 180]",
            get_radius="radius",
            pickable=True,
        )
        tooltip = {"text": "{city}\nจำนวนผู้ใช้: {count}"}
        st.pydeck_chart(
            pdk.Deck(
                map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
                initial_view_state=view_state,
                layers=[layer],
                tooltip=tooltip,
            )
        )

with tab_manage:
    if not items:
        st.info("ยังไม่มี user ให้แก้ไขหรือลบน้า")
    else:
        options = {
            f"{item.get('name', 'Unknown')} ({item.get('city', '-')}) - {str(item['_id'])}": item
            for item in items
        }
        selected_label = st.selectbox("เลือก user ที่ต้องการแก้ไข / ลบ", list(options.keys()))
        selected_user = options[selected_label]

        col1, col2, col3 = st.columns((2, 1, 2))
        edit_name = col1.text_input("Name", value=selected_user.get("name", ""), key=f"edit_name_{selected_user['_id']}")
        edit_age = col2.number_input(
            "Age",
            min_value=0,
            max_value=120,
            step=1,
            value=int(selected_user.get("age", 0)),
            key=f"edit_age_{selected_user['_id']}",
        )
        try:
            city_index = city_options.index(selected_user.get("city", ""))
        except ValueError:
            city_index = 0
        edit_city = col3.selectbox(
            "City (จังหวัด)",
            options=city_options,
            index=city_index,
            key=f"edit_city_{selected_user['_id']}",
        )

        col_update, col_delete = st.columns(2)
        with col_update:
            if st.button("💾 Save changes", type="primary"):
                collection.update_one(
                    {"_id": selected_user["_id"]},
                    {"$set": {"name": edit_name.strip(), "age": int(edit_age), "city": edit_city}},
                )
                st.success("อัปเดตข้อมูลเรียบร้อยแล้ว ✅")
                trigger_rerun()

        with col_delete:
            if st.button("🗑 Delete this user"):
                collection.delete_one({"_id": selected_user["_id"]})
                st.warning("ลบผู้ใช้คนนี้แล้ว ⚠️")
                trigger_rerun()
