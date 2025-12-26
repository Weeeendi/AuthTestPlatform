# AI Coding Agent Guide — Vehiclink Auth & Test Platform

This repo is a Windows-focused PyQt5 app for IoT device authorization and factory testing, skinned with QFluentWidgets, packaged via PyInstaller, and integrated with serial devices and BarTender label printing.

## Big Picture
- Entry point: [main_page.py](../../main_page.py). Shows `LoginWindow` then main `FluentWindow` with pages: [AuthTest](../../view/AuthTest_interface.py) and [Settings](../../view/settingConf_interface.py).
- Versioning: Centralized in [version_manager.py](../../version_manager.py) reading/writing [resources/version/version.json](../../resources/version/version.json) (used to paint window titles, spec name, and releases).
- Runtime config: Primary sources are in [resources/config/](../../resources/config). System: [sysConfig.json](../../resources/config/sysConfig.json). Test items: `userConfig.json` (created/managed by the app; see Settings and `testSetTableWidget`).
- Serial I/O: `QThread`-based worker [baseUart.py](../../baseUart.py) and UI coordination in [view/AuthTest_interface.py](../../view/AuthTest_interface.py).
- Factory flow: Long-running test worker [userTest.py](../../userTest.py) drives commands over UART, calls cloud registration via `requests`, updates UI via signals, and exports CSV via [baseUtils.addToRegList()](../../baseUtils.py).
- Printing: Windows-only BarTender integration via `pythonnet`/`clr` in [basePrinter.py](../../basePrinter.py), using [resources/yunJi_tag.btw](../../resources/yunJi_tag.btw).

## Dev Workflows
- Run (dev):
  ```bash
  pip install -r requirements.txt
  python main_page.py
  ```
- Launch Qt Designer with widgets preloaded: `python tools/designer.py` (see [tools/designer.py](../../tools/designer.py)).
- Logs: written to `Logs/YYYY-MM-DD.log` in GBK encoding. Level comes from [resources/config/sysConfig.json](../../resources/config/sysConfig.json) → `current_logger_level`. Logger setup in [baseLogger.py](../../baseLogger.py).

## Build & Versioning
- Bump version.json build and package:
  ```bat
  build.bat
  ```
  - Steps: `update_version.py --increment build --only-json` → `build.py` → updates `main.spec` app name with current version → `pyinstaller main.spec`.
- Programmatic version access: prefer `from version_manager import get_version_string, DEFAULT_VERSION_STRING` and set `APP_VERSION` like in [main_page.py](../../main_page.py#L16-L31).

## Configuration Model (authoritative)
- System settings: [sysConfig.json](../../resources/config/sysConfig.json)
  - Keys: `current_logger_level`, `auth_params`, `current_auth_param`, `current_device_type` (`BLE`/`BLE&4G`/`4G`), `burning_pid`, `tag_print_times`, `reg_urls` items with `desc/url/host/port`, `current_auth_account/current_auth_password`.
  - Read/Write: [data_manage.py](../../data_manage.py) and [view/settingConf_interface.py](../../view/settingConf_interface.py) (toggle edit button to enable controls; save happens on toggle off).
- Test items (factory steps): `resources/config/userConfig.json`
  - Structure per item: `{"funName","dspName","cmd","enable":bool,"data","rev_dict":json_str,"interval(ms)":int,"retry":int,"process":"ALL|4G"}`.
  - Consumed by [userTest.py](../../userTest.py) via `_init_param_from_json()`/`_init_obj_json()`; ensure `cmd` is hex string without spaces, and `process` matches device type.

## Architecture & Patterns
- Resource paths: always use `baseUtils.resource_path()` to support PyInstaller; never `os.path.abspath(__file__)` for packaged assets. Example: [main_page.py](../../main_page.py#L69-L71).
- Threading: long operations in `QThread` with `pyqtSignal` bridging to UI. Patterns in [baseUart.py](../../baseUart.py) and [userTest.py](../../userTest.py). Ensure proper `.quit()`/`.wait()` on shutdown (see `closeEvent()` in [AuthTest_interface](../../view/AuthTest_interface.py#L149-L160)).
- UART framing: helpers in [baseUtils.py](../../baseUtils.py): `byteToHexString()`, `HexStringToByte()`, `uchar_checksum()`; send path composes frame then emits `uartWrite_sinOut` (see `userTestSend()` in [userTest.py](../../userTest.py#L167-L183)).
- UI integration: Add pages via `addSubInterface()` on `FluentWindow` (see `initNavigation()` in [main_page.py](../../main_page.py#L176-L209)). Use QFluentWidgets InfoBar/Flyout for user feedback.
- Printing: instantiate `BasePrinterThread` once, call `change_PrintCnt()` and `insertMsg()`; only when printer checkbox is enabled (see [AuthTest_interface.py](../../view/AuthTest_interface.py#L120-L147) and printing hookup around start).

## External Integrations
- Cloud registration: `requests` within [userTest.py](../../userTest.py) using `regUrl`, `clientId/clientSecret` from `sysConfig.json`. Device type and region influence command set and flow.
- Data export: CSVs written under `output/` with format `regList_<PID>_<YYYYMMDD>.csv`; dedup by `IMEI` or `DID` depending on context (see `addToRegList()` in [baseUtils.py](../../baseUtils.py)).

## Conventions & Gotchas
- Use `APP_VERSION` from `version_manager`; don’t hardcode window titles.
- Paths are Windows-first; use double backslashes in literals or `resource_path()`.
- Don’t block UI thread; use signals to drive UI (InfoBars, progress, logs).
- Logs are GBK-encoded; mind Unicode when tailing.
- When adding settings, wire both the editor (in `data_manage.SysItemEditFactory`) and the consumer (e.g., `AuthTest_interface.updateSetting`).

## Quick Examples
- Add a new page: create a `QWidget` and call `self.addSubInterface(widget, FIF.X, 'Title', position)` in `initNavigation()`.
- Add a test step: append to `resources/config/userConfig.json` with a new item; set `process` to `ALL` or `4G`; verify it appears in Settings → Test Details and runs in `UserTestThread`.

> If anything above is unclear (e.g., main.spec expectations, BarTender DLL placement, or BLE/4G test matrix), tell us and we’ll refine this guide.
