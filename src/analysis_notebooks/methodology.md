## Methodology

This chapter details the methodology employed by this project. Section 1 describes the asset universe and data sourcing. Sections 2 and 3 present the cointegration screening procedure and spread modelling framework. Section 4 develops the return estimation approaches. Section 5 formulates the portfolio optimisation problem, and Section 6 describes the backtesting framework.

### 1. Data and Universe

The investment universe comprises 26 large-capitalisation US equities drawn from seven sectors: Technology (Semiconductors), Consumer Staples, Financials, Energy, Airlines, E-Commerce/Cloud, and Healthcare. Stocks were selected on the basis of market capitalisation and sector co-membership, as economic similarity provides a prior expectation of long-run co-movement — a necessary condition for cointegration.

| Sector | Ticker | Name |
|---|---|---|
| Semiconductors | NVDA | Nvidia |
| | AMD | AMD |
| | TSM | TSMC |
| | INTC | Intel |
| Consumer Staples | KO | Coca-Cola |
| | PEP | PepsiCo |
| | COST | Costco |
| | TGT | Target |
| Financials | JPM | JPMorgan Chase |
| | BAC | Bank of America |
| | GS | Goldman Sachs |
| | MS | Morgan Stanley |
| Energy | XOM | ExxonMobil |
| | CVX | Chevron |
| | SLB | Schlumberger |
| | HAL | Halliburton |
| Airlines | DAL | Delta Air Lines |
| | UAL | United Airlines |
| E-Commerce / Cloud | AMZN | Amazon |
| | MSFT | Microsoft |
| | META | Meta |
| | GOOGL | Alphabet |
| Healthcare | JNJ | Johnson & Johnson |
| | PFE | Pfizer |
| | MRK | Merck |
| | ABBV | AbbVie |

From these 26 stocks, 16 candidate pairs are formed within sectors. Restricting pair formation to within-sector groupings reflects the economic rationale that stocks exposed to common demand drivers, regulatory environments, and supply chains are more likely to share a long-run stochastic trend.

Daily adjusted close prices are sourced from the Refinitiv Workspace API at daily frequency. The full sample spans 1 January 2018 to 31 December 2025 and is partitioned into:

- **In-sample (IS):** 1 January 2018 – 31 December 2023 — used for cointegration estimation and model calibration.
- **Out-of-sample (OOS):** 1 January 2024 – 31 December 2025 — reserved exclusively for backtesting.

This temporal split ensures that all model parameters are estimated without look-ahead bias.

***

### 2. Cointegration Screening

The cointegration screening pipeline identifies which of the 16 candidate pairs exhibit a statistically significant long-run equilibrium relationship, following the two-step Engle–Granger procedure.

#### 2.1 Unit Root Testing

A prerequisite for cointegration is that each individual price series is integrated of order one, denoted *I(1)*: non-stationary in levels but stationary in first differences. For each stock, the Augmented Dickey–Fuller (ADF) test is applied to both the level series $P_t$ and its first difference $\Delta P_t$. A series is classified as *I(1)* if:

1. The ADF test on the level series **fails to reject** the null hypothesis of a unit root at the 5% significance level, **and**
2. The ADF test on the first-differenced series **rejects** the null at the 5% level.

The ADF regression takes the form:

$$\Delta P_t = \alpha + \gamma P_{t-1} + \sum_{j=1}^{p} \delta_j \Delta P_{t-j} + \varepsilon_t$$

where the null hypothesis is $H_0: \gamma = 0$ (unit root present). The lag order $p$ is selected automatically using the Akaike Information Criterion (AIC). Only pairs in which both constituents are confirmed *I(1)* proceed to the cointegration step.

#### 2.2 Engle–Granger Procedure

For each candidate pair $(Y_t, X_t)$ passing the *I(1)* filter:

**Step 1 — Cointegrating regression.** Estimate the static OLS regression on the in-sample period:

$$Y_t = \alpha + \beta X_t + \epsilon_t$$

where $\beta$ is the hedge ratio and $\alpha$ is the intercept.

**Step 2 — Residual stationarity test.** Apply the ADF test to the OLS residuals $\hat{\epsilon}_t = Y_t - \hat{\alpha} - \hat{\beta} X_t$. Engle–Granger critical values are used to account for additional estimation uncertainty.

To guard against ordering effects, both orderings ($Y$ on $X$ and $X$ on $Y$) are tested and the ordering yielding the lower ADF $p$-value is retained. A pair is deemed cointegrated if the residual ADF $p$-value is below 0.05.

***

### 3. Spread Modelling

For each cointegrated pair, the spread is constructed and its mean-reverting dynamics are characterised.

#### 3.1 Spread Construction

