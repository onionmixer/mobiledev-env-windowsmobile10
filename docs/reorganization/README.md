# 2026-11-05 재분류 기록

이 폴더의 PNG·PPM·JSON은 호스트별 로컬 검증 기록이며 Git에서 제외한다. 이 README만 커밋에 포함하므로, 원본 자료가 없는 체크아웃에서도 아래 내용을 작업 기록으로 읽을 수 있다.

실행 도구는 `tools`, 검증 문서와 선별 증거는 `docs`, 시뮬레이터 구성과 큰 생성물은 `emulator`로 모았다. 루트에는 [README](../../README.md), [HOWROUSE](../../HOWROUSE.md), [HISTORY](../../HISTORY.md)를 둔다.

## 경로 대응

| 이전 | 현재 |
| --- | --- |
| `run_simulator.sh` | `tools/run_simulator.sh` |
| `artifacts/` | `emulator/artifacts/` |
| `runtime/` | `emulator/runtime/` |
| `reference/` | `emulator/third_party/` |
| `profiles/`, `manifests/` | `emulator/profiles/`, `emulator/manifests/` |
| `firmware/`, `qemu-build/` | `emulator/firmware/`, `emulator/qemu-build/` |
| 외부 소스 내부의 기존 QEMU·SeaBIOS 빌드 디렉터리 | `emulator/build-archive/` |
| 새 빌드 디렉터리 | `emulator/build/qemu/`, `emulator/build/seabios/` |

실행기의 루트 계산·기본 경로, 빌드 스크립트·프로필 참조·Git 제외 경로를 수정했다. 실행 래퍼는 호출하는 현재 디렉터리와 무관하게 프로젝트 위치를 찾는다. 외부 저장소의 검토 파일 목록은 그 저장소 내부 경로이므로 프로젝트 이동 경로를 접두사로 붙이지 않았다.

## 디스크 보존

`pre-move.json`은 QEMU 중지 후 이동 전 파일·qcow2 정보를 담고, `migration.json`은 변경 후 backing chain과 비교 결과를 담는다. 중지는 QMP quit이었으며 Windows 정상 종료라고 간주하지 않았다.

기준·현재 작업·세로 화면 시험 전 디스크의 `qemu-img check`를 먼저 수행했다. 현재 overlay는 바꾸기 전에 `emulator/runtime/layout-backup/disk-before-layout.qcow2`로 복사했다. 기준 디스크의 SHA-256은 이동 전후 `052ec05e2d4a3a4683827869a44d809173d6e44771664cbc41e9bedac50d7125`로 같았다.

동일 기준 디스크를 확인한 후 오프라인 상태에서 `qemu-img rebase -u`로 backing 메타데이터만 다음과 같이 고쳤다.

- 현재 `disk.qcow2`: `base.qcow2`.
- `experiments/before-portrait.qcow2`: `../base.qcow2`.

변경 후 두 overlay의 qcow2 검사와 backing chain 확인을 통과했다. 현재 overlay와 수정하지 않은 이동 전 복사본의 게스트 가시 내용도 `qemu-img compare`로 비교했다. 복사본에는 이전 절대 backing 경로가 남아 있어 JSON block 옵션으로 동일한 새 위치의 기준 디스크를 명시했다. 결과는 **`Images are identical.`**였다. 이 비교는 재시작 전 오프라인 시점의 결과다. 이후 Windows 실행에 따른 작업 디스크 변경은 정상이다.

이동 전 복사본은 독립 완전 디스크가 아니다. 기준 디스크 없이 바로 실행하거나 이전 절대 경로를 무시해 복구하면 안 된다. 세로 화면 시험 전 overlay도 최신 설정 전체를 담은 백업이 아니다.

## 빌드·증거 보존

이전 생성 빌드에는 절대 경로가 들어 있으므로 보관용으로 분리했다. 수정된 두 빌드 스크립트를 실제 실행하여 새 디렉터리에서 모두 빌드했다. 로그는 `emulator/build/logs/seabios-reorganized.log`, `qemu-reorganized.log`다. 소스 커밋과 패치는 이전과 동일하며 빌드 경로·시각 등에 따라 바이너리 해시는 달라졌다.

| 새 생성물 | SHA-256 |
| --- | --- |
| SeaVGABIOS | `dab8520c9740f8c2bf6e1f8849cf111098d2d71c93537d0565ba332f29a36f75` |
| QEMU | `4f34009426de1503fa95d75c05b6d8ba8052ef0d0babe66a11d638273dbf0be6` |

선별한 과거 증거 17개는 [증거 목록](../evidence/2026-11-05/README.md)에 복사·해시 기록했다. 그 외 기존 화면·녹음·통신 기록은 `emulator/runtime/experiments/raw-evidence`, 이전 PID·명령·창 좌표·로그는 `emulator/runtime/history/pre-reorganization`에 보관했다. SDK 분석용 raw·NTFS·이전 수동 다운로드 설정은 `emulator/artifacts/diagnostics/sdk-14393`에 두었다. 이 수동 설정의 오래된 경로는 현행 실행 지침이 아니다.

기존 `import.json`·`display-input-validation.json`도 과거 기록 폴더에 보관하고 현재 실행 폴더의 중복 복사본은 동일함을 대조한 뒤 정리했다. SDK 캐시의 `image.json`에는 준비 당시의 원본 경로가 남아 있다. 이는 생성 당시 영수증이며 현재 실행할 디스크 경로를 결정하는 설정 파일이 아니다.

## 이동 후 실행 검증

새 경로의 로컬 QEMU·VGA ROM·작업 overlay로 KVM을 실행했다. `restart-frame.png`에서 Windows 시작 화면이 1080×1920 전체 영역을 사용하는 것을 확인했다. GTK 기록은 배율 0.5, 영상 540×960, 당시 메뉴 포함 클라이언트 540×987이다. 이 창 크기는 호스트 환경에 따른 관측값이다.

기계 판독 결과는 `post-move.json`에 기록한다. `last-command.json`의 `boot_verified: false`는 런처가 OS 부팅을 자동 판정하지 않는다는 고정 기록이며, 수동으로 확인한 시작 화면과 별개다. 재분류는 새 앱 배포나 오디오 PCM 재시험을 수행했다는 뜻이 아니다.

실제 X11 버튼 패널은 104×400으로 확인했다. 이후 사용자 요청으로 버튼·제목·상태 안내를 영어로 바꾸고 QEMU PID를 유지한 채 패널만 교체했다. 영어 패널 화면（로컬 파일: `english-panel.png`）에서 7개 라벨이 잘리지 않고 보이는 것을 확인했다. 변경 전 재실행 패널（로컬 파일: `restart-panel.png`）과 과거 한국어 증거는 그대로 보존했다. 이 변경은 다국어 선택 기능을 추가한 것이 아니다.

Device Portal은 새 실행에서도 `https://127.0.0.1:5443/authenticate.htm` HTTP 200을 확인했다. 자동 검사 7개, 셸 구문 검사, `/tmp`에서의 실행 래퍼 dry-run, 외부 소스 변경의 공백 검사도 통과했다. 샌드박스에서 수행한 dry-run·doctor의 KVM 미노출 결과는 실제 호스트 KVM 실행 결과와 구분한다.
