# -*- coding: utf-8 -*-
"""
Created on Thu Jan 23 18:07:39 2025

@author: antho
"""

import os
import json
import pandas as pd
import requests
import time
import numpy as np
from thefuzz import fuzz, process


def __filter_and_replace_fuzzy_match(df, column_name, match_strings, threshold=70):
    """
    Filters rows of the dataframe based on fuzzy matching with a list of strings
    and replaces the original value with the best matching string.

    Parameters:
    - df: pandas DataFrame
    - column_name: str, name of the column to perform fuzzy matching on
    - match_strings: list of str, strings to match against
    - threshold: int, fuzzy match threshold (0-100)

    Returns:
    - Filtered DataFrame with replaced values
    """

    def best_match(value):
        # Handle missing values
        if pd.isna(value):
            return None

        value_str = str(value)
        best_score = 0
        best_match_str = None

        for match_str in match_strings:
            score = fuzz.ratio(value_str, match_str)
            if score > best_score:
                best_score = score
                best_match_str = match_str

        return best_match_str if best_score >= threshold else None

    # Apply the best match function to the DataFrame column
    df[column_name] = df[column_name].apply(lambda x: best_match(x))

    # Filter the DataFrame based on non-null values in the column
    filtered_df = df[df[column_name].notna()]

    return filtered_df


def __parse_trials(trials_json, loc_limiter=False, clinic=None):
    """
    Parse json data returned from api request to clinicaltrials.gov
    We need to parse data for both AS trials overall and trial at AS clinics
    This lets us combine it to a single function rather than repeat the code.
    """

    trials_list = []
    trials_locs_list = []
    loc_type_list = ["facility", "city", "state", "zip", "country"]
    for study in trials_json["studies"]:
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
        trials_list.append(trial_list)

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
                trials_locs_list.append(locs_list)
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
    trials_df = pd.DataFrame(
        trials_list,
        columns=[
            "NCT_ID",
            "Sponsor",
            "Study_Name",
            "Start_Date",
            "End_Date",
            "Current_Status",
        ],
    )

    trials_locs_df = pd.DataFrame(
        trials_locs_list,
        columns=["NCT_ID", "Facility", "City", "State", "Zip", "Country", "Lat", "Lon"],
    )

    return (trials_df, trials_locs_df)


