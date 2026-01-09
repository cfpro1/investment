import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from data_generator import (
    generate_models, generate_today_signals, generate_signal_history,
    generate_performance_data, generate_cumulative_returns,
    generate_model_positions, generate_signal_history_all,
    generate_price_data, generate_model_signal_history
)

# 페이지 설정
st.set_page_config(
    page_title="코인 선물 예측 모델 대시보드",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS 스타일
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 1rem;
    }
    .model-card {
        background-color: #f0f2f6;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 5px solid #1f77b4;
        margin-bottom: 1rem;
    }
    .positive {
        color: #00cc00;
        font-weight: bold;
    }
    .negative {
        color: #ff3333;
        font-weight: bold;
    }
    .signal-long {
        background-color: #10b981;
        color: white;
        padding: 0.3rem 0.8rem;
        border-radius: 5px;
        display: inline-block;
    }
    .signal-short {
        background-color: #ef4444;
        color: white;
        padding: 0.3rem 0.8rem;
        border-radius: 5px;
        display: inline-block;
    }
    .signal-stay {
        background-color: #6b7280;
        color: white;
        padding: 0.3rem 0.8rem;
        border-radius: 5px;
        display: inline-block;
    }
</style>
""", unsafe_allow_html=True)

# 세션 상태 초기화
if 'models' not in st.session_state:
    st.session_state.models = generate_models()
if 'signals' not in st.session_state:
    st.session_state.signals = generate_today_signals(st.session_state.models)

def format_percent(value):
    sign = '+' if value >= 0 else ''
    return f"{sign}{value:.2f}%"

def format_currency(value):
    return f"${value:,.2f}"

def get_signal_color(signal):
    if signal == 'Long':
        return '🟢'
    elif signal == 'Short':
        return '🔴'
    else:
        return '⚪'

# 메인 페이지
def main_dashboard():
    st.markdown('<div class="main-header">코인 선물 예측 모델 대시보드</div>', unsafe_allow_html=True)
    st.markdown(f"**날짜:** {datetime.now().strftime('%Y년 %m월 %d일')}")
    
    # 최고 성과 모델 찾기
    best_model = max(st.session_state.models, key=lambda x: x['performance3M'])
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown("### 모델별 3개월 수익률 요약")
    with col2:
        st.markdown(f"**최고 성과:** {best_model['name']} ({format_percent(best_model['performance3M'])})")
    
    # 모델 카드
    cols = st.columns(3)
    for idx, model in enumerate(st.session_state.models):
        with cols[idx]:
            perf = model['performance3M']
            color_class = 'positive' if perf >= 0 else 'negative'
            st.markdown(f"""
            <div class="model-card">
                <h3>{model['name']}</h3>
                <p style="font-size: 1.5rem;">
                    <span class="{color_class}">{format_percent(perf)}</span>
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button(f"{model['name']} 상세보기", key=f"btn_{model['id']}"):
                st.session_state.selected_model = model['id']
                st.rerun()
    
    st.divider()
    
    # 필터
    col1, col2 = st.columns(2)
    with col1:
        selected_model_filter = st.selectbox(
            "모델 필터",
            ['전체', 'Model G', 'Model A', 'Model B'],
            key='model_filter'
        )
    with col2:
        show_active_only = st.checkbox("활성 시그널만 보기 (Stay 제외)", key='active_only')
    
    # 새로고침 버튼
    if st.button("🔄 데이터 새로고침"):
        st.session_state.models = generate_models()
        st.session_state.signals = generate_today_signals(st.session_state.models)
        st.rerun()
    
    st.markdown("### 오늘의 시그널")
    
    # 시그널 테이블
    signals_df = st.session_state.signals.copy()
    
    # 필터 적용
    if show_active_only:
        signals_df = signals_df[
            (signals_df['modelG'] != 'Stay') |
            (signals_df['modelA'] != 'Stay') |
            (signals_df['modelB'] != 'Stay')
        ]
    
    for _, row in signals_df.iterrows():
        with st.expander(f"{row['coin']} - {format_currency(row['current_price'])}", expanded=False):
            # 오늘의 시그널 표시
            st.markdown("### 오늘의 시그널")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown("**Model G**")
                signal = row['modelG']
                st.markdown(f'<span class="signal-{signal.lower()}">{signal}</span>', unsafe_allow_html=True)
            
            with col2:
                st.markdown("**Model A**")
                signal = row['modelA']
                st.markdown(f'<span class="signal-{signal.lower()}">{signal}</span>', unsafe_allow_html=True)
            
            with col3:
                st.markdown("**Model B**")
                signal = row['modelB']
                st.markdown(f'<span class="signal-{signal.lower()}">{signal}</span>', unsafe_allow_html=True)
            
            st.divider()
            
            # 가격 차트
            st.markdown(f"### {row['coin']} 가격 차트 (30일)")
            price_data = generate_price_data(row['coin'], 30)
            fig = px.line(
                price_data,
                x='date',
                y='price',
                title=f"{row['coin']} 가격 차트 (30일)",
                labels={'price': '가격 (USD)', 'date': '날짜'}
            )
            fig.update_layout(height=400, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
            
            st.divider()
            
            # 각 모델별 7일간 시그널 히스토리를 하나의 테이블로 통합
            st.markdown("### 지난 7일간 모델별 시그널 히스토리")
            
            models = ['G', 'A', 'B']
            
            # 모든 모델의 히스토리 수집
            all_histories = {}
            for model_id in models:
                model_history = generate_model_signal_history(row['coin'], model_id, 7)
                all_histories[model_id] = model_history
            
            # 첫 번째 모델의 날짜와 가격을 기준으로 통합
            base_history = all_histories['G'].copy()
            base_history = base_history.rename(columns={'signal': 'Model G'})
            base_history = base_history.drop(columns=['coin', 'model'], errors='ignore')
            
            # 다른 모델들의 시그널 추가
            for model_id in ['A', 'B']:
                model_history = all_histories[model_id].copy()
                model_history = model_history.rename(columns={'signal': f'Model {model_id}'})
                base_history = base_history.merge(
                    model_history[['date', f'Model {model_id}']],
                    on='date',
                    how='left'
                )
            
            # 컬럼 순서 재정렬
            base_history = base_history[['date', 'price', 'Model G', 'Model A', 'Model B']]
            base_history = base_history.rename(columns={
                'date': '날짜',
                'price': '가격'
            })
            
            # 시그널을 색상으로 표시하기 위한 스타일링 함수
            def style_signal_columns(df):
                styles = pd.DataFrame('', index=df.index, columns=df.columns)
                for col in ['Model G', 'Model A', 'Model B']:
                    if col in df.columns:
                        styles[col] = df[col].apply(lambda x: 
                            'background-color: #10b981; color: white' if x == 'Long' else
                            'background-color: #ef4444; color: white' if x == 'Short' else
                            'background-color: #6b7280; color: white'
                        )
                return styles
            
            # 날짜 포맷팅
            base_history['날짜'] = pd.to_datetime(base_history['날짜']).dt.strftime('%Y-%m-%d')
            
            styled_df = base_history.style.format({
                '가격': '${:,.2f}'
            }).apply(style_signal_columns, axis=None)
            
            st.dataframe(
                styled_df,
                use_container_width=True,
                hide_index=True
            )

# 모델 상세 페이지
def model_detail_page(model_id: str):
    model = next((m for m in st.session_state.models if m['id'] == model_id), None)
    if not model:
        st.error("모델을 찾을 수 없습니다.")
        return
    
    if st.button("← 뒤로"):
        if 'selected_model' in st.session_state:
            del st.session_state.selected_model
        st.rerun()
    
    st.markdown(f'<div class="main-header">{model["name"]}</div>', unsafe_allow_html=True)
    
    # 성과 탭
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(['1M', '3M', '6M', '1Y', '2Y', '3Y'])
    
    tabs = {'1M': tab1, '3M': tab2, '6M': tab3, '1Y': tab4, '2Y': tab5, '3Y': tab6}
    
    for period, tab in tabs.items():
        with tab:
            perf_data = generate_performance_data(model_id)
            period_data = perf_data[perf_data['period'] == period].iloc[0]
            
            # 성과 지표
            col1, col2, col3, col4, col5 = st.columns(5)
            
            with col1:
                st.metric("총 수익률", format_percent(period_data['return']))
            with col2:
                st.metric("샤프 비율", f"{period_data['sharpeRatio']:.2f}")
            with col3:
                st.metric("승률", format_percent(period_data['winRate']))
            with col4:
                st.metric("최대 낙폭", format_percent(period_data['maxDrawdown']))
            with col5:
                st.metric("거래 횟수", int(period_data['numTrades']))
            
            # 누적 수익률 차트
            period_days = {'1M': 30, '3M': 90, '6M': 180, '1Y': 365, '2Y': 730, '3Y': 1095}[period]
            returns_data = generate_cumulative_returns(period_days)
            
            fig = px.line(
                returns_data,
                x='date',
                y='return',
                title=f"누적 수익률 차트 ({period})",
                labels={'return': '누적 수익률 (%)', 'date': '날짜'}
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
    
    st.divider()
    
    # 현재 포지션
    st.markdown("### 현재 포지션")
    positions = generate_model_positions(model_id)
    
    def color_pnl(val):
        color = 'green' if val >= 0 else 'red'
        return f'color: {color}'
    
    styled_positions = positions.style.format({
        'entryPrice': '${:,.2f}',
        'currentPrice': '${:,.2f}',
        'pnl': '{:.2f}%'
    }).applymap(color_pnl, subset=['pnl'])
    
    st.dataframe(
        styled_positions,
        use_container_width=True,
        hide_index=True
    )
    
    st.divider()
    
    # 시그널 히스토리
    st.markdown("### 시그널 히스토리")
    selected_coin = st.selectbox("코인 필터", ['전체'] + list(positions['coin'].unique()), key='coin_filter')
    
    history_all = generate_signal_history_all(20)
    if selected_coin != '전체':
        history_all = history_all[history_all['coin'] == selected_coin]
    
    st.dataframe(
        history_all.head(20).style.format({
            'price': '${:,.2f}',
            'date': lambda x: x.strftime('%Y-%m-%d')
        }),
        use_container_width=True,
        hide_index=True
    )

# 메인 로직
if 'selected_model' in st.session_state:
    model_detail_page(st.session_state.selected_model)
else:
    main_dashboard()

