'''transit_data_manager.py
Data Manager that will maintain and update the information for display 
'''

# GENERAL
from datetime import date, datetime
import json
import os
import sys
import time

# SPECIFIC
from tabulate import tabulate
import pandas as pd
pd.set_option('display.max_rows', None)

# PROJECT
from web_crawlers.crawler_path import PATHScraper 
from web_crawlers.crawler_hb_str_clean import ParkingScraper

ACCEPTABLE_LOCS = ['HOB', '33rd', 'WTC', 'JSQ']
DAY_CONV = {
            'Monday': 0, 
            'Tuesday': 1, 
            'Wednesday': 2, 
            'Thursday': 3, 
            'Friday': 4, 
            'Saturday': 5,
            'Sunday': 6
            }
PROJ_DIR_PATH = os.path.dirname(os.path.abspath(__file__))
MAX_DISP_COL = 25

class DataManager:
    def __init__(self, all_locations, time_range='all'):
        self.all_locations = all_locations
        self.time_range = time_range
        self.time_now = datetime.now()
        self.all_attributes = [self.raw_street_clean_data, self.raw_street_clean_data,
                                self.filtered_street_clean_data, self.filtered_path_data]


    @property
    def raw_path_train_data(self):
        if isinstance(self.all_locations, list):
            for i, location_pair in enumerate(self.all_locations):
                self.start_loc, self.end_loc = location_pair.split(':')
                self.headers, transit_data = PATHScraper(self.start_loc, self.end_loc).train_schedule_data
                time_df = pd.DataFrame(transit_data, columns=self.headers)
            
                # DF Combination
                first_col = time_df.iloc[:,0]
                last_col = time_df.iloc[:,-1]
                location = self.headers[-1].split(': ')[1]
                short_df = pd.concat([first_col, last_col], axis=1, keys=['Start_Time', 'End_Time', 'Location', 'Remarks'])
                short_df['Location'] = location
                short_df['Category'] = 'PATH'

                if i == 0:
                    comb_df = short_df
                else:
                    comb_df = comb_df.append(short_df)
            
        return comb_df

    @property
    def raw_street_clean_data(self):
        pd.set_option('display.max_columns', None)
        cleaning_df = pd.DataFrame(ParkingScraper().main())
        cleaning_df['Start Date_Fix'] = cleaning_df['Start Date'].apply(lambda x: DAY_CONV[x])
        cleaning_df['End Date_Fix'] = cleaning_df['End Date'].apply(lambda x: DAY_CONV[x])

        cleaning_df['Start_Time'] = cleaning_df['Start Hour'].apply(self.convert_ampm_dt)
        cleaning_df['End_Time'] = cleaning_df['End Hour'].apply(self.convert_ampm_dt)
        cleaning_df = cleaning_df.drop(['Start Hour', 'End Hour'], axis=1)
        return cleaning_df


    @property
    def filtered_path_data(self):
        '''Filter the existing PATH data based on the current time'''
        self.time_now = datetime.now()
        df = self.raw_path_train_data

        # Convert to Datetime
        df['Start_Time'] = df['Start_Time'].apply(self.convert_ampm_dt)
        df['End_Time'] = df['End_Time'].apply(self.convert_ampm_dt)

        return df[(df['Start_Time'] > self.time_now)]


    @property
    def filtered_street_clean_data(self):
        self.time_now = datetime.now()
        df = self.raw_street_clean_data
        df['Category'] = 'PARK'
        df['Remarks'] = df['Start Street'].str.cat(df['End Street'],sep=" through ")
        df['Remarks'] = df['Remarks'].str.cat(df['Start Date'],sep=" from ")
        df['Remarks'] = df['Remarks'].str.cat(df['End Date'],sep=" to ")

        df['Location'] = df['Base Street']
        df['Start Date'] = df['End Date_Fix']
        df['End Date'] = df['End Date_Fix']

        df = df[(df['End Date'] >= self.time_now.weekday())]
        df = df.drop(['Start Street', 'End Street', 'Base Street', 'Side', 'End Date_Fix', 'Start Date_Fix'], axis=1)
        return df[(df['Start_Time'] > self.time_now)]


    def convert_ampm_dt(self, row_time):
        '''Convert str(time) w/ AM/PM to datetime'''
        fix_format = '%I:%M%p'

        try:
            value = datetime.strptime(row_time, fix_format)
            value = value.replace(
                                    year=self.time_now.year,
                                    month=self.time_now.month,
                                    day=self.time_now.day)
        except ValueError:
            fix_format = '%I %p'
            value = datetime.strptime(row_time, fix_format)
            value = value.replace(
                                year=self.time_now.year,
                                month=self.time_now.month,
                                day=self.time_now.day,
                                minute=0)
        return value


    def combine_dfs(self):
        '''Method to combine and sort PATH and cleaning data'''
        result = self.filtered_street_clean_data.append(self.filtered_path_data, sort='True')
        result = result.sort_values(by=['Start_Time'])
        return result


    def write_config(self):
        '''Write existing filtered df to json config'''

        self.all_data = self.combine_dfs()
        dict_form = self.all_data.to_json(orient="values")
        dict_form = {'data': []}

        for row in self.all_data.itertuples(index=False):
            category = row.Category
            start_time = '{}:{:02d}'.format(row.Start_Time.hour, row.Start_Time.minute)
            end_time = '{}:{:02d}'.format(row.End_Time.hour, row.End_Time.minute)
            location = row.Location
            remarks = row.Remarks

            if not isinstance(remarks, str):
                remarks = ''
            
            config_element = {
                                'Category': category,
                                'Location': location,
                                'Start Time': start_time,
                                'End Time': end_time,
                                'Remarks': remarks
                            }

            dict_form['data'].append(config_element)

        file_name = os.path.join(PROJ_DIR_PATH, 'configs', 'schedule_data.json')
        with open(file_name, 'w+') as config:
            json.dump(dict_form, config, indent=4)

    def display_config(self):
        '''Method to load the config'''

        file_name = os.path.join(PROJ_DIR_PATH, 'configs', 'schedule_data.json')
        with open(file_name, 'r') as config:
            load_transit_data = json.load(config)['data']

        row_data = []
        for i, row in enumerate(load_transit_data):
            headers = list(row.keys())
            add_values = list(row.values())
            row_data.append(add_values)

        while True:
            self.time_now = datetime.now()
            conv_format = '%H:%M'
            os.system('clear')

            # Go reset data every 10 mins
            if len(row_data) == 0:
                print('No Data Left to Show!!')
                time.sleep(600)
                return

            start_time = row_data[0][2]
            start_time = datetime.strptime(start_time, conv_format).replace(
                                year=self.time_now.year,
                                month=self.time_now.month,
                                day=self.time_now.day)
            
            table = tabulate(row_data[0:MAX_DISP_COL], headers=headers, tablefmt="psql")
            date_time = self.time_now.strftime("%H:%M:%S")
            print('\n\nCurrent Time: {}\n{}'.format(date_time, table))

            if self.time_now > start_time:
                row_data = row_data[1:]
                time.sleep(1)
            else:
                time.sleep(1)


if __name__ == "__main__":
    all_locations = sys.argv[1:]
    while True:
        tm = DataManager(all_locations)
        tm.write_config()
        tm.display_config()