'''transit_data_manager.py
Data Manager that will maintain and update the information for display 
'''

# GENERAL
from datetime import date, datetime
import json
import os
import sys

# SPECIFIC
import pandas as pd

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

class DataManager:
    def __init__(self, all_locations, time_range='all'):
        self.start_loc, self.end_loc = all_locations.split(':')
        self.time_range = time_range
        # self.closest_train_time = self.filtered_path_data.iloc[0,0]
        self.time_now = datetime.now()


    @property
    def raw_path_train_data(self):
        self.headers, transit_data = PATHScraper(self.start_loc, self.end_loc).train_schedule_data
        time_df = pd.DataFrame(transit_data, columns = self.headers)  
        return time_df.apply(self.convert_ampm_dt)


    @property
    def raw_street_clean_data(self):
        pd.set_option('display.max_columns', None)
        cleaning_df = pd.DataFrame(ParkingScraper().main())
        cleaning_df['Start Date'] = cleaning_df['Start Date'].apply(lambda x: DAY_CONV[x])
        cleaning_df['Start Time'] = cleaning_df['Start Hour'].apply(self.convert_ampm_dt)
        cleaning_df['End Time'] = cleaning_df['End Hour'].apply(self.convert_ampm_dt)
        cleaning_df = cleaning_df.drop(['Start Hour', 'End Hour'], axis=1)
        return cleaning_df


    @property
    def filtered_path_data(self):
        '''Filter the existing PATH data based on the current time'''
        self.time_now = datetime.now()
        df = self.raw_path_train_data
        df.columns.values[0] = "Start Time"
        # df.columns.values[-1] = "End Time"
        df['Category'] = 'PATH'
        depart_loc = df.columns.tolist()[0]

        cols = [c for c in df.columns if 'Depart' not in c]
        df=df[cols]
        return df[(df[depart_loc] > self.time_now)]


    @property
    def filtered_street_clean_data(self):
        self.time_now = datetime.now()
        df = self.raw_street_clean_data
        df['Category'] = 'PARK'
        df['Remarks'] = df['Start Street'].str.cat(df['End Street'],sep=" through ")
        df['Remarks'] = df['Remarks'].str.cat(df['End Date'],sep=" until ")
        df = df[(df['Start Date'] > self.time_now.weekday())]
        df = df.drop(['Start Street', 'End Street', 'Start Date'], axis=1)
        return df[(df['Start Time'] > self.time_now)]


    def convert_ampm_dt(self, row_times):
        '''Convert str(time) w/ AM/PM to datetime'''
        adj_values = []
        fix_format = '%I:%M%p'

        try:
            for time in row_times:
                value = datetime.strptime(time, fix_format)
                value = value.replace(
                                    year=self.time_now.year,
                                    month=self.time_now.month,
                                    day=self.time_now.day)
                adj_values.append(value)
            return adj_values

        except ValueError:
            fix_format = '%I %p'
            value = datetime.strptime(row_times, fix_format)
            value = value.replace(
                                year=self.time_now.year,
                                month=self.time_now.month,
                                day=self.time_now.day,
                                minute=0)
            return value


    def combine_dfs(self):
        '''Method to combine and sort PATH and cleaning data'''
        result = self.filtered_street_clean_data.append(self.filtered_path_data, sort='True')
        result = result.sort_values(by=['Start Time'])
        return result


    def write_config(self):
        '''Write existing filtered df to json config'''

        self.all_data = self.combine_dfs()
        dict_form = self.all_data.to_json(orient="values")

        dict_form = {'data': []}
        for row in self.all_data.itertuples(index=False):
            category = row.Category
            depart_time = '{}:{:02d}'.format(row[-1].hour, row[-1].minute)

            try:
                arrival_time = '{}:{:02d}'.format(row[4].hour, row[4].minute)
            except ValueError:
                try:
                    arrival_time = '{}:{:02d}'.format(row[7].hour, row[7].minute)
                except ValueError:
                    arrival_time = '{}:{:02d}'.format(row[0].hour, row[0].minute)

            remarks = ''
            destination = self.headers[-1].split(': ')[1]

            if category == 'PARK':
                destination = row[1]
                remarks = row.Remarks
            
            config_element = {
                                'Category': category,
                                'Destination': destination,
                                'Start Time': depart_time,
                                'End Time': arrival_time,
                                'Remarks': remarks
                            }

            dict_form['data'].append(config_element)

        file_name = os.path.join(PROJ_DIR_PATH, 'configs', 'schedule_data.json')
        with open(file_name, 'w+') as config:
            json.dump(dict_form, config, indent=4)


if __name__ == "__main__":
    all_locations = sys.argv[1]
    tm = DataManager(all_locations).write_config()

'''
Category: 'Street'
Destination: Base Street
Start Time: Start Hour
End Time: Ending Hour
Remarks: Start Street to End Street
'''