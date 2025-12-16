"""
거시경제 지표 기반 자산배분 모니터링 대시보드
메인 Streamlit 앱
"""
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
from dotenv import load_dotenv

from config import (
    FRED_INDICATORS,
    INDICATOR_CATEGORIES,
    WEIGHTS
)
from indicator_descriptions import INDICATOR_DESCRIPTIONS
from data_collector import EconomicDataCollector
from indicator_analyzer import IndicatorAnalyzer
from asset_allocator import AssetAllocator
from utils import (
    format_percentage,
    format_number,
    get_score_color,
    get_market_sentiment
)
import yfinance as yf

# 환경변수 로드
load_dotenv()

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 페이지 설정
st.set_page_config(
    page_title="거시경제 자산배분 대시보드",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 세션 상태 초기화
if 'data_loaded' not in st.session_state:
    st.session_state.data_loaded = False
if 'indicator_data' not in st.session_state:
    st.session_state.indicator_data = None
if 'scores' not in st.session_state:
    st.session_state.scores = None
if 'allocation' not in st.session_state:
    st.session_state.allocation = None


def load_data(api_key: str, use_cache: bool = True) -> Dict[str, Any]:
    """데이터 로드"""
    collector = EconomicDataCollector(api_key)
    return collector.fetch_all_indicators(use_cache=use_cache)


def analyze_data(indicator_data: Dict[str, Any]) -> Dict[str, Any]:
    """데이터 분석 및 점수화"""
    analyzer = IndicatorAnalyzer()
    return analyzer.get_overall_score(indicator_data)


def calculate_allocation(overall_score: float) -> Dict[str, Any]:
    """자산배분 계산"""
    allocator = AssetAllocator()
    return allocator.get_allocation_recommendation(overall_score)


def calculate_historical_overall_scores(indicator_data: Dict[str, Any], days: int = 1825) -> pd.DataFrame:
    """
    과거 종합점수 계산 (5년 추이)
    
    Args:
        indicator_data: 지표 데이터 딕셔너리
        days: 계산할 일수 (기본 1825일 = 5년)
        
    Returns:
        날짜와 종합점수가 포함된 DataFrame
    """
    import numpy as np
    
    try:
        analyzer = IndicatorAnalyzer()
        
        # 모든 지표의 시계열 데이터 수집
        all_series = {}
        for indicator_id, data in indicator_data.items():
            if data is None or not isinstance(data, dict):
                continue
            
            series = data.get('series')
            if series is not None and isinstance(series, pd.Series) and len(series) > 0:
                # 인덱스를 datetime으로 변환
                try:
                    if not pd.api.types.is_datetime64_any_dtype(series.index):
                        series.index = pd.to_datetime(series.index)
                    all_series[indicator_id] = series
                except Exception as e:
                    logger.warning(f"지표 {indicator_id}의 날짜 변환 실패: {e}")
                    continue
        
        if not all_series:
            return pd.DataFrame(columns=['date', 'overall_score'])
        
        # 실제 데이터가 있는 날짜만 사용 (모든 지표의 공통 날짜가 아닌, 각 지표의 실제 데이터 날짜)
        # 각 지표의 실제 데이터 포인트를 기준으로 계산
        all_data_dates = set()
        for series in all_series.values():
            try:
                all_data_dates.update(series.index)
            except Exception as e:
                logger.warning(f"날짜 수집 실패: {e}")
                continue
        
        if not all_data_dates:
            return pd.DataFrame(columns=['date', 'overall_score'])
        
        # 날짜를 datetime으로 변환하고 정렬
        try:
            all_data_dates = sorted([pd.to_datetime(d) for d in all_data_dates])
        except Exception as e:
            logger.warning(f"날짜 정렬 실패: {e}")
            return pd.DataFrame(columns=['date', 'overall_score'])
        
        if len(all_data_dates) < 2:
            return pd.DataFrame(columns=['date', 'overall_score'])
        
        # 최근 N일만 사용
        try:
            cutoff_date = all_data_dates[-1] - timedelta(days=days)
            valid_dates = [d for d in all_data_dates if d >= cutoff_date]
        except Exception as e:
            logger.warning(f"날짜 필터링 실패: {e}")
            return pd.DataFrame(columns=['date', 'overall_score'])
        
        if len(valid_dates) < 2:
            return pd.DataFrame(columns=['date', 'overall_score'])
        
        # 주간 샘플링 (매주 계산하여 성능 향상)
        # 하지만 실제 데이터 포인트를 우선 사용
        # 5년 데이터이므로 더 많은 포인트 사용 (최대 260개 = 5년 * 52주)
        weekly_dates = []
        step = max(1, len(valid_dates) // 260)  # 최대 260개 포인트
        for i in range(0, len(valid_dates), step):
            weekly_dates.append(valid_dates[i])
        
        # 마지막 날짜는 항상 포함
        if valid_dates[-1] not in weekly_dates:
            weekly_dates.append(valid_dates[-1])
        
        historical_scores = []
        debug_info = []  # 디버깅용
        
        for date in weekly_dates:
            # 해당 날짜의 지표 값들 추출
            date_indicator_data = {}
            date_debug = {'date': date, 'indicators': {}}
            
            for indicator_id, series in all_series.items():
                try:
                    # 해당 날짜 이하의 가장 가까운 값 찾기
                    # 월별 데이터인 경우 같은 월의 마지막 데이터를 사용
                    available_dates = series.index[series.index <= date]
                    if len(available_dates) == 0:
                        continue
                    
                    # 같은 월의 데이터가 있는지 확인 (월별 데이터의 경우)
                    same_month_dates = [d for d in available_dates if d.year == date.year and d.month == date.month]
                    if same_month_dates:
                        # 같은 월의 마지막 데이터 사용
                        closest_date = same_month_dates[-1]
                    else:
                        # 같은 월 데이터가 없으면 가장 가까운 이전 데이터 사용
                        closest_date = available_dates[-1]
                    
                    value = float(series.loc[closest_date])
                    
                    if pd.isna(value) or np.isnan(value):
                        continue
                    
                    indicator_debug = {
                        'used_date': closest_date,
                        'value': value
                    }
                    
                    # YoY 계산이 필요한 지표들
                    if indicator_id in ['CPIAUCSL', 'PPIACO', 'M2SL', 'PCEPILFE', 'INDPRO', 'WALCL']:
                        # 정확히 12개월 전 값 찾기 (같은 월의 같은 날짜 기준)
                        try:
                            # 12개월 전 날짜 계산
                            year_ago_date_target = date - pd.DateOffset(months=12)
                            # 해당 날짜 이하의 가장 가까운 값 찾기
                            year_ago_dates = series.index[series.index <= year_ago_date_target]
                            if len(year_ago_dates) > 0:
                                year_ago_date = year_ago_dates[-1]
                                year_ago_value = float(series.loc[year_ago_date])
                                if not pd.isna(year_ago_value) and not np.isnan(year_ago_value) and year_ago_value != 0:
                                    yoy = ((value - year_ago_value) / year_ago_value) * 100
                                    date_indicator_data[indicator_id] = {
                                        'latest_value': value,
                                        'yoy': yoy
                                    }
                                    indicator_debug['yoy'] = yoy
                                    indicator_debug['yoy_date'] = year_ago_date
                                    indicator_debug['yoy_value'] = year_ago_value
                                else:
                                    date_indicator_data[indicator_id] = {
                                        'latest_value': value,
                                        'yoy': None
                                    }
                            else:
                                date_indicator_data[indicator_id] = {
                                    'latest_value': value,
                                    'yoy': None
                                }
                        except Exception as e:
                            logger.debug(f"YoY 계산 실패 ({indicator_id}, {date}): {e}")
                            date_indicator_data[indicator_id] = {
                                'latest_value': value,
                                'yoy': None
                            }
                    else:
                        date_indicator_data[indicator_id] = {
                            'latest_value': value,
                            'yoy': None
                        }
                    
                    date_debug['indicators'][indicator_id] = indicator_debug
                except Exception as e:
                    logger.debug(f"지표 {indicator_id} 값 추출 실패 ({date}): {e}")
                    continue
            
            # 해당 날짜의 종합점수 계산
            if date_indicator_data:
                try:
                    scores = analyzer.get_overall_score(date_indicator_data)
                    overall_score = scores.get('overall_score', None)
                    if overall_score is not None and not pd.isna(overall_score) and not np.isnan(overall_score):
                        historical_scores.append({
                            'date': date,
                            'overall_score': float(overall_score)
                        })
                        date_debug['overall_score'] = float(overall_score)
                        debug_info.append(date_debug)
                except Exception as e:
                    logger.debug(f"날짜 {date}의 종합점수 계산 실패: {e}")
                    continue
        
        # 디버깅: 12월 5일과 12월 8일 비교
        dec5_debug = [d for d in debug_info if d['date'].month == 12 and d['date'].day == 5]
        dec8_debug = [d for d in debug_info if d['date'].month == 12 and d['date'].day == 8]
        
        if dec5_debug and dec8_debug:
            logger.info(f"12월 5일 종합점수: {dec5_debug[0].get('overall_score')}")
            logger.info(f"12월 8일 종합점수: {dec8_debug[0].get('overall_score')}")
            # 주요 지표 비교
            for indicator_id in ['CPIAUCSL', 'PPIACO', 'UNRATE', 'DFF', 'VIX']:
                if indicator_id in dec5_debug[0]['indicators'] and indicator_id in dec8_debug[0]['indicators']:
                    dec5_val = dec5_debug[0]['indicators'][indicator_id]
                    dec8_val = dec8_debug[0]['indicators'][indicator_id]
                    if dec5_val.get('value') != dec8_val.get('value') or dec5_val.get('yoy') != dec8_val.get('yoy'):
                        logger.info(f"{indicator_id} 차이 - 12/5: {dec5_val}, 12/8: {dec8_val}")
        
        if not historical_scores:
            return pd.DataFrame(columns=['date', 'overall_score'])
        
        df = pd.DataFrame(historical_scores)
        df = df.sort_values('date')
        return df
    
    except Exception as e:
        logger.error(f"과거 종합점수 계산 중 오류 발생: {e}", exc_info=True)
        return pd.DataFrame(columns=['date', 'overall_score'])


def fetch_sp500_data(start_date, end_date) -> Optional[pd.Series]:
    """S&P 500 데이터 가져오기"""
    try:
        # 날짜를 pd.Timestamp로 통일
        if isinstance(start_date, pd.Timestamp):
            start_ts = start_date
        elif isinstance(start_date, datetime):
            start_ts = pd.Timestamp(start_date)
        else:
            start_ts = pd.to_datetime(start_date)
        
        if isinstance(end_date, pd.Timestamp):
            end_ts = end_date
        elif isinstance(end_date, datetime):
            end_ts = pd.Timestamp(end_date)
        else:
            end_ts = pd.to_datetime(end_date)
        
        # yfinance는 date 객체를 받음
        start_date_obj = start_ts.date()
        end_date_obj = end_ts.date()
        
        logger.info(f"S&P 500 데이터 수집 시도: {start_date_obj} ~ {end_date_obj}")
        
        ticker = yf.Ticker('^GSPC')
        # period를 사용하여 더 안정적으로 가져오기
        hist = ticker.history(start=start_date_obj, end=end_date_obj, auto_adjust=True)
        
        if hist is None or len(hist) == 0:
            logger.warning("S&P 500 데이터가 없습니다.")
            return None
        
        logger.info(f"S&P 500 데이터 수집 성공: {len(hist)}개 포인트, 첫날: {hist.index[0]}, 마지막날: {hist.index[-1]}")
        
        # 종가 사용
        close_series = hist['Close']
        return close_series
    except Exception as e:
        logger.error(f"S&P 500 데이터 수집 실패: {e}", exc_info=True)
        import traceback
        logger.error(traceback.format_exc())
        return None


def convert_to_monthly_data(historical_scores: pd.DataFrame) -> pd.DataFrame:
    """
    종합점수 데이터를 월별 데이터로 변환
    
    Args:
        historical_scores: 일별/주별 종합점수 DataFrame (columns: 'date', 'overall_score')
        
    Returns:
        월별 종합점수 DataFrame (columns: '년월', '날짜', '종합점수')
    """
    if historical_scores.empty or len(historical_scores) == 0:
        return pd.DataFrame(columns=['년월', '날짜', '종합점수'])
    
    try:
        # 날짜를 datetime으로 변환
        historical_scores = historical_scores.copy()
        historical_scores['date'] = pd.to_datetime(historical_scores['date'])
        
        # 날짜로 정렬
        historical_scores = historical_scores.sort_values('date')
        
        # 년-월 컬럼 추가
        historical_scores['year_month'] = historical_scores['date'].dt.to_period('M')
        
        # 월별로 그룹화하여 각 월의 마지막 날짜의 값 사용
        monthly_data = historical_scores.groupby('year_month').agg({
            'date': 'last',
            'overall_score': 'last'
        }).reset_index()
        
        # 컬럼명 변경 및 포맷팅
        monthly_data['년월'] = monthly_data['year_month'].astype(str)
        monthly_data['날짜'] = monthly_data['date'].dt.strftime('%Y-%m-%d')
        monthly_data['종합점수'] = monthly_data['overall_score'].round(2)
        
        # 최종 컬럼만 선택
        result = monthly_data[['년월', '날짜', '종합점수']].copy()
        
        return result
    except Exception as e:
        logger.error(f"월별 데이터 변환 실패: {e}", exc_info=True)
        return pd.DataFrame(columns=['년월', '날짜', '종합점수'])


def convert_sp500_to_monthly(sp500_series: pd.Series) -> pd.DataFrame:
    """
    S&P 500 데이터를 월별 데이터로 변환
    
    Args:
        sp500_series: S&P 500 시계열 데이터 (인덱스가 날짜)
        
    Returns:
        월별 S&P 500 DataFrame (columns: '년월', '날짜', 'S&P500')
    """
    if sp500_series is None or len(sp500_series) == 0:
        return pd.DataFrame(columns=['년월', '날짜', 'S&P500'])
    
    try:
        # Series를 DataFrame으로 변환
        df = pd.DataFrame({'date': sp500_series.index, 'sp500': sp500_series.values})
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
        
        # 년-월 컬럼 추가
        df['year_month'] = df['date'].dt.to_period('M')
        
        # 월별로 그룹화하여 각 월의 마지막 날짜의 값 사용
        monthly_data = df.groupby('year_month').agg({
            'date': 'last',
            'sp500': 'last'
        }).reset_index()
        
        # 컬럼명 변경 및 포맷팅
        monthly_data['년월'] = monthly_data['year_month'].astype(str)
        monthly_data['날짜'] = monthly_data['date'].dt.strftime('%Y-%m-%d')
        monthly_data['S&P500'] = monthly_data['sp500'].round(2)
        
        # 최종 컬럼만 선택
        result = monthly_data[['년월', '날짜', 'S&P500']].copy()
        
        return result
    except Exception as e:
        logger.error(f"S&P 500 월별 데이터 변환 실패: {e}", exc_info=True)
        return pd.DataFrame(columns=['년월', '날짜', 'S&P500'])


def merge_monthly_data(monthly_scores: pd.DataFrame, monthly_sp500: pd.DataFrame) -> pd.DataFrame:
    """
    종합점수와 S&P 500 월별 데이터를 합치기
    
    Args:
        monthly_scores: 월별 종합점수 DataFrame
        monthly_sp500: 월별 S&P 500 DataFrame
        
    Returns:
        합쳐진 월별 데이터 DataFrame
    """
    try:
        if monthly_scores.empty and monthly_sp500.empty:
            return pd.DataFrame(columns=['년월', '날짜', '종합점수', 'S&P500'])
        
        # 날짜를 기준으로 병합
        merged = pd.merge(
            monthly_scores,
            monthly_sp500,
            on=['년월', '날짜'],
            how='outer',
            suffixes=('', '_sp500')
        )
        
        # 날짜로 정렬
        merged = merged.sort_values('날짜')
        
        # 중복된 날짜 컬럼 제거 (있는 경우)
        if '날짜_sp500' in merged.columns:
            merged = merged.drop('날짜_sp500', axis=1)
        
        return merged
    except Exception as e:
        logger.error(f"월별 데이터 병합 실패: {e}", exc_info=True)
        return pd.DataFrame(columns=['년월', '날짜', '종합점수', 'S&P500'])


def create_overall_score_trend_chart(historical_scores: pd.DataFrame) -> go.Figure:
    """종합점수 추이 차트 생성"""
    if historical_scores.empty or len(historical_scores) == 0:
        fig = go.Figure()
        fig.add_annotation(
            text="데이터가 부족하여 추이를 표시할 수 없습니다",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=16)
        )
        fig.update_layout(height=400)
        return fig
    
    fig = go.Figure()
    
    # 종합점수 라인
    fig.add_trace(go.Scatter(
        x=historical_scores['date'],
        y=historical_scores['overall_score'],
        mode='lines+markers',
        name='종합점수',
        line=dict(color='#1f77b4', width=3),
        marker=dict(size=6),
        hovertemplate='날짜: %{x}<br>종합점수: %{y:.1f}<extra></extra>'
    ))
    
    # 기준선 추가 (50점, 70점)
    fig.add_hline(y=70, line_dash="dash", line_color="green", 
                  annotation_text="양호 기준 (70점)", annotation_position="right")
    fig.add_hline(y=50, line_dash="dash", line_color="gray", 
                  annotation_text="중립 (50점)", annotation_position="right")
    fig.add_hline(y=40, line_dash="dash", line_color="red", 
                  annotation_text="주의 기준 (40점)", annotation_position="right")
    
    # 영역 색상 추가
    fig.add_hrect(y0=70, y1=100, fillcolor="green", opacity=0.1, layer="below", line_width=0)
    fig.add_hrect(y0=40, y1=70, fillcolor="yellow", opacity=0.1, layer="below", line_width=0)
    fig.add_hrect(y0=0, y1=40, fillcolor="red", opacity=0.1, layer="below", line_width=0)
    
    fig.update_layout(
        title="종합점수 5년 추이",
        xaxis_title="날짜",
        yaxis_title="종합점수",
        height=400,
        hovermode='x unified',
        showlegend=False,
        yaxis=dict(range=[0, 100])
    )
    
    return fig


def create_sp500_chart(start_date, end_date) -> Optional[go.Figure]:
    """S&P 500 차트 생성"""
    try:
        sp500_series = fetch_sp500_data(start_date, end_date)
        
        if sp500_series is None or len(sp500_series) == 0:
            return None
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=sp500_series.index,
            y=sp500_series.values,
            mode='lines',
            name='S&P 500',
            line=dict(color='#ff7f0e', width=2.5),
            hovertemplate='날짜: %{x|%Y-%m-%d}<br>S&P 500: %{y:,.0f}<extra></extra>'
        ))
        
        fig.update_layout(
            title="S&P 500 지수 5년 추이",
            xaxis_title="날짜",
            yaxis_title="S&P 500",
            height=300,
            hovermode='x unified',
            showlegend=False
        )
        
        return fig
    except Exception as e:
        logger.warning(f"S&P 500 차트 생성 실패: {e}")
        return None