The spread is defined as the residual from the cointegrating regression estimated on the in-sample period:

$$S_t = Y_t - \hat{\beta} X_t - \hat{\alpha}$$

where $\hat{\beta}$ and $\hat{\alpha}$ are fixed at their in-sample OLS estimates and applied without recalibration to the OOS period. Under the cointegration hypothesis, $S_t$ is a stationary, mean-reverting process with a well-defined long-run equilibrium near zero. The daily log-return of the spread position is:

$$r_t^{S} = \ln\!\left(\frac{Y_t}{Y_{t-1}}\right) - \hat{\beta} \cdot \ln\!\left(\frac{X_t}{X_{t-1}}\right)$$

Using log-returns ensures that the spread return $r_t^S$ is in the same units as the expected change $\mathbb{E}[\Delta S]$ derived from the continuous-time OU model, facilitating direct use of OU-implied forecasts as expected returns in portfolio optimisation.

#### 3.2 Half-Life of Mean Reversion

The speed of mean reversion is characterised via a discrete-time AR(1) regression on the spread:

$$\Delta S_t = \lambda S_{t-1} + \varepsilon_t$$

where $\lambda < 0$ implies mean reversion. The half-life — the expected time for the spread to revert halfway to its equilibrium — is given by:

$$h = -\frac{\ln 2}{\ln(1 + \lambda)} \approx -\frac{\ln 2}{\lambda}$$

A short half-life indicates rapid mean reversion and stronger trading signal quality. Pairs with estimated half-lives shorter than the lookback window ($w = 60$ trading days) are preferred, as this ensures multiple reversion cycles are observed within a single estimation window.

#### 3.3 Hurst Exponent

The Hurst exponent $H$ provides a model-free measure of the persistence or anti-persistence of a time series. For a spread $\{S_t\}$, the variogram at lag $\tau$ is:

$$V(\tau) = \mathbb{E}\left[(S_{t+\tau} - S_t)^2\right]$$

Since $V(\tau) \propto \tau^{2H}$, the Hurst exponent is estimated by regressing $\log V(\tau)$ on $\log \tau$ and halving the slope coefficient. Values of $H < 0.5$ indicate mean-reverting (anti-persistent) behaviour; $H = 0.5$ corresponds to a random walk; and $H > 0.5$ indicates trending behaviour. Only pairs for which $H < 0.5$ in-sample are retained, providing a model-free confirmation of mean-reversion consistent with the cointegration result.

#### 3.4 Rolling Z-Score

To generate trading signals that adapt to time-varying spread dynamics, a rolling z-score is computed over a trailing window of $w = 60$ trading days:

$$z_t = \frac{S_t - \bar{S}_t^{(w)}}{\sigma_t^{(w)}}$$

where $\bar{S}_t^{(w)}$ and $\sigma_t^{(w)}$ are the rolling sample mean and standard deviation of the spread. The z-score measures the current dislocation from the local equilibrium in units of local volatility, providing a scale-invariant entry signal.

***

### 4. Return Estimation

#### 4.1 OU-Implied Expected Returns

The Ornstein–Uhlenbeck (OU) process provides the continuous-time stochastic model for the mean-reverting spread:

$$dS_t = \kappa(\theta - S_t)\,dt + \sigma\,dW_t$$

where $\kappa > 0$ is the speed of mean reversion, $\theta$ is the long-run equilibrium level, $\sigma$ is the diffusion coefficient, and $W_t$ is a standard Brownian motion. The mean-reversion speed is linked to the discrete-time half-life estimate by:

$$\kappa = \frac{\ln 2}{h}$$

Conditional on the current spread level $S_t$, the expected change over a single trading period is:

$$\mathbb{E}[\Delta S_{t+1} \mid S_t] = (\theta - S_t)\left(1 - e^{-\kappa}\right)$$

When the spread is below equilibrium ($S_t < \theta$), the forecast is positive (expected upward reversion), and conversely. The long-run mean $\theta$ is estimated as the rolling 60-day sample mean of the spread. Because the spread is constructed from log-prices, the expected change $\mathbb{E}[\Delta S]$ is in log-return units directly comparable to $r_t^S$, and no further normalisation is required.

The annualised OU-implied expected return for spread $i$ is:

$$\mu_i^{\text{OU}} = 252 \cdot \mathbb{E}[\Delta S_{i,T} \mid S_{i,T}]$$

where $T$ denotes the end of the in-sample period. This scalar captures the model's forecast of the spread's tendency to revert at the point of portfolio construction.

#### 4.2 Historical Mean Returns

As a baseline estimator, the expected return for spread $i$ is the sample mean of in-sample log spread returns:

