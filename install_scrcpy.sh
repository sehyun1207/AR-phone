#!/bin/bash

# 라즈베리파이 OS용 scrcpy 설치 스크립트
# Android 미러링을 위한 scrcpy 설치

echo "라즈베리파이 OS용 scrcpy 설치를 시작합니다..."

# 시스템 업데이트
echo "시스템 패키지 업데이트 중..."
sudo apt update

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
    libavdevice58 \
    wget \
    tar

# 현재 scrcpy 설치 확인
if command -v scrcpy &> /dev/null; then
    echo "scrcpy가 이미 설치되어 있습니다: $(scrcpy --version)"
    read -p "재설치하시겠습니까? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "설치를 취소합니다."
        exit 0
    fi
fi

# 임시 디렉토리로 이동
cd /tmp

# scrcpy 최신 버전 확인 및 다운로드
echo "scrcpy 최신 버전 확인 중..."
SCRCPY_VERSION="2.7"
SCRCPY_URL="https://github.com/Genymobile/scrcpy/releases/download/v${SCRCPY_VERSION}/scrcpy-linux-v${SCRCPY_VERSION}.tar.gz"

echo "scrcpy v${SCRCPY_VERSION} 다운로드 중..."
if wget -O scrcpy.tar.gz "$SCRCPY_URL"; then
    echo "다운로드 완료"
    
    # 압축 해제
    echo "압축 해제 중..."
    tar -xzf scrcpy.tar.gz
    cd scrcpy-linux-v${SCRCPY_VERSION}
    
    # 바이너리 설치
    echo "scrcpy 바이너리 설치 중..."
    sudo cp scrcpy /usr/local/bin/
    sudo cp scrcpy-server /usr/local/bin/
    sudo chmod +x /usr/local/bin/scrcpy
    sudo chmod +x /usr/local/bin/scrcpy-server
    
    # 정리
    cd ..
    rm -rf scrcpy-linux-v${SCRCPY_VERSION} scrcpy.tar.gz
    
    echo "✅ scrcpy 설치 완료!"
    
    # 설치 확인
    if command -v scrcpy &> /dev/null; then
        echo "설치된 scrcpy 버전: $(scrcpy --version)"
    else
        echo "❌ scrcpy 설치 확인 실패"
        exit 1
    fi
    
else
    echo "❌ scrcpy 다운로드 실패"
    echo "대안 방법을 시도합니다..."
    
    # 대안 1: snap을 통한 설치
    echo "snap을 통한 scrcpy 설치 시도..."
    if ! command -v snap &> /dev/null; then
        echo "snap 설치 중..."
        sudo apt install -y snapd
        sudo systemctl enable --now snapd.socket
        sudo ln -s /var/lib/snapd/snap /snap
    fi
    
    if sudo snap install scrcpy; then
        echo "✅ snap을 통한 scrcpy 설치 완료!"
    else
        echo "❌ snap을 통한 설치도 실패했습니다."
        echo ""
        echo "수동 설치 방법:"
        echo "1. 웹 브라우저에서 https://github.com/Genymobile/scrcpy/releases 방문"
        echo "2. 최신 릴리스의 'scrcpy-linux-v*.tar.gz' 파일 다운로드"
        echo "3. 다음 명령어 실행:"
        echo "   tar -xzf scrcpy-linux-v*.tar.gz"
        echo "   sudo cp scrcpy-linux-v*/scrcpy /usr/local/bin/"
        echo "   sudo cp scrcpy-linux-v*/scrcpy-server /usr/local/bin/"
        echo "   sudo chmod +x /usr/local/bin/scrcpy"
        echo "   sudo chmod +x /usr/local/bin/scrcpy-server"
        exit 1
    fi
fi

# ADB 설치 확인
echo "ADB 설치 확인 중..."
if ! command -v adb &> /dev/null; then
    echo "ADB 설치 중..."
    sudo apt install -y android-tools-adb
else
    echo "ADB가 이미 설치되어 있습니다: $(adb version | head -n1)"
fi

# 원래 디렉토리로 돌아가기
cd - > /dev/null

echo ""
echo "🎉 scrcpy 설치가 완료되었습니다!"
echo ""
echo "사용법:"
echo "1. Android 디바이스에서 USB 디버깅 활성화"
echo "2. USB로 연결 후: adb devices"
echo "3. scrcpy 실행: scrcpy"
echo "4. WiFi 연결: adb tcpip 5555 && adb connect [IP]:5555"
echo ""
echo "테스트:"
echo "  scrcpy --version  # 버전 확인"
echo "  adb devices       # 디바이스 연결 확인"
echo "  scrcpy --no-audio --max-fps=30  # 테스트 실행"
