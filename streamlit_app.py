"""
Streamlit Executive Dashboard for Order_Data.xlsx

Features:
- Robust column normalization + explicit column mapping
- Cached Excel loading
- 6 analysis tabs + executive summary + strategic recommendations
- Plotly Express charts + custom CSS alert boxes
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st


# -----------------------------
# Page config + CSS
# -----------------------------
st.set_page_config(page_title="Order Dashboard", layout="wide")

CUSTOM_CSS = """
<style>
.danger-box {
  padding: 0.8rem 1rem;
  border-radius: 0.75rem;
  background: rgba(255, 0, 0, 0.08);
  border: 1px solid rgba(255, 0, 0, 0.25);
}
.warning-box {
  padding: 0.8rem 1rem;
  border-radius: 0.75rem;
  background: rgba(255, 191, 0, 0.10);
  border: 1px solid rgba(255, 191, 0, 0.35);
}
.success-box {
  padding: 0.8rem 1rem;
  border-radius: 0.75rem;
  background: rgba(0, 128, 0, 0.08);
  border: 1px solid rgba(0, 128, 0, 0.25);
}
.small-muted {
  color: rgba(49, 51, 63, 0.65);
  font-size: 0.9rem;
}
.kpi-card {
  padding: 0.9rem 1rem;
  border-radius: 0.9rem;
  border: 1px solid rgba(49, 51, 63, 0.15);
  background: rgba(255, 255, 255, 0.65);
}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# -----------------------------
# Column normalization + mapping
# -----------------------------
def _norm(s: str) -> str:
    """Normalize a column name to a code-friendly key for matching."""
    s = str(s).strip().lower()
    s = s.replace("&", "and")
    s = re.sub(r"[^\w]+", "_", s)  # spaces, dots, %, etc.
    s = re.sub(r"_+", "_", s).strip("_")
    return s


# Explicit mapping from Excel column names (as in your file) to code-friendly names.
# Note: the loader will still handle case/spaces/underscores variations.
COLUMN_MAPPING_EXPLICIT: Dict[str, str] = {
    "OrderNumber": "order_number",
    "OrderType": "order_type",
    "ReferralOrder": "referral_order",
    "CreatedAt": "created_at",
    "MenuDate": "menu_date",
    "Time": "time",
    "Type": "fulfillment_type",
    "Channel": "channel",
    "Customer": "customer",
    "CustomerID": "customer_id",
    "CustomerEmail": "customer_email",
    "CustomerMobileNumber": "customer_mobile",
    "CorporateID": "corporate_id",
    "Company": "company",
    "Building": "building",
    "PaidStatus": "paid_status",
    "Items": "items",
    "Vendors": "vendor",
    "Outlets": "outlet",
    "Status": "status",
    "Promo": "promo",
    "FeedbackSuggestion": "feedback_suggestion",
    "Selling Cost": "selling_cost",
    "Smart Discount": "smart_discount",
    "Offer Discount": "offer_discount",
    "Discount": "discount",
    "SST to client": "sst_to_client",
    "DeliveryFee": "delivery_fee",
    "MarkupDeliveryFee": "markup_delivery_fee",
    "Vendor Delivery Fee": "vendor_delivery_fee",
    "Tips": "tips",
    "Service Charges": "service_charges",
    "Extra Fee": "extra_fee",
    "Loyalty to Client in Currency": "loyalty_to_client",
    "Loyalty Redeemed": "loyalty_redeemed",
    "Total": "total",
    "Paid": "paid",
    "Due": "due",
    "GMV": "gmv",
    "TOTALFMCHARGES": "total_fm_charges",
    "Allowance": "allowance",
    "Restaurant price": "restaurant_price",
    "SST to vendor": "sst_to_vendor",
    "Total Revenue": "total_revenue",
    "COMMISSION in Currency": "commission_value",
    "COMMISSION %": "commission_pct",
    "Taxable Amount": "taxable_amount",
    "COMMISSION SST": "commission_sst",
    "SmartLogistics Cost": "smartlogistics_cost",
    "Act.SmartLogistics Cost": "act_smartlogistics_cost",
    "Loyalty to Vendor in Currency": "loyalty_to_vendor",
    "Loyalty %": "loyalty_pct",
    "COGS": "cogs",
    "Refund Type": "refund_type",
    "Refund Paid By Vendor": "refund_paid_by_vendor",
    "Refund Amount Customer Due": "refund_amount_customer_due",
    "Refund Amount": "refund_amount",
    "Penalty Amount": "penalty_amount",
    "Customer Care Fee": "customer_care_fee",
    "PaymentGateway Fee": "payment_gateway_fee",
    "Margin": "margin",
    "SmartLogisticMargin": "smart_logistics_margin",
    "Markup": "markup",
    "GrossRevenue": "gross_revenue",
    "Delivery Status": "delivery_status",
    "Self Delivery": "self_delivery",
    "Delivery Type": "delivery_type",
    "Late Reason": "late_reason",
    "Late Remarks": "late_remarks",
    "Tax %": "tax_pct",
}

