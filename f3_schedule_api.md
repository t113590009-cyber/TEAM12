# F3 個人課表模組介面文件
負責人：翁恩雲
模組檔案：src/f3_schedule.py
相依模組：src/common/time_slot.py（由組員C實作）
統一回傳格式：{"ok": bool, "data": any, "errors": list[str]}

## 功能說明
F3 負責管理學生個人課表，提供新增、刪除、查詢課表項目。
時間衝突檢查直接呼叫 time_slot 的函式，不自行實作時段判斷邏輯。

## 資料結構
單一課表項目
```json
{
  "student_id": "S001",
  "course_id": "C001",
  "weekday": 1,
  "period": "2"
}
