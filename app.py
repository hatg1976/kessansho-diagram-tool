"""
決算書図解ツール - スタンドアロン SaaS 版
無料プラン：1期のみ・エクスポートなし
有料プラン：3期比較・PNG/PDFエクスポート
"""

import streamlit as st
import plotly.graph_objects as go
from datetime import datetime

# ─────────────────────────────────────────────────────────────────
# ページ設定
# ─────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="決算書図解ツール",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────────────────────────
# プラン管理
# ─────────────────────────────────────────────────────────────────
def _is_paid() -> bool:
    return st.session_state.get("plan") == "paid"

def _try_unlock(code: str) -> bool:
    """入力コードを secrets の PAID_CODES リストと照合"""
    codes = st.secrets.get("PAID_CODES", [])
    return code.strip() in codes

# ─────────────────────────────────────────────────────────────────
# X レイアウト
# ─────────────────────────────────────────────────────────────────
BS_A = (0,   95)
BS_L = (95,  190)
REV  = (230, 365)
MAIN = (365, 500)
FIX  = (500, 635)
SUB  = (635, 770)
RT   = (770, 880)
CF   = (880, 990)
W    = 995


# ─────────────────────────────────────────────────────────────────
# 図解描画
# ─────────────────────────────────────────────────────────────────
def _draw_block_diagram(bs, pl, year_label, unit_label, watermark=False):

    curr_a  = bs["流動資産"];  fix_a  = bs["固定資産"];  def_a = bs["繰延資産"]
    curr_l  = bs["流動負債"];  fix_l  = bs["固定負債"];  eqy   = bs["純資産"]
    total_a = curr_a + fix_a + def_a

    rev     = pl["売上高"];    var    = pl["変動費"];    fix    = pl["固定費"]
    non_rev = pl["営業外収益"]; non_exp = pl["営業外費用"]
    sp_gn   = pl["特別利益"];  sp_ls  = pl["特別損失"];  tax    = pl["法人税等"]
    jinken  = pl.get("人件費", 0);  deprec = pl.get("減価償却費", 0)

    gross     = rev - var
    gross_r   = gross / rev if rev else 0
    ord_p     = gross - fix + non_rev - non_exp
    pre_tax   = ord_p + sp_gn - sp_ls
    net       = pre_tax - tax
    bep       = fix / gross_r if gross_r > 0 else None
    rodo      = jinken / gross if gross > 0 else 0
    other_fix = max(0.0, fix - jinken - deprec)
    overflow  = max(0.0, fix - gross)

    ca_top = total_a;   ca_bot = total_a - curr_a
    fa_top = ca_bot;    fa_bot = def_a
    da_top = def_a;     da_bot = 0.0

    if eqy >= 0:
        cl_top = total_a;   cl_bot = total_a - curr_l
        fl_top = cl_bot;    fl_bot = eqy
        eq_top = eqy;       eq_bot = 0.0
        eq_negative = False
    else:
        fl_bot = eqy;       fl_top = eqy + fix_l
        cl_bot = fl_top;    cl_top = total_a
        eq_top = 0.0;       eq_bot = eqy
        eq_negative = True

    var_top = rev;    var_bot = gross
    gro_top = gross;  gro_bot = 0.0

    fc_in_top = gross;  fc_in_bot = 0.0
    ov_top    = 0.0;    ov_bot    = -overflow

    fix_top_coord = min(fix, gross)
    sy = fix_top_coord
    def _take(h):
        nonlocal sy
        top = sy;  bot = sy - max(0.0, h);  sy = bot;  return top, bot

    j_top,  j_bot  = _take(jinken)
    dp_top, dp_bot = _take(deprec)
    ot_top, ot_bot = _take(other_fix)

    y_neg = min(0.0, -overflow, ord_p if ord_p < 0 else 0, net if net < 0 else 0,
                eqy if eqy < 0 else 0)
    y_pos = max(rev + max(non_rev, 0.0), total_a)
    y_min = y_neg * 1.35 if y_neg < 0 else -rev * 0.05
    y_max = y_pos * 1.18

    shapes, anns = [], []

    def rect(xs, y0, y1, fill, lclr="#444", lw=0.8):
        if y1 <= y0:
            return
        shapes.append(dict(type="rect", x0=xs[0], y0=y0, x1=xs[1], y1=y1,
                           fillcolor=fill, line=dict(color=lclr, width=lw), layer="below"))

    def hline(xs, y, clr="#444", lw=1.0):
        shapes.append(dict(type="line", x0=xs[0], y0=y, x1=xs[1], y1=y,
                           line=dict(color=clr, width=lw)))

    def _label(x, y, txt, sz, clr, xa="center", ya="middle",
               bg=None, bc=None, bold=False):
        t = f"<b>{txt}</b>" if bold else txt
        a = dict(x=x, y=y, text=t, showarrow=False,
                 font=dict(size=sz, color=clr),
                 xanchor=xa, yanchor=ya, align="center")
        if bg:
            a.update(bgcolor=bg, bordercolor=bc or "#888", borderwidth=1, borderpad=3)
        anns.append(a)

    def box(xs, y0, y1, txt, sz=9, clr="#222", bold=False, oneline=False):
        if y1 <= y0:
            return
        h  = y1 - y0
        cx = (xs[0] + xs[1]) / 2
        cy = (y0 + y1) / 2
        t  = txt.replace("<br>", " ") if oneline else txt
        if h >= rev * 0.025:
            _label(cx, cy, t, sz, clr, bold=bold)
        elif h >= rev * 0.008:
            _label(cx, cy, t, max(8, sz - 2), clr, bold=bold)
        else:
            anns.append(dict(x=xs[1] + 3, y=cy,
                             text=t.replace("<br>", " "),
                             showarrow=True, arrowhead=2, arrowsize=0.5,
                             ax=25, ay=0, arrowcolor="#666",
                             font=dict(size=8, color=clr),
                             xanchor="left", yanchor="middle",
                             bgcolor="rgba(255,255,255,0.85)",
                             bordercolor="#aaa", borderwidth=0.5, borderpad=2))

    BS  = "#FAF3E0"
    PL  = "#E8F4FD"
    BDR = "#888"

    rect(BS_A, ca_bot, ca_top, BS, BDR)
    box( BS_A, ca_bot, ca_top, f"流動資産<br>{curr_a:,.0f}", 11, "#222", True)
    rect(BS_A, fa_bot, fa_top, BS, BDR)
    box( BS_A, fa_bot, fa_top, f"固定資産<br>{fix_a:,.0f}",  11, "#222", True)
    if def_a > 0:
        rect(BS_A, da_bot, da_top, BS, BDR)
        box( BS_A, da_bot, da_top, f"繰延資産<br>{def_a:,.0f}", 10, "#222")

    rect(BS_L, cl_bot, cl_top, BS, BDR)
    box( BS_L, cl_bot, cl_top, f"流動負債<br>{curr_l:,.0f}", 11, "#222", True)
    rect(BS_L, fl_bot, fl_top, BS, BDR)
    box( BS_L, fl_bot, fl_top, f"固定負債<br>{fix_l:,.0f}",  11, "#222", True)
    if eq_negative:
        rect(BS_A, eq_bot, eq_top, BS, BDR)
        box( BS_A, eq_bot, eq_top, f"▲純資産<br>{eqy:,.0f}", 11, "#222", True)
    else:
        rect(BS_L, eq_bot, eq_top, BS, BDR)
        box( BS_L, eq_bot, eq_top, f"純資産<br>{eqy:,.0f}",  11, "#222", True)

    rect(REV, 0, rev, PL, BDR)
    box( REV, 0, rev, f"売上高<br>{rev:,.0f}", 12, "#222", True)
    hline(REV, rev, BDR, 1.5)

    rect(MAIN, var_bot, var_top, PL, BDR)
    box( MAIN, var_bot, var_top, f"変動費<br>{var:,.0f}", 12, "#222", True)
    rect(MAIN, gro_bot, gro_top, PL, BDR)
    box( MAIN, gro_bot, gro_top, f"粗利益<br>{gross:,.0f}", 12, "#222", True)
    hline(MAIN, gross, BDR, 1.2)
    hline(MAIN, rev,   BDR, 1.5)

    fix_top = min(fix, gross)
    fix_bot = -overflow
    rect(FIX, fix_bot, fix_top, PL, BDR, 1.0)
    box( FIX, fix_bot, fix_top, f"固定費<br>{fix:,.0f}", 11, "#222", True)
    hline(FIX, 0, BDR, 1.0)

    if jinken > 0 and j_top > j_bot:
        rect(SUB, j_bot,  j_top,  PL, BDR)
        box( SUB, j_bot,  j_top,  f"人件費 {jinken:,.0f}", 10, "#222", oneline=True)
    if deprec > 0 and dp_top > dp_bot:
        rect(SUB, dp_bot, dp_top, PL, BDR)
        box( SUB, dp_bot, dp_top, f"減価償却費 {deprec:,.0f}", 10, "#222", oneline=True)
    if other_fix > 0 and ot_top > ot_bot:
        rect(SUB, ot_bot, ot_top, PL, BDR)
        box( SUB, ot_bot, ot_top, f"その他固定費 {other_fix:,.0f}", 10, "#222", oneline=True)
    hline(SUB, fix_top_coord, BDR, 1.0)
    hline(SUB, 0,             BDR, 0.8)

    if ord_p > 0:
        rect(RT, 0, ord_p, PL, BDR)
        box( RT, 0, ord_p, f"経常利益 {ord_p:,.0f}", 10, "#222", oneline=True)
    elif ord_p < 0:
        rect(RT, ord_p, 0, PL, BDR)
        box( RT, ord_p, 0, f"経常損失 {ord_p:,.0f}", 10, "#222", oneline=True)
    hline(RT, 0, BDR, 0.8)

    if net > 0:
        rect(CF, 0, net, PL, BDR)
        box( CF, 0, net, f"当期純利益 {net:,.0f}", 10, "#222", oneline=True)
    elif net < 0:
        rect(CF, net, 0, PL, BDR)
        box( CF, net, 0, f"当期純損失 {net:,.0f}", 10, "#222", oneline=True)
    hline(CF, 0, BDR, 0.8)

    ann_y = y_max * 0.97
    _label((REV[0]+MAIN[1])/2, ann_y,
           f"粗利益率=粗利益÷売上高<br>{gross_r:.1%}",
           11, "#333", xa="center", ya="top", bg="#FFFACD", bc="#888")
    if jinken > 0 and gross > 0:
        _label((FIX[0]+SUB[1])/2, ann_y,
               f"労働分配率=人件費÷粗利益<br>{rodo:.1%}",
               11, "#333", xa="center", ya="top", bg="#E3F2FD", bc="#888")
    if bep is not None:
        _label(W, ann_y,
               f"損益分岐点売上高=固定費÷粗利益率<br>{bep:,.0f} {unit_label}",
               11, "#B71C1C", xa="right", ya="top", bg="#FFF9C4", bc="#C00")

    # 透かし（無料版）
    if watermark:
        anns.append(dict(
            x=W/2, y=(y_min+y_max)/2,
            text="無料版 — 3期比較・エクスポートは有料版で",
            showarrow=False,
            font=dict(size=18, color="rgba(180,180,180,0.5)"),
            xanchor="center", yanchor="middle",
            textangle=-20,
        ))

    fig = go.Figure()
    fig.update_layout(
        shapes=shapes, annotations=anns,
        xaxis=dict(range=[-10, W+10],
                   showgrid=False, showticklabels=False, zeroline=False, fixedrange=True),
        yaxis=dict(range=[y_min, y_max],
                   showgrid=False, showticklabels=False, zeroline=False, fixedrange=True),
        title=dict(text=year_label, font=dict(size=15), x=0.5, xanchor="center"),
        height=650, margin=dict(l=10, r=10, t=50, b=20),
        plot_bgcolor="white", paper_bgcolor="white",
    )
    return fig


