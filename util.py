"""
유틸리티 함수 모듈
"""
import json
import os
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import pandas as pd

from config import CACHE_DIR, CACHE_FILE, CACHE_EXPIRY_HOURS

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def ensure_cache_dir() -> Path:
    """캐시 디렉토리 생성"""
    cache_path = Path(CACHE_DIR)
    cache_path.mkdir(exist_ok=True)
    return cache_path


def load_cache() -> Optional[Dict[str, Any]]:
    """캐시 파일 로드"""
    cache_path = Path(CACHE_DIR) / CACHE_FILE
    
    if not cache_path.exists():
        return None
    
    try:
        with open(cache_path, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
        
        # 캐시 만료 확인
        cache_time = datetime.fromisoformat(cache_data.get('timestamp', ''))
        expiry_time = cache_time + timedelta(hours=CACHE_EXPIRY_HOURS)
        
        if datetime.now() > expiry_time:
            logger.info("캐시가 만료되었습니다.")
            return None
        
        # pandas Series 복원
        data = cache_data.get('data', {})
        restored_data = {}
        
        for key, value in data.items():
            if value is None:
                restored_data[key] = None
            elif isinstance(value, dict):
                restored_value = {}
                for k, v in value.items():
                    if isinstance(v, dict) and v.get('_type') == 'pandas_series':
                        # pandas Series 복원
                        try:
                            index = pd.to_datetime(v.get('index', []))
                            restored_value[k] = pd.Series(v.get('values', []), index=index)
                        except Exception as e:
                            logger.warning(f"Series 복원 실패 ({key}.{k}): {e}")
                            restored_value[k] = v
                    else:
                        restored_value[k] = v
                restored_data[key] = restored_value
            else:
                restored_data[key] = value
        
        logger.info("캐시에서 데이터를 로드했습니다.")
        return restored_data
    
    except Exception as e:
        logger.error(f"캐시 로드 실패: {e}")
        return None


def save_cache(data: Dict[str, Any]) -> None:
    """캐시 파일 저장"""
    ensure_cache_dir()
    cache_path = Path(CACHE_DIR) / CACHE_FILE
    
    try:
        # pandas Series를 딕셔너리로 변환하여 저장
        cache_data = {
            'timestamp': datetime.now().isoformat(),
            'data': {}
        }
        
        for key, value in data.items():
            if value is None:
                cache_data['data'][key] = None
            elif isinstance(value, dict):
                cache_value = {}
                for k, v in value.items():
                    if isinstance(v, pd.Series):
                        # pandas Series를 딕셔너리로 변환
                        cache_value[k] = {
                            '_type': 'pandas_series',
                            'index': [str(i) for i in v.index],
                            'values': v.values.tolist()
                        }
                    else:
                        cache_value[k] = v
                cache_data['data'][key] = cache_value
            else:
                cache_data['data'][key] = value
        
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, indent=2, default=str)
        
        logger.info("캐시를 저장했습니다.")
    
    except Exception as e:
        logger.error(f"캐시 저장 실패: {e}")


def calculate_yoy_growth(series: pd.Series) -> Optional[float]:
    """연간 증가율(YoY) 계산"""
    if len(series) < 2:
        return None
    
    try:
        latest = series.iloc[-1]
        
        # 12개월 전 데이터 찾기 (가능한 경우)
        if len(series) >= 12:
            year_ago = series.iloc[-12]
        else:
            # 데이터가 부족하면 첫 번째 값 사용
            year_ago = series.iloc[0]
        
        if pd.isna(latest) or pd.isna(year_ago):
            return None
        
        if year_ago == 0:
            # 0으로 나누기 방지
            return None
        
        yoy = ((latest - year_ago) / year_ago) * 100
        return float(yoy)
    
    except Exception as e:
        logger.error(f"YoY 계산 실패: {e}")
        return None


def calculate_mom_growth(series: pd.Series) -> Optional[float]:
    """전월 대비 증가율(MoM) 계산"""
    if len(series) < 2:
        return None
    
    try:
        latest = series.iloc[-1]
        prev = series.iloc[-2]
        
        if pd.isna(latest) or pd.isna(prev) or prev == 0:
            return None
        
        mom = ((latest - prev) / prev) * 100
        return float(mom)
    
    except Exception as e:
        logger.error(f"MoM 계산 실패: {e}")
        return None


def calculate_qoq_growth(series: pd.Series) -> Optional[float]:
    """전분기 대비 증가율(QoQ) 계산"""
    if len(series) < 2:
        return None
    
    try:
        latest = series.iloc[-1]
        # 3개월 전 데이터 (분기)
        if len(series) >= 3:
            quarter_ago = series.iloc[-3]
        else:
            # 데이터가 부족하면 첫 번째 값 사용
            quarter_ago = series.iloc[0]
        
        if pd.isna(latest) or pd.isna(quarter_ago):
            return None
        
        if quarter_ago == 0:
            return None
        
        qoq = ((latest - quarter_ago) / quarter_ago) * 100
        return float(qoq)
    
    except Exception as e:
        logger.error(f"QoQ 계산 실패: {e}")
        return None


def format_percentage(value: float, decimals: int = 2) -> str:
    """퍼센트 포맷팅"""
    return f"{value:.{decimals}f}%"


def format_number(value: float, decimals: int = 2) -> str:
    """숫자 포맷팅"""
    return f"{value:,.{decimals}f}"


def get_score_color(score: float) -> str:
    """점수에 따른 색상 반환"""
    if score >= 70:
        return "#00ff00"  # 초록
    elif score >= 40:
        return "#ffaa00"  # 노랑
    else:
        return "#ff0000"  # 빨강


def get_market_sentiment(score: float) -> Tuple[str, str]:
    """점수에 따른 시장 심리 반환"""
    if score >= 80:
        return "매우 긍정적", "🟢"
    elif score >= 60:
        return "긍정적", "🟡"
    elif score >= 40:
        return "중립적", "🟠"
    elif score >= 20:
        return "부정적", "🔴"
    else:
        return "매우 부정적", "⚫"

