from __future__ import annotations

from html import escape
from pathlib import Path
from textwrap import dedent

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components


st.set_page_config(
    page_title="지역 자원 상표 연계 대시보드",
    layout="wide",
)

DATA_DIR = Path(__file__).parent / "data"
SUMMARY_FILE = DATA_DIR / "dashboard_summary.csv"
DETAIL_FILE = DATA_DIR / "dashboard_detail.csv"

DEFAULT_REGION = "경상북도"
DEFAULT_SIGUNGU = "안동시"
CATEGORY_ORDER = ["특산품", "유형유산", "무형유산", "자연유산", "문화축제"]


def normalize_region_name(region: str) -> str:
    aliases = {
        "경상북도": "경북",
        "경상남도": "경남",
        "충청북도": "충북",
        "충청남도": "충남",
        "전북특별자치도": "전북",
        "전라남도": "전남",
        "강원특별자치도": "강원",
        "제주특별자치도": "제주",
        "서울특별시": "서울",
        "부산광역시": "부산",
        "대구광역시": "대구",
        "인천광역시": "인천",
        "광주광역시": "광주",
        "대전광역시": "대전",
        "울산광역시": "울산",
        "세종특별자치시": "세종",
    }
    return aliases.get(region, region)


@st.cache_data(show_spinner=False)
def load_dashboard_source(summary_mtime: float) -> pd.DataFrame:
    df = pd.read_csv(SUMMARY_FILE, encoding="utf-8-sig")
    numeric_cols = ["item_count", "applied_item_count", "application_rate", "application_count"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    for col in ["region", "sigungu", "category", "applied_examples", "unapplied_examples"]:
        df[col] = df[col].fillna("").astype(str)
    return df


def build_dashboard_data(region: str, sigungu: str) -> list[dict]:
    source = load_dashboard_source(SUMMARY_FILE.stat().st_mtime)
    selected = source[source["region"].eq(region) & source["sigungu"].eq(sigungu)]
    rows = []
    for category in CATEGORY_ORDER:
        matched = selected[selected["category"].eq(category)]
        if matched.empty:
            rows.append(
                {
                    "category": category,
                    "item_count": 0,
                    "applied_item_count": 0,
                    "application_rate": 0.0,
                    "applied_examples": [],
                    "application_count": 0,
                    "unapplied_examples": [],
                }
            )
            continue
        row = matched.iloc[0]
        rows.append(
            {
                "category": category,
                "item_count": int(row["item_count"]),
                "applied_item_count": int(row["applied_item_count"]),
                "application_rate": float(row["application_rate"]),
                "applied_examples": [x for x in row["applied_examples"].split("|") if x],
                "application_count": int(row["application_count"]),
                "unapplied_examples": [x for x in row["unapplied_examples"].split("|") if x],
            }
        )
    return rows


def get_region_options() -> pd.DataFrame:
    source = load_dashboard_source(SUMMARY_FILE.stat().st_mtime)
    return (
        source[["region", "sigungu"]]
        .dropna()
        .drop_duplicates()
        .sort_values(["region", "sigungu"])
        .reset_index(drop=True)
    )


@st.cache_data(show_spinner=False)
def load_detail_source(detail_mtime: float) -> pd.DataFrame:
    if not DETAIL_FILE.exists():
        return pd.DataFrame()
    df = pd.read_csv(DETAIL_FILE, encoding="utf-8-sig")
    df["valid_application_count"] = pd.to_numeric(
        df["valid_application_count"], errors="coerce"
    ).fillna(0).astype(int)
    for col in [
        "region",
        "sigungu",
        "category",
        "item_name",
        "application_status",
        "application_numbers",
        "trademark_names",
        "lgst_values",
    ]:
        df[col] = df[col].fillna("").astype(str)
    return df


def render_detail_section(region: str, sigungu: str) -> None:
    st.markdown(
        """
        <style>        div[data-testid="stExpander"] {
            background: #ffffff;
            border: 1px solid #e5e7eb;
            border-radius: 14px;
            box-shadow: 0 12px 30px rgba(15, 23, 42, 0.06);
        }
        div[data-testid="stExpander"] summary {
            font-size: 24px;
            font-weight: 850;
            color: #111827;
        }
        .detail-caption {
            color: #667085;
            font-size: 14px;
            font-weight: 700;
            margin: 0.1rem 0 0.8rem 0;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("\uc804\uccb4 \ubaa9\ub85d \ubcf4\uae30", expanded=False):
        if not DETAIL_FILE.exists():
            st.warning("\uc0c1\uc138 \ubaa9\ub85d \ud30c\uc77c\uc774 \uc5c6\uc2b5\ub2c8\ub2e4.")
            return

        detail = load_detail_source(DETAIL_FILE.stat().st_mtime)
        selected = detail[detail["region"].eq(region) & detail["sigungu"].eq(sigungu)].copy()

        if selected.empty:
            st.info("\uc120\ud0dd\ud55c \uc9c0\uc5ed\uc758 \uc0c1\uc138 \ubaa9\ub85d\uc774 \uc5c6\uc2b5\ub2c8\ub2e4.")
            return

        st.markdown(
            f'<div class="detail-caption">{region} {sigungu} \uae30\uc900 \uc804\uccb4 \ucd9c\uc6d0/\ubbf8\ucd9c\uc6d0 \ud56d\ubaa9\uc744 \uc870\ud68c\ud569\ub2c8\ub2e4.</div>',
            unsafe_allow_html=True,
        )

        category_options = ["\uc804\uccb4"] + [category for category in CATEGORY_ORDER if category in selected["category"].unique()]
        status_order = ["\uc720\ud6a8\ucd9c\uc6d0", "\ucd9c\uc6d0", "\ubbf8\ucd9c\uc6d0"]
        existing_statuses = selected["application_status"].dropna().unique().tolist()
        status_options = ["\uc804\uccb4"] + [
            status for status in status_order if status in existing_statuses
        ]
        status_options += [
            status for status in sorted(existing_statuses) if status not in status_options
        ]

        filter_a, filter_b, filter_c = st.columns([1.1, 1.1, 2.4])
        with filter_a:
            selected_category = st.selectbox("\uc720\ud615", category_options, key="detail_category")
        with filter_b:
            selected_status = st.selectbox("\ucd9c\uc6d0\uc0c1\ud0dc", status_options, key="detail_status")
        with filter_c:
            keyword = st.text_input("\uac80\uc0c9\uc5b4", placeholder="\ud56d\ubaa9\uba85, \ucd9c\uc6d0\ubc88\ud638 \uac80\uc0c9", key="detail_keyword")

        filtered = selected.copy()
        if selected_category != "\uc804\uccb4":
            filtered = filtered[filtered["category"].eq(selected_category)]
        if selected_status != "\uc804\uccb4":
            filtered = filtered[filtered["application_status"].eq(selected_status)]
        if keyword.strip():
            pattern = keyword.strip()
            filtered = filtered[
                filtered["item_name"].str.contains(pattern, case=False, na=False)
                | filtered["application_numbers"].str.contains(pattern, case=False, na=False)
            ]

        display = filtered[[
            "category",
            "item_name",
            "application_status",
            "valid_application_count",
        ]].rename(columns={
            "category": "\uad6c\ubd84",
            "item_name": "\ud56d\ubaa9\uba85",
            "application_status": "\ucd9c\uc6d0\uc0c1\ud0dc",
            "valid_application_count": "\uc720\ud6a8\ucd9c\uc6d0\uac74\uc218",
        })

        st.metric("\uc870\ud68c \ud56d\ubaa9 \uc218", f"{len(display):,}")

        st.dataframe(
            display,
            use_container_width=True,
            height=420,
            hide_index=True,
        )
        st.caption(
            "\ucd9c\uc6d0\uc740 \ucd9c\uc6d0\u00b7\uacf5\uace0\u00b7\ub4f1\ub85d \uc0c1\ud0dc\uc758 \uc0c1\ud45c\ub9cc \ud3ec\ud568\ud558\uba70, "
            "\ucd9c\uc6d0 \ud6c4 \ucde8\ud558\u00b7\uac70\uc808\u00b7\uc18c\uba78\ub41c \uac74\uc740 \uc81c\uc678"
        )


def render_tag_list(items: list[str], kind: str) -> str:
    if not items:
        return '<span class="empty-value">-</span>'
    tags = "".join(f'<span class="tag {kind}">{escape(str(item))}</span>' for item in items)
    return f'<div class="tag-list">{tags}</div>'


def render_category_row(item: dict) -> str:
    category = escape(item["category"])
    item_count = f'{item["item_count"]:,}'
    applied_item_count = f'{item["applied_item_count"]:,}'
    application_rate = f'{item["application_rate"]:.1f}%'
    application_count = f'{item["application_count"]:,}'
    applied_examples = render_tag_list(item["applied_examples"], "applied")
    unapplied_examples = render_tag_list(item["unapplied_examples"], "unapplied")

    return f"""
    <section class="category-row">
        <div class="category-cell">
            <div class="category-name">{category}</div>
            <div class="category-count"><strong>{item_count}</strong>개 품목</div>
        </div>
        <div class="applied-cell">
            <div class="label">출원 품목 수</div>
            <div class="applied-metric"><strong>{applied_item_count}</strong>개</div>
            <div class="rate">{application_rate}</div>
        </div>
        <div class="example-cell">
            
            {applied_examples}
        </div>
        <div class="count-cell">
            <div class="label">출원 건수</div>
            <div class="application-count"><strong>{application_count}</strong><span>건</span></div>
        </div>
        <div class="example-cell">
            
            {unapplied_examples}
        </div>
    </section>
    """


def render_dashboard(data: list[dict]) -> None:
    rows = "\n".join(render_category_row(item) for item in data)
    html = dedent(f"""
        <style>        .stApp {{
            background: #f4f6f8;
        }}
        .block-container {{
            max-width: 1480px;
            padding-top: 1.25rem;
            padding-bottom: 1rem;
        }}
        .table-card {{
            background: #ffffff;
            border: 1px solid #e5e7eb;
            border-radius: 18px;
            box-shadow: 0 18px 42px rgba(15, 23, 42, 0.08);
            overflow: hidden;
        }}
        .table-head,
        .category-row {{
            display: grid;
            grid-template-columns: 1fr 1fr 1.5fr 0.9fr 1.5fr;
            column-gap: 16px;
            align-items: stretch;
        }}
        .table-head {{
            background: #f9fafb;
            color: #475467;
            font-size: 23px;
            font-weight: 850;
            padding: 17px 22px;
            border-bottom: 1px solid #e5e7eb;
        }}
        .category-row {{
            padding: 18px 22px;
            border-bottom: 1px solid #eef0f3;
            min-height: 118px;
        }}
        .category-row:last-child {{
            border-bottom: 0;
        }}
        .category-cell,
        .applied-cell,
        .example-cell,
        .count-cell {{
            display: flex;
            flex-direction: column;
            justify-content: center;
        }}
        .category-row > div {{
            border-right: 1px solid #e1e6ee;
            padding-right: 18px;
        }}
        .category-row > div:last-child {{
            border-right: 0;
            padding-right: 0;
        }}
        .category-name {{
            color: #111827;
            font-size: 23px;
            font-weight: 850;
            line-height: 1.2;
        }}
        .category-count {{
            color: #667085;
            font-size: 16px;
            margin-top: 7px;
        }}
        .category-count strong {{
            color: #111827;
            font-size: 25px;
        }}
        .label {{
            color: #6b7280;
            font-size: 13px;
            font-weight: 800;
            margin-bottom: 8px;
        }}
        .applied-metric {{
            color: #111827;
            font-size: 17px;
            font-weight: 700;
            line-height: 1.15;
        }}
        .applied-metric strong {{
            color: #1d4ed8;
            font-size: 32px;
            font-weight: 900;
        }}
        .rate {{
            color: #2563eb;
            font-size: 17px;
            font-weight: 850;
            margin-top: 7px;
        }}
        .count-cell {{
            padding-left: 6px;
        }}
        .application-count {{
            display: inline-flex;
            align-items: baseline;
            justify-content: flex-start;
            gap: 9px;
            color: #111827;
            padding: 0 24px 0 0;
        }}
        .application-count strong {{
            font-size: 41px;
            font-weight: 950;
            line-height: 1;
        }}
        .application-count span {{
            color: #374151;
            font-size: 19px;
            font-weight: 850;
        }}
        .tag-list {{
            display: flex;
            flex-wrap: wrap;
            gap: 7px;
        }}
        .tag {{
            display: inline-flex;
            align-items: center;
            min-height: 30px;
            border-radius: 999px;
            padding: 6px 11px;
            font-size: 14px;
            font-weight: 800;
            line-height: 1.2;
            word-break: keep-all;
        }}
        .tag.applied {{
            background: #dbeafe;
            color: #1d4ed8;
            border: 1px solid #bfdbfe;
        }}
        .tag.unapplied {{
            background: #ffe4e6;
            color: #be123c;
            border: 1px solid #fecdd3;
        }}
        .empty-value {{
            color: #9ca3af;
            font-size: 17px;
            font-weight: 800;
        }}
        @media (max-width: 1100px) {{
            .table-head {{
                display: none;
            }}
            .category-row {{
                grid-template-columns: 1fr;
                row-gap: 20px;
            }}
            .count-cell {{
                padding-left: 0;
            }}
            .category-row > div {{
                border-right: 0;
                border-bottom: 1px solid #eef0f3;
                padding-right: 0;
                padding-bottom: 16px;
            }}
            .category-row > div:last-child {{
                border-bottom: 0;
                padding-bottom: 0;
            }}
        }}
        </style>
        <main class="table-card">
            <div class="table-head">
                <div>구분</div>
                <div>출원 품목 수 / 비율</div>
                <div>상표 출원 품목 예시</div>
                <div>출원 건수</div>
                <div>상표 미출원 품목 예시</div>
            </div>
            {rows}
        </main>
    """)
    components.html(html, height=900, scrolling=False)


region_options = get_region_options()
region_values = region_options["region"].drop_duplicates().tolist()
default_region_index = region_values.index(DEFAULT_REGION) if DEFAULT_REGION in region_values else 0

st.markdown(
    """
    <style>
    div[data-testid="stElementToolbar"] {
        display: none !important;
        visibility: hidden !important;
    }
    div[data-testid="stDataFrame"] {
        position: relative !important;
    }
    div[data-testid="stDataFrame"] * {
        font-size: 16px !important;
    }
    div[data-testid="stDataFrame"] [role="columnheader"] * {
        font-size: 17px !important;
        font-weight: 800 !important;
    }

    div[data-testid="stSelectbox"] label {
        font-weight: 800 !important;
        color: #111827 !important;
    }
    .filter-title {
        color: #111827;
        font-size: 24px;
        font-weight: 850;
        margin-bottom: 0.35rem;
    }
    </style>
    <div class="filter-title">조회 지역</div>
    """,
    unsafe_allow_html=True,
)

filter_left, filter_right, filter_spacer = st.columns([1, 1, 3.2])
with filter_left:
    selected_region = st.selectbox(
        "행정구역",
        region_values,
        index=default_region_index,
    )

sigungu_values = region_options.loc[
    region_options["region"].eq(selected_region),
    "sigungu",
].drop_duplicates().tolist()
default_sigungu_index = (
    sigungu_values.index(DEFAULT_SIGUNGU)
    if selected_region == DEFAULT_REGION and DEFAULT_SIGUNGU in sigungu_values
    else 0
)
with filter_right:
    selected_sigungu = st.selectbox(
        "시군구",
        sigungu_values,
        index=default_sigungu_index,
    )

dashboard_data = build_dashboard_data(selected_region, selected_sigungu)
render_dashboard(dashboard_data)
render_detail_section(selected_region, selected_sigungu)