# ─────────────────────────────────────────────────────────────────
# ヘッダー・プランバナー
# ─────────────────────────────────────────────────────────────────
def _render_header():
    st.title("📊 決算書図解ツール")
    st.caption(
        "貸借対照表（BS）・損益計算書（P/L）の数値を入力するだけで、"
        "財務構造をブロック図で即座に可視化します。"
    )

    if _is_paid():
        st.success("✅ 有料プラン利用中 — 3期比較・PNG/PDFエクスポート 有効")
    else:
        st.info(
            "**無料プラン**（1期表示のみ）　|　"
            "[🔓 有料プランにアップグレード（月額500円）](https://buy.stripe.com/YOUR_LINK) "
            "で3期比較・エクスポートが使えます"
        )


# ─────────────────────────────────────────────────────────────────
# アクセスコード入力欄（サイドバー）
# ─────────────────────────────────────────────────────────────────
def _render_sidebar():
    with st.sidebar:
        st.markdown("## 📊 決算書図解ツール")
        st.markdown("---")

        if _is_paid():
            st.success("✅ 有料プラン")
            if st.button("ログアウト"):
                st.session_state["plan"] = "free"
                st.rerun()
        else:
            st.markdown("### 🔓 アクセスコード")
            st.caption("有料プラン購入後に届くコードを入力してください")
            code_input = st.text_input("コード", type="password", label_visibility="collapsed")
            if st.button("認証する", use_container_width=True):
                if _try_unlock(code_input):
                    st.session_state["plan"] = "paid"
                    st.success("✅ 有料プランが有効になりました！")
                    st.rerun()
                else:
                    st.error("コードが正しくありません")

            st.markdown("---")
            st.markdown("### 💳 有料プランを購入")
            st.markdown(
                "**月額 500円**\n\n"
                "- 3期比較\n"
                "- PNG / PDF エクスポート\n"
                "- 透かしなし\n\n"
                "[Stripeで購入する →](https://buy.stripe.com/YOUR_LINK)"
            )

        st.markdown("---")
        st.markdown(
            "### 📖 使い方ガイド\n"
            "[noteで詳しく解説](https://note.com/management_step/n/n7185c002ac3d)"
        )


