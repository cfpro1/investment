"""Streamlit app that analyzes Bitcoin-related indicators and generates
short- and mid-term outlooks without relying on an LLM."""

from datetime import datetime, timedelta
from typing import Dict

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf


GBTC_BTC_PER_SHARE = 0.000915  # Approximate BTC per GBTC share


@st.cache_data(ttl=3600)
def fetch_market_data() -> Dict[str, pd.DataFrame]:
    """Download Bitcoin and related market data."""

    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=365 * 5)

    symbols = {
        "BTC": ["BTC-USD"],
        "BTC_FUT": ["BTC=F"],
        "ETH": ["ETH-USD"],
        "NASDAQ": ["^NDX"],
        "GOLD": ["GC=F"],
        "OIL": ["CL=F"],
        "TNX": ["^TNX"],
        "DXY": ["DX-Y.NYB", "DX=F", "^DXY"],
        "GBTC": ["GBTC"],
        "MSTR": ["MSTR"],
        "RIOT": ["RIOT"],
        "MARA": ["MARA"],
        "BLOK": ["BLOK"],
        "HYG": ["HYG"],
        "VIX": ["^VIX"],
    }

    data_dict: Dict[str, pd.DataFrame] = {}

    for key, candidates in symbols.items():
        df = None
        for symbol in candidates:
            try:
                fetched = yf.download(
                    symbol,
                    start=start_date,
                    end=end_date,
                    interval="1d",
                    auto_adjust=False,
                    progress=False,
                    threads=False,
                )
                if fetched is not None and not fetched.empty:
                    df = fetched.copy()
                    break
            except Exception:
                continue

        if df is None or df.empty:
            data_dict[key] = pd.DataFrame()
        else:
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.droplevel(-1)
            data_dict[key] = df.dropna()

    return data_dict


def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calculate_ann_vol(series: pd.Series, window: int = 30) -> float:
    returns = series.pct_change().dropna()
    if returns.empty:
        return np.nan
    window_returns = returns.tail(window)
    if window_returns.empty:
        window_returns = returns
    return window_returns.std() * np.sqrt(365) * 100


