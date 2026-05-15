# AR Phone Interface - Android Only

Gesture-based AR Android smartphone interface using Raspberry Pi 4

---

![AR demo](assets/KakaoTalk_20251118_083449212_02.jpg)
![AR demo](assets/KakaoTalk_20251118_083449212_03.jpg)

## Why I Built This

Most of what makes a person productive — the way they navigate a phone, the gestures they reach for instinctively, the micro-decisions they make without thinking — is tacit knowledge. It lives in muscle memory and habit, not in any document or dataset.

This project is an attempt to change that. By instrumenting everyday smartphone interaction through an AR interface, I wanted to capture personal usage patterns as structured, machine-learnable data. Every gesture, tap, swipe, and navigation sequence becomes a data point. Over time, that stream of behavioral data can be used to model individual habits, predict intent, and ultimately train a system that understands how a specific person uses their phone — not how the average user does.

The AR phone is the collection mechanism. The real goal is turning embodied, habitual behavior into something a machine can learn from.

---

## Project Overview

This project implements an AR (Augmented Reality) interface using Raspberry Pi 4 that allows users to control an Android smartphone through hand gestures. It creates the visual effect of a transparent smartphone screen floating in front of the user, controllable through natural hand movements.

## Key Features

- Real-time Android mirroring via scrcpy with high-quality output
- Full control support including touch, swipe, key input, and text input
- Hand gesture recognition powered by MediaPipe
- AR display using LCD and mirror optics
- Intuitive control through natural hand movements

## Hardware Requirements

### Required Components
- Raspberry Pi 4 (4GB RAM recommended)
- Camera module: Pi Camera v2 (recommended) or USB webcam
- LCD display: 7-inch touchscreen (800x480 or higher)
- Mirror: semi-transparent mirror for AR effect
- Lens: opaque lens for screen projection

Camera selection guide:
- Pi Camera v2: optimized performance via Picamera2 library, resolves buffer issues
- USB webcam: uses OpenCV VideoCapture, excellent compatibility

### Optional Components
- Microphone for voice commands
- Speaker for audio feedback
- LED for status indication

## Software Requirements

- OS: Raspberry Pi OS (64-bit)
- Python: 3.8 or higher
- Camera library: Picamera2 (Pi Camera v2) or OpenCV (USB webcam)
- Android: scrcpy, ADB
- Android device with USB debugging enabled

## Installation

### 1. Automatic Installation (Recommended)
```bash
# Clone the repository
git clone <repository-url>
cd ar_phone

# Run the setup script
chmod +x setup.sh
./setup.sh
```

### 2. Manual Installation
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y python3 python3-pip python3-venv opencv-python

# Create Python virtual environment
python3 -m venv ar_phone_env
source ar_phone_env/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install scrcpy for Android
sudo apt install -y scrcpy adb
```

### 3. Raspberry Pi Configuration
```bash
# Enable camera module
sudo raspi-config
# Interface Options > Camera > Enable

# Enable I2C/SPI for LCD
sudo raspi-config
# Interface Options > I2C > Enable
# Interface Options > SPI > Enable
```

## Gesture Controls

| Gesture | Action | Description |
|---------|--------|-------------|
| Pointing | Mouse cursor | Extend index finger and move to control cursor |
| Grab | Click/Drag | Make a fist and move to click or drag |
| Pinch | Zoom in/out | Pinch thumb and index finger to adjust zoom |
| Wave | Back | Wave hand left/right to go back |
| Open palm | Home button | Show palm to return to home screen |

## Project Structure

```
ar_phone/
├── main.py                    # Main application
├── config.json               # Configuration file
├── requirements.txt          # Python dependencies
├── setup.sh                 # Automatic setup script
├── run.sh                   # Run script
├── test_components.py       # Component tests
├── phone_mirroring/         # Android mirroring module
│   ├── __init__.py
│   └── android_mirror.py    # Android scrcpy mirroring
├── hand_tracking/           # Hand gesture recognition module
│   ├── __init__.py
│   └── gesture_detector.py  # MediaPipe-based gesture detection
├── gesture_controls/        # Gesture control mapping
│   ├── __init__.py
│   └── gesture_mapper.py    # Gesture to smartphone action mapping
├── display_manager/         # Display management
│   ├── __init__.py
│   └── ar_display.py        # AR display and overlay
└── utils/                   # Utility functions
    ├── __init__.py
    ├── config.py            # Configuration management
    └── logger.py            # Logging system
```

## Usage

### Basic Execution
```bash
# Activate virtual environment
source ar_phone_env/bin/activate

