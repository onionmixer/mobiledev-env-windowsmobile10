# 2026-11-05 선별 증거

재분류 전에 생성한 파일 17개를 바이트 그대로 복사했다. [index.json](index.json)에 각 파일의 SHA-256과 당시 원래 경로를 기록했다. 이미지에 찍힌 게스트 시각이나 파일 시각만으로 세부 작업 순서를 추정하지 않는다. 전체 경위는 [HISTORY](../../../HISTORY.md)에 있다.

| 파일 | 보여 주는 범위·주의점 |
| --- | --- |
| `boot-bios-01.png` | 초기 부팅 시도. TCG 셸 부팅 성공 증거로 사용하지 않음 |
| `boot-kvm-01.png` | 초기 KVM 시작 화면 |
| `portrait-rom-01.png` | 프레임버퍼만 세로가 된 중간 상태. Windows의 전체 영역 사용 성공이 아님 |
| `portrait-native-01.png` | 호환 모드 제외 후 전체 세로 영역 사용 |
| `gtk-50pct-02.png` | 당시 GTK 50% 표시 |
| `controls-visible.png` | 옆으로 옮겨 보이게 한 가로 패널. 최종 배치가 아님 |
| `controls-vertical-final.png` | 후속 요청을 반영한 세로 패널 |
| `dpi-slider-tooltip.png`, `dpi-tooltip-detail.png` | 게스트 설정 250% 툴팁과 확대 부분 |
| `dpi250-after-reboot.png` | Apply·게스트 재시작 후 표시 |
| `touch-before.png`, `touch-after.png` | QMP 한 접점 터치 드래그 전후 |
| `gtk-drag-verified.png` | 실제 GTK 마우스 드래그 후 화면 |
| `direct-volume-final.png`, `shortcut-volume-final.png` | 직접 입력·호스트 단축키의 볼륨 표시. 모든 버튼 전수 검증은 아님 |
| `audio-smoke.wav` | 초기 Ubuntu QEMU 키패드 PCM. 로컬 터치 QEMU에서 재녹음한 파일이 아님 |
| `display-input-validation.json` | 당시 경로·버전·바이너리 해시. 재빌드 후 현재 바이너리와 다를 수 있음 |

기타 원자료는 `emulator/runtime/experiments/raw-evidence`, 이동 전 실행 로그는 `emulator/runtime/history/pre-reorganization`에 있다. 두 경로는 용량이 큰 로컬 자료이며 Git 제외 대상이다. 이 폴더에서도 화면·녹음·원본 검증 JSON은 로컬 보존하고 Git에서 제외한다. 커밋에는 README와 `index.json`만 포함한다. 표의 원본 파일은 Git 체크아웃만으로 제공되지 않는다.

이번 재분류 후 새로 얻은 화면·수치는 [재분류 기록](../../reorganization/README.md)에 분리한다. 과거 JSON 안의 경로·해시를 최신 값으로 고치지 않는다.
