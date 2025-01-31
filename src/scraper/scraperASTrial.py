# -*- coding: utf-8 -*-
"""
Created on Fri Jan 24 16:02:25 2025

@author: antho
"""
import requests
import numpy as np
import pandas as pd
from thefuzz import process
import os
import time


def as_trials():
    """
    Call the clinicaltrials.gov api and get list of trials for AS.
    Parse out to get basic trial info and locations. Will be used to make a map
    of AS trials.
    """
    as_trial_url = "https://clinicaltrials.gov/api/v2/studies"
    as_trials_req = requests.get(
        as_trial_url,
        params={
            "query.cond": "Angelman Syndrome",
            "fields": "IdentificationModule,StatusModule,ContactsLocationsModule",
            "pageSize": 1000,
        },
    )
    as_trials_json = as_trials_req.json()

    as_trials_list = []
    as_trials_locs_list = []
    loc_type_list = ["facility", "city", "state", "zip", "country"]
    for study in as_trials_json["studies"]:
        # Make a df of
        trial_list = []
        nct_id = study["protocolSection"]["identificationModule"]["nctId"]
        trial_list.append(nct_id)
        trial_list.append(
            study["protocolSection"]["identificationModule"]["organization"]["fullName"]
        )
        try:
            trial_list.append(
                study["protocolSection"]["identificationModule"]["officialTitle"]
            )
        except KeyError:
            trial_list.append(
                study["protocolSection"]["identificationModule"]["briefTitle"]
            )
        trial_list.append(
            study["protocolSection"]["statusModule"]["studyFirstSubmitDate"]
        )
        try:
            trial_list.append(
                study["protocolSection"]["statusModule"]["completionDateStruct"]["date"]
            )
        except KeyError:
            trial_list.append("unknown")
        trial_list.append(study["protocolSection"]["statusModule"]["overallStatus"])
        as_trials_list.append(trial_list)

        # Make a separate df for trial locs since a give trial might have many locs
        try:
            for loc in study["protocolSection"]["contactsLocationsModule"]["locations"]:
                locs_list = []
                locs_list.append(nct_id)
                for loc_type in loc_type_list:
                    try:
                        locs_list.append(loc[loc_type])
                    except KeyError:
                        locs_list.append(np.nan)
                try:
                    locs_list.append(loc["geoPoint"]["lat"])
                except KeyError:
                    locs_list.append(np.nan)
                try:
                    locs_list.append(loc["geoPoint"]["lon"])
                except KeyError:
                    locs_list.append(np.nan)
                as_trials_locs_list.append(locs_list)
        except KeyError:
            locs_list = []
            try:
                for official in study["protocolSection"]["contactsLocationsModule"][
                    "overallOfficials"
                ]:
                    locs_list.append(official["affiliation"])
                    [locs_list.append(np.nan) for _ in range(6)]
            except KeyError:
                continue

    # output dataframes for use in visualization
    as_trials_df = pd.DataFrame(
        as_trials_list,
        columns=[
            "NCT_ID",
            "Sponsor",
            "Study_Name",
            "Start_Date",
            "End_Date",
            "Current_Status",
        ],
    )
    # as_trials_df.to_csv(f"{wkdir}/data/as_trials_df.csv", index=False)

    as_trials_locs_df = pd.DataFrame(
        as_trials_locs_list,
        columns=["NCT_ID", "Facility", "City", "State", "Zip", "Country", "Lat", "Lon"],
    )
    # as_trials_locs_df.to_csv(f"{wkdir}/data/as_trials_locs_df.csv", index=False)

    loc_type_list = ["City", "State", "Zip", "Country"]
    as_trials_locs_dedup = as_trials_locs_df.loc[
        :, ["NCT_ID", "Facility", "Lat", "Lon"]
    ]
    for loc_type in loc_type_list:
        loc_dedup_df = (
            as_trials_locs_df.loc[:, ["Facility", "Lat", "Lon", loc_type]]
            .sort_values(by=["Facility", "Lat", "Lon", loc_type])
            .drop_duplicates(subset=["Facility", "Lat", "Lon"], keep="first")
        )
        as_trials_locs_dedup = as_trials_locs_dedup.merge(
            loc_dedup_df, how="left", on=["Facility", "Lat", "Lon"]
        )
    as_trials_locs_df1 = as_trials_df.merge(
        as_trials_locs_dedup, how="left", on="NCT_ID"
    )

    as_trials_locs_df1["Hover_City"] = as_trials_locs_df1[
        ["City", "State", "Country"]
    ].apply(lambda x: x.str.cat(sep=", "), axis=1)

    lat_lon_df = as_trials_locs_df1[["Lat", "Lon"]].drop_duplicates()

    # as_trials_locs_df1.to_csv(f"{wkdir}/data/as_trials_locs_df1.csv", index=False)
    all_cities = pd.DataFrame()
    for city in lat_lon_df.itertuples():
        current_city = as_trials_locs_df1.loc[
            (as_trials_locs_df1["Lat"] == city[1])
            & (as_trials_locs_df1["Lon"] == city[2])
        ]
        
        #BE CAREFUL, I DON T FIND A METHOD DEDUPE WITH THIS ARG
        #facilities_dedup = process.dedupe(current_city["Facility"], threshold=70, len_selector="shortest")
        facilities_dedup = process.dedupe(current_city["Facility"], threshold=70)
        current_city["Facility_dedupe"] = current_city["Facility"].apply(
            lambda x: process.extractOne(x, facilities_dedup)[0]
        )
        cities_dedupe = process.dedupe(current_city["Hover_City"], threshold=70)
        current_city["Dedupe_City"] = current_city["Hover_City"].apply(
            lambda x: process.extractOne(x, cities_dedupe)[0]
        )
        all_cities = pd.concat([all_cities, current_city], axis=0)
    all_cities.drop_duplicates(
        subset=["NCT_ID", "Facility", "Dedupe_City"]
    ).sort_values(by=["NCT_ID", "Dedupe_City", "Facility_dedupe"])

    # all_cities.to_csv(f"{wkdir}/data/all_cities.csv", index=False)

    final_as_trials_locs = (
        all_cities.groupby(["Facility_dedupe", "Dedupe_City", "Lat", "Lon"])
        .agg({"NCT_ID": pd.Series.nunique})
        .reset_index()
        .rename(columns={"NCT_ID": "Trial_Count"})
        .drop_duplicates()
        .sort_values(by=["Dedupe_City", "Facility_dedupe"])
        .rename(columns={"Facility_dedupe": "Institution", "Dedupe_City": "City"})
    )

    # final_as_trials_locs.to_csv(f"{wkdir}/data/final_as_trials_locs.csv", index=False)
    
    return all_cities

if __name__ == "__main__":
    start = time.time()
    # Get working directory
    wkdir = os.path.dirname(__file__)
    all_cities = as_trials()
    all_cities.to_csv(f"{wkdir}/../../data/all_cities.csv", index=False)
    print("Execute time : ", round(time.time()-start, 2), "s")