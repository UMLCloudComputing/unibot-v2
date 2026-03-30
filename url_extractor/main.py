import requests
import re
from urllib.robotparser import RobotFileParser
from urllib.parse import urlparse

def get_allowed_urls(domain):
    # Ensure domain has a scheme
    if not domain.startswith('http'):
        domain = 'https://' + domain
    
    robots_url = f"{domain.rstrip('/')}/robots.txt"
    sitemap_url = f"{domain.rstrip('/')}/sitemap.xml"
    
    # 1. Setup Robot Framework
    rp = RobotFileParser()
    rp.set_url(robots_url)
    try:
        rp.read()
    except Exception as e:
        print(f"Could not read robots.txt: {e}")
        return

    # 2. Fetch Sitemap
    try:
        response = requests.get(sitemap_url)
        response.raise_for_status()
    except Exception as e:
        print(f"Could not fetch sitemap: {e}")
        return

    # 3. Extract URLs using Regex (simple and effective for <loc> tags)
    raw_urls = re.findall(r'<loc>(.*?)</loc>', response.text)
    
    # 4. Filter by robots.txt permissions
    allowed_urls = []
    for url in raw_urls:
        if rp.can_fetch("*", url):
            allowed_urls.append(url)

    # 5. Write to file
    output_file = "allowed_urls.txt"
    with open(output_file, "w") as f:
        for url in allowed_urls:
            f.write(url + "\n")
            
    print(f"Success! {len(allowed_urls)} URLs saved to {output_file}")

# Example usage:
# get_allowed_urls("example.com")
if __name__ == "__main__":
  get_allowed_urls("uml.edu")