$$\hat{\mu}_i^{\text{hist}} = \frac{252}{T}\sum_{t=1}^{T} r_{i,t}^{S}$$

This estimator is unbiased but exhibits high sampling variance, a well-documented limitation in portfolio optimisation that motivates the use of model-based alternatives such as the OU estimator (Merton, 1980; Black and Litterman, 1992).

#### 4.3 The Zero-Return Baseline

A natural test of the OU return estimates is comparison against a zero-return assumption. Setting $\boldsymbol{\mu} = \mathbf{0}$ effectively asserts that the expected return of every spread is zero. Under this assumption, the maximum-Sharpe objective reduces to:

$$\max_{\mathbf{w}} \frac{0 - r_f}{\sqrt{\mathbf{w}^\top \boldsymbol{\Sigma} \mathbf{w}}} = \min_{\mathbf{w}} \sqrt{\mathbf{w}^\top \boldsymbol{\Sigma} \mathbf{w}}$$

which is precisely the minimum-variance problem. Therefore, the **minimum-variance portfolio serves as the zero-return baseline** — the optimal allocation when no return signal is assumed. Any improvement from using OU-implied returns is measured by comparing the Spread Max-Sharpe (OU) portfolio against the Spread Min-Var portfolio.

Critically, the minimum-variance objective is return-agnostic by construction: its weights depend only on $\boldsymbol{\Sigma}$ and are invariant to the choice of $\boldsymbol{\mu}$. This means that OU-implied returns can only be evaluated through the max-Sharpe objective, not through min-variance weights.

***

### 5. Portfolio Optimisation

Given an expected return vector $\boldsymbol{\mu} \in \mathbb{R}^n$ and covariance matrix $\boldsymbol{\Sigma} \in \mathbb{R}^{n \times n}$ for $n$ spread strategies, the allocation problem is cast in the Markowitz (1952) mean-variance framework.

#### 5.1 Minimum-Variance Portfolio

The minimum-variance portfolio minimises portfolio variance subject to full investment and long-only constraints, with an optional ridge ($L_2$) regularisation term to moderate weight concentration:

$$\min_{\mathbf{w}} \quad \mathbf{w}^\top \boldsymbol{\Sigma} \mathbf{w} + \delta \|\mathbf{w}\|_2^2 \quad \text{subject to} \quad \mathbf{1}^\top \mathbf{w} = 1,\; \mathbf{w} \geq \mathbf{0}$$

where $\delta \geq 0$ controls the regularisation strength. As noted above, this portfolio does not utilise $\boldsymbol{\mu}$ and thus serves simultaneously as the zero-return baseline and the covariance-only allocation.

#### 5.2 Maximum Sharpe Ratio Portfolio

The maximum Sharpe ratio (tangency) portfolio maximises the risk-adjusted excess return:

$$\max_{\mathbf{w}} \quad \frac{\mathbf{w}^\top \boldsymbol{\mu} - r_f}{\sqrt{\mathbf{w}^\top \boldsymbol{\Sigma} \mathbf{w}}} - \delta \|\mathbf{w}\|_2^2$$

subject to the same constraints, where $r_f = 0.02$ is the annualised risk-free rate, set equal to the average 3-month US Treasury Bill rate over the in-sample period. This is the portfolio where the OU-implied return estimates enter the optimisation.

Both problems are solved numerically via Sequential Least Squares Programming (SLSQP), with $L_2$ regularisation parameter $\delta = 0.05$ and tolerance $10^{-12}$.

#### 5.3 Covariance Estimation

The covariance matrix $\boldsymbol{\Sigma}$ is estimated using the **Ledoit–Wolf shrinkage estimator** (Ledoit and Wolf, 2004), which linearly combines the sample covariance matrix with a scaled identity target:

$$\hat{\boldsymbol{\Sigma}}_{\text{LW}} = (1-\rho)\,\hat{\boldsymbol{\Sigma}}_{\text{sample}} + \rho \cdot \mu_{\text{tr}} \mathbf{I}$$

where $\rho \in [0,1]$ is determined analytically by minimising the expected Frobenius norm of the estimation error. Shrinkage improves conditioning relative to the raw sample covariance, which is important when the number of assets is non-trivially large relative to the time series length. All inputs to the optimiser are expressed in annualised units: $\boldsymbol{\mu}_{\text{ann}}$ and $\boldsymbol{\Sigma}_{\text{ann}} = 252 \cdot \boldsymbol{\Sigma}_{\text{daily}}$.

#### 5.4 Spread Space versus Asset Space

Optimisation is performed in two distinct spaces to enable direct comparison:

