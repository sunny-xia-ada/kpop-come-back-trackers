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
            
            # Extract Image from description or media extensions
            image_url = ""
            
            # Try media:content or enclosure first (higher quality)
            media_content = item.find("media:content")
            if media_content and media_content.get("url"):
                image_url = media_content["url"]
            
            # Fallback to description parsing
            if not image_url and description:
                desc_soup = BeautifulSoup(description, "html.parser")
                img_tag = desc_soup.find("img")
                if img_tag and img_tag.get("src"):
                    image_url = img_tag["src"]

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
                "image_url": image_url,
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

    def fetch_og_image(self, url: str) -> str:
        """Fetch Open Graph image from a URL."""
        try:
            # Short timeout, user agent to avoid bot blocks
            headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36'}
            resp = requests.get(url, headers=headers, timeout=3)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.content, "html.parser")
                og_image = soup.find("meta", property="og:image")
                if og_image and og_image.get("content"):
                    return og_image["content"]
        except Exception as e:
            logger.debug(f"Failed to fetch OG image for {url}: {e}")
        return ""

    def enrich_with_images(self, items: List[Dict], limit_per_artist: int = 4):
        """Post-process items to add images by scraping source URL."""
        logger.info("Enriching news metadata (Scanning for images)...")
        
        # Track counts to limit scraping
        artist_counts = {} 
        
        updated_items = []
        for item in items:
            key = f"{item['artist']}_{item['topic']}"
            count = artist_counts.get(key, 0)
            
            if count < limit_per_artist and not item.get("image_url"):
                # Fetch only if we don't have one and haven't hit limit
                item["image_url"] = self.fetch_og_image(item["url"])
                artist_counts[key] = count + 1
                logger.info(f"Scraped image for {item['artist']} - {item['title'][:20]}...")
            
            updated_items.append(item)
            
        return updated_items

    def deduplicate(self, items: List[Dict]) -> List[Dict]:
        """Deduplicate news items based on Title similarity."""
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
        
        # Enrich with images (Scrape OG tags for top items)
        # We only enrich the top N items per artist/category to save time
        enriched_news = self.enrich_with_images(clean_news, limit_per_artist=3)
        
        # Output JSON
        with open("kpop_intelligence.json", "w") as f:
            json.dump(enriched_news, f, indent=2)
            
        # Output Markdown Summary
        self.generate_markdown(enriched_news)
        
        # Output HTML Web Report
        self.generate_html(enriched_news, targets)
        
        logger.info(f"Scan complete. Found {len(enriched_news)} relevant intelligence items.")
        print(json.dumps(enriched_news, indent=2))

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
    <title>K-pop Intelligence Dashboard</title>
    <style>
        :root {
            --bg-color: #f9fafb;
            --card-bg: #ffffff;
            --text-primary: #111827;
            --text-secondary: #4b5563;
            --accent: #d946ef;
            --border: #e5e7eb;
            --header-height: 80px;
        }

        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-primary);
            margin: 0;
            padding: 20px;
            line-height: 1.5;
        }

        /* Layout */
        .dashboard-container {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            max-width: 1800px;
            margin: 0 auto;
            height: calc(100vh - 40px);
        }

        .panel {
            background: #fff;
            border-radius: 16px;
            border: 1px solid var(--border);
            display: flex;
            flex-direction: column;
            overflow: hidden;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }

        .panel-header {
            padding: 20px;
            border-bottom: 1px solid var(--border);
            background: #f8fafc;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .panel-title {
            font-size: 1.25rem;
            font-weight: 700;
            color: var(--text-primary);
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .select-wrapper {
            position: relative;
            min-width: 200px;
        }

        select {
            width: 100%;
            padding: 8px 12px;
            border-radius: 8px;
            border: 1px solid var(--border);
            font-size: 0.9rem;
            background: white;
            cursor: pointer;
            appearance: none;
            -webkit-appearance: none;
        }
        
        /* Custom arrow for select */
        .select-wrapper::after {
            content: '▼';
            font-size: 0.8rem;
            position: absolute;
            right: 12px;
            top: 50%;
            transform: translateY(-50%);
            pointer-events: none;
            color: var(--text-secondary);
        }

        .panel-content {
            flex: 1;
            overflow-y: auto;
            padding: 20px;
            background: #f1f5f9;
        }

        /* Artist Card */
        .artist-group {
            background: white;
            border-radius: 12px;
            margin-bottom: 40px;
            border: 1px solid var(--border);
            overflow: hidden;
        }
        
        .artist-header-row {
            padding: 16px 20px;
            border-bottom: 1px solid var(--border);
            display: flex;
            align-items: center;
            gap: 16px; /* Increased gap */
            background: #fff;
        }

        .artist-avatar {
            width: 48px;
            height: 48px;
            border-radius: 50%;
            object-fit: cover;
            border: 2px solid var(--accent);
            background: #f3f4f6;
            flex-shrink: 0;
        }

        .artist-name {
            font-size: 1.5rem;
            font-weight: 800;
            letter-spacing: -0.5px;
        }

        .sub-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
        }
    </style>
