"""
미국 섹터 트렌드 분석 대시보드
메인 페이지
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional
import streamlit as st
import pandas as pd
import numpy as np

from modules.sector.config import SECTORS, BENCHMARK, COLOR_SCHEME, SCORE_THRESHOLDS
from modules.sector.data_loader import get_all_sector_data, validate_data, get_benchmark_data
from modules.sector.indicators import calculate_all_indicators
from modules.sector.scoring import calculate_total_score, get_signal_korean
from modules.sector.visualizations import (
    create_sector_heatmap,
    create_radar_chart,
    create_ranking_table,
    create_price_chart
)

logger = logging.getLogger(__name__)

# 페이지 설정
st.set_page_config(
    page_title="미국 섹터 트렌드 분석",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🎯 미국 섹터 트렌드 분석")
st.markdown("---")

# 사이드바
with st.sidebar:
    st.header("⚙️ 설정")
    
    # 데이터 새로고침 버튼
    if st.button("🔄 데이터 새로고침", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    
    st.markdown("---")
    
    # 점수 임계값 필터
    st.subheader("점수 필터")
    min_score = st.slider(
        "최소 점수",
        min_value=0,
        max_value=100,
        value=0,
        step=5,
        help="이 점수 이상인 섹터만 표시합니다."
    )
    
    st.markdown("---")
    
    # 표시 모드 선택
    st.subheader("표시 모드")
    display_mode = st.radio(
        "모드 선택",
        ["그리드", "리스트"],
        index=0
    )
    
    st.markdown("---")
    
    # 정렬 기준 선택
    st.subheader("정렬 기준")
    sort_column = st.selectbox(
        "정렬 기준",
        ["종합점수", "모멘텀점수", "트렌드점수", "변동성점수", "기술적점수", "1M수익률"],
        index=0
    )
    
    sort_ascending = st.checkbox("오름차순", value=False)
    
    st.markdown("---")
    
    # 방법론 설명
    with st.expander("📖 방법론 설명"):
        st.markdown("""
        ### 점수 계산 체계 (100점 만점)
        
        **모멘텀 점수 (30점)**
        - 20일 상대강도 > SPY: +10점
        - 60일 상대강도 > SPY: +10점
        - 거래량 증가 (20일 평균 초과): +5점
        - 골든크로스 상태: +5점
        
        **트렌드 점수 (30점)**
        - 1개월 ROC: +10점(>5%), +5점(>0%), 0점(음수)
        - 3개월 ROC: +10점(>10%), +5점(>0%), 0점(음수)
        - 6개월 ROC: +10점(>15%), +5점(>0%), 0점(음수)
        
        **변동성 점수 (20점)**
        - 20일 변동성: +20점(<15%), +10점(<25%), 0점(>25%)
        
        **기술적 점수 (20점)**
        - 현재가 > 50일 이평: +10점
        - 현재가 > 200일 이평: +10점
        
        ### 진입 신호
        - **80점 이상**: 적극 매수 (Strong Buy)
        - **65-79점**: 매수 (Buy)
        - **50-64점**: 보유 (Hold)
        - **50점 미만**: 회피 (Avoid)
        """)

# 데이터 로딩
@st.cache_data(ttl=3600, show_spinner=True)
def load_and_process_data():
    """데이터를 로드하고 처리합니다."""
    try:
        data_dict = get_all_sector_data()
        
        if not data_dict or not validate_data(data_dict):
            logger.warning("데이터 검증 실패")
            return None, None, None
        
        benchmark_df = data_dict.get(BENCHMARK)
        if benchmark_df is None or benchmark_df.empty:
            logger.warning("벤치마크 데이터 없음")
            return None, None, None
        
        # 각 섹터별 지표 및 점수 계산
        sector_scores = {}
        
        for ticker in SECTORS.keys():
            if ticker not in data_dict:
                logger.warning(f"{ticker} 데이터 없음")
                continue
            
            sector_df = data_dict[ticker]
            
            if sector_df.empty:
                logger.warning(f"{ticker} 데이터프레임이 비어있음")
                continue
            
            try:
                # 지표 계산
                indicators = calculate_all_indicators(sector_df, benchmark_df)
                
                # 점수 계산
                score_data = calculate_total_score(indicators)
                score_data['indicators'] = indicators
                
                sector_scores[ticker] = score_data
                
            except Exception as e:
                logger.error(f"{ticker} 처리 중 오류: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
                continue
        
        if not sector_scores:
            logger.warning("처리된 섹터가 없음")
            return None, None, None
        
        return sector_scores, benchmark_df, data_dict
        
    except Exception as e:
        logger.error(f"데이터 로딩 중 오류: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None, None, None

# 메인 로직
# 캐시된 데이터가 있으면 빠르게 로드, 없으면 수집
try:
    sector_scores, benchmark_df, data_dict = load_and_process_data()
except Exception as e:
    st.error(f"데이터 수집 중 오류가 발생했습니다: {str(e)}")
    st.info("💡 **해결 방법**:")
    st.info("1. 네트워크 연결을 확인하세요")
    st.info("2. 사이드바의 '데이터 새로고침' 버튼을 클릭하세요")
    st.info("3. 잠시 후 다시 시도하세요")
    st.stop()

if sector_scores is None or benchmark_df is None or data_dict is None:
    st.error("데이터 수집에 실패했습니다. 잠시 후 다시 시도해주세요.")
    st.info("💡 **팁**: 네트워크 연결을 확인하거나, 사이드바에서 '데이터 새로고침' 버튼을 클릭해보세요.")
    st.stop()

# 마지막 업데이트 시간 표시
st.info(f"📅 마지막 업데이트: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# 필터링
filtered_scores = {
    ticker: score_data 
    for ticker, score_data in sector_scores.items()
    if score_data.get('total_score', 0) >= min_score
}

if not filtered_scores:
    st.warning("필터 조건에 맞는 섹터가 없습니다.")
    st.stop()

# 섹션 1: 섹터 히트맵
st.header("📊 섹터 히트맵")
st.markdown("각 섹터의 종합 점수를 색상으로 표시합니다.")

if display_mode == "그리드":
    heatmap_fig = create_sector_heatmap(filtered_scores)
    st.plotly_chart(heatmap_fig, use_container_width=True)
else:
    # 리스트 모드: 카드 형태로 표시
    cols = st.columns(3)
    col_idx = 0
    
    for ticker, score_data in sorted(
        filtered_scores.items(),
        key=lambda x: x[1].get('total_score', 0),
        reverse=True
    ):
        sector_name = SECTORS[ticker]['name']
        total_score = score_data.get('total_score', 0)
        signal = get_signal_korean(score_data.get('signal', 'Hold'))
        indicators = score_data.get('indicators', {})
        roc_1m = indicators.get('roc_20d', np.nan)
        
        # 색상 결정
        if total_score >= 80:
            color = COLOR_SCHEME['strong_buy']
        elif total_score >= 65:
            color = COLOR_SCHEME['buy']
        elif total_score >= 50:
            color = COLOR_SCHEME['hold']
        else:
            color = COLOR_SCHEME['avoid']
        
        # 주요 종목 정보 (상위 3개)
        top_holdings = SECTORS[ticker].get('top_holdings', [])
        top_3_holdings = ', '.join(top_holdings[:3]) if top_holdings else 'N/A'
        
        with cols[col_idx]:
            st.markdown(
                f"""
                <div style="
                    background-color: {color};
                    padding: 20px;
                    border-radius: 10px;
                    margin-bottom: 10px;
                    color: white;
                    text-align: center;
                ">
                    <h3>{sector_name}</h3>
                    <p><strong>{ticker}</strong></p>
                    <h2>{total_score:.1f}점</h2>
                    <p>{signal}</p>
                    <p>1M 수익률: {roc_1m:.2f}%</p>
                    <p style="font-size: 0.85em; margin-top: 10px; opacity: 0.9;">
                        주요 종목: {top_3_holdings}
                    </p>
                </div>
                """,
                unsafe_allow_html=True
            )
        
        col_idx = (col_idx + 1) % 3

st.markdown("---")

# 섹션 2: 섹터 순위표
st.header("📈 섹터 순위표")

# 정렬 기준 매핑
sort_mapping = {
    "종합점수": "total_score",
    "모멘텀점수": "momentum_score",
    "트렌드점수": "trend_score",
    "변동성점수": "volatility_score",
    "기술적점수": "technical_score",
    "1M수익률": "roc_20d"
}

sort_key = sort_mapping.get(sort_column, "total_score")

# 순위표 생성
ranking_df = create_ranking_table(filtered_scores, sort_by=sort_key, ascending=sort_ascending)

if not ranking_df.empty:
    # 스타일링 적용
    def color_score(val):
        if pd.isna(val):
            return ''
        if val >= 80:
            return f'background-color: {COLOR_SCHEME["strong_buy"]}; color: white'
        elif val >= 65:
            return f'background-color: {COLOR_SCHEME["buy"]}; color: white'
        elif val >= 50:
            return f'background-color: {COLOR_SCHEME["hold"]}; color: black'
        else:
            return f'background-color: {COLOR_SCHEME["avoid"]}; color: white'
    
    styled_df = ranking_df.style.applymap(
        color_score,
        subset=['종합점수']
    )
    
    st.dataframe(styled_df, use_container_width=True, height=400)
    
    # CSV 내보내기
    csv = ranking_df.to_csv(index=False, encoding='utf-8-sig')
    st.download_button(
        label="📥 CSV 내보내기",
        data=csv,
        file_name=f"sector_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv"
    )

st.markdown("---")

# 섹션 3: 섹터 상세 분석
st.header("🔍 섹터 상세 분석")

# 섹터 선택
selected_ticker = st.selectbox(
    "분석할 섹터 선택",
    options=list(filtered_scores.keys()),
    format_func=lambda x: f"{SECTORS[x]['name']} ({x})"
)

if selected_ticker and selected_ticker in sector_scores:
    score_data = sector_scores[selected_ticker]
    indicators = score_data.get('indicators', {})
    sector_name = SECTORS[selected_ticker]['name']
    
    # 상세 정보 요약
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("종합 점수", f"{score_data.get('total_score', 0):.1f}점")
    
    with col2:
        signal = get_signal_korean(score_data.get('signal', 'Hold'))
        st.metric("진입 신호", signal)
    
    with col3:
        roc_1m = indicators.get('roc_20d', np.nan)
        st.metric("1개월 수익률", f"{roc_1m:.2f}%" if not pd.isna(roc_1m) else "N/A")
    
    with col4:
        current_price = indicators.get('current_price', np.nan)
        st.metric("현재가", f"${current_price:.2f}" if not pd.isna(current_price) else "N/A")
    
    st.markdown("---")
    
    # 점수 구성
    st.subheader("점수 구성")
    col1, col2 = st.columns(2)
    
    with col1:
        score_details = pd.DataFrame({
            '항목': ['모멘텀', '트렌드', '변동성', '기술적'],
            '점수': [
                score_data.get('momentum_score', 0),
                score_data.get('trend_score', 0),
                score_data.get('volatility_score', 0),
                score_data.get('technical_score', 0)
            ],
            '만점': [30, 30, 20, 20]
        })
        
        st.dataframe(score_details, use_container_width=True, hide_index=True)
    
    with col2:
        # 평균 점수 계산
        avg_scores = {
            'momentum_score': np.mean([s.get('momentum_score', 0) for s in sector_scores.values()]),
            'trend_score': np.mean([s.get('trend_score', 0) for s in sector_scores.values()]),
            'volatility_score': np.mean([s.get('volatility_score', 0) for s in sector_scores.values()]),
            'technical_score': np.mean([s.get('technical_score', 0) for s in sector_scores.values()])
        }
        
        radar_fig = create_radar_chart(score_data, avg_scores)
        st.plotly_chart(radar_fig, use_container_width=True)
        
        # 레이더 차트 해석 가이드
        with st.expander("📖 레이더 차트 해석 가이드", expanded=False):
            st.markdown("""
            ### 레이더 차트 해석 방법
            
            **축(카테고리) 의미:**
            - **모멘텀** (30점 만점): 상대강도, 거래량 트렌드, 골든크로스 등
            - **트렌드** (30점 만점): 1개월/3개월/6개월 수익률(ROC)
            - **변동성** (20점 만점): 20일 변동성 (낮을수록 높은 점수)
            - **기술적** (20점 만점): 50일/200일 이동평균선 위/아래 여부
            
            **값의 의미:**
            - 각 값은 **만점 대비 비율(%)**로 표시됩니다
            - 예: 모멘텀 20점 → 20/30 × 100 = **66.7%**
            - 0% = 최저, 100% = 만점
            
            **비교 해석:**
            - **파란색 (현재 섹터)**: 선택한 섹터의 점수
            - **빨간색 (전체 평균)**: 11개 섹터의 평균 점수
            
            **투자 판단:**
            - ✅ **현재 섹터 > 전체 평균**: 해당 지표에서 평균보다 **강함** (강점)
            - ⚠️ **현재 섹터 < 전체 평균**: 해당 지표에서 평균보다 **약함** (약점 또는 개선 여지)
            - 📈 **전체적으로 파란색이 빨간색보다 크면**: 평균보다 **우수한 섹터**
            
            **실전 활용:**
            - 모멘텀과 기술적 지표가 평균보다 크면 → **단기적으로 강세**
            - 트렌드가 평균보다 크면 → **중장기 추세가 양호**
            - 변동성이 평균보다 크면 → **리스크가 낮음** (안정적)
            """)
    
    st.markdown("---")
    
    # 가격 추이 및 차트 분석
    st.subheader("📈 가격 추이 및 차트 분석")
    
    # 3년 데이터 가져오기
    from modules.sector.data_loader import load_sector_data
    from datetime import datetime, timedelta
    
    try:
        # 3년 데이터 수집
        with st.spinner("3년 가격 데이터를 불러오는 중..."):
            sector_data_3y = load_sector_data(
                [selected_ticker],
                period_years=3,
                force_refresh=False
            )
        
        if selected_ticker in sector_data_3y and not sector_data_3y[selected_ticker].empty:
            sector_df_3y = sector_data_3y[selected_ticker]
            
            # 데이터 확인 및 디버깅
            if len(sector_df_3y) > 0:
                # 날짜 인덱스 확인
                if isinstance(sector_df_3y.index, pd.DatetimeIndex):
                    start_date_str = sector_df_3y.index[0].strftime('%Y-%m-%d')
                    end_date_str = sector_df_3y.index[-1].strftime('%Y-%m-%d')
                    st.info(f"📊 데이터 기간: {len(sector_df_3y)}일 ({start_date_str} ~ {end_date_str})")
                else:
                    st.info(f"📊 데이터 기간: {len(sector_df_3y)}일")
                
                # 가격 차트 생성
                price_chart = create_price_chart(sector_df_3y, selected_ticker, show_volume=True)
                
                # 빈 차트인지 확인
                if price_chart and len(price_chart.data) > 0:
                    st.plotly_chart(price_chart, use_container_width=True)
                else:
                    st.warning("차트 데이터가 없습니다. 기존 데이터를 사용합니다.")
                    # 기존 데이터로 차트 생성 시도
                    if selected_ticker in data_dict and not data_dict[selected_ticker].empty:
                        price_chart = create_price_chart(data_dict[selected_ticker], selected_ticker, show_volume=True)
                        if price_chart and len(price_chart.data) > 0:
                            st.plotly_chart(price_chart, use_container_width=True)
                        else:
                            st.error("차트를 생성할 수 없습니다.")
                    else:
                        st.error("사용 가능한 데이터가 없습니다.")
            else:
                st.warning("3년 데이터가 비어있습니다.")
            
            # 주요 이평선 지표 표시
            st.markdown("### 주요 이평선 지표")
            
            # 이평선 계산
            close_prices = sector_df_3y['close'].sort_index()
            
            # 다양한 기간의 이평선 계산
            ma_periods = {
                '20일': 20,
                '50일': 50,
                '100일': 100,
                '200일': 200
            }
            
            ma_data = []
            current_price = close_prices.iloc[-1] if len(close_prices) > 0 else 0
            
            for ma_name, period in ma_periods.items():
                if len(close_prices) >= period:
                    ma_value = close_prices.rolling(window=period).mean().iloc[-1]
                    diff = current_price - ma_value
                    diff_pct = (diff / ma_value * 100) if ma_value > 0 else 0
                    
                    ma_data.append({
                        '이평선': ma_name,
                        '값': f"${ma_value:.2f}",
                        '현재가 대비': f"${diff:+.2f}",
                        '변동률': f"{diff_pct:+.2f}%",
                        '위치': '위' if diff > 0 else '아래'
                    })
            
            if ma_data:
                ma_df = pd.DataFrame(ma_data)
                
                # 색상 스타일링
                def style_ma(row):
                    if row['위치'] == '위':
                        return ['background-color: #d4edda'] * len(row)
                    else:
                        return ['background-color: #f8d7da'] * len(row)
                
                styled_ma_df = ma_df.style.apply(style_ma, axis=1)
                st.dataframe(styled_ma_df, use_container_width=True, hide_index=True)
            
            # 추가 기술적 지표
            st.markdown("### 추가 기술적 지표")
            
            tech_indicators = []
            
            # 52주 고점/저점
            if len(close_prices) >= 252:
                high_52w = close_prices.tail(252).max()
                low_52w = close_prices.tail(252).min()
                current_to_high = (current_price / high_52w - 1) * 100 if high_52w > 0 else 0
                current_to_low = (current_price / low_52w - 1) * 100 if low_52w > 0 else 0
                
                tech_indicators.append({
                    '지표': '52주 고점',
                    '값': f"${high_52w:.2f}",
                    '현재가 대비': f"{current_to_high:.2f}%"
                })
                tech_indicators.append({
                    '지표': '52주 저점',
                    '값': f"${low_52w:.2f}",
                    '현재가 대비': f"{current_to_low:.2f}%"
                })
            
            # 변동성 (20일)
            if len(close_prices) >= 20:
                returns = close_prices.pct_change().tail(20)
                volatility = returns.std() * np.sqrt(252) * 100
                tech_indicators.append({
                    '지표': '20일 변동성 (연율화)',
                    '값': f"{volatility:.2f}%",
                    '현재가 대비': '-'
                })
            
            # 최근 수익률
            if len(close_prices) >= 5:
                week_return = (close_prices.iloc[-1] / close_prices.iloc[-5] - 1) * 100
                tech_indicators.append({
                    '지표': '5일 수익률',
                    '값': f"{week_return:+.2f}%",
                    '현재가 대비': '-'
                })
            
            if tech_indicators:
                tech_df = pd.DataFrame(tech_indicators)
                st.dataframe(tech_df, use_container_width=True, hide_index=True)
        else:
            st.warning("3년 가격 데이터를 불러올 수 없습니다.")
    except Exception as e:
        logger.error(f"가격 추이 데이터 로딩 실패: {str(e)}")
        st.warning("가격 추이 데이터를 불러오는 중 오류가 발생했습니다.")
    
    st.markdown("---")
    
    # 주요 종목 정보 (지연 로딩)
    st.subheader("📋 주요 구성 종목")
    
    top_holdings = SECTORS[selected_ticker].get('top_holdings', [])
    
    if top_holdings:
        # 기본 정보만 먼저 표시
        st.markdown(f"**주요 종목 티커**: {', '.join(top_holdings[:10])}")
        
        # 상세 정보는 expander로 숨기고 필요시에만 로드
        with st.expander("📊 상세 종목 정보 보기 (클릭 시 로드)", expanded=False):
            # ETF 보유 종목 수 정보 가져오기 시도
            from modules.sector.data_loader import get_etf_holdings_info, get_etf_holdings_with_weights
            
            try:
                holdings_info = get_etf_holdings_info(selected_ticker)
                holdings_count = holdings_info.get('holdings_count', 0)
                
                if holdings_count > 0:
                    st.info(f"**총 보유 종목 수**: {holdings_count}개")
            except:
                pass
            
            # 상세 종목 정보 가져오기 (최대 10개만)
            with st.spinner("주요 종목 정보를 불러오는 중... (최대 30초 소요)"):
                holdings_df = get_etf_holdings_with_weights(selected_ticker, top_n=min(10, len(top_holdings)))
            
            if not holdings_df.empty:
                # 비중 정보 안내
                st.info("💡 **참고**: 비중 정보는 추정치이며, 실제 ETF 보유 비중과 다를 수 있습니다. 정확한 비중은 ETF 발행사 공시 자료를 참고하세요.")
                
                # 종목별 상세 정보 표시
                st.markdown("### 상위 주요 종목 상세 정보")
                
                for idx, row in holdings_df.iterrows():
                    yahoo_link = f"https://finance.yahoo.com/quote/{row['ticker']}"
                    
                    with st.expander(f"#{int(row['rank'])} {row['name']} ({row['ticker']}) - 비중: {row['weight']:.2f}%", expanded=(idx < 3)):
                        col1, col2 = st.columns([2, 1])
                        
                        with col1:
                            st.markdown(f"**회사명**: {row['name']}")
                            st.markdown(f"**티커**: {row['ticker']}")
                            st.markdown(f"**섹터**: {row['sector']}")
                            st.markdown(f"**산업**: {row['industry']}")
                            
                            # 주가 정보 (Yahoo Finance 링크 포함)
                            if row['current_price'] > 0:
                                st.markdown(f"**현재 주가**: ${row['current_price']:.2f}")
                                st.markdown(f"🔗 [Yahoo Finance에서 상세 정보 보기]({yahoo_link})")
                            else:
                                st.markdown(f"**주가 정보**: [Yahoo Finance에서 확인]({yahoo_link})")
                            
                            st.markdown(f"**ETF 내 비중**: {row['weight']:.2f}%")
                        
                        with col2:
                            # 간단한 사업 설명
                            st.markdown("**사업 설명:**")
                            st.info(row['description'])
                
                # 요약 테이블
                st.markdown("### 종목 요약 테이블")
                
                # 테이블용 데이터 준비
                summary_data = []
                for idx, row in holdings_df.iterrows():
                    yahoo_link = f"https://finance.yahoo.com/quote/{row['ticker']}"
                    price_text = f"${row['current_price']:.2f}" if row['current_price'] > 0 else "N/A"
                    
                    summary_data.append({
                        '순위': int(row['rank']),
                        '티커': row['ticker'],
                        '회사명': row['name'],
                        '비중 (%)': f"{row['weight']:.2f}",
                        '주가': price_text,
                        '링크': f"[Yahoo Finance]({yahoo_link})"
                    })
                
                summary_df = pd.DataFrame(summary_data)
                st.dataframe(
                    summary_df,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "링크": st.column_config.LinkColumn("Yahoo Finance 링크")
                    }
                )
            else:
                # 기본 정보만 표시
                st.markdown("**상위 주요 종목:**")
                cols = st.columns(2)
                
                for idx, ticker_symbol in enumerate(top_holdings[:10]):
                    col_idx = idx % 2
                    with cols[col_idx]:
                        yahoo_link = f"https://finance.yahoo.com/quote/{ticker_symbol}"
                        st.markdown(f"- **{ticker_symbol}** - [Yahoo Finance]({yahoo_link})")
    else:
        st.info("주요 종목 정보를 가져올 수 없습니다.")
else:
    st.error(f"{selected_ticker} 데이터를 불러올 수 없습니다.")

