import streamlit as st
from graphviz import Digraph
import csv, io

st.set_page_config(page_title="System Map Builder", layout="wide")
st.title("System Map Builder（行ごとの入力 + 矢印のプルダウン + CSV入出力）")

# -------- Helpers --------
def ensure_state():
    if "actors" not in st.session_state:
        st.session_state.actors = [{"name": "顧客"}, {"name": "営業担当"}]
    if "systems" not in st.session_state:
        st.session_state.systems = [
            {"name": "顧客管理システム", "description": "顧客登録・問合せ対応", "data": "＊顧客ID, 氏名, 住所"},
            {"name": "販売管理システム", "description": "受注・請求処理", "data": "＊注文ID, 顧客ID, 商品情報"},
            {"name": "会計システム", "description": "売上計上・入金処理", "data": "＊仕訳ID, 請求金額"},
        ]
    if "arrows" not in st.session_state:
        st.session_state.arrows = [
            {"from": "顧客", "to": "顧客管理システム", "text": "登録依頼"},
            {"from": "営業担当", "to": "顧客管理システム", "text": "登録作業"},
            {"from": "顧客管理システム", "to": "販売管理システム", "text": "顧客ID"},
            {"from": "販売管理システム", "to": "会計システム", "text": "請求情報"},
        ]

def add_row(kind):
    if kind == "actor":
        st.session_state.actors.append({"name": ""})
    elif kind == "system":
        st.session_state.systems.append({"name": "", "description": "", "data": ""})
    elif kind == "arrow":
        opts = [*actor_names(), *system_names()]
        frm = opts[0] if opts else ""
        to = opts[1] if len(opts) > 1 else frm
        st.session_state.arrows.append({"from": frm, "to": to, "text": ""})

def del_row(kind, idx):
    if kind == "actor" and 0 <= idx < len(st.session_state.actors):
        st.session_state.actors.pop(idx)
    elif kind == "system" and 0 <= idx < len(st.session_state.systems):
        st.session_state.systems.pop(idx)
    elif kind == "arrow" and 0 <= idx < len(st.session_state.arrows):
        st.session_state.arrows.pop(idx)

def actor_names():
    return [a["name"].strip() for a in st.session_state.actors if a["name"].strip()]

def system_names():
    return [s["name"].strip() for s in st.session_state.systems if s["name"].strip()]

def build_system_label(sys, header_bg, data_bg, emph_bg):
    raw = sys.get("data", "").strip()
    items = [i.strip() for i in raw.split(",")] if raw else []
    rows = []
    for item in items:
        if not item: 
            continue
        emph = item.startswith("*") or item.startswith("＊")
        label = item[1:].strip() if emph else item
        bg = emph_bg if emph else data_bg
        rows.append(f'<TR><TD BGCOLOR="{bg}">{label}</TD></TR>')
    rows_html = "\n".join(rows) if rows else f'<TR><TD BGCOLOR="{data_bg}">（項目なし）</TD></TR>'
    return f"""<
      <TABLE BORDER="1" CELLBORDER="1" CELLSPACING="0">
        <TR><TD BGCOLOR="{header_bg}"><B>{sys.get("name","")}</B></TD></TR>
        <TR><TD>{sys.get("description","")}</TD></TR>
        <TR><TD>
          <TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0">{rows_html}</TABLE>
        </TD></TR>
      </TABLE>
    >"""

def render_graph(rankdir, font, actor_color, system_color, system_header, data_bg, emph_bg, edge_color):
    dot = Digraph(format="svg")
    dot.attr(rankdir=rankdir, fontname=font)
    dot.attr("node", fontname=font)
    dot.attr("edge", fontname=font, color=edge_color)

    for a in st.session_state.actors:
        name = a["name"].strip()
        if name:
            dot.node(name, name, shape="ellipse", style="filled", fillcolor=actor_color)

    for s in st.session_state.systems:
        name = s["name"].strip()
        if name:
            dot.node(name, build_system_label(s, system_header, data_bg, emph_bg),
                     shape="plaintext", style="filled", fillcolor=system_color)

    for e in st.session_state.arrows:
        frm, to, text = e["from"].strip(), e["to"].strip(), e["text"]
        if frm and to:
            dot.edge(frm, to, label=text)
    return dot

