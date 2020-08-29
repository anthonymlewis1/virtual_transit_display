'''crawler_hb_path.py
Web crawler will go into any specified PATH schedule and return a dynamic timestable
https://old.panynj.gov/path/schedules-full-screen-mod.cfm?id=HOB_33rd_Weekday
'''

# GENERAL
import re

# SPECIFIC
import pandas as pd
import requests
from bs4 import BeautifulSoup


class PATHScraper:
    ''' Create a web crawler that goes and extracts given PATH information'''
    def __init__(self, start_loc, end_loc, time_period='Weekday'):
        self.start_loc = start_loc
        self.end_loc = end_loc
        self.time_period = time_period

    @property
    def train_schedule_url(self):
        map_id = '{}_{}_{}'.format(self.start_loc, self.end_loc, self.time_period)
        return 'https://old.panynj.gov/path/schedules-full-screen-mod.cfm?id={}'.format(map_id)

    @property
    def train_schedule_data(self):
        page = requests.get(self.train_schedule_url)
        soup = BeautifulSoup(page.text, "html.parser")

        table_headers = soup.findAll('table')[0].findAll('th')
        table_data = soup.findAll('table')[1]
        return self.clean_data(table_headers, table_data)

    def clean_data(self, table_headers, table_data):
        clean_headers = []

        header_length = int(len(table_headers) / 2)
        for i, table_header in enumerate(table_headers):
            if i == header_length:
                break

            # Header Fixing
            regex_pattern = '>(.*)<'
            action = re.findall(regex_pattern, str(table_header))[0]
            location = re.findall(regex_pattern, str(table_headers[i + header_length]))[0]
            fixed_name = '{}: {}'.format(action, location)
            clean_headers.append(fixed_name)

        # Row Fixing
        num_elements_row = header_length
        table_rows = re.findall('(\d{1,2}:\d{2}\w*)', str(table_data))
        chunks = [table_rows[x:x+num_elements_row] for x in range(0, len(table_rows), num_elements_row)]           
        return clean_headers, chunks

def main():
    start_loc = 'HOB'
    end_loc = '33rd'
    headers, parking_data = PATHScraper(start_loc, end_loc).train_schedule_data

    df = pd.DataFrame(parking_data, columns = headers)  

if __name__ == "__main__":
    main()
        