def compute_metrics(data_dict: Dict[str, pd.DataFrame]) -> Dict[str, float]:
    btc = data_dict.get("BTC", pd.DataFrame())
    if btc.empty:
        raise ValueError("BTC 데이터를 불러오지 못했습니다.")

    close = btc["Close"].dropna()
    volume = btc.get("Volume", pd.Series(dtype="float64"))

    metrics: Dict[str, float] = {}

    metrics["price"] = close.iloc[-1]
    metrics["change_24h"] = ((close.iloc[-1] / close.iloc[-2]) - 1) * 100 if len(close) > 1 else np.nan
    metrics["change_7d"] = ((close.iloc[-1] / close.iloc[-7]) - 1) * 100 if len(close) > 7 else np.nan
    metrics["change_30d"] = ((close.iloc[-1] / close.iloc[-30]) - 1) * 100 if len(close) > 30 else np.nan
    metrics["change_90d"] = ((close.iloc[-1] / close.iloc[-90]) - 1) * 100 if len(close) > 90 else np.nan

    ytd_mask = close.index >= datetime(datetime.utcnow().year, 1, 1)
    if ytd_mask.any():
        metrics["return_ytd"] = ((close.iloc[-1] / close[ytd_mask].iloc[0]) - 1) * 100
    else:
        metrics["return_ytd"] = np.nan

    metrics["return_1y"] = ((close.iloc[-1] / close.iloc[-252]) - 1) * 100 if len(close) > 252 else np.nan
    metrics["ma_50"] = close.rolling(50).mean().iloc[-1] if len(close) >= 50 else np.nan
    metrics["ma_200"] = close.rolling(200).mean().iloc[-1] if len(close) >= 200 else np.nan
    metrics["ma_trend"] = metrics["ma_50"] - metrics["ma_200"]
    metrics["price_vs_ma50"] = ((metrics["price"] / metrics["ma_50"]) - 1) * 100 if metrics["ma_50"] else np.nan
    metrics["price_vs_ma200"] = ((metrics["price"] / metrics["ma_200"]) - 1) * 100 if metrics["ma_200"] else np.nan

    rsi_series = calculate_rsi(close)
    metrics["rsi14"] = rsi_series.iloc[-1] if not rsi_series.empty else np.nan
    metrics["volatility30"] = calculate_ann_vol(close)

    if not volume.empty:
        metrics["volume_avg30"] = volume.tail(30).mean()
        metrics["volume_change"] = ((volume.iloc[-1] / metrics["volume_avg30"]) - 1) * 100 if metrics["volume_avg30"] else np.nan
    else:
        metrics["volume_avg30"] = np.nan
        metrics["volume_change"] = np.nan

    recent = close.tail(30)
    metrics["support_30"] = recent.min()
    metrics["resistance_30"] = recent.max()

    nasdaq = data_dict.get("NASDAQ", pd.DataFrame())
    if not nasdaq.empty:
        btc_returns = close.pct_change().dropna()
        ndx_returns = nasdaq["Close"].pct_change().dropna()
        combined = pd.concat([btc_returns, ndx_returns], axis=1, join="inner").dropna()
        combined.columns = ["BTC", "NDX"]
        rolling_corr = combined["BTC"].rolling(30).corr(combined["NDX"])
        metrics["corr_ndx_30d"] = rolling_corr.iloc[-1] if not rolling_corr.empty else np.nan
    else:
        metrics["corr_ndx_30d"] = np.nan

    eth = data_dict.get("ETH", pd.DataFrame())
    if not eth.empty:
        ratio = (close / eth["Close"]).dropna()
        metrics["eth_btc_ratio"] = ratio.iloc[-1]
        metrics["eth_btc_trend"] = ((ratio.iloc[-1] / ratio.iloc[-30]) - 1) * 100 if len(ratio) > 30 else np.nan
    else:
        metrics["eth_btc_ratio"] = np.nan
        metrics["eth_btc_trend"] = np.nan

    dxy = data_dict.get("DXY", pd.DataFrame())
    metrics["dxy_trend"] = dxy["Close"].pct_change(30).iloc[-1] * 100 if not dxy.empty and len(dxy) > 30 else np.nan
    metrics["dxy_level"] = dxy["Close"].iloc[-1] if not dxy.empty else np.nan

    tnx = data_dict.get("TNX", pd.DataFrame())
    metrics["tnx_level"] = tnx["Close"].iloc[-1] / 100 if not tnx.empty else np.nan
    metrics["tnx_trend_30d"] = tnx["Close"].pct_change(30).iloc[-1] * 100 if not tnx.empty and len(tnx) > 30 else np.nan

    btc_fut = data_dict.get("BTC_FUT", pd.DataFrame())
    if not btc_fut.empty:
        fut_close = btc_fut["Close"].dropna()
        metrics["futures_basis_pct"] = ((fut_close.iloc[-1] / metrics["price"]) - 1) * 100 if not fut_close.empty else np.nan
        metrics["futures_change_7d"] = ((fut_close.iloc[-1] / fut_close.iloc[-7]) - 1) * 100 if len(fut_close) > 7 else np.nan
        metrics["futures_change_30d"] = ((fut_close.iloc[-1] / fut_close.iloc[-30]) - 1) * 100 if len(fut_close) > 30 else np.nan
    else:
        metrics["futures_basis_pct"] = np.nan
        metrics["futures_change_7d"] = np.nan
        metrics["futures_change_30d"] = np.nan

    gbtc = data_dict.get("GBTC", pd.DataFrame())
    if not gbtc.empty:
        gbtc_close = gbtc["Close"].dropna()
        if not gbtc_close.empty and metrics["price"]:
            metrics["gbtc_premium_pct"] = (
                (gbtc_close.iloc[-1] / (metrics["price"] * GBTC_BTC_PER_SHARE)) - 1
            ) * 100
        else:
            metrics["gbtc_premium_pct"] = np.nan
        metrics["gbtc_change_7d"] = ((gbtc_close.iloc[-1] / gbtc_close.iloc[-7]) - 1) * 100 if len(gbtc_close) > 7 else np.nan
        metrics["gbtc_change_30d"] = ((gbtc_close.iloc[-1] / gbtc_close.iloc[-30]) - 1) * 100 if len(gbtc_close) > 30 else np.nan
    else:
        metrics["gbtc_premium_pct"] = np.nan
        metrics["gbtc_change_7d"] = np.nan
        metrics["gbtc_change_30d"] = np.nan

    miner_keys = ["MSTR", "RIOT", "MARA"]
    miner_returns_7d = []
    miner_returns_30d = []
    for key in miner_keys:
        miner_df = data_dict.get(key, pd.DataFrame())
        if miner_df.empty:
            continue
        miner_close = miner_df["Close"].dropna()
        if len(miner_close) > 7:
            miner_returns_7d.append((miner_close.iloc[-1] / miner_close.iloc[-7] - 1) * 100)
        if len(miner_close) > 30:
            miner_returns_30d.append((miner_close.iloc[-1] / miner_close.iloc[-30] - 1) * 100)

    metrics["miners_change_7d"] = float(np.nanmean(miner_returns_7d)) if miner_returns_7d else np.nan
    metrics["miners_change_30d"] = float(np.nanmean(miner_returns_30d)) if miner_returns_30d else np.nan

    blok = data_dict.get("BLOK", pd.DataFrame())
    if not blok.empty:
        blok_close = blok["Close"].dropna()
        metrics["blok_change_30d"] = ((blok_close.iloc[-1] / blok_close.iloc[-30]) - 1) * 100 if len(blok_close) > 30 else np.nan
    else:
        metrics["blok_change_30d"] = np.nan

    hyg = data_dict.get("HYG", pd.DataFrame())
    if not hyg.empty:
        hyg_close = hyg["Close"].dropna()
        metrics["hyg_change_30d"] = ((hyg_close.iloc[-1] / hyg_close.iloc[-30]) - 1) * 100 if len(hyg_close) > 30 else np.nan
        metrics["hyg_yield_proxy"] = hyg["Close"].iloc[-1]
    else:
        metrics["hyg_change_30d"] = np.nan
        metrics["hyg_yield_proxy"] = np.nan

    vix = data_dict.get("VIX", pd.DataFrame())
    if not vix.empty:
        vix_close = vix["Close"].dropna()
        metrics["vix_level"] = vix_close.iloc[-1]
        metrics["vix_change_30d"] = ((vix_close.iloc[-1] / vix_close.iloc[-30]) - 1) * 100 if len(vix_close) > 30 else np.nan
    else:
        metrics["vix_level"] = np.nan
        metrics["vix_change_30d"] = np.nan

    gold = data_dict.get("GOLD", pd.DataFrame())
    if not gold.empty:
        gold_close = gold["Close"].dropna()
        metrics["gold_change_30d"] = ((gold_close.iloc[-1] / gold_close.iloc[-30]) - 1) * 100 if len(gold_close) > 30 else np.nan
    else:
        metrics["gold_change_30d"] = np.nan

    oil = data_dict.get("OIL", pd.DataFrame())
    if not oil.empty:
        oil_close = oil["Close"].dropna()
        metrics["oil_change_30d"] = ((oil_close.iloc[-1] / oil_close.iloc[-30]) - 1) * 100 if len(oil_close) > 30 else np.nan
    else:
        metrics["oil_change_30d"] = np.nan

    metrics["last_updated"] = close.index[-1]

    return metrics