# For resilient matching across variations.
COLUMN_MAPPING_NORMALIZED: Dict[str, str] = {_norm(k): v for k, v in COLUMN_MAPPING_EXPLICIT.items()}


NUMERIC_CANDIDATES: List[str] = [
    "selling_cost",
    "smart_discount",
    "offer_discount",
    "discount",
    "sst_to_client",
    "delivery_fee",
    "markup_delivery_fee",
    "vendor_delivery_fee",
    "tips",
    "service_charges",
    "extra_fee",
    "loyalty_to_client",
    "loyalty_redeemed",
    "total",
    "paid",
    "due",
    "gmv",
    "total_fm_charges",
    "allowance",
    "restaurant_price",
    "sst_to_vendor",
    "total_revenue",
    "commission_value",
    "commission_pct",
    "taxable_amount",
    "commission_sst",
    "smartlogistics_cost",
    "act_smartlogistics_cost",
    "loyalty_to_vendor",
    "loyalty_pct",
    "cogs",
    "refund_amount_customer_due",
    "refund_amount",
    "penalty_amount",
    "customer_care_fee",
    "payment_gateway_fee",
    "margin",
    "smart_logistics_margin",
    "markup",
    "gross_revenue",
    "tax_pct",
]


def _format_myr(x: float) -> str:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "MYR 0"
    return f"MYR {x:,.0f}"


def _format_pct(x: float) -> str:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "0.00%"
    return f"{x*100:.2f}%"


def _safe_div(n: float, d: float) -> float:
    d = 0.0 if d is None else float(d)
    if abs(d) < 1e-12:
        return 0.0
    return float(n) / d


def _coalesce(df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
    """Return first column present in df among candidates."""
    for c in candidates:
        if c in df.columns:
            return c
    return None


@st.cache_data(show_spinner=False)
def load_data(xlsx_path: str) -> Tuple[pd.DataFrame, Dict[str, str], List[str]]:
    """
    Load the Excel file and rename columns using resilient mapping.
    Returns:
      - cleaned dataframe
      - mapping used (original -> renamed)
      - missing important columns (friendly names)
    """
    try:
        raw = pd.read_excel(xlsx_path)
    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {xlsx_path}")
    except Exception as e:
        raise RuntimeError(f"Failed to read Excel: {e}")

    used_mapping: Dict[str, str] = {}
    new_cols = {}
    for col in raw.columns:
        key = _norm(col)
        if key in COLUMN_MAPPING_NORMALIZED:
            new_name = COLUMN_MAPPING_NORMALIZED[key]
            # avoid collisions
            if new_name in new_cols.values():
                i = 2
                while f"{new_name}_{i}" in new_cols.values():
                    i += 1
                new_name = f"{new_name}_{i}"
            new_cols[col] = new_name
            used_mapping[col] = new_name
        else:
            # keep normalized for safety, but don't force unknown columns
            new_cols[col] = _norm(col)

    df = raw.rename(columns=new_cols).copy()

    # Type fixes
    if "created_at" in df.columns:
        df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")
    if "menu_date" in df.columns:
        df["menu_date"] = pd.to_datetime(df["menu_date"], errors="coerce")

    # Numeric conversions
    for c in NUMERIC_CANDIDATES:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)

    # Ensure key dims exist even if missing
    if "order_number" not in df.columns:
        df["order_number"] = np.arange(1, len(df) + 1).astype(str)

    if "customer_id" not in df.columns and "customer" in df.columns:
        df["customer_id"] = df["customer"].astype(str)
    if "customer" not in df.columns and "customer_id" in df.columns:
        df["customer"] = df["customer_id"].astype(str)

    if "vendor" not in df.columns and "outlet" in df.columns:
        df["vendor"] = df["outlet"].astype(str)
    if "vendor" not in df.columns:
        df["vendor"] = "Unknown"

    important = ["total_revenue", "margin", "smart_logistics_margin", "refund_amount", "delivery_status"]
    missing = [c for c in important if c not in df.columns]

    return df, used_mapping, missing


