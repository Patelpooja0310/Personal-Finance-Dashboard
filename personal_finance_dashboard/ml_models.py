# =============================================================================
# ml_models.py — Machine Learning Models for Financial Forecasting
# Models: Linear Regression | Random Forest | Decision Tree
# Tasks:  Expense Prediction | Savings Forecasting | Spending Analysis
# =============================================================================

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.tree import DecisionTreeRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from typing import Dict, Any, Tuple


# =============================================================================
# FEATURE ENGINEERING
# =============================================================================

def prepare_ml_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert raw transactions into a monthly feature table for ML.

    Input DataFrame columns expected:
        date (datetime), amount (float), type (str: income/expense)

    Returns a DataFrame with columns:
        month, total_expense, total_income, savings, month_num,
        lag1, lag2, lag3, rolling_avg3, rolling_std3
    """
    if df.empty:
        return pd.DataFrame()

    df = df.copy()
    df["date"] = pd.to_datetime(df["date"] if "date" in df.columns else df["Date"])
    df["month"] = df["date"].dt.to_period("M").astype(str)

    expense_df = df[df["amount" if "amount" in df.columns else "Amount"] < 0].copy()
    income_df  = df[df["amount" if "amount" in df.columns else "Amount"] > 0].copy()

    amt_col = "amount" if "amount" in df.columns else "Amount"

    monthly_exp = (
        expense_df.groupby("month")[amt_col].sum().abs()
        .reset_index().rename(columns={amt_col: "total_expense"})
    )
    monthly_inc = (
        income_df.groupby("month")[amt_col].sum()
        .reset_index().rename(columns={amt_col: "total_income"})
    )

    monthly = (
        monthly_exp
        .merge(monthly_inc, on="month", how="outer")
        .fillna(0)
        .sort_values("month")
        .reset_index(drop=True)
    )
    monthly["savings"]    = monthly["total_income"] - monthly["total_expense"]
    monthly["month_num"]  = range(1, len(monthly) + 1)

    # Lag features (previous months' expenses)
    monthly["lag1"] = monthly["total_expense"].shift(1)
    monthly["lag2"] = monthly["total_expense"].shift(2)
    monthly["lag3"] = monthly["total_expense"].shift(3)

    # Rolling statistics
    monthly["rolling_avg3"] = monthly["total_expense"].rolling(3, min_periods=1).mean()
    monthly["rolling_std3"] = monthly["total_expense"].rolling(3, min_periods=1).std().fillna(0)

    return monthly


# =============================================================================
# MODEL TRAINING
# =============================================================================

def _get_features(monthly: pd.DataFrame,
                  drop_nans: bool = True) -> Tuple[pd.DataFrame, pd.Series]:
    """
    Select feature columns and target.
    Uses lag features when enough rows exist, otherwise falls back to month_num only.
    """
    use_lags = len(monthly.dropna()) >= 5
    if use_lags:
        feat_cols = ["month_num", "lag1", "lag2", "lag3", "rolling_avg3", "rolling_std3"]
        data = monthly.dropna(subset=feat_cols).copy()
    else:
        feat_cols = ["month_num", "rolling_avg3"]
        data = monthly.copy()

    X = data[feat_cols]
    y = data["total_expense"]
    return X, y, feat_cols, data


def train_all_models(monthly: pd.DataFrame) -> Dict[str, Any]:
    """
    Train three ML models on monthly expense data.

    Returns a dict keyed by model name:
        {
            "model":       fitted estimator,
            "predictions": np.array (full dataset),
            "mae":         float,
            "rmse":        float,
            "r2":          float,
            "feature_importance": dict (RF & DT only),
        }
    """
    if monthly.empty or len(monthly) < 2:
        return {}

    X, y, feat_cols, data = _get_features(monthly)

    # Minimal split — if not enough rows for a real test set, use all data
    if len(X) < 5:
        X_train, X_test = X, X
        y_train, y_test = y, y
    else:
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, shuffle=False
        )

    estimators = {
        "Linear Regression": LinearRegression(),
        "Random Forest":     RandomForestRegressor(
            n_estimators=200, max_depth=6, random_state=42, n_jobs=-1
        ),
        "Decision Tree":     DecisionTreeRegressor(max_depth=5, random_state=42),
    }

    results: Dict[str, Any] = {}
    for name, model in estimators.items():
        model.fit(X_train, y_train)
        preds_test = model.predict(X_test)
        preds_full = model.predict(X)

        mae  = mean_absolute_error(y_test, preds_test)
        rmse = np.sqrt(mean_squared_error(y_test, preds_test))
        r2   = r2_score(y_test, preds_test)

        # Feature importance (tree-based models)
        fi: Dict[str, float] = {}
        if hasattr(model, "feature_importances_"):
            fi = dict(zip(feat_cols, model.feature_importances_.round(4)))

        results[name] = {
            "model":               model,
            "predictions":         np.maximum(preds_full, 0),
            "mae":                 mae,
            "rmse":                rmse,
            "r2":                  r2,
            "feature_importance":  fi,
            "feat_cols":           feat_cols,
            "data":                data,
        }

    return results


# =============================================================================
# NEXT-MONTH PREDICTION
# =============================================================================

def predict_next_month(monthly: pd.DataFrame,
                       results: Dict[str, Any]) -> Dict[str, float]:
    """
    Predict total expense for the next unseen month using each trained model.
    Returns {"Model Name": predicted_value, ...}
    """
    next_num = len(monthly) + 1
    next_preds: Dict[str, float] = {}

    for name, res in results.items():
        feat_cols = res["feat_cols"]
        next_row: Dict[str, float] = {"month_num": next_num}

        if "lag1" in feat_cols:
            last_expenses = monthly["total_expense"].values
            next_row["lag1"] = last_expenses[-1] if len(last_expenses) >= 1 else 0
            next_row["lag2"] = last_expenses[-2] if len(last_expenses) >= 2 else 0
            next_row["lag3"] = last_expenses[-3] if len(last_expenses) >= 3 else 0
        if "rolling_avg3" in feat_cols:
            next_row["rolling_avg3"] = monthly["total_expense"].tail(3).mean()
        if "rolling_std3" in feat_cols:
            next_row["rolling_std3"] = monthly["total_expense"].tail(3).std() or 0.0

        X_next = pd.DataFrame([next_row])[feat_cols]
        val = res["model"].predict(X_next)[0]
        next_preds[name] = float(max(val, 0))

    return next_preds


# =============================================================================
# SAVINGS FORECASTING
# =============================================================================

def forecast_savings(monthly: pd.DataFrame, months_ahead: int = 6) -> pd.DataFrame:
    """
    Project future savings for the next `months_ahead` months
    using a simple linear trend on historical savings.

    Returns a DataFrame with columns: month_label, projected_savings, lower, upper
    (lower/upper = ±1 std-dev confidence band).
    """
    if monthly.empty or len(monthly) < 2:
        return pd.DataFrame()

    X = monthly[["month_num"]].values
    y = monthly["savings"].values

    model = LinearRegression()
    model.fit(X, y)

    residuals = y - model.predict(X)
    std_err   = np.std(residuals)

    future_nums    = np.arange(len(monthly) + 1, len(monthly) + months_ahead + 1)
    future_savings = model.predict(future_nums.reshape(-1, 1))

    # Build human-readable month labels
    last_period = pd.Period(monthly["month"].iloc[-1], freq="M")
    labels = [(last_period + i).strftime("%b %Y") for i in range(1, months_ahead + 1)]

    return pd.DataFrame({
        "month_label":       labels,
        "projected_savings": future_savings,
        "lower":             future_savings - std_err,
        "upper":             future_savings + std_err,
    })


# =============================================================================
# MONTHLY SPENDING ANALYSIS
# =============================================================================

def spending_anomaly_detection(monthly: pd.DataFrame,
                               threshold_sigma: float = 1.5) -> pd.DataFrame:
    """
    Flag months where expense is anomalously high or low
    using a Z-score approach.

    Returns the input DataFrame with two extra columns:
        z_score, is_anomaly (bool)
    """
    if monthly.empty:
        return monthly

    df = monthly.copy()
    mean_exp = df["total_expense"].mean()
    std_exp  = df["total_expense"].std() or 1.0

    df["z_score"]   = (df["total_expense"] - mean_exp) / std_exp
    df["is_anomaly"] = df["z_score"].abs() > threshold_sigma
    df["anomaly_label"] = df.apply(
        lambda r: "🔴 High" if r["z_score"] > threshold_sigma
                  else ("🟢 Low" if r["z_score"] < -threshold_sigma else "Normal"),
        axis=1,
    )
    return df


def month_over_month_change(monthly: pd.DataFrame) -> pd.DataFrame:
    """
    Add month-over-month % change columns for expense, income, and savings.
    """
    df = monthly.copy()
    for col in ["total_expense", "total_income", "savings"]:
        df[f"{col}_pct_change"] = df[col].pct_change() * 100
    return df


# =============================================================================
# PLOTLY CHARTS
# =============================================================================

def plot_predictions(monthly: pd.DataFrame,
                     results: Dict[str, Any]) -> go.Figure:
    """
    Plotly figure: Actual Expense vs All Model Predictions (dashed lines).
    """
    COLORS = {
        "Linear Regression": "#4F6EF7",
        "Random Forest":     "#22C58B",
        "Decision Tree":     "#F5A623",
    }

    fig = go.Figure()

    # Actual
    fig.add_trace(go.Scatter(
        x=monthly["month"],
        y=monthly["total_expense"],
        mode="lines+markers",
        name="Actual Expense",
        line=dict(color="#F05C5C", width=3),
        marker=dict(size=8),
    ))

    # Predictions
    for name, res in results.items():
        data_used = res["data"]
        fig.add_trace(go.Scatter(
            x=data_used["month"],
            y=res["predictions"],
            mode="lines+markers",
            name=f"{name} (Predicted)",
            line=dict(color=COLORS.get(name, "#888"), width=2, dash="dash"),
            marker=dict(size=6),
        ))

    fig.update_layout(
        title="📈 Actual vs Predicted Monthly Expenses",
        xaxis_title="Month",
        yaxis_title="Total Expense (₹)",
        height=420,
        legend=dict(orientation="h", y=-0.3),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(gridcolor="#EEEEEE"),
        hovermode="x unified",
    )
    return fig


def plot_savings_forecast(historical: pd.DataFrame,
                          forecast: pd.DataFrame) -> go.Figure:
    """
    Plotly figure showing historical savings + future forecast with confidence band.
    """
    fig = go.Figure()

    # Historical savings
    fig.add_trace(go.Scatter(
        x=historical["month"],
        y=historical["savings"],
        mode="lines+markers",
        name="Historical Savings",
        line=dict(color="#22C58B", width=2.5),
        marker=dict(size=7),
    ))

    # Confidence band (shaded)
    fig.add_trace(go.Scatter(
        x=list(forecast["month_label"]) + list(reversed(forecast["month_label"])),
        y=list(forecast["upper"]) + list(reversed(forecast["lower"])),
        fill="toself",
        fillcolor="rgba(79,110,247,0.15)",
        line=dict(color="rgba(0,0,0,0)"),
        hoverinfo="skip",
        showlegend=False,
    ))

    # Forecast line
    fig.add_trace(go.Scatter(
        x=forecast["month_label"],
        y=forecast["projected_savings"],
        mode="lines+markers",
        name="Forecast (6-month)",
        line=dict(color="#4F6EF7", width=2.5, dash="dash"),
        marker=dict(size=7, symbol="diamond"),
    ))

    fig.update_layout(
        title="💰 Savings Forecast (Next 6 Months)",
        xaxis_title="Month",
        yaxis_title="Savings (₹)",
        height=380,
        legend=dict(orientation="h", y=-0.25),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(gridcolor="#EEEEEE"),
    )
    return fig


def plot_anomalies(monthly_with_anomaly: pd.DataFrame) -> go.Figure:
    """Bar chart highlighting anomalous spending months in red."""
    df = monthly_with_anomaly.copy()
    colors = ["#F05C5C" if a else "#4F6EF7" for a in df["is_anomaly"]]

    fig = go.Figure(go.Bar(
        x=df["month"],
        y=df["total_expense"],
        marker_color=colors,
        text=df["anomaly_label"],
        textposition="outside",
        hovertemplate="<b>%{x}</b><br>₹%{y:,.0f}<br>%{text}<extra></extra>",
    ))
    fig.update_layout(
        title="🔍 Monthly Spending Anomaly Detection",
        xaxis_title="Month",
        yaxis_title="Total Expense (₹)",
        height=360,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(gridcolor="#EEEEEE"),
    )
    return fig


# =============================================================================
# MODEL COMPARISON TABLE
# =============================================================================

def model_comparison_df(results: Dict[str, Any]) -> pd.DataFrame:
    """
    Returns a tidy DataFrame comparing MAE, RMSE, R², and Accuracy
    for all trained models, sorted by MAE ascending.
    """
    rows = []
    for name, res in results.items():
        rows.append({
            "Model":      name,
            "MAE (₹)":    f"₹{res['mae']:,.0f}",
            "RMSE (₹)":   f"₹{res['rmse']:,.0f}",
            "R² Score":   f"{res['r2']:.4f}",
            "Accuracy":   f"{max(res['r2'] * 100, 0):.1f}%",
        })

    df = pd.DataFrame(rows)
    # Sort by raw MAE value for ranking
    df["_mae"] = [res["mae"] for res in results.values()]
    df = df.sort_values("_mae").drop(columns=["_mae"])
    df.insert(0, "Rank", range(1, len(df) + 1))
    return df.reset_index(drop=True)
