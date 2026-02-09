# Autonomous Agent - 完全自主的任務執行

## 概述

Agent Skills Library 現在提供**完全自主的 agent**，用戶只需要：
1. 提供問題/任務
2. 提供 LLM 實例
3. （可選）提供 approval callback

Agent 會**自動處理所有事情**：
- ✅ 選擇適當的 skills
- ✅ 載入 instructions 和 references
- ✅ 執行 scripts（需要用戶批准）
- ✅ 迭代直到任務完成

## 快速開始

### 最簡單的使用方式

```python
from pathlib import Path
from langchain_openai import ChatOpenAI
from agent_skills import SkillsRepository, ExecutionPolicy, AutonomousAgent

# 1. 建立 repository
repo = SkillsRepository(
    roots=[Path("./skills")],
    execution_policy=ExecutionPolicy(
        enabled=True,
        allow_skills={"data-processor"},
        allow_scripts_glob=["scripts/*.py"],
    )
)
repo.refresh()

# 2. 建立 LLM
llm = ChatOpenAI(model="gpt-4")

# 3. 建立 autonomous agent
agent = AutonomousAgent(
    repository=repo,
    llm=llm,
    # approval_callback=None,  # None = 自動批准所有執行
)

# 4. 執行任務（就這麼簡單！）
result = agent.run("Convert sample.csv to JSON format")
print(result)
```

## 使用 Approval Callback

### 互動式批准

```python
from agent_skills import ApprovalRequest, ApprovalResponse

def approval_callback(request: ApprovalRequest) -> ApprovalResponse:
    """用戶批准 callback"""
    print(f"\n任務: {request.task_description}")
    print(f"原因: {request.reasoning}")
    print(f"\n執行詳情:")
    print(f"  Skill: {request.skill_name}")
    print(f"  Script: {request.script_path}")
    print(f"  參數: {request.args}")
    print(f"  Timeout: {request.timeout_s}s")
    
    response = input("\n批准執行? (y/n): ")
    
    if response.lower() == 'y':
        return ApprovalResponse(approved=True)
    else:
        reason = input("拒絕原因: ")
        return ApprovalResponse(approved=False, reason=reason)

# 使用 callback
agent = AutonomousAgent(
    repository=repo,
    llm=llm,
    approval_callback=approval_callback,
)

result = agent.run("Process data.csv")
```

### 自動批准（顯示資訊）

```python
def auto_approval_callback(request: ApprovalRequest) -> ApprovalResponse:
    """自動批准但顯示資訊"""
    print(f"\n[自動批准] 執行: {request.script_path}")
    print(f"  原因: {request.reasoning}")
    return ApprovalResponse(approved=True)

agent = AutonomousAgent(
    repository=repo,
    llm=llm,
    approval_callback=auto_approval_callback,
)
```

### 條件式批准

```python
def conditional_approval_callback(request: ApprovalRequest) -> ApprovalResponse:
    """根據條件批准"""
    # 只批准特定 skills
    if request.skill_name not in ["data-processor", "api-client"]:
        return ApprovalResponse(
            approved=False,
            reason=f"Skill '{request.skill_name}' not in approved list"
        )
    
    # 只批准短時間執行
    if request.timeout_s > 60:
        return ApprovalResponse(
            approved=False,
            reason=f"Timeout {request.timeout_s}s exceeds limit"
        )
    
    # 批准
    return ApprovalResponse(approved=True)

agent = AutonomousAgent(
    repository=repo,
    llm=llm,
    approval_callback=conditional_approval_callback,
)
```

## ApprovalRequest 詳細資訊

當 agent 需要執行 script 時，會呼叫 approval callback 並提供 `ApprovalRequest`：

