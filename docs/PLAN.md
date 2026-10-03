# DOCX / PPTX → Markdown 實作計畫

## 原理

`.docx` / `.pptx` 本身就是 zip。Python 的 `zipfile` 可以直接打開，不需要先改名成 `.zip` 再解壓。

| 需要的資訊 | DOCX 位置 | PPTX 位置 |
|---|---|---|
| 內文 / 結構 | `word/document.xml` | `ppt/slides/slideN.xml` |
| 圖片檔 | `word/media/*` | `ppt/media/*` |
| 圖片 ↔ 位置對應 | `word/_rels/document.xml.rels`（`r:embed="rIdX"` → `media/imageN.png`） | `ppt/slides/_rels/slideN.xml.rels` |
| 標題樣式 | `word/styles.xml` | placeholder `type="title"` |
| 清單種類 | `word/numbering.xml` | `a:pPr lvl` / `a:buChar` |
| 投影片順序 | — | `ppt/presentation.xml` 的 `sldIdLst` |

圖片會在 XML 錨點所在的位置輸出成 `![](<stem>_media/imageN.png)`，所以順序不會跑掉。

只用 Python 標準函式庫（`zipfile`、`xml.etree`、`argparse`），沒有額外相依套件。

## 使用方式

```bash
python src/main.py report.docx slides.pptx -o output/
```

## Issues

> `gh` 的 token 已失效，所以 issues 先寫在這裡。執行 `gh auth refresh -h github.com` 重新登入後，就能用最下方的指令一次建立。

### #1 OOXML 套件讀取與關聯解析 ✅
- 用 `zipfile` 直接讀取 `.docx` / `.pptx`
- 解析 `_rels/*.rels`，把 rId 對應到 zip 內的路徑或外部 URL
- 把圖片匯出到 `<stem>_media/`

### #2 DOCX 文字與結構 ✅
- 段落，以及粗體 / 斜體（相鄰且格式相同的 run 會合併）
- 標題：`Heading N` / `Title` 樣式名稱；樣式名稱被在地化時，改看 outlineLvl
- 清單：段落直接帶的 numPr ＋ 樣式帶的 numPr（List Bullet / List Number），依 `numbering.xml` 判斷是 bullet 還是 ordered，並支援巢狀
- 超連結、換行、tab、修訂中的插入（`w:ins`）、內容控制項（`w:sdt`）

### #3 DOCX 圖片、表格、文字方塊 ✅
- `w:drawing`（`a:blip`）與舊版 `w:pict`（`v:imagedata`）圖片
- 略過 `mc:Fallback`，避免同一張圖輸出兩次
- 表格會轉成 GFM table，`gridSpan` 會補空欄，`|` 會跳脫
- 文字方塊（`w:txbxContent`）

### #4 PPTX 轉換 ✅
- 依 `sldIdLst` 決定投影片順序，每張投影片輸出成 `## 標題`（沒有標題時用 `## Slide N`）
- 內文 placeholder 輸出成巢狀清單，一般文字方塊輸出成段落
- 圖片（`p:pic`）、表格（`a:tbl`）

### #5 CLI 與錯誤處理 ✅
- `python src/main.py FILE... [-o DIR]`
- 遇到 `.doc` / `.ppt` 舊格式、壞掉的 zip 時，在 stderr 顯示錯誤並以 exit code 1 結束；其他檔案照常繼續轉換

### #6 尚未實作（等有實際需求再做）
- [ ] 頁首、頁尾、註腳、批註
- [ ] PPTX 依 `a:off` 座標排序 shape（目前依 XML 順序）、講者備忘稿、shape 上的超連結
- [ ] 合併儲存格（vMerge）真正合併：Markdown table 本身不支援，可能要改輸出 HTML table
- [ ] EMF/WMF 圖片轉 PNG（瀏覽器無法顯示這兩種格式）
- [ ] 特殊字元跳脫（例如段落開頭的 `#`、`*`）
- [ ] 同一批轉換中，主檔名相同的 `a.docx` 與 `a.pptx` 會輸出到同一個 `a.md`

### 一次建立上面的 issues

```bash
for t in "OOXML 套件讀取與關聯解析" "DOCX 文字與結構" "DOCX 圖片、表格、文字方塊" "PPTX 轉換" "CLI 與錯誤處理" "未實作項目追蹤"; do gh issue create --title "$t" --body "見 docs/PLAN.md"; done
```
