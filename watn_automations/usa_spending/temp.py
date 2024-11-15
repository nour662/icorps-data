import requests
import pandas as pd
from time import sleep
from lxml import html
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
import math

def search_keyword(driver, keyword):
    try:
        search_bar = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//input[@class="search-section__input"]'))
        )

        submit_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//button[@class="search-section__button"]'))
        )

        search_bar.send_keys(keyword)
        submit_button.click()
        sleep(7)

        links = driver.find_elements(By.XPATH, '//td[@class="recipient-list__body-cell"][span[text()="R"]]/a')

        filtered_links = [link.get_attribute('href') for link in links]

        return filtered_links

    except Exception as e:
        print(f"Error searching keyword '{keyword}': {e}")
        return []



def scrape_links(driver, keyword, url):
    try:
        driver.get(url)

        def safe_find(xpath):
            try:
                element = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, xpath)))
                return element.text
            except Exception as e:
                print(f"Element not found for XPath {xpath}: {e}")
                return None

       
        legal_name = safe_find('//h2[@class="recipient-overview__title"]')
        
      
        if legal_name:
            legal_name = legal_name.split('\n')[0].strip()

        identifiers = safe_find('//td[@class="recipient-section__details-table-first-td"]')
        uei  , legacy_duns = identifiers.split("\n")

        uei = uei.strip().replace(" (UEI )" , "") if uei else None
        legacy_duns = legacy_duns.strip().replace(" (Legacy DUNS )", "") if legacy_duns else None

        cage = safe_find('(//span[@class="wrap font-sans-md tablet:font-sans-lg h2"])[2]')

        address_divs = driver.find_elements(By.XPATH, '//tr[th[contains(text(), "Address")]]/td/div')
        full_address = ', '.join(div.text.strip() for div in address_divs if div.text.strip())
        congressional_district = safe_find('//th[div[contains(text(), "Congressional District")]]/following-sibling::td/div')

        company_info = {
            "keyword": keyword,
            "legal_name": legal_name,
            "uei": uei,
            "legacy_duns": legacy_duns,
            "cage": cage,
            "full_address": full_address, 
            "congressional_district": congressional_district,
        }
        
        if uei == legacy_duns:
            legacy_duns = None 

        print(company_info)

        return company_info

    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return None

def scrape_usda_table(driver):
    wait = WebDriverWait(driver, 10)
    wait.until(EC.presence_of_element_located((By.XPATH, "//tbody[@class='usda-table__body']")))

    page_source = driver.page_source
    tree = html.fromstring(page_source)

    rows = tree.xpath("//tbody[@class='usda-table__body']/tr")

    data = []
    for row in rows:
        award_number = row.xpath(".//td[1]//a/text()")[0]
        company_name = row.xpath(".//td[2]/div/text()")[0]
        amount = row.xpath(".//td[3]/div/text()")[0]
        date = row.xpath(".//td[4]/div/text()")[0]
        award_id = row.xpath(".//td[5]//a/text()")[0]
        recipient_name = row.xpath(".//td[6]//a/text()")[0]
        agency_1 = row.xpath(".//td[7]/div/text()")[0]
        agency_2 = row.xpath(".//td[8]/div/text()")[0]

        data.append({
            'award_number': award_number,
            'company_name': company_name,
            'amount': amount,
            'date': date,
            'award_id': award_id,
            'recipient_name': recipient_name,
            'agency_1': agency_1,
            'agency_2': agency_2
        })

    return data

def get_funding_info(driver, keyword):
    funding_info = []
    try:
        awards_link = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//a[@class="recipient-section__award-button"]'))
        )
        awards_link.click()
        sleep(5)

        driver.switch_to.window(driver.window_handles[-1])  

        filter_dropdown = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH , '//button[@class="filter__dropdown-button-sm enabled subaward-dropdown__button"]'))
        )
        filter_dropdown.click()

        subaward_dropdown = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH , '//button[contains(text(), "Subawards")]'))
        )
        subaward_dropdown.click()

        sleep(5)

        funding_info = scrape_usda_table(driver)

        driver.close()   
        driver.switch_to.window(driver.window_handles[0])  

    except Exception as e:
        print(f"Error getting funding info for '{keyword}': {e}")

    return funding_info

def process_batch(driver, input_list, start, end, funding_output_folder, batch_number):
    company_data = []
    funding_data = []

    batch_input = input_list[start:end]

    for name in batch_input:
        search_input = str(name)
        result_links = search_keyword(driver, search_input)
        
        for url in result_links:
            company_info = scrape_links(driver, search_input, url)
            if company_info:
                company_data.append(company_info)
                funding_info = get_funding_info(driver, search_input)
                if funding_info: 
                    funding_data.extend(funding_info)

    company_df = pd.DataFrame(company_data)
    company_filename = f"company_output/company_batch_{batch_number}.csv"
    company_df.to_csv(company_filename, index=False)
    print(f"Batch {batch_number} company data saved to '{company_filename}'")

    if funding_data:
        funding_df = pd.DataFrame(funding_data)
        funding_filename = f"{funding_output_folder}/funding_output_{batch_number}.csv"
        funding_df.to_csv(funding_filename, index=False)
        print(f"Funding info saved to '{funding_filename}'")

def main(starting_batch=0):
    input_list = ['JJTZLGTS4W36']

    chrome_options = Options()
    chrome_options.add_argument('--remote-debugging-port=9222')
    driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=chrome_options)

    funding_output_folder = "funding_output"  

    try:
        driver.get("https://www.usaspending.gov/recipient")
        sleep(5)

        batch_size = 20
        num_batches = math.ceil(len(input_list) / batch_size)

        if not os.path.exists("company_output"):
            os.makedirs("company_output")

        if not os.path.exists(funding_output_folder):
            os.makedirs(funding_output_folder)

        for i in range(starting_batch, num_batches):
            start_idx = i * batch_size
            end_idx = min(start_idx + batch_size, len(input_list))
            print(f"Processing batch {i+1}/{num_batches}, companies {start_idx+1} to {end_idx}")

            process_batch(driver, input_list, start_idx, end_idx, funding_output_folder, i+1)

        driver.get("https://www.usaspending.gov/recipient")

    except Exception as e:
        print(f"Error in main function: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    starting_batch = int(input("Enter the batch number to start from: "))
    main(starting_batch)