# ---- CSV utils ----
def bytes_csv(rows, headers):
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=headers)
    writer.writeheader()
    for r in rows:
        writer.writerow({k: r.get(k, "") for k in headers})
    # Excel配慮で UTF-8 BOM 付き
    return ("\ufeff" + buf.getvalue()).encode("utf-8-sig")

def import_csv(file, required_headers):
    try:
        text = file.read().decode("utf-8-sig")
    except Exception:
        text = file.read().decode("utf-8")
    buf = io.StringIO(text)
    reader = csv.DictReader(buf)
    miss = [h for h in required_headers if h not in reader.fieldnames]
    if miss:
        st.error(f"CSVヘッダが不足：{miss}（必要：{required_headers}）")
        return None
    return list(reader)

# -------- サイドバー（折り畳み可能） --------
with st.sidebar.expander("⚙️ オプション", expanded=False):
    rankdir = st.selectbox("レイアウト方向", ["LR","TB","BT","RL"], 0)
    font = st.text_input("フォント", "Noto Sans")
    actor_color = st.color_picker("Actor色", "#FFF7D6")
    system_color = st.color_picker("System色", "#EAF3FF")
    system_header = st.color_picker("Systemヘッダ色", "#D6E9FF")
    data_bg = st.color_picker("データ欄色", "#FFFFFF")
    emph_bg = st.color_picker("強調データ色", "#B3D9FF")
    edge_color = st.color_picker("矢印色", "#666666")

# -------- UI --------
ensure_state()

# === Actors ===
st.subheader("Actors")
top_cols = st.columns([1,1,3,3,3])
if top_cols[0].button("Add", key="add_actor"): add_row("actor")
# Export
actors_csv = bytes_csv(st.session_state.actors, headers=["name"])
top_cols[1].download_button("Export CSV", actors_csv, file_name="actors.csv", mime="text/csv", use_container_width=True)
# Import
with top_cols[2]:
    up_actors = st.file_uploader("Actors CSV Import", type=["csv"], key="up_actors")
with top_cols[3]:
    if st.button("インポート（Actors）", use_container_width=True):
        if up_actors:
            rows = import_csv(up_actors, ["name"])
            if rows is not None:
                st.session_state.actors = [{"name": r.get("name","")} for r in rows]
                st.success("Actorsをインポートしました。"); st.rerun()
        else:
            st.warning("CSVファイルを選択してください。")

for i, a in enumerate(st.session_state.actors):
    c1, c2 = st.columns([8,1])
    a["name"] = c1.text_input(f"Actor {i+1}", value=a["name"], key=f"actor_{i}")
    if c2.button("×", key=f"del_actor_{i}"):
        del_row("actor", i); st.rerun()

st.markdown("---")

# === Systems ===
st.subheader("Systems")
sys_top = st.columns([1,1,3,3,3])
if sys_top[0].button("Add", key="add_system"): add_row("system")
# Export
systems_csv = bytes_csv(st.session_state.systems, headers=["name","description","data"])
sys_top[1].download_button("Export CSV", systems_csv, file_name="systems.csv", mime="text/csv", use_container_width=True)
# Import
with sys_top[2]:
    up_systems = st.file_uploader("Systems CSV Import", type=["csv"], key="up_systems")
with sys_top[3]:
    if st.button("インポート（Systems）", use_container_width=True):
        if up_systems:
            rows = import_csv(up_systems, ["name","description","data"])
            if rows is not None:
                st.session_state.systems = [
                    {"name": r.get("name",""), "description": r.get("description",""), "data": r.get("data","")}
                    for r in rows
                ]
                st.success("Systemsをインポートしました。"); st.rerun()
        else:
            st.warning("CSVファイルを選択してください。")

