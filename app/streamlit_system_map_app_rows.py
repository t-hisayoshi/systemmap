import streamlit as st
from graphviz import Digraph

st.set_page_config(page_title="System Map Builder", layout="wide")
st.title("System Map Builder")

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
        if not item: continue
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

st.subheader("Actors")
if st.button("add", key="add_actor"): add_row("actor")
for i, a in enumerate(st.session_state.actors):
    c1, c2 = st.columns([8,1])
    a["name"] = c1.text_input(f"Actor {i+1}", value=a["name"], key=f"actor_{i}")
    if c2.button("×", key=f"del_actor_{i}"):
        del_row("actor", i); st.rerun()

st.subheader("Systems (dataの頭に*/＊をつけると強調表示されます)")
if st.button("add", key="add_system"): add_row("system")
for i, s in enumerate(st.session_state.systems):
    c1, c2, c3, c4 = st.columns([4,4,4,1])
    s["name"] = c1.text_input(f"name_{i}", value=s["name"], key=f"sys_name_{i}")
    s["description"] = c2.text_input(f"description_{i}", value=s["description"], key=f"sys_desc_{i}")
    s["data"] = c3.text_input(f"data_{i}", value=s["data"], key=f"sys_data_{i}")
    if c4.button("×", key=f"del_system_{i}"):
        del_row("system", i); st.rerun()

st.subheader("Arrows")
if st.button("add", key="add_arrow"): add_row("arrow")
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
if st.button("描画する", type="primary"):
    dot = render_graph(rankdir, font, actor_color, system_color, system_header, data_bg, emph_bg, edge_color)
    st.graphviz_chart(dot.source, use_container_width=True)
    st.download_button("SVGをダウンロード", dot.pipe(format="svg"),
                       file_name="system_map.svg", mime="image/svg+xml")
