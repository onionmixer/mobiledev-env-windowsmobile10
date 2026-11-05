# 사용 방법

이 문서의 명령은 특별한 설명이 없으면 프로젝트 루트에서 실행합니다. 검증한 환경은 Linux x86_64·KVM·GTK/X11·PulseAudio입니다. 다른 호스트의 지원 여부는 코드에 선택지가 있다는 이유만으로 확인된 것으로 간주하지 않습니다.

## 준비된 환경 실행

```bash
python3 tools/mobile_sim.py doctor
./start_emulator_wm10.sh
```

`./start_emulator_wm10.sh`는 기존 `tools/run_simulator.sh`를 호출하며 모든 인수를 그대로 전달합니다. 다른 디렉터리에서도 스크립트의 절대 경로로 실행할 수 있습니다.

현재 작업 폴더에는 SDK VHD, 기준·작업 디스크, 터치 입력을 추가한 QEMU와 세로 모드 VGA ROM이 있습니다. 런처는 `emulator/artifacts/qemu/qemu-system-x86_64`를 우선 선택합니다. 이것이 없으면 시스템 QEMU를 선택하지만, 시스템 QEMU에 별도의 `usb-touchscreen` 장치가 추가되는 것은 아닙니다.

화면은 1080×1920, GTK 표시는 기본 50%입니다. 현재 디스크의 UI 배율은 250%이며 RAM 2GB·가상 CPU 4개·E1000·USB Audio를 사용합니다.

| 실행 예 | 용도 |
| --- | --- |
| `./start_emulator_wm10.sh --dry-run` | 실행 인수만 확인 |
| `./start_emulator_wm10.sh --headless` | GTK 창·버튼 패널 없이 실행 |
| `./start_emulator_wm10.sh --headless --audio none` | 사운드 서버 없는 시험 환경 |
| `./start_emulator_wm10.sh --gtk-scale 0.75` | GTK 표시를 75%로 변경 |
| `./start_emulator_wm10.sh --no-controls` | 옆 버튼 패널·호스트 단축키 도우미 없이 실행 |
| `./start_emulator_wm10.sh --pointer mouse` | 터치 대신 기존 USB 마우스 태블릿으로 시험 |
| `./start_emulator_wm10.sh --no-portrait` | 표준 VGA 경로로 시험. 게스트 저장 설정에 따라 표시가 달라질 수 있음 |
| `./start_emulator_wm10.sh --snapshot` | 해당 실행의 디스크 쓰기를 종료 시 폐기 |

같은 작업 디스크로 두 인스턴스를 실행하지 않습니다. 시작 실패 시 `emulator/runtime/qemu.stderr.log`와 현재 `last-command.json`을 확인합니다. `--dry-run`의 자동 가속 선택은 그 명령이 실행된 환경을 따릅니다. 샌드박스 안에서 `/dev/kvm`이 보이지 않는다고 실제 호스트에도 KVM이 없다고 결론 내리지 않습니다.

## 종료와 재시작

```bash
python3 tools/mobile_sim.py qmp status
python3 tools/mobile_sim.py qmp quit
```

`qmp quit`은 QEMU를 즉시 종료합니다. Windows 게스트의 정상 종료와 동일한 명령이 아니므로 게스트에 저장할 작업을 먼저 마칩니다. 게스트 설정에서 재시작할 때는 `-no-reboot` 때문에 QEMU가 종료될 수 있습니다. 기존 프로세스가 끝난 것을 확인하고 다시 실행합니다. 이전 시험에서는 게스트 종료가 끝나기 전에 실행기를 다시 호출해 시작이 실패한 적이 있습니다.

`emulator/runtime/process.json`은 PID 기록이며 살아 있는 프로세스임을 보장하지 않습니다. `last-command.json`의 `boot_verified: false`는 런처가 OS 부팅을 판정하지 않는다는 뜻으로, 별도의 화면 검증 결과와 구분합니다.

## 화면·DPI·조작

| 층 | 의미 |
| --- | --- |
| 실제 픽셀 | Windows가 그리는 1080×1920 |
| UI 배율 | 게스트 Windows의 250%. 계산상 논리 영역은 432×768 |
| 논리 DPI | 96×2.5 = 240. 앱 API로 직접 측정한 결과는 아님 |
| 물리 밀도 | Lumia 1520의 6인치·1080×1920 사양에서 약 367ppi로 계산 |
| GTK 표시 배율 | 호스트에 영상을 50%로 표시하여 영상 부분이 540×960이 됨 |

GTK 메뉴·창 테두리까지 포함한 창 크기는 호스트 테마와 DPI에 따라 달라집니다. 이전 환경에서 측정한 540×987을 모든 호스트의 고정 크기로 사용하면 안 됩니다.

GTK 기본 실행은 `show-cursor=on`으로 호스트 마우스 포인터를 표시합니다. 포인터는 호스트의 위치 안내이며 손가락 접촉은 왼쪽 버튼을 누른 동안만 전달됩니다.

