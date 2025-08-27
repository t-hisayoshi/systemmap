import streamlit as st
from graphviz import Digraph
import csv
import io

# =========================
# 初期設定
# =========================
st.set_page_config(page_title="System Map Builder", layout="wide")
st.title("System Map Builder（行ごとの入力 + 矢印のプルダウン + CSV I/O）")

# =========================
# セッションステート初期化
# =========================
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

# =========================
# CSV I/O ユーティリティ（堅牢化）
# =========================
def _norm(s: str) -> str:
    """BOM除去・全角スペース→半角・strip・lower"""
    return (s or "").replace("\u3000", " ").strip().lstrip("\ufeff").lower()

def _apply_aliases(cols, aliases):
    fixed = []
    for c in cols:
        k = _norm(c)
        fixed.append(aliases.get(k, k))
    return fixed

def parse_csv_uploaded(file, required_cols, aliases=None, allow_extra=True):
    """
    CSVを寛容に読む（BOM/全角/大小・別名対応）
    required_cols: 例 ["name"] or ["name","description","data"]
    aliases: {"discription":"description","desc":"description","名前":"name"} など
    """
    aliases = aliases or {}
    data = file.read()  # bytes
    text = data.decode("utf-8-sig", errors="replace")  # Excel互換
    reader = csv.DictReader(io.StringIO(text))

    if reader.fieldnames is None:
        return [], "CSVのヘッダ行が見つかりません。"

    raw_headers = reader.fieldnames
    fixed_headers = _apply_aliases(raw_headers, aliases)

    need = set(_norm(c) for c in required_cols)
    have = set(fixed_headers)
    if not need.issubset(have):
        return [], f"CSVヘッダが不足: {sorted(need - have)}（必要: {sorted(need)}）"

    rows = []
    for raw_row in reader:
        row = {}
        for raw_k, v in raw_row.items():
            k = _apply_aliases([raw_k], aliases)[0]
            row[k] = (v or "").strip()
        if not allow_extra:
            row = {k: row.get(k, "") for k in need}
        rows.append(row)
    return rows, None

def download_csv(filename: str, headers: list[str], rows: list[list[str]]):
    """UTF-8-SIG でDL（ExcelでもOK）"""
    buf = io.StringIO()
    buf.write("\ufeff")  # BOM
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(headers)
    writer.writerows(rows)
    st.download_button(
        label=f"{filename} をダウンロード",
        data=buf.getvalue().encode("utf-8"),
        file_name=filename,
        mime="text/csv; charset=utf-8",
    )

# =========================
# 図の生成
# =========================
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

# =========================
# サイドバー（折り畳み可能）
# =========================
with st.sidebar.expander("⚙️ オプション", expanded=False):
    rankdir = st.selectbox("レイアウト方向", ["LR","TB","BT","RL"], 0)
    font = st.text_input("フォント（例: Noto Sans, Meiryo）", "Noto Sans")
    actor_color = st.color_picker("Actor色", "#FFF7D6")
    system_color = st.color_picker("System色", "#EAF3FF")
    system_header = st.color_picker("Systemヘッダ色", "#D6E9FF")
    data_bg = st.color_picker("データ欄色", "#FFFFFF")
    emph_bg = st.color_picker("強調データ色（＊項目）", "#B3D9FF")
    edge_color = st.color_picker("矢印色", "#666666")

# =========================
# 本体UI
# =========================
ensure_state()

# --- Actors ---
st.subheader("Actors")
cols = st.columns([1,1,3,3,3])
if cols[0].button("+", key="add_actor", help="Actor を1行追加"):
    add_row("actor")
if cols[1].button("CSV出力", key="exp_actor"):
    download_csv(
        "actors.csv",
        headers=["name"],
        rows=[[a["name"]] for a in st.session_state.actors]
    )
imp_actor = cols[2].file_uploader("インポート（Actors）", type=["csv"], key="imp_actor")
if imp_actor is not None:
    rows, err = parse_csv_uploaded(
        imp_actor, required_cols=["name"], aliases={"名前": "name"}
    )
    if err:
        st.error(err)
    else:
        st.session_state.actors = [{"name": r.get("name","")} for r in rows if r.get("name","").strip()]
        st.success(f"{len(st.session_state.actors)} 件インポートしました")

for i, a in enumerate(st.session_state.actors):
    c1, c2 = st.columns([8,1])
    a["name"] = c1.text_input(f"Actor {i+1}", value=a["name"], key=f"actor_{i}")
    if c2.button("×", key=f"del_actor_{i}", help="この行を削除"):
        del_row("actor", i)
        st.experimental_rerun()

st.divider()

