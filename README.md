# Python-Templater

這是一個 Python 模板 Repo，支援 **Windows 與 Linux** 環境，搭配 [uv](https://github.com/astral-sh/uv)（Windows）或 venv（Linux）管理虛擬環境與套件，並預設整合 Claude Code 開發流程與 GitHub Actions CI。

## 環境需求

### Windows

| 工具 | 說明 |
|------|------|
| [uv](https://docs.astral.sh/uv/getting-started/installation/) | Python 套件與虛擬環境管理器 |
| Python 3.10.19 | 由 uv 自動下載，不需手動安裝 |
| Windows 10 / 11 | 主要執行平台 |

安裝 uv（PowerShell）：

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### Linux

| 工具 | 說明 |
|------|------|
| Python 3.10+ | 需預先安裝（`python3`） |
| pip | 隨 Python 一同安裝 |

安裝 Python（Ubuntu / Debian）：

```bash
sudo apt update && sudo apt install -y python3 python3-pip python3-venv
```

## 快速開始

### Windows

```bat
python\Windows.bat
```

### Linux

```bash
chmod +x python/Linux.sh
./python/Linux.sh
```

執行後會自動完成以下步驟：

1. 建立 `venv/` 虛擬環境
2. 升級 pip
3. 安裝 `requirements.txt` 中的所有套件

> Windows 版本會先刪除舊的 `venv/` 再重建；Linux 版本直接建立（已存在時會更新）。

## 目錄結構

```
Python-Templater/
├── .github/
│   └── workflows/
│       └── pytest.yaml      # GitHub Actions CI（push / PR 自動跑測試）
├── src/
│   └── main.py              # 程式進入點
├── tests/
│   └── test_main.py         # PyTest 測試範本
├── python/
│   ├── Windows.bat          # 建立虛擬環境並安裝套件（Windows）
│   └── Linux.sh             # 建立虛擬環境並安裝套件（Linux / CI）
├── PyTest/
│   ├── Windows.bat          # 執行 PyTest（Windows）
│   └── Linux.sh             # 執行 PyTest（Linux / CI）
├── requirements.txt         # 套件清單
├── CLAUDE.md                # Claude Code 專案設定
├── .gitignore
└── README.md
```

## 執行測試

### Windows

```bat
PyTest\Windows.bat
```

### Linux

```bash
chmod +x PyTest/Linux.sh
./PyTest/Linux.sh
```

執行後會自動：

1. 產生 `pytest.ini`（設定 `pythonpath = src`、`addopts = -v --tb=short`）
2. 以 venv 內的 Python 執行 `pytest tests`
3. 清理 `pytest.ini`（無論成功或失敗皆清理）

## 執行程式

### Windows

```bat
venv\Scripts\activate
python src\main.py
```

或不啟動直接用 uv 執行：

```bat
uv run --python venv\Scripts\python.exe src\main.py
```

### Linux

```bash
source venv/bin/activate
python src/main.py
```

## 新增套件

在 `requirements.txt` 加入套件名稱後，重新執行對應的 setup 腳本，或手動安裝：

**Windows：**

```bat
uv pip install --python venv\Scripts\python.exe <package-name>
```

**Linux：**

```bash
venv/bin/pip install <package-name>
```

## GitHub Actions CI

每次 push 到 `main` 或開啟 / 更新 Pull Request 時，CI 會自動：

1. 建立 Python 3.10 虛擬環境並安裝套件（`python/Linux.sh`）
2. 執行 `pytest tests`（`PyTest/Linux.sh`）

設定檔位於 [.github/workflows/pytest.yaml](.github/workflows/pytest.yaml)。

## 相關工具

- [uv 文件](https://docs.astral.sh/uv/)
- [Claude Code](https://claude.ai/code)
