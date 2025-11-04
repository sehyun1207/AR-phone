
#!/bin/bash

# AR Phone Interface 설치 스크립트
# 라즈베리파이 4용 환경 설정

echo "AR Phone Interface 설치를 시작합니다..."

# 시스템 업데이트
echo "시스템 패키지 업데이트 중..."
sudo apt update && sudo apt upgrade -y

# 필수 패키지 설치
echo "필수 패키지 설치 중..."
sudo apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    libopencv-dev \
    python3-opencv \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libgstreamer1.0-0 \
    libgstreamer-plugins-base1.0-0 \
    libgtk-3-0 \
    libavcodec-dev \
    libavformat-dev \
    libswscale-dev \
    libv4l-dev \
    libxvidcore-dev \
    libx264-dev \
    libjpeg-dev \
    libpng-dev \
    libtiff-dev \
    libatlas-base-dev \
    gfortran \
    wget \
    git \
    cmake \
    build-essential

# Picamera2 설치 (라즈베리파이 카메라 모듈 지원)
echo "Picamera2 설치 중..."
sudo apt install -y python3-picamera2

# 카메라 모듈 활성화 확인
echo "카메라 모듈 활성화 확인 중..."
if ! grep -q "camera_auto_detect=1" /boot/config.txt; then
    echo "카메라 모듈을 활성화합니다..."
    echo "camera_auto_detect=1" | sudo tee -a /boot/config.txt
    echo "⚠️ 카메라 모듈이 활성화되었습니다. 재부팅이 필요할 수 있습니다."
fi

# pyenv 설치 및 Python 3.11 환경 구축
echo "pyenv 설치 확인 중..."
if ! command -v pyenv &> /dev/null; then
    echo "pyenv 설치 중..."
    # pyenv 의존성 설치
    sudo apt install -y make build-essential libssl-dev zlib1g-dev \
        libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm \
        libncursesw5-dev xz-utils tk-dev libxml2-dev libxmlsec1-dev \
        libffi-dev liblzma-dev
    
    # pyenv 설치
    curl https://pyenv.run | bash
    
    # 환경 변수 설정
    echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bashrc
    echo 'command -v pyenv >/dev/null || export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bashrc
    echo 'eval "$(pyenv init -)"' >> ~/.bashrc
    echo 'eval "$(pyenv virtualenv-init -)"' >> ~/.bashrc
    
    # 현재 세션에 환경 변수 적용
    export PYENV_ROOT="$HOME/.pyenv"
    export PATH="$PYENV_ROOT/bin:$PATH"
    eval "$(pyenv init -)"
    eval "$(pyenv virtualenv-init -)"
    
    echo "pyenv 설치 완료"
    echo "새 터미널을 열거나 'source ~/.bashrc'를 실행하여 pyenv를 사용하세요."
else
    # 기존 pyenv 환경 변수 로드
    export PYENV_ROOT="$HOME/.pyenv"
    export PATH="$PYENV_ROOT/bin:$PATH"
    eval "$(pyenv init -)"
    eval "$(pyenv virtualenv-init -)"
fi

# Python 3.11 설치
echo "Python 3.11 설치 확인 중..."
if ! pyenv versions | grep -q "3.11.10"; then
    echo "Python 3.11.10 설치 중..."
    pyenv install 3.11.10
else
    echo "Python 3.11.10이 이미 설치되어 있습니다."
fi

pyenv global 3.11.10
echo "Python 3.11 설치 완료: $(pyenv version)"

# Python 가상환경 생성 (pyenv 기반)
echo "Python 3.11 가상환경 생성 중..."
if ! pyenv versions | grep -q "ar_phone_env"; then
    pyenv virtualenv 3.11.10 ar_phone_env
    echo "ar_phone_env 가상환경이 생성되었습니다."
else
    echo "ar_phone_env 가상환경이 이미 존재합니다."
fi
pyenv activate ar_phone_env

# 가상환경 Python 버전 확인
echo "가상환경 Python 버전: $(python --version)"
echo "pyenv 버전: $(pyenv version)"

# Python 패키지 업그레이드
echo "Python 패키지 업그레이드 중..."
pip install --upgrade pip setuptools wheel

# Python 의존성 설치 (Python 3.11 호환 버전)
echo "Python 3.11 호환 의존성 설치 중..."
pip install -r requirements.txt

# ADB 설치 (Android 디버깅용)
echo "ADB 설치 중..."
sudo apt install -y android-tools-adb

