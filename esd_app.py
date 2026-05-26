# app.py
# ============================================================
# ESD Trade Structure Explorer
# ============================================================
# Required files:
#
# data/esd_state_yearly.csv
# data/core_structure.csv
# data/major_hs_share.csv
# data/hs_country_share.csv
#
# Run:
# streamlit run app.py
# ============================================================

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


DATA_DIR = Path("data")


st.set_page_config(
    page_title="ESD Trade Structure Explorer",
    page_icon="🌐",
    layout="wide",
)


@st.cache_data
def load_csv(path: str) -> pd.DataFrame:
    return pd.read_csv(path)


def file_exists(filename: str) -> bool:
    return (DATA_DIR / filename).exists()


def format_l1(x):
    try:
        return f"{x:,.0f}"
    except Exception:
        return x


def normalize_core_columns(core: pd.DataFrame) -> pd.DataFrame:
    core = core.copy()

    rename_map = {}

    if "CountryEffN" in core.columns:
        rename_map["CountryEffN"] = "CoreCountryEffN"
    if "HSEffN" in core.columns:
        rename_map["HSEffN"] = "CoreHSEffN"
    if "EffN_country" in core.columns:
        rename_map["EffN_country"] = "CoreCountryEffN"
    if "EffN_HS" in core.columns:
        rename_map["EffN_HS"] = "CoreHSEffN"

    return core.rename(columns=rename_map)


def normalize_hs_share_columns(hs: pd.DataFrame) -> pd.DataFrame:
    hs = hs.copy()

    if "cmdCode" in hs.columns:
        hs["cmdCode"] = hs["cmdCode"].astype(str)

    if "share" not in hs.columns and "primaryValue" in hs.columns:
        total = hs.groupby("refYear")["primaryValue"].transform("sum")
        hs["share"] = hs["primaryValue"] / total

    return hs


def normalize_hs_country_columns(hc: pd.DataFrame) -> pd.DataFrame:
    hc = hc.copy()

    if "cmdCode" not in hc.columns:
        hc["cmdCode"] = "85"

    hc["cmdCode"] = hc["cmdCode"].astype(str)

    if "partnerDesc" not in hc.columns and "Country" in hc.columns:
        hc = hc.rename(columns={"Country": "partnerDesc"})

    if "share" not in hc.columns and "primaryValue" in hc.columns:
        total = hc.groupby(["refYear", "cmdCode"])["primaryValue"].transform("sum")
        hc["share"] = hc["primaryValue"] / total

    return hc


st.sidebar.title("ESD Explorer")

available_files = {
    "State": file_exists("esd_state_yearly.csv"),
    "Core": file_exists("core_structure.csv"),
    "HS share": file_exists("major_hs_share.csv"),
    "HS-country": file_exists("hs_country_share.csv"),
}

for name, ok in available_files.items():
    st.sidebar.write(f"{'✅' if ok else '⚠️'} {name}")


st.title("ESD Trade Structure Explorer")

st.markdown(
    """
**ESD (Emergent Structure Dynamics)** transforms trade tables into dynamic state-space representations.

$$
\\mathbf{S}_t = (L1_t, EffN_{country,t}, EffN_{HS,t})
$$

DOI: **10.5281/zenodo.20389082**
"""
)


if not file_exists("esd_state_yearly.csv"):
    st.error(
        """
`data/esd_state_yearly.csv` not found.

Create it from the notebook first, then place it under the `data/` folder.
"""
    )
    st.stop()


state = load_csv(str(DATA_DIR / "esd_state_yearly.csv"))

required_state_cols = {
    "refYear",
    "L1",
    "EffN_country",
    "EffN_HS",
}

missing = required_state_cols - set(state.columns)

if missing:
    st.error(f"Missing columns in esd_state_yearly.csv: {missing}")
    st.stop()

if "Gap" not in state.columns:
    state["Gap"] = state["EffN_country"] - state["EffN_HS"]


latest = state.sort_values("refYear").iloc[-1]

c1, c2, c3, c4 = st.columns(4)

