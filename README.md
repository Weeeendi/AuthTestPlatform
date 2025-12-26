<p align="center">
</p>
  <h1 align="center">
  Vehiclink auth&test platform
</h1>
<p align="center">
  A fluent design widgets library based on PyQt5
</p>


  <a href="https://pypi.org/project/PyQt-Fluent-Widgets" target="_blank">
    <img src="https://img.shields.io/pypi/v/pyqt-fluent-widgets?color=%2334D058&label=Version" alt="Version">
  </a>

  <a style="text-decoration:none">
    <img src="https://img.shields.io/badge/License-GPLv3-blue?color=#4ec820" alt="GPLv3"/>
  </a>

  <a style="text-decoration:none">
    <img src="https://img.shields.io/badge/Platform-Win32%20|%20Linux%20|%20macOS-blue?color=#4ec820" alt="Platform Win32 | Linux | macOS"/>
  </a>




## 简介
使用该软件可以对 Vbox 等 Iot 设备进行授权和产测协议


> **注意**
> 设备的授权和测试功能需要设备支持，请先确认设备是否支持，是否已经集成了测试协议.

## 文档
如果想要了解关于产测的细节及规定请访问我们的文档

[<云迹物联设备产测协议>](https://funhez50ho.feishu.cn/wiki/wikcnuglFOxcuI0V6AQSltsIPvf)


## 产测操作视频
查阅此视频 [▶ 云迹物联设备产测上位机操作视频](https://www.bilibili.com/video/BV12c411L73q) ，该视频展示了如何使用云迹产测上位机 🎉

## 导出数据
该工具支持导出数据，导出数据时，先选定导出的日期和对应的pid，会自动将数据导出到本地，并生成一个压缩包，压缩包中包含所有数据，包括设备信息、测试结果、测试日志等。

> **提示**
该工具支持的操作系统为：windows10以上

## 开发者指南（简版）
- 运行（开发）：
  ```bash
  pip install -r requirements.txt
  python main_page.py
  ```
- Qt Designer（带 Fluent 组件）：
  ```bash
  python tools/designer.py
  ```
- 构建发行版（自动递增 build 并更新 spec）：
  ```bat
  build.bat
  ```
- 入口与页面：入口在 [main_page.py](main_page.py)，先显示登录窗体，再进入主窗体，包含页面：[授权与测试](view/AuthTest_interface.py)、[设置](view/settingConf_interface.py)。
- 版本与打包：版本集中在 [version_manager.py](version_manager.py) 管理，读写 [resources/version/version.json](resources/version/version.json)；构建脚本见 [build.py](build.py) 与 [update_version.py](update_version.py)。
- 配置：系统参数位于 [resources/config/sysConfig.json](resources/config/sysConfig.json)（日志级别、设备类型、授权地址与账号、打印次数等）；测试项位于 `resources/config/userConfig.json`，在设置页可编辑（字段示例参见代码注释与 UI）。
- 串口与测试：串口线程 [baseUart.py](baseUart.py)（`QThread` + `pyqtSignal`），测试流程线程 [userTest.py](userTest.py)（发送帧、解析响应、云端注册、导出 CSV）。发送帧使用 [baseUtils.py](baseUtils.py) 的 `uchar_checksum()`、`HexStringToByte()` 等工具。
- 日志与编码：日志写入 `Logs/YYYY-MM-DD.log`，编码 GBK；日志级别由 `sysConfig.json` 的 `current_logger_level` 控制，初始化在 [baseLogger.py](baseLogger.py)。
- 资源路径：所有打包资源使用 `baseUtils.resource_path()` 获取路径，避免 PyInstaller 环境下路径错误。
- UI 反馈：统一用 QFluentWidgets 的 `InfoBar`/`Flyout` 等组件；新增页面通过 `FluentWindow.addSubInterface()` 接入（参考 `initNavigation()`）。
- 快速增加测试项：在 `resources/config/userConfig.json` 追加项（`funName/dspName/cmd/enable/data/rev_dict/interval(ms)/retry/process`），`cmd` 为不含空格的十六进制字符串；`process` 为 `ALL` 或 `4G`。

更多细节（架构、约定、外部集成等）见 [.github/copilot-instructions.md](.github/copilot-instructions.md)。

## License
该工具遵循 [GPLv3](./LICENSE).