# -----------------------------
# Calculations (requested funcs)
# -----------------------------
def calculate_overall_metrics(df: pd.DataFrame) -> Dict[str, float]:
    revenue_col = _coalesce(df, ["total_revenue", "gross_revenue", "total", "gmv"])
    margin_col = _coalesce(df, ["margin", "gm1", "gm2"])
    logistics_margin_col = _coalesce(df, ["smart_logistics_margin"])

    total_revenue = float(df[revenue_col].sum()) if revenue_col else 0.0
    order_count = int(df["order_number"].nunique()) if "order_number" in df.columns else len(df)
    avg_order = _safe_div(total_revenue, max(order_count, 1))

    gross_margin = float(df[margin_col].sum()) if margin_col else 0.0
    gross_margin_pct = _safe_div(gross_margin, total_revenue)

    customer_count = int(df["customer_id"].nunique()) if "customer_id" in df.columns else int(df["customer"].nunique())
    vendor_count = int(df["vendor"].nunique()) if "vendor" in df.columns else 0

    logistics_margin = float(df[logistics_margin_col].sum()) if logistics_margin_col else 0.0
    logistics_margin_pct = _safe_div(logistics_margin, total_revenue)

    return {
        "total_revenue": total_revenue,
        "avg_order": avg_order,
        "gross_margin": gross_margin,
        "gross_margin_pct": gross_margin_pct,
        "customer_count": float(customer_count),
        "vendor_count": float(vendor_count),
        "logistics_margin": logistics_margin,
        "logistics_margin_pct": logistics_margin_pct,
        "order_count": float(order_count),
    }


def calculate_customer_concentration(df: pd.DataFrame) -> pd.DataFrame:
    revenue_col = _coalesce(df, ["total_revenue", "gross_revenue", "total", "gmv"])
    if not revenue_col:
        return pd.DataFrame(columns=["customer", "revenue", "share"])

    g = (
        df.groupby("customer", dropna=False)[revenue_col]
        .sum()
        .sort_values(ascending=False)
        .head(10)
        .reset_index()
        .rename(columns={revenue_col: "revenue"})
    )

    total = float(df[revenue_col].sum())
    g["share"] = g["revenue"].apply(lambda x: _safe_div(x, total))
    return g


def calculate_repeat_behavior(df: pd.DataFrame) -> pd.DataFrame:
    revenue_col = _coalesce(df, ["total_revenue", "gross_revenue", "total", "gmv"])
    if not revenue_col:
        return pd.DataFrame(columns=["segment", "customers", "revenue"])

    # Orders per customer
    orders = df.groupby("customer_id")["order_number"].nunique().rename("orders")
    rev = df.groupby("customer_id")[revenue_col].sum().rename("revenue")
    d = pd.concat([orders, rev], axis=1).reset_index()

    bins = [-np.inf, 1, 5, 10, 20, np.inf]
    labels = ["1", "2-5", "6-10", "11-20", "21+"]
    d["segment"] = pd.cut(d["orders"], bins=bins, labels=labels, right=True)

    seg = d.groupby("segment", dropna=False).agg(customers=("customer_id", "nunique"), revenue=("revenue", "sum")).reset_index()
    seg["segment"] = seg["segment"].astype(str)
    # Ensure order
    seg["segment_order"] = seg["segment"].map({l: i for i, l in enumerate(labels)})
    seg = seg.sort_values("segment_order").drop(columns=["segment_order"])
    return seg