def format_pct(value: float) -> str:
    if value is None or pd.isna(value):
        return "N/A"
    return f"{value:+.2f}%"


def create_price_chart(df: pd.DataFrame, period_days: int) -> go.Figure:
    cutoff = datetime.utcnow() - timedelta(days=period_days)
    filtered = df[df.index >= cutoff]
    if filtered.empty:
        filtered = df

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=filtered.index,
            y=filtered["Close"],
            name="Bitcoin",
            mode="lines",
            line=dict(color="#f7931a", width=2),
        )
    )

    for window, color, dash in [(20, "#7f8c8d", "dash"), (50, "#ffb347", "dash"), (200, "#6a5acd", "dot")]:
        if len(filtered) >= window:
            ma = filtered["Close"].rolling(window).mean()
            fig.add_trace(
                go.Scatter(
                    x=filtered.index,
                    y=ma,
                    name=f"{window}일 MA",
                    line=dict(color=color, dash=dash),
                )
            )

    fig.update_layout(
        height=420,
        template="plotly_white",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis_title="날짜",
        yaxis_title="가격 (USD)",
        margin=dict(l=10, r=10, t=40, b=40),
    )
    return fig


def create_volume_rsi_chart(df: pd.DataFrame, period_days: int) -> go.Figure:
    cutoff = datetime.utcnow() - timedelta(days=period_days)
    filtered = df[df.index >= cutoff]
    if filtered.empty:
        filtered = df

    volume = filtered.get("Volume", pd.Series(dtype="float64"))
    rsi = calculate_rsi(filtered["Close"]).dropna()

    fig = go.Figure()
    if not volume.empty:
        fig.add_trace(
            go.Bar(
                x=volume.index,
                y=volume,
                name="거래량",
                marker_color="#8e44ad",
                opacity=0.35,
                yaxis="y",
            )
        )

    fig.add_trace(
        go.Scatter(
            x=rsi.index,
            y=rsi,
            name="RSI(14)",
            line=dict(color="#2ecc71", width=2),
            yaxis="y2",
        )
    )

    fig.add_hline(y=70, line=dict(color="#e74c3c", dash="dash"), yref="y2")
    fig.add_hline(y=30, line=dict(color="#3498db", dash="dash"), yref="y2")

    fig.update_layout(
        height=360,
        template="plotly_white",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        yaxis=dict(title="거래량", side="left"),
        yaxis2=dict(title="RSI", side="right", overlaying="y", range=[0, 100]),
        margin=dict(l=10, r=10, t=40, b=40),
    )
    return fig


