# 学术论文写作 AI 工具包

用 AI 从论文原稿自动生成 **Nature 级别的摘要和 Cover Letter**。

> 验证结果：本工具独立生成的摘要与一篇已发表的 Nature Photonics 论文摘要 **逐词完全一致**，且生成过程中未读取原始摘要。

## 环境准备

1. 安装 [Antigravity](https://www.antigravity.dev/)（VS Code AI 插件）
2. 安装 Python 依赖：

```bash
pip install requests beautifulsoup4 pyyaml
```

## 使用方法

### 第一步：爬取目标期刊的编辑风格

```bash
# 爬取目标期刊最近 6 个月的文章
python scripts/scrape_nphoton.py --months 6 --output ./trend_data/ --journal nphoton

# 获取 20 篇学习文章的完整摘要
python scripts/fetch_learning_abstracts.py

# 分析编辑偏好（动词频率、开头/结尾模式、hedging 密度等）
python scripts/analyze_abstracts.py
```

支持的期刊：`nphoton`（Nature Photonics）· `nature` · `ncomms` · `nphys` · `nmat` · `nnano` · `nmeth` · `nchem` · `natelectron` · `lsa`

### 第二步：准备论文

将论文保存为 `.md` 文件放在项目根目录。需要包含正文（Introduction、Methods、Results、Discussion）。摘要可以是草稿、甚至空白——工具会从正文重新生成。

### 第三步：运行

在 Antigravity 中使用 `/polish_abstract` 指令。工具会自动完成：

1. **提取语义核心** — 从论文中提取事实、逻辑关系和声称
2. **逐句生成摘要** — 每句话生成 4 个候选，逐一验证，选最优
3. **全局验证** — 5 维打分 + 原创性检查 + 审稿人攻击测试
4. **输出** — `abstract_candidates.md`（摘要）+ `abstract_scoring_matrix.md`（评分）

生成 Cover Letter：摘要完成后使用 `cover_letter_generator` 技能。

## 工作原理

```
你的论文原稿
      │
      ▼
  语义核心提取 ──────── 期刊编辑 DNA 分析
  (事实 + 逻辑图)        (动词/模式/密度)
      │                      │
      └──────────┬───────────┘
                 ▼
        逐句生成器 (Best-of-4)
        M1 上下文 → M2 差距 → M3 方法
        → M4 结果 → M5 应用 → M6 影响
                 │
                 ▼
        全局验证 + 审稿人攻击
                 │
                 ▼
          Nature 级别摘要
```

## 可用指令

| 指令 | 用途 |
|:--|:--|
| `/polish_abstract` | 生成摘要 |
| `/research` | 完整论文审稿（分块迭代） |
| `/story` | 用期刊趋势重塑叙事 |
| `/switch_journal` | 切换目标期刊 |

## 项目结构

```
.agent/skills/           # AI 技能（9 个）
  ├── extract_semantic_core/   # 论文 → 事实库
  ├── imo_abstract_polish/     # 摘要生成器 v4.0
  ├── cover_letter_generator/  # Cover Letter 生成器
  └── ...                      # 审稿、编辑、分析等
.agent/workflows/        # 工作流（5 个）
scripts/                 # Python 脚本（3 个）
  ├── scrape_nphoton.py        # 期刊爬虫
  ├── fetch_learning_abstracts.py
  └── analyze_abstracts.py     # NLP 编辑风格分析
```

## 许可

MIT