def calculate_stock_allocation_signal(historical_scores: pd.DataFrame, start_date, end_date) -> Optional[pd.DataFrame]:
    """종합점수와 S&P 500 기반 주식 비중 확대/축소 시그널 계산"""
    try:
        from asset_allocator import AssetAllocator
        
        if historical_scores is None or historical_scores.empty or len(historical_scores) == 0:
            logger.warning("종합점수 데이터가 없어 시그널을 계산할 수 없습니다.")
            return None
        
        # S&P 500 데이터 가져오기
        logger.info(f"S&P 500 데이터 수집 시도: {start_date} ~ {end_date}")
        sp500_series = fetch_sp500_data(start_date, end_date)
        
        if sp500_series is None or len(sp500_series) == 0:
            logger.warning("S&P 500 데이터가 없어 시그널을 계산할 수 없습니다.")
            return None
        
        logger.info(f"S&P 500 데이터 수집 성공: {len(sp500_series)}개 포인트")
        
        allocator = AssetAllocator()
        signal_data = []
        
        # 이전 값 추적 (변화율 계산용)
        prev_stock_pct = None
        matched_count = 0
        skipped_count = 0
        
        for _, row in historical_scores.iterrows():
            try:
                date_val = row['date']
                score = row['overall_score']
                
                if pd.isna(score) or np.isnan(score):
                    skipped_count += 1
                    continue
                
                # 날짜를 pd.Timestamp로 변환
                if isinstance(date_val, pd.Timestamp):
                    date_ts = date_val.normalize()
                elif isinstance(date_val, datetime):
                    date_ts = pd.Timestamp(date_val).normalize()
                else:
                    date_ts = pd.to_datetime(date_val).normalize()
                
                # 종합점수 기반 주식 비중 계산
                allocation = allocator.calculate_allocation(float(score))
                stock_pct = allocation.get('stocks', 0)
                
                # 해당 날짜의 S&P 500 값 찾기 (더 유연한 매칭)
                # 먼저 정확히 일치하는 날짜 찾기
                if date_ts in sp500_series.index:
                    sp500_value = float(sp500_series.loc[date_ts])
                else:
                    # 해당 날짜 이하의 가장 가까운 값 찾기
                    available_dates = sp500_series.index[sp500_series.index <= date_ts]
                    if len(available_dates) == 0:
                        # 날짜가 너무 이전이면 최근 30일 이내의 데이터 허용
                        future_dates = sp500_series.index[sp500_series.index >= date_ts - timedelta(days=30)]
                        if len(future_dates) > 0:
                            closest_date = future_dates[0]
                            sp500_value = float(sp500_series.loc[closest_date])
                        else:
                            skipped_count += 1
                            continue
                    else:
                        closest_date = available_dates[-1]
                        sp500_value = float(sp500_series.loc[closest_date])
                
                if pd.isna(sp500_value) or np.isnan(sp500_value):
                    skipped_count += 1
                    continue
                
                # 시그널 계산
                signal = "중립"
                signal_value = 0
                
                # 주식 비중 변화
                if prev_stock_pct is not None:
                    stock_change = stock_pct - prev_stock_pct
                    
                    # 시그널 결정 로직
                    if stock_change > 2:  # 주식 비중이 2%p 이상 증가
                        signal = "확대"
                        signal_value = 1
                    elif stock_change < -2:  # 주식 비중이 2%p 이상 감소
                        signal = "축소"
                        signal_value = -1
                    elif stock_change > 0:
                        signal = "소폭 확대"
                        signal_value = 0.5
                    elif stock_change < 0:
                        signal = "소폭 축소"
                        signal_value = -0.5
                
                signal_data.append({
                    'date': date_ts,
                    'score': float(score),
                    'stock_pct': stock_pct,
                    'sp500': sp500_value,
                    'signal': signal,
                    'signal_value': signal_value
                })
                
                prev_stock_pct = stock_pct
                matched_count += 1
                
            except Exception as e:
                logger.debug(f"시그널 계산 실패 ({date_val}): {e}")
                skipped_count += 1
                continue
        
        logger.info(f"시그널 데이터 매칭 완료: 성공 {matched_count}개, 건너뜀 {skipped_count}개")
        
        if len(signal_data) < 2:
            logger.warning(f"주식 비중 시그널 데이터가 부족합니다. (데이터 포인트: {len(signal_data)}, 최소 2개 필요)")
            return None
        
        df = pd.DataFrame(signal_data)
        logger.info(f"주식 비중 시그널 데이터 생성 완료. (데이터 포인트: {len(df)})")
        return df
        
    except Exception as e:
        logger.error(f"주식 비중 시그널 계산 실패: {e}", exc_info=True)
        import traceback
        logger.error(traceback.format_exc())
        return None


