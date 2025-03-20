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

def __requestJSON2(clinic_geocode, queryCondition):
    query_params = {
        "filter.geo": clinic_geocode,
        "query.intr" : queryCondition,
        "fields": "IdentificationModule,StatusModule,ContactsLocationsModule",
        "countTotal" : "true",
        "pageSize": 1000,
    }
        
    as_trial_url = "https://clinicaltrials.gov/api/v2/studies"
    
    as_trials_req = requests.get(
        as_trial_url,
        params=query_params,
    )
    return as_trials_req.json()

def __getNctId(study):
    return study["protocolSection"]["identificationModule"]["nctId"]

def __getOrganization(study):
    return study["protocolSection"]["identificationModule"]["organization"]["fullName"]

def __getTitle(study):
    try:
        return study["protocolSection"]["identificationModule"]["officialTitle"]
    except KeyError:
        return study["protocolSection"]["identificationModule"]["briefTitle"]

def __getFirstSumbitDate(study):
    return study["protocolSection"]["statusModule"]["studyFirstSubmitDate"]

def __getCompletionDate(study):
    try:
        return study["protocolSection"]["statusModule"]["completionDateStruct"]["date"]
    except KeyError:
        return "unknown"

def __getOverallStatus(study):
    return study["protocolSection"]["statusModule"]["overallStatus"]

def __getGeoPointLat(loc):
    try:
        return loc["geoPoint"]["lat"]
    except KeyError:
        return np.nan

def __getGeoPointLon(loc):
    try:
        return loc["geoPoint"]["lon"]
    except KeyError:
        return(np.nan)

def __buildTrialList(study, TypeTherapy):
    trial_list = []
    nct_id = __getNctId(study)
    trial_list.append(nct_id)
    trial_list.append( __getOrganization(study))
    trial_list.append(__getTitle(study))
    trial_list.append(__getFirstSumbitDate(study))
    trial_list.append(__getCompletionDate(study))
    trial_list.append(__getOverallStatus(study))
    trial_list.append(TypeTherapy)
    return trial_list     

def __BuildDataFrame(data, listColumns):
    return pd.DataFrame(
        data,
        columns=listColumns,
    ) if data != None else None

def __getFacility(loc):
    try:
        return loc["facility"]
    except KeyError:
        return np.nan

def __buildLocsList(nct_id,loc):
    locs_list = []
    locs_list.append(__getFacility(loc))
    return locs_list

def __filter_and_replace_fuzzy_match(clinicListNames, locationName, threshold=70):
    """
    Given a locationName, try to find in the clinicListNames a fuzzy matching

    Parameters:
    - clinicListNames : list of clinic Names
    - locationName : str, name of the column to perform fuzzy matching on
    - threshold: int, fuzzy match threshold (0-100)

    Returns:
    - best_match_str or None if we don't match
    """

    best_score = 0
    best_match_str = None

    for match_str in clinicListNames:
        score = fuzz.ratio(locationName, match_str)
        if score > best_score:
            best_score = score
            best_match_str = match_str

    return best_match_str if best_score >= threshold else None


def __buid_ClinicalsTrials(clinic, queryCondition, TypeTherapy):
    #For ASO or GeneTherapy (queryCondition), find clinical trials
    try:
        clinic_geocode = f'distance({clinic["Lat_scrape"]},{clinic["Lon_scrape"]},1mi)'
        as_trials_req = __requestJSON2(clinic_geocode, queryCondition)

        as_trials_list = []
        
        for study in as_trials_req["studies"]:
            nct_id = __getNctId(study)
            #print(nct_id)
            for loc in study["protocolSection"]["contactsLocationsModule"]["locations"]:
                latitude = __getGeoPointLat(loc)
                longitude = __getGeoPointLon(loc)
                #Equality of 2 decimal with an error of 1e-6
                testValLatEquality = (abs(latitude-clinic["Lat"])<1e-6)
                testValLonEquality = (abs(longitude-clinic["Lon"])<1e-6)
                if(testValLatEquality and testValLonEquality):
                    facility = __getFacility(loc)
                    best_match = __filter_and_replace_fuzzy_match(clinic["Hospitals"],facility)
                    if best_match != None :
                        trial_list = __buildTrialList(study, TypeTherapy)
                        trial_list.append(clinic.name)
                        trial_list.append(latitude)
                        trial_list.append(longitude)
                        as_trials_list.append(trial_list)               
        return as_trials_list
    except :
        #NOT NORMAL BECAUSE IT WORKS WITH THE PARAMETERS OF THE REQUEST
        print("ISSUE : " + TypeTherapy)
        print(clinic)
        print()
        return None

def __concatDataFrame(df1, df2, clinic):
    if not df1.empty and not df2.empty :
        return pd.concat([df1, df2], axis = 0)
    if df1.empty and df2.empty:
        print("Clinic without trials")
        print(clinic)
        # return clinic alone without clinic trials
        #return pd.DataFrame()
        return pd.DataFrame({"NCT_ID":[None], "Sponsor":[None], "Study_Name":[None],"Start_Date":[None], "End_Date":[None], "Current_Status":[None], "Treatment":[None], "Facility":[clinic.name], "Lat_scrape":[clinic["Lat_scrape"]], "Lon_scrape":[clinic["Lon_scrape"]], "Lat_map":[clinic["Lat_map"]], "Lon_map":[clinic["Lon_map"]]})
    if df1.empty and not df2.empty:
        return df2
    if not df1.empty and df2.empty:
        return df1
    

def trials_clinics_LonLat(clinics_json_df):
    """
    Parse clinics_json_df dataframe in order to find some clinical trials (ASO or Gene Therapy) 
    """
    df_result = pd.DataFrame()
    for index, clinic in clinics_json_df.iterrows() :
        
        #print(clinic)
        as_trials_list_ASO = __buid_ClinicalsTrials(clinic, 
                                                    'EXPANSION[Concept]"ASO" OR EXPANSION[Concept]"antisense oligonucleotide"', 
                                                    "ASO")
        
        df_trialsASO = __BuildDataFrame(as_trials_list_ASO,
                                        listColumns=["NCT_ID","Sponsor","Study_Name","Start_Date","End_Date", "Current_Status", "Treatment", "Facility", "Lat_scrape", "Lon_scrape", "Lat_map", "Lon_map"])
        
        #print(df_trialsASO)
        
        as_trials_list_GeneTherapy = __buid_ClinicalsTrials(clinic, 
                                                            'EXPANSION[Concept]"gene therapy"', 
                                                            "gene_therapy")
        
        df_trialsGeneTherapy =  __BuildDataFrame(as_trials_list_GeneTherapy,
                                                 listColumns=["NCT_ID","Sponsor","Study_Name","Start_Date","End_Date", "Current_Status", "Treatment", "Facility", "Lat_scrape", "Lon_scrape", "Lat_map", "Lon_map"])
        
        #print(df_trialsGeneTherapy)
        
        df_trials_list_clinic = __concatDataFrame(df_trialsASO, df_trialsGeneTherapy, clinic)
        df_result = __concatDataFrame(df_trials_list_clinic, df_result, clinic)
    return df_result


if __name__ == "__main__":
    start = time.time()
    wkdir = os.path.dirname(__file__)
    clinics_json_df = pd.read_json(f"{wkdir}/../../data/AS_clinics.json", orient="index")
    clinics_trials_df = trials_clinics_LonLat(clinics_json_df)
    clinics_trials_df.to_csv(f"{wkdir}/../../data/clinics_trials.csv", index=False)
    print("Execute time : ", round(time.time()-start, 2), "s")