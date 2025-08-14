from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import csv
import time

# Initialises browser
def init_browser():
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    # Suppress noisy Chrome logs
    options.add_experimental_option("excludeSwitches", ["enable-logging"])
    options.add_argument("--disable-logging")
    return webdriver.Chrome(options=options)

# Closes RockAuto popup
def close_popup(driver):
    try:
        print("→ Checking for popup...")
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'img[alt="Close"]'))
        )
        close_button = driver.find_element(By.CSS_SELECTOR, 'img[alt="Close"]')
        close_button.click()
        print("→ Popup closed.")
        time.sleep(1)
    except:
        print("→ No popup found.")

# Inputs the YMM into the search bar
def perform_top_search(driver, search_term):
    try:
        # Use RockAuto's main search box selector
        search_box = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'input[placeholder*="year make model"]'))
        )
        search_box.clear()
        search_box.send_keys(search_term)
        time.sleep(0.5)
        search_box.send_keys(Keys.ENTER)
        print(f"→ Performed top search for: {search_term}")
        # Let results load
        time.sleep(3)
    except Exception as e:
        print(f"[!] Top search failed ({type(e).__name__}): {e}")

# ---- Shared helper used by all filter scrapers on a loaded results page ----
def _extract_brand_and_part_from_results_page(driver, brand_filter=None):
    """
    Assumes the driver is currently on a RockAuto search results page
    where parts are listed with manufacturer + part number.
    Returns a list like ["Brand: Part", ...] filtered by brand_filter if provided.
    """
    try:
        # Wait for part numbers and manufacturers to appear
        WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'span.listing-final-partnumber.as-link-if-js'))
        )
        WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'span.listing-final-manufacturer'))
        )
        time.sleep(1)
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        results = []

        brands = soup.select('span.listing-final-manufacturer')
        parts = soup.select('span.listing-final-partnumber.as-link-if-js')
        if not brands or not parts:
            print("[!] No filter elements found on page.")
            return []
        if len(brands) != len(parts):
            print(f"[!] Warning: found {len(brands)} brands but {len(parts)} parts; pairing by index.")

        for brand_tag, part_tag in zip(brands, parts):
            brand = brand_tag.get_text(strip=True)
            part = part_tag.get_text(strip=True)
            if brand_filter and not any(b.lower() in brand.lower() for b in brand_filter):
                continue
            results.append(f"{brand}: {part}")

        return results

    except Exception as e:
        print(f"[!] Results extraction failed ({type(e).__name__}): {e}")
        return []

# Finds oil filter brands and part numbers
def scrape_oil_filters(driver, brand_filter=None):
    try:
        return _extract_brand_and_part_from_results_page(driver, brand_filter)
    except Exception as e:
        print(f"[!] Oil filter scraping failed ({type(e).__name__}): {e}")
        return []

# Finds engine air filter brands and part numbers
def scrape_engine_air_filters(driver, brand_filter=None):
    try:
        return _extract_brand_and_part_from_results_page(driver, brand_filter)
    except Exception as e:
        print(f"[!] Engine air filter scraping failed ({type(e).__name__}): {e}")
        return []

# Finds cabin air filter brands and part numbers
def scrape_cabin_air_filters(driver, brand_filter=None):
    try:
        return _extract_brand_and_part_from_results_page(driver, brand_filter)
    except Exception as e:
        print(f"[!] Cabin air filter scraping failed ({type(e).__name__}): {e}")
        return []

# Finds oil types and strips for viscosity
def scrape_oil_types(driver):
    try:
        # Wait for oil type spans
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'span.span-link-underline-remover'))
        )
        time.sleep(1)
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        viscosities = []
        for span in soup.select('span.span-link-underline-remover'):
            text = span.get_text(strip=True)
            # Extract viscosity pattern like '5W-30'
            match = re.search(r"(\d+[wW]-\d+)", text)
            if match:
                viscosities.append(match.group(1).lower())
        # Remove duplicates
        seen = set()
        unique = []
        for v in viscosities:
            if v not in seen:
                seen.add(v)
                unique.append(v)
        return unique

    except Exception as e:
        print(f"[!] Oil type scraping failed ({type(e).__name__}): {e}")
        return []