def create_stock_signal_chart(signal_data: pd.DataFrame) -> Optional[go.Figure]:
    """주식 비중 확대/축소 시그널 차트 생성"""
    try:
        # 데이터 검증
        if signal_data is None or len(signal_data) == 0:
            logger.warning("시그널 차트 생성 실패: 데이터가 비어있습니다.")
            return None
        
        required_columns = ['date', 'stock_pct', 'score', 'sp500', 'signal_value']
        missing_columns = [col for col in required_columns if col not in signal_data.columns]
        if missing_columns:
            logger.error(f"시그널 차트 생성 실패: 필수 컬럼이 없습니다. ({missing_columns})")
            return None
        
        fig = go.Figure()
        
        # 주식 비중 라인
        fig.add_trace(go.Scatter(
            x=signal_data['date'],
            y=signal_data['stock_pct'],
            mode='lines+markers',
            name='주식 비중 (%)',
            line=dict(color='#1f77b4', width=2.5),
            marker=dict(size=6),
            hovertemplate='날짜: %{x|%Y-%m-%d}<br>주식 비중: %{y:.1f}%<br>종합점수: %{customdata:.1f}<extra></extra>',
            customdata=signal_data['score'],
            yaxis='y'
        ))
        
        # 시그널 포인트 (확대/축소)
        expand_data = signal_data[signal_data['signal_value'] > 0]
        reduce_data = signal_data[signal_data['signal_value'] < 0]
        
        if len(expand_data) > 0:
            fig.add_trace(go.Scatter(
                x=expand_data['date'],
                y=expand_data['stock_pct'],
                mode='markers',
                name='확대 시그널',
                marker=dict(
                    symbol='triangle-up',
                    size=12,
                    color='green',
                    line=dict(width=2, color='darkgreen')
                ),
                hovertemplate='날짜: %{x|%Y-%m-%d}<br>시그널: 확대<br>주식 비중: %{y:.1f}%<extra></extra>',
                yaxis='y'
            ))
        
        if len(reduce_data) > 0:
            fig.add_trace(go.Scatter(
                x=reduce_data['date'],
                y=reduce_data['stock_pct'],
                mode='markers',
                name='축소 시그널',
                marker=dict(
                    symbol='triangle-down',
                    size=12,
                    color='red',
                    line=dict(width=2, color='darkred')
                ),
                hovertemplate='날짜: %{x|%Y-%m-%d}<br>시그널: 축소<br>주식 비중: %{y:.1f}%<extra></extra>',
                yaxis='y'
            ))
        
        # S&P 500 (오른쪽 y축)
        fig.add_trace(go.Scatter(
            x=signal_data['date'],
            y=signal_data['sp500'],
            mode='lines',
            name='S&P 500',
            line=dict(color='#ff7f0e', width=2, dash='dot'),
            hovertemplate='날짜: %{x|%Y-%m-%d}<br>S&P 500: %{y:,.0f}<extra></extra>',
            yaxis='y2'
        ))
        
        fig.update_layout(
            title="주식 비중 확대/축소 시그널 추이 (종합점수 & S&P 500 기반)",
            xaxis_title="날짜",
            yaxis=dict(
                title="주식 비중 (%)",
                side='left',
                range=[0, 100],
                titlefont=dict(color='#1f77b4'),
                tickfont=dict(color='#1f77b4')
            ),
            yaxis2=dict(
                title="S&P 500",
                overlaying='y',
                side='right',
                showgrid=False,
                titlefont=dict(color='#ff7f0e'),
                tickfont=dict(color='#ff7f0e')
            ),
            height=400,
            hovermode='x unified',
            showlegend=True,
            legend=dict(
                yanchor="top",
                y=0.99,
                xanchor="left",
                x=0.01
            )
        )
        
        return fig
        
    except Exception as e:
        logger.error(f"시그널 차트 생성 실패: {e}", exc_info=True)
        return None


