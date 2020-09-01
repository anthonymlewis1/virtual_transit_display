'''crawler_hb_str_clean.py 
Web crawler will go into the Hoboken Street Cleaning and return the timetable
'''

# GENERAL
import os
import random
import re
import time

# SPECIFIC
import geocoder
import requests
from bs4 import BeautifulSoup
import pandas as pd

BING_MAPS_API = ''
HOBO_CLEAN_SCHED = 'https://www.hobokennj.gov/resources/street-cleaning-schedule'

class ParkingScraper:
    def __init__(self):
        self.all_results = []
        self.parking_dict = []
        self.cleaned_data = []


    def main(self):
        self.get_parking_data()
        self.organize_parking_data()
        self.clean_parking_data()
        return self.cleaned_data

    def get_parking_data(self):
        '''Get the table from the website'''
        page = requests.get(HOBO_CLEAN_SCHED)
        soup = BeautifulSoup(page.text, "html.parser")
        self.table = soup.find_all("div", {"class": "table-content bottom"})


    def organize_parking_data(self):
        '''Structurally fix the table cells'''
        curr_data = []

        # Columnify within the dicts
        for i, cell in enumerate(self.table):
            cell_value = ''.join(re.findall('(?<=<div>)((&|\s*|\w|[^<])*<)', str(cell))[0]).replace('<', '')

            if i % 4 == 0 and i != 0:
                self.all_results.append(curr_data)
                curr_data = [cell_value]
            else:
                curr_data.append(cell_value)

        # Organize into list of dictionary
        corr_dict = {}
        headers = self.all_results[0]
        for bulk_result in self.all_results[1:]:
            corr_dict = {}

            for i, parameter in enumerate(bulk_result):
                corr_dict[headers[i]] = parameter

            self.parking_dict.append(corr_dict)


    def clean_parking_data(self):
        ''' Clean the parking data'''
        for park_group in self.parking_dict:
            dup_add = False
            base_street = park_group['Street'].replace('.', '')
            park_group['Base Street'] = base_street


            days_hours = 'Days &amp; Hours'
            set_hours = re.findall('(\d{1,2} [apmno]{2,4})', park_group[days_hours])

            # Two Locations or Range Determination
            try:
                set_streets = re.findall('(.*) to (.*)', park_group['Location'])[0]
            except IndexError:
                set_streets = re.findall('(.*) and (.*)', park_group['Location'])[0]
                dup_add = True

            # Single Date or Multiple Dates
            if 'through' in park_group[days_hours]:
                set_day = park_group[days_hours].split(' through ')

                park_group['Start Date'] = set_day[0]
                park_group['End Date'] = set_day[1].split(' -')[0]

            else:
                set_day = park_group[days_hours].split(' -')[0]
                park_group['Start Date'] = set_day
                park_group['End Date'] = set_day

            park_group['Start Hour'] = set_hours[0]
            park_group['End Hour'] = set_hours[1].replace('noon', 'pm')

            # Delete unnecessary fields
            del park_group[days_hours]
            del park_group['Location']
            del park_group['Street']

            if dup_add:
                park_group['Start Street'] = set_streets[0]
                park_group['End Street'] = set_streets[0]
                self.cleaned_data.append(park_group)
                park_group['Start Street'] = set_streets[1]
                park_group['End Street'] = set_streets[1]
            else:
                park_group['Start Street'] = set_streets[0]
                park_group['End Street'] = set_streets[1]

            
            # conv_coords = self.convert_to_coord_data(base_street, set_streets[0], set_streets[1])
            # park_group['Coordinates'] = conv_coords
            self.cleaned_data.append(park_group)


    def convert_to_coord_data(self, base_street, start_street, end_street):
        location1 = "{} and {}, Hoboken, NJ, 07030".format(base_street, start_street)
        lat_long = geocoder.bing(location1, key=BING_MAPS_API).latlng

        location2 = "{} and {}, Hoboken, NJ, 07030".format(base_street, end_street)
        late_long_2 = geocoder.bing(location2, key=BING_MAPS_API).latlng

        return (lat_long, late_long_2)


def main():
    parking_data = ParkingScraper().main()

if __name__ == "__main__":
    main()