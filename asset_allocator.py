"""
자산배분 로직 모듈
"""
import logging
from typing import Dict
import numpy as np

from config import ALLOCATION_SCORES

logger = logging.getLogger(__name__)


class AssetAllocator:
    """자산배분 계산 클래스"""
    
    def calculate_allocation(self, overall_score: float) -> Dict[str, float]:
        """
        종합 점수 기반 자산배분 계산
        
        Args:
            overall_score: 종합 점수 (0-100)
            
        Returns:
            자산배분 딕셔너리 (퍼센트)
        """
        # 점수 구간 결정
        if overall_score >= 80:
            allocation_range = ALLOCATION_SCORES['80-100']
        elif overall_score >= 60:
            allocation_range = ALLOCATION_SCORES['60-80']
        elif overall_score >= 40:
            allocation_range = ALLOCATION_SCORES['40-60']
        elif overall_score >= 20:
            allocation_range = ALLOCATION_SCORES['20-40']
        else:
            allocation_range = ALLOCATION_SCORES['0-20']
        
        # 각 자산군의 범위 내에서 점수에 따라 선형 보간
        allocation = {}
        
        for asset_type, (min_pct, max_pct) in allocation_range.items():
            # 점수 구간 내에서의 위치 (0-1)
            if overall_score >= 80:
                position = (overall_score - 80) / 20
            elif overall_score >= 60:
                position = (overall_score - 60) / 20
            elif overall_score >= 40:
                position = (overall_score - 40) / 20
            elif overall_score >= 20:
                position = (overall_score - 20) / 20
            else:
                position = overall_score / 20
            
            # 선형 보간
            pct = min_pct + (max_pct - min_pct) * position
            allocation[asset_type] = round(pct, 2)
        
        # 합계가 100%가 되도록 정규화
        total = sum(allocation.values())
        if total != 100.0:
            for asset_type in allocation:
                allocation[asset_type] = round(allocation[asset_type] * 100 / total, 2)
        
        # 마지막 자산에 나머지 할당하여 정확히 100% 맞추기
        total = sum(allocation.values())
        if total != 100.0:
            diff = 100.0 - total
            # 가장 큰 자산에 차이 추가
            max_asset = max(allocation.items(), key=lambda x: x[1])[0]
            allocation[max_asset] = round(allocation[max_asset] + diff, 2)
        
        return allocation
    
    def get_allocation_recommendation(self, overall_score: float) -> Dict[str, any]:
        """
        자산배분 추천 및 설명
        
        Args:
            overall_score: 종합 점수
            
        Returns:
            자산배분 및 추천 설명
        """
        allocation = self.calculate_allocation(overall_score)
        
        # 추천 설명 생성
        if overall_score >= 80:
            recommendation = "매우 긍정적인 시장 환경입니다. 주식에 높은 비중을 배분하는 것을 권장합니다."
            risk_level = "낮음"
        elif overall_score >= 60:
            recommendation = "긍정적인 시장 환경입니다. 주식 중심의 균형잡힌 포트폴리오를 권장합니다."
            risk_level = "중간-낮음"
        elif overall_score >= 40:
            recommendation = "중립적인 시장 환경입니다. 보수적인 자산배분을 권장합니다."
            risk_level = "중간"
        elif overall_score >= 20:
            recommendation = "부정적인 시장 환경입니다. 현금과 채권 비중을 높이는 것을 권장합니다."
            risk_level = "중간-높음"
        else:
            recommendation = "매우 부정적인 시장 환경입니다. 현금 비중을 대폭 높이고 방어적 자산배분을 권장합니다."
            risk_level = "높음"
        
        return {
            'allocation': allocation,
            'recommendation': recommendation,
            'risk_level': risk_level,
            'score': overall_score
        }



