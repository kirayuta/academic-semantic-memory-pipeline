---
name: academic_analyst
description: Scientific analysis frameworks for experimental physics — replaces commercial frameworks with research methodology
---

# Academic Analyst (学术分析)

> 判断复杂度 → 选科学方法 → 定量分析 → 输出结论

---

## 框架选择

| 问题类型 | 首选框架 | 示例 |
|----------|----------|------|
| 根因诊断 | **First Principles** | "为什么 NA 1.1 优于 1.4？" |
| 假设验证 | **Hypothesis-Driven** | "SPP 共振是主因吗？" |
| 竞争机制 | **Trade-off Analysis** | "穿透深度 vs 场强度" |
| 误差溯源 | **Error Propagation** | "ε 值误差如何影响 NA_spp？" |
| 数量级估算 | **Order-of-Magnitude** | "d_p 在 50-100nm 量级？" |
| 量纲验证 | **Dimensional Analysis** | "公式左右单位是否一致？" |
| 文献调研 | **Systematic Review** | "TERS 中 AO 的已有报道" |
| 实验设计 | **Controls & Variables** | "对照组/变量/可重复性" |

---

## 关键方法论

### Trade-off Analysis (权衡分析) 🆕
**用途**：当多个物理机制相互竞争时
**步骤**：
1. 列出所有相关物理量
2. 确定每个量随控制参数的变化趋势
3. 计算或估算乘积/竞争关系
4. 画出 Figure of Merit vs 控制参数曲线
5. 找到最优点并解释物理原因

### Error Propagation (误差传播) 🆕
**用途**：评估输入参数不确定性对结论的影响
**步骤**：
1. 识别关键输入参数及其不确定性
2. 计算 $\partial f / \partial x_i$ 灵敏度
3. 评估结论的鲁棒性

### Systematic Literature Review 🆕
**用途**：学术文献调研
**步骤**：
1. 定义搜索关键词矩阵
2. 选择数据库 (Web of Science, PubMed, Google Scholar)
3. 筛选标准 (年份、期刊、引用数)
4. 提取关键数据并制表
5. 识别 Knowledge Gap

---

## 数据来源可信度（学术版）

| 层级 | 来源 | 可信度 |
|------|------|--------|
| 1 | 同行评审论文 (Nature/Science/PRL) | ⭐⭐⭐ |
| 2 | 专业教科书 (Novotny, Born & Wolf) | ⭐⭐⭐ |
| 3 | 会议论文 (CLEO, SPIE) | ⭐⭐ |
| 4 | 预印本 (arXiv) | ⭐⭐ (需验证) |
| 5 | 课堂讲义 / 在线数据库 | ⭐ |
| 6 | AI 生成内容 | ⚠️ (必须交叉验证) |
