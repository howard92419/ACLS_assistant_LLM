## ACLS Assistant CLI 專案

### 專案簡介

ACLS Assistant CLI 是一個命令行工具，旨在協助到院前急救人員（ACLS 專業救護員）在緊急情況下進行事件記錄、藥物使用追蹤、計時器管理以及根據 AHA-ACLS 流程提供下一步處置建議。本專案利用 OpenAI 的能力來理解複雜的急救指令和情境，並將數據儲存在本地 SQLite 資料庫中。

### 功能特色

* **智能建議與記錄**：利用 OpenAI 模型解析使用者輸入，提供急救建議，並自動將事件格式化為完整的 ACLS 記錄（例如：`epi 1mg ivp` 應記錄為 `Epinephrine 1mg IV-push`）。
* **上下文感知**：OpenAI 模型會參考過去的急救事件記錄來提供更準確的下一步建議。
* **急救事件記錄**：重要的急救事件、藥物、劑量、途徑等資訊會被記錄到本地 SQLite 資料庫 (`events.db`) 中，並標註時間（使用 `Asia/Taipei` 時區）。
* **計時器管理**：可根據使用者指令（如「計時 X 分鐘」）啟動非阻塞式計時器。計時結束時會發出提示音（僅限部分平台）並執行回呼函數。
* **資料匯出**：支援將所有急救紀錄匯出成 Excel 檔案（`.xlsx`）。
* **CLI 介面**：簡單的命令列操作，方便在急救現場快速輸入和獲取資訊。

### 環境與依賴

本專案使用 Python 撰寫，需要安裝以下函式庫：

* `openai`
* `python-dotenv`
* `pandas`
* `openpyxl`
* `pytz`

您可以使用 `requirements.txt` 檔案來安裝所有依賴：
```bash
pip install -r requirements.txt

## 快速開始

### 1. 設定環境變數

建立一個 `.env` 檔案，並在其中填入您的 OpenAI API Key：

```dotenv
OPENAI_API_KEY="YOUR_API_KEY_HERE"

如果未設定 `OPENAI_API_KEY`，系統將無法使用智能解析功能。

### 2. 運行程式

從專案的根目錄運行 `main.py`：

```bash
python main.py

### 3. CLI 指令

程式啟動後會自動初始化資料庫並清除舊記錄。您可以輸入以下指令：

| CLI 指令 | 說明 |
| :--- | :--- |
| `病人OHCA` | 觸發 OHCA 事件記錄，並提示 CPR 與 AED 準備。 |
| `epi 1mg ivp` | 智能解析並記錄為 `Epinephrine 1mg IV-push`，並提供下一步建議。 |
| `幫我計時3分鐘` | 智能解析並啟動一個 180 秒的計時器。 |
| `show logs` / `顯示紀錄` | 顯示最近的事件記錄（XML 格式）。 |
| `export logs` / `匯出紀錄` | 將所有記錄匯出成 `ACLS_logs_YYYYMMDD_HHMMSS.xlsx` 檔案。 |
| `help` / `h` / `?` | 顯示可用指令。 |
| `exit` / `quit` / `q` | 結束程式。 |

## 專案結構

| 檔案名稱 | 說明 |
| :--- | :--- |
| `main.py` | 專案主程式，包含 CLI 迴圈、OpenAI 溝通邏輯、事件處理和資料匯出。 |
| `requirements.txt` | Python 函式庫依賴列表。 |
| `utils/logger.py` | 資料庫 (SQLite) 操作模組，負責初始化、事件記錄、列出和清除記錄。 |
| `utils/timer.py` | 非阻塞式計時器模組，使用 `threading` 實現背景計時，並在結束時執行回呼函數。 |
| `utils/__init__.py` | `utils` 套件的初始化檔案，用於暴露 `logger` 和 `timer` 模組中的函式。 |
| `events.db` | (執行後產生) SQLite 資料庫檔案，用於儲存急救事件記錄。 |