c1.metric("Latest year", int(latest["refYear"]))
c2.metric("L1 export scale", format_l1(latest["L1"]))
c3.metric("EffN country", f"{latest['EffN_country']:.2f}")
c4.metric("EffN HS", f"{latest['EffN_HS']:.2f}")


tab_overview, tab_state, tab_gap, tab_core, tab_hs, tab_detail, tab_data = st.tabs(
    [
        "Overview",
        "State Trajectory",
        "Diversity Gap",
        "Core Structure",
        "Major HS Share",
        "HS Detail",
        "Data",
    ]
)


with tab_overview:
    st.subheader("Framework")

    st.markdown(
        """
ESD summarizes trade structure with three state variables:

- **L1**: total export scale
- **EffN_country**: effective number of export destinations
- **EffN_HS**: effective number of export products

Core equations:

$$
L1_t = \\sum_i x_i
$$

$$
HHI = \\frac{\\sum_i x_i^2}{(\\sum_i x_i)^2}
$$

$$
EffN = \\frac{1}{HHI}
$$
"""
    )

    st.subheader("Yearly state table")
    st.dataframe(state.sort_values("refYear"), use_container_width=True)


with tab_state:
    st.subheader("ESD State Trajectory")

    fig = px.line(
        state.sort_values("refYear"),
        x="EffN_country",
        y="EffN_HS",
        text="refYear",
        markers=True,
        hover_data={
            "refYear": True,
            "L1": ":,.0f",
            "Gap": ":.3f",
            "EffN_country": ":.3f",
            "EffN_HS": ":.3f",
        },
        title="EffN Country vs EffN HS",
    )

    fig.update_traces(textposition="top center")

    fig.update_layout(
        xaxis_title="Effective Number of Countries",
        yaxis_title="Effective Number of HS Products",
    )

    st.plotly_chart(fig, use_container_width=True)

    st.caption(
        "A movement to the right means broader destination diversity. "
        "A movement upward means broader product diversity."
    )


with tab_gap:
    st.subheader("Diversity Gap")

    st.markdown(
        """
$$
Gap = EffN_{country} - EffN_{HS}
$$

A larger gap means destination diversity is wider than product diversity.
"""
    )

    fig = px.line(
        state.sort_values("refYear"),
        x="refYear",
        y="Gap",
        markers=True,
        title="Diversity Gap",
    )

    fig.update_layout(
        xaxis_title="Year",
        yaxis_title="Gap",
    )

    st.plotly_chart(fig, use_container_width=True)

    fig2 = px.line(
        state.sort_values("refYear"),
        x="refYear",
        y=["EffN_country", "EffN_HS"],
        markers=True,
        title="Country diversity vs HS diversity",
    )

    fig2.update_layout(
        xaxis_title="Year",
        yaxis_title="Effective Number",
        legend_title="Metric",
    )

    st.plotly_chart(fig2, use_container_width=True)


with tab_core:
    st.subheader("Top 10% Core Structure")

    if not file_exists("core_structure.csv"):
        st.warning(
            "`data/core_structure.csv` not found. Export `core_state` from the notebook first."
        )
    else:
        core = load_csv(str(DATA_DIR / "core_structure.csv"))
        core = normalize_core_columns(core)

        required_core_cols = {
            "refYear",
            "CoreCountryEffN",
            "CoreHSEffN",
        }

        missing_core = required_core_cols - set(core.columns)

        if missing_core:
            st.error(f"Missing columns in core_structure.csv: {missing_core}")
        else:
            fig = px.line(
                core.sort_values("refYear"),
                x="refYear",
                y=["CoreCountryEffN", "CoreHSEffN"],
                markers=True,
                title="Core Effective Numbers",
            )

            fig.update_layout(
                xaxis_title="Year",
                yaxis_title="Effective Number",
                legend_title="Metric",
            )

            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(core.sort_values("refYear"), use_container_width=True)


