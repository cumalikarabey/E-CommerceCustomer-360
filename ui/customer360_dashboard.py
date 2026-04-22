from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RAW_DIR = PROJECT_ROOT / "data" / "raw"
DEFAULT_CUSTOMER360_PATH = PROJECT_ROOT / "data" / "processed" / "customer_360.parquet"

RAW_FILE_MAP = {
    "customers": "olist_customers_dataset.csv",
    "orders": "olist_orders_dataset.csv",
    "order_items": "olist_order_items_dataset.csv",
    "order_payments": "olist_order_payments_dataset.csv",
    "order_reviews": "olist_order_reviews_dataset.csv",
}


@st.cache_data(show_spinner=False)
def load_raw_tables(raw_dir: str) -> dict[str, pd.DataFrame]:
    base = Path(raw_dir)
    missing = [name for name in RAW_FILE_MAP.values() if not (base / name).exists()]
    if missing:
        missing_text = "\n".join(f"- {name}" for name in missing)
        raise FileNotFoundError(f"Eksik ham dosyalar:\n{missing_text}")

    tables = {
        key: pd.read_csv(base / file_name, low_memory=False)
        for key, file_name in RAW_FILE_MAP.items()
    }
    return tables


@st.cache_data(show_spinner=False)
def load_customer360(path: str) -> pd.DataFrame:
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"customer_360 dosyası bulunamadı: {file_path}")
    if file_path.suffix.lower() in {".parquet", ".pq"}:
        df = pd.read_parquet(file_path)
    else:
        df = pd.read_csv(file_path, low_memory=False)

    for col in ["first_order_date", "last_order_date", "snapshot_date"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    return df


def prepare_order_view(raw_tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    customers = raw_tables["customers"][["customer_id", "customer_unique_id"]].copy()
    orders = raw_tables["orders"][
        [
            "order_id",
            "customer_id",
            "order_status",
            "order_purchase_timestamp",
            "order_estimated_delivery_date",
            "order_delivered_customer_date",
        ]
    ].copy()
    payments = raw_tables["order_payments"].groupby("order_id", as_index=False).agg(
        payment_value=("payment_value", "sum")
    )
    reviews = raw_tables["order_reviews"].groupby("order_id", as_index=False).agg(
        review_score=("review_score", "mean")
    )

    for col in [
        "order_purchase_timestamp",
        "order_estimated_delivery_date",
        "order_delivered_customer_date",
    ]:
        orders[col] = pd.to_datetime(orders[col], errors="coerce")

    order_view = (
        orders.merge(customers, on="customer_id", how="left")
        .merge(payments, on="order_id", how="left")
        .merge(reviews, on="order_id", how="left")
    )
    order_view["payment_value"] = order_view["payment_value"].fillna(0.0)
    return order_view


def monthly_order_series(order_view: pd.DataFrame) -> pd.Series:
    series = (
        order_view.dropna(subset=["order_purchase_timestamp"])
        .assign(month=lambda d: d["order_purchase_timestamp"].dt.to_period("M").dt.to_timestamp())
        .groupby("month")["order_id"]
        .nunique()
        .sort_index()
    )
    return series


def monthly_new_customer_series(customer360: pd.DataFrame) -> pd.Series:
    if "first_order_date" not in customer360.columns:
        return pd.Series(dtype="float64")
    series = (
        customer360.dropna(subset=["first_order_date"])
        .assign(month=lambda d: d["first_order_date"].dt.to_period("M").dt.to_timestamp())
        .groupby("month")["customer_unique_id"]
        .nunique()
        .sort_index()
    )
    return series


def render_project_story(raw_tables: dict[str, pd.DataFrame], customer360: pd.DataFrame) -> None:
    st.subheader("Bu Proje Ne İşe Yarıyor?")
    st.markdown(
        """
        Bu dashboard, sipariş seviyesindeki ham e-ticaret verisini müşteri seviyesinde tek satırlık bir
        **Customer 360** yapısına dönüştürdüğümüz süreci gösterir.

        Amaç:
        - Müşteriyi tek yerden görmek (gelir, teslimat, yorum, problemli sipariş, RFM)
        - CRM/pazarlama aksiyonlarını segment bazında çalıştırmak
        - Modelleme için (churn/CLV) temiz bir feature tabanı oluşturmak
        """
    )

    st.subheader("Gerçekleştirilen İşlemler")
    st.markdown(
        """
        1. Ham tablolar yüklendi (`customers`, `orders`, `order_items`, `order_payments`, `order_reviews`)
        2. Sipariş seviyesinde ödeme, teslimat ve review metrikleri birleştirildi
        3. Müşteri seviyesinde lifecycle metrikleri üretildi (ilk/son sipariş, recency, gelir, frekans)
        4. Deneyim metrikleri üretildi (on-time delivery, delay, review kalitesi, problem order oranı)
        5. RFM skorları ve segment etiketleri hesaplandı
        6. Nihai çıktı `customer_360.parquet` olarak yazıldı
        """
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Ham Sipariş Satırı", f"{raw_tables['orders'].shape[0]:,}")
    c2.metric("Tekil Sipariş", f"{raw_tables['orders']['order_id'].nunique():,}")
    c3.metric("Tekil Müşteri (unique_id)", f"{raw_tables['customers']['customer_unique_id'].nunique():,}")
    c4.metric("Customer 360 Satırı", f"{customer360.shape[0]:,}")


def render_before_after(raw_tables: dict[str, pd.DataFrame], customer360: pd.DataFrame) -> None:
    st.subheader("Eski Veri vs Yeni Veri")

    order_view = prepare_order_view(raw_tables)
    granularity = pd.DataFrame(
        {
            "Katman": ["Ham Sipariş Verisi", "Customer 360"],
            "Satır Sayısı": [len(order_view), len(customer360)],
        }
    ).set_index("Katman")
    st.caption("Granularity dönüşümü: transaction-level -> customer-level")
    st.bar_chart(granularity)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Ham veri örneği (`orders`)**")
        st.dataframe(raw_tables["orders"].head(15), use_container_width=True)
    with col2:
        st.markdown("**Yeni veri örneği (`customer_360`)**")
        st.dataframe(customer360.head(15), use_container_width=True)

    m1, m2 = st.columns(2)
    with m1:
        st.markdown("**Aylık sipariş hacmi (eski veri)**")
        st.line_chart(monthly_order_series(order_view))
    with m2:
        st.markdown("**Aylık yeni müşteri kazanımı (yeni veri)**")
        st.line_chart(monthly_new_customer_series(customer360))


def render_customer_drilldown(raw_tables: dict[str, pd.DataFrame], customer360: pd.DataFrame) -> None:
    st.subheader("Müşteri Drill-down (Eski + Yeni)")
    order_view = prepare_order_view(raw_tables)
    customer_ids = sorted(customer360["customer_unique_id"].dropna().astype(str).unique().tolist())
    selected = st.selectbox("customer_unique_id seç", customer_ids, index=0)

    selected_360 = customer360[customer360["customer_unique_id"].astype(str) == selected]
    selected_orders = order_view[order_view["customer_unique_id"].astype(str) == selected].sort_values(
        "order_purchase_timestamp", ascending=False
    )

    left, right = st.columns([1, 1.2])
    with left:
        st.markdown("**Customer 360 satırı (özet)**")
        if selected_360.empty:
            st.warning("Seçilen müşteri customer_360 içinde bulunamadı.")
        else:
            st.dataframe(selected_360.T, use_container_width=True)

    with right:
        st.markdown("**Ham sipariş geçmişi (detay)**")
        if selected_orders.empty:
            st.info("Bu müşteri için ham sipariş satırı bulunamadı.")
        else:
            st.dataframe(
                selected_orders[
                    [
                        "order_id",
                        "order_status",
                        "order_purchase_timestamp",
                        "order_estimated_delivery_date",
                        "order_delivered_customer_date",
                        "payment_value",
                        "review_score",
                    ]
                ],
                use_container_width=True,
            )


def render_segment_insights(customer360: pd.DataFrame) -> None:
    st.subheader("Segment ve İş Etkisi")
    if "rfm_segment" not in customer360.columns:
        st.warning("rfm_segment kolonu bulunamadı.")
        return

    seg_counts = (
        customer360["rfm_segment"].fillna("Unknown").value_counts().rename_axis("Segment").to_frame("Müşteri")
    )
    st.markdown("**RFM segment dağılımı**")
    st.bar_chart(seg_counts)

    if "total_revenue" in customer360.columns:
        seg_revenue = (
            customer360.groupby("rfm_segment", as_index=False)
            .agg(
                customers=("customer_unique_id", "nunique"),
                revenue=("total_revenue", "sum"),
                avg_revenue=("total_revenue", "mean"),
            )
            .sort_values("revenue", ascending=False)
        )
        st.markdown("**Segment bazında gelir katkısı**")
        st.dataframe(seg_revenue, use_container_width=True)


def main() -> None:
    st.set_page_config(page_title="E-commerce Customer 360", page_icon="🧭", layout="wide")
    st.title("E-commerce Customer 360 Dashboard")
    st.caption("Sipariş verisinden müşteri yaşam döngüsüne geçişin görsel hikayesi")

    with st.sidebar:
        st.header("Veri Kaynakları")
        raw_dir = st.text_input("Raw data klasörü", str(DEFAULT_RAW_DIR))
        c360_path = st.text_input("Customer 360 dosyası", str(DEFAULT_CUSTOMER360_PATH))
        st.caption("Dosya yollarını değiştirip dashboard'u güncelleyebilirsin.")

    try:
        raw_tables = load_raw_tables(raw_dir)
        customer360 = load_customer360(c360_path)
    except Exception as exc:
        st.error(str(exc))
        st.stop()

    tab1, tab2, tab3, tab4 = st.tabs(
        ["Proje Hikayesi", "Eski vs Yeni Veri", "Müşteri Explorer", "Segment İçgörüleri"]
    )

    with tab1:
        render_project_story(raw_tables, customer360)
    with tab2:
        render_before_after(raw_tables, customer360)
    with tab3:
        render_customer_drilldown(raw_tables, customer360)
    with tab4:
        render_segment_insights(customer360)


if __name__ == "__main__":
    main()