def _late_flag(df: pd.DataFrame) -> pd.Series:
    """
    Define late delivery with a conservative heuristic:
    - delivery_status == 'red' OR
    - late_reason not null/empty OR
    - late_remarks not null/empty
    """
    s = pd.Series(False, index=df.index)
    if "delivery_status" in df.columns:
        s = s | (df["delivery_status"].astype(str).str.lower().str.strip() == "red")
    for c in ["late_reason", "late_remarks"]:
        if c in df.columns:
            s = s | (df[c].astype(str).str.strip().replace("nan", "") != "")
    return s


def calculate_vendor_performance(df: pd.DataFrame) -> pd.DataFrame:
    revenue_col = _coalesce(df, ["total_revenue", "gross_revenue", "total", "gmv"])
    margin_col = _coalesce(df, ["margin", "gm1", "gm2"])

    base = df.copy()
    base["is_late"] = _late_flag(base).astype(int)

    g = base.groupby("vendor", dropna=False).agg(
        orders=("order_number", "nunique"),
        revenue=(revenue_col, "sum") if revenue_col else ("order_number", "count"),
        margin=(margin_col, "sum") if margin_col else ("order_number", "count"),
        late_deliveries=("is_late", "sum"),
    ).reset_index()

    if revenue_col and margin_col:
        g["margin_pct"] = g.apply(lambda r: _safe_div(r["margin"], r["revenue"]), axis=1)
    else:
        g["margin_pct"] = 0.0

    # Keep top 10 by revenue (more useful)
    g = g.sort_values(["revenue", "orders"], ascending=False).head(10)
    return g


def calculate_order_size_segments(df: pd.DataFrame) -> pd.DataFrame:
    revenue_col = _coalesce(df, ["total_revenue", "gross_revenue", "total", "gmv"])
    margin_col = _coalesce(df, ["margin", "gm1", "gm2"])
    if not revenue_col:
        return pd.DataFrame(columns=["segment", "orders", "revenue", "margin_pct"])

    d = df.copy()
    # Segment by order revenue
    bins = [-np.inf, 50, 150, 300, 500, 1000, np.inf]
    labels = ["<50", "50-150", "150-300", "300-500", "500-1000", "1000+"]

    d["segment"] = pd.cut(d[revenue_col], bins=bins, labels=labels, right=False)

    seg = d.groupby("segment", dropna=False).agg(
        orders=("order_number", "nunique"),
        revenue=(revenue_col, "sum"),
        margin=(margin_col, "sum") if margin_col else (revenue_col, "sum"),
    ).reset_index()
    seg["segment"] = seg["segment"].astype(str)
    seg["margin_pct"] = seg.apply(lambda r: _safe_div(r["margin"], r["revenue"]), axis=1)

    seg["segment_order"] = seg["segment"].map({l: i for i, l in enumerate(labels)})
    seg = seg.sort_values("segment_order").drop(columns=["segment_order", "margin"])
    return seg


def calculate_logistics_metrics(df: pd.DataFrame) -> Dict[str, float]:
    """
    A pragmatic "net logistics margin" definition.
    You can adjust these components later if your finance definition differs.

    Fees charged (inflow):
      - delivery_fee + markup_delivery_fee + total_fm_charges + service_charges + extra_fee

    Vendor/logistics costs (outflow):
      - vendor_delivery_fee + smartlogistics_cost + act_smartlogistics_cost

    Other costs:
      - payment_gateway_fee + customer_care_fee + penalty_amount

    Net = inflow - outflow - other
    """
    def colsum(name: str) -> float:
        return float(df[name].sum()) if name in df.columns else 0.0

    inflow = (
        colsum("delivery_fee")
        + colsum("markup_delivery_fee")
        + colsum("total_fm_charges")
        + colsum("service_charges")
        + colsum("extra_fee")
    )
    outflow = colsum("vendor_delivery_fee") + colsum("smartlogistics_cost") + colsum("act_smartlogistics_cost")
    other = colsum("payment_gateway_fee") + colsum("customer_care_fee") + colsum("penalty_amount")

    net = inflow - outflow - other
    return {"fees_inflow": inflow, "vendor_and_logistics_costs": outflow, "other_costs": other, "net_logistics_margin": net}


