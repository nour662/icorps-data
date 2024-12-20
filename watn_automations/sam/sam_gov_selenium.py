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

"""
This script searches the sam.gov government database for companies of interest using the company name's in the "input.csv" file.
The script will universalize the companies name's by removing any title such as "Inc", "LLC","Corp", as well as any punctuation,
in order to make it a better seach term and optimize the results outputed. The program will run the input file's records at 
20 records each time to minimize loss in the result of a crash. The format of the output will be as follows: 

keyword,legal_name,num_uei,cage,physical_address,mailing_address,entity_url,start_date,contact1,contact2,
state_country_incorporation,congressional_district

The results will appear as .csv files named "batch_1.csv", "batch_2.csv", ect. As company name's are not a unique search term,
multiple records could appear as the result of a singular search, and therfore the output will need to be cleaned. In order to 
ease the cleaning process, it is recommend to use the "merging.py" script following this program to combine all batches into a 
large .csv file. 

**Nour Ali Ahmed**
**Scott Lucarelli**
"""

#Opens Chrome and navigates through the website to the search screen
def search_keyword(driver, keyword):
    """
    This function opens chrome to the sam.gov homepage, and after the user logs in, it navigates through the website to 
    the search screen. After this, it will search through the list within "input.csv" and locate the records that appear as the 
    result of the search term. 
    """
    
    try:
        search_bar = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//input[@name="search"]'))
        )
        submit_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//button[@class="usa-button ng-star-inserted"]'))
        )

        search_bar.send_keys(keyword)
        submit_button.click()

        sleep(5)
        links = driver.find_elements(By.XPATH, '//div[@class="grid-row grid-gap"]//a')
        return [a.get_attribute('href') for a in links][:5]
    except Exception as e:
        print(f"Error searching keyword {keyword}: {e}")
        return []

#Scrapes the individual company pages for each companies information  
def scrape_links(driver, keyword, url):
    """
    This function clicks on the identified records and pulls tageted information relating to the company such as legal name,
    mailing address, physical address, website, UEI, CAGE, ect. through using the xpath of this information's location. 
    After collecting and storing the information, the function formats and returns the companies data.
    """

    try:
        driver.get(url)
        sleep(5)

        def safe_find(xpath):
            try:
                return driver.find_element(By.XPATH, xpath).text
            except Exception:
                return None

        def safe_find_attr(xpath, attr):
            try:
                return driver.find_element(By.XPATH, xpath).get_attribute(attr)
            except Exception:
                return None

        #Utilizes Xpaths to locate the targetted information on the company page 
        legal_name = safe_find('//h1[@class="grid-col margin-top-3 display-none tablet:display-block wrap"]')
        num_uei = safe_find('(//span[@class="wrap font-sans-md tablet:font-sans-lg h2"])[1]')
        cage = safe_find('(//span[@class="wrap font-sans-md tablet:font-sans-lg h2"])[2]')
        physical_address = safe_find('//ul[@class="sds-list sds-list--unstyled margin-top-1"]')
        mailing_address = safe_find('(//ul[@class="sds-list sds-list--unstyled"])[2]')
        entity_url = safe_find_attr('//a[@class="usa-link"]', 'href')
        start_date = safe_find('//span[contains(text(), "Entity Start Date")]/following-sibling::span')
        contact1 = safe_find('(//div[@class="sds-card__body padding-2"]//child::h3)[1]')
        contact2 = safe_find('(//div[@class="sds-card__body padding-2"]//child::h3)[2]')
        state_country_incorporation = safe_find('(//div[@class= "grid-col-6 sds-field ng-star-inserted"])[3]//span[2]')
        congressional_district = safe_find('(//div[@class= "grid-col-6 sds-field"])[3]//span[2]')

        physical_address_lines = physical_address.split('\n') if physical_address else None
        mailing_address_lines = mailing_address.split('\n') if mailing_address else None

        result1 = ','.join(physical_address_lines) if physical_address_lines else None
        result2 = ','.join(mailing_address_lines) if mailing_address_lines else None

        #Returns and formats the results of the search which appear on the output .csv file 
        return {
            "keyword": keyword,
            "legal_name": legal_name,
            "num_uei": num_uei,
            "cage": cage,
            "physical_address": result1,
            "mailing_address": result2,
            "entity_url": entity_url,
            "start_date": start_date,
            "contact1": contact1,
            "contact2": contact2,
            "state_country_incorporation": state_country_incorporation,
            "congressional_district": congressional_district,
        }

    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return None

