# AR Phone Interface - Android 전용

라즈베리파이 4를 사용한 제스처 기반 AR Android 스마트폰 인터페이스

## 📱 프로젝트 개요

이 프로젝트는 라즈베리파이 4를 사용하여 손 제스처로 Android 스마트폰을 조작하는 AR(증강현실) 인터페이스를 구현합니다. 투명한 스마트폰 화면이 눈 앞에 떠 있는 것처럼 보이게 하고, 손 동작으로 직관적으로 조작할 수 있습니다.

## 🎯 주요 기능

- **실시간 Android 미러링**: scrcpy를 통한 고품질 화면 미러링
- **완전한 제어 기능**: 터치, 스와이프, 키 입력, 텍스트 입력 지원
- **손 제스처 인식**: MediaPipe 기반 정확한 손 동작 감지
- **AR 디스플레이**: LCD와 거울을 활용한 AR 효과
- **직관적 제어**: 자연스러운 손 동작으로 Android 스마트폰 조작

## 🛠️ 하드웨어 요구사항

### 필수 구성요소
- **라즈베리파이 4** (4GB RAM 권장)
- **카메라 모듈**: Pi Camera v2 또는 USB 웹캠
- **LCD 디스플레이**: 7인치 터치스크린 (800x480 이상)
- **거울**: 반투명 거울 (AR 효과용)
- **렌즈**: 불투명 렌즈 (화면 투영용)

### 선택적 구성요소
- **마이크**: 음성 명령용
- **스피커**: 피드백 사운드용
- **LED**: 상태 표시용

## 💻 소프트웨어 요구사항

- **OS**: 라즈베리파이 OS (64-bit)
- **Python**: 3.8 이상
- **Android**: scrcpy, ADB
- **Android 디바이스**: USB 디버깅 활성화 필요

## 🚀 설치 방법

### 1. 자동 설치 (권장)
```bash
# 저장소 클론
git clone <repository-url>
cd ar_phone

# 설치 스크립트 실행
chmod +x setup.sh
./setup.sh
```

### 2. 수동 설치
```bash
# 시스템 업데이트
sudo apt update && sudo apt upgrade -y

# 필수 패키지 설치
sudo apt install -y python3 python3-pip python3-venv opencv-python

# Python 가상환경 생성
python3 -m venv ar_phone_env
source ar_phone_env/bin/activate

# 의존성 설치
pip install -r requirements.txt

# scrcpy 설치 (Android용)
sudo apt install -y scrcpy adb
```

### 3. 라즈베리파이 설정
```bash
# 카메라 모듈 활성화
sudo raspi-config
# Interface Options > Camera > Enable

# I2C/SPI 활성화 (LCD용)
sudo raspi-config
# Interface Options > I2C > Enable
# Interface Options > SPI > Enable
```

## 🎮 제스처 컨트롤

| 제스처 | 동작 | 설명 |
|--------|------|------|
| 👆 **포인팅** | 마우스 커서 | 검지를 펴고 움직여 커서 이동 |
| ✊ **그랩** | 클릭/드래그 | 주먹을 쥐고 움직여 클릭 또는 드래그 |
| 👌 **핀치** | 줌 인/아웃 | 엄지와 검지로 핀치하여 줌 조절 |
| 👋 **흔들기** | 뒤로가기 | 손을 좌우로 흔들어 뒤로가기 |
| ✋ **손바닥** | 홈 버튼 | 손바닥을 보여 홈 화면으로 이동 |

## 🏗️ 프로젝트 구조

```
ar_phone/
├── main.py                    # 메인 애플리케이션
├── config.json               # 설정 파일
├── requirements.txt          # Python 의존성
├── setup.sh                 # 자동 설치 스크립트
├── run.sh                   # 실행 스크립트
├── test_components.py       # 컴포넌트 테스트
├── phone_mirroring/         # Android 미러링 모듈
│   ├── __init__.py
│   └── android_mirror.py    # Android scrcpy 미러링
├── hand_tracking/           # 손 제스처 인식 모듈
│   ├── __init__.py
│   └── gesture_detector.py  # MediaPipe 기반 제스처 감지
├── gesture_controls/        # 제스처 컨트롤 변환
│   ├── __init__.py
│   └── gesture_mapper.py    # 제스처를 스마트폰 조작으로 변환
├── display_manager/         # 디스플레이 관리
│   ├── __init__.py
│   └── ar_display.py        # AR 디스플레이 및 오버레이
└── utils/                   # 유틸리티 함수들
    ├── __init__.py
    ├── config.py            # 설정 관리
    └── logger.py            # 로깅 시스템
```

## 🎯 사용법

### 기본 실행
```bash
# 가상환경 활성화
source ar_phone_env/bin/activate

# 기본 실행
python main.py

# 또는 실행 스크립트 사용
./run.sh
```

### 고급 옵션
```bash
# 특정 카메라 사용
python main.py --camera 1

# 특정 Android 디바이스 지정 (여러 디바이스 연결 시)
python main.py --device-id [디바이스_ID]

# LCD 디스플레이 모드
python main.py --display lcd

# 디버그 모드
python main.py --debug
```

### Android 디바이스 연결
```bash
# 1. Android 디바이스에서 USB 디버깅 활성화
# 설정 > 개발자 옵션 > USB 디버깅 활성화

# 2. 디바이스 연결 확인
adb devices

# 3. WiFi 연결 설정 (선택사항)
adb tcpip 5555
adb connect [디바이스_IP]:5555

# 4. scrcpy 설치 확인
scrcpy --version
```

