# 탭 해제와 호스트 포인터 검증

검증일: 2026-11-05. 사용자는 드래그는 동작하나 클릭·탭이 반응하지 않는다고 보고했고, 이어 마우스 위치를 볼 수 있는 포인터 표시를 요청했다.

## 원인과 수정

기존 USB 터치 보고서는 접촉 중 Tip Switch·In Range·Confidence를 모두 켜서 플래그 `0x07`을 보냈으나, 해제 시 전부 꺼서 `0x00`을 보냈다. Microsoft의 [Windows Touchscreen HID 규칙](https://learn.microsoft.com/en-us/windows-hardware/design/component-guidelines/touchscreen-required-hid-top-level-collections)은 의도한 터치의 Confidence를 손을 뗄 때까지 유지하도록 설명한다. Confidence가 꺼지면 OS가 접촉을 취소할 수 있다.

`emulator/qemu-build/usb-touchscreen.patch`의 보고서 인코더를 수정하여 해제 시 `0x04`를 보낸다. Tip Switch·In Range는 해제하고 Confidence는 유지한다. 기존 접점 ID·마지막 좌표·해제 접점 수 1은 유지한다. 이는 한 접점 장치의 수정이며 다중 터치 구현을 추가한 것이 아니다.

GTK 커서는 상류 QEMU 6.2의 `ui/gtk.c`가 절대 좌표 장치에서 기본적으로 숨기고 있었다. 동일 소스에 이미 구현된 `show-cursor` 옵션을 사용하여 런처 기본값을 `gtk,zoom-to-fit=off,grab-on-hover=off,show-cursor=on`으로 바꿨다. 별도 커서 렌더링이나 게스트 마우스 드라이버는 추가하지 않았다.

## 비교 시험

시험 시작 시 기존 QMP 포트는 연결 거부 상태였다. 기존 실행 파일을 같은 디렉터리의 `qemu-system-x86_64-before-tap-fix`로 보존하고 `--snapshot --pointer touch`를 명시해 실행했다. 원래 작업 디스크를 시험 전 상태로 되돌리는 작업은 하지 않았다.

| 시험 | 수정 전 | 수정 후 |
| --- | --- | --- |
| QMP `(90,150)` 80ms 탭 | 시작 화면 유지 | 전화 앱 열림 |
| GTK 50% 전화 타일 `(45,102)` 탭 | 시작 화면 유지 | 전화 앱 열림 |
| GTK 키패드 `(75,602)`, `(250,602)` | 비교하지 않음 | 각각 80ms·20ms 탭으로 `12` 입력 |
| QMP 위로 드래그 | 이전 단계에서 확인 | 누른 상태와 해제 후 화면 모두 아래쪽 타일·All apps 확인 |
| 실제 GTK 아래로 드래그 | 이전 단계에서 확인 | 위쪽 전화 타일로 복귀 확인 |
| XFixes 커서 이미지 | 1×1, 비투명 픽셀 0 | 48×48, 비투명 픽셀 715 |

위 GTK 좌표는 당시 클라이언트의 27픽셀 메뉴 높이를 포함한 값이며 모든 호스트의 고정 좌표가 아니다. 키패드 숫자만 입력했고 통화는 하지 않았다. 포인터는 사용자도 보인다고 확인했다. 처음에는 화면 이동 직후 드래그를 연달아 보낸 캡처가 불명확해 이를 성공 증거로 쓰지 않았고, 안정된 시작 화면에서 접촉 중·해제 후 캡처를 나누어 다시 확인했다.

원래 실행 파일로 시작한 snapshot 비교 인스턴스를 종료한 뒤 수정 빌드를 일반 모드로 실행했다. 검증 후 수정된 게스트는 계속 실행 중으로 두었다. 이후 생존 여부는 별도로 확인해야 한다.

## 회귀 검사와 빌드

`tests/test_touchscreen_report.py`는 저장한 패치에서 실제 C 인코더를 추출·컴파일한다. tablet 샘플과 시계만 stub으로 대체하고 손을 뗀 보고서의 Confidence, Tip Switch 해제, 접점 ID·좌표·접점 수, scan-time, 짧은 출력 버퍼, 기존 마우스 경로를 검사한다. 수정 전 Confidence 검사 실패를 확인했고 수정 후 전체 8개 검사가 통과했다. `cc`가 없으면 이 C 검사는 skip된다. USB 전송과 실제 Windows 동작은 위 게스트 시험으로 별도 확인했다.

QEMU는 `tools/build_touch_qemu.sh`로 다시 빌드했다. 로그는 로컬 `emulator/build/logs/qemu-tap-fix.log`다. 새 실행 파일 SHA-256은 `8b8a119e40dbc714a0bf421f1963859e85c5628a7e4b69e25d4dc5e7f696d3e0`이다. 소스 pin과 SeaVGABIOS는 바꾸지 않았다.

## 증거와 범위

로컬 `emulator/runtime/tap-validation.json`에 비교 설정·해시·커서 측정값·화면 파일 목록을 보관했다. `tap-debug-*` PNG·PPM과 `tap-cursor-*.json`도 같은 폴더에 있으며 `.gitignore`로 제외된다. 과거 증거·재분류 빌드 해시를 이번 값으로 덮어쓰지 않았다.

이 시험은 전화 앱·키패드·시작 화면에서의 탭과 드래그 확인이다. 모든 앱·입력 지연·장시간 안정성·다중 접점을 검증한 것은 아니며, 앱 배포·오디오 PCM도 재시험하지 않았다.