# scrcpy 설치 (Android 미러링용) - 라즈베리파이 OS용
echo "scrcpy 설치 중..."
if ! command -v scrcpy &> /dev/null; then
    echo "scrcpy가 설치되지 않았습니다. 설치를 진행합니다..."
    
    # scrcpy 의존성 설치
    echo "scrcpy 의존성 설치 중..."
    sudo apt install -y \
        ffmpeg \
        libsdl2-2.0-0 \
        libavcodec58 \
        libavformat58 \
        libavutil56 \
        libswresample3 \
        libswscale5 \
        libusb-1.0-0 \
        libusb-1.0-0-dev \
        libavdevice58
    
    # scrcpy 바이너리 다운로드 (라즈베리파이 64비트용)
    echo "scrcpy 바이너리 다운로드 중..."
    cd /tmp
    
    # 최신 scrcpy 릴리스 확인 및 다운로드
    SCRCPY_VERSION="2.7"
    SCRCPY_URL="https://github.com/Genymobile/scrcpy/releases/download/v${SCRCPY_VERSION}/scrcpy-linux-v${SCRCPY_VERSION}.tar.gz"
    
    if wget -q --spider "$SCRCPY_URL"; then
        echo "scrcpy v${SCRCPY_VERSION} 다운로드 중..."
        wget -O scrcpy.tar.gz "$SCRCPY_URL"
        
        # 압축 해제
        tar -xzf scrcpy.tar.gz
        cd scrcpy-linux-v${SCRCPY_VERSION}
        
        # 바이너리 설치
        sudo cp scrcpy /usr/local/bin/
        sudo cp scrcpy-server /usr/local/bin/
        sudo chmod +x /usr/local/bin/scrcpy
        sudo chmod +x /usr/local/bin/scrcpy-server
        
        # 정리
        cd ..
        rm -rf scrcpy-linux-v${SCRCPY_VERSION} scrcpy.tar.gz
        
        echo "scrcpy 설치 완료"
        
        # 원래 디렉토리로 돌아가기
        cd - > /dev/null
    else
        echo "scrcpy 다운로드 실패. 대안 방법을 시도합니다..."
        
        # 원래 디렉토리로 돌아가기
        cd - > /dev/null
        
        # 대안: snap을 통한 설치 시도
        if command -v snap &> /dev/null; then
            echo "snap을 통한 scrcpy 설치 시도..."
            sudo snap install scrcpy
        else
            echo "snap이 설치되지 않았습니다. 수동 설치를 진행합니다..."
            
            # snap 설치
            sudo apt install -y snapd
            sudo systemctl enable --now snapd.socket
            sudo ln -s /var/lib/snapd/snap /snap
            
            # snap을 통한 scrcpy 설치
            sudo snap install scrcpy
        fi
    fi
    
    # 설치 확인
    if command -v scrcpy &> /dev/null; then
        echo "✅ scrcpy 설치 성공: $(scrcpy --version)"
    else
        echo "❌ scrcpy 설치 실패. 수동 설치가 필요할 수 있습니다."
        echo "수동 설치 방법:"
        echo "1. https://github.com/Genymobile/scrcpy/releases 에서 최신 릴리스 다운로드"
        echo "2. tar -xzf scrcpy-linux-*.tar.gz"
        echo "3. sudo cp scrcpy /usr/local/bin/"
        echo "4. sudo cp scrcpy-server /usr/local/bin/"
    fi
else
    echo "scrcpy가 이미 설치되어 있습니다: $(scrcpy --version)"
fi

# 라즈베리파이 카메라 모듈 활성화
echo "라즈베리파이 카메라 모듈 활성화 중..."
sudo raspi-config nonint do_camera 0

# I2C 활성화 (LCD 디스플레이용)
echo "I2C 활성화 중..."
sudo raspi-config nonint do_i2c 0

# SPI 활성화 (LCD 디스플레이용)
echo "SPI 활성화 중..."
sudo raspi-config nonint do_spi 0

# GPU 메모리 할당 증가
echo "GPU 메모리 할당 설정 중..."
sudo raspi-config nonint do_memory_split 128

# 부팅 시 자동 시작 설정
echo "부팅 시 자동 시작 설정 중..."
cat > ar_phone.service << EOF
[Unit]
Description=AR Phone Interface
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=$(pwd)
Environment=PATH=$HOME/.pyenv/versions/3.11.10/envs/ar_phone_env/bin:$HOME/.pyenv/shims:$HOME/.pyenv/bin:$PATH
Environment=PYENV_ROOT=$HOME/.pyenv
Environment=PYENV_VERSION=ar_phone_env
ExecStart=$HOME/.pyenv/versions/3.11.10/envs/ar_phone_env/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo mv ar_phone.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable ar_phone.service

# 권한 설정
echo "권한 설정 중..."
chmod +x main.py
chmod +x setup.sh

# 설정 파일 생성
echo "설정 파일 생성 중..."
cat > config.json << EOF
{
  "camera_index": 0,
  "camera_width": 640,
  "camera_height": 480,
  "camera_fps": 30,
  "display_mode": "lcd",
  "screen_width": 800,
  "screen_height": 600,
  "phone_platform": "auto",
  "gesture_confidence_threshold": 0.7,
  "gesture_hold_time": 0.5,
  "show_gesture_info": true,
  "overlay_transparency": 0.8,
  "log_level": "INFO",
  "debug": false
}
EOF

echo "설치가 완료되었습니다!"
echo ""
echo "사용법:"
echo "1. 가상환경 활성화: pyenv activate ar_phone_env"
echo "2. 프로그램 실행: python main.py"
echo "3. 자동 시작: sudo systemctl start ar_phone"
echo ""
echo "pyenv 명령어:"
echo "- 가상환경 목록: pyenv versions"
echo "- 가상환경 활성화: pyenv activate ar_phone_env"
echo "- 가상환경 비활성화: pyenv deactivate"
echo ""
echo "Android 디바이스 연결:"
echo "1. USB 디버깅 활성화"
echo "2. USB로 연결 후: adb devices"
echo "3. WiFi 연결: adb tcpip 5555 && adb connect [IP]:5555"
echo ""
echo "재부팅 후 자동으로 시작됩니다."
