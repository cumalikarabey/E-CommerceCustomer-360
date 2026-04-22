# Customer 360 Feature Dictionary

| Column | Description |
|---|---|
| `customer_unique_id` | Olist seviyesinde tekil müşteri kimliği |
| `first_order_date` | Müşterinin ilk sipariş tarihi |
| `last_order_date` | Müşterinin son sipariş tarihi |
| `order_count` | Toplam sipariş sayısı |
| `order_count_last_12m` | Son 12 aydaki sipariş sayısı |
| `total_revenue` | Toplam ödeme tutarı |
| `avg_order_value` | Ortalama sipariş değeri |
| `median_order_value` | Medyan sipariş değeri |
| `recency_days` | Snapshot tarihine göre son siparişten geçen gün |
| `order_lifecycle_days` | İlk ve son sipariş arası gün |
| `problem_order_count` | `canceled` / `unavailable` sipariş adedi |
| `problem_order_rate` | Problemli sipariş oranı |
| `avg_review_score` | Ortalama review skoru |
| `low_review_ratio` | 1-2 puanlı review oranı |
| `on_time_delivery_rate` | Tahmin edilen tarihe zamanında teslim oranı |
| `avg_delivery_delay_days` | Ortalama teslimat gecikmesi (gün) |
| `p95_delivery_delay_days` | 95. persentil teslimat gecikmesi |
| `recency_score` | RFM Recency skoru (1-5) |
| `frequency_score` | RFM Frequency skoru (1-5) |
| `monetary_score` | RFM Monetary skoru (1-5) |
| `rfm_score` | Toplam RFM skoru (3-15) |
| `rfm_segment` | RFM segment etiketi |
| `first_acquisition_channel` | (Opsiyonel GA) İlk edinim kanalı |
| `latest_acquisition_channel` | (Opsiyonel GA) Son gözlenen kanal |
| `ga_event_count` | (Opsiyonel GA) O müşteri için event adedi |
| `snapshot_date` | Tablonun üretildiği referans tarih |

