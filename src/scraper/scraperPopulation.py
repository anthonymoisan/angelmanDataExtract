# -*- coding: utf-8 -*-
"""
Created on Thu Jan 23 16:43:46 2025

@author: antho
"""
import pandas as pd
import requests
import time
from datetime import datetime
import numpy as np
from configparser import ConfigParser
import sys
import os
from tools.logger import setup_logger

# Set up logger
logger = setup_logger( debug=False)


def get_un_locations(locations_url):
    """
    Call UN WPP API to get list of locations.
    Convert to dataframe, filter to countries,
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
                logger.error(f"Population call failed attempt {i}")
                time.sleep(2)
                response = requests.get(url, headers=headers, params=params)
                i += 1

        response_json = response.json()

        # Convert json response to dataframe
        temp_data_df = pd.DataFrame.from_dict(response_json["data"])

        # Keep all ages, 0-17, and 18+ age groups
        temp_filter_pop_df = temp_data_df.loc[
            :,
            [
                "locationId",
                "location",
                "iso3",
                "timeLabel",
                "sex",
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


def un_population(auth_token):
    """
    Pull national level UN population estimates to feed a map in the patient population
    section of the dashboard. Collect most recent data, then divide by 15000 to meet the
    1/15000 people born with AS.
    """

    base_path = "https://population.un.org/dataportalapi/api/v1"

    # Get locations
    countries_df = get_un_locations(f"{base_path}/locations")
    time.sleep(2)

    # Set values for calling data api
    indicators = "47"
    start_year = datetime.now().year - 2
    end_year = datetime.now().year - 2

    # Separate out countries into groups of 100 and call data api for all countries
    pop_dfs = []
    for i in range(0, len(countries_df), 100):
        locations = ",".join(countries_df.loc[countries_df.index[i:i+100], "id"])
        logger.info(f"--- Pop {i+100} ---")
        pop_df = get_country_pops(auth_token, indicators, start_year, end_year, locations)
        pop_dfs.append(pop_df)
        time.sleep(2)

    # concatenate dataframes to make one for all countries
    pop_df = pd.concat(pop_dfs, axis=0, ignore_index=True)

    # 1/15000 people are angels, so divide to get estimate
    pop_df.loc[:, "angelPopEstimate"] = pop_df["value"] / 15000
    pop_df["value"] = pop_df["value"].round().astype(int)
    pop_df["angelPopEstimate"] = pop_df["angelPopEstimate"].round().astype(int)

    # Rename columns for clarity
    pop_df.rename(
        columns={"location": "countryName", "iso3": "countryIso3_code",
                 "timeLabel": "dataYear", "ageLabel": "Age",
                 "value": "totalPopEstimate"}
    )

    return pop_df


if __name__ == "__main__":
    start = time.time()
    # Get working directory
    wkdir = os.path.dirname(__file__)
    config = ConfigParser()
    filePath = f"{wkdir}/../../angelman_viz_keys/Config3.ini"
    if config.read(filePath):
        auth_token = config['UnPopulation']['bearerToken']
        un_pop_final_df = un_population(auth_token)
        un_pop_final_df.to_csv(f"{wkdir}/../../data/un_wpp_pivot_data.csv", index=False)
    else:
        logger.error("Error Config3.ini File with auth_token")
    logger.info("\nExecute time : %.2fs", time.time() - start)