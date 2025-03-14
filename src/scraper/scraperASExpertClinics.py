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
from thefuzz import fuzz


def __filter_and_replace_fuzzy_match(df, column_name, match_strings, threshold=70):
    def best_match(value):
        if pd.isna(value):
            return None
        best_match_str = max(match_strings, key=lambda x: fuzz.ratio(str(value), x), default=None)
        return best_match_str if fuzz.ratio(str(value), best_match_str) >= threshold else None

    df[column_name] = df[column_name].apply(best_match)
    return df[df[column_name].notna()]


def __parse_trials(trials_json):
    trials_list = []
    trials_locs_list = []
    loc_type_list = ["facility", "city", "state", "zip", "country"]
    for study in trials_json["studies"]:
        nct_id = study["protocolSection"]["identificationModule"]["nctId"]
        trial_list = [
            nct_id,
            study["protocolSection"]["identificationModule"]["organization"]["fullName"],
            study["protocolSection"]["identificationModule"].get("officialTitle", study["protocolSection"]["identificationModule"]["briefTitle"]),
            study["protocolSection"]["statusModule"]["studyFirstSubmitDate"],
            study["protocolSection"]["statusModule"].get("completionDateStruct", {}).get("date", "unknown"),
            study["protocolSection"]["statusModule"]["overallStatus"]
        ]
        trials_list.append(trial_list)

        for loc in study["protocolSection"]["contactsLocationsModule"].get("locations", []):
            locs_list = [nct_id] + [loc.get(loc_type, np.nan) for loc_type in loc_type_list] + [loc.get("geoPoint", {}).get("lat", np.nan), loc.get("geoPoint", {}).get("lon", np.nan)]
            trials_locs_list.append(locs_list)

    trials_df = pd.DataFrame(trials_list, columns=["NCT_ID", "Sponsor", "Study_Name", "Start_Date", "End_Date", "Current_Status"])
    trials_locs_df = pd.DataFrame(trials_locs_list, columns=["NCT_ID", "Facility", "City", "State", "Zip", "Country", "Lat", "Lon"])
    return trials_df, trials_locs_df


def trials_ASExpertClinics(clinics_json_df, clinics_json):
    clinics_json_df = clinics_json_df.explode("Hospitals").rename(columns={"Hospitals": "Facility"})
    trial_url = "https://clinicaltrials.gov/api/v2/studies"
    interventions = {"ASO": ["antisense oligonucleotide", "ASO"], "gene_therapy": ["gene therapy"]}
    all_clinics = [hospital for clinic in clinics_json.values() for hospital in clinic["Hospitals"]]
    asexpert_all_trials_merge_df = pd.DataFrame()

    for intervention, terms in interventions.items():
        treatment = 'EXPANSION[Concept]"' + '" OR EXPANSION[Concept]"'.join(terms) + '"'
        for clinic in clinics_json.values():
            clinic_geocode = f'distance({clinic["Lat_scrape"]},{clinic["Lon_scrape"]},5mi)'
            query_params = {"filter.geo": clinic_geocode, "query.intr": treatment, "fields": "IdentificationModule,StatusModule,ContactsLocationsModule", "pageSize": 1000}
            next_page_token = None

            while True:
                response = requests.get(trial_url, params={**query_params, "pageToken": next_page_token})
                trials_json = response.json()
                trial_df, trial_locs_df = __parse_trials(trials_json)
                trial_df["Treatment"] = intervention

                trial_locs_df = trial_locs_df.loc[(trial_locs_df["Lat"] == clinic["Lat"]) & (trial_locs_df["Lon"] == clinic["Lon"])]
                trial_locs_df = __filter_and_replace_fuzzy_match(trial_locs_df, "Facility", clinic["Hospitals"])
                trial_locs_df["Hover_City"] = clinic["City"]

                merged_df = trial_df.merge(trial_locs_df, how="inner", on="NCT_ID")
                asexpert_all_trials_merge_df = pd.concat([asexpert_all_trials_merge_df, merged_df], axis=0)

                next_page_token = trials_json.get("nextPageToken")
                if not next_page_token:
                    break
                time.sleep(1)

    asexpert_all_trials_merge_df.drop(columns=["Hover_City", "City", "State", "Zip", "Country"], inplace=True)
    return asexpert_all_trials_merge_df


if __name__ == "__main__":
    start = time.time()
    wkdir = os.path.dirname(__file__)
    with open(f"{wkdir}/../../data/AS_expert_clinics.json") as f:
        clinics_json = json.load(f)
    clinics_json_df = pd.read_json(f"{wkdir}/../../data/AS_expert_clinics.json", orient="index")
    ASExpertClinics_df = trials_ASExpertClinics(clinics_json_df, clinics_json)
    ASExpertClinics_df.to_csv(f"{wkdir}/../../data/ASExpertClinics_data.csv", index=False)
    print("Execute time : ", round(time.time() - start, 2), "s")