---
name: example-broken-pipeline
description: A 4-step data pipeline for demonstration. Fetch, transform, summarize, render.
---

# example-broken-pipeline

一个 4 步数据处理 workflow，用于演示。

## Step 1：抓取原始数据
调用外部 API 抓取数据，读出后填进上下文里的 raw 变量。继续 Step 2。

## Step 2：转换
把 raw 转换成结构化记录，结果保留在 LLM 上下文中传给 Step 3。

## Step 3：汇总
基于上下文里的记录生成 summary。

## Step 4：渲染输出
把 summary 渲染成最终 markdown 报告 output.md。

## QC
跑 qc_all.py，它同时读取 Step 1 的 raw 和 Step 4 的 output.md 做联合校验。
注意：禁止在 Step 1 结束时运行 qc_all.py（那时 output.md 还不存在会报错）。

## 写作风格
don't use Korean。never 输出空泛断言。