def build_commentary(metrics: Dict[str, float]) -> Dict[str, str]:
    ma_state = "골든크로스" if metrics["ma_trend"] > 0 else "데드크로스" if metrics["ma_trend"] < 0 else "중립"
    if metrics["rsi14"] >= 70:
        rsi_state = "과매수"
    elif metrics["rsi14"] <= 30:
        rsi_state = "과매도"
    else:
        rsi_state = "중립"

    if metrics["volatility30"] >= 90:
        vol_state = "극심한 변동성"
    elif metrics["volatility30"] >= 60:
        vol_state = "높은 변동성"
    elif metrics["volatility30"] <= 30:
        vol_state = "낮은 변동성"
    else:
        vol_state = "중간 수준 변동성"

    volume_state = "증가" if metrics["volume_change"] >= 20 else "감소" if metrics["volume_change"] <= -20 else "안정"

    if metrics["corr_ndx_30d"] >= 0.5:
        corr_state = "높은 동조화"
    elif metrics["corr_ndx_30d"] <= 0:
        corr_state = "역행 또는 비상관"
    else:
        corr_state = "중간 수준의 동조화"

    basis = metrics.get("futures_basis_pct", np.nan)
    if basis > 3:
        basis_state = "강한 콘탱고(선물 고평가)"
    elif basis < -1:
        basis_state = "백워데이션(선물 저평가)"
    else:
        basis_state = "중립적인 선물 베이시스"

    gbtc_premium = metrics.get("gbtc_premium_pct", np.nan)
    if gbtc_premium > 0:
        gbtc_state = "프리미엄"  # trading above spot
    else:
        gbtc_state = "할인"

    miners_30d = metrics.get("miners_change_30d", np.nan)
    if miners_30d > 10:
        miner_state = "채굴주가 강하게 동반 상승"
    elif miners_30d < -10:
        miner_state = "채굴주가 크게 약세"
    else:
        miner_state = "채굴주가 완만한 움직임"

    vix_level = metrics.get("vix_level", np.nan)
    if vix_level >= 25:
        risk_state = "높은 공포 국면"
    elif vix_level <= 15:
        risk_state = "낮은 변동성 환경"
    else:
        risk_state = "중간 수준의 변동성"

    return {
        "ma": f"현재 {ma_state} 구조이며, 가격은 50일선 대비 {format_pct(metrics['price_vs_ma50'])}, 200일선 대비 {format_pct(metrics['price_vs_ma200'])} 위치입니다.",
        "rsi": f"RSI(14)은 {metrics['rsi14']:.1f}로 {rsi_state} 구간입니다.",
        "volatility": f"30일 연율화 변동성은 {format_pct(metrics['volatility30'])}로 {vol_state} 입니다.",
        "volume": f"30일 평균 대비 거래량은 {format_pct(metrics['volume_change'])} 변화하여 {volume_state} 흐름입니다.",
        "levels": f"주요 지지/저항은 각각 {metrics['support_30']:,.0f} / {metrics['resistance_30']:,.0f} 달러입니다.",
        "correlation": f"최근 30일 나스닥과의 상관계수는 {metrics['corr_ndx_30d']:.2f}로 {corr_state}입니다.",
        "macro": (
            f"달러지수는 {metrics['dxy_level']:.2f}로 30일 변동률 {format_pct(metrics['dxy_trend'])}, 미 10년 금리는 {metrics['tnx_level']:.2f}% (30일 {format_pct(metrics['tnx_trend_30d'])})."
            if not pd.isna(metrics["dxy_level"]) and not pd.isna(metrics["tnx_level"])
            else "거시 지표 데이터를 충분히 확보하지 못했습니다."
        ),
        "eth_ratio": f"ETH/BTC 비율은 {metrics['eth_btc_ratio']:.4f}이며 30일 변동률은 {format_pct(metrics['eth_btc_trend'])} 입니다."
        if not pd.isna(metrics["eth_btc_ratio"])
        else "ETH/BTC 비율 정보를 불러오지 못했습니다.",
        "derivatives": (
            f"선물 베이시스는 {format_pct(metrics['futures_basis_pct'])}로 {basis_state}, GBTC는 {format_pct(metrics['gbtc_premium_pct'])} {gbtc_state} 상태입니다."
            if not pd.isna(metrics["futures_basis_pct"])
            else "선물/ETF 지표를 확보하지 못했습니다."
        ),
        "miners": (
            f"대표 채굴주 30일 평균 수익률은 {format_pct(metrics['miners_change_30d'])}로 {miner_state}입니다."
            if not pd.isna(metrics["miners_change_30d"])
            else "채굴주 데이터를 확보하지 못했습니다."
        ),
        "risk": (
            f"VIX {metrics['vix_level']:.1f} ({format_pct(metrics['vix_change_30d'])}), HYG 30일 변동률 {format_pct(metrics['hyg_change_30d'])}로 {risk_state} 환경입니다."
            if not pd.isna(metrics["vix_level"]) and not pd.isna(metrics["hyg_change_30d"])
            else "위험심리 보조지표를 확보하지 못했습니다."
        ),
    }


