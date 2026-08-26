# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

HrFluentWidgets is a PySide6 widget library for industrial AOI (Automated Optical Inspection) vision systems — an in-house extension layer on top of `qfluentwidgets` (PySide6-Fluent-Widgets). It provides image-display graphics views/scenes, editable overlay items with calipers, JSON-backed parameter config, camera/recipe/calibration/setting interfaces, role-based login, and motion-control (zauxdll) IO widgets. UI strings, comments, and commit messages are in Chinese.

## Commands

- **Install for development**: `pip install -e .` (requires Python ≥ 3.12; deps: `PySide6`, `PySide6-Fluent-Widgets`, `pandas`)
- **Run demos** — always from the repo root, since demos insert the cwd into `sys.path` and then `os.chdir()` into their own directory:
  - Full app demo: `python examples/AoiWindow/Demo.py`
  - Component demos: `python examples/Graphicsview/demo.py`, `examples/CameraView/demo.py`, `examples/Login/demo.py`, `examples/Calibration/demo.py`, `examples/GroupCameraView/demo.py`, `examples/MatchView/demo.py`, `examples/LineDefectView/demo.py`, `examples/motion/iowidget/demo.py`, and the per-widget demos under `examples/Widget/`
- There is no test suite and no linter/formatter configured; verification is done by launching the demos.

## Architecture

Three layers, each re-exporting everything via `*` imports (importing `hrfluentwidgets` pulls in all of `common` + `components`; `motion` is NOT re-exported and must be imported explicitly: `from hrfluentwidgets.motion import IoWatchWidget, IoOptionWidget`):

- **`hrfluentwidgets/common/`** — primitive building blocks:
  - `GraphicsItem/` — `QGraphicsItem` subclasses (`GraphicsRectItem`, `GraphicsPolygonItem`, `GraphicsLineItem`, `GraphicsRotatedRectItem`, `GraphicsBezierCurveItem`, `GraphicsCrossItem`) plus caliper variants mixed with `CaliperBase` (drawn edge-detection rectangles, e.g. `GraphicsCaliperRectItem`). Each item pairs with a plain-data class (`RectItemData`, `PolygonItemData`, `LineItemData`, `*Caliper*ItemData`…) holding its serializable state.
  - `GraphicsScene/` — `GraphicsScene` (image + overlay items, Ctrl+S save image, Ctrl+A select all, Delete removes with `itemRemoved` signal) and `GraphicsItemScene` (edit mode: set `addItemFunc` + `setEditMode(True)` to draw new items; emits `itemFinished`/`itemChanged`).
  - `GraphicsView/` — `GraphicsView` base plus capability **mixins** (`DropImageBase`, `DisplayCrossBase`, `DisplayPixelBase`, `TorchBase` touch gestures, `NoImageViewBase`, `AutoFitViewBase`); concrete views are composed from mixins, e.g. `InterfaceView = DropImageBase + DisplayCrossBase + DisplayPixelBase + GraphicsView`. `TorchBase` implements two-finger pinch zoom / single-finger pan for touchscreens.
  - `Param/` — config registry: `ParamConfig` (a `QObject` holding `qfluentwidgets.ConfigItem`s keyed by `"group.name"`, persisted to `config/param.json`) plus custom Qt-geometry validators/serializers (`QRectF`, `QPointF`, `QPolygonF`, range values) and `*ItemConfigItem` classes that serialize graphics-item data (e.g. `RectItemConfigItem`).
  - `Widget/` — ready-made controls: `ParamItem` subclasses (`SpinBoxItem`, `DoubleSpinBoxItem`, `RangeSpinBoxItem`, `RangeDoubleSpinBoxItem`, `SwitchItem`, `ComboxItem`) bound to a `ParamConfig` key; `RecipeManager` dialogs; `LogWidget` + module-global `log` (logging to `logs/logRecord.log`, rotating at midnight); `ColorPicker`/`ColorPalette`; custom sliders/spinboxes; `ProgressPushButton`; `FlyoutDialog`; `GraphicsCaliperRectParam`.
  - `HrIcon/` — custom `FluentIconBase` enum, svgs at `:/hricon/icons/`.
  - `_rc/` — Qt compiled resources (`resource.py` generated from `resource.qrc`); see Resources below.

