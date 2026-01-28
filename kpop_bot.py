import os
import re
import json
import logging
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from dotenv import load_dotenv
from typing import List, Dict, Set
from urllib.parse import urlparse, unquote

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

class KpopIntelligenceBot:
    def __init__(self):
        self.whitelist: Set[str] = {
            "soompi.com", "allkpop.com", "billboard.com", "nme.com", 
            "koreaboo.com", "rollingstone.com", "weverse.io", "hypebeast.com",
            "variety.com", "koreaherald.com"
        }
        
        self.validation_keywords: Set[str] = {
            "confirmed", "announced", "schedule", "ticket sales", 
            "dates", "cities", "unveils", "drops", "release", "comeback"
        }
        
        # Regex for US Cities (Common tour stops)
        self.city_regex = re.compile(
            r"\b(Seattle|New York|NYC|Los Angeles|LA|Chicago|Houston|Atlanta|"
            r"Dallas|San Francisco|Oakland|Newark|Washington D\.C\.|Las Vegas|"
            r"Anaheim|Inglewood|Rosemont|Fort Worth|Belmont Park|Reading)\b", 
            re.IGNORECASE
        )
        
        # Regex for future dates (simplified for demonstration)
        self.date_regex = re.compile(
            r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}\b",
            re.IGNORECASE
        )

    def is_whitelisted(self, url: str) -> bool:
        """Check if the source domain is in the whitelist."""
        try:
            domain = urlparse(url).netloc.lower()
            return any(allowed in domain for allowed in self.whitelist)
        except Exception:
            return False

    def validate_content(self, text: str) -> bool:
        """Check if text contains at least one validation keyword."""
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in self.validation_keywords)

    def extract_metadata(self, text: str) -> Dict:
        """Extract structured data using regex."""
        cities = list(set(self.city_regex.findall(text)))
        dates = list(set(self.date_regex.findall(text)))
        return {
            "cities": cities,
            "dates": dates
        }

    def fetch_news(self, artist: str, query_type: str = "US Tour") -> List[Dict]:
        """Fetch news from Google News RSS."""
        query = f"{artist} {query_type}"
        encoded_query = requests.utils.quote(query)
        rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"
        
        logger.info(f"Fetching news for: {query}")
        
        try:
            response = requests.get(rss_url, timeout=10)
            response.raise_for_status()
        except requests.RequestException as e:
            logger.error(f"Failed to fetch RSS feed: {e}")
            return []

        soup = BeautifulSoup(response.content, "xml")
        items = soup.find_all("item")
        
        logger.info(f"Found {len(items)} raw items for {query}")
        
        extracted_data = []

        for item in items:
            title = item.title.text
            # Google News RSS source is often in <source> tag or appended to title
            source_tag = item.find("source")
            source_name = source_tag.text if source_tag else "Unknown"
            link = item.link.text
            pub_date = item.pubDate.text
            description = item.description.text if item.description else ""
            
            # Combined text for analysis
            full_text = f"{title} {description}"

            # 1. Source Whitelisting (Strict Mode: Skip if not authoritative)
            # Note: Google News RSS links are redirected. We check the source name if available or try to resolve.
            # Ideally we check the source name provided by RSS first to save time.
            # Using simple source name check for efficiency in this demo.
            # In a real expanded bot, we might HEAD request the link to check final domain.
            if not self.is_whitelisted_source_name(source_name) and not self.is_whitelisted(link):
                 # Fallback: Many RSS links are news.google.com, so we trust Source Name primarily
                 if not self.is_whitelisted_source_name(source_name):
                     continue

            # 2. Keyword Validation
            if not self.validate_content(full_text):
                continue

            # 3. Extraction
            metadata = self.extract_metadata(full_text)
            
            extracted_data.append({
                "artist": artist,
                "topic": query_type,
                "title": title,
                "source": source_name,
                "url": link,
                "published_at": pub_date,
                "extracted_cities": metadata["cities"],
                "extracted_dates": metadata["dates"]
            })
            
        return extracted_data
        
    def is_whitelisted_source_name(self, source_name: str) -> bool:
        """Helper to match Source Name (e.g. 'Soompi') against whitelist domains."""
        # Simple mapping or containment check
        name_clean = source_name.lower().replace(" ", "")
        for domain in self.whitelist:
            if name_clean in domain.replace(".", ""):
                return True
        return False

    def deduplicate(self, items: List[Dict]) -> List[Dict]:
        """Deduplicate news items based on Title Similarity."""
        unique_items = []
        seen_titles = set()
        
        for item in items:
            # Simple normalization: First 20 chars of title + source
            # In production, use Fuzzy Matching (e.g. Lev Distance)
            title_key = item['title'][:30].lower()
            if title_key not in seen_titles:
                seen_titles.add(title_key)
                unique_items.append(item)
                
        return unique_items

    def run(self, targets: Dict[str, str]):
        all_news = []
        artists = list(targets.keys())
        
        for artist in artists:
            # Check for both Tour and Comeback
            all_news.extend(self.fetch_news(artist, "US Tour"))
            all_news.extend(self.fetch_news(artist, "Comeback"))
            
        clean_news = self.deduplicate(all_news)
        
        # Output JSON
        with open("kpop_intelligence.json", "w") as f:
            json.dump(clean_news, f, indent=2)
            
        # Output Markdown Summary
        self.generate_markdown(clean_news)
        
        # Output HTML Web Report
        self.generate_html(clean_news, targets)
        
        logger.info(f"Scan complete. Found {len(clean_news)} relevant intelligence items.")
        print(json.dumps(clean_news, indent=2))

    def generate_markdown(self, items: List[Dict]):
        md_lines = ["# K-pop Intelligence Report", f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ""]
        
        if not items:
            md_lines.append("_No high-priority intelligence found in this scan._")
        else:
            md_lines.append("| Artist | Topic | Source | Title | Cities/Dates |")
            md_lines.append("|---|---|---|---|---|")
            
            for item in items:
                meta = []
                if item['extracted_cities']:
                    meta.append(f"🏙️ {', '.join(item['extracted_cities'])}")
                if item['extracted_dates']:
                    meta.append(f"📅 {', '.join(item['extracted_dates'])}")
                
                meta_str = "<br>".join(meta) if meta else "-"
                
                row = f"| **{item['artist']}** | {item['topic']} | *{item['source']}* | [{item['title']}]({item['url']}) | {meta_str} |"
                md_lines.append(row)
                
        with open("summary.md", "w") as f:
            f.write("\n".join(md_lines))

    def generate_html(self, items: List[Dict], categories: Dict[str, str]):
        html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>K-pop Intelligence Report</title>
    <style>
        :root {
            --bg-color: #f9fafb;
            --card-bg: #ffffff;
            --text-primary: #111827;
            --text-secondary: #4b5563;
            --accent: #d946ef;
            --accent-glow: rgba(217, 70, 239, 0.3);
            --border: #e5e7eb;
            --tour-color: #3b82f6;
            --comeback-color: #ec4899;
        }

        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-primary);
            margin: 0;
            padding: 40px 20px;
            line-height: 1.6;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
        }

        header {
            margin-bottom: 40px;
            border-bottom: 1px solid var(--border);
            padding-bottom: 20px;
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
        }

        h1 {
            font-size: 2.5rem;
            margin: 0;
            background: linear-gradient(135deg, #111 0%, var(--accent) 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            letter-spacing: -1px;
        }

        h2 {
            font-size: 1.8rem;
            margin: 40px 0 20px 0;
            padding-bottom: 10px;
            border-bottom: 2px solid var(--accent);
            display: inline-block;
        }

        .meta {
            color: var(--text-secondary);
            font-size: 0.9rem;
        }

        .artist-section {
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 24px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }

        .artist-header {
            font-size: 1.5rem;
            font-weight: 700;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 1px solid var(--border);
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .artist-badge {
            font-size: 0.8rem;
            padding: 4px 8px;
            border-radius: 999px;
            background: #f3f4f6;
            color: var(--text-secondary);
            font-weight: 600;
        }

        .split-layout {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
        }

        @media (max-width: 768px) {
            .split-layout { grid-template-columns: 1fr; }
        }

        .column h3 {
            font-size: 1.1rem;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: var(--text-secondary);
            margin: 0 0 16px 0;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .column-content {
            min-height: 100px;
        }

        .news-item {
            margin-bottom: 16px;
            padding-bottom: 16px;
            border-bottom: 1px dashed var(--border);
        }

        .news-item:last-child {
            border-bottom: none;
        }

        .news-title {
            font-weight: 600;
            margin-bottom: 4px;
            display: block;
            text-decoration: none;
            color: var(--text-primary);
        }

        .news-title:hover {
            color: var(--accent);
        }

        .news-source {
            font-size: 0.8rem;
            color: var(--text-secondary);
        }

        .cities-list {
            margin: 10px 0;
            font-size: 0.95rem;
        }

        .ticket-buttons {
            display: flex;
            gap: 10px;
            margin-top: 12px;
        }

        .btn {
            display: inline-flex;
            align-items: center;
            padding: 6px 12px;
            font-size: 0.85rem;
            font-weight: 500;
            text-decoration: none;
            border-radius: 6px;
            transition: background 0.2s;
        }

        .btn-tm {
            background-color: #026cdf;
            color: white;
        }
        .btn-tm:hover { background-color: #0257b4; }

        .btn-sh {
            background-color: #6432a1;
            color: white;
        }
        .btn-sh:hover { background-color: #4b267a; }

        .empty-col {
            color: #d1d5db;
            font-style: italic;
            font-size: 0.9rem;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div>
                <h1>K-pop Intelligence</h1>
                <div class="meta">Live Tracker Report</div>
            </div>
            <div class="meta">Generated: {generated_time}</div>
        </header>

        {content}

    </div>
</body>
</html>
"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
        
        # Group items by Artist
        artist_data = {}
        for item in items:
            name = item['artist']
            if name not in artist_data:
                artist_data[name] = {"tour": [], "comeback": []}
            
            if "Tour" in item['topic']:
                artist_data[name]["tour"].append(item)
            else:
                artist_data[name]["comeback"].append(item)
        
        # Build Content separated by Category
        categories_order = ["Girl Group", "Boy Group", "Co-ed Group", "Soloist"]
        grouped_html = []

        # Sort artists alphabetically within current active artists list
        active_artists = sorted(artist_data.keys())

        # Iterate by Category
        for cat in categories_order:
            cat_artists = [a for a in active_artists if categories.get(a, "Unknown") == cat]
            if not cat_artists:
                continue

            section_html = [f"<h2>{cat}s</h2>"]
            
            for artist in cat_artists:
                data = artist_data[artist]
                
                # --- TOUR COLUMN ---
                tour_html = []
                if not data["tour"]:
                    tour_html.append('<div class="empty-col">No active tour news found.</div>')
                else:
                    # Collect all unique cities
                    all_cities = set()
                    for t in data["tour"]:
                        all_cities.update(t['extracted_cities'])
                    
                    if all_cities:
                        tour_html.append(f'<div class="cities-list"><strong>Cities:</strong> {", ".join(sorted(all_cities))}</div>')
                    
                    # Ticket Buttons
                    tm_link = f"https://www.ticketmaster.com/search?q={requests.utils.quote(artist)}"
                    sh_link = f"https://www.stubhub.com/secure/search?q={requests.utils.quote(artist)}"
                    
                    tour_html.append(f'''
                        <div class="ticket-buttons">
                            <a href="{tm_link}" target="_blank" class="btn btn-tm">Ticketmaster</a>
                            <a href="{sh_link}" target="_blank" class="btn btn-sh">StubHub</a>
                        </div>
                    ''')

                    # List Articles
                    for t in data["tour"][:3]: # Limit to 3 recent articles
                         tour_html.append(f'''
                            <div class="news-item">
                                <a href="{t['url']}" target="_blank" class="news-title">{t['title']}</a>
                                <span class="news-source">{t['source']} • {t['published_at'][:16]}</span>
                            </div>
                        ''')

                # --- COMEBACK COLUMN ---
                comeback_html = []
                if not data["comeback"]:
                    comeback_html.append('<div class="empty-col">No recent comeback news.</div>')
                else:
                    for c in data["comeback"][:5]: # Limit to 5
                         comeback_html.append(f'''
                            <div class="news-item">
                                <a href="{c['url']}" target="_blank" class="news-title">{c['title']}</a>
                                <span class="news-source">{c['source']} • {c['published_at'][:16]}</span>
                            </div>
                        ''')

                artist_block = f"""
                <div class="artist-section">
                    <div class="artist-header">
                        {artist}
                        <span class="artist-badge">{categories.get(artist, "Artist")}</span>
                    </div>
                    <div class="split-layout">
                        <div class="column">
                            <h3>🌍 US Tour</h3>
                            <div class="column-content">{''.join(tour_html)}</div>
                        </div>
                        <div class="column">
                            <h3>🎵 New Comeback</h3>
                            <div class="column-content">{''.join(comeback_html)}</div>
                        </div>
                    </div>
                </div>
                """
                section_html.append(artist_block)
            
            grouped_html.append("".join(section_html))
            
        final_content = "".join(grouped_html) if grouped_html else '<div class="empty-state">No meaningful intelligence found for any targets.</div>'
        final_html = html_template.replace("{generated_time}", timestamp).replace("{content}", final_content)
        
        with open("report.html", "w") as f:
            f.write(final_html)

if __name__ == "__main__":
    bot = KpopIntelligenceBot()
    
    # Categorized Targets
    targets = {
        # Boy Groups
        "BTS": "Boy Group", "ENHYPEN": "Boy Group", "SEVENTEEN": "Boy Group",
        "NCT DREAM": "Boy Group", "TWS": "Boy Group", "NCT WISH": "Boy Group",
        "Cortis": "Boy Group", "Stray Kids": "Boy Group", "ATEEZ": "Boy Group",
        
        # Girl Groups
        "BLACKPINK": "Girl Group", "ITZY": "Girl Group", "NewJeans": "Girl Group",
        "aespa": "Girl Group", "KISS OF LIFE": "Girl Group", "XG": "Girl Group",
        "TWICE": "Girl Group", "LE SSERAFIM": "Girl Group", "SAY MY NAME": "Girl Group",
        "izna": "Girl Group", "MEOVV": "Girl Group", "IVE": "Girl Group",
        "BABYMONSTER": "Girl Group",
        
        # Soloists
        "BIBI": "Soloist", 
        
        # Co-ed
        "All Day Project": "Co-ed Group"
    }

    bot.run(targets)