def scrape_oil_info(driver, search_base, filters):
    """
    Gathers:
        - oil filters (brands: Mobil, Wix, Fram)
        - oil types
        - engine air filters (searches '<YMME> air filter'; brands: Wix, Fram)
        - cabin air filters (brands: Wix, Fram)
        - oil capacity (heuristic)
    """
    try:
        driver.get("https://www.rockauto.com/")
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, 'body'))
        )
        time.sleep(2)
        close_popup(driver)
        
        oil_filters = "N/A"
        oil_types = "N/A"
        engine_air_filters = "N/A"
        cabin_air_filters = "N/A"
        oil_capacity = "N/A"

        #only run the scraper on the items needed
        if "Cabin Air Filter" in filters:
            # Cabin air filters — only Wix, Fram
            perform_top_search(driver, f"{search_base} cabin air filter")
            time.sleep(0.5)
            cabin_air_filters = scrape_cabin_air_filters(driver, ["Wix", "Fram"])

        if "Engine Air Filter" in filters:
            # Engine air filters — search uses "air filter" (not "engine air filter"); only Wix, Fram
            perform_top_search(driver, f"{search_base} air filter")
            time.sleep(0.5)
            engine_air_filters = scrape_engine_air_filters(driver, ["Wix", "Fram"])

        if "Oil Capacity" in filters:
            # Capacity heuristic (unchanged)
            oil_capacity_estimates = {
                '1.4l l4': '4.0 quarts',
                '1.8l l4': '4.4 quarts',
                '2.0l l4': '4.7 quarts',
                '2.4l l4': '5.5 quarts',
                '5.0l v8': '7.7 quarts'
            }
            engine_key = ' '.join(search_base.lower().split()[-2:])
            if engine_key.endswith('4l'):
                engine_key = engine_key.replace('4l', 'l4')
            oil_capacity = oil_capacity_estimates.get(engine_key, 'Unknown')

        if "Oil Filters" in filters:
            # Oil filters — allow Mobil, Wix, Fram
            perform_top_search(driver, f"{search_base} oil filter")
            time.sleep(0.5)
            oil_filters = scrape_oil_filters(driver, ["Mobil", "Wix", "Fram"])

        if "Oil Types" in filters:
            # Oil types
            perform_top_search(driver, f"{search_base} oil")
            time.sleep(0.5)
            oil_types = scrape_oil_types(driver)

        return {
            'oil_filters': oil_filters,
            'oil_types': oil_types,
            'engine_air_filters': engine_air_filters,
            'cabin_air_filters': cabin_air_filters,
            'oil_capacity': oil_capacity
        }

    except Exception as e:
        print(f"[!] Failed to scrape info ({type(e).__name__}): {e}")
        return {
            'oil_filters': [],
            'oil_types': [],
            'engine_air_filters': [],
            'cabin_air_filters': [],
            'oil_capacity': 'Unknown'
        }

def runScrape(desc, filters):
    print("supplying scraper with info")

    driver = init_browser()
    results = {}

    print(f"\n=== {desc} ===")
    data = scrape_oil_info(driver, desc, filters)

    print("Oil Filters:")
    if data['oil_filters']:
        for f in data['oil_filters']:
            print(' -', f)
    else:
        print(' (none found)')

    print("Oil Types:")
    if data['oil_types']:
        for o in data['oil_types']:
            print(' -', o)
    else:
        print(' (none found)')

    print("Engine Air Filters (Wix/Fram only):")
    if data['engine_air_filters']:
        for f in data['engine_air_filters']:
            print(' -', f)
    else:
        print(' (none found)')

    print("Cabin Air Filters (Wix/Fram only):")
    if data['cabin_air_filters']:
        for f in data['cabin_air_filters']:
            print(' -', f)
    else:
        print(' (none found)')

    print("Oil Capacity:", data['oil_capacity'])

    results = {
        'Car':desc,
        'Oil Filters': '\n'.join(data['oil_filters']),
        'Oil Types': '\n'.join(data['oil_types']),
        'Engine Air Filters': '\n'.join(data['engine_air_filters']),
        'Cabin Air Filters': '\n'.join(data['cabin_air_filters']),
        'Oil Capacity': data['oil_capacity']
    }

    driver.quit()
    # if results:
    #     mode = 'a' if os.path.isfile('results.csv') else 'w'
    #     with open('results.csv', mode, newline='', encoding='utf-8') as f:
    #         writer = csv.DictWriter(f, fieldnames=results[0].keys())
    #         if mode == 'w': writer.writeheader()
    #         writer.writerows(results)
    #     print("\n Results saved to results.csv")
    # else:
    #     print("\n No results to save.")

    print("Here's what we found!")
    print(type(results))
    return results