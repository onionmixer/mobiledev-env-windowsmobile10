# 실행 검증 기록

검증일: 2026-11-05. 기존 파일이 없는 작업 폴더에서 공식 SDK를 내려받아 준비했다.

## 출처와 이미지

- 참고 코드: `115dkk/Open-Mobile-Emulator`, 커밋 `1a739ac835219cc79038ff171aff04454e01fd3a`.
- Microsoft SDK 이미지: `10.0.14393.0`, 공식 SDK 다운로드 보관소의 `LinkId=822928`.
- 다운로드: Vhd1.cab~Vhd50.cab와 WindowsPhoneSDK-VHD.msi, 51개 파일, 2,108,679,447바이트. 크기와 설치기 내 SHA-1 대조 통과.
- 조립: MSI의 `LargeFileFragments` 테이블에서 얻은 26개 조각을 `Sequence` 오름차순으로 연결.
- VHD: 2,658,107,392바이트, 가상 용량 10GiB.
- VHD SHA-256: `b990f599b1496d9ae86204150dd8a1ee8a8bf963b439d518b50d04446fdaf913`.
- 변환한 qcow2의 `qemu-img check` 통과. 기준 이미지와 작업 overlay를 분리했다.
- SDK의 `IMAGECONFIG_XDE`에서 `1080p 6 inch 2GB`, x86, `1080x1920`, 메모리 `2048` 프로필을 확인했다. 이 프로필은 XDE 설정이며 QEMU 설정에 자동 적용되지 않는다.

## 실행 결과

호스트: Linux 6.8.0-138-generic x86_64. 초기에는 Ubuntu QEMU 6.2.0을 사용했고, 현재는 같은 상류 버전에서 USB 터치 장치를 추가한 빌드를 사용한다. 실제 호스트의 `/dev/kvm`은 접근 가능했으며 실행 샌드박스 안에서는 보이지 않았다.

| 구성 | 관찰 결과 |
| --- | --- |
| pc / SeaBIOS / IDE / TCG / max / 4 CPU / 2GB / 표준 VGA | Windows 로고 표시, 이후 KVM으로 전환 |
| pc / SeaBIOS / IDE / KVM / host / 4 CPU / 2GB / 표준 VGA | 시작 화면 부팅 |
| USB tablet + USB keyboard | 앱 목록 전환, 전화·설정 앱 실행, 스크롤, F4 전환 후 문자 입력 |
| VGA EDID 1080×1920 요청 | 셸 부팅은 가능했으나 출력은 1024×768 유지 |
| SeaVGABIOS 고정 기본 모드 + 작은 호환 모드 제외 | Windows가 1080×1920 전체 영역을 사용 |
| 게스트 UI 250%, GTK 50% | 설정 툴팁과 호스트 540×960 표시 확인. 432×768 논리 영역은 배율로 계산 |
| USB HID 터치 장치 | QMP 드래그와 실제 GTK 마우스 드래그로 시작 화면 스크롤 확인 |
| 세로 버튼 패널 | 폭 104×높이 400, 다중 모니터 경계 안에 배치 |
| tulip NIC | 드라이버/포털 사용 성공을 확인하지 못해 기본값에서 제외 |
| E1000 NIC | DHCP 요청·응답 교환, Device Portal HTTPS 연결 확인 |
| USB audio / pa / 48kHz stereo | 초기 Ubuntu QEMU에서 스트림·키패드 PCM 확인. 로컬 터치 빌드의 PCM 재시험 기록은 없음 |

## 사운드 증거

