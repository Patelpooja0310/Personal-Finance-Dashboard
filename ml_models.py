# ml_models.py — ML Prediction: Linear Regression vs Random Forest vs Decision Tree
 
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.tree import DecisionTreeRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
import plotly.graph_objects as go
 
 
# ─── Prepare monthly expense data for ML ─────────────────────────────────────
 
def prepare_ml_data(df: pd.DataFrame):
    """
    Converts raw transactions into monthly expense totals
    and creates a numeric 'Month_Num' feature for ML.
    """
    expense_df = df[df["Amount"] < 0].copy()
    expense_df["Month"] = expense_df["Date"].dt.to_period("M").astype(str)
    monthly = expense_df.groupby("Month")["Amount"].sum().abs().reset_index()
    monthly.columns = ["Month", "Total_Expense"]
    monthly = monthly.sort_values("Month").reset_index(drop=True)
    monthly["Month_Num"] = range(1, len(monthly) + 1)
    return monthly
 
 
# ─── Train 3 models & collect results ────────────────────────────────────────
 
def train_all_models(monthly: pd.DataFrame):
    """
    Trains Linear Regression, Random Forest, and Decision Tree.
    Returns a dict with predictions and metrics for each model.
    """
    X = monthly[["Month_Num"]].values
    y = monthly["Total_Expense"].values
 
    # If very little data, use all for training (no test split)
    if len(monthly) < 4:
        X_train, X_test, y_train, y_test = X, X, y, y
    else:
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.25, random_state=42
        )
 
    models = {
        "Linear Regression": LinearRegression(),
        "Random Forest":     RandomForestRegressor(n_estimators=100, random_state=42),
        "Decision Tree":     DecisionTreeRegressor(max_depth=4, random_state=42),
    }
 
    results = {}
    for name, model in models.items():
        model.fit(X_train, y_train)
        preds_full = model.predict(X)
        preds_test = model.predict(X_test)
        mae = mean_absolute_error(y_test, preds_test)
        r2  = r2_score(y_test, preds_test)
        results[name] = {
            "model":        model,
            "predictions":  preds_full,
            "mae":          mae,
            "r2":           r2,
        }
    return results
 
 
# ─── Predict next month ───────────────────────────────────────────────────────
 
def predict_next_month(monthly: pd.DataFrame, results: dict) -> dict:
    """Predict next month's expense for each model."""
    next_num = len(monthly) + 1
    next_preds = {}
    for name, res in results.items():
        val = res["model"].predict([[next_num]])[0]
        next_preds[name] = max(val, 0)          # no negative expense
    return next_preds
 
 
# ─── Actual vs Predicted chart ───────────────────────────────────────────────
 
def plot_predictions(monthly: pd.DataFrame, results: dict) -> go.Figure:
    """
    Returns a Plotly figure showing:
      - Actual expense (black line)
      - Predicted lines for each model (coloured)
    """
    colors = {
        "Linear Regression": "#4F6EF7",
        "Random Forest":     "#22C58B",
        "Decision Tree":     "#F5A623",
    }
 
    fig = go.Figure()
 
    # Actual line
    fig.add_trace(go.Scatter(
        x=monthly["Month"],
        y=monthly["Total_Expense"],
        mode="lines+markers",
        name="Actual Expense",
        line=dict(color="#F05C5C", width=3),
        marker=dict(size=8),
    ))
 
    # Predicted lines
    for name, res in results.items():
        fig.add_trace(go.Scatter(
            x=monthly["Month"],
            y=res["predictions"],
            mode="lines+markers",
            name=f"{name} (Predicted)",
            line=dict(color=colors[name], width=2, dash="dash"),
            marker=dict(size=6),
        ))
 
    fig.update_layout(
        title="📈 Actual vs Predicted Monthly Expenses",
        xaxis_title="Month",
        yaxis_title="Total Expense (₹)",
        height=400,
        legend=dict(orientation="h", y=-0.25),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(gridcolor="#EEEEEE"),
    )
    return fig
 
 
# ─── Model comparison table ───────────────────────────────────────────────────
 
def model_comparison_df(results: dict) -> pd.DataFrame:
    """Returns a DataFrame comparing MAE and R² for all 3 models."""
    rows = []
    for name, res in results.items():
        rows.append({
            "Model":       name,
            "MAE (₹)":     f"₹{res['mae']:,.0f}",
            "R² Score":    f"{res['r2']:.4f}",
            "Accuracy":    f"{max(res['r2']*100, 0):.1f}%",
        })
    return pd.DataFrame(rows)