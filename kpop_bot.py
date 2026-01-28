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

    def run(self, artists: List[str]):
        all_news = []
        
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
        self.generate_html(clean_news)
        
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

    def generate_html(self, items: List[Dict]):
        html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>K-pop Intelligence Report</title>
    <style>
        :root {
            --bg-color: #0f0f13;
            --card-bg: #1a1a23;
            --text-primary: #ffffff;
            --text-secondary: #a0a0b0;
            --accent: #d946ef; /* Pink/Purple */
            --accent-glow: rgba(217, 70, 239, 0.3);
            --border: #2e2e3a;
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
            max-width: 1200px;
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
            background: linear-gradient(135deg, #fff 0%, var(--accent) 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            letter-spacing: -1px;
        }

        .meta {
            color: var(--text-secondary);
            font-size: 0.9rem;
        }

        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 24px;
        }

        .card {
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 24px;
            transition: transform 0.2s, box-shadow 0.2s;
            position: relative;
            overflow: hidden;
        }

        .card:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 30px rgba(0,0,0,0.3);
            border-color: var(--accent);
        }

        .tag {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
            margin-bottom: 12px;
        }

        .tag.tour { background: rgba(59, 130, 246, 0.2); color: #60a5fa; }
        .tag.comeback { background: rgba(236, 72, 153, 0.2); color: #f472b6; }

        .artist {
            font-size: 0.85rem;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 8px;
            display: block;
        }

        .title {
            font-size: 1.1rem;
            font-weight: 700;
            margin: 0 0 16px 0;
            line-height: 1.4;
        }

        .title a {
            color: var(--text-primary);
            text-decoration: none;
            transition: color 0.2s;
        }

        .title a:hover {
            color: var(--accent);
        }

        .source {
            font-size: 0.85rem;
            color: var(--text-secondary);
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .source::before {
            content: '';
            display: inline-block;
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background-color: var(--accent);
        }

        .metadata {
            margin-top: 16px;
            padding-top: 16px;
            border-top: 1px solid var(--border);
            font-size: 0.9rem;
        }

        .metadata-item {
            display: flex;
            gap: 8px;
            margin-top: 4px;
            color: var(--text-secondary);
        }
        
        .empty-state {
            text-align: center;
            padding: 60px;
            color: var(--text-secondary);
            font-style: italic;
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
        
        if not items:
            content = '<div class="empty-state">No active intelligence found in this scan.</div>'
        else:
            cards = []
            for item in items:
                tag_class = "tour" if "Tour" in item['topic'] else "comeback"
                
                meta_html = ""
                if item['extracted_cities']:
                    meta_html += f'<div class="metadata-item"><span>🏙️</span> <span>{", ".join(item["extracted_cities"])}</span></div>'
                if item['extracted_dates']:
                    meta_html += f'<div class="metadata-item"><span>📅</span> <span>{", ".join(item["extracted_dates"])}</span></div>'
                
                if meta_html:
                    meta_html = f'<div class="metadata">{meta_html}</div>'

                card = f"""
                <div class="card">
                    <span class="artist">{item['artist']}</span>
                    <span class="tag {tag_class}">{item['topic']}</span>
                    <h3 class="title"><a href="{item['url']}" target="_blank">{item['title']}</a></h3>
                    <div class="source">{item['source']}</div>
                    {meta_html}
                </div>
                """
                cards.append(card)
            
            content = f'<div class="grid">{"".join(cards)}</div>'
            
        final_html = html_template.replace("{generated_time}", timestamp).replace("{content}", content)
        
        with open("report.html", "w") as f:
            f.write(final_html)

if __name__ == "__main__":
    bot = KpopIntelligenceBot()
    # List of target artists
    targets = ["BTS", "BLACKPINK", "ITZY", "ENHYPEN", "SEVENTEEN", "NewJeans"]
    bot.run(targets)
