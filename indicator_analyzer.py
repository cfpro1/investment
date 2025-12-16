"""
지표 분석 및 점수화 모듈
"""
import logging
from typing import Dict, Optional, Any
import numpy as np

from config import (
    SCORING_THRESHOLDS,
    WEIGHTS,
    INDICATOR_CATEGORIES
)

logger = logging.getLogger(__name__)


class IndicatorAnalyzer:
    """지표 분석 및 점수화 클래스"""
    
    def __init__(self):
        """초기화"""
        self.weights = WEIGHTS
    
    def analyze_unemployment(self, rate: float) -> float:
        """
        실업률 분석 (0-100점)
        
        Args:
            rate: 실업률 (%)
            
        Returns:
            점수 (0-100)
        """
        thresholds = SCORING_THRESHOLDS['UNRATE']
        excellent = thresholds['excellent']  # 4%
        poor = thresholds['poor']  # 6%
        
        if rate <= excellent:
            return 100.0
        elif rate >= poor:
            return 0.0
        else:
            # 선형 보간
            score = 100 * (1 - (rate - excellent) / (poor - excellent))
            return max(0.0, min(100.0, score))
    
    def analyze_yield_curve(self, spread: float) -> float:
        """
        수익률 곡선 분석 (0-100점)
        
        Args:
            spread: 10년-2년 스프레드 (%)
            
        Returns:
            점수 (0-100)
        """
        thresholds = SCORING_THRESHOLDS['T10Y2Y']
        excellent = thresholds['excellent']  # +0.5%
        poor = thresholds['poor']  # -0.5%
        
        if spread >= excellent:
            return 100.0
        elif spread <= poor:
            return 0.0
        else:
            # 선형 보간
            score = 100 * (spread - poor) / (excellent - poor)
            return max(0.0, min(100.0, score))
    
    def analyze_vix(self, vix_value: float) -> float:
        """
        VIX 분석 (0-100점)
        
        Args:
            vix_value: VIX 값
            
        Returns:
            점수 (0-100)
        """
        thresholds = SCORING_THRESHOLDS['VIX']
        excellent = thresholds['excellent']  # 12
        poor = thresholds['poor']  # 30
        
        if vix_value <= excellent:
            return 100.0
        elif vix_value >= poor:
            return 0.0
        else:
            # 선형 보간 (낮을수록 좋음)
            score = 100 * (1 - (vix_value - excellent) / (poor - excellent))
            return max(0.0, min(100.0, score))
    
    def analyze_consumer_sentiment(self, sentiment: float) -> float:
        """
        소비자 신뢰지수 분석 (0-100점)
        
        Args:
            sentiment: 소비자 신뢰지수
            
        Returns:
            점수 (0-100)
        """
        thresholds = SCORING_THRESHOLDS['UMCSENT']
        excellent = thresholds['excellent']  # 100
        poor = thresholds['poor']  # 50
        
        if sentiment >= excellent:
            return 100.0
        elif sentiment <= poor:
            return 0.0
        else:
            score = 100 * (sentiment - poor) / (excellent - poor)
            return max(0.0, min(100.0, score))
    
    def analyze_fed_funds_rate(self, rate: float) -> float:
        """
        연방기금금리 분석 (0-100점)
        낮을수록 좋음 (주식 시장 관점)
        
        Args:
            rate: 연방기금금리 (%)
            
        Returns:
            점수 (0-100)
        """
        thresholds = SCORING_THRESHOLDS['DFF']
        excellent = thresholds['excellent']  # 2%
        poor = thresholds['poor']  # 5%
        
        if rate <= excellent:
            return 100.0
        elif rate >= poor:
            return 0.0
        else:
            score = 100 * (1 - (rate - excellent) / (poor - excellent))
            return max(0.0, min(100.0, score))
    
    def analyze_real_rate(self, rate: float) -> float:
        """
        실질금리 분석 (0-100점)
        
        Args:
            rate: 실질금리 (%)
            
        Returns:
            점수 (0-100)
        """
        thresholds = SCORING_THRESHOLDS['DFII10']
        excellent = thresholds['excellent']  # 0.5%
        poor = thresholds['poor']  # 2.5%
        
        if rate <= excellent:
            return 100.0
        elif rate >= poor:
            return 0.0
        else:
            score = 100 * (1 - (rate - excellent) / (poor - excellent))
            return max(0.0, min(100.0, score))
    
    def analyze_inflation(self, inflation_rate: float) -> float:
        """
        인플레이션 분석 (0-100점)
        낮을수록 좋음
        
        Args:
            inflation_rate: 인플레이션율 (%)
            
        Returns:
            점수 (0-100)
        """
        thresholds = SCORING_THRESHOLDS['PCEPILFE']
        excellent = thresholds['excellent']  # 2%
        poor = thresholds['poor']  # 4%
        
        if inflation_rate <= excellent:
            return 100.0
        elif inflation_rate >= poor:
            return 0.0
        else:
            score = 100 * (1 - (inflation_rate - excellent) / (poor - excellent))
            return max(0.0, min(100.0, score))
    
    def analyze_breakeven_inflation(self, rate: float) -> float:
        """
        브레이크이븐 인플레이션 분석 (0-100점)
        
        Args:
            rate: 브레이크이븐 인플레이션율 (%)
            
        Returns:
            점수 (0-100)
        """
        thresholds = SCORING_THRESHOLDS['T5YIE']
        excellent = thresholds['excellent']  # 2%
        poor = thresholds['poor']  # 3.5%
        
        if rate <= excellent:
            return 100.0
        elif rate >= poor:
            return 0.0
        else:
            score = 100 * (1 - (rate - excellent) / (poor - excellent))
            return max(0.0, min(100.0, score))
    
    def analyze_high_yield_spread(self, spread: float) -> float:
        """
        하이일드 스프레드 분석 (0-100점)
        
        Args:
            spread: 하이일드 스프레드 (%)
            
        Returns:
            점수 (0-100)
        """
        thresholds = SCORING_THRESHOLDS['BAMLH0A0HYM2']
        excellent = thresholds['excellent']  # 3%
        poor = thresholds['poor']  # 8%
        
        if spread <= excellent:
            return 100.0
        elif spread >= poor:
            return 0.0
        else:
            score = 100 * (1 - (spread - excellent) / (poor - excellent))
            return max(0.0, min(100.0, score))
    
    def analyze_m2_growth(self, yoy_rate: float) -> float:
        """
        M2 증가율 분석 (0-100점)
        높을수록 좋음 (유동성 관점)
        
        Args:
            yoy_rate: M2 YoY 증가율 (%)
            
        Returns:
            점수 (0-100)
        """
        thresholds = SCORING_THRESHOLDS['M2SL']
        excellent = thresholds['excellent']  # 10%
        poor = thresholds['poor']  # -2%
        
        if yoy_rate >= excellent:
            return 100.0
        elif yoy_rate <= poor:
            return 0.0
        else:
            score = 100 * (yoy_rate - poor) / (excellent - poor)
            return max(0.0, min(100.0, score))
    
    def analyze_industrial_production(self, yoy_rate: float) -> float:
        """
        산업생산지수(INDPRO) YoY 증가율 분석 (0-100점)
        
        Args:
            yoy_rate: 산업생산지수 YoY 증가율 (%)
            
        Returns:
            점수 (0-100)
        """
        thresholds = SCORING_THRESHOLDS['INDPRO']
        excellent = thresholds['excellent']  # 3% 이상: 100점
        good = thresholds['good']  # 1-3%: 70점
        neutral = thresholds['neutral']  # -1~1%: 40점
        poor = thresholds['poor']  # -1% 이하: 0점
        
        if yoy_rate >= excellent:
            return 100.0
        elif yoy_rate >= good:
            # 1-3% 구간: 70-100점 선형 보간
            score = 70 + 30 * (yoy_rate - good) / (excellent - good)
            return max(70.0, min(100.0, score))
        elif yoy_rate >= neutral:
            # -1~1% 구간: 40-70점 선형 보간
            score = 40 + 30 * (yoy_rate - neutral) / (good - neutral)
            return max(40.0, min(70.0, score))
        elif yoy_rate >= poor:
            # -1% 이하: 0-40점 선형 보간
            score = 40 * (yoy_rate - poor) / (neutral - poor)
            return max(0.0, min(40.0, score))
        else:
            return 0.0
    
    def analyze_capacity_utilization(self, tcu_value: float) -> float:
        """
        제조업 가동률(TCU) 분석 (0-100점)
        
        Args:
            tcu_value: 제조업 가동률 (%)
            
        Returns:
            점수 (0-100)
        """
        thresholds = SCORING_THRESHOLDS['TCU']
        excellent = thresholds['excellent']  # 75-80%: 100점
        good = thresholds['good']  # 70-75%: 60점
        poor = thresholds['poor']  # 70% 이하: 20점
        overheat = thresholds['overheat']  # 80% 이상: 과열 우려
        
        if tcu_value >= overheat:
            # 80% 이상: 과열 우려로 점수 감소 (인플레 압력)
            # 80-85%: 100점에서 80점으로 감소
            if tcu_value >= 85:
                return 80.0
            else:
                return 100.0 - 20.0 * (tcu_value - overheat) / 5.0
        elif tcu_value >= excellent:
            # 75-80%: 100점 (정상 범위)
            return 100.0
        elif tcu_value >= good:
            # 70-75%: 60-100점 선형 보간
            score = 60 + 40 * (tcu_value - good) / (excellent - good)
            return max(60.0, min(100.0, score))
        else:
            # 70% 이하: 20점 (경기침체 신호)
            if tcu_value <= 60:
                return 20.0
            else:
                # 60-70%: 20-60점 선형 보간
                score = 20 + 40 * (tcu_value - 60) / (good - 60)
                return max(20.0, min(60.0, score))
    
    def analyze_fed_balance_sheet(self, yoy_rate: float) -> float:
        """
        연준 대차대조표(WALCL) YoY 증가율 분석 (0-100점)
        증가하면 유동성 공급 (긍정적)
        
        Args:
            yoy_rate: 연준 대차대조표 YoY 증가율 (%)
            
        Returns:
            점수 (0-100)
        """
        thresholds = SCORING_THRESHOLDS['WALCL']
        excellent = thresholds['excellent']  # 5% 이상: 100점
        good = thresholds['good']  # 0-5%: 70점
        poor = thresholds['poor']  # -10% 이하: 0점
        
        if yoy_rate >= excellent:
            return 100.0
        elif yoy_rate >= good:
            # 0-5% 구간: 70-100점 선형 보간
            score = 70 + 30 * (yoy_rate - good) / (excellent - good)
            return max(70.0, min(100.0, score))
        elif yoy_rate >= poor:
            # -10~0% 구간: 0-70점 선형 보간
            score = 70 * (yoy_rate - poor) / (good - poor)
            return max(0.0, min(70.0, score))
        else:
            return 0.0
    
    def analyze_reverse_repo(self, balance: float) -> float:
        """
        역레포 잔액(RRPONTSYD) 분석 (0-100점)
        적정 수준이 좋고, 너무 높으면 유동성 과잉
        
        Args:
            balance: 역레포 잔액 (조 달러)
            
        Returns:
            점수 (0-100)
        """
        thresholds = SCORING_THRESHOLDS['RRPONTSYD']
        excellent = thresholds['excellent']  # 0.5조 이하: 100점
        good = thresholds['good']  # 0.5-1조: 80점
        neutral = thresholds['neutral']  # 1-2조: 60점
        poor = thresholds['poor']  # 2조 이상: 40점
        
        if balance <= excellent:
            return 100.0
        elif balance <= good:
            # 0.5-1조 구간: 80-100점 선형 보간
            score = 80 + 20 * (balance - excellent) / (good - excellent)
            return max(80.0, min(100.0, score))
        elif balance <= neutral:
            # 1-2조 구간: 60-80점 선형 보간
            score = 60 + 20 * (balance - good) / (neutral - good)
            return max(60.0, min(80.0, score))
        else:
            # 2조 이상: 40점
            return 40.0
    
    def score_indicator(self, indicator_id: str, value: Optional[float]) -> Optional[float]:
        """
        개별 지표 점수화
        
        Args:
            indicator_id: 지표 ID
            value: 지표 값
            
        Returns:
            점수 또는 None
        """
        if value is None or np.isnan(value):
            return None
        
        try:
            if indicator_id == 'UNRATE':
                return self.analyze_unemployment(value)
            elif indicator_id == 'T10Y2Y':
                return self.analyze_yield_curve(value)
            elif indicator_id == 'VIX':
                return self.analyze_vix(value)
            elif indicator_id == 'UMCSENT':
                return self.analyze_consumer_sentiment(value)
            elif indicator_id == 'DFF':
                return self.analyze_fed_funds_rate(value)
            elif indicator_id == 'DFII10':
                return self.analyze_real_rate(value)
            elif indicator_id in ['PCEPILFE', 'CPIAUCSL', 'PPIACO']:
                # YoY 값 사용
                return self.analyze_inflation(value)
            elif indicator_id == 'T5YIE':
                return self.analyze_breakeven_inflation(value)
            elif indicator_id == 'BAMLH0A0HYM2':
                return self.analyze_high_yield_spread(value)
            elif indicator_id == 'M2SL':
                # YoY 값 사용
                return self.analyze_m2_growth(value)
            elif indicator_id == 'INDPRO':
                # YoY 값 사용
                return self.analyze_industrial_production(value)
            elif indicator_id == 'TCU':
                return self.analyze_capacity_utilization(value)
            elif indicator_id == 'WALCL':
                # YoY 값 사용
                return self.analyze_fed_balance_sheet(value)
            elif indicator_id == 'RRPONTSYD':
                # 원본 값 사용 (조 달러 단위)
                # 값이 너무 크면 조 달러로 변환 (예: 2000000 = 2조)
                balance_in_trillions = value / 1000000 if value > 1000 else value
                return self.analyze_reverse_repo(balance_in_trillions)
            else:
                logger.warning(f"알 수 없는 지표: {indicator_id}")
                return None
        except Exception as e:
            logger.error(f"지표 {indicator_id} 점수화 실패: {e}")
            return None
    
    def get_overall_score(self, indicator_data: Dict[str, Any]) -> Dict[str, float]:
        """
        종합 점수 계산
        
        Args:
            indicator_data: 지표 데이터 딕셔너리
            
        Returns:
            카테고리별 점수 및 종합 점수
        """
        category_scores = {}
        category_values = {}
        
        # 카테고리별 점수 계산
        for category, indicators in INDICATOR_CATEGORIES.items():
            scores = []
            
            for indicator_id in indicators:
                if indicator_id not in indicator_data or indicator_data[indicator_id] is None:
                    continue
                
                data = indicator_data[indicator_id]
                
                # 값 추출
                value = None
                if indicator_id in ['CPIAUCSL', 'PPIACO', 'M2SL', 'PCEPILFE', 'INDPRO', 'WALCL']:
                    # YoY 값 사용
                    value = data.get('yoy')
                    # YoY 값이 없으면 latest_value 사용
                    if value is None:
                        value = data.get('latest_value')
                else:
                    value = data.get('latest_value')
                
                if value is None:
                    continue
                
                # 점수화
                score = self.score_indicator(indicator_id, value)
                if score is not None:
                    scores.append(score)
                    category_values[indicator_id] = {
                        'value': value,
                        'score': score
                    }
            
            # 카테고리 평균 점수
            if scores:
                category_scores[category] = np.mean(scores)
            else:
                category_scores[category] = None
        
        # 종합 점수 계산 (가중평균)
        overall_score = 0.0
        total_weight = 0.0
        
        for category, weight in self.weights.items():
            score = category_scores.get(category)
            if score is not None:
                overall_score += score * weight
                total_weight += weight
        
        if total_weight > 0:
            overall_score = overall_score / total_weight
        else:
            overall_score = 50.0  # 기본값
        
        return {
            'economy_score': category_scores.get('economy'),
            'rates_score': category_scores.get('rates'),
            'inflation_score': category_scores.get('inflation'),
            'volatility_score': category_scores.get('volatility'),
            'liquidity_score': category_scores.get('liquidity'),
            'overall_score': overall_score,
            'indicator_scores': category_values
        }

