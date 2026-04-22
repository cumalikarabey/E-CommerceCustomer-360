# E-commerce Customer 360 (Olist + Opsiyonel GA)

Bu repo, sipariş seviyesi verilerden müşteri seviyesi bir `customer_360` tablosu üretmek için başlangıç iskeletini içerir.
Odak: veri bilimci gözüyle segmentasyon, yaşam döngüsü analizi, churn/CLV modelleme ve operasyonel içgörü üretimi.

## Ne Üretiyoruz?

Her müşteri için tek satır:
- Kimlik ve yaşam döngüsü: ilk sipariş, son sipariş, sipariş sayısı, recency
- Gelir davranışı: toplam ciro, ortalama sipariş değeri
- Teslimat deneyimi: zamanında teslim oranı, ortalama gecikme
- İade/iptal davranışı: iptal/uygunsuz sipariş oranı
- Yorum kalitesi: ortalama review skoru, düşük review oranı
- RFM: `recency_score`, `frequency_score`, `monetary_score`, `rfm_segment`
- Opsiyonel trafik zenginleştirme: `first_acquisition_channel`, `latest_acquisition_channel`

## Beklenen Olist Dosyaları (`data/raw`)

- `olist_customers_dataset.csv`
- `olist_orders_dataset.csv`
- `olist_order_items_dataset.csv`
- `olist_order_payments_dataset.csv`
- `olist_order_reviews_dataset.csv`

Opsiyonel GA dosyası:
- `ga_customer_events.csv` (veya CLI ile farklı path)

## Kurulum

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

## Çalıştırma

```bash
python scripts/build_customer360.py \
  --data-dir data/raw \
  --output data/processed/customer_360.parquet \
  --ga-file data/raw/ga_customer_events.csv
```

Referans tarih sabitlemek için:

```bash
python scripts/build_customer360.py \
  --data-dir data/raw \
  --output data/processed/customer_360.csv \
  --reference-date 2024-12-31
```

Pipeline varsayilan olarak renkli ve adim adim log basar.

```bash
python scripts/build_customer360.py \
  --data-dir data/raw \
  --output data/processed/customer_360.parquet
```

Log secenekleri:
- `--quiet`: sadece warning/error
- `--no-color`: ANSI renklerini kapatir

Varsayılan dosya adların farklıysa açıkça verebilirsin:

```bash
python scripts/build_customer360.py \
  --data-dir data/raw \
  --output data/processed/customer_360.parquet \
  --customers-file customers.csv \
  --orders-file orders.csv \
  --order-items-file items.csv \
  --order-payments-file payments.csv \
  --order-reviews-file reviews.csv
```

## Sık Hata: `Input file not found`

Bu hata genelde `data/raw` klasörü boş olduğunda veya dosya adları farklı olduğunda gelir.

1. Olist dosyalarını indir (Kaggle linki: [Olist Dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)).
2. Aşağıdaki çekirdek dosyaları `data/raw` altına koy:
   - `olist_customers_dataset.csv`
   - `olist_orders_dataset.csv`
   - `olist_order_items_dataset.csv`
   - `olist_order_payments_dataset.csv`
   - `olist_order_reviews_dataset.csv`
3. Dosya adları farklıysa CLI’de `--*-file` parametrelerini kullan.

## Test

```bash
pytest -q
```

## UI Dashboard (Eski vs Yeni Veri)

Dashboard, ham sipariş verisini ve üretilen `customer_360` tablosunu birlikte görselleştirir:
- Projenin ne işe yaradığı ve pipeline adımları
- Eski (transaction-level) vs yeni (customer-level) veri karşılaştırması
- Tek müşteri drill-down: ham sipariş geçmişi + customer_360 özeti
- RFM segment dağılımı ve segment bazlı gelir

Kurulum:

```bash
pip install -e '.[ui]'
```

Çalıştırma:

```bash
streamlit run ui/customer360_dashboard.py
```

Alternatif:

```bash
make ui
```

## Proje Yapısı

```text
.
├── data/
├── docs/
├── notebooks/
├── scripts/
├── src/customer360/
└── tests/
```

Feature sözlüğü için: `docs/customer360_feature_dictionary.md`
