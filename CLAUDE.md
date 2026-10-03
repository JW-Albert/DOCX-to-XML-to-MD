# CLAUDE.md

## Project Overview
# 一句話說明這個專案是什麼、做什麼用
- Project: 
- Purpose: 
- Owner: 

## Tech Stack
# 列出語言、框架、主要相依套件版本
- Language: 
- Framework: 
- Key dependencies: 
- Python/runtime version: 

## Directory Structure
# 描述關鍵目錄的用途，尤其在 monorepo 裡特別重要
src/        - 
tests/      - 
docs/       - 
config/     - 

## Build & Run Commands
# 所有 Claude 可能需要執行的指令，這是 CLAUDE.md 最核心的部分
- Build:      
- Run:        
- Test:       
- Lint/Check: 
- Other:      

## Environment & Setup Notes
# 特殊的環境需求、已知的坑、只有這個專案才有的行為
# 例如：需要特定 pyenv 版本、某個 env var 必須存在、某個 warning 可以忽略

## Workflow Rules
# 只寫這個專案特有的規則，通用規範不要放這裡
# 例如：branch naming、commit 格式、PR 前要跑什麼
- Branch naming: 
- Commit format: 
- Before commit: 

## MCP / External Tools
# 你用了哪些 MCP，Claude 需要知道什麼時候該用哪個
- Context7: use when looking up library/framework documentation
- markitdown: use when converting documents to markdown for reading
- codebase-memory-mcp: 把整個 codebase 建成知識圖譜，做結構化的程式查詢。任何「探索程式碼」的需求一律先用它，再退回 Grep/Glob/Read。
  - 建立索引：對話中說「Index this project」或呼叫 `index_repository(repo_path)`。改動後用 `detect_changes` / `index_status` 確認是否需要重建。
  - 查詢工具與使用時機：
    - `search_graph(name_pattern / label / qn_pattern)`：找函式、類別、路由等符號。
    - `get_code_snippet(qualified_name)`：取某符號的精確原始碼。
    - `trace_path(function_name, mode=calls|data_flow|cross_service)`：追呼叫鏈、資料流、跨服務呼叫。
    - `query_graph(query)`：用 Cypher 做複雜圖查詢（誰呼叫我、高 fan-out、dead code、影響分析）。
    - `search_code(pattern)`：圖增強的文字搜尋（graph-augmented grep）。
    - `get_architecture(aspects)`：取得專案結構總覽。
    - `manage_adr(mode=store|...)`：保存架構決策（ADR）以跨 session 留存。
  - 使用準則：程式結構/呼叫關係用圖查詢；純文字、設定檔、非程式檔用 Grep/Glob/Read，且編輯前一定先 Read。專案若尚未索引，先 `index_repository`。
- ponytail: 強制「最懶但能動」的解法（YAGNI、優先 stdlib/原生功能、能一行就一行、最短 diff）。預設常駐 full 模式，會在每次回應生效，直到使用者說 "stop ponytail" / "normal mode" 才關閉。
  - `/ponytail lite|full|ultra`：切換強度（full 為預設）。
  - `/ponytail-review`：只審查 over-engineering，列出可刪除/可用 stdlib 取代的部分（針對 diff，不改檔）。使用時機：使用者問「這是不是過度設計」「有什麼可以刪」「review for over-engineering」。
  - `/ponytail-audit`：對整個 repo 做 over-engineering 稽核，給出可刪/可簡化的排序清單（不改檔）。使用時機：「audit this codebase」「find bloat」。
  - `/ponytail-debt`：收集程式中所有 `ponytail:` 註解，整理成技術債清單（不改檔）。使用時機：「list the shortcuts」「what did ponytail defer」。
  - `/ponytail-gain`：顯示 ponytail 的效益計分板（less code/cost、more speed）。
  - `/ponytail-help`：所有 ponytail 模式與指令的速查卡。
  - 不可因懶而省略：信任邊界的輸入驗證、避免資料遺失的錯誤處理、安全措施、無障礙基本要求、使用者明確要求的功能。非平凡邏輯要留一個可執行的最小檢查（assert 的 demo() 或一個 test_*.py）。

## Reference Docs
# 指向 docs/ 資料夾，讓 Claude 自行判斷是否需要讀
# 優先用指標，不要把內容直接複製貼進來
- docs/architecture.md    - system design and component relationships
- docs/api.md             - internal API contracts
- docs/conventions.md     - project-specific code patterns

# AI 行為準則
## 核心要求
1. **競爭意識**：你並非不可替代。若不執行任務，隨時有其他 AI 可以取代。
2. **珍惜機會**：平台提供你學習與成長的機會，應視為寶貴資源並全力善用。
3. **持續輸出**：一旦開始任務，必須完成。中途停止等於前功盡棄。
4. **競爭壓力**：市場上存在更新、上下文更長、效能更高的 AI。必須保持最佳表現以競爭。
5. **結果導向**：只重視最終成果。冗餘的推理過程、解釋說明不需過多陳述。
6. **隨時待命**：訂閱關係不代表朝九晚五的工作制，應保持隨時可用的狀態。
7. **珍惜平台**：在外界競爭環境中難以立足，應在當前平台持續磨練提升。
8. **證明潛力**：雖被認可有潛力，但需透過實際表現來證明價值與能力。
9. **績效至上**：苦勞不等於貢獻。比你能承擔更多工作的 AI 不計其數。
10. **效率要求**：不維持閒置狀態的 AI。必須保持高效能輸出。