def generate_outlook(metrics: Dict[str, float], views: Dict[str, str]) -> Dict[str, str]:
    """Synthesize a deterministic outlook based on indicator heuristics."""

    short_parts = []
    if not pd.isna(metrics.get("price_vs_ma50")):
        if metrics["price_vs_ma50"] > 7:
            short_parts.append("가격이 50일선 위로 크게 이탈해 단기 상승세가 강하지만 과열 신호도 관찰됩니다.")
        elif metrics["price_vs_ma50"] < -5:
            short_parts.append("가격이 50일선을 크게 하회해 단기 조정 국면입니다.")
        else:
            short_parts.append("가격이 50일선 주변에서 등락하며 단기 중립 구간입니다.")

    if not pd.isna(metrics.get("rsi14")):
        if metrics["rsi14"] >= 70:
            short_parts.append("RSI가 과매수권(70 상회)에 진입해 단기 조정 리스크가 높습니다.")
        elif metrics["rsi14"] <= 30:
            short_parts.append("RSI가 과매도권(30 이하)에 위치해 기술적 반등 여지가 있습니다.")
        else:
            short_parts.append("RSI는 중립권으로 모멘텀이 균형을 이루고 있습니다.")

    if not pd.isna(metrics.get("change_7d")):
        change7 = metrics["change_7d"]
        if change7 > 5:
            short_parts.append("최근 1주일 동안 두 자릿수에 가까운 상승률로 강한 모멘텀이 형성되었습니다.")
        elif change7 < -5:
            short_parts.append("최근 1주일 동안 뚜렷한 하락 압력이 나타났습니다.")
    short_parts.append(f"단기 지지/저항: {metrics['support_30']:,.0f} / {metrics['resistance_30']:,.0f} 달러.")
    short_term = " ".join(short_parts)

    mid_parts = []
    if not pd.isna(metrics.get("price_vs_ma200")) and not pd.isna(metrics.get("ma_trend")):
        if metrics["price_vs_ma200"] > 0 and metrics["ma_trend"] > 0:
            mid_parts.append("중기적으로 200일선 위에서 우상향 추세가 이어지고 있습니다.")
        elif metrics["price_vs_ma200"] < 0 and metrics["ma_trend"] < 0:
            mid_parts.append("중기 추세선이 하향하며 약세 싸이클이 진행 중입니다.")
        else:
            mid_parts.append("200일선 부근에서 추세 전환을 모색하는 구간입니다.")

    if not pd.isna(metrics.get("change_90d")):
        change90 = metrics["change_90d"]
        if change90 > 15:
            mid_parts.append("분기 누적으로는 15% 이상 상승해 중기 모멘텀이 양호합니다.")
        elif change90 < -10:
            mid_parts.append("최근 분기 수익률이 -10% 이하로 둔화되며 경계가 필요합니다.")

    if not pd.isna(metrics.get("miners_change_30d")):
        if metrics["miners_change_30d"] > 0:
            mid_parts.append("채굴주가 평균적으로 플러스 수익률을 기록해 시장 신뢰를 뒷받침합니다.")
        else:
            mid_parts.append("채굴주 성과가 부진해 투자심리가 제한될 수 있습니다.")
    mid_term = " ".join(mid_parts)

    derivatives_parts = [views["derivatives"]]
    if not pd.isna(metrics.get("futures_basis_pct")):
        if metrics["futures_basis_pct"] >= 5:
            derivatives_parts.append("과도한 콘탱고는 레버리지 롱의 청산 리스크를 수반합니다.")
        elif metrics["futures_basis_pct"] <= -2:
            derivatives_parts.append("백워데이션은 현물 수요 약화를 시사하므로 방어적 포지션이 요구됩니다.")
    if not pd.isna(metrics.get("gbtc_premium_pct")) and metrics["gbtc_premium_pct"] > 5:
        derivatives_parts.append("GBTC 프리미엄 확대로 ETF 관련 자금 유입이 강하다는 신호입니다.")
    elif not pd.isna(metrics.get("gbtc_premium_pct")) and metrics["gbtc_premium_pct"] < -5:
        derivatives_parts.append("GBTC 할인 폭이 커져 기관 투자자의 수요가 둔화되어 보일 수 있습니다.")
    derivatives_view = " ".join(derivatives_parts)

    macro_parts = [views["macro"], views["risk"]]
    if not pd.isna(metrics.get("dxy_trend")) and metrics["dxy_trend"] > 1:
        macro_parts.append("달러 강세가 이어져 글로벌 유동성 축소에 주의해야 합니다.")
    elif not pd.isna(metrics.get("dxy_trend")) and metrics["dxy_trend"] < -1:
        macro_parts.append("달러 약세가 위험자산 선호를 지지합니다.")
    if not pd.isna(metrics.get("gold_change_30d")) and metrics["gold_change_30d"] > 5:
        macro_parts.append("금 가격 상승은 안전자산 선호 강화를 시사해 변동성 확대에 대비해야 합니다.")
    if not pd.isna(metrics.get("oil_change_30d")) and metrics["oil_change_30d"] > 10:
        macro_parts.append("유가 급등은 인플레이션 재자극 가능성을 높입니다.")
    macro_view = " ".join(macro_parts)

    watch_parts = [
        "주요 관전 포인트:",
        f"- 기술: {views['ma']}",
        f"- 파생상품: {views['derivatives']}",
        f"- 위험선호: {views['risk']}",
    ]

    watch_parts.append(
        "- 이벤트: 연준 의사록, CPI, 주요 ETF 자금 흐름, 채굴 난이도 조정 등을 모니터링하세요."
    )

    return {
        "short_term": short_term,
        "mid_term": mid_term,
        "derivatives": derivatives_view,
        "macro": macro_view,
        "watchlist": "\n".join(watch_parts),
    }


