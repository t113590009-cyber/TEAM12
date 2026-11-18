# 選課與課表規劃系統（TEAM12）

計算機程式設計團體作業。以 Python 開發的命令列選課與課表規劃系統，目前為期中系統 v1.0（F1～F6）。

## 環境需求

- Python 3.10 以上
- pytest（只使用 Python 標準函式庫與 pytest）

安裝 pytest：

```
python -m pip install pytest
```

## 如何執行

在專案根目錄執行：

```
python main.py
```

啟動時會從 `data/` 載入資料（缺檔或壞資料會顯示錯誤，但程式不中止），離開時會自動存檔。

> Windows 若 `python` 指令無法使用，可改用 `py main.py`。

## 如何執行測試

```
python -m pytest
```

依分類執行：

```
python -m pytest -m normal
python -m pytest -m boundary
python -m pytest -m error
```

## 專案目錄

```
TEAM12/
├─ main.py            # 唯一入口，只放選單與輸入輸出
├─ src/
│  ├─ common/         # 時段工具、check_room_conflict、回傳結構、State、驗證函式
│  ├─ f1_data.py      # F1 課程、學生、教室資料管理
│  ├─ f2_enrollment.py# F2 選課檢查
│  ├─ f3_schedule.py  # F3 個人課表與空閒時段
│  ├─ f4_activity.py  # F4 活動與教室配置
│  ├─ f5_filter.py    # F5 課程篩選
│  └─ f6_storage.py   # F6 儲存與載入
├─ tests/             # pytest 測試，tests/fixtures/bad/ 為壞資料檔
├─ data/              # 正式資料（JSON，五個檔）
└─ docs/              # 需求規格、資料格式書、Use Case、系統架構、工作分解表等
```

## 設計重點

- 所有系統資料放在 `State`，由 `main.py` 建立並傳入各函式，不使用全域變數。
- 核心函式不使用 `input()`、`print()`，一律以回傳值輸出；顯示格式由 `main.py` 處理。
- 所有函式回傳 `{ok, data, errors}`，業務錯誤不拋例外；檢查類函式一次回報全部錯誤。

## 開發規範

- 分支：`feature/<功能>-<說明>`、`fix/...`、`test/...`、`docs/...`；`main` 只放可執行版本，不直接 push。
- Commit：`<類型>(<功能>): <一句話說明>`，例如 `feat(F4): 新增活動教室配置`。
- 合併進 `main` 前，至少一位非原開發者 Review，並通過全部測試。

詳見 `docs/` 內的 Coding Convention 與資料格式書。