```python
@dataclass
class ApprovalRequest:
    # 執行參數
    skill_name: str          # Skill 名稱
    script_path: str         # Script 相對路徑
    args: list[str]          # 命令列參數
    stdin: Optional[str]     # 標準輸入
    timeout_s: int           # Timeout（秒）
    
    # 上下文資訊
    skill_description: str   # Skill 描述
    script_full_path: str    # Script 完整路徑
    working_directory: str   # 工作目錄
    
    # Agent 意圖
    task_description: str    # 用戶的原始任務
    reasoning: str           # Agent 為什麼要執行這個 script
```

## ApprovalResponse

用戶的回應：

```python
@dataclass
class ApprovalResponse:
    approved: bool           # 是否批准
    reason: Optional[str]    # 拒絕原因（可選）
```

## 完整範例

### 範例 1: CSV to JSON 轉換

```python
from pathlib import Path
from langchain_openai import ChatOpenAI
from agent_skills import (
    SkillsRepository,
    ExecutionPolicy,
    AutonomousAgent,
    ApprovalRequest,
    ApprovalResponse,
)

# 設定
repo = SkillsRepository(
    roots=[Path("./skills")],
    execution_policy=ExecutionPolicy(
        enabled=True,
        allow_skills={"data-processor"},
        allow_scripts_glob=["scripts/*.py"],
    )
)
repo.refresh()

llm = ChatOpenAI(model="gpt-4", temperature=0)

# Approval callback
def approval_callback(request: ApprovalRequest) -> ApprovalResponse:
    print(f"\n批准請求:")
    print(f"  任務: {request.task_description}")
    print(f"  Skill: {request.skill_name}")
    print(f"  Script: {request.script_path}")
    print(f"  原因: {request.reasoning}")
    
    response = input("批准? (y/n): ")
    return ApprovalResponse(approved=response.lower() == 'y')

# 建立 agent
agent = AutonomousAgent(
    repository=repo,
    llm=llm,
    approval_callback=approval_callback,
    max_iterations=15,
    verbose=True,
)

# 執行任務
result = agent.run(
    "Convert the CSV file at 'data.csv' to JSON format "
    "and save it to 'data.json'"
)

print(f"\n結果: {result}")
```

### 範例 2: 多個任務

```python
# 建立 agent（自動批准）
agent = AutonomousAgent(
    repository=repo,
    llm=llm,
    approval_callback=None,  # 自動批准
    verbose=True,
)

# 任務 1
result1 = agent.run("Say hello using a skill")
print(f"Task 1: {result1}")

# 任務 2
result2 = agent.run("Process data.csv and validate it")
print(f"Task 2: {result2}")

# 任務 3
result3 = agent.run("Make an API call to get user data")
print(f"Task 3: {result3}")
```

## Agent 工作流程

```
用戶提供問題
    ↓
Agent 分析任務
    ↓
Agent 使用 skills_list 尋找相關 skills
    ↓
Agent 使用 skills_activate 載入 instructions
    ↓
Agent 使用 skills_read 讀取 references（如需要）
    ↓
Agent 使用 skills_run 執行 scripts
    ↓ (需要批准)
呼叫 approval_callback
    ↓
用戶批准/拒絕
    ↓
繼續執行或嘗試其他方法
    ↓
迭代直到完成
    ↓
返回最終答案
```

## 配置選項

### AutonomousAgent 參數

```python
agent = AutonomousAgent(
    repository=repo,              # SkillsRepository 實例
    llm=llm,                      # LangChain LLM 實例
    approval_callback=callback,   # 批准 callback（None = 自動批准）
    max_iterations=15,            # 最大迭代次數
    verbose=True,                 # 是否顯示詳細資訊
)
```

### ExecutionPolicy 設定

```python
policy = ExecutionPolicy(
    enabled=True,                      # 啟用執行
    allow_skills={"skill1", "skill2"}, # 允許的 skills
    allow_scripts_glob=["scripts/*.py"], # 允許的 script patterns
    timeout_s_default=60,              # 預設 timeout
    env_allowlist=["PATH", "HOME"],    # 環境變數 allowlist
)
```

## 優勢

### 用戶視角

