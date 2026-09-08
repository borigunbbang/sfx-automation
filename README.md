# AutoSFX (MVP, 진행 중)

방송 예능 자막 효과에 맞춰 효과음을 자동으로 찾아 매칭하는 프로그램. 기획/설계는 [PRD.md](./PRD.md)와 [TECH_SPEC.md](./TECH_SPEC.md) 참고.

## 현재 상태 (M1~M3 프로토타입)
- `src/event_detection.py`: 자막 이벤트 감지 (프레임 차분, M1)
- `src/reference_matching.py`: 참고 이미지 매칭 (M2, 단순 버전 — 정확도 튜닝 전)
- `src/sfx_matching.py`: 효과음 폴더 매칭 (M3)
- `scripts/run_pipeline.py`: 전체 파이프라인 실행 (영상 → CSV)

## ⚠️ 이 저장소에 포함되지 않은 것 (저작권 문제로 제외)
아래 항목들은 테스트에 사용한 실제 방송 영상/효과음이라 `.gitignore`로 제외되어 있습니다. 직접 재현하려면 본인 소유(또는 라이선스 보유)의 파일로 아래 위치에 채워 넣으세요.

- `data/` — 영상에서 추출한 프레임 스크린샷, 파이프라인 결과 CSV
- `eff sample/` — 효과음(.wav/.m4a) 라이브러리
- `references/*.png` — 참고 이미지(자막 스타일 캡처). `references/references.yaml`은 설정 파일이라 포함되어 있음

## 실행 방법
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
`scripts/run_pipeline.py` 상단의 `VIDEO_PATH`를 본인 영상 경로로 바꾸고, `references/references.yaml`에 본인 참고 이미지/효과음 폴더 경로를 등록한 뒤 실행:
```bash
python3 scripts/run_pipeline.py
```