def calculate_correlation(historical_scores: pd.DataFrame, start_date, end_date) -> Optional[Dict[str, Any]]:
    """종합점수와 S&P 500의 상관관계 계산"""
    try:
        logger.info(f"상관관계 계산 시작: 종합점수 {len(historical_scores)}개 포인트")
        
        # S&P 500 데이터 가져오기
        sp500_series = fetch_sp500_data(start_date, end_date)
        
        if sp500_series is None or len(sp500_series) == 0:
            logger.warning("S&P 500 데이터가 없어 상관관계를 계산할 수 없습니다.")
            return None
        
        logger.info(f"S&P 500 데이터 수집됨: {len(sp500_series)}개 포인트")
        
        # 종합점수와 S&P 500을 같은 날짜로 매칭
        matched_data = []
        
        for _, row in historical_scores.iterrows():
            try:
                date_val = row['date']
                score = row['overall_score']
                
                # 날짜를 pd.Timestamp로 변환
                if isinstance(date_val, pd.Timestamp):
                    date_ts = date_val.normalize()
                elif isinstance(date_val, datetime):
                    date_ts = pd.Timestamp(date_val).normalize()
                else:
                    date_ts = pd.to_datetime(date_val).normalize()
                
                # 해당 날짜 이하의 가장 가까운 S&P 500 값 찾기
                available_dates = sp500_series.index[sp500_series.index <= date_ts]
                if len(available_dates) > 0:
                    closest_date = available_dates[-1]
                    sp500_value = float(sp500_series.loc[closest_date])
                    
                    if not pd.isna(score) and not np.isnan(score) and not pd.isna(sp500_value) and not np.isnan(sp500_value):
                        matched_data.append({
                            'date': date_ts,
                            'score': float(score),
                            'sp500': sp500_value
                        })
            except Exception as e:
                logger.debug(f"날짜 매칭 실패: {e}")
                continue
        
        logger.info(f"매칭된 데이터 포인트: {len(matched_data)}개")
        
        if len(matched_data) < 5:  # 최소 5개 데이터 포인트 필요
            logger.warning(f"매칭된 데이터가 부족합니다: {len(matched_data)}개 (최소 5개 필요)")
            return None
        
        # DataFrame 생성
        df = pd.DataFrame(matched_data)
        
        # 상관계수 계산
        correlation = df['score'].corr(df['sp500'])
        
        if pd.isna(correlation) or np.isnan(correlation):
            logger.warning("상관계수가 NaN입니다.")
            return None
        
        logger.info(f"상관계수 계산 완료: {correlation:.3f} ({len(df)}개 포인트)")
        
        return {
            'correlation': float(correlation),
            'data': df,
            'count': len(df)
        }
    except Exception as e:
        logger.error(f"상관관계 계산 실패: {e}", exc_info=True)
        import traceback
        logger.error(traceback.format_exc())
        return None


def create_correlation_chart(correlation_data: Dict[str, Any]) -> go.Figure:
    """상관관계 스캐터 플롯 생성"""
    df = correlation_data['data']
    correlation = correlation_data['correlation']
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=df['score'],
        y=df['sp500'],
        mode='markers',
        name='데이터 포인트',
        marker=dict(
            size=8,
            color=df['score'],
            colorscale='Viridis',
            showscale=True,
            colorbar=dict(title="종합점수")
        ),
        hovertemplate='종합점수: %{x:.1f}<br>S&P 500: %{y:,.0f}<extra></extra>',
        text=[d.strftime('%Y-%m-%d') for d in df['date']],
        textposition='top center'
    ))
    
    # 추세선 추가
    z = np.polyfit(df['score'], df['sp500'], 1)
    p = np.poly1d(z)
    x_trend = np.linspace(df['score'].min(), df['score'].max(), 100)
    y_trend = p(x_trend)
    
    fig.add_trace(go.Scatter(
        x=x_trend,
        y=y_trend,
        mode='lines',
        name='추세선',
        line=dict(color='red', width=2, dash='dash')
    ))
    
    # 상관계수 해석
    if abs(correlation) >= 0.7:
        strength = "강한"
    elif abs(correlation) >= 0.4:
        strength = "중간"
    else:
        strength = "약한"
    
    direction = "양의" if correlation > 0 else "음의"
    
    fig.update_layout(
        title=f"종합점수 vs S&P 500 상관관계 (상관계수: {correlation:.3f})",
        xaxis_title="종합점수",
        yaxis_title="S&P 500",
        height=400,
        hovermode='closest',
        showlegend=True,
        annotations=[
            dict(
                x=0.05,
                y=0.95,
                xref="paper",
                yref="paper",
                text=f"상관계수: {correlation:.3f}<br>{strength} {direction} 상관관계",
                showarrow=False,
                bgcolor="rgba(255,255,255,0.8)",
                bordercolor="black",
                borderwidth=1
            )
        ]
    )
    
    return fig