# ─────────────────────────────────────────────────────────────────
# メイン入力フォーム
# ─────────────────────────────────────────────────────────────────
def _render_form():
    paid = _is_paid()
    max_years = 3 if paid else 1

    with st.expander("📝 基本設定・データ入力", expanded=True):
        c1, c2 = st.columns(2)
        unit_label = c1.selectbox("単位", ["千円", "百万円", "億円"])

        if paid:
            n_years = c2.selectbox("決算期数", [1, 2, 3], index=2)
        else:
            n_years = 1
            c2.selectbox("決算期数", ["1期（無料）"], disabled=True)
            c2.caption("🔒 3期比較は有料プランで")

        _BS_KEYS = ["流動資産", "固定資産", "繰延資産", "流動負債", "固定負債", "純資産"]
        _PL_KEYS = ["売上高", "変動費", "固定費", "営業外収益", "営業外費用",
                    "特別利益", "特別損失", "法人税等", "人件費", "減価償却費"]

        _now = datetime.now()
        _latest_year = _now.year - 1 if _now.month >= 4 else _now.year - 2

        yr_cols = st.columns(3)
        years = []
        for i in range(3):
            with yr_cols[i]:
                disabled = (i >= n_years)
                y = st.number_input(f"第{i+1}期（西暦）", value=_latest_year - 2 + i,
                    min_value=1900, max_value=2100, step=1,
                    disabled=disabled, key=f"year_{i}")
                years.append(int(y))
                if i < n_years:
                    if st.button(f"🗑️ 第{i+1}期をクリア", key=f"clear_{i}"):
                        for k in _BS_KEYS:
                            st.session_state[f"bs_{k}_{i}"] = 0
                        for k in _PL_KEYS:
                            st.session_state[f"pl_{k}_{i}"] = 0
                        st.rerun()

        year_labels = [f"{years[i]}年度" for i in range(3)]

        st.markdown("---")
        tab_bs, tab_pl = st.tabs(["📋 貸借対照表（BS）", "📈 損益計算書（P/L）"])

        BS_DEF = {
            "流動資産": [650, 660, 567],
            "固定資産": [398, 392, 389],
            "繰延資産": [0,   0,   0  ],
            "流動負債": [509, 508, 372],
            "固定負債": [408, 406, 444],
            "純資産":   [131, 138, 140],
        }
        PL_DEF = {
            "売上高":     [1321, 1322, 1327],
            "変動費":     [858,  836,  860 ],
            "固定費":     [300,  491,  484 ],
            "営業外収益": [15,   11,   23  ],
            "営業外費用": [54,   57,   60  ],
            "特別利益":   [2,    2,    1   ],
            "特別損失":   [0,    0,    0   ],
            "法人税等":   [3,    7,    4   ],
            "人件費":     [242,  243,  210 ],
            "減価償却費": [50,   48,   48  ],
        }

        bs = {k: list(v) for k, v in BS_DEF.items()}
        pl = {k: list(v) for k, v in PL_DEF.items()}

        with tab_bs:
            st.markdown("#### 資産の部")
            cols = st.columns(n_years)
            for i, col in enumerate(cols):
                col.markdown(f"**{year_labels[i]}**")
                for key in ["流動資産", "固定資産", "繰延資産"]:
                    bs[key][i] = col.number_input(key, value=BS_DEF[key][i],
                        min_value=0, max_value=9_999_999_999,
                        step=1, key=f"bs_{key}_{i}", format="%d")
                col.metric("資産合計",
                    f"{sum(bs[k][i] for k in ['流動資産','固定資産','繰延資産']):,.0f}")

            st.markdown("#### 負債・純資産の部")
            cols2 = st.columns(n_years)
            for i, col in enumerate(cols2):
                col.markdown(f"**{year_labels[i]}**")
                for key in ["流動負債", "固定負債"]:
                    bs[key][i] = col.number_input(key, value=BS_DEF[key][i],
                        min_value=0, max_value=9_999_999_999,
                        step=1, key=f"bs_{key}_{i}", format="%d")
                bs["純資産"][i] = col.number_input("純資産", value=BS_DEF["純資産"][i],
                    min_value=-9_999_999_999, max_value=9_999_999_999,
                    step=1, key=f"bs_純資産_{i}", format="%d")
                col.metric("負債・純資産合計",
                    f"{sum(bs[k][i] for k in ['流動負債','固定負債','純資産']):,.0f}")

        with tab_pl:
            PL_FIELDS = [
                ("売上高",     "売上高"),
                ("変動費",     "変動費合計（製造原価＋販管費の変動費）"),
                ("固定費",     "固定費合計（製造原価＋販管費の固定費）"),
                ("営業外収益", "営業外収益"),
                ("営業外費用", "営業外費用（支払利息等）"),
                ("特別利益",   "特別利益"),
                ("特別損失",   "特別損失"),
                ("法人税等",   "法人税等"),
                ("人件費",     "人件費（固定費の内訳・任意）"),
                ("減価償却費", "減価償却費（固定費の内訳・任意）"),
            ]
            pl_cols = st.columns(n_years)
            for i, col in enumerate(pl_cols):
                col.markdown(f"**{year_labels[i]}**")
                for key, label in PL_FIELDS:
                    pl[key][i] = col.number_input(label, value=PL_DEF[key][i],
                        min_value=0, max_value=9_999_999_999,
                        step=1, key=f"pl_{key}_{i}", format="%d")

    return bs, pl, n_years, year_labels, unit_label