#Searches through the inputted .csv file and formats the company names 
def process_batch(driver, input_list, start, end):
    """
    This function takes the companies names from the input file and universalizes them through removing punctuation and company
    titles. This allows them to have a higher success rate when reurning records.
    """

    links = {}
    batch_input = input_list[start:end]

    #Universilizes the naming conventions of each company on the .csv file by removing company titles and symbols
    for name in batch_input:
        name = str(name)
        search_input = name.lower().strip()
        search_input = search_input.replace(".", "").replace(",", "").replace("inc", "").replace("llc", "").replace("corp", "").replace("ltd", "").replace("limited", "").replace("pty", "")
        result_links = search_keyword(driver, search_input)
        links[name] = result_links

    links_data = []
    for keyword, urls in links.items():
        for url in urls:
            result = scrape_links(driver, keyword, url)
            if result:
                links_data.append(result)

    return links_data

def main(starting_batch=0):
    """
    This main function calls on all previously created functions while creating the tradional batch size and deciding on the
    naming conventions for the outputted files.
    """

    input_df = pd.read_csv("input.csv") #Calls to an external .csv file which contains the company names (User input)
    input_list = input_df["Company_Name"].tolist()

    chrome_options = Options()
    chrome_options.add_argument('--remote-debugging-port=9222')
    driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=chrome_options)


    try:
        driver.get("https://sam.gov/content/home")
        sleep(60)

        search_page_button = driver.find_element(By.XPATH, '//a[@id="search"]')
        search_page_button.click()

        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//div[@class="sds-card sds-card--collapsible sds-card--collapsed ng-star-inserted"]')))
        domain_button = driver.find_element(By.XPATH, '//div[@class="sds-card sds-card--collapsible sds-card--collapsed ng-star-inserted"]')
        domain_button.click()

        entity_domain = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '(//li[@class="usa-sidenav__item ng-star-inserted"])[3]'))
        )
        entity_domain.click()

        #Determines how many company name's the program will seach for in each batch
        batch_size = 20
        num_batches = math.ceil(len(input_list) / batch_size)

        if not os.path.exists("output"):
            os.makedirs("output")

        for i in range(starting_batch, num_batches):
            start_idx = i * batch_size
            end_idx = min(start_idx + batch_size, len(input_list))
            print(f"Processing batch {i+1}/{num_batches}, companies {start_idx+1} to {end_idx}")

            batch_data = process_batch(driver, input_list, start_idx, end_idx)

            output_df = pd.DataFrame(batch_data)

            output_filename = f"output/batch_{i+1}.csv"
            output_df.to_csv(output_filename, index=False)
            print(f"Batch {i+1} completed and saved to {output_filename}")
            driver.get("https://sam.gov/search/?index=ei&page=1&pageSize=25&sort=-relevance&sfm%5BsimpleSearch%5D%5BkeywordRadio%5D=ALL&sfm%5BsimpleSearch%5D%5BkeywordEditorTextarea%5D=&sfm%5Bstatus%5D%5Bis_active%5D=true&sfm%5Bstatus%5D%5Bis_inactive%5D=false")


    finally:
        driver.quit()

if __name__ == "__main__":
    starting_batch = int(input("Enter the batch number to start from: "))
    main(starting_batch)