### 라즈베리파이 OS에서 scrcpy 설치 문제 해결

라즈베리파이 OS에서는 기본 패키지 저장소에 scrcpy가 없어서 설치 오류가 발생할 수 있습니다.

#### 자동 설치 (권장)
```bash
# 전용 설치 스크립트 실행
chmod +x install_scrcpy.sh
./install_scrcpy.sh
```

#### 수동 설치
```bash
# 1. 의존성 설치
sudo apt update
sudo apt install -y ffmpeg libsdl2-2.0-0 libavcodec58 libavformat58 libavutil56 libswresample3 libswscale5 libusb-1.0-0 wget tar

# 2. scrcpy 다운로드 및 설치
cd /tmp
wget https://github.com/Genymobile/scrcpy/releases/download/v2.7/scrcpy-linux-v2.7.tar.gz
tar -xzf scrcpy-linux-v2.7.tar.gz
cd scrcpy-linux-v2.7
sudo cp scrcpy /usr/local/bin/
sudo cp scrcpy-server /usr/local/bin/
sudo chmod +x /usr/local/bin/scrcpy
sudo chmod +x /usr/local/bin/scrcpy-server

# 3. 설치 확인
scrcpy --version
```

#### 대안: snap을 통한 설치
```bash
# snap 설치 (없는 경우)
sudo apt install -y snapd
sudo systemctl enable --now snapd.socket
sudo ln -s /var/lib/snapd/snap /snap

# scrcpy 설치
sudo snap install scrcpy
```

## ⚙️ 설정

`config.json` 파일에서 다양한 설정을 조정할 수 있습니다:

```json
{
  "camera_index": 0,
  "display_mode": "pygame",
  "android_device_id": null,
  "scrcpy_max_fps": 30,
  "scrcpy_bit_rate": "2M",
  "scrcpy_no_audio": true,
  "gesture_confidence_threshold": 0.7,
  "gesture_hold_time": 0.5,
  "show_gesture_info": true,
  "overlay_transparency": 0.8
}
```

## 🧪 테스트

컴포넌트별 테스트를 실행할 수 있습니다:

```bash
# 전체 컴포넌트 테스트
python test_components.py

# Android 제어 기능 테스트
python test_android_control.py

# 특정 테스트만 실행
python test_android_control.py --test adb
python test_android_control.py --test scrcpy
python test_android_control.py --test mirror

# Android 디바이스 연결 테스트
adb devices

# scrcpy 테스트
scrcpy --no-audio --max-fps=30
```

## 🔧 문제 해결

### 일반적인 문제들

1. **카메라가 인식되지 않음**
   ```bash
   # 카메라 모듈 활성화 확인
   sudo raspi-config
   # USB 웹캠인 경우 다른 인덱스 시도
   python main.py --camera 1
   ```

2. **Android 디바이스 연결 실패**
   ```bash
   # USB 디버깅 활성화 확인
   adb devices
   # 드라이버 재설치
   sudo apt reinstall android-tools-adb
   ```

3. **scrcpy 설치 실패 (라즈베리파이 OS)**
   ```bash
   # 전용 설치 스크립트 사용
   chmod +x install_scrcpy.sh
   ./install_scrcpy.sh
   
   # 또는 수동 설치
   cd /tmp
   wget https://github.com/Genymobile/scrcpy/releases/download/v2.7/scrcpy-linux-v2.7.tar.gz
   tar -xzf scrcpy-linux-v2.7.tar.gz
   cd scrcpy-linux-v2.7
   sudo cp scrcpy /usr/local/bin/
   sudo cp scrcpy-server /usr/local/bin/
   sudo chmod +x /usr/local/bin/scrcpy
   sudo chmod +x /usr/local/bin/scrcpy-server
   ```

4. **Android 디바이스 연결 실패**
   ```bash
   # USB 디버깅 활성화 확인
   adb devices
   
   # 드라이버 재설치
   sudo apt reinstall android-tools-adb
   
   # Android 디바이스 상태 확인 (런타임에서 A 키)
   ```

5. **성능 문제**
   ```bash
   # GPU 메모리 할당 증가
   sudo raspi-config
   # Advanced Options > Memory Split > 128
   ```

## 📱 Android 제어 기능

### 지원하는 제어 방법

1. **scrcpy 미러링** (기본)
   - 고품질 화면 미러링
   - 실시간 터치 및 키 제어
   - WiFi 및 USB 연결 지원

2. **ADB 명령어 제어**
   - 터치, 스와이프, 키 입력
   - 텍스트 입력 지원
   - 다중 디바이스 지원

### 런타임 제어

- **A 키**: Android 디바이스 상태 정보 표시
- **R 키**: Android 미러링 재시작
- **F 키**: 제스처 정보 토글
- **T 키**: 투명도 조절

## 📊 성능 최적화

- **GPU 메모리**: 128MB 이상 할당
- **카메라 해상도**: 640x480 권장
- **프레임 레이트**: 30 FPS
- **제스처 임계값**: 0.7 이상

## 🤝 기여하기

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

## 📞 지원

문제가 발생하거나 질문이 있으시면 이슈를 생성해 주세요.

---

**주의**: 이 프로젝트는 교육 및 연구 목적으로 제작되었습니다. 상업적 사용 시 관련 라이선스를 확인하시기 바랍니다.