# rows
for i, s in enumerate(st.session_state.systems):
    c1, c2, c3, c4 = st.columns([4,4,4,1])
    s["name"] = c1.text_input(f"name_{i}", value=s["name"], key=f"sys_name_{i}")
    s["description"] = c2.text_input(f"description_{i}", value=s["description"], key=f"sys_desc_{i}")
    s["data"] = c3.text_input(f"data_{i}", value=s["data"], key=f"sys_data_{i}")
    if c4.button("×", key=f"del_system_{i}"):
        del_row("system", i); st.rerun()

st.markdown("---")

# === Arrows ===
st.subheader("Arrows")
arr_top = st.columns([1,1,3,3,3])
if arr_top[0].button("Add", key="add_arrow"): add_row("arrow")
# Export
arrows_csv = bytes_csv(st.session_state.arrows, headers=["from","to","text"])
arr_top[1].download_button("Export CSV", arrows_csv, file_name="arrows.csv", mime="text/csv", use_container_width=True)
# Import
with arr_top[2]:
    up_arrows = st.file_uploader("Arrows CSV Import", type=["csv"], key="up_arrows")
with arr_top[3]:
    if st.button("インポート（Arrows）", use_container_width=True):
        if up_arrows:
            rows = import_csv(up_arrows, ["from","to","text"])
            if rows is not None:
                st.session_state.arrows = [
                    {"from": r.get("from",""), "to": r.get("to",""), "text": r.get("text","")}
                    for r in rows
                ]
                st.success("Arrowsをインポートしました。"); st.rerun()
        else:
            st.warning("CSVファイルを選択してください。")

# rows
options = [*actor_names(), *system_names()]
for i, e in enumerate(st.session_state.arrows):
    c1,c2,c3,c4 = st.columns([4,4,3,1])
    cur_from = e["from"] if e["from"] in options else (options[0] if options else "")
    cur_to = e["to"] if e["to"] in options else (options[0] if options else "")
    e["from"] = c1.selectbox(f"from_{i}", options, index=options.index(cur_from) if cur_from in options else 0, key=f"arr_from_{i}")
    e["to"] = c2.selectbox(f"to_{i}", options, index=options.index(cur_to) if cur_to in options else 0, key=f"arr_to_{i}")
    e["text"] = c3.text_input(f"text_{i}", value=e["text"], key=f"arr_text_{i}")
    if c4.button("×", key=f"del_arrow_{i}"):
        del_row("arrow", i); st.rerun()

st.markdown("---")

# === Render & Clear ===
c1, c2 = st.columns([1,1])
with c1:
    if st.button("描画する", type="primary", use_container_width=True):
        dot = render_graph(rankdir, font, actor_color, system_color, system_header, data_bg, emph_bg, edge_color)
        st.graphviz_chart(dot.source, use_container_width=True)
        # SVGはGraphvizバイナリが必要：Cloudで未導入ならDOTフォールバック
        svg_bytes = None
        try:
            svg_bytes = dot.pipe(format="svg")
        except Exception:
            st.warning("SVG生成に失敗（Graphvizバイナリ未導入の可能性）。DOTソースのダウンロードを提供します。")
        if svg_bytes:
            st.download_button("SVGをダウンロード", svg_bytes,
                               file_name="system_map.svg", mime="image/svg+xml", use_container_width=True)
        else:
            st.download_button("DOTソースをダウンロード",
                               dot.source.encode("utf-8"),
                               file_name="system_map.dot", mime="text/vnd.graphviz",
                               use_container_width=True)

with c2:
    if st.button("すべてクリア", use_container_width=True):
        st.session_state.actors = []
        st.session_state.systems = []
        st.session_state.arrows = []
        st.rerun()
