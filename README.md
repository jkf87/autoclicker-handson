# 화면 인식 클릭 자동화 도구

이 프로그램은 화면의 특정 이미지를 인식하여 자동으로 클릭하는 작업을 자동화하는 도구입니다. 시나리오를 생성하고 저장하여 반복적인 작업을 자동화할 수 있습니다.

## 작동 원리

1. **이미지 인식**: OpenCV를 사용하여 화면에서 지정된 이미지를 찾습니다
2. **시나리오 기반**: 여러 단계의 작업을 시나리오로 저장하고 실행할 수 있습니다
3. **유연한 설정**: 각 액션마다 검색 영역, 대기 시간, 클릭 위치를 개별적으로 설정할 수 있습니다

## 환경 설정

### 시스템 요구사항
- Python 3.11 이상
- 메모리: 최소 4GB
- 디스크 공간: 최소 500MB
- 운영체제: Windows 10/11, macOS 10.15+, Ubuntu 20.04+

### Python 설치
1. [Python 공식 웹사이트](https://www.python.org/downloads/)에서 Python 3.11 이상 버전 다운로드
2. 설치 시 "Add Python to PATH" 옵션 체크

### 필요 라이브러리
```python
pip install opencv-python>=4.8.0
pip install pyautogui>=0.9.53
pip install pillow>=9.5.0
pip install keyboard>=0.13.5
pip install pywin32>=305  # Windows 전용
```


### 가상환경 설정 (선택사항)

```bash
python -m venv venv
source venv/bin/activate # Linux/Mac
venv\Scripts\activate # Windows
```


## 사용 방법

### GUI 프로그램 사용법

1. **시나리오 생성**
   - "새 시나리오" 버튼 클릭
   - 시나리오 이름 입력

2. **액션 추가**
   - "영역 설정 시작" 버튼 클릭
   - 마우스로 화면의 검색할 영역 드래그
   - 우클릭으로 클릭할 위치 지정
   - 대기 시간 설정 (기본값: 1초)

3. **시나리오 실행**
   - "시나리오 시작" 버튼 클릭
   - ESC 키로 실행 중단 가능

4. **시나리오 관리**
   - 저장된 시나리오 목록에서 선택
   - 시나리오 삭제/수정 가능

### 단축키
- `ESC`: 실행 중인 시나리오 중단
- `우클릭`: 클릭 위치 지정
- `드래그`: 검색 영역 설정

## Windows 실행 파일 사용

### 실행 파일 위치

`dist/ScreenClickSystem_Windows.exe`

### 실행 방법
1. `ScreenClickSystem_Windows.exe` 더블클릭
2. Windows 보안 경고 발생 시:
   - "추가 정보" 클릭
   - "실행" 선택

### 주의사항
- 관리자 권한이 필요할 수 있음
- 처음 실행 시 Windows Defender 경고가 표시될 수 있음
- 프로그램 실행 중 화면 설정 변경을 피해야 함

## 기술 스택
- Python 3.11
- OpenCV
- PyAutoGUI
- Tkinter (GUI)
- PyWin32 (Windows API)

## 라이선스
이 프로젝트는 MIT 라이선스를 따릅니다.

## 문제시 해결방법
1. **이미지 인식 실패**
   - 검색 영역을 더 좁게 설정
   - 대기 시간 증가 (최소 2초 권장)
   - 화면 해상도 확인
   - 모니터 배율 설정 확인 (100% 권장)

2. **권한 오류**
   - 관리자 권한으로 실행
   - 안티바이러스 예외 설정
   - Windows의 경우 UAC 설정 확인

3. **실행 파일 오류**
   - 최신 Windows 업데이트 설치
   - [Visual C++ 재배포 패키지](https://aka.ms/vs/17/release/vc_redist.x64.exe) 설치
   - .NET Framework 4.8 이상 설치