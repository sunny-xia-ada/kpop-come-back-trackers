# KPOP追星机器人 from 一丹 🎵✨

> A beautiful, intelligent K-Pop tracking dashboard with kawaii aesthetics! Track your favorite artists' comebacks, tours, and get style inspiration from their latest looks.

![Baby Pink Theme](https://img.shields.io/badge/Theme-Baby%20Pink%20%26%20Blue-FFB6C1?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.9+-blue?style=for-the-badge&logo=python)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

## ✨ Features

### 🎤 Live Tour Tracking (巡演)
- **Smart Proximity Sorting**: Tours sorted by distance from Seattle, WA
- **Best Value Detection**: Automatic "⭐⭐⭐⭐⭐ Best Value" badge for closest shows
- **Multi-Platform Price Comparison**: Compare prices across StubHub, Vivid Seats, Ticketmaster, and SeatGeek
- **Bulletproof Deep Links**: Direct links to performer pages with city-specific search
- **Top 4 Cities**: Shows only the best 4 unique cities per artist

### 🎵 New Comeback Stage (新歌和舞台)
- **6-Month Filter**: Only shows releases from the last 6 months
- **YouTube Integration**: "▶ Watch Official MV" button for each song
- **News Aggregation**: Pulls from trusted K-Pop sources (Soompi, Billboard, NME, Weverse)
- **Smart Filtering**: Keyword validation ensures only confirmed news

### 🛍️ Idol Closet (偶像衣橱)
**NEW!** Get the look of your favorite idols!
- **Style Recommendations**: Curated outfit suggestions inspired by latest MVs and stages
- **Multi-Store Shopping**: One-click links to W Concept, Musinsa, and Lewkin
- **Artist-Specific Looks**: 
  - BTS: Vintage Denim, Oversized Hoodies, Bucket Hats
  - NMIXX: Y2K Pleated Skirts, Crop Tees, Platform Boots
  - And more for each artist!

### 🎨 Beautiful UI Design
- **Baby Pink & Blue Theme**: Soft, kawaii-inspired color palette
- **Cute Decorations**: Floating stars ⭐ and cats 🐱 in the background
- **Bilingual Interface**: English + Chinese (中文) labels
- **Responsive Design**: Works perfectly on all screen sizes
- **Glass-morphism Effects**: Modern, premium aesthetic

### 🤖 Intelligent Data Processing
- **Multi-Source Scraping**: Google News RSS aggregation
- **City & Date Extraction**: Automatic detection of US tour stops
- **Image Enrichment**: Fetches artist profile images
- **Real-Time Updates**: Fresh data on every run

## 🚀 Quick Start

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/sunny-xia-ada/kpop-come-back-trackers.git
   cd kpop-come-back-trackers
   ```

2. **Set up virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment** (optional)
   ```bash
   cp .env.example .env
   # Edit .env to set LOG_LEVEL if needed
   ```

### Usage

Run the bot:
```bash
python kpop_bot.py
```

Then open `report.html` in your browser to see the beautiful dashboard! 🎉

## 🎯 Tracked Artists

### Boy Groups (男团)
- BTS
- ENHYPEN
- SEVENTEEN
- Stray Kids
- TOMORROW X TOGETHER (TXT)
- ATEEZ

### Girl Groups (女团)
- BLACKPINK
- ITZY
- NewJeans
- aespa
- IVE
- NMIXX
- LE SSERAFIM
- (G)I-DLE

### Soloists (独唱)
- IU
- Taeyeon
- Jungkook
- V (BTS)
- Lisa (BLACKPINK)

**Want to add more artists?** Edit the `targets` dictionary in `kpop_bot.py`!

## 📁 Output Files

After running, you'll get:

| File | Description |
|------|-------------|
| `report.html` | 🌟 **Main dashboard** - Open this in your browser! |
| `kpop_intelligence.json` | Raw data for programmatic use |
| `summary.md` | Text-based summary |

## 🎨 UI Features

### Three Tabs
1. **Live Tour (巡演)** - Concert dates and ticket prices
2. **New Comeback Stage (新歌和舞台)** - Latest music releases
3. **Idol Closet (偶像衣橱)** - Style inspiration and shopping

### Smart Features
- **Independent Dropdowns**: Select from Girl Groups, Boy Groups, or Soloists
- **Default View**: Automatically shows Live Tour tab
- **Proximity Ranking**: Seattle-based distance sorting
- **Price Intelligence**: Always shows the cheapest option first

## 🛠️ Technical Details

### Built With
- **Python 3.9+**
- **BeautifulSoup4** - HTML parsing
- **Requests** - HTTP requests
- **Python-dotenv** - Environment management

### Data Sources
- Google News RSS feeds
- Trusted K-Pop media outlets
- DiceBear API for placeholder images

### Architecture
- **Data Layer**: News scraping and filtering
- **Processing Layer**: City/date extraction, price comparison
- **Presentation Layer**: Dynamic HTML generation with embedded JavaScript

## 🎯 Customization

### Adding New Artists
Edit `kpop_bot.py`:
```python
targets = {
    "YOUR_ARTIST": "Boy Group",  # or "Girl Group" or "Soloist"
    # ... add more
}
```

### Changing Home Location
Update the proximity sorting in `getProfessionalSort()` function to use your city instead of Seattle.

### Modifying Color Theme
Edit the CSS `:root` variables in `kpop_bot.py`:
```css
:root {
    --bg: #FFE4E8;  /* Baby pink background */
    --baby-blue: #89CFF0;
    --pink: #FFB6C1;
    /* ... customize colors */
}
```

## 🐛 Troubleshooting

**Issue**: No data showing up
- **Solution**: Check your internet connection. The bot needs to fetch from Google News.

**Issue**: Images not loading
- **Solution**: Some artists may not have cached images. The bot will use fallback avatars.

**Issue**: Prices seem outdated
- **Solution**: Prices are simulated for demo purposes. For real-time prices, integrate with ticketing APIs.

## 📝 License

MIT License - feel free to use and modify!

## 🙏 Acknowledgments

- K-Pop news sources: Soompi, Billboard, NME, Weverse
- Ticketing platforms: StubHub, Vivid Seats, Ticketmaster, SeatGeek
- Fashion retailers: W Concept, Musinsa, Lewkin

## 💖 Made with Love

Created by 一丹 (Yidan) for K-Pop fans worldwide! 

---

# 中文说明 (Chinese Instructions)

## 功能特性

### 🎤 巡演追踪
- 按距离西雅图的远近排序
- 自动标记"最佳选择"
- 多平台票价对比
- 智能购票链接

### 🎵 新歌和舞台
- 仅显示最近6个月的发布
- YouTube MV 直达链接
- 可信新闻源聚合

### 🛍️ 偶像衣橱
**全新功能！** 获取爱豆同款穿搭灵感
- 根据最新 MV 和舞台推荐服装
- 一键购物链接（W Concept、Musinsa、Lewkin）
- 每位艺人专属风格推荐

### 🎨 精美界面
- 粉蓝配色主题
- 可爱装饰（星星和小猫）
- 中英双语标签
- 响应式设计

## 快速开始

1. 克隆仓库并安装依赖（见上方英文说明）
2. 运行 `python kpop_bot.py`
3. 在浏览器中打开 `report.html`

## 自定义

### 添加艺人
编辑 `kpop_bot.py` 中的 `targets` 字典

### 修改主题颜色
编辑 CSS 变量中的颜色值

## 输出文件
- `report.html` - 主仪表盘（在浏览器中打开）
- `kpop_intelligence.json` - 原始数据
- `summary.md` - 文本摘要

---

**用爱制作** 💖 by 一丹