def trials_ASExpertClinics(clinics_json_df, clinics_json):
    """
    Pull list of trials that occured at clinics sponsored by different patient groups.
    This will be fed into a map so it can be overlaid with the clinics. 

    For the past few years, ASF has recruiting clinics that were specifically identified by
    industry as being good partners for clinical trials. The ASExpertClinics
    builds on this idea by expanding it globally and putting it in the form of a dashboard. 

    1. Identify all clinics globally sponsored by AS patient groups
    2. For each clinic, pull all trials that have occured there on specific treatments
       These are not just AS trials, but all trials that may be similar in some way to 
       potential future AS trials.
        a. ASO trials (current generation gene targeting therapies)
        b. Gene therapy trials (future generation gene targeting therapies)
        c. We can add more trial types in the future if and when good ones are identified
    """
    clinics_json_df = clinics_json_df.explode("Hospitals").rename(
        columns={"Hospitals": "Facility"}
    )

    trial_url = "https://clinicaltrials.gov/api/v2/studies"

    all_clinics = []
    asexpert_clinics_all_trials_merge_df = pd.DataFrame()
    for _, clinic in clinics_json.items():
        all_clinics = [*all_clinics, *clinic["Hospitals"]]
    interventions = {
        "ASO": ["antisense oligonucleotide", "ASO"],
        "gene_therapy": ["gene therapy"],
    }

    for i, intervention in enumerate(interventions.keys()):
        for key, clinic in clinics_json.items():
            clinic_geocode = f'distance({clinic["Lat"]},{clinic["Lon"]},5mi)'
            next_page_token = None
            treatment = (
                'EXPANSION[Concept]"'
                + '" OR EXPANSION[Concept]"'.join(interventions[intervention])
                + '"'
            )
            query_params = {
                "filter.geo": clinic_geocode,
                "query.intr": treatment,
                "fields": "IdentificationModule,StatusModule,ContactsLocationsModule",
                "pageSize": 1000,
            }

            asexpert_trials_req = requests.get(
                trial_url,
                params=query_params,
            )
            time.sleep(1)

            asexpert_trials_json = asexpert_trials_req.json()

            # Get next page token from json response if it exists
            try:
                next_page_token = asexpert_trials_json["nextPageToken"]
                print(f"Next page token: {next_page_token}")
            except KeyError:
                next_page_token = None

            trial_df_tuple = __parse_trials(asexpert_trials_json)

            asexpert_trials_df = trial_df_tuple[0]
            asexpert_trials_df["Treatment"] = intervention
            try:
                asexpert_trials_locs_df = trial_df_tuple[1]
                asexpert_trials_locs_df = asexpert_trials_locs_df.loc[
                    (asexpert_trials_locs_df["Lat"] == clinic["Lat"])
                    & (asexpert_trials_locs_df["Lon"] == clinic["Lon"])
                ]
                asexpert_trials_locs_df = __filter_and_replace_fuzzy_match(
                    asexpert_trials_locs_df, "Facility", clinic["Hospitals"], threshold=70
                )
                asexpert_trials_locs_df.loc[:, ["Hover_City"]] = clinic["City"]
            except:
                print("AS Expert Clinics Trials Locs clinic filter failed")
                asexpert_trials_locs_df = trial_df_tuple[1]

            asexpert_trials_merge = asexpert_trials_df.merge(
                asexpert_trials_locs_df, how="inner", on="NCT_ID"
            )
            asexpert_all_trials_merge_df = pd.concat(
                [asexpert_all_trials_merge_df, asexpert_trials_merge], axis=0
            )

            while next_page_token:
                print(f"Entered subloop for {next_page_token}")
                asexpert_trials_req = requests.get(
                    trial_url,
                    params={
                        "filter.geo": clinic_geocode,
                        "query.intr": treatment,
                        "fields": "IdentificationModule,StatusModule,ContactsLocationsModule",
                        "pageSize": 1000,
                        "pageToken": next_page_token,
                    },
                )
                time.sleep(1)
                asexpert_trials_json = asexpert_trials_req.json()

                # Get next page token from json response if it exists
                try:
                    next_page_token = asexpert_trials_json["nextPageToken"]
                except KeyError:
                    next_page_token = None

                trial_df_tuple = __parse_trials(asexpert_trials_json)
                asexpert_trials_df = trial_df_tuple[0]
                asexpert_trials_df["Treatment"] = intervention
                try:
                    asexpert_trials_locs_df = trial_df_tuple[1]
                    asexpert_trials_locs_df = asexpert_trials_locs_df.loc[
                        (asexpert_trials_locs_df["Lat"] == clinic["Lat"])
                        & (asexpert_trials_locs_df["Lon"] == clinic["Lon"])
                    ]
                    asexpert_trials_locs_df = __filter_and_replace_fuzzy_match(
                        asexpert_trials_locs_df,
                        "Facility",
                        clinic["Hospitals"],
                        threshold=70,
                    )
                    asexpert_trials_locs_df.loc[:, ["Hover_City"]] = clinic["City"]
                except:
                    print("AS Expert Clinics Trials Locs clinic filter failed")
                    asexpert_trials_locs_df = trial_df_tuple[1]

                asexpert_trials_merge = asexpert_trials_df.merge(
                    asexpert_trials_locs_df, how="inner", on="NCT_ID"
                )
                asexpert_all_trials_merge_df = pd.concat(
                    [asexpert_all_trials_merge_df, asexpert_trials_merge], axis=0
                )
    asexpert_all_trials_merge_df.drop(
        columns=["Hover_City", "City", "State", "Zip", "Country"], inplace=True
    )

    # pivot_asexpert_trials_locs = pd.pivot_table(
    #   asexpert_all_trials_merge_df,
    #    values="NCT_ID",
    #    aggfunc=pd.Series.nunique,
    #    index=["Facility", "Lat", "Lon"],
    #    columns=["Treatment"],
    #    fill_value=0,
    # )
    # pivot_asexpert_trials_locs.reset_index(inplace=True)
    # final_asexpert_trials_locs = (
    #    clinics_json_df.merge(
    #        pivot_asexpert_trials_locs, how="left", on=["Lat", "Lon", "Facility"]
    #    )
    #    .drop_duplicates()
    #    .fillna(value=0)
    #    .astype({"ASO": "int", "gene_therapy": "int"})
    #    .rename(columns={"Facility": "Institution"})
    # )
    return asexpert_all_trials_merge_df


if __name__ == "__main__":
    start = time.time()
    wkdir = os.path.dirname(__file__)
    with open(f"{wkdir}/../../data/AS_expert_clinics.json") as f:
        clinics_json = json.load(f)
    clinics_json_df = pd.read_json(f"{wkdir}/../../data/AS_expert_clinics.json", orient="index")
    ASExpertClinics_df = trials_ASExpertClinics(clinics_json_df, clinics_json)
    ASExpertClinics_df.to_csv(f"{wkdir}/../../data/ASExpertClinics_data.csv", index=False)
    print("Execute time : ", round(time.time()-start, 2), "s")