def calculate_operational_risk(df: pd.DataFrame) -> Dict[str, float]:
    total_orders = int(df["order_number"].nunique()) if "order_number" in df.columns else len(df)

    refund_orders = 0
    if "refund_amount" in df.columns:
        refund_orders = int((df["refund_amount"] > 0).sum())
    elif "refund_type" in df.columns:
        refund_orders = int((df["refund_type"].astype(str).str.strip().replace("nan", "") != "").sum())

    late_orders = int(_late_flag(df).sum())

    refund_rate = _safe_div(refund_orders, max(total_orders, 1))
    late_rate = _safe_div(late_orders, max(total_orders, 1))
    on_time = max(0.0, 1.0 - late_rate)

    return {"refund_rate": refund_rate, "late_rate": late_rate, "on_time_rate": on_time, "total_orders": float(total_orders)}


# -----------------------------
# UI helpers
# -----------------------------
def _box(kind: str, title: str, body: str) -> None:
    cls = {"danger": "danger-box", "warning": "warning-box", "success": "success-box"}.get(kind, "warning-box")
    st.markdown(f'<div class="{cls}"><b>{title}</b><br/>{body}</div>', unsafe_allow_html=True)


def _kpi(title: str, value: str, sub: str) -> None:
    st.markdown(
        f'<div class="kpi-card"><div class="small-muted">{title}</div>'
        f'<div style="font-size:1.55rem; font-weight:700; margin-top:0.1rem">{value}</div>'
        f'<div class="small-muted" style="margin-top:0.25rem">{sub}</div></div>',
        unsafe_allow_html=True,
    )


