# 코인 선물 예측 모델 대시보드 (Streamlit)

Streamlit으로 구현된 코인 선물 예측 모델 대시보드입니다.

## 설치 및 실행

1. Python이 설치되어 있는지 확인:
```bash
python --version
```

2. 필요한 패키지 설치:
```bash
pip install -r requirements.txt
```

3. 프로그램 실행:
```bash
streamlit run app.py
```

브라우저가 자동으로 열리고 `http://localhost:8501`에서 대시보드를 확인할 수 있습니다.

## 주요 기능

- **모델별 3개월 수익률 요약**: 메인 화면에서 각 모델의 성과 확인
- **상세 분석**: 모델 클릭 시 1M, 3M, 6M, 1Y, 2Y, 3Y 기간별 성과 지표 확인
- **코인별 시그널**: 7종 코인(BTC, ETH, ADA, DOT, XRP, SOL, DOGE)의 오늘의 시그널 및 차트
- **시그널 히스토리**: 지난 7일간의 시그널 변화 추적
- **필터링**: 모델별 필터, 활성 시그널만 보기 기능
- **인터랙티브 차트**: Plotly를 사용한 동적 차트

## 파일 구조

- `app.py`: 메인 Streamlit 애플리케이션
- `data_generator.py`: 목 데이터 생성 모듈
- `requirements.txt`: 필요한 Python 패키지 목록