게스트에 `USBAUDIO.sys`가 존재한다. [Microsoft USB 클래스 드라이버 표](https://learn.microsoft.com/en-us/windows-hardware/drivers/usbcon/usb-dual-role-driver-stack-architecture)는 Windows 10 Mobile의 USB Audio 입출력 지원을 명시한다. 이를 QEMU의 [USB 오디오 장치](https://www.qemu.org/docs/master/system/devices/usb.html)와 연결했다.

시험한 연결은 `usb-audio,audiodev=snd0` 및 `pa,id=snd0,out.frequency=48000,out.channels=2`다. 호스트 PulseAudio의 QEMU 스트림 형식은 `s16le 2ch 48000Hz`였다.

`wavcapture`로 녹음을 시작하고 게스트 전화 앱의 키패드 1·2·3을 눌렀다. 통화 버튼은 누르지 않았다. 녹음을 종료한 후 다음을 확인했다.

| 항목 | 값 |
| --- | --- |
| 파일 | `evidence/2026-11-05/audio-smoke.wav` |
| 크기 | 2,762,188바이트 |
| 샘플레이트 | 48,000Hz |
| 채널 | 2 |
| PCM | signed 16-bit |
| 프레임 | 690,536 |
| 무음이 아닌 샘플 | 21,227 |
| peak | 70 / 32,767 |
| RMS | 약 4.1546 |

이 시험은 로컬 터치 QEMU 빌드 이전 Ubuntu QEMU에서 수행했다. 이후 동일한 PCM 시험을 다시 수행했다는 기록은 없다. 이는 게스트가 비영 오디오를 생성했고 QEMU 오디오 경로로 전달했음을 확인한 결과다. 출력 레벨은 낮으며 일반 미디어 재생 볼륨·장시간 품질·실제 스피커 청취·마이크는 별도 검증 대상이다. PA 초기화 로그에 `set_sink_input_volume/mute: Invalid argument`가 남았으나 출력 스트림과 위 PCM 데이터는 확보되었다.

## 개발 연결과 미완료 범위

게스트는 Developer mode가 이미 선택된 SDK 이미지였다. Device Portal을 활성화했고 인증은 켜 둔 상태다. QEMU 포워딩을 거쳐 HTTP는 HTTPS로 리디렉션되며, HTTPS 최종 응답은 `200`, 경로는 `/authenticate.htm`, 제목은 `Set up access`였다.

테스트할 사용자 앱 패키지는 제공되지 않았다. 앱 설치, 서명 인증서 등록, 의존성 설치, Visual Studio 디버거 연결은 아직 검증하지 않았다. 포털 접근 성공을 앱 배포 성공으로 간주하지 않는다.

Lumia 1520용 1080×1920 세로 출력과 250% UI 배율은 후속 검증으로 확인했다. ARM 바이너리 실행, 물리 센서·카메라·모뎀·GPU 재현은 포함하지 않는다. 현재 결과는 x86 SDK 앱 환경이다.

선별 실행 증거는 [증거 목록](evidence/2026-11-05/README.md)에 보관했다. 기존 `input-app-list-02.png`, `settings-search-03.png`, `device-portal-enabled.png` 등 원자료는 `emulator/runtime/experiments/raw-evidence`에 있다. 포털 인증 코드나 인증 쿠키를 문서에 기록하지 않는다.

## 세로 화면·DPI·입력 후속 검증

`emulator/firmware/bochs-portrait.patch`는 SeaVGABIOS의 `CONFIG_DISPLAY_BOCHS` 경로에서 작은 호환 모드 목록을 제외한다. 변경 전에는 1080×1920 프레임버퍼에도 Windows가 1024×768 영역만 그렸으나, 변경 후 전체 영역을 사용한다. 게스트 이미지·드라이버의 바이너리 패치는 하지 않았다.

게스트 설정 슬라이더의 **250%** 툴팁을 확인한 뒤 Apply와 정상 재시작을 수행했다. 상태 표시줄과 앱 글자가 커진 것을 재부팅 후 확인했다. 이는 Microsoft [앱 디자인 자료의 Lumia 1520 250%·768×432 표](https://download.microsoft.com/download/E/B/4/EB41BB72-7447-4B42-8E16-9C520CF3A16D/WIN010_shintak_FINAL.pdf)와 일치한다. 배율에서 계산한 논리 DPI는 240이고 논리 영역은 432×768이다. 앱 API로 직접 측정한 값은 아니다. 이 값은 실기기의 물리 밀도 약 367ppi 및 GTK 50%와 구분한다.

QEMU GTK의 배율 조정 단축키로 화면을 50%로 설정했다. X11에서 실제 측정된 클라이언트 창은 **540×987**이며, 이 중 27픽셀은 GTK 메뉴이고 게스트 영상은 **540×960**이다.

버튼이 보이지 않던 원인은 1920×1080 모니터의 바깥으로 아래쪽 패널이 배치된 것이었다. 현재는 오른쪽의 세로 패널이며, 같은 모니터의 경계 안에 두고 오른쪽이 좁으면 왼쪽으로 옮긴다. 기존 문제의 다중 모니터 좌표 및 음수 좌표를 회귀 검사에 포함했다.

`emulator/qemu-build/usb-touchscreen.patch`는 기존 마우스 태블릿과 별개의 `usb-touchscreen` 장치를 추가한다. USB HID Digitizer/Touch Screen, 한 접점, Tip Switch·In Range·Confidence·접점 ID·X/Y·Scan Time·Contact Count를 보고한다. GTK/QMP의 왼쪽 버튼과 절대 좌표가 손가락 접촉 상태로 변환되므로, 마우스 드래그를 휠 이벤트로 바꾸는 우회 처리는 하지 않는다.

QMP로 `(500,1600) → (500,450)`을 1초에 걸쳐 드래그한 뒤 시작 화면이 하단 `All apps`까지 이동했다. 이어 GTK 창에서 50% 표시 좌표 `(250,277) → (250,727)`의 실제 마우스 드래그로 위쪽 타일로 돌아가는 것도 확인했다. 다중 접점·핀치는 구현하지 않았다.

증거는 [선별 증거 목록](evidence/2026-11-05/README.md)에 있다. 당시 소스 버전·바이너리 해시·설정은 `evidence/2026-11-05/display-input-validation.json`에 보존했다. 그 안의 경로는 당시 경로이며 재분류 후 현재 경로로 소급 수정하지 않았다.

250%는 현재 작업 overlay에 적용한 상태다. 새 SDK 디스크는 Windows 설정에서 직접 적용해야 하며, 프로필 JSON이나 GTK 배율만으로 자동 적용되지 않는다. GTK 메뉴 높이와 창 외곽 크기는 호스트마다 달라질 수 있다.

## 재분류 검증

폴더 이동 전후 기준 디스크 해시·overlay 내용 비교, 새 경로에서의 두 소스 빌드와 실제 부팅은 [별도 재분류 기록](reorganization/README.md)에 있다. 과거 오디오 수치나 바이너리 해시를 재분류 후 재측정한 값으로 해석하지 않는다.


## 탭 해제·포인터 후속 검증

드래그와 별개로 보고된 탭 취소를 수정했고, 실제 GTK 숫자 입력과 드래그를 다시 확인했다. 원인·수정 전후 비교·커서 측정·새 자동 검사 8개의 범위는 [터치 입력 검증](touch-input.md)에 있다. 기존 단계의 성공 범위를 탭까지 소급 확대하지 않는다.