# Run with automatic camera selection
python main.py

# Force Pi Camera v2
python main.py --camera-type picamera2

# Force USB webcam
python main.py --camera-type opencv

# Or use the run script
./run.sh
```

### Advanced Options
```bash
# Use a specific camera index
python main.py --camera 1

# Specify Android device (when multiple devices are connected)
python main.py --device-id [device_id]

# LCD display mode
python main.py --display lcd

# Debug mode
python main.py --debug
```

### Android Device Setup
```bash
# 1. Enable USB debugging on Android
# Settings > Developer Options > USB Debugging

# 2. Verify device connection
adb devices

# 3. Set up WiFi connection (optional)
adb tcpip 5555
adb connect [device_ip]:5555

# 4. Verify scrcpy installation
scrcpy --version
```

### Fixing scrcpy Installation on Raspberry Pi OS

The default Raspberry Pi OS package repository may not include scrcpy, causing installation errors.

#### Automatic Installation (Recommended)
```bash
chmod +x install_scrcpy.sh
./install_scrcpy.sh
```

#### Manual Installation
```bash
# 1. Install dependencies
sudo apt update
sudo apt install -y ffmpeg libsdl2-2.0-0 libavcodec58 libavformat58 libavutil56 libswresample3 libswscale5 libusb-1.0-0 wget tar

# 2. Download and install scrcpy
cd /tmp
wget https://github.com/Genymobile/scrcpy/releases/download/v2.7/scrcpy-linux-v2.7.tar.gz
tar -xzf scrcpy-linux-v2.7.tar.gz
cd scrcpy-linux-v2.7
sudo cp scrcpy /usr/local/bin/
sudo cp scrcpy-server /usr/local/bin/
sudo chmod +x /usr/local/bin/scrcpy
sudo chmod +x /usr/local/bin/scrcpy-server

# 3. Verify installation
scrcpy --version
```

#### Alternative: Install via snap
```bash
# Install snap if not present
sudo apt install -y snapd
sudo systemctl enable --now snapd.socket
sudo ln -s /var/lib/snapd/snap /snap

# Install scrcpy
sudo snap install scrcpy
```

## Configuration

Adjust settings in `config.json`:

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

## Testing

```bash
# Run all component tests
python test_components.py

# Test Android control features
python test_android_control.py

# Run specific tests
python test_android_control.py --test adb
python test_android_control.py --test scrcpy
python test_android_control.py --test mirror

# Test Android device connection
adb devices

# Test scrcpy
scrcpy --no-audio --max-fps=30
```

## Troubleshooting

### Camera Not Detected
```bash
# Check camera module is enabled
sudo raspi-config
# For USB webcam, try a different index
python main.py --camera 1
```

### Android Device Connection Failed
```bash
# Verify USB debugging is enabled
adb devices
# Reinstall ADB driver
sudo apt reinstall android-tools-adb
```

### scrcpy Installation Failed (Raspberry Pi OS)
```bash
# Use the dedicated install script
chmod +x install_scrcpy.sh
./install_scrcpy.sh

# Or install manually
cd /tmp
wget https://github.com/Genymobile/scrcpy/releases/download/v2.7/scrcpy-linux-v2.7.tar.gz
tar -xzf scrcpy-linux-v2.7.tar.gz
cd scrcpy-linux-v2.7
sudo cp scrcpy /usr/local/bin/
sudo cp scrcpy-server /usr/local/bin/
sudo chmod +x /usr/local/bin/scrcpy
sudo chmod +x /usr/local/bin/scrcpy-server
```

### Performance Issues
```bash
# Increase GPU memory allocation
sudo raspi-config
# Advanced Options > Memory Split > 128
```

## Android Control Features

### Supported Control Methods

**scrcpy Mirroring (Default)**
- High-quality screen mirroring
- Real-time touch and key control
- Supports both WiFi and USB connections

**ADB Command Control**
- Touch, swipe, and key input
- Text input support
- Multi-device support

### Runtime Controls

- A key: Display Android device status info
- R key: Restart Android mirroring
- F key: Toggle gesture info overlay
- T key: Adjust transparency

## Performance Optimization

- GPU memory: allocate 128MB or more
- Camera resolution: 640x480 recommended
- Frame rate: 30 FPS
- Gesture confidence threshold: 0.7 or higher

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is distributed under the MIT License.

## Support

If you encounter issues or have questions, please open an issue in the repository.

---

Note: This project was created for educational and research purposes. Please verify relevant licenses before any commercial use.