- **`hrfluentwidgets/components/`** — composite widgets and application-level interfaces:
  - `CameraView/` — `MatchView`, `CameraView`, `CameraResultView`, `CameraEditView`, `GroupCameraView` (grid of cameras, built on `HeaderCardWidget` with a `CommandBar` of view actions).
  - `ParamWidget/` — parameter panels: `RecipeParamWidget` (scrollable `ParamItem` list), `RecipeParamWithViewWidget` (adds a `MatchView` + edit buttons drawing ROIs into a scene), and `GraphicsItemData.py` defining `SupportBase` subclasses (`RectItemSupport`, `PolygonItemSupport`, …) with `setData`/`getData`/`genData`/`connectSignals` bridging between a `QGraphicsItem` and its data class. `GraphicsParamWidget.py` (`RecipeUserItemParamWidget`, `RecipeUserItemWithViewParamWidget`) lets apps register custom item types via `addItemType(name, factory, support)`.
  - `Login/` — `LoginWidget`, `LoginWidgetWithRole` (role list + `verifayFun`/`afterLoginFun` hooks).
  - `Window/` — `AoiWindow` (subclass of `MSFluentWindow`); `addSubInterface(interface, icon, text, Role=n, ...)` and `setRole()` gate navigation pages by role (0 操作员 / 1 工程师 / 2 厂商 / 3 超级管理员).
  - `interface/` — full pages: `DetectInterface` (camera grid + log widget + result display), `RecipeInterface`/`RecipeMatchInterface`/`RecipeWithItemInterface` (camera ↔ param-widget pairing via `addCamera`, `RecipeManager` for switching recipes), `CalibrationInterface` (chessboard / nine-point calibration, `CalibrationBase`), `SettingInterface` (qfluentwidgets setting cards; accepts an `IoWatchWidget`/`IoOptionWidget` class and IO config via `setIoWatchWidget`/`setIoConfig`), `SettingConfig` (`QConfig` subclass, singleton `setting_cfg`, loaded from `config/config.json`).

- **`hrfluentwidgets/motion/`** — industrial motion control, Windows-only: `os.add_dll_directory()` loads `zauxdll.dll`/`zmotion.dll` from `motion/thirdparty/`; `ZAUXDLL` (ctypes wrapper, `ZAux_Execute` etc.); `IoWatchWidget`/`IoOptionWidget` display/set IO states (config from Excel files via pandas, e.g. `input_ioconfig.xlsx` in the demo).

## Key patterns

- **Item ↔ Data ↔ Config**: every overlay item has a serializable data class and a matching `ConfigItem` (with validator + serializer) so ROIs persist in `param.json`; the `*ItemSupport` classes in `components/ParamWidget/GraphicsItemData.py` handle the item↔data sync inside the edit UI. When adding a new item type, you typically add: `GraphicsXxxItem` (common/GraphicsItem), `XxxItemData`, `XxxItemConfigItem` (common/Param), `XxxItemSupport` (components/ParamWidget), and wire `addEditBtn`/`addItemType` in the recipe widget.
- **View capabilities via mixins**: extend `GraphicsView` behavior by composing the mixin classes, not by editing the base class.
- **Config persistence**: `ParamConfig` (manual `addParam`/`load`/`set`, JSON at `config/param.json`) vs `SettingConfig`/`setting_cfg` (qfluentwidgets `qconfig.load`, JSON at `config/config.json`). Keys are `"group.name"` strings; `param_cfg` and `setting_cfg` are singletons created at import time.

## Resources (icons/images)

`.qrc` files live next to generated `resource.py` files (`common/_rc/`, `components/_rc/`, `components/interface/resource/`). The generated modules are imported as `resource` in `__init__.py` files so `:/...` paths resolve. Prefixes: `/hricon` (icons, both `_black`/`_white` theme variants) and `/resource` (images incl. `noImage.svg` placeholder used by views). After adding an asset, regenerate the `resource.py` with e.g. `pyside6-rcc resource.qrc -o resource.py`.

## Gotchas

- Demos must be launched from the repo root (they `chdir()` into their own folder at import time).
- `GraphicsItem` classes inherit `QObject`; removing an item from a scene requires `item.deleteLater()` (or `del`), or the app can crash (see git history: "GraphicsRectItem删除时会导致程序崩溃").
- The global `log` logger and `param_cfg`/`setting_cfg` singletons create/read files (`logs/`, `config/`) relative to the **current working directory** — run from the project root.
- The motion subpackage is Windows-only; importing it outside Windows fails at DLL load.
