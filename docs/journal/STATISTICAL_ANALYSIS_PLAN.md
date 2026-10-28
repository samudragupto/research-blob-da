# Statistical Analysis Plan

This document details the statistical methodology, estimation techniques, hypothesis testing procedures, and reporting standards for the `research-blob-da` journal extension.

---

## 1. Descriptive Statistics and Estimators

For all quantitative measurements across $N$ independent trials:

1. **Central Tendency**:
   - Arithmetic Mean: $\bar{x} = \frac{1}{N} \sum_{i=1}^N x_i$.
   - Sample Median: $\tilde{x} = \text{Percentile}_{50}(x)$.
2. **Dispersion**:
   - Sample Standard Deviation: $s = \sqrt{\frac{1}{N-1} \sum_{i=1}^N (x_i - \bar{x})^2}$.
   - Interquartile Range (IQR): $Q_3 - Q_1$, where $Q_1 = \text{Percentile}_{25}$ and $Q_3 = \text{Percentile}_{75}$.
   - Range: $[\min(x), \max(x)]$.
3. **Extreme Percentiles**:
   - 95th Percentile ($p_{95}$).
   - 99th Percentile ($p_{99}$): Reported only when sample size $N \ge 100$. For small samples ($N < 100$), $p_{99}$ is explicitly omitted or accompanied by a small-sample distortion warning.

---

## 2. Confidence Interval Estimation

### 2.1 Non-Parametric Bootstrap CI
For timing, throughput, and latency metrics that exhibit positive skewness (non-normal distributions typical in I/O and network operations):
- Method: Percentile Bootstrap with $B = 1,000$ resamples.
- Seed: Deterministic PRNG seed `42` to guarantee exact replication.
- Confidence Level: $95\%$ two-sided confidence interval $[CI_{\text{lower}}, CI_{\text{upper}}]$.

### 2.2 Binomial Proportion CI
For success rates (retrieval success, transaction inclusion success, adversarial detection rate):
- Method: Wilson Score Interval with continuity correction to handle boundary proportions ($p \approx 0$ or $p \approx 1$):
  $$w = \frac{p + \frac{z^2}{2N} \pm z \sqrt{\frac{p(1-p)}{N} + \frac{z^2}{4N^2}}}{1 + \frac{z^2}{N}}$$
  where $z = 1.96$ for $95\%$ confidence.

---

## 3. Comparative Hypothesis Testing

1. **Non-Parametric Group Comparison**:
   - For comparisons between algorithms (e.g., `FE31` vs `FE254b` packing latency, zstd level 1 vs level 3 throughput), the two-sided **Mann-Whitney $U$ test** (Wilcoxon rank-sum test) is used to avoid normality assumptions.
   - Significance threshold: $\alpha = 0.05$.
2. **Paired Comparisons**:
   - For cold-cache versus warm-cache conditions on identical dataset instances, the **Wilcoxon signed-rank test** is applied.

---

## 4. Handling of Missing Data and Outliers

1. **Exclusion Criteria**:
   - Unrecorded warm-up iterations ($N=2$) are discarded by protocol.
   - System interruptions or OS-level external context switches causing >10x deviation from median are flagged as external environmental anomalies and documented; no data points are silently dropped.
2. **Missing Network Data**:
   - Failed RPC requests or dropped public Beacon API queries are recorded as explicit failures with HTTP status codes and error categories; they are never imputed as zeroes or omitted from success rate calculations.
3. **Pending Experiments**:
   - Any experiment not executed due to budget, safety, or network access constraints is recorded as `pending` with zero counts and explicitly marked in all tables and figures.