# ─────────────────────────────────────────────────────────────────
# 図解出力 + エクスポート
# ─────────────────────────────────────────────────────────────────
def _render_charts(bs, pl, n_years, year_labels, unit_label):
    paid = _is_paid()
    st.markdown(f"## 財務状況　（単位：{unit_label}）")

    for i in range(n_years):
        bs_yr = {k: bs[k][i] for k in bs}
        pl_yr = {k: pl[k][i] for k in pl}
        fig = _draw_block_diagram(bs_yr, pl_yr, year_labels[i], unit_label,
                                  watermark=not paid)
        st.plotly_chart(fig, use_container_width=True)

        # エクスポートボタン（有料のみ）
        if paid:
            ecol1, ecol2, _ = st.columns([1, 1, 4])
            try:
                png_bytes = fig.to_image(format="png", width=1800, height=700, scale=2)
                ecol1.download_button(
                    "📥 PNG",
                    png_bytes,
                    f"financial_{year_labels[i]}.png",
                    "image/png",
                    key=f"png_{i}",
                )
                pdf_bytes = fig.to_image(format="pdf", width=1800, height=700)
                ecol2.download_button(
                    "📥 PDF",
                    pdf_bytes,
                    f"financial_{year_labels[i]}.pdf",
                    "application/pdf",
                    key=f"pdf_{i}",
                )
            except Exception:
                st.caption("⚠️ エクスポートには `kaleido` パッケージが必要です")
        else:
            st.caption("🔒 PNG/PDF エクスポートは有料プランで利用できます")

        st.markdown("---")


# ─────────────────────────────────────────────────────────────────
# エントリポイント
# ─────────────────────────────────────────────────────────────────
def main():
    _render_sidebar()
    _render_header()
    bs, pl, n_years, year_labels, unit_label = _render_form()
    _render_charts(bs, pl, n_years, year_labels, unit_label)


if __name__ == "__main__":
    main()
