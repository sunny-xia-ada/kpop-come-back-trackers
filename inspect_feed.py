import requests
from bs4 import BeautifulSoup

def inspect_feed():
    query = "BTS US Tour"
    encoded_query = requests.utils.quote(query)
    rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"
    
    print(f"Fetching: {rss_url}")
    response = requests.get(rss_url)
    
    # Print raw first item
    print("\n--- RAW XML (First 1000 chars) ---")
    print(response.text[:1000])
    
    soup = BeautifulSoup(response.content, "xml")
    items = soup.find_all("item")
    
    if items:
        item = items[0]
        print("\n--- First Item ---")
        print(item.prettify())
        
        print("\n--- Description Content ---")
        if item.description:
            print(item.description.text)
    else:
        print("No items found.")

if __name__ == "__main__":
    inspect_feed()