**Spread-space optimisation** constructs the $n = 3$ cointegrated spread returns and estimates $\boldsymbol{\mu}$ and $\boldsymbol{\Sigma}$ in this lower-dimensional space. Each weight $w_i$ allocates capital to a hedged pair strategy. Spread returns are inherently lower-variance than individual asset returns because the hedge ratio $\hat{\beta}$ removes common-factor exposure, so $\boldsymbol{\Sigma}_{\text{spread}}$ has smaller diagonal entries than $\boldsymbol{\Sigma}_{\text{asset}}$.

**Asset-space optimisation** treats all six underlying stocks independently, estimating $\boldsymbol{\mu}$ from historical log-returns and $\boldsymbol{\Sigma}$ from the full $6 \times 6$ sample covariance with Ledoit–Wolf shrinkage. This corresponds to the conventional historical mean-variance approach.

The two approaches operate over structurally different universes — three hedged spreads versus six raw equities — which has direct implications for the scale of portfolio volatility and the interpretation of volatility reduction metrics.

***

### 6. Backtesting Framework

#### 6.1 In-Sample / Out-of-Sample Split

The temporal split is strict: all model parameters (cointegrating regressions, hedge ratios, OU parameters, and portfolio weights) are estimated on the in-sample period and fixed prior to the OOS evaluation window. No re-estimation or recalibration is performed during the OOS period, ensuring a clean test of generalisation.

**Pair-level signal generation.** A rolling z-score state machine with three thresholds generates discrete positions for each pair independently:

- **Entry** ($|z_t| \geq 2.0$): open a position in the direction of expected reversion when the spread is sufficiently dislocated.
- **Exit** ($z_t \to 0$): close the position once the spread has reverted to its rolling mean.
- **Stop-loss** ($|z_t| \geq 4.0$): force-close the position if the spread diverges materially further, limiting tail losses.

Positions take values in $\{-1, 0, +1\}$, where $+1$ denotes long the spread (long $Y$, short $\hat{\beta}$ units of $X$) and $-1$ denotes the reverse.

**Position sizing and transaction costs.** Full initial capital ($C_0 = \$100{,}000$) is deployed into each active spread position. One spread unit has a notional cost of $Y_t + |\hat{\beta}| \cdot X_t$, so the number of units held is $n_t = C_0 / (Y_t + |\hat{\beta}| X_t)$. Transaction costs of $c = 10$ basis points are applied proportional to the capital traded on each position change. The net daily strategy return is:

$$r_t = \frac{\text{pos}_{t-1} \cdot n_{t-1} \cdot (\Delta Y_t - \hat{\beta} \cdot \Delta X_t) - \text{TC}_t}{C_0}$$

#### 6.2 Portfolio-Level Simulation

Portfolio-level OOS returns are constructed by applying fixed weights $\mathbf{w}$ to the matrix of daily spread returns:

$$r_t^P = \sum_{i=1}^{n} w_i \cdot r_{i,t}^{S}$$

This is equivalent to a buy-and-hold portfolio of spread strategies with rebalancing to fixed weights daily. For the asset-space (historical) portfolios, arithmetic returns $r_{i,t}^{\text{asset}} = (P_{i,t} - P_{i,t-1}) / P_{i,t-1}$ are used in place of log spread returns.

#### 6.3 Evaluation Metrics

**Annualised Sharpe ratio** (Sharpe, 1994):

$$\text{SR} = \frac{\bar{e}}{\hat{\sigma}_e} \cdot \sqrt{252}, \quad e_t = r_t - r_f / 252$$

where $\bar{e}$ is the mean daily excess return and $\hat{\sigma}_e$ is its sample standard deviation (with Bessel correction).

**Maximum drawdown:**

$$\text{MDD} = \min_t \frac{V_t - \max_{\tau \leq t} V_\tau}{\max_{\tau \leq t} V_\tau}, \quad V_t = \prod_{\tau=1}^{t}(1 + r_\tau)$$

**Volatility reduction** relative to the equal-weight spread benchmark:

$$\text{VR} = 1 - \frac{\hat{\sigma}_{\text{strategy}}}{\hat{\sigma}_{\text{benchmark}}}$$

where both annualised volatilities are estimated as $\hat{\sigma} = \hat{\sigma}_{\text{daily}} \cdot \sqrt{252}$. A positive value indicates lower volatility than the benchmark; negative values indicate higher volatility. Note that spread portfolios and asset-space portfolios operate at fundamentally different volatility scales, so the volatility reduction metric is most meaningful within the same universe.

**Total return:** $R_T = \prod_{t=1}^{T}(1 + r_t) - 1$.

**Benchmarks:** (i) equal-weight spread portfolio (average of all spread returns), (ii) equal-weight buy-and-hold of the first cointegrated pair's constituent stocks, and (iii) the S&P 500 index (SPY) as a broad market proxy.
