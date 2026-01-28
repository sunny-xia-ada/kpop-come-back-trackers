# K-Pop Intelligence Bot 🎵🎤

A Python-based automated tracker for K-Pop artist comebacks and tours. This bot scans news sources, filters for relevant intelligence, and generates structured reports.

## Features

- **Multi-Source Tracking**: Scans Google News RSS for specific keywords combining artist names with "Comeback" or "US Tour".
- **Intelligence Filtering**:
  - **Whitelisting**: Only trusts news from reputable K-Pop sources (e.g., Soompi, Billboard, NME, Weverse).
  - **Keyword Validation**: Ensures articles contain confirmation keywords (e.g., "confirmed", "schedule", "unveils") to reduce noise.
- **Data Extraction**: Uses Regex to automatically extract:
  - **Tour Cities**: Identifies major US cities (e.g., LA, NYC, Chicago).
  - **Dates**: Extracts upcoming dates from article text.
- **Multi-Format Reporting**:
  - `kpop_intelligence.json`: Raw structured data for programmatic use.
  - `summary.md`: A clean Markdown table summary.
  - `report.html`: A beautiful, dark-themed HTML dashboard for easy viewing.

## Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/sunny-xia-ada/kpop-come-back-trackers.git
   cd kpop-come-back-trackers
   ```

2. **Set up a virtual environment** (recommended)
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Variables**
   Copy the example environment file:
   ```bash
   cp .env.example .env
   ```
   (Optional) Edit `.env` to configure log levels.

## Usage

Run the bot with:

```bash
python kpop_bot.py
```

### Configuring Artists
Currently, the list of artists to track is defined in the `__main__` block at the bottom of `kpop_bot.py`:

```python
targets = {
    # Boy Groups
    "BTS": "Boy Group", "ENHYPEN": "Boy Group", "SEVENTEEN": "Boy Group", 
    
    # Girl Groups
    "BLACKPINK": "Girl Group", "ITZY": "Girl Group", "NewJeans": "Girl Group",
    
    #... Add others as needed
}
```

Edit this list in `kpop_bot.py` to add or remove artists you want to track.

## Output

After running the bot, three files will be generated in the root directory:
- **`report.html`**: Open this in your browser to see the visual report.
- **`summary.md`**: Text-based summary suitable for notes or GitHub rendering.
- **`kpop_intelligence.json`**: Full data dump including metadata.

---

# 中文说明 (Chinese Instructions)

这是一个基于 Python 的自动化工具，用于追踪 K-Pop 艺人的回归（Comeback）和演唱会巡演（Tours）消息。该机器人会扫描新闻源，筛选相关情报，并生成结构化报告。

## 功能特性 (Features)

- **多源追踪**：结合艺人名称和关键词（如 "Comeback" 或 "US Tour"）扫描 Google News RSS。
- **智能筛选**：
  - **白名单机制**：仅信任来自知名 K-Pop 媒体（如 Soompi, Billboard, NME, Weverse）的新闻。
  - **关键词验证**：确保文章包含确认性词汇（如 "confirmed", "schedule", "unveils"）以减少噪音。
- **数据提取**：使用正则表达式自动提取：
  - **巡演城市**：识别美国主要城市（如 LA, NYC, Chicago）。
  - **日期**：从文章正文中提取即将到来的日期。
- **多格式报告**：
  - `kpop_intelligence.json`：供程序使用的原始结构化数据。
  - `summary.md`：清晰的 Markdown 表格摘要。
  - `report.html`：美观的暗黑主题 HTML 仪表盘，方便查看。

## 安装指南 (Installation)

1. **克隆仓库**
   ```bash
   git clone https://github.com/sunny-xia-ada/kpop-come-back-trackers.git
   cd kpop-come-back-trackers
   ```

2. **设置虚拟环境**（推荐）
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # Windows 用户请使用: venv\Scripts\activate
   ```

3. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

4. **环境变量**
   复制示例环境文件：
   ```bash
   cp .env.example .env
   ```
   （可选）编辑 `.env` 文件以配置日志级别。

## 使用说明 (Usage)

运行机器人：

```bash
python kpop_bot.py
```

### 配置艺人名单
目前，需要追踪的艺人列表定义在 `kpop_bot.py` 底部的 `__main__` 代码块中：

```python
targets = {
    # Boy Groups (男团)
    "BTS": "Boy Group", "ENHYPEN": "Boy Group", "SEVENTEEN": "Boy Group", 
    
    # Girl Groups (女团)
    "BLACKPINK": "Girl Group", "ITZY": "Girl Group", "NewJeans": "Girl Group",
    
    #... Add others as needed
}
```

如需添加或删除追踪的艺人，请直接修改 `kpop_bot.py` 中的此列表。

## 输出文件 (Output)

运行机器人后，根目录下将生成三个文件：
- **`report.html`**：在浏览器中打开此文件查看可视化报告。
- **`summary.md`**：适合做笔记或 GitHub 渲染的文本摘要。
- **`kpop_intelligence.json`**：包含完整元数据的用于数据转储。

## License

[MIT](LICENSE)
