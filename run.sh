#!/bin/bash

# AR Phone Interface 실행 스크립트

# 가상환경 활성화
source ar_phone_env/bin/activate

# 프로그램 실행
python main.py "$@"

pyenv activate ar_phone_env
adb tcpip 5555
adb connect 192.168.0.102:5555