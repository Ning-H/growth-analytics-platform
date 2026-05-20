# Attribution Methodology

This project uses a 30-day lookback window from each conversion to eligible TikTok Ads touchpoints for the same resolved user, advertiser, and product.

Eligible touchpoints are `ad_impression`, `video_view`, `ad_click`, and `engagement`. A `video_view` can also be a conversion only for `brand_awareness` campaigns when the simulator emits a conversion id.

## Models

| Model | Rule |
|---|---|
| First touch | Earliest eligible touchpoint receives 100% credit. |
| Last touch | Latest eligible touchpoint receives 100% credit. |
| Linear | Every eligible touchpoint receives equal credit. |
| Time decay | Credit is weighted by exponential decay with a 7-day half-life. |
| Position based | First touch receives 40%, last touch receives 40%, and middle touches split 20%. For two touches, each gets 50%. |

## Example

For a journey:

```text
tiktok_ad_impression -> google_ad_click -> email_engagement -> purchase($100)
```

The models assign credit as:

| Model | TikTok impression | Google click | Email engagement |
|---|---:|---:|---:|
| First touch | $100 | $0 | $0 |
| Last touch | $0 | $0 | $100 |
| Linear | $33.33 | $33.33 | $33.33 |
| Time decay | Depends on recency; newer touches receive more credit. |
| Position based | $40 | $20 | $40 |

The dbt test `attribution_credit_sums_to_one` fails if any included conversion has total attribution credit outside a tight floating-point tolerance.
