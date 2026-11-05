# Lumia 1520 개발용 Windows 10 Mobile 시뮬레이터

Windows 10 Mobile SDK의 **x86 게스트**를 QEMU/KVM에서 실행하고, Lumia 1520에 맞는 화면·UI 배율·조작 환경을 준비한 프로젝트입니다. 참고한 [Open-Mobile-Emulator](https://github.com/115dkk/Open-Mobile-Emulator)는 Android용이며, 여기서는 매니페스트·디스크 분리·QMP 제어 구조를 참고했습니다.

**Snapdragon 800이나 Lumia 1520 보드를 구현한 에뮬레이터는 아닙니다.** 실제 기기의 ARM 전용 앱·FFU를 그대로 실행하는 환경으로 해석하면 안 됩니다. 이 게스트에서 테스트할 앱에는 x86 빌드와 호환되는 API·의존성이 필요합니다.

## 문서

- [HOWROUSE.md](HOWROUSE.md): 실행, 입력, 사운드, 앱 배포 연결, 처음부터 준비하는 방법.
- [HISTORY.md](HISTORY.md): 작업 순서, 시도와 수정, 판단 근거, 검증의 한계. 이후 변경 이력도 여기에 추가합니다.
- [검증 기록](docs/validation.md): 시험 환경·수치·증거 파일.
- [재분류 기록](docs/reorganization/README.md): 경로 변경, 디스크 보존과 재검증.

`HOWROUSE`는 요청한 문서 이름을 그대로 사용합니다.

## 현재 기본 구성

| 구분 | 설정·확인 범위 |
| --- | --- |
| 검증한 호스트 | Linux x86_64, KVM, GTK/X11, PulseAudio |
| 게스트 | Windows 10 Mobile SDK 10.0.14393.0, x86 |
| CPU·메모리 | 가상 CPU 4개, 2,048MiB RAM |
| 실제 게스트 화면 | 1080×1920 세로, 수정한 SeaVGABIOS 사용 |
| 게스트 UI | 현재 작업 디스크에 250% 배율 저장 |
| 논리 영역·DPI | 배율에서 계산하면 432×768, 240 논리 DPI. 앱 API로 직접 측정한 값은 아님 |
| 호스트 표시 | GTK 50%, 게스트 영상 540×960. 메뉴·창 테두리는 별도 |
| 입력 | 별도로 추가한 USB HID 터치스크린, 한 손가락 드래그·탭. 호스트 포인터 표시 |
| 버튼 | 영어 라벨의 옆 세로 패널 104×400, X11 호스트 단축키 |
| 네트워크 | E1000, DHCP 교환과 Device Portal 초기 인증 페이지 확인 |
| 사운드 | USB Audio → PulseAudio 구성. 초기 Ubuntu QEMU에서 비영 PCM 출력 확인 |

새 SDK 디스크에 250% 배율이 자동으로 들어가지는 않습니다. 현재 디스크는 Windows 설정에서 적용·재시작한 상태이며, 새 디스크의 설정 방법은 HOWROUSE에 있습니다. [프로필 JSON](emulator/profiles/lumia-1520.json)은 사양·현황 기록이고, 모든 값이 런처에 자동 적용되는 설정 파일은 아닙니다.

## 실행

프로젝트 루트에서 실행합니다. 같은 작업 디스크의 QEMU가 이미 실행 중이면 중복 실행하지 않습니다.

```bash
./start_emulator_wm10.sh
```

게스트 부팅과 터치 드래그, GTK 50% 표시, 세로 버튼 패널을 실제 화면에서 확인했습니다. 물리 버튼의 일반 동작은 사용자의 확인도 받았고, 볼륨은 직접 버튼과 호스트 단축키의 화면 변화를 비교했습니다. 모든 버튼·앱에 대한 전수 시험을 수행한 것은 아닙니다.

## 폴더 구성

```text
README.md                       프로젝트 개요·현재 상태
HOWROUSE.md                     사용·준비 방법
HISTORY.md                      사실과 한계를 구분한 작업 이력
start_emulator_wm10.sh           한 번에 실행하는 진입 스크립트
tools/                          실행기·컨트롤·빌드 도구
tests/                          저장소 보존·창 배치 회귀 검사
docs/                           검증 문서·선별 증거·재분류 기록
emulator/
  profiles/                     목표 사양·검증 상태
  manifests/                    SDK 파일·해시·참고 저장소 정보
  firmware/                     SeaVGABIOS 패치·빌드 설정
  qemu-build/                   QEMU 패치·소스 버전
  third_party/                  외부 저장소 체크아웃
  artifacts/                    SDK 캐시·생성 실행 파일·진단 자료
  runtime/                      기준 디스크·작업 디스크·현재 실행 기록
  build/                        현재 구조의 빌드 작업 디렉터리·로그
  build-archive/                이동 전 빌드 디렉터리 보관
```

`third_party`, `artifacts`, `runtime`, `build`, `build-archive`는 Git 제외 대상입니다. 선별한 증거는 [docs/evidence/2026-11-05](docs/evidence/2026-11-05/README.md)에 로컬 보관하며, 원본 실행 로그의 과거 경로는 소급해서 바꾸지 않습니다. 화면·녹음 원본과 호스트별 검증 JSON은 Git에서 제외하고 설명·해시 목록만 포함합니다.

## 아직 확인하지 않은 범위

- 사용자 앱 설치, 서명·의존성 등록, Visual Studio 디버거 연결.
- ARM 바이너리 실행과 Lumia 보드·실기기 GPU·모뎀·센서 재현.
- 다중 터치·핀치, 마이크, 카메라 영상, 장시간 오디오 품질·물리 스피커 청취.
- Windows/WHPX, macOS, Wayland에서의 전체 실행.

Device Portal의 HTTP 200은 초기 인증 페이지 접근의 증거이며 앱 배포 성공의 증거는 아닙니다. 초기 사운드 녹음은 로컬 터치 QEMU 빌드 이전 결과로, 이후 단계에서 동일한 PCM 시험을 다시 수행했다는 기록은 없습니다.

```bash
python3 -m unittest discover -s tests -v
```

현재 자동 검사는 8개입니다. 터치 보고서 검사는 `cc`가 없으면 skip됩니다. 이 검사는 저장소 보존·패널 배치·터치 보고서의 접촉 해제를 다루며 전체 게스트·하드웨어 호환성을 보증하지 않습니다.


## Git 관리 범위

커밋 대상은 실행 도구·테스트·패치·빌드 설정·프로필·SDK 메타데이터·문서입니다. SDK와 Windows 이미지·게스트 변경 디스크·생성 실행 파일·외부 소스·빌드 결과는 포함하지 않습니다. SDK 다운로드는 공식 배포처에서 다시 수행합니다.

[.gitignore](.gitignore)는 잘못된 위치에 복사한 디스크·설치 패키지·실행 바이너리, 인증 키·환경 파일·로컬 도구 설정, 실행 로그·통신 캡처·캐시도 제외합니다. `docs/evidence`에서는 README와 `index.json`만 포함하고, `docs/reorganization`의 화면과 JSON은 로컬 검증 자료로 둡니다. 따라서 Git 체크아웃만으로 문서에 언급된 원본 증거가 모두 제공되지는 않습니다. 제외 파일은 이번 정리에서 삭제하지 않았습니다.

아직 이 폴더를 Git 저장소로 초기화하거나 파일을 stage·commit하지 않았습니다. 제외 규칙과 후보 파일은 임시 저장소의 인덱스로 점검했습니다. [.gitattributes](.gitattributes)는 패치 형식에 필요한 빈 문맥 줄의 공백을 검사 오류로 처리하지 않도록 설정합니다. 초기화 후에는 `git status --short`와 `git diff --cached --stat`으로 실제 추가 대상을 확인합니다. `.gitignore`는 이미 추적 중인 파일을 제외하는 기능이 아니므로, 이후 규칙을 바꾸면 추적 상태도 확인해야 합니다.


탭 해제 수정과 포인터 표시의 비교 검증은 [터치 입력 검증](docs/touch-input.md)에 기록했습니다.

## 라이선스

이 저장소의 직접 작성한 도구·테스트·문서·메타데이터는 [MIT License](LICENSE)입니다. 아래 구성요소는 예외이거나 이 라이선스에 포함되지 않습니다.

| 구성요소 | 라이선스 |
| --- | --- |
| [`emulator/firmware/`](emulator/firmware/)의 SeaBIOS 패치·설정 | LGPL-3.0-or-later. 대상 소스(SeaBIOS)의 라이선스를 따르며 같은 폴더의 `COPYING.LESSER`, `COPYING`에 전문이 있습니다. |
| [`emulator/qemu-build/usb-touchscreen.patch`](emulator/qemu-build/usb-touchscreen.patch) | 대상 파일 `hw/usb/dev-hid.c`의 MIT 라이선스를 따릅니다. 패치를 적용한 QEMU 전체는 GPL-2.0입니다. 이 저장소는 QEMU 바이너리를 배포하지 않습니다. |
| QEMU·SeaBIOS·Open-Mobile-Emulator 체크아웃 | 저장소에 포함하지 않습니다. 각 프로젝트의 라이선스를 따릅니다. Open-Mobile-Emulator(GPL-2.0)는 구조 참고용이며 코드를 재사용하지 않았습니다. |
| Windows 10 Mobile SDK 및 게스트 이미지 | 저장소에 포함하지 않습니다. Microsoft의 약관을 따르며 이 저장소의 라이선스와 무관합니다. |
