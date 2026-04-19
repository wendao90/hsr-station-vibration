# Huzhou Nanxun Station Train-Induced Vibration — Dataset & Toolkit

[English](#english) | [中文](#中文)

---

## English

Field measurements and analysis toolkit for the paper

> **Smartphone-based Multi-Source Synchronous Measurement and Analysis of Train-Induced Vibration at a Bridge-Building Integrated HSR Station**
> LUO Mingzhang, DAN Danhui, WANG Wenzhao. *Railway Technical Standard*, 2026.

The project bundles everything needed to reproduce the paper's figures and tables from raw smartphone-captured vibration and audio — a low-cost workflow intended to be re-applied at other stations with minimal barrier.

### What is here

| Folder | Content |
|---|---|
| `vib_data/` | Raw tri-axial acceleration (smartphone MEMS, 99.43 Hz) in xls format |
| `sound/` | Raw continuous audio (48 kHz m4a); **not redistributed — local use only** |
| `vib_viz/` | Browser-based interactive tool (`align.html`) for aligning vibration, audio and field notes; also preparation scripts |
| `analysis/` | Event extraction, ISO 2631-1 weighting, 1/3-octave band analysis, figure generation |
| `scripts/` | `prepare_release.py` — builds a public `data_release/` bundle with privacy-scrubbed audio clips |

### Quick reproduction

```bash
pip install -r requirements.txt

# 1. Open the alignment tool
python -m http.server 9200
# browse http://127.0.0.1:9200/vib_viz/align.html
# load alignment JSON via the "导入 JSON" button

# 2. Extract event/baseline segments and compute features
python analysis/extract_clean_baselines.py
python analysis/iso2631_and_octave.py

# 3. Regenerate paper figures
python analysis/paper_figures.py
```

### Dataset overview

Measurements were collected on the evening of 6 April 2026 at Huzhou Nanxun Station of the Shanghai-Suzhou-Huzhou HSR, using a Redmi Note 14 Pro smartphone running [phyphox](https://phyphox.org/). Three passenger-activity positions were instrumented:

- **M1** service desk (waiting hall)
- **M2** hall floor, directly behind M1
- **M3** platform, near track

The annotated dataset contains **9 train-pass events** and **18 clean-background segments** (total ≈ 420 s). Alignment between vibration and audio uses manual knock events as time anchors; the resulting consistency error is within ±30 ms.

### License

- **Code** (this repository): MIT — see `LICENSE`
- **Data** (`data_release/`, Zenodo archive): CC BY 4.0 — see `DATA-LICENSE`

### Citation

If this dataset or code is useful to your work, please cite both the paper and the dataset/software record. See `CITATION.cff` at the repository root.

### Acknowledgements

Supported by National Natural Science Foundation of China (52578234), Shanghai Natural Science Foundation (24ZR1468300), and CRSCD Engineering Design & Consultation Group project (KY2024A031).

---

## 中文

本仓库是论文

> **桥建合一高铁站车致振动智能手机多源同步测量与分析**
> 罗鸣璋，淡丹辉，王文钊. 铁道技术标准（中英文），2026.

的配套实测数据与分析工具链。全部基于智能手机 + phyphox 的低成本方案实现，便于其他站房直接复现或扩展。

### 目录结构

| 目录 | 内容 |
|---|---|
| `vib_data/` | 三轴加速度原始数据（智能手机 MEMS，99.43 Hz，xls） |
| `sound/` | 连续音频（48 kHz m4a）；**本地使用，不公开分发** |
| `vib_viz/` | 基于浏览器的振动/音频/笔记交互式标注工具（`align.html`）及预处理脚本 |
| `analysis/` | 事件提取、ISO 2631-1 频率加权、1/3 倍频程谱、出图 |
| `scripts/` | `prepare_release.py` — 生成面向公众的 `data_release/`（音频已裁剪脱敏） |

### 快速复现

```bash
pip install -r requirements.txt

# 1. 启动标注工具
python -m http.server 9200
# 浏览器打开 http://127.0.0.1:9200/vib_viz/align.html
# 通过 "导入 JSON" 按钮加载对齐数据

# 2. 提取事件/本底段，计算加权 RMS
python analysis/extract_clean_baselines.py
python analysis/iso2631_and_octave.py

# 3. 重绘论文配图
python analysis/paper_figures.py
```

### 数据概览

2026 年 4 月 6 日晚于沪苏湖高铁湖州南浔站测得，设备为 Redmi Note 14 Pro 搭载 [phyphox](https://phyphox.org/)。在 3 个旅客活动典型位置布置测点：

- **M1** 候车大厅服务台
- **M2** M1 正后方楼板地面
- **M3** 站台近轨道位置

共标注获得 **9 次过车事件**、**18 段干净本底段**（累计约 420 s）。振动与音频通过现场人工敲击作为时间锚点对齐，实测一致性误差在 ±30 ms 以内。

### 许可协议

- **代码**（本仓库）：MIT License（`LICENSE`）
- **数据**（`data_release/` 及 Zenodo 归档）：CC BY 4.0（`DATA-LICENSE`）

### 引用方式

若本数据集或代码对您的研究有所帮助，请同时引用论文与数据集记录，详见根目录 `CITATION.cff`。

### 致谢

受国家自然科学基金项目（52578234）、上海市自然科学基金（24ZR1468300）及中铁工程设计咨询集团有限公司项目（KY2024A031）资助。
