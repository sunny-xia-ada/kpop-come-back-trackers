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
targets = ["BTS", "BLACKPINK", "ITZY", "ENHYPEN", "SEVENTEEN", "NewJeans"]
```

Edit this list in `kpop_bot.py` to add or remove artists you want to track.

## Output

After running the bot, three files will be generated in the root directory:

- **`report.html`**: Open this in your browser to see the visual report.
- **`summary.md`**: Text-based summary suitable for notes or GitHub rendering.
- **`kpop_intelligence.json`**: Full data dump including metadata.

## License

[MIT](LICENSE)