def create_gauge_chart(score: float, title: str) -> go.Figure:
    """게이지 차트 생성"""
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=score,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': title},
        delta={'reference': 50},
        gauge={
            'axis': {'range': [None, 100]},
            'bar': {'color': get_score_color(score)},
            'steps': [
                {'range': [0, 40], 'color': "lightgray"},
                {'range': [40, 70], 'color': "gray"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 90
            }
        }
    ))
    fig.update_layout(height=250)
    return fig


def create_pie_chart(allocation: Dict[str, float]) -> go.Figure:
    """파이 차트 생성"""
    colors = {
        'stocks': '#1f77b4',
        'bonds': '#2ca02c',
        'cash': '#ff7f0e',
        'real_estate': '#d62728'
    }
    
    labels = {
        'stocks': '주식',
        'bonds': '채권',
        'cash': '현금',
        'real_estate': '부동산'
    }
    
    fig = go.Figure(data=[go.Pie(
        labels=[labels.get(k, k) for k in allocation.keys()],
        values=list(allocation.values()),
        hole=0.4,
        marker_colors=[colors.get(k, '#gray') for k in allocation.keys()]
    )])
    
    fig.update_layout(
        title="추천 자산배분",
        height=400,
        showlegend=True
    )
    
    return fig


def create_time_series_chart(indicator_data: Dict[str, Any], indicators: list, period: str = '1Y') -> go.Figure:
    """시계열 차트 생성"""
    # 기간 설정
    days_map = {'1Y': 365, '3Y': 1095, '5Y': 1825}
    days = days_map.get(period, 365)
    
    # 실제 사용 가능한 지표만 필터링
    valid_indicators = []
    for ind in indicators:
        if ind in indicator_data and indicator_data[ind] is not None:
            data = indicator_data[ind]
            series = data.get('series')
            if series is not None and isinstance(series, pd.Series) and len(series) > 0:
                valid_indicators.append(ind)
    
    if not valid_indicators:
        # 빈 차트 반환
        fig = go.Figure()
        fig.add_annotation(text="표시할 데이터가 없습니다", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        return fig
    
    # 너무 많은 지표는 스크롤 가능하도록 높이 제한
    max_height = min(300 * len(valid_indicators), 3000)
    
    fig = make_subplots(
        rows=len(valid_indicators),
        cols=1,
        subplot_titles=[FRED_INDICATORS.get(ind, ind) for ind in valid_indicators],
        vertical_spacing=0.05 if len(valid_indicators) > 10 else 0.1
    )
    
    for idx, indicator_id in enumerate(valid_indicators):
        data = indicator_data[indicator_id]
        series = data.get('series')
        
        # 최근 N일 데이터만
        if len(series) > days:
            series = series.iloc[-days:]
        
        fig.add_trace(
            go.Scatter(
                x=series.index,
                y=series.values,
                mode='lines',
                name=FRED_INDICATORS.get(indicator_id, indicator_id),
                line=dict(width=2)
            ),
            row=idx+1,
            col=1
        )
    
    fig.update_layout(
        height=max_height,
        showlegend=False,
        title_text=f"모든 지표 추이 ({period}) - 총 {len(valid_indicators)}개"
    )
    
    return fig


def format_indicator_value(indicator_id: str, value: float) -> str:
    """지표 값 포맷팅"""
    # YoY 증가율을 표시하는 지표들 (퍼센트)
    if indicator_id in ['UNRATE', 'DFF', 'DFII10', 'T10Y2Y', 'T5YIE', 'BAMLH0A0HYM2', 'TCU']:
        return format_percentage(value)
    # YoY 증가율을 표시하는 인플레이션 지표들
    elif indicator_id in ['PCEPILFE', 'CPIAUCSL', 'PPIACO', 'INDPRO', 'M2SL']:
        # YoY 값이면 퍼센트로 표시
        return format_percentage(value)
    elif indicator_id == 'VIX':
        return f"{value:.2f}"
    elif indicator_id in ['UMCSENT']:
        return f"{value:.1f}"
    else:
        return format_number(value)


def get_indicator_status(score: Optional[float]) -> tuple[str, str]:
    """지표 상태 반환"""
    if score is None:
        return "데이터 없음", "⚪"
    
    if score >= 70:
        return "양호", "🟢"
    elif score >= 40:
        return "보통", "🟡"
    else:
        return "주의", "🔴"


# 사이드바
with st.sidebar:
    st.title("⚙️ 설정")
    
    # API 키 입력
    api_key = st.text_input(
        "FRED API 키",
        value=os.getenv("FRED_API_KEY", ""),
        type="password",
        help="https://fred.stlouisfed.org/docs/api/api_key.html"
    )
    
    use_cache = st.checkbox("캐시 사용", value=True)
    
    if st.button("🔄 데이터 새로고침", type="primary"):
        if api_key:
            with st.spinner("데이터를 수집하는 중..."):
                try:
                    indicator_data = load_data(api_key, use_cache=use_cache)
                    
                    # 수집된 지표 확인
                    collected_count = sum(1 for v in indicator_data.values() if v is not None)
                    total_count = len(indicator_data)
                    
                    if collected_count == 0:
                        st.error("❌ 데이터 수집 실패: 수집된 지표가 없습니다.")
                        st.info("💡 FRED API 키가 올바른지 확인하거나, 캐시를 비활성화하고 다시 시도하세요.")
                    else:
                        scores = analyze_data(indicator_data)
                        allocation_result = calculate_allocation(scores['overall_score'])
                        
                        st.session_state.indicator_data = indicator_data
                        st.session_state.scores = scores
                        st.session_state.allocation = allocation_result
                        st.session_state.data_loaded = True
                        
                        st.success(f"✅ 데이터 로드 완료! ({collected_count}/{total_count} 지표 수집됨)")
                        st.rerun()
                except Exception as e:
                    import traceback
                    st.error(f"❌ 데이터 로드 실패: {e}")
                    with st.expander("🔍 상세 에러 정보"):
                        st.code(traceback.format_exc())
        else:
            st.error("FRED API 키를 입력하세요.")
    
    st.divider()
    
    st.markdown("### 📚 정보")
    st.markdown("""
    이 대시보드는 거시경제 지표를 분석하여
    자산배분을 제안합니다.
    
    **데이터 출처:**
    - FRED (Federal Reserve Economic Data)
    - Yahoo Finance (VIX)
    """)


# 메인 대시보드
st.title("📊 거시경제 지표 기반 자산배분 모니터링 대시보드")

# 데이터가 로드되지 않은 경우
if not st.session_state.data_loaded or st.session_state.indicator_data is None:
    st.info("👈 사이드바에서 FRED API 키를 입력하고 '데이터 새로고침' 버튼을 클릭하세요.")
    
    # 예시 데이터 표시 (선택사항)
    st.markdown("### 사용 방법")
    st.markdown("""
    1. FRED API 키 발급: https://fred.stlouisfed.org/docs/api/api_key.html
    2. 사이드바에 API 키 입력
    3. '데이터 새로고침' 버튼 클릭
    4. 대시보드에서 실시간 분석 결과 확인
    """)
    
    st.stop()

# 데이터 로드 완료
indicator_data = st.session_state.indicator_data
scores = st.session_state.scores
allocation_result = st.session_state.allocation

# 마지막 업데이트 시간
st.caption(f"마지막 업데이트: {datetime.now().strftime('%Y-%m-%d %H:%M:%S KST')}")

# 종합 점수 섹션
st.header("📈 종합 점수")
overall_score = scores['overall_score']
sentiment, emoji = get_market_sentiment(overall_score)

col1, col2, col3 = st.columns([2, 2, 2])

with col1:
    st.plotly_chart(create_gauge_chart(overall_score, "종합 점수"), use_container_width=True)

with col2:
    st.metric(
        "종합 점수",
        f"{overall_score:.1f}/100",
        delta=f"{overall_score - 50:.1f}",
        delta_color="normal"
    )
    st.markdown(f"### {emoji} {sentiment}")

with col3:
    st.markdown("### 카테고리별 점수")
    for category, weight in WEIGHTS.items():
        score = scores.get(f'{category}_score')
        if score is not None:
            category_name = {
                'economy': '경기',
                'rates': '금리',
                'inflation': '인플레',
                'volatility': '변동성',
                'liquidity': '유동성'
            }.get(category, category)
            st.progress(score / 100, text=f"{category_name}({weight*100:.0f}%): {score:.1f}점")

# 종합점수 추이 차트
try:
    historical_scores = calculate_historical_overall_scores(indicator_data, days=1825)  # 5년 추이
    
    # 현재 종합점수를 그래프에 추가 (마지막 날짜로)
    if not historical_scores.empty and len(historical_scores) > 0:
        # 현재 날짜와 종합점수 추가
        current_date = datetime.now().date()
        current_row = pd.DataFrame({
            'date': [pd.Timestamp(current_date)],
            'overall_score': [overall_score]
        })
        
        # 기존 데이터와 합치기 (중복 제거)
        historical_scores = pd.concat([historical_scores, current_row], ignore_index=True)
        historical_scores = historical_scores.drop_duplicates(subset=['date'], keep='last')
        historical_scores = historical_scores.sort_values('date')
        
        st.plotly_chart(create_overall_score_trend_chart(historical_scores), use_container_width=True)
        
        # S&P 500 차트 및 상관관계 분석 (종합점수 추이 아래)
        try:
            start_date = pd.Timestamp(historical_scores['date'].min())
            end_date = pd.Timestamp(historical_scores['date'].max()) + timedelta(days=10)
            sp500_series = fetch_sp500_data(start_date, end_date)
            sp500_chart = create_sp500_chart(start_date, end_date)
            if sp500_chart is not None:
                st.plotly_chart(sp500_chart, use_container_width=True)
            
            # 월별 데이터 다운로드 버튼 (종합점수 + S&P 500)
            try:
                monthly_scores = convert_to_monthly_data(historical_scores)
                monthly_sp500 = convert_sp500_to_monthly(sp500_series) if sp500_series is not None and len(sp500_series) > 0 else pd.DataFrame()
                
                # 데이터 병합
                if not monthly_scores.empty or not monthly_sp500.empty:
                    merged_data = merge_monthly_data(monthly_scores, monthly_sp500)
                    
                    if not merged_data.empty and len(merged_data) > 0:
                        # CSV로 변환
                        csv_data = merged_data.to_csv(index=False, encoding='utf-8-sig')
                        
                        # 다운로드 버튼
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.download_button(
                                label="📥 종합점수 + S&P 500 (CSV)",
                                data=csv_data,
                                file_name=f"종합점수_S&P500_월별데이터_{datetime.now().strftime('%Y%m%d')}.csv",
                                mime="text/csv",
                                help="5년간의 월별 종합점수와 S&P 500 데이터를 CSV 파일로 다운로드합니다.",
                                use_container_width=True
                            )
                        with col2:
                            # 종합점수만 다운로드 버튼
                            if not monthly_scores.empty:
                                scores_csv = monthly_scores.to_csv(index=False, encoding='utf-8-sig')
                                st.download_button(
                                    label="📥 종합점수만 (CSV)",
                                    data=scores_csv,
                                    file_name=f"종합점수_월별데이터_{datetime.now().strftime('%Y%m%d')}.csv",
                                    mime="text/csv",
                                    help="5년간의 월별 종합점수 데이터만 CSV 파일로 다운로드합니다.",
                                    use_container_width=True
                                )
                        with col3:
                            # S&P 500만 다운로드 버튼
                            if not monthly_sp500.empty:
                                sp500_csv = monthly_sp500.to_csv(index=False, encoding='utf-8-sig')
                                st.download_button(
                                    label="📥 S&P 500만 (CSV)",
                                    data=sp500_csv,
                                    file_name=f"S&P500_월별데이터_{datetime.now().strftime('%Y%m%d')}.csv",
                                    mime="text/csv",
                                    help="5년간의 월별 S&P 500 데이터만 CSV 파일로 다운로드합니다.",
                                    use_container_width=True
                                )
                        
                        # 데이터 정보 표시
                        date_range = f"{merged_data['날짜'].min()} ~ {merged_data['날짜'].max()}"
                        score_count = merged_data['종합점수'].notna().sum()
                        sp500_count = merged_data['S&P500'].notna().sum()
                        st.caption(f"총 {len(merged_data)}개월 데이터 (기간: {date_range}) | 종합점수: {score_count}개월 | S&P 500: {sp500_count}개월")
                else:
                    # 종합점수만 있는 경우
                    if not monthly_scores.empty and len(monthly_scores) > 0:
                        csv_data = monthly_scores.to_csv(index=False, encoding='utf-8-sig')
                        st.download_button(
                            label="📥 종합점수 5년 월별 데이터 다운로드 (CSV)",
                            data=csv_data,
                            file_name=f"종합점수_월별데이터_{datetime.now().strftime('%Y%m%d')}.csv",
                            mime="text/csv",
                            help="5년간의 월별 종합점수 데이터를 CSV 파일로 다운로드합니다."
                        )
                        st.caption(f"총 {len(monthly_scores)}개월 데이터 (기간: {monthly_scores['날짜'].min()} ~ {monthly_scores['날짜'].max()})")
            except Exception as e:
                logger.error(f"월별 데이터 다운로드 준비 실패: {e}", exc_info=True)
            
            # 주식 비중 확대/축소 시그널 추이
            try:
                logger.info(f"주식 비중 시그널 계산 시작: 종합점수 {len(historical_scores)}개 포인트")
                signal_data = calculate_stock_allocation_signal(historical_scores, start_date, end_date)
                if signal_data is not None and len(signal_data) > 0:
                    logger.info(f"주식 비중 시그널 데이터 준비 완료: {len(signal_data)}개 포인트")
                    signal_chart = create_stock_signal_chart(signal_data)
                    if signal_chart is not None:
                        st.plotly_chart(signal_chart, use_container_width=True)
                    else:
                        logger.warning("주식 비중 시그널 차트 생성 실패: 차트 객체가 None입니다.")
                        st.warning("⚠️ 주식 비중 확대/축소 시그널 추이 그래프를 생성할 수 없습니다.")
                else:
                    data_count = len(signal_data) if signal_data is not None else 0
                    logger.warning(f"주식 비중 시그널 데이터가 부족합니다. (데이터 포인트: {data_count}, 종합점수 데이터: {len(historical_scores)})")
                    with st.expander("ℹ️ 주식 비중 확대/축소 시그널 추이 그래프 정보"):
                        st.info("주식 비중 확대/축소 시그널 추이 그래프를 표시하기에 데이터가 충분하지 않습니다.")
                        st.caption(f"종합점수 데이터: {len(historical_scores)}개 포인트")
                        st.caption(f"매칭된 시그널 데이터: {data_count}개 포인트 (최소 2개 필요)")
                        st.caption("S&P 500 데이터와 종합점수 데이터의 날짜 매칭이 필요합니다.")
            except Exception as e:
                logger.error(f"주식 비중 시그널 차트 생성 실패: {e}", exc_info=True)
                import traceback
                with st.expander("⚠️ 주식 비중 확대/축소 시그널 추이 그래프 오류"):
                    st.error(f"오류: {str(e)}")
                    st.code(traceback.format_exc())
        except Exception as e:
            logger.debug(f"S&P 500 차트 및 상관관계 분석 실패: {e}")
    else:
        # 데이터가 없어도 현재 점수만이라도 표시
        current_date = datetime.now().date()
        current_row = pd.DataFrame({
            'date': [pd.Timestamp(current_date)],
            'overall_score': [overall_score]
        })
        st.plotly_chart(create_overall_score_trend_chart(current_row), use_container_width=True)
except Exception as e:
    import traceback
    logger.error(f"종합점수 추이 계산 실패: {e}", exc_info=True)
    with st.expander("⚠️ 종합점수 추이 계산 오류"):
        st.error(f"오류: {str(e)}")
        st.code(traceback.format_exc())
    st.info("종합점수 추이를 계산하는 중 오류가 발생했습니다. 데이터를 새로고침해보세요.")

# 자산배분 섹션
st.header("💰 추천 자산배분")

col1, col2 = st.columns([1, 1])

with col1:
    allocation = allocation_result['allocation']
    st.plotly_chart(create_pie_chart(allocation), use_container_width=True)

with col2:
    st.markdown("### 배분 비율")
    for asset_type, pct in allocation.items():
        asset_name = {
            'stocks': '🔵 주식',
            'bonds': '🟢 채권',
            'cash': '🟡 현금',
            'real_estate': '🟠 부동산'
        }.get(asset_type, asset_type)
        
        st.markdown(f"**{asset_name}**: {pct}%")
        st.progress(pct / 100)
    
    st.info(f"**추천**: {allocation_result['recommendation']}")
    st.caption(f"위험 수준: {allocation_result['risk_level']}")

# 카테고리별 상세 지표
st.header("📊 카테고리별 상세 지표")

category_names = {
    'economy': '경기 사이클',
    'rates': '금리/채권',
    'inflation': '인플레이션',
    'volatility': '변동성',
    'liquidity': '유동성'
}

for category, indicators in INDICATOR_CATEGORIES.items():
    with st.expander(f"📌 {category_names.get(category, category)} (가중치: {WEIGHTS[category]*100:.0f}%)"):
        # 사용 가능한 지표만 필터링
        available_indicators_in_category = []
        for indicator_id in indicators:
            if indicator_id in indicator_data and indicator_data[indicator_id] is not None:
                data = indicator_data[indicator_id]
                if isinstance(data, dict):
                    # INDPRO는 YoY 값을 우선 사용하지만, 없으면 latest_value도 허용
                    if indicator_id == 'INDPRO':
                        if data.get('yoy') is not None or data.get('latest_value') is not None:
                            available_indicators_in_category.append(indicator_id)
                    elif data.get('latest_value') is not None:
                        available_indicators_in_category.append(indicator_id)
        
        if not available_indicators_in_category:
            st.warning(f"이 카테고리에는 사용 가능한 지표가 없습니다. (예상 지표: {', '.join(indicators)})")
            continue
        
        cols = st.columns(min(len(available_indicators_in_category), 3))
        
        for idx, indicator_id in enumerate(available_indicators_in_category):
            data = indicator_data[indicator_id]
            # YoY 값을 사용하는 지표들
            if indicator_id in ['CPIAUCSL', 'PPIACO', 'PCEPILFE', 'M2SL', 'INDPRO']:
                display_value = data.get('yoy')
                if display_value is None:
                    display_value = data.get('latest_value')
            else:
                display_value = data.get('latest_value')
            
            if display_value is None:
                continue
            
            change_pct = data.get('change_pct')
            score = scores.get('indicator_scores', {}).get(indicator_id, {}).get('score')
            
            with cols[idx % len(cols)]:
                status, status_emoji = get_indicator_status(score)
                
                # 변화 방향 표시
                delta_symbol = ""
                if change_pct is not None:
                    if change_pct > 0:
                        delta_symbol = "↑"
                    elif change_pct < 0:
                        delta_symbol = "↓"
                
                # 지표 설명 툴팁
                desc = INDICATOR_DESCRIPTIONS.get(indicator_id, {})
                tooltip_text = f"**{desc.get('description', indicator_id)}**\n\n{desc.get('detail', '')}\n\n**기준점:**\n"
                if desc.get('criteria'):
                    for key, value in desc.get('criteria', {}).items():
                        tooltip_text += f"- {value}\n"
                
                with st.popover(f"ℹ️ {FRED_INDICATORS.get(indicator_id, indicator_id)}"):
                    st.markdown(tooltip_text)
                
                st.metric(
                    label=FRED_INDICATORS.get(indicator_id, indicator_id),
                    value=format_indicator_value(indicator_id, display_value),
                    delta=f"{delta_symbol} {format_percentage(abs(change_pct)) if change_pct else ''}",
                    delta_color="normal" if (change_pct is None or change_pct < 0) else "inverse"
                )
                st.caption(f"{status_emoji} {status} (점수: {score:.1f}점)" if score else "데이터 없음")

# 데이터 테이블 (선택사항)
with st.expander("📋 원본 데이터 보기"):
    # 선택된 지표를 저장할 세션 상태
    if 'selected_indicator_detail' not in st.session_state:
        st.session_state.selected_indicator_detail = None
    
    data_rows = []
    for indicator_id, data in indicator_data.items():
        if data is None:
            data_rows.append({
                '지표': FRED_INDICATORS.get(indicator_id, indicator_id),
                'ID': indicator_id,
                '상태': '❌ 수집 실패',
                '표시값': None,
                '원본값': None,
                '전년대비(YoY, %)': None,
                '전분기대비(QoQ, %)': None,
                '전월대비(MoM, %)': None,
                '최신일자': None,
                '점수': None
            })
            continue
        
        if not isinstance(data, dict):
            data_rows.append({
                '지표': FRED_INDICATORS.get(indicator_id, indicator_id),
                'ID': indicator_id,
                '상태': '⚠️ 데이터 형식 오류',
                '표시값': None,
                '원본값': None,
                '전년대비(YoY, %)': None,
                '전분기대비(QoQ, %)': None,
                '전월대비(MoM, %)': None,
                '최신일자': None,
                '점수': None
            })
            continue
        
        # YoY 값을 사용하는 지표들
        if indicator_id in ['CPIAUCSL', 'PPIACO', 'PCEPILFE', 'M2SL', 'INDPRO']:
            display_value = data.get('yoy')
            status_check = '✅ 수집 완료' if display_value is not None else '⚠️ YoY 값 없음'
            original_value = data.get('latest_value')  # 원본 인덱스 값
        else:
            display_value = data.get('latest_value')
            status_check = '✅ 수집 완료' if display_value is not None else '⚠️ 값 없음'
            original_value = None
        
        # None 값을 "-"로 표시
        def format_value(val):
            if val is None:
                return "-"
            elif isinstance(val, float):
                return f"{val:.2f}"
            else:
                return val
        
        # 시그널 판단 함수 (변화가 좋은지 나쁜지)
        def get_change_signal(change_value: Optional[float], indicator_id: str) -> str:
            """변화율에 따른 시그널 반환 (🟢 좋음, 🔴 나쁨, ⚪ 변화 없음/데이터 없음)"""
            if change_value is None or pd.isna(change_value):
                return "⚪"
            
            # 인플레이션 지표: 낮아지면 좋음 (음수 = 좋음)
            if indicator_id in ['PCEPILFE', 'CPIAUCSL', 'PPIACO', 'T5YIE']:
                return "🟢" if change_value < 0 else "🔴" if change_value > 0 else "⚪"
            
            # 실업률: 낮아지면 좋음 (음수 = 좋음)
            elif indicator_id == 'UNRATE':
                return "🟢" if change_value < 0 else "🔴" if change_value > 0 else "⚪"
            
            # 경기 지표: 높아지면 좋음 (양수 = 좋음)
            elif indicator_id in ['UMCSENT', 'INDPRO', 'TCU']:
                return "🟢" if change_value > 0 else "🔴" if change_value < 0 else "⚪"
            
            # 금리 지표: 낮아지면 좋음 (음수 = 좋음)
            elif indicator_id in ['DFF', 'DFII10']:
                return "🟢" if change_value < 0 else "🔴" if change_value > 0 else "⚪"
            
            # 수익률 곡선: 양수 변화가 좋음 (스프레드 확대)
            elif indicator_id == 'T10Y2Y':
                return "🟢" if change_value > 0 else "🔴" if change_value < 0 else "⚪"
            
            # 변동성 지표: 낮아지면 좋음 (음수 = 좋음)
            elif indicator_id in ['VIX', 'BAMLH0A0HYM2']:
                return "🟢" if change_value < 0 else "🔴" if change_value > 0 else "⚪"
            
            # 유동성 지표
            elif indicator_id in ['WALCL', 'M2SL']:
                # 증가하면 좋음 (양수 = 좋음)
                return "🟢" if change_value > 0 else "🔴" if change_value < 0 else "⚪"
            elif indicator_id == 'RRPONTSYD':
                # 감소하면 좋음 (음수 = 좋음)
                return "🟢" if change_value < 0 else "🔴" if change_value > 0 else "⚪"
            
            else:
                return "⚪"
        
        # 시그널과 함께 값 포맷팅
        def format_value_with_signal(val: Optional[float], indicator_id: str) -> str:
            """값과 시그널을 함께 반환"""
            formatted = format_value(val)
            if formatted == "-":
                return "-"
            signal = get_change_signal(val, indicator_id)
            return f"{formatted} {signal}"
        
        yoy_value = data.get('yoy')
        qoq_value = data.get('qoq')
        mom_value = data.get('mom')
        
        # 표시값에 대한 시그널 (점수 기반)
        indicator_score = scores.get('indicator_scores', {}).get(indicator_id, {}).get('score')
        _, score_signal = get_indicator_status(indicator_score)
        
        # 표시값과 시그널 포맷팅
        def format_display_value_with_signal(val: Optional[float], signal: str) -> str:
            """표시값과 시그널을 함께 반환"""
            formatted = format_value(val)
            if formatted == "-":
                return "-"
            return f"{formatted} {signal}"
        
        data_rows.append({
            '지표': FRED_INDICATORS.get(indicator_id, indicator_id),
            'ID': indicator_id,
            '상태': status_check,
            '표시값': format_display_value_with_signal(display_value, score_signal),
            '원본값': format_value(original_value) if original_value is not None else "-",  # 인덱스 값 (YoY 지표인 경우)
            '전년대비(YoY, %)': format_value_with_signal(yoy_value, indicator_id),
            '전분기대비(QoQ, %)': format_value_with_signal(qoq_value, indicator_id),
            '전월대비(MoM, %)': format_value_with_signal(mom_value, indicator_id),
            '최신일자': data.get('latest_date', '-'),
            '점수': format_value(scores.get('indicator_scores', {}).get(indicator_id, {}).get('score'))
        })
    
    if data_rows:
        # 선택된 지표를 저장할 세션 상태
        if 'selected_indicator_detail' not in st.session_state:
            st.session_state.selected_indicator_detail = None
        
        # 데이터프레임 생성 및 표시
        df = pd.DataFrame(data_rows)
        
        st.markdown("💡 **지표명을 클릭하여 상세 설명을 확인하세요**")
        st.dataframe(df, use_container_width=True)
        
        # 지표명 선택을 위한 버튼들 (데이터프레임 아래)
        st.markdown("### 📖 지표 상세 설명")
        
        # 지표명 버튼들을 그리드로 배치
        cols_per_row = 4
        indicator_list = [(row['ID'], row['지표']) for row in data_rows]
        
        for i in range(0, len(indicator_list), cols_per_row):
            cols = st.columns(cols_per_row)
            for j, (indicator_id, indicator_name) in enumerate(indicator_list[i:i+cols_per_row]):
                with cols[j]:
                    # 현재 선택된 지표인지 확인
                    is_selected = st.session_state.selected_indicator_detail == indicator_id
                    button_label = f"📊 {indicator_name}"
                    button_type = "primary" if is_selected else "secondary"
                    
                    if st.button(button_label, key=f"indicator_btn_{indicator_id}", 
                                use_container_width=True, type=button_type):
                        if is_selected:
                            # 같은 지표를 다시 클릭하면 닫기
                            st.session_state.selected_indicator_detail = None
                        else:
                            st.session_state.selected_indicator_detail = indicator_id
                        st.rerun()
        
        st.divider()
        
        # 선택된 지표의 상세 설명 표시 (테이블 바로 아래)
        if st.session_state.selected_indicator_detail:
            selected_id = st.session_state.selected_indicator_detail
            selected_desc = INDICATOR_DESCRIPTIONS.get(selected_id, {})
            selected_name = FRED_INDICATORS.get(selected_id, selected_id)
            
            if selected_desc:
                # 선택된 지표의 전체 데이터 찾기
                selected_row = next((r for r in data_rows if r['ID'] == selected_id), None)
                
                st.markdown("---")
                st.markdown(f"### 📊 {selected_name} 상세 정보")
                
                # 상세 설명
                st.markdown(f"**{selected_desc.get('description', selected_name)}**")
                st.markdown(selected_desc.get('detail', ''))
                
                if selected_desc.get('criteria'):
                    st.markdown("**기준점:**")
                    for key, value in selected_desc.get('criteria', {}).items():
                        st.markdown(f"- {value}")
                
                # 해당 지표의 데이터 표시
                if selected_row:
                    st.markdown("**현재 값:**")
                    data_cols = st.columns(4)
                    with data_cols[0]:
                        st.metric("표시값", selected_row.get('표시값', '-'))
                    with data_cols[1]:
                        st.metric("YoY", selected_row.get('전년대비(YoY, %)', '-'))
                    with data_cols[2]:
                        st.metric("QoQ", selected_row.get('전분기대비(QoQ, %)', '-'))
                    with data_cols[3]:
                        st.metric("MoM", selected_row.get('전월대비(MoM, %)', '-'))
                
                # 닫기 버튼
                if st.button("❌ 설명 닫기", key="close_detail"):
                    st.session_state.selected_indicator_detail = None
                    st.rerun()
        
        # 통계 정보
        success_count = sum(1 for row in data_rows if row['상태'] == '✅ 수집 완료')
        st.caption(f"수집 성공: {success_count}/{len(data_rows)} 지표")

# 시계열 차트 (맨 아래)
st.header("📈 시계열 차트")

period = st.selectbox("기간 선택", ["1Y", "3Y", "5Y"], index=0)

# 모든 지표 수집
all_available_indicators = []
for indicator_id in FRED_INDICATORS.keys():
    if indicator_id in indicator_data and indicator_data[indicator_id] is not None:
        data = indicator_data[indicator_id]
        if isinstance(data, dict) and data.get('series') is not None:
            series = data.get('series')
            if isinstance(series, pd.Series) and len(series) > 0:
                all_available_indicators.append(indicator_id)

# VIX도 추가
if 'VIX' in indicator_data and indicator_data['VIX'] is not None:
    vix_data = indicator_data['VIX']
    if isinstance(vix_data, dict) and vix_data.get('series') is not None:
        series = vix_data.get('series')
        if isinstance(series, pd.Series) and len(series) > 0:
            if 'VIX' not in all_available_indicators:
                all_available_indicators.append('VIX')

if all_available_indicators:
    st.plotly_chart(
        create_time_series_chart(indicator_data, all_available_indicators, period),
        use_container_width=True
    )
    st.caption(f"총 {len(all_available_indicators)}개 지표 표시 중")
else:
    st.warning("시계열 차트를 표시할 수 있는 지표가 없습니다.")
    st.info("💡 데이터를 새로고침하거나 '원본 데이터 보기' 섹션에서 수집된 지표를 확인하세요.")

# 푸터
st.divider()
st.markdown("""
<div style='text-align: center; color: gray;'>
    <small>거시경제 지표 기반 자산배분 모니터링 대시보드 | 데이터는 참고용이며 투자 결정에 대한 책임은 사용자에게 있습니다.</small>
</div>
""", unsafe_allow_html=True)

