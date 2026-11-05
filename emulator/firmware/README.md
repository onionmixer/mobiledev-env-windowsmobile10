# Lumia 세로 화면용 SeaVGABIOS

원본: [SeaBIOS rel-1.16.3](https://github.com/coreboot/seabios/tree/a6ed6b701f0a57db0569ab98b0661c12a6ec3ff8), 커밋 `a6ed6b701f0a57db0569ab98b0661c12a6ec3ff8`.

`CONFIG_DISPLAY_BOCHS`의 고정 프레임버퍼 기능은 QEMU EDID의 기본 해상도를 사용한다. 여기에 `bochs-portrait.patch`를 적용해 1024×768 등 작은 호환 모드의 광고를 제외했다. 고정된 프레임버퍼를 쓰면서 작은 모드가 선택되면 Windows가 화면 위쪽 일부에만 그리기 때문이다.

`VGA,xres=1080,yres=1920,romfile=...`과 함께 사용한다. Microsoft SDK 이미지나 Windows 드라이버를 수정하지 않는다.

```bash
bash tools/build_portrait_firmware.sh
```

프로젝트 루트에서 실행한다. 출력은 `emulator/artifacts/firmware/vgabios-bochs-portrait.bin`이다. 소스와 패치·빌드 설정을 이 작업 폴더에서 재현할 수 있으며, 생성한 바이너리는 Git에서 제외한다. SeaVGABIOS 소스의 라이선스는 LGPL-3.0이며 원본 `emulator/third_party/seabios/COPYING.LESSER`, `COPYING`에 있다. 현재 빌드 디렉터리는 `emulator/build/seabios`다.

## 라이선스

이 폴더의 `bochs-portrait.patch`와 `bochs-portrait.config`는 SeaBIOS 소스의 파생물이므로 상위 저장소의 MIT가 아니라 **LGPL-3.0-or-later**를 따른다. 전문은 `COPYING.LESSER`(LGPL-3.0)와 이를 참조하는 `COPYING`(GPL-3.0)이다.