왼쪽 마우스 버튼을 누른 채 움직이면 한 손가락 터치로 전달됩니다. 탭은 앱 선택, 드래그는 터치 스크롤 등에 사용합니다. 다중 접점·핀치는 구현하지 않았습니다. `--pointer mouse`에서는 마우스 입력으로 바뀌므로 터치와 같은 스와이프 동작을 기대하지 않습니다.

문자 입력이 되지 않으면 게스트에서 **F4**를 눌러 하드웨어 키보드 입력을 전환합니다. Windows 키는 시작 화면, Win+I는 설정을 여는 동작을 확인했습니다.

### 새 SDK 디스크의 UI 배율

런처의 `--gtk-scale`과 Windows UI 배율은 별개입니다. 새로 가져온 SDK 디스크는 다음 설정을 한 번 수행합니다.

1. 게스트의 `Settings → System → Display`를 엽니다.
2. `Size of text, apps, and items`에서 **250%**를 선택합니다. 단순히 슬라이더 위치로 추정하지 말고 표시되는 값을 확인합니다.
3. Apply 후 게스트를 재시작하고 실행기가 종료되었다면 다시 실행합니다.

현재 작업 디스크에는 이미 저장되어 있습니다. SDK 원본 VHD나 모든 향후 디스크를 자동 수정한 것은 아닙니다. 프로필 JSON의 수치를 바꾸는 것만으로 이 설정이 적용되지 않습니다.

### 옆 물리 버튼

패널은 폭 104·높이 400픽셀의 세로형입니다. QEMU가 있는 모니터 안쪽에 배치하며 오른쪽 공간이 부족하면 왼쪽을 사용합니다. 패널을 끄려면 `--no-controls`로 시작합니다. 버튼 라벨·창 제목·상태 안내는 영어로 고정되어 있으며 다국어 선택 기능은 없습니다.

| 버튼 | 호스트 단축키 | 게스트 입력 |
| --- | --- | --- |
| Back | Ctrl+Alt+Shift+B | Win+Esc |
| Start | Ctrl+Alt+Shift+H | Win |
| Search | Ctrl+Alt+Shift+S | Win+F3 |
| Volume − | Ctrl+Alt+Shift+D | Win+F10 |
| Volume + | Ctrl+Alt+Shift+U | Win+F9 |
| Power | Ctrl+Alt+Shift+P | Win+F12 |
| Camera | Ctrl+Alt+Shift+C | Win+F7 |

호스트 단축키는 X11에서 도우미가 처리합니다. 다른 프로그램이 같은 키 조합을 이미 잡고 있으면 해당 조합이 동작하지 않을 수 있습니다. 버튼은 QMP로 입력을 보냅니다. 전원은 휴대폰 잠금·깨우기용 입력이며 QEMU 종료 명령이 아닙니다. 카메라 버튼이 존재한다고 실제 카메라 장치가 구현된 것은 아닙니다.

## 앱 배포 연결

현재 작업 디스크에서는 SDK의 Developer mode 상태를 확인하고 Device Portal을 켰습니다. 인증은 끄지 않았습니다.

1. 게스트 `Settings → Update & security → For developers`에서 Device discovery를 켭니다.
2. 호스트 브라우저로 **https://127.0.0.1:5443/** 에 접속합니다. 게스트의 자체 서명 인증서를 사용하는 로컬 연결입니다.
3. 게스트 설정의 Pair 버튼으로 표시되는 코드를 브라우저에 입력합니다.
4. 인증 후 앱 관리 화면에서 호환되는 x86 패키지·의존성·서명 인증서를 준비해 설치를 시도할 수 있습니다.

| 호스트 접속 지점 | 용도 |
| --- | --- |
| `https://127.0.0.1:5443/` | Device Portal HTTPS |
| `http://127.0.0.1:5080/` | HTTP 진입점, 시험 당시 HTTPS로 리디렉션 |
| `127.0.0.1:44520` | QMP 관리 |

확인한 것은 초기 인증 페이지 `/authenticate.htm`의 HTTP 200까지입니다. 실제 페어링 완료·사용자 앱 설치·Visual Studio 디버깅은 미검증입니다. 빌드에는 별도의 호환 Windows/UWP 도구 체인이 필요하며, 이 실행기는 컴파일러를 제공하지 않습니다. 게스트 버전 14393에서 지원하는 최소 OS 버전·API·x86 의존성을 사용해야 합니다. ARM 전용 앱·Lumia FFU는 실행 대상이 아닙니다.

## 사운드

```bash
./start_emulator_wm10.sh --audio pa
```

Linux 기본 출력은 `usb-audio`와 PulseAudio의 48kHz 스테레오 구성입니다. `--audio none`으로 끄거나 `--audio wav`로 파일 출력 경로를 선택할 수 있습니다. Windows `dsound`·macOS `coreaudio` 선택지는 있으나 전체 호스트 실행을 검증하지 않았습니다.