# --- Systems ---
st.subheader("Systems")
cols = st.columns([1,1,3,3,3])
if cols[0].button("+", key="add_system", help="System を1行追加"):
    add_row("system")
if cols[1].button("CSV出力", key="exp_system"):
    download_csv(
        "systems.csv",
        headers=["name","description","data"],
        rows=[[s["name"], s["description"], s["data"]] for s in st.session_state.systems]
    )
imp_sys = cols[2].file_uploader("インポート（Systems）", type=["csv"], key="imp_system")
if imp_sys is not None:
    rows, err = parse_csv_uploaded(
        imp_sys,
        required_cols=["name","description","data"],
        aliases={
            "discription":"description", "desc":"description", "説明":"description",
            "データ":"data", "項目":"data", "名前":"name"
        }
    )
    if err:
        st.error(err)
    else:
        st.session_state.systems = [
            {"name": r.get("name",""), "description": r.get("description",""), "data": r.get("data","")}
            for r in rows if r.get("name","").strip()
        ]
        st.success(f"{len(st.session_state.systems)} 件インポートしました")

hdr = st.columns([4,4,4,1])
hdr[0].markdown("**name**")
hdr[1].markdown("**description**")
hdr[2].markdown("**data（カンマ区切り・先頭`*`/`＊`で強調）**")
for i, s in enumerate(st.session_state.systems):
    c1, c2, c3, c4 = st.columns([4,4,4,1])
    s["name"] = c1.text_input(f"name_{i}", value=s["name"], key=f"sys_name_{i}")
    s["description"] = c2.text_input(f"description_{i}", value=s["description"], key=f"sys_desc_{i}")
    s["data"] = c3.text_input(f"data_{i}", value=s["data"], key=f"sys_data_{i}")
    if c4.button("×", key=f"del_system_{i}", help="この行を削除"):
        del_row("system", i)
        st.experimental_rerun()

st.divider()

# --- Arrows ---
st.subheader("Arrows")
cols = st.columns([1,1,3,3,3])
if cols[0].button("+", key="add_arrow", help="Arrow を1行追加"):
    add_row("arrow")
if cols[1].button("CSV出力", key="exp_arrow"):
    download_csv(
        "arrows.csv",
        headers=["from","to","text"],
        rows=[[e["from"], e["to"], e["text"]] for e in st.session_state.arrows]
    )
imp_arr = cols[2].file_uploader("インポート（Arrows）", type=["csv"], key="imp_arrow")
if imp_arr is not None:
    rows, err = parse_csv_uploaded(
        imp_arr,
        required_cols=["from","to","text"],
        aliases={"fromノード":"from","toノード":"to","label":"text","ラベル":"text"}
    )
    if err:
        st.error(err)
    else:
        st.session_state.arrows = [
            {"from": r.get("from",""), "to": r.get("to",""), "text": r.get("text","")}
            for r in rows if r.get("from","").strip() and r.get("to","").strip()
        ]
        st.success(f"{len(st.session_state.arrows)} 件インポートしました")

options = [*actor_names(), *system_names()]
arr_hdr = st.columns([4,4,3,1])
arr_hdr[0].markdown("**from**")
arr_hdr[1].markdown("**to**")
arr_hdr[2].markdown("**text（矢印ラベル）**")
for i, e in enumerate(st.session_state.arrows):
    c1, c2, c3, c4 = st.columns([4,4,3,1])
    cur_from = e["from"] if e["from"] in options else (options[0] if options else "")
    cur_to = e["to"] if e["to"] in options else (options[0] if options else "")
    e["from"] = c1.selectbox(f"from_{i}", options, index=options.index(cur_from) if cur_from in options else 0, key=f"arr_from_{i}")
    e["to"] = c2.selectbox(f"to_{i}", options, index=options.index(cur_to) if cur_to in options else 0, key=f"arr_to_{i}")
    e["text"] = c3.text_input(f"text_{i}", value=e["text"], key=f"arr_text_{i}")
    if c4.button("×", key=f"del_arrow_{i}", help="この行を削除"):
        del_row("arrow", i)
        st.experimental_rerun()

st.markdown("---")

# =========================
# 描画
# =========================
if st.button("描画する", type="primary"):
    # 重複名チェック（ID衝突回避）
    names = actor_names() + system_names()
    if len(names) != len(set(names)):
        st.warning("Actor/System の名前が重複しています。ノードIDとして使うため、一意にしてください。")
    dot = render_graph(rankdir, font, actor_color, system_color, system_header, data_bg, emph_bg, edge_color)
    st.graphviz_chart(dot.source, use_container_width=True)
    st.download_button("SVGをダウンロード", dot.pipe(format="svg"),
                       file_name="system_map.svg", mime="image/svg+xml")
else:
    st.info("各行に入力し、「描画する」を押してください。")
