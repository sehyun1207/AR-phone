# AR Phone Interface 설치 가이드

## 📋 사전 준비사항

### 하드웨어 체크리스트
- [ ] 라즈베리파이 4 (4GB RAM 권장)
- [ ] MicroSD 카드 (32GB 이상, Class 10)
- [ ] Pi Camera v2 또는 USB 웹캠
- [ ] 7인치 LCD 디스플레이 (800x480 이상)
- [ ] 반투명 거울 (AR 효과용)
- [ ] 불투명 렌즈 (화면 투영용)
- [ ] 전원 어댑터 (5V 3A)
- [ ] 케이스 및 쿨링 팬 (선택사항)

### 소프트웨어 체크리스트
- [ ] 라즈베리파이 OS (64-bit) 이미지
- [ ] Raspberry Pi Imager
- [ ] Android 디바이스 (USB 디버깅 활성화)
- [ ] 또는 iOS 디바이스 (AirPlay 지원)

## 🚀 단계별 설치

### 1단계: 라즈베리파이 OS 설치

1. **Raspberry Pi Imager 다운로드**
   - [공식 사이트](https://www.raspberrypi.org/downloads/)에서 다운로드

2. **OS 이미지 플래시**
   ```bash
   # Raspberry Pi OS (64-bit) 선택
   # Advanced Options에서 SSH 활성화
   # WiFi 설정 (선택사항)
   ```

3. **MicroSD 카드 삽입 및 부팅**
   - 라즈베리파이에 MicroSD 카드 삽입
   - 전원 연결하여 부팅

### 2단계: 시스템 업데이트

```bash
# SSH로 연결 또는 직접 터미널 사용
ssh pi@[라즈베리파이_IP]

# 시스템 업데이트
sudo apt update && sudo apt upgrade -y

# 필수 패키지 설치
sudo apt install -y git curl wget
```

### 3단계: 프로젝트 다운로드

```bash
# 프로젝트 클론
git clone <repository-url>
cd ar_phone

# 또는 직접 다운로드
wget <project-zip-url>
unzip ar_phone.zip
cd ar_phone
```

### 4단계: 자동 설치 실행

```bash
# 설치 스크립트 실행 권한 부여
chmod +x setup.sh

# 자동 설치 실행
./setup.sh
```

### 5단계: 라즈베리파이 설정

```bash
# raspi-config 실행
sudo raspi-config

# 다음 항목들 활성화:
# - Interface Options > Camera > Enable
# - Interface Options > I2C > Enable  
# - Interface Options > SPI > Enable
# - Advanced Options > Memory Split > 128
```

### 6단계: 하드웨어 연결

1. **카메라 모듈 연결**
   ```bash
   # Pi Camera v2의 경우
   # CSI 포트에 카메라 케이블 연결
   
   # USB 웹캠의 경우
   # USB 포트에 연결
   ```

2. **LCD 디스플레이 연결**
   ```bash
   # GPIO 핀 연결 (LCD 모델에 따라 다름)
   # 일반적으로 I2C 또는 SPI 사용
   ```

3. **전원 연결 및 부팅**
   ```bash
   # 모든 연결 확인 후 전원 연결
   sudo reboot
   ```

## 🔧 수동 설치 (고급 사용자)

### Python 환경 설정

```bash
# Python 가상환경 생성
python3 -m venv ar_phone_env
source ar_phone_env/bin/activate

# pip 업그레이드
pip install --upgrade pip setuptools wheel
```

### 의존성 설치

```bash
# OpenCV 및 관련 라이브러리
sudo apt install -y \
    libopencv-dev \
    python3-opencv \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev

# Python 패키지 설치
pip install -r requirements.txt
```

### scrcpy 설치 (Android용)

```bash
# scrcpy 설치
sudo apt install -y scrcpy

# ADB 설치
sudo apt install -y android-tools-adb

# 권한 설정
sudo usermod -a -G plugdev $USER
```

## 📱 디바이스 연결 설정

### Android 디바이스

1. **개발자 옵션 활성화**
   - 설정 > 휴대전화 정보 > 빌드 번호 7번 탭

2. **USB 디버깅 활성화**
   - 설정 > 개발자 옵션 > USB 디버깅 ON

3. **디바이스 연결 테스트**
   ```bash
   # USB로 연결
   adb devices
   
   # WiFi 연결 설정
   adb tcpip 5555
   adb connect [디바이스_IP]:5555
   ```

### iOS 디바이스

1. **AirPlay 활성화**
   - 설정 > 화면 미러링 > AirPlay 활성화

2. **같은 네트워크 연결**
   - 라즈베리파이와 iOS 디바이스가 같은 WiFi에 연결

## 🧪 설치 확인

### 컴포넌트 테스트

```bash
# 가상환경 활성화
source ar_phone_env/bin/activate

# 테스트 실행
python test_components.py
```

### 수동 테스트

```bash
# 카메라 테스트
python -c "import cv2; cap = cv2.VideoCapture(0); print('Camera OK' if cap.isOpened() else 'Camera Failed')"

# MediaPipe 테스트
python -c "import mediapipe as mp; print('MediaPipe OK')"

# Pygame 테스트
python -c "import pygame; pygame.init(); print('Pygame OK')"
```

## ⚙️ 설정 파일 수정

`config.json` 파일을 환경에 맞게 수정:

```json
{
  "camera_index": 0,
  "display_mode": "lcd",
  "phone_platform": "android",
  "gesture_confidence_threshold": 0.7,
  "screen_width": 800,
  "screen_height": 600
}
```

## 🚀 첫 실행

```bash
# 가상환경 활성화
source ar_phone_env/bin/activate

# 프로그램 실행
python main.py

# 또는 실행 스크립트 사용
./run.sh
```

## 🔄 자동 시작 설정

```bash
# systemd 서비스 활성화
sudo systemctl enable ar_phone.service

# 서비스 시작
sudo systemctl start ar_phone.service

# 서비스 상태 확인
sudo systemctl status ar_phone.service
```

## 🛠️ 문제 해결

### 일반적인 문제들

1. **카메라 인식 실패**
   ```bash
   # 카메라 모듈 활성화 확인
   sudo raspi-config
   
   # 다른 카메라 인덱스 시도
   python main.py --camera 1
   ```

2. **권한 문제**
   ```bash
   # 사용자를 video 그룹에 추가
   sudo usermod -a -G video $USER
   
   # 재로그인 필요
   ```

3. **메모리 부족**
   ```bash
   # 스왑 파일 생성
   sudo dphys-swapfile swapoff
   sudo nano /etc/dphys-swapfile
   # CONF_SWAPSIZE=1024
   sudo dphys-swapfile setup
   sudo dphys-swapfile swapon
   ```

4. **성능 문제**
   ```bash
   # GPU 메모리 할당 증가
   sudo raspi-config
   # Advanced Options > Memory Split > 128
   
   # 오버클럭 설정
   sudo raspi-config
   # Advanced Options > Overclock > High
   ```

## 📞 지원

설치 중 문제가 발생하면:

1. 로그 파일 확인: `tail -f ar_phone.log`
2. GitHub Issues에 문제 보고
3. 커뮤니티 포럼에서 도움 요청

---

**참고**: 이 설치 가이드는 라즈베리파이 4 기준으로 작성되었습니다. 다른 모델의 경우 일부 설정이 다를 수 있습니다.