**之前（手動）：**
```python
# 用戶需要做很多事情
tools = build_langchain_tools(repo)
llm_with_tools = llm.bind_tools(tools)

messages = [SystemMessage(...), HumanMessage(...)]

for iteration in range(15):
    ai_msg = llm_with_tools.invoke(messages)
    messages.append(ai_msg)
    
    if not ai_msg.tool_calls:
        break
    
    for tool_call in ai_msg.tool_calls:
        tool = find_tool(tool_call["name"])
        result = tool.invoke(tool_call["args"])
        messages.append(ToolMessage(...))

final_answer = messages[-1].content
```

**現在（自動）：**
```python
# 用戶只需要做這些
agent = AutonomousAgent(repo, llm, approval_callback)
result = agent.run("Convert CSV to JSON")
```

### Library 視角

Library 現在處理：
- ✅ Tool 建立和管理
- ✅ LLM 與 tools 的綁定
- ✅ Agent loop 實作
- ✅ Tool 執行
- ✅ 訊息管理
- ✅ 錯誤處理
- ✅ 迭代控制
- ✅ 批准流程

## 安全特性

### 多層安全

1. **ExecutionPolicy** - 定義允許的 skills 和 scripts
2. **Approval Callback** - 用戶批准每次執行
3. **ScriptRunner** - Policy enforcement 和安全檢查
4. **Sandbox** - 隔離執行環境

### 批准流程

```
Agent 決定執行 script
    ↓
建立 ApprovalRequest（包含所有資訊）
    ↓
呼叫 approval_callback
    ↓
用戶審查資訊
    ↓
用戶批准/拒絕
    ↓
如果批准：執行 script
如果拒絕：返回錯誤給 agent
    ↓
Agent 根據結果決定下一步
```

## 錯誤處理

### Agent 自動處理錯誤

```python
# Agent 會自動處理錯誤並嘗試其他方法
result = agent.run("Process invalid_file.csv")

# Agent 可能會：
# 1. 檢查檔案是否存在
# 2. 嘗試不同的 skill
# 3. 讀取更多文件
# 4. 提供有用的錯誤訊息
```

### 用戶可以拒絕執行

```python
def careful_approval(request: ApprovalRequest) -> ApprovalResponse:
    # 檢查參數
    if "--delete" in request.args:
        return ApprovalResponse(
            approved=False,
            reason="Deletion operations not allowed"
        )
    
    return ApprovalResponse(approved=True)
```

## 最佳實踐

### 1. 使用明確的任務描述

```python
# ✅ 好
result = agent.run(
    "Convert the CSV file at '/path/to/data.csv' to JSON format "
    "and save it to '/path/to/output.json'"
)

# ❌ 不好
result = agent.run("process file")
```

### 2. 設定適當的 max_iterations

```python
# 簡單任務
agent = AutonomousAgent(repo, llm, max_iterations=5)

# 複雜任務
agent = AutonomousAgent(repo, llm, max_iterations=20)
```

### 3. 使用 verbose 模式進行除錯

```python
# 開發時
agent = AutonomousAgent(repo, llm, verbose=True)

# 生產環境
agent = AutonomousAgent(repo, llm, verbose=False)
```

### 4. 實作智能的 approval callback

```python
def smart_approval(request: ApprovalRequest) -> ApprovalResponse:
    # 記錄所有請求
    log_approval_request(request)
    
    # 檢查安全性
    if is_safe(request):
        return ApprovalResponse(approved=True)
    
    # 需要人工審查
    return ask_human(request)
```

## 總結

Autonomous Agent 讓使用 agent-skills library 變得**極其簡單**：

**用戶只需要：**
1. 建立 SkillsRepository
2. 建立 LLM
3. 建立 AutonomousAgent
4. 呼叫 agent.run()

**Library 處理所有事情：**
- Skill 選擇
- Instructions 載入
- References 讀取
- Scripts 執行（需要批准）
- 迭代控制
- 錯誤處理

這是使用 agent-skills library 的**最簡單方式**！