# -----------------------------
# Main app
# -----------------------------
def main() -> None:
    st.title("📊 Order Performance Dashboard")

    with st.sidebar:
        st.header("Data")
        xlsx_path = st.text_input("Excel path", value="Order_Data.xlsx", help="Default expects the file in the app root.")
        st.caption("Tip: You can also upload a file below.")
        upload = st.file_uploader("Upload Excel", type=["xlsx"])

    # Load
    try:
        if upload is not None:
            df, used_map, missing = load_data(upload)
        else:
            df, used_map, missing = load_data(xlsx_path)
    except Exception as e:
        st.error(str(e))
        st.stop()

    if missing:
        _box(
            "warning",
            "Some important columns are missing (dashboard will still run)",
            "Missing: " + ", ".join(missing) + ". You can still explore other tabs.",
        )

    # Executive Summary
    st.subheader("Executive Summary")
    metrics = calculate_overall_metrics(df)

    c1, c2, c3, c4 = st.columns(4, gap="large")
    with c1:
        _kpi("Total Revenue", _format_myr(metrics["total_revenue"]), f"Avg per order: {_format_myr(metrics['avg_order'])}")
    with c2:
        _kpi("Gross Margin", _format_myr(metrics["gross_margin"]), f"Margin: {_format_pct(metrics['gross_margin_pct'])}")
    with c3:
        _kpi("Customers & Vendors", f"{int(metrics['customer_count']):,} / {int(metrics['vendor_count']):,}", f"Orders: {int(metrics['order_count']):,}")
    with c4:
        _kpi("Logistics Margin", _format_myr(metrics["logistics_margin"]), f"Share of revenue: {_format_pct(metrics['logistics_margin_pct'])}")

    st.divider()

    # Tabs
    tabs = st.tabs(
        [
            "1) Customer Concentration",
            "2) Repeat Behavior",
            "3) Vendor Performance",
            "4) Order Size",
            "5) Logistics / Profitability",
            "6) Operational Metrics",
        ]
    )

    # Tab 1
    with tabs[0]:
        st.subheader("Customer Concentration Risk")
        cc = calculate_customer_concentration(df)

        if cc.empty:
            st.info("Not enough information to compute customer concentration (missing revenue column).")
        else:
            left, right = st.columns([2, 1], gap="large")
            with left:
                fig = px.bar(
                    cc.sort_values("share"),
                    x="share",
                    y="customer",
                    orientation="h",
                    hover_data={"revenue": ":,.0f", "share": ":.2%"},
                    labels={"share": "Share of total revenue", "customer": "Customer"},
                    title="Top 10 customers by revenue share",
                )
                fig.update_layout(margin=dict(l=10, r=10, t=50, b=10))
                st.plotly_chart(fig, use_container_width=True)
            with right:
                st.markdown("**Top 10 list**")
                t = cc.copy()
                t["revenue"] = t["revenue"].map(lambda x: _format_myr(x))
                t["share"] = t["share"].map(lambda x: f"{x*100:.2f}%")
                st.dataframe(t[["customer", "revenue", "share"]], use_container_width=True, hide_index=True)

            risky = cc[cc["share"] > 0.10]
            if len(risky) > 0:
                names = ", ".join(risky["customer"].astype(str).tolist())
                _box("danger", "Concentration risk", f"Customers above 10% of revenue: <b>{names}</b>.")
            else:
                _box("success", "Healthy concentration", "No single customer exceeds 10% of revenue in the top 10.")

    # Tab 2
    with tabs[1]:
        st.subheader("Customer Repeat Behavior")
        seg = calculate_repeat_behavior(df)

        if seg.empty:
            st.info("Not enough information to compute repeat behavior (missing revenue column).")
        else:
            total_cust = int(df["customer_id"].nunique())
            one_time = int(seg.loc[seg["segment"] == "1", "customers"].sum()) if "1" in seg["segment"].values else 0
            repeat = total_cust - one_time

            m1, m2, m3 = st.columns(3)
            with m1:
                _kpi("Total customers", f"{total_cust:,}", "")
            with m2:
                _kpi("One-time customers", f"{one_time:,}", _format_pct(_safe_div(one_time, max(total_cust, 1))))
            with m3:
                _kpi("Repeat customers", f"{repeat:,}", _format_pct(_safe_div(repeat, max(total_cust, 1))))

            c1, c2 = st.columns(2, gap="large")
            with c1:
                fig1 = px.bar(seg, x="segment", y="customers", title="Customers by repeat segment", labels={"segment": "Orders per customer"})
                fig1.update_layout(margin=dict(l=10, r=10, t=50, b=10))
                st.plotly_chart(fig1, use_container_width=True)
            with c2:
                fig2 = px.bar(seg, x="segment", y="revenue", title="Revenue by repeat segment", labels={"segment": "Orders per customer"})
                fig2.update_layout(margin=dict(l=10, r=10, t=50, b=10))
                st.plotly_chart(fig2, use_container_width=True)

            # Simple recommendations (data-informed)
            one_time_share = _safe_div(one_time, max(total_cust, 1))
            if one_time_share > 0.60:
                _box("warning", "Retention looks fragile", "A large share of customers are one-time. Consider targeted reactivation and post-purchase journeys.")
            else:
                _box("success", "Retention baseline is decent", "Repeat customers represent a meaningful base. Focus on moving 2-5 to 6-10 orders.")

            st.markdown("**Practical levers**")
            st.write(
                "- Trigger a re-order reminder 3–7 days after delivery\n"
                "- Loyalty: double points on 2nd order (not the 1st)\n"
                "- Corporate accounts: propose scheduled weekly team orders\n"
                "- Identify churn signals: refunds + late delivery → proactive customer care"
            )

    # Tab 3
    with tabs[2]:
        st.subheader("Vendor Performance")
        vp = calculate_vendor_performance(df)

        if vp.empty:
            st.info("Not enough information to compute vendor performance.")
        else:
            # Charts
            left, right = st.columns([2, 1], gap="large")
            with left:
                fig = px.bar(
                    vp.sort_values("revenue"),
                    x="revenue",
                    y="vendor",
                    orientation="h",
                    color="margin_pct",
                    hover_data={"orders": True, "margin_pct": ":.2%", "late_deliveries": True},
                    labels={"revenue": "Revenue", "vendor": "Vendor", "margin_pct": "Margin %"},
                    title="Top vendors by revenue (color = margin %)",
                    color_continuous_scale="RdYlGn",
                )
                fig.update_layout(margin=dict(l=10, r=10, t=50, b=10))
                st.plotly_chart(fig, use_container_width=True)

            with right:
                low = vp[vp["margin_pct"] < 0.005]
                if len(low) > 0:
                    _box("danger", "Low/zero margin vendors", f"{len(low)} vendors under 0.5% margin in top 10. Prioritize pricing / fee fixes.")
                else:
                    _box("success", "Margins acceptable", "No top-10 vendor under 0.5% margin.")

            table = vp.copy()
            table["revenue"] = table["revenue"].map(_format_myr)
            table["margin_pct"] = table["margin_pct"].map(lambda x: f"{x*100:.2f}%")
            st.dataframe(table[["vendor", "orders", "revenue", "margin_pct", "late_deliveries"]], use_container_width=True, hide_index=True)

            st.caption("Note: 'Late deliveries' uses a conservative heuristic based on Delivery Status (red) and Late Reason/Remarks.")

    # Tab 4
    with tabs[3]:
        st.subheader("Order Size Segmentation")
        os = calculate_order_size_segments(df)

        if os.empty:
            st.info("Not enough information to compute order size segments (missing revenue column).")
        else:
            c1, c2 = st.columns(2, gap="large")
            with c1:
                fig1 = px.bar(os, x="segment", y="revenue", title="Revenue by order size segment", labels={"segment": "Order revenue (MYR)"})
                fig1.update_layout(margin=dict(l=10, r=10, t=50, b=10))
                st.plotly_chart(fig1, use_container_width=True)
            with c2:
                fig2 = px.bar(os, x="segment", y="margin_pct", title="Margin % by order size segment", labels={"segment": "Order revenue (MYR)", "margin_pct": "Margin %"})
                fig2.update_layout(margin=dict(l=10, r=10, t=50, b=10))
                st.plotly_chart(fig2, use_container_width=True)

            best = os.sort_values("margin_pct", ascending=False).head(1)
            if len(best) > 0:
                segname = best["segment"].iloc[0]
                mp = best["margin_pct"].iloc[0]
                _box("success", "Best-performing segment", f"Highest margin segment: <b>{segname}</b> ({mp*100:.2f}%).")

    # Tab 5
    with tabs[4]:
        st.subheader("Logistics / Profitability")
        lm = calculate_logistics_metrics(df)

        c1, c2, c3, c4 = st.columns(4, gap="large")
        with c1:
            _kpi("Fees inflow", _format_myr(lm["fees_inflow"]), "Delivery + markups + charges")
        with c2:
            _kpi("Vendor/logistics costs", _format_myr(lm["vendor_and_logistics_costs"]), "Vendor delivery + SmartLogistics")
        with c3:
            _kpi("Other costs", _format_myr(lm["other_costs"]), "Gateway + care + penalties")
        with c4:
            _kpi("Net logistics margin", _format_myr(lm["net_logistics_margin"]), "")

        if lm["net_logistics_margin"] < 0:
            _box("danger", "Crisis: logistics margin is negative", "You are losing money on logistics under the current cost allocation.")
        else:
            _box("success", "Logistics margin positive", "Keep monitoring: this depends heavily on delivery fee vs vendor/logistics costs.")

        st.markdown("**Action ideas**")
        st.write(
            "- Re-price delivery fee tiers for far zones / peak hours\n"
            "- Negotiate vendor delivery fees for top-volume vendors\n"
            "- Reduce re-delivery & customer care cases (root cause: lateness/refunds)\n"
            "- Measure SmartLogistics variance (planned vs actual) and fix outliers"
        )
        st.caption("If your finance definition differs, edit `calculate_logistics_metrics()`.")

    # Tab 6
    with tabs[5]:
        st.subheader("Operational Metrics")
        op = calculate_operational_risk(df)

        c1, c2, c3 = st.columns(3, gap="large")
        with c1:
            _kpi("Refund rate", _format_pct(op["refund_rate"]), f"Orders: {int(op['total_orders']):,}")
        with c2:
            _kpi("Late delivery rate", _format_pct(op["late_rate"]), "Heuristic-based")
        with c3:
            _kpi("On-time delivery", _format_pct(op["on_time_rate"]), "")

        # Alerts with simple ranges
        if op["refund_rate"] > 0.10:
            _box("danger", "Refunds too high", "Refund rate above 10% is usually a serious issue (vendor quality, ops, or wrong expectations).")
        elif op["refund_rate"] > 0.05:
            _box("warning", "Refunds elevated", "Refund rate above 5% deserves investigation.")
        else:
            _box("success", "Refunds under control", "Refund rate is within a common acceptable range.")

        if op["late_rate"] > 0.20:
            _box("danger", "Lateness too high", "Late delivery rate above 20% is typically damaging for retention and unit economics.")
        elif op["late_rate"] > 0.10:
            _box("warning", "Lateness elevated", "Late delivery rate above 10% often correlates with complaints and churn.")
        else:
            _box("success", "Delivery performance acceptable", "Lateness appears manageable based on available signals.")

    st.divider()

    # Strategic recommendations
    st.subheader("Strategic Recommendations (auto-generated)")
    cc = calculate_customer_concentration(df)
    op = calculate_operational_risk(df)
    lm = calculate_logistics_metrics(df)
    metrics = calculate_overall_metrics(df)

    # Basic 90-day impact projection (conservative)
    # Assumption: improve one lever modestly; user should sanity-check.
    proj = 0.0
    # If negative logistics margin, fixing it matters most
    if lm["net_logistics_margin"] < 0:
        proj += abs(lm["net_logistics_margin"]) * 0.25  # recover 25% over 90 days
    # Reduce refunds slightly
    proj += metrics["total_revenue"] * 0.01  # +1% revenue-equivalent via retention/less leakage
    # Improve margin slightly
    proj += metrics["total_revenue"] * 0.005  # +0.5% margin uplift

    r1, r2, r3 = st.columns(3, gap="large")

    with r1:
        risks = []
        if not cc.empty and (cc["share"] > 0.10).any():
            risks.append("High revenue concentration on 1–2 customers")
        if op["refund_rate"] > 0.05:
            risks.append("Refunds are elevated (churn + cost)")
        if op["late_rate"] > 0.10:
            risks.append("Lateness harms repeat rate")
        if lm["net_logistics_margin"] < 0:
            risks.append("Negative logistics unit economics")
        if not risks:
            risks = ["No critical red flags detected from available columns (still validate definitions)."]
        _box("danger", "Critical Risks", "<br/>".join([f"• {x}" for x in risks]))

    with r2:
        opps = [
            "Move 1-order customers into 2–5 with reactivation flows",
            "Fix low-margin vendors first (pricing, fees, assortment)",
            "Focus on best margin order-size segment (push bundles/upsell)",
        ]
        _box("warning", "Opportunities", "<br/>".join([f"• {x}" for x in opps]))

    with r3:
        quick = [
            "Weekly vendor scorecard: margin % + lateness + refunds",
            "Audit top 20 late deliveries: root causes + actions",
            "Standardize delivery fee rules for outlier routes",
        ]
        _box("success", "Quick Wins", "<br/>".join([f"• {x}" for x in quick]))

    st.markdown(f"**90-day impact (rough, conservative):** {_format_myr(proj)}")
    st.caption("This projection is a heuristic. Validate the definitions of 'Margin' and 'Logistics net' with finance.")

    # Debug / transparency
    with st.expander("Show column mapping used"):
        st.write("Original → Renamed (used by the app)")
        st.json(used_map)


if __name__ == "__main__":
    main()
