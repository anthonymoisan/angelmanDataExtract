# -*- coding: utf-8 -*-
"""
Created on Thu Jan 23 16:43:46 2025

@author: antho
"""
import pandas as pd
import requests
import time
from datetime import datetime
import os
import numpy as np

def get_un_locations(locations_url):
    """
    Call UN WPP API to get list of locations. Convert to dataframe, filter to countries,
    then return.
    """

    locs_df = pd.DataFrame()
    page_num = 1
    while True:
        locs_response = requests.get(
            locations_url,
            params={"sort": "id", "pageNumber": page_num, "pageSize": 100},
        )
        locs_json = locs_response.json()
        next_page = locs_json["nextPage"]
        temp_df = pd.DataFrame.from_dict(locs_json["data"])
        locs_df = pd.concat([locs_df, temp_df], axis=0, ignore_index=True)
        if next_page is None:
            break
        else:
            page_num += 1

    # In their API response, countries have latitude and longitude. Other groupings do not
    countries_df = locs_df.loc[locs_df["longitude"].notnull(), :]
    countries_df = countries_df.loc[:, ["id", "name", "iso2", "iso3"]].astype(str)
    return countries_df


def get_country_pops(auth_token, indicators, start_year, end_year, countries_list):
    """
    Gets population by age breakdown for a given list of countries
    """
    # Create initial blank dataframe to fill in by concatenation
    pop_df = pd.DataFrame()

    # These two things remain constant for the duration of the function call
    url = f"https://population.un.org/dataportalapi/api/v1/data/indicators/{indicators}/locations/{countries_list}"
    headers = {"Authorization": auth_token}

    # Start at page 1, then update while looping
    page_num = 1

    # Loop through all pages of population values for the countries in the list
    while True:
        # Build the api call and get json response
        params = {
            "pagingInHeader": "false",
            "format": "json",
            "pageSize": "100",
            "pageNumber": page_num,
            "startYear": start_year,
            "endYear": end_year,
            "sexes": "3",
        }

        i = 0
        while i in range(4):  # try max of 4 times if call fails
            try:
                response = requests.get(url, headers=headers, params=params)
                break
            except:
                print(f"Population call failed attempt {i}")
                time.sleep(2)
                response = requests.get(url, headers=headers, params=params)
                i += 1

        # print(response.json())
        response_json = response.json()

        # Convert json response to dataframe
        temp_data_df = pd.DataFrame.from_dict(response_json["data"])

        # Keep all ages, 0-17, and 18+ age groups
        temp_filter_pop_df = temp_data_df.loc[
            (temp_data_df["ageId"].isin([188, 7, 3, 25, 8])),
            [
                "locationId",
                "location",
                "iso3",
                "timeLabel",
                "sex",
                "ageId",
                "ageLabel",
                "value",
            ],
        ]

        # Concatenate to master dataframe and check for next page
        pop_df = pd.concat([pop_df, temp_filter_pop_df], axis=0, ignore_index=True)
        next_page = response_json["nextPage"]

        # exit the loop when there are no more next pages and return the dataframe
        if next_page is None:
            break
        else:
            time.sleep(2)
            page_num += 1

    return pop_df


def un_population():
    """
    Pull national level UN population estimates to feed a map in the patient population
    section of the dashboard. Collect most recent data, then divide by 15000 to meet the
    1/15000 people born with AS.
    """

    base_path = "https://population.un.org/dataportalapi/api/v1"

    # Get locations
    countries_df = get_un_locations(f"{base_path}/locations")
    time.sleep(2)

    # Read in api bearer token
    with open(f"{key_dir}/un_population_bearer_token.txt") as api_txt:
        auth_token = api_txt.read()

    # Set values for calling data api
    indicators = "70"
    start_year = datetime.now().year - 2
    end_year = datetime.now().year - 2

    # Separate out countries into groups of 100
    locations_1 = ",".join(countries_df.loc[countries_df.index[0:100], "id"])
    locations_2 = ",".join(countries_df.loc[countries_df.index[100:200], "id"])
    locations_3 = ",".join(countries_df.loc[countries_df.index[200:300], "id"])

    # Call data api for all countries and concatenate all results
    pop_df_1 = get_country_pops(
        auth_token, indicators, start_year, end_year, locations_1
    )
    time.sleep(2)
    pop_df_2 = get_country_pops(
        auth_token, indicators, start_year, end_year, locations_2
    )
    time.sleep(2)
    pop_df_3 = get_country_pops(
        auth_token, indicators, start_year, end_year, locations_3
    )

    pop_df = pd.concat([pop_df_1, pop_df_2, pop_df_3], axis=0, ignore_index=True)

    # 1/15000 people are angels, so divide to get estimate
    pop_df.loc[:, "wpp_angel_estimate"] = pop_df["value"] / 15000
    pop_df["value"] = pop_df["value"].round().astype(int)
    pop_df["wpp_angel_estimate"] = pop_df["wpp_angel_estimate"].round().astype(int)

    pop_total_df = (
        pop_df.loc[
            pop_df["ageLabel"] == "Total", pop_df.columns != "wpp_angel_estimate"
        ]
        .drop_duplicates()
        .drop(columns="ageLabel")
    )
    pop_angel_df = pop_df.loc[:, ["iso3", "ageLabel", "wpp_angel_estimate"]]
    pop_angel_wide_df = pop_angel_df.pivot_table(
        values="wpp_angel_estimate", columns="ageLabel", index="iso3"
    ).reset_index()

    un_pop_final_df = pop_total_df.merge(
        pop_angel_wide_df, how="left", on="iso3"
    ).rename(
        columns={
            "value": "total_population",
            "0-4": "angels_0-4",
            "5-10": "angels_5-10",
            "11-17": "angels_11-17",
            "18+": "angels_18+",
            "Total": "angels_Total",
        }
    )

    un_pop_final_df.loc[:, 'angels_color'] = np.log(un_pop_final_df['angels_Total'])
    return un_pop_final_df
    
if __name__ == "__main__":
    # PULL PUBMED DATA
    # Get working directory
    wkdir = os.path.dirname(__file__)
    key_dir = os.path.normpath(os.path.join(wkdir, "../angelman_viz_keys"))
    
    un_pop_final_df = un_population()
    un_pop_final_df.to_csv(f"{wkdir}/../data/un_wpp_pivot_data.csv", index=False)