</head>
<body>

<div class="dashboard-container">
    <!-- Left Panel: Boy Groups -->
    <div class="panel">
        <div class="panel-header">
            <div class="panel-title">🕺 Boy Groups</div>
            <div class="select-wrapper">
                <select id="boys-select" onchange="filterList('boys-content', this.value)">
                    <option value="all">Show All</option>
                    {boys_options}
                </select>
            </div>
        </div>
        <div class="panel-content" id="boys-content">
            {boys_html}
        </div>
    </div>

    <!-- Right Panel: Girl Groups -->
    <div class="panel">
        <div class="panel-header">
            <div class="panel-title">💃 Girl Groups</div>
            <div class="select-wrapper">
                <select id="girls-select" onchange="filterList('girls-content', this.value)">
                    <option value="all">Show All</option>
                    {girls_options}
                </select>
            </div>
        </div>
        <div class="panel-content" id="girls-content">
            {girls_html}
        </div>
    </div>
</div>

<script>
    function filterList(containerId, selectedArtist) {
        const container = document.getElementById(containerId);
        const groups = container.getElementsByClassName('artist-group');
        
        for (let group of groups) {
            if (selectedArtist === 'all' || group.getAttribute('data-artist') === selectedArtist) {
                group.classList.remove('hidden');
            } else {
                group.classList.add('hidden');
            }
        }
    }
</script>

