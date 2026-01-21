"""A dummy scraper for ar5iv articles."""
import os

import requests
from bs4 import BeautifulSoup

def scrape_ar5iv_html(arxiv_id):
    """
    Fetches the HTML content of an ar5iv article given its arXiv ID.
    
    :param arxiv_id: The ID of the paper (e.g., '1910.06709').
    :return: The formatted HTML content string, or None if the request fails.
    """
    url = f"https://ar5iv.org/abs/{arxiv_id}"

    try:
        # 1. Fetch the raw HTML content
        response = requests.get(url, timeout=15)
        response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)

        # 2. Parse the HTML content, skip for now
        # 3. Return parsed content
        soup = BeautifulSoup(response.content, 'html.parser')
        return soup.prettify() # Fallback: return the whole page HTML

    except requests.exceptions.HTTPError as errh:
        print(f"HTTP Error: {errh}")
    except requests.exceptions.ConnectionError as errc:
        print(f"Connection Error: {errc}")
    except requests.exceptions.Timeout as errt:
        print(f"Timeout Error: {errt}")
    except requests.exceptions.RequestException as err:
        print(f"An unexpected error occurred: {err}")
        
    return None


if __name__ == "__main__":
    target_papers = ['1511.00113', '1904.07985', '1610.01765', '1601.00948', '1711.00807']

    for article_id in target_papers:
        print(f"Scraping article ID: {article_id}")
        html_output = scrape_ar5iv_html(article_id)

        if html_output:
            # Define where to save the output file
            script_dir = os.path.dirname(os.path.abspath(__file__))
            SAVE_DIRECTORY = os.path.join(script_dir, os.pardir, "data") 
            file_path = os.path.join(SAVE_DIRECTORY, f"{article_id}.html")

            try:
                # 4. Create the directory if it doesn't exist
                os.makedirs(SAVE_DIRECTORY, exist_ok=True) 

                # 5. Save the content
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(html_output)
                
                print(f"Content successfully saved to: {file_path}")

            except OSError as e:
                print(f"Error saving to {SAVE_DIRECTORY}: {e}")