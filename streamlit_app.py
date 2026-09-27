"""AI Berkshire 报告浏览器（Streamlit）。

读取 reports/index.json（由 tools/reports_index.py 生成），按分类 → 分组 → 报告浏览。
本地运行：pip install -r requirements.txt && streamlit run streamlit_app.py
"""

import json
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "reports" / "index.json"
MAX_CHARS = 300_000  # 超大文件（如全量发言记录）只渲染前一部分，避免页面卡死

st.set_page_config(page_title="AI Berkshire 研究报告", page_icon="📈", layout="wide")

# 浏览器“翻译此页”会把文字节点替换成 <font>，React 再更新时报
# "Failed to execute 'removeChild' on 'Node'" 并整页崩溃。
# 给主页面打补丁（参见 facebook/react#11538），让翻译后仍能正常切换报告。
components.html(
    """<script>
    const w = window.parent;
    if (!w.__translatePatched) {
      w.__translatePatched = true;
      const P = w.Node.prototype, remove = P.removeChild, insert = P.insertBefore;
      P.removeChild = function (child) {
        return child.parentNode === this ? remove.call(this, child)
          : (child.parentNode ? remove.call(child.parentNode, child) : child);
      };
      P.insertBefore = function (node, ref) {
        return ref && ref.parentNode !== this ? this.appendChild(node) : insert.call(this, node, ref);
      };
    }
    </script>""",
    height=0,
)


@st.cache_data
def load_index():
    reports = json.loads(INDEX.read_text(encoding="utf-8"))["reports"]
    return [r for r in reports if (ROOT / r["path"]).is_file()]


@st.cache_data
def load_report(path):
    return (ROOT / path).read_text(encoding="utf-8", errors="replace")


def label(r):
    return f"{r['date'] or '无日期'} · {r['title']}"


reports = load_index()
by_path = {r["path"]: r for r in reports}

with st.sidebar:
    st.title("📈 AI Berkshire")
    st.caption(f"共 {len(reports)} 份报告")
    query = st.text_input("搜索标题 / 公司", "").strip().lower()

    if query:
        options = [
            r for r in reports
            if query in r["title"].lower() or query in r["group"].lower() or query in r["path"].lower()
        ]
        st.caption(f"匹配 {len(options)} 份")
    else:
        buckets = sorted({r["bucket"] for r in reports})
        bucket = st.selectbox("分类", buckets, index=buckets.index("公司") if "公司" in buckets else 0)
        in_bucket = [r for r in reports if r["bucket"] == bucket]
        groups = sorted({r["group"] for r in in_bucket})
        group = st.selectbox("分组", groups)
        options = [r for r in in_bucket if r["group"] == group]

    options = sorted(options, key=lambda r: r["date"] or "", reverse=True)
    paths = [r["path"] for r in options]
    current = st.query_params.get("r")
    selected = st.radio(
        "报告",
        paths,
        index=paths.index(current) if current in paths else 0,
        format_func=lambda p: label(by_path[p]),
    ) if paths else None

if not selected:
    st.info("没有匹配的报告。")
    st.stop()

st.query_params["r"] = selected  # 地址栏可直接分享当前报告
meta = by_path[selected]
st.caption(" · ".join(x for x in (meta["bucket"], meta["group"], meta["type"], meta["date"], selected) if x))

text = load_report(selected)
if len(text) > MAX_CHARS:
    st.warning(f"文件较大（{len(text):,} 字符），仅显示前 {MAX_CHARS:,} 字符；完整内容请下载。")
st.download_button("下载 Markdown", text, file_name=Path(selected).name)
st.markdown(text[:MAX_CHARS])
