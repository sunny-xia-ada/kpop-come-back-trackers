from kpop_bot import KpopIntelligenceBot

def debug_filter():
    bot = KpopIntelligenceBot()
    bad_url = "https://lh3.googleusercontent.com/J6_coFbogxhRI9iM864NL_liGXvsQp2AupsKei7z0cNNfDvGUmWUy20nuUhkREQyrpY4bEeIBuc=s0-w300-rw"
    
    print(f"Testing URL: {bad_url}")
    print(f"Patterns: {bot.BAD_IMAGE_PATTERNS}")
    
    is_valid = bot.is_valid_image(bad_url)
    print(f"Result: {is_valid}")
    
    if is_valid:
        print("FAIL: Bad URL was marked as valid.")
    else:
        print("SUCCESS: Bad URL was caught.")

if __name__ == "__main__":
    debug_filter()