with tab_hs:
    st.subheader("Major HS Share")

    if not file_exists("major_hs_share.csv"):
        st.warning(
            "`data/major_hs_share.csv` not found. Export `hs_year` from the notebook first."
        )
    else:
        hs = load_csv(str(DATA_DIR / "major_hs_share.csv"))
        hs = normalize_hs_share_columns(hs)

        required_hs_cols = {
            "refYear",
            "cmdCode",
            "share",
        }

        missing_hs = required_hs_cols - set(hs.columns)

        if missing_hs:
            st.error(f"Missing columns in major_hs_share.csv: {missing_hs}")
        else:
            hs_codes = sorted(hs["cmdCode"].astype(str).unique())

            default_codes = [
                code
                for code in ["85", "87", "89", "84", "29"]
                if code in hs_codes
            ]

            selected_hs = st.multiselect(
                "Select HS codes",
                hs_codes,
                default=default_codes if default_codes else hs_codes[:5],
            )

            plot_hs = hs[hs["cmdCode"].astype(str).isin(selected_hs)].copy()

            fig = px.line(
                plot_hs.sort_values("refYear"),
                x="refYear",
                y="share",
                color="cmdCode",
                markers=True,
                title="HS share over time",
                hover_data={
                    "primaryValue": ":,.0f"
                    if "primaryValue" in plot_hs.columns
                    else False
                },
            )

            fig.update_layout(
                xaxis_title="Year",
                yaxis_title="Share",
                legend_title="HS Code",
            )

            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(
                plot_hs.sort_values(["cmdCode", "refYear"]),
                use_container_width=True,
            )


with tab_detail:
    st.subheader("HS Country Detail")

    if not file_exists("hs_country_share.csv"):
        st.warning(
            "`data/hs_country_share.csv` not found. Export `hs85_country` or full HS-country share first."
        )
    else:
        hc = load_csv(str(DATA_DIR / "hs_country_share.csv"))
        hc = normalize_hs_country_columns(hc)

        required_hc_cols = {
            "refYear",
            "cmdCode",
            "partnerDesc",
            "share",
        }

        missing_hc = required_hc_cols - set(hc.columns)

        if missing_hc:
            st.error(f"Missing columns in hs_country_share.csv: {missing_hc}")
        else:
            hs_codes = sorted(hc["cmdCode"].astype(str).unique())

            selected_code = st.selectbox(
                "Select HS code",
                hs_codes,
                index=0,
            )

            tmp = hc[hc["cmdCode"].astype(str) == selected_code].copy()

            partners = (
                tmp.groupby("partnerDesc")["share"]
                .mean()
                .sort_values(ascending=False)
                .head(15)
                .index
                .tolist()
            )

            selected_partners = st.multiselect(
                "Select partner countries",
                sorted(tmp["partnerDesc"].dropna().unique()),
                default=partners,
            )

            plot_hc = tmp[tmp["partnerDesc"].isin(selected_partners)].copy()

            fig = px.line(
                plot_hc.sort_values("refYear"),
                x="refYear",
                y="share",
                color="partnerDesc",
                markers=True,
                title=f"Country share structure for HS {selected_code}",
                hover_data={
                    "primaryValue": ":,.0f"
                    if "primaryValue" in plot_hc.columns
                    else False
                },
            )

            fig.update_layout(
                xaxis_title="Year",
                yaxis_title="Share",
                legend_title="Country",
            )

            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(
                plot_hc.sort_values(["partnerDesc", "refYear"]),
                use_container_width=True,
            )


with tab_data:
    st.subheader("Loaded data")

    st.markdown("### State")
    st.dataframe(state, use_container_width=True)

    if file_exists("core_structure.csv"):
        st.markdown("### Core")
        st.dataframe(
            normalize_core_columns(load_csv(str(DATA_DIR / "core_structure.csv"))),
            use_container_width=True,
        )

    if file_exists("major_hs_share.csv"):
        st.markdown("### Major HS Share")
        st.dataframe(
            normalize_hs_share_columns(load_csv(str(DATA_DIR / "major_hs_share.csv"))),
            use_container_width=True,
        )

    if file_exists("hs_country_share.csv"):
        st.markdown("### HS Country Share")
        st.dataframe(
            normalize_hs_country_columns(load_csv(str(DATA_DIR / "hs_country_share.csv"))),
            use_container_width=True,
        )
