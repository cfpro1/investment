"""
거시경제 데이터 수집 모듈
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
import pandas as pd
import yfinance as yf
from fredapi import Fred

from config import (
    FRED_INDICATORS,
    VIX_TICKER,
    LOOKBACK_DAYS,
    INDICATOR_CATEGORIES
)
from utils import load_cache, save_cache, calculate_yoy_growth, calculate_mom_growth, calculate_qoq_growth

logger = logging.getLogger(__name__)


class EconomicDataCollector:
    """거시경제 데이터 수집 클래스"""
    
    def __init__(self, fred_api_key: str):
        """
        Args:
            fred_api_key: FRED API 키
        """
        self.fred = Fred(api_key=fred_api_key)
        self.cache_enabled = True
    
    def fetch_all_indicators(self, use_cache: bool = True) -> Dict[str, Any]:
        """
        모든 지표 수집
        
        Args:
            use_cache: 캐시 사용 여부
            
        Returns:
            지표 데이터 딕셔너리
        """
        # 캐시 확인
        if use_cache and self.cache_enabled:
            cached_data = load_cache()
            if cached_data:
                return cached_data
        
        logger.info("새로운 데이터를 수집합니다...")
        
        data = {}
        
        # FRED 지표 수집
        for indicator_id, description in FRED_INDICATORS.items():
            try:
                logger.info(f"{indicator_id} 수집 중...")
                series_data = self.fetch_fred_indicator(indicator_id)
                if series_data is not None:
                    data[indicator_id] = series_data
            except Exception as e:
                logger.error(f"{indicator_id} 수집 실패: {e}")
                data[indicator_id] = None
        
        # VIX 수집
        try:
            logger.info("VIX 수집 중...")
            vix_data = self.fetch_vix()
            if vix_data is not None:
                data['VIX'] = vix_data
        except Exception as e:
            logger.error(f"VIX 수집 실패: {e}")
            data['VIX'] = None
        
        # 모든 지표에 대해 YoY, QoQ, MoM 계산
        for indicator_id, indicator_data in data.items():
            if indicator_data is None or not isinstance(indicator_data, dict):
                continue
            
            series = indicator_data.get('series')
            if series is not None and isinstance(series, pd.Series) and len(series) > 0:
                # YoY 계산
                if 'yoy' not in indicator_data:
                    yoy = calculate_yoy_growth(series)
                    if yoy is not None:
                        indicator_data['yoy'] = yoy
                
                # QoQ 계산
                if 'qoq' not in indicator_data:
                    qoq = calculate_qoq_growth(series)
                    if qoq is not None:
                        indicator_data['qoq'] = qoq
                
                # MoM 계산
                if 'mom' not in indicator_data:
                    mom = calculate_mom_growth(series)
                    if mom is not None:
                        indicator_data['mom'] = mom
        
        # 캐시 저장
        if self.cache_enabled:
            save_cache(data)
        
        return data
    
    def fetch_fred_indicator(
        self, 
        series_id: str, 
        lookback_days: int = LOOKBACK_DAYS
    ) -> Optional[Dict[str, Any]]:
        """
        개별 FRED 지표 수집
        
        Args:
            series_id: FRED 시리즈 ID
            lookback_days: 조회 기간 (일)
            
        Returns:
            지표 데이터 딕셔너리 또는 None
        """
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=lookback_days)
            
            series = self.fred.get_series(
                series_id,
                start=start_date,
                end=end_date
            )
            
            if series is None or len(series) == 0:
                logger.warning(f"{series_id}: 데이터가 없습니다.")
                return None
            
            # 최신 값
            latest_value = float(series.iloc[-1])
            latest_date = series.index[-1]
            
            # 이전 값 (변화율 계산용)
            prev_value = None
            change_pct = None
            if len(series) > 1:
                prev_value = float(series.iloc[-2])
                if prev_value != 0:
                    change_pct = ((latest_value - prev_value) / prev_value) * 100
            
            return {
                'series_id': series_id,
                'description': FRED_INDICATORS.get(series_id, ''),
                'latest_value': latest_value,
                'latest_date': latest_date.isoformat() if hasattr(latest_date, 'isoformat') else str(latest_date),
                'prev_value': prev_value,
                'change_pct': change_pct,
                'series': series,
                'data_points': len(series)
            }
        
        except Exception as e:
            logger.error(f"FRED 지표 {series_id} 수집 실패: {e}")
            return None
    
    def fetch_vix(self, lookback_days: int = LOOKBACK_DAYS) -> Optional[Dict[str, Any]]:
        """
        VIX 지수 수집 (yfinance 사용)
        
        Args:
            lookback_days: 조회 기간 (일)
            
        Returns:
            VIX 데이터 딕셔너리 또는 None
        """
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=lookback_days)
            
            ticker = yf.Ticker(VIX_TICKER)
            hist = ticker.history(start=start_date, end=end_date)
            
            if hist is None or len(hist) == 0:
                logger.warning("VIX 데이터가 없습니다.")
                return None
            
            # 종가 사용
            close_series = hist['Close']
            latest_value = float(close_series.iloc[-1])
            latest_date = close_series.index[-1]
            
            # 이전 값
            prev_value = None
            change_pct = None
            if len(close_series) > 1:
                prev_value = float(close_series.iloc[-2])
                if prev_value != 0:
                    change_pct = ((latest_value - prev_value) / prev_value) * 100
            
            return {
                'series_id': 'VIX',
                'description': 'CBOE Volatility Index',
                'latest_value': latest_value,
                'latest_date': latest_date.isoformat() if hasattr(latest_date, 'isoformat') else str(latest_date),
                'prev_value': prev_value,
                'change_pct': change_pct,
                'series': close_series,
                'data_points': len(close_series)
            }
        
        except Exception as e:
            logger.error(f"VIX 수집 실패: {e}")
            return None
    
    def disable_cache(self):
        """캐시 비활성화"""
        self.cache_enabled = False
    
    def enable_cache(self):
        """캐시 활성화"""
        self.cache_enabled = True

