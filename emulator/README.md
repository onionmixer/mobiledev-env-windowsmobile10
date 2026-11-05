# 시뮬레이터 구성과 생성물

실행은 프로젝트 루트의 [HOWROUSE](../HOWROUSE.md)를 따른다. 이 폴더는 Lumia 보드 에뮬레이터가 아니라 x86 Windows 10 Mobile SDK 게스트를 위한 구성이다.

| 폴더 | 역할 |
| --- | --- |
| `profiles/` | 목표 기기 사양과 현재 검증 상태. 모든 항목이 자동 적용되는 실행 설정은 아님 |
| `manifests/` | SDK payload·조립 순서·해시·참고 소스 버전 |
| `firmware/` | 세로 화면용 SeaVGABIOS 패치·설정·설명 |
| `qemu-build/` | 한 접점 USB 터치 QEMU 패치·버전 고정 정보 |
| `third_party/` | 외부 소스 체크아웃. 자체 변경은 위 패치와 별도 실행 도구로 관리 |
| `artifacts/` | 공식 SDK 캐시, 생성 QEMU·ROM, `diagnostics/` 분석용 복사본 |
| `runtime/` | 기준·작업 디스크, 현재 로그·PID·QMP 관련 상태 |
| `build/` | 현재 경로의 빌드 디렉터리·로그 |
| `build-archive/` | 이동 전 절대 경로를 포함한 생성 빌드 보관. 재빌드에 사용하지 않음 |

큰 생성물·외부 소스·실행 데이터는 Git에서 제외한다. 재현에 필요한 스크립트·패치·매니페스트는 제외하지 않는다. 현재 실행 데이터와 보존한 과거 로그·실험 자료는 `runtime/history`, `runtime/experiments`로 구분한다. 디스크 연결·백업 한계는 [재분류 기록](../docs/reorganization/README.md)을 확인한다.
