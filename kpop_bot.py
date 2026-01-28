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

        # Bad Image Patterns (Google News Logos, tracking pixels, etc.)
        self.BAD_IMAGE_PATTERNS = [
            "lh3.googleusercontent.com",
            "google.com/logos",
            "gstatic.com",
            "gnews-logo"
        ]

    def is_valid_image(self, url: str) -> bool:
        """Check if image URL is valid and not a known placeholder."""
        if not url:
            return False
        for pattern in self.BAD_IMAGE_PATTERNS:
            if pattern in url:
                return False
        return True

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
                    candidate_url = img_tag["src"]
                    if self.is_valid_image(candidate_url):
                        image_url = candidate_url

            # Combined text for analysis
            full_text = f"{title} {description}"

            # 1. Source Whitelisting (Strict Mode: Skip if not authoritative)
            if not self.is_whitelisted_source_name(source_name) and not self.is_whitelisted(link):
                 if not self.is_whitelisted_source_name(source_name):
                     continue

            # 2. Keyword Validation
            if not self.validate_content(full_text):
                continue

            # 3. Extraction
            metadata = self.extract_metadata(full_text)
            
            # Final image check before adding
            if image_url and not self.is_valid_image(image_url):
                 image_url = ""

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
                    img_src = og_image["content"]
                    if self.is_valid_image(img_src):
                        return img_src
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
        
        # Check if we have cached data to speed up UI dev
        if os.path.exists("kpop_intelligence.json"):
            logger.info("Loading cached intelligence data...")
            with open("kpop_intelligence.json", "r") as f:
                enriched_news = json.load(f)
        else:
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
        
        logger.info(f"Scan complete. Processing {len(enriched_news)} items.")

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
        # Static Profile Images
        PROFILE_IMAGES = {
            "BTS": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/65/BTS_logo_%282017%29.png/600px-BTS_logo_%282017%29.png",
            "BLACKPINK": "https://upload.wikimedia.org/wikipedia/commons/2/29/Blackpink_logo.svg",
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
            "BIBI": "https://i.scdn.co/image/ab6761610000e5eb989ed05e1f059c60d5b6de3d",
            "XG": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/0d/XG_Logo.svg/1200px-XG_Logo.svg.png",
            "Cortis": "",
            "All Day Project": ""
        }

        # Prepare Data for Frontend
        artist_data = {}
        processed_artists = set()
        
        for item in items:
            name = item['artist']
            processed_artists.add(name)
            if name not in artist_data:
                artist_data[name] = {"tour": [], "comeback": [], "avatar": "", "category": categories.get(name, "Unknown")}
            
            key = "tour" if "Tour" in item['topic'] else "comeback"
            artist_data[name][key].append(item)

        # Avatar Resolution
        for name, data in artist_data.items():
            avatar = ""
            # Priority 1: Comeback News Image
            for item in data['comeback']:
                if item.get("image_url"):
                    avatar = item["image_url"]
                    break
            # Priority 2: Tour News Image
            if not avatar:
                for item in data['tour']:
                    if item.get("image_url"):
                        avatar = item["image_url"]
                        break
            # Priority 3: Static Profile
            if not avatar:
                avatar = PROFILE_IMAGES.get(name, "")
            
            # Priority 4: UI Avatar
            if not avatar:
                safe_name = requests.utils.quote(name)
                avatar = f"https://ui-avatars.com/api/?name={safe_name}&background=random&color=fff&size=200"
            
            artist_data[name]["avatar"] = avatar
        
        # Sort for dropdown
        sorted_artists = sorted(list(processed_artists))

        html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>K-Pop Intelligence</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg: #0f172a;
            --surface: #1e293b;
            --surface-hover: #334155;
            --text: #f8fafc;
            --text-muted: #94a3b8;
            --violet: #8b5cf6;
            --pink: #ec4899;
            --glass: rgba(30, 41, 59, 0.7);
            --border: rgba(255, 255, 255, 0.1);
        }
        
        * { box-sizing: border-box; margin: 0; padding: 0; }
        
        body {
            font-family: 'Inter', sans-serif;
            background-color: var(--bg);
            color: var(--text);
            min-height: 100vh;
            overflow-x: hidden;
            display: flex;
            flex-direction: column;
            align-items: center;
        }

        /* Floating Nav */
        .nav-container {
            position: fixed;
            top: 24px;
            z-index: 100;
            background: var(--glass);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            padding: 12px 24px;
            border-radius: 999px;
            border: 1px solid var(--border);
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            display: flex;
            gap: 16px;
            align-items: center;
        }

        .nav-logo {
            font-weight: 800;
            background: linear-gradient(135deg, var(--violet), var(--pink));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-size: 1.2rem;
            letter-spacing: -0.02em;
        }

        select {
            background: rgba(0, 0, 0, 0.2);
            border: 1px solid var(--border);
            color: var(--text);
            padding: 8px 32px 8px 16px;
            border-radius: 20px;
            font-family: inherit;
            font-size: 0.95rem;
            cursor: pointer;
            outline: none;
            appearance: none;
            background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 24 24' fill='none' stroke='%2394a3b8' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='6 9 12 15 18 9'%3E%3C/polyline%3E%3C/svg%3E");
            background-repeat: no-repeat;
            background-position: right 8px center;
            background-size: 16px;
            min-width: 200px;
            transition: all 0.2s;
        }
        
        select:hover {
            background-color: rgba(255, 255, 255, 0.05);
            border-color: rgba(255, 255, 255, 0.2);
        }

        /* Hero Container */
        .main-stage {
            margin-top: 120px;
            width: 100%;
            max-width: 1200px;
            padding: 0 24px;
            animation: fadeIn 0.6s ease-out;
        }

        /* Hero Card */
        #hero-card {
            background: var(--surface);
            border-radius: 32px;
            border: 1px solid var(--border);
            overflow: hidden;
            box-shadow: 0 20px 50px -10px rgba(0, 0, 0, 0.5);
            display: grid;
            grid-template-columns: 350px 1fr;
            min-height: 600px;
        }

        /* Left Side: Avatar & Stats */
        .hero-profile {
            background: linear-gradient(to bottom, #2d1b4e, var(--surface));
            padding: 40px;
            display: flex;
            flex-direction: column;
            align-items: center;
            text-align: center;
            border-right: 1px solid var(--border);
            position: relative;
        }
        
        .hero-avatar {
            width: 200px;
            height: 200px;
            border-radius: 50%;
            object-fit: cover;
            border: 4px solid rgba(255, 255, 255, 0.1);
            box-shadow: 0 0 40px rgba(139, 92, 246, 0.3);
            margin-bottom: 24px;
        }

        .hero-name {
            font-size: 2.5rem;
            font-weight: 800;
            line-height: 1.1;
            margin-bottom: 8px;
            letter-spacing: -0.03em;
            background: linear-gradient(135deg, #fff, #94a3b8);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .hero-badge {
            display: inline-block;
            padding: 6px 16px;
            border-radius: 99px;
            font-size: 0.85rem;
            font-weight: 600;
            background: rgba(236, 72, 153, 0.1);
            color: var(--pink);
            border: 1px solid rgba(236, 72, 153, 0.2);
            margin-bottom: 32px;
        }

        /* Right Side: Content */
        .hero-content {
            padding: 40px;
            display: flex;
            flex-direction: column;
        }

        /* Tabs */
        .tabs {
            display: flex;
            gap: 24px;
            border-bottom: 1px solid var(--border);
            margin-bottom: 32px;
        }

        .tab-btn {
            background: none;
            border: none;
            color: var(--text-muted);
            font-size: 1.1rem;
            font-weight: 600;
            padding-bottom: 16px;
            cursor: pointer;
            position: relative;
            transition: color 0.2s;
        }

        .tab-btn:hover { color: var(--text); }
        .tab-btn.active { color: var(--text); }
        
        .tab-btn.active::after {
            content: '';
            position: absolute;
            bottom: -1px;
            left: 0;
            width: 100%;
            height: 3px;
            background: linear-gradient(90deg, var(--violet), var(--pink));
            border-radius: 3px 3px 0 0;
            box-shadow: 0 0 10px rgba(139, 92, 246, 0.5);
        }

        /* News Grid */
        .news-grid {
            display: grid;
            gap: 16px;
            overflow-y: auto;
            padding-right: 8px;
            max-height: 500px;
        }
        
        /* Scrollbar */
        .news-grid::-webkit-scrollbar { width: 6px; }
        .news-grid::-webkit-scrollbar-track { background: transparent; }
        .news-grid::-webkit-scrollbar-thumb { background: var(--surface-hover); border-radius: 3px; }

        .news-item {
            display: flex;
            gap: 16px;
            padding: 16px;
            background: rgba(255, 255, 255, 0.03);
            border-radius: 12px;
            border: 1px solid transparent;
            transition: all 0.2s;
            text-decoration: none;
            color: inherit;
        }

        .news-item:hover {
            background: rgba(255, 255, 255, 0.05);
            border-color: rgba(255, 255, 255, 0.1);
            transform: translateX(4px);
        }

        .news-thumb {
            width: 80px;
            height: 80px;
            border-radius: 8px;
            object-fit: cover;
            background: #000;
        }

        .news-info {
            flex: 1;
            display: flex;
            flex-direction: column;
            justify-content: center;
        }

        .news-title {
            font-weight: 600;
            font-size: 1rem;
            margin-bottom: 6px;
            line-height: 1.4;
        }

        .news-meta {
            font-size: 0.85rem;
            color: var(--text-muted);
            display: flex;
            gap: 12px;
        }

        /* Buttons */
        .ticket-row {
            margin-top: auto; /* Push to bottom of profile */
            width: 100%;
            display: flex;
            flex-direction: column;
            gap: 12px;
        }

        .btn {
            display: block;
            width: 100%;
            padding: 14px;
            border-radius: 12px;
            text-align: center;
            font-weight: 700;
            text-decoration: none;
            transition: transform 0.2s, box-shadow 0.2s;
        }

        .btn-tm {
            background: #fff;
            color: #000;
        }
        
        .btn-tm:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 20px rgba(255, 255, 255, 0.2);
        }

        .btn-sh {
            border: 1px solid rgba(255, 255, 255, 0.2);
            color: var(--text);
            background: transparent;
        }
        
        .btn-sh:hover {
            background: rgba(255, 255, 255, 0.05);
        }

        /* Animations */
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .hidden { display: none; }
        .fade-in { animation: fadeIn 0.4s ease-out; }
        
        /* Empty State */
        .empty-state {
            text-align: center;
            padding: 40px;
            color: var(--text-muted);
            font-style: italic;
        }
    </style>
</head>
<body>

    <div class="nav-container">
        <div class="nav-logo">K-POP INTEL</div>
        <select id="artist-select">
            <!-- Options populated by JS -->
        </select>
    </div>

    <div class="main-stage">
        <div id="hero-card">
            <!-- Rendered by JS -->
        </div>
    </div>

    <script>
        // Injected Data
        const KPOP_DATA = {kpop_json};
        const SORTED_ARTISTS = {artists_json};
        
        // DOM Elements
        const select = document.getElementById('artist-select');
        const heroCard = document.getElementById('hero-card');

        // Init
        function init() {
            // Populate Dropdown
            SORTED_ARTISTS.forEach(artist => {
                const opt = document.createElement('option');
                opt.value = artist;
                opt.innerText = artist;
                select.appendChild(opt);
            });

            // Set Initial Artist (First one or stored)
            renderArtist(SORTED_ARTISTS[0]);

            // Listener
            select.addEventListener('change', (e) => {
                renderArtist(e.target.value);
            });
        }

        function renderArtist(name) {
            const data = KPOP_DATA[name];
            if (!data) return;

            // Animate Out (Optional enhancement, simple replace for now)
            
            // Build HTML
            const avatar = data.avatar;
            const category = data.category;
            
            // Ticket Links
            const tmLink = `https://www.ticketmaster.com/search?q=${encodeURIComponent(name)}`;
            const shLink = `https://www.stubhub.com/secure/search?q=${encodeURIComponent(name)}`;

            const html = `
                <div class="hero-profile fade-in">
                    <img src="${avatar}" class="hero-avatar" alt="${name}">
                    <div class="hero-name">${name}</div>
                    <div class="hero-badge">${category}</div>
                    
                    <div class="ticket-row">
                        <a href="${tmLink}" target="_blank" class="btn btn-tm">Buy Tickets</a>
                        <a href="${shLink}" target="_blank" class="btn btn-sh">Compare (StubHub)</a>
                    </div>
                </div>

                <div class="hero-content fade-in">
                    <div class="tabs">
                        <button class="tab-btn active" onclick="switchTab('tour')">Live Tour</button>
                        <button class="tab-btn" onclick="switchTab('comeback')">New Music</button>
                    </div>

                    <div id="tab-content" class="news-grid">
                        ${renderNewsItems(data.tour, 'tour')}
                    </div>
                </div>
            `;
            
            heroCard.innerHTML = html;
            window.currentArtistData = data; // Store for tab switching
        }

        function renderNewsItems(items, type) {
            if (!items || items.length === 0) {
                return `
                    <div class="empty-state">
                        ${type === 'tour' ? 'No active tour dates found.' : 'No recent comeback news.'}
                    </div>
                `;
            }

            return items.map(item => {
                const img = item.image_url ? `<img src="${item.image_url}" class="news-thumb">` : `<div class="news-thumb" style="background:#334155"></div>`;
                return `
                    <a href="${item.url}" target="_blank" class="news-item">
                        ${img}
                        <div class="news-info">
                            <div class="news-title">${item.title}</div>
                            <div class="news-meta">
                                <span>${item.source}</span>
                                <span>•</span>
                                <span>${item.extracted_cities.length > 0 ? '📍 ' + item.extracted_cities.slice(0,2).join(', ') : new Date(item.published_at).toLocaleDateString()}</span>
                            </div>
                        </div>
                    </a>
                `;
            }).join('');
        }

        window.switchTab = function(tabName) {
            // Update Tab classes
            document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
            event.target.classList.add('active'); // Start simple, assumes click target is button
            
            // Render Content
            const content = document.getElementById('tab-content');
            const data = window.currentArtistData[tabName];
            
            content.innerHTML = renderNewsItems(data, tabName);
            content.classList.remove('fade-in');
            void content.offsetWidth; // trigger reflow
            content.classList.add('fade-in');
        }

        // Add proper event delegation check for switchTab if needed or just use inline onclick for simplicity in prototype
        
        init();
    </script>
</body>
</html>
"""
        final_html = html_template.replace("{kpop_json}", json.dumps(artist_data)) \
                                  .replace("{artists_json}", json.dumps(sorted_artists))
        
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