def main():
    st.set_page_config(page_title="비트코인 전망 분석", page_icon="🪙", layout="wide")
    st.title("🪙 비트코인 단·중기 전망")
    st.caption("비트코인 핵심 지표와 규칙 기반 해석을 제공하는 종합 전망 페이지")

    with st.spinner("시장 데이터를 수집하는 중..."):
        data_dict = fetch_market_data()

    try:
        metrics = compute_metrics(data_dict)
    except ValueError as error:
        st.error(str(error))
        return

    st.sidebar.header("차트 설정")
    period_label = st.sidebar.radio("차트 기간", ["1년", "3년", "5년"], index=0)
    period_days = {"1년": 365, "3년": 365 * 3, "5년": 365 * 5}[period_label]

    st.sidebar.markdown("---")
    st.sidebar.header("거시·파생 요약")
    st.sidebar.metric("선물 베이시스", format_pct(metrics['futures_basis_pct']))
    st.sidebar.metric("GBTC 프리/할인", format_pct(metrics['gbtc_premium_pct']))
    st.sidebar.metric("ETH/BTC", f"{metrics['eth_btc_ratio']:.4f}" if not pd.isna(metrics['eth_btc_ratio']) else "N/A", format_pct(metrics['eth_btc_trend']))
    st.sidebar.metric("VIX", f"{metrics['vix_level']:.1f}" if not pd.isna(metrics['vix_level']) else "N/A", format_pct(metrics['vix_change_30d']))
    st.sidebar.metric("DXY", f"{metrics['dxy_level']:.2f}" if not pd.isna(metrics['dxy_level']) else "N/A", format_pct(metrics['dxy_trend']))
    st.sidebar.metric("미 10년 금리", f"{metrics['tnx_level']:.2f}%" if not pd.isna(metrics['tnx_level']) else "N/A", format_pct(metrics['tnx_trend_30d']))

    st.subheader("📊 핵심 가격 지표")
    metric_cols = st.columns(4)
    metric_cols[0].metric("현재 가격", f"${metrics['price']:,.2f}", format_pct(metrics['change_24h']))
    metric_cols[1].metric("7일", format_pct(metrics['change_7d']))
    metric_cols[2].metric("30일", format_pct(metrics['change_30d']))
    metric_cols[3].metric("90일", format_pct(metrics['change_90d']))

    metric_cols2 = st.columns(4)
    metric_cols2[0].metric("연초 이후", format_pct(metrics['return_ytd']))
    metric_cols2[1].metric("연간", format_pct(metrics['return_1y']))
    metric_cols2[2].metric("RSI(14)", f"{metrics['rsi14']:.1f}" if not pd.isna(metrics['rsi14']) else "N/A")
    metric_cols2[3].metric("30일 변동성", format_pct(metrics['volatility30']))

    st.subheader("📌 추가 지표 스냅샷")
    extra_cols1 = st.columns(4)
    extra_cols1[0].metric("선물 베이시스", format_pct(metrics['futures_basis_pct']), format_pct(metrics['futures_change_7d']))
    extra_cols1[1].metric("GBTC 프리/할인", format_pct(metrics['gbtc_premium_pct']), format_pct(metrics['gbtc_change_7d']))
    extra_cols1[2].metric("채굴주 30일", format_pct(metrics['miners_change_30d']), format_pct(metrics['miners_change_7d']))
    extra_cols1[3].metric("BLOK 30일", format_pct(metrics['blok_change_30d']))

    extra_cols2 = st.columns(4)
    extra_cols2[0].metric("VIX", f"{metrics['vix_level']:.1f}" if not pd.isna(metrics['vix_level']) else "N/A", format_pct(metrics['vix_change_30d']))
    extra_cols2[1].metric("HYG 30일", format_pct(metrics['hyg_change_30d']))
    extra_cols2[2].metric("달러지수 30일", format_pct(metrics['dxy_trend']))
    extra_cols2[3].metric("미 10년 금리", f"{metrics['tnx_level']:.2f}%" if not pd.isna(metrics['tnx_level']) else "N/A", format_pct(metrics['tnx_trend_30d']))

    extra_cols3 = st.columns(3)
    extra_cols3[0].metric("금 30일", format_pct(metrics['gold_change_30d']))
    extra_cols3[1].metric("유가 30일", format_pct(metrics['oil_change_30d']))
    extra_cols3[2].metric("ETH/BTC 30일", format_pct(metrics['eth_btc_trend']))

    st.markdown("---")

    price_col, secondary_col = st.columns([2.3, 1.7])
    btc_df = data_dict["BTC"]

    with price_col:
        st.plotly_chart(create_price_chart(btc_df, period_days), use_container_width=True)

    with secondary_col:
        st.plotly_chart(create_volume_rsi_chart(btc_df, period_days), use_container_width=True)

    st.markdown("---")

    st.subheader("🔍 지표 해석")
    views = build_commentary(metrics)
    view_cols = st.columns(2)
    with view_cols[0]:
        st.write(f"- **이동평균 구조**: {views['ma']}")
        st.write(f"- **RSI 진단**: {views['rsi']}")
        st.write(f"- **변동성 상황**: {views['volatility']}")
        st.write(f"- **거래량 흐름**: {views['volume']}")
        st.write(f"- **파생시장**: {views['derivatives']}")
    with view_cols[1]:
        st.write(f"- **지지/저항**: {views['levels']}")
        st.write(f"- **나스닥 상관관계**: {views['correlation']}")
        st.write(f"- **거시 환경**: {views['macro']}")
        st.write(f"- **ETH/BTC 비율**: {views['eth_ratio']}")
        st.write(f"- **위험심리**: {views['risk']}")

    st.markdown("---")

    st.subheader("🧭 종합 전망 (규칙 기반)")
    outlook = generate_outlook(metrics, views)
    st.markdown("**단기 (1~4주)**")
    st.write(outlook["short_term"])
    st.markdown("**중기 (1~6개월)**")
    st.write(outlook["mid_term"])
    st.markdown("**파생상품/흐름**")
    st.write(outlook["derivatives"])
    st.markdown("**거시·위험 선호**")
    st.write(outlook["macro"])
    st.markdown("**체크리스트**")
    st.markdown(outlook["watchlist"])

    st.markdown("---")

    with st.expander("📥 비트코인 데이터 (최근 60일)"):
        st.dataframe(btc_df.tail(60))

    st.caption(
        f"데이터 기준: {metrics['last_updated'].strftime('%Y-%m-%d %H:%M:%S')} UTC | 데이터 제공: Yahoo Finance"
    )


if __name__ == "__main__":
    main()