실행 중인 게스트의 출력을 확인하려면 다음과 같이 녹음합니다. 출력 파일은 기존 파일과 다른 이름을 사용합니다.

```bash
python3 tools/mobile_sim.py qmp audio-record --output emulator/runtime/audio-check.wav
# 게스트 앱에서 소리 재생
python3 tools/mobile_sim.py qmp audio-stop
```

초기 키패드 녹음은 보관한 WAV（로컬 파일: `docs/evidence/2026-11-05/audio-smoke.wav`）와 [검증 수치](docs/validation.md)에 있습니다. 이 시험은 Ubuntu QEMU에서 수행했고, 로컬 터치 QEMU 빌드 이후 같은 PCM 시험을 다시 했다는 기록은 없습니다. 마이크·물리 스피커 청취·일반 미디어 품질·지연을 검증한 결과로 확대해 해석하지 않습니다.

## 처음부터 준비

동일 계열의 Ubuntu/Linux 환경을 기준으로 합니다. Python 3/Tk, `qemu-img`, `curl`, `cabextract`, `xdotool`, `xrandr`와 빌드 도구가 필요합니다. 소스 빌드에는 C/C++ 컴파일러, Make, Meson, Ninja, GLib·Pixman·GTK3·PulseAudio 개발 헤더를 사용했습니다.

해당 Ubuntu 패키지의 예는 `qemu-utils curl cabextract python3 python3-tk xdotool x11-xserver-utils build-essential pkg-config meson ninja-build libglib2.0-dev libpixman-1-dev libgtk-3-dev libpulse-dev`입니다. 패키지를 자동 설치하는 기능은 없습니다.

```bash
bash tools/build_portrait_firmware.sh
bash tools/build_touch_qemu.sh
python3 tools/mobile_sim.py doctor
python3 tools/mobile_sim.py download-sdk
python3 tools/mobile_sim.py prepare-sdk
python3 tools/mobile_sim.py import-image emulator/artifacts/sdk-14393/flash.vhd
./start_emulator_wm10.sh
```

SDK 다운로드는 약 2.1GB이고 캐시·조각·변환본·외부 소스·빌드는 추가 공간을 사용합니다. 공식 HTTPS 배포처에서 받은 설치기에 기록된 크기·SHA-1로 payload를 대조하며, SHA-256은 로컬 영수증과 조립 VHD 검사에 사용합니다. Authenticode 서명 검증을 수행했다고 주장하지 않습니다.

SDK·실행 파일은 `emulator/artifacts`, 외부 소스는 `emulator/third_party`, 빌드는 `emulator/build`에 둡니다. `emulator/build-archive`의 이동 전 생성물에는 이전 절대 경로가 남아 있으므로 재빌드 작업 디렉터리로 사용하지 않습니다.

## 디스크·기록 보존

- `emulator/runtime/base.qcow2`: SDK VHD에서 변환한 기준 디스크.
- `emulator/runtime/disk.qcow2`: 현재 게스트 설정·변경을 담은 overlay. 기준 디스크를 상대 경로 `base.qcow2`로 참조합니다.
- `emulator/runtime/experiments/before-portrait.qcow2`: 세로 화면 시험 전 백업. 현재 DPI·설정이 모두 들어 있는 최신 백업은 아닙니다.
- `emulator/runtime/layout-backup/disk-before-layout.qcow2`: 재분류 직전 overlay의 원본 복사본. 당시 절대 backing 경로를 보존하므로 새 위치에서 단독 실행할 수 있는 독립 디스크가 아닙니다. 복구 시 같은 기준 디스크가 필요합니다.
- `emulator/runtime/history/pre-reorganization`: 이동 전 실행 인수·PID·창 좌표·로그.
- `emulator/runtime/experiments/raw-evidence`: 선별하지 않은 기존 화면·녹음·통신 기록.

디스크를 옮길 때에는 QEMU를 먼저 종료하고 overlay와 backing의 연결을 확인합니다. 단순 경로 변경을 위해 새 SDK를 가져오거나 기준 디스크로 작업 디스크를 덮어쓰면 안 됩니다. 이번 재분류의 보존·비교 결과는 `docs/reorganization/migration.json`에 기록했습니다.

## 검사

```bash
python3 -m unittest discover -s tests -v
```

8개 검사는 손상 payload 거부, 기존 디스크 보호, VHD 변환·상대 backing 이동, FFU 거부, 다중 모니터 패널 배치, 터치 해제 보고서의 Confidence·좌표·접점 유지를 확인합니다. 마지막 검사는 C 컴파일러 `cc`가 필요하며 없으면 skip됩니다. 게스트 앱 설치나 전체 하드웨어 호환성을 대신하는 검사는 아닙니다.


탭 해제 수정과 포인터 표시의 비교 검증은 [터치 입력 검증](docs/touch-input.md)에 기록했습니다.
