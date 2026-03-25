# Asset-Pair-Portfolio-Optimiser
Developed as part of my Final Year Project for UCL BSc Computer Science, where this project estimates expected returns by predicting the spread between asset pairs, for portfolio optimisation.  

The notebooks in `src/analysis_notebooks` contain the results gathered from my analysis when comparing Spread-based portfolio optimisation versus traditional MPT portfolio optimiastion (Markowitz), where I estimate and compare the estimated returns

## Pre-requisites

- Python 3.10+
- Pip
- Streamlit
- LSEG Workspace subscription
- Jupyter Notebook (to run the analysis)
- yfinance
- pandas
- numpy
- plotly
- matplotlib
- seaborn

## How to run

### Streamlit

Using the terminal:

Go to the `src/dashboard` via `cd ./src/dashboard` from the root project directory.

Then run `streamlit run app.py`

You will be able to see the visualisations at `http://localhost:8501`. Alternatively you can access via network URL that is given in the terminal.