</body>
</html>
"""
        def build_artist_block(artist_name, data):
            # Static Profile Images (Fallback)
            PROFILE_IMAGES = {
                "BTS": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/65/BTS_logo_%282017%29.png/600px-BTS_logo_%282017%29.png",
                "BLACKPINK": "https://upload.wikimedia.org/wikipedia/commons/2/29/Blackpink_logo.svg", # SVG might need check, using logo
                "SEVENTEEN": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f6/Seventeen_Logo.jpg/640px-Seventeen_Logo.jpg",
                "NewJeans": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1b/NewJeans_Logo.svg/1200px-NewJeans_Logo.svg.png",
                "ENHYPEN": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6b/Enhypen_logo.svg/1200px-Enhypen_logo.svg.png",
                "ITZY": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b3/Itzy_logo.svg/1200px-Itzy_logo.svg.png",
                "NCT DREAM": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/30/NCT_Dream_logo.svg/1200px-NCT_Dream_logo.svg.png",
                "TWICE": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f3/Twice_Logo.png/640px-Twice_Logo.png",
                "Stray Kids": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f1/Stray_Kids_Logo.svg/1200px-Stray_Kids_Logo.svg.png",
                "aespa": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/23/Aespa_Logo.svg/1200px-Aespa_Logo.svg.png",
                "IVE": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c9/Ive_Logo.svg/1200px-Ive_Logo.svg.png",
                "LE SSERAFIM": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e0/Le_Sserafim_Logo.svg/1200px-Le_Sserafim_Logo.svg.png",
                "BABYMONSTER": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a2/Babymonster_Logo.svg/1200px-Babymonster_Logo.svg.png",
                "ATEEZ": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/14/Ateez_logo.png/640px-Ateez_logo.png",
                "NCT WISH": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/07/NCT_Wish_Logo.svg/1200px-NCT_Wish_Logo.svg.png",
                "TWS": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/52/TWS_Logo.svg/1200px-TWS_Logo.svg.png",
                "KISS OF LIFE": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3d/Kiss_of_Life_Logo.svg/1200px-Kiss_of_Life_Logo.svg.png",
                "BIBI": "https://i.scdn.co/image/ab6761610000e5eb989ed05e1f059c60d5b6de3d", # Spotify
                "XG": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/0d/XG_Logo.svg/1200px-XG_Logo.svg.png",
            }
            
            # Find best image for avatar
            # Priority: 1. Scraped News Image  2. Static Profile Image  3. UI Avatar
            avatar_url = ""
            
            # 1. Scraped News (Freshest)
            for item in data['comeback']:
                if item.get("image_url"):
                    avatar_url = item["image_url"]
                    break
            if not avatar_url:
                for item in data['tour']:
                    if item.get("image_url"):
                        avatar_url = item["image_url"]
                        break
            
            # 2. Static Fallback
            if not avatar_url:
                avatar_url = PROFILE_IMAGES.get(artist_name, "")
            
            # 3. Last Resort (UI Avatars)
            if not avatar_url:
                safe_name = requests.utils.quote(artist_name)
                avatar_url = f"https://ui-avatars.com/api/?name={safe_name}&background=random&color=fff&size=128"
            
            avatar_html = f'<img src="{avatar_url}" class="artist-avatar">'

            # Tour Section
            tour_rows = []
            
            # Ticket Buttons
            tm_link = f"https://www.ticketmaster.com/search?q={requests.utils.quote(artist_name)}"
            sh_link = f"https://www.stubhub.com/secure/search?q={requests.utils.quote(artist_name)}"
            buttons_html = f'''
                <div class="btn-group">
                    <a href="{tm_link}" target="_blank" class="btn tm">Ticketmaster</a>
                    <a href="{sh_link}" target="_blank" class="btn sh">StubHub</a>
                </div>
            '''
            
            if data['tour']:
                cities = set()
                for item in data['tour']:
                    cities.update(item['extracted_cities'])
                
                cities_html = ""
                if cities:
                    cities_html = f"<div style='font-size:0.85rem; margin-bottom:10px;'>🏙️ {', '.join(sorted(cities))}</div>"

                for item in data['tour'][:3]:
                    img_html = f'<img src="{item["image_url"]}" class="news-thumb">' if item.get("image_url") else '<div class="news-thumb"></div>'
                    tour_rows.append(f'''
                        <div class="news-card">
                            {img_html}
                            <div class="news-info">
                                <a href="{item["url"]}" target="_blank" class="news-link">{item["title"]}</a>
                                <div class="news-meta">{item["source"]}</div>
                            </div>
                        </div>
                    ''')
                tour_content = f"{buttons_html}{cities_html}{''.join(tour_rows)}"
            else:
                tour_content = f"{buttons_html}<div style='color:#9ca3af; font-style:italic;'>No active tour news.</div>"

            # Comeback Section
            comeback_rows = []
            if data['comeback']:
                for item in data['comeback'][:4]:
                    img_html = f'<img src="{item["image_url"]}" class="news-thumb">' if item.get("image_url") else '<div class="news-thumb"></div>'
                    comeback_rows.append(f'''
                        <div class="news-card">
                            {img_html}
                            <div class="news-info">
                                <a href="{item["url"]}" target="_blank" class="news-link">{item["title"]}</a>
                                <div class="news-meta">{item["source"]}</div>
                            </div>
                        </div>
                    ''')
                comeback_content = "".join(comeback_rows)
            else:
                comeback_content = "<div style='color:#9ca3af; font-style:italic;'>No recent comeback news.</div>"

            return f'''
            <div class="artist-group" data-artist="{artist_name}">
                <div class="artist-header-row">
                    {avatar_html}
                    <span class="artist-name">{artist_name}</span>
                </div>
                <div class="sub-grid">
                    <div class="sub-col sub-col-tour">
                        <div class="sub-title">🌍 US Tour & Tickets</div>
                        {tour_content}
                    </div>
                    <div class="sub-col">
                        <div class="sub-title">🎵 Latest Comeback</div>
                        {comeback_content}
                    </div>
                </div>
            </div>
            '''

        # Group Data
        artist_data = {}
        for item in items:
            name = item['artist']
            if name not in artist_data:
                artist_data[name] = {"tour": [], "comeback": []}
            
            key = "tour" if "Tour" in item['topic'] else "comeback"
            artist_data[name][key].append(item)

        # Separate by Side
        boys_html = []
        boys_options = []
        girls_html = []
        girls_options = []
        
        # Sort artists
        sorted_artists = sorted(artist_data.keys())
        
        for artist in sorted_artists:
            cat = categories.get(artist, "Unknown")
            # Map categories to sides
            is_boy_side = cat == "Boy Group"
            is_girl_side = cat in ["Girl Group", "Co-ed Group", "Soloist"] # Map others to Right for now (or split logic)
            
            # Specific Check for known genders if Category is Soloist
            # BIBI -> Female
            # We assume Right Side unless Boy Group.
            
            html_block = build_artist_block(artist, artist_data[artist])
            option_block = f'<option value="{artist}">{artist}</option>'
            
            if is_boy_side:
                boys_html.append(html_block)
                boys_options.append(option_block)
            else:
                girls_html.append(html_block)
                girls_options.append(option_block)

        final_html = html_template.replace("{boys_options}", "".join(boys_options)) \
                                  .replace("{boys_html}", "".join(boys_html) if boys_html else '<div style="padding:20px; text-align:center;">No data</div>') \
                                  .replace("{girls_options}", "".join(girls_options)) \
                                  .replace("{girls_html}", "".join(girls_html) if girls_html else '<div style="padding:20px; text-align:center;">No data</div>')
        
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
