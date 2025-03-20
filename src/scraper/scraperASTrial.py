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
import json
import re

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

def __getMinimumAge(study):
    try:
        return study["protocolSection"]["eligibilityModule"]["minimumAge"]
    except KeyError:
        return "unknown"

def __getMaximumAge(study):
    try:
        return study["protocolSection"]["eligibilityModule"]["maximumAge"]
    except KeyError:
        return "unknown"

def __getSex(study):
    try:
        return study["protocolSection"]["eligibilityModule"]["sex"]
    except KeyError:
        return "unknown"


def __is_word_in_text(word, text):
    """
    Check if a word is in a text.

    Parameters
    ----------
    word : str
    text : str

    Returns
    -------
    bool : True if word is in text, otherwise False.

    Examples
    --------
    >>> is_word_in_text("Python", "python is awesome.")
    True

    >>> is_word_in_text("Python", "camelCase is pythonic.")
    False

    >>> is_word_in_text("Python", "At the end is Python")
    True
    """
    pattern = r'(^|[^\w]){}([^\w]|$)'.format(word)
    pattern = re.compile(pattern, re.IGNORECASE)
    matches = re.search(pattern, text)
    return bool(matches)

### Only Eligibility Inclusion Criteria in the eligibility free text
###
def __splitEligibility(textEligibility):
    posInclusionCriteria = textEligibility.find("inclusion criteria:")
    posExclusionCriteria = textEligibility.find("exclusion criteria:")
    textExclusionCriteria = textEligibility[posInclusionCriteria:(posExclusionCriteria-1)]
    return(textExclusionCriteria)


def __getGenotype(textEligibilityCriteria, studyType):
    if(studyType == "OBSERVATIONAL"):
        # return All genotype
        isDeletion = True
        isMutation = True
        isUPD = True
        isID = True
    else :    
        #Interventional clinical trials
        textEligibilityLower = textEligibilityCriteria.lower()
        #print(textEligibilityLower)
        textInclusionCriteria = __splitEligibility(textEligibilityLower)
        #print(textInclusionCriteria)
        isDeletion = __is_word_in_text('deletion', textInclusionCriteria)
        isMutation = __is_word_in_text('mutation', textInclusionCriteria)
        isUPD = (__is_word_in_text('upd', textInclusionCriteria) or __is_word_in_text('disomie', textInclusionCriteria))
        isID = (__is_word_in_text('icd', textInclusionCriteria) or __is_word_in_text('imprinting defect', textInclusionCriteria))
        
        if(( not isDeletion) and (not isMutation) and (not isUPD) and (not isID)):
            # reset at all genotype for instance with the following keyword : confirmed molecular diagnosis of as
            isDeletion = isMutation = isID = isUPD = True
    return (isDeletion, isMutation, isUPD, isID)

def __getEligibilityCriteria(study):
    try:
        return study["protocolSection"]["eligibilityModule"]["eligibilityCriteria"]
    except KeyError:
        return "unknown"

def __getBriefSummary(study):
    try:
        return study["protocolSection"]["descriptionModule"]["briefSummary"]
    except KeyError:
        return "unknown"

def __getStudyType(study):
    try:
        return study["protocolSection"]["designModule"]["studyType"]
    except KeyError:
        return "unknown"

def __getPhases(study):
    try:
        enumPhases = study["protocolSection"]["designModule"]["phases"]
        enumPhasesStr = ','.join(enumPhases)
        #enumPhasesStr = str.replace(','.join(enumPhases),'[','')
        #enumPhasesStr = str.replace(enumPhasesStr,']','')
        return enumPhasesStr
    except KeyError:
        return "unknown"

def __getEnrollmentInfo(study):
    try:
        return study["protocolSection"]["designModule"]["enrollmentInfo"]["count"]
    except KeyError:
        return 0

def __getFacility(loc):
    try:
        return loc["facility"]
    except KeyError:
        return np.nan

def __getCity(loc):
    try:
        return loc["city"]
    except KeyError:
        return np.nan
    
def __getState(loc):
    try:
        return loc["state"]
    except KeyError:
        return np.nan


def __getZip(loc):
    try :
        return loc["zip"]
    except KeyError:
        return np.nan
 
def __getCountry(loc):
    try:
        return loc["country"]
    except KeyError:
        return np.nan

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

def __buildTrialList(study):
    trial_list = []
    nct_id = __getNctId(study)
    trial_list.append(nct_id)
    trial_list.append( __getOrganization(study))
    trial_list.append(__getTitle(study))
    trial_list.append(__getFirstSumbitDate(study))
    trial_list.append(__getCompletionDate(study))
    trial_list.append(__getOverallStatus(study))
    trial_list.append(__getMinimumAge(study))
    trial_list.append(__getMaximumAge(study))
    trial_list.append(__getSex(study))
    studyType = __getStudyType(study)
    trial_list.append(studyType)
    trial_list.append(__getPhases(study))
    trial_list.append(__getEnrollmentInfo(study))
    eligibilityCriteria = __getEligibilityCriteria(study)
    (isDeletion,isMutation,isUPD, isID) = __getGenotype(eligibilityCriteria,studyType)
    trial_list.append(isDeletion)
    trial_list.append(isMutation)
    trial_list.append(isUPD)
    trial_list.append(isID)
    trial_list.append(eligibilityCriteria)
    trial_list.append(__getBriefSummary(study))
    return trial_list 
    
def __buildLocsList(nct_id,loc):
    locs_list = []
    locs_list.append(nct_id)
    locs_list.append(__getFacility(loc))
    locs_list.append(__getCity(loc))
    locs_list.append(__getState(loc))
    locs_list.append(__getZip(loc))
    locs_list.append(__getCountry(loc))
    locs_list.append(__getGeoPointLat(loc))
    locs_list.append(__getGeoPointLon(loc))
    return locs_list

def __buildLocsListError(study):
    locs_list = []
    try:
        for official in study["protocolSection"]["contactsLocationsModule"]["overallOfficials"]:
            locs_list.append(official["affiliation"])
            [locs_list.append(np.nan) for _ in range(6)]    
    except KeyError:
        pass
    return locs_list
    
    

def __requestJSON():
    as_trial_url = "https://clinicaltrials.gov/api/v2/studies"
    as_trials_req = requests.get(
        as_trial_url,
        params={
            "query.cond": "Angelman Syndrome",
            "fields": "IdentificationModule,StatusModule,ContactsLocationsModule,EligibilityModule,DesignModule,DescriptionModule",
            "pageSize": 1000,
        },
    )
    return as_trials_req.json()

def __BuildDataFrame(data, listColumns):
    return pd.DataFrame(
        data,
        columns=listColumns,
    )

def as_trials():
    """
    Call the clinicaltrials.gov api and get list of trials for AS.
    Parse out to get basic trial info and locations. Will be used to make a map
    of AS trials.
    """
    as_trials_json = __requestJSON()

    #Only in Debug Mode
    #with open(f"{wkdir}/../../data/all_cities.json", 'w') as fichier:
    #    json.dump(as_trials_json, fichier, indent=4)
    
    as_trials_list = []
    as_trials_locs_list = []
    for study in as_trials_json["studies"]:
        # Make a df of
        nct_id = __getNctId(study)
        trial_list = __buildTrialList(study)
        as_trials_list.append(trial_list)

        # Make a separate df for trial locs since a give trial might have many locs
        try:
            for loc in study["protocolSection"]["contactsLocationsModule"]["locations"]:
                locs_list = __buildLocsList(nct_id,loc)
                as_trials_locs_list.append(locs_list)
        except KeyError:
            locs_list = __buildLocsListError(study)
            
    # output dataframes for use in visualization
    as_trials_df = __BuildDataFrame(as_trials_list,
                                    listColumns=["NCT_ID","Sponsor","Study_Name","Start_Date","End_Date", "Current_Status", "Minimum_Age", "Maximum_Age", "Sex","StudyType","Phases","EnrollmentInfo", "IsDeletion", "IsMutation", "IsUPD", "IsID","EligibilityCriteria","BriefSummary"])
    # as_trials_df.to_csv(f"{wkdir}/data/as_trials_df.csv", index=False)

    as_trials_locs_df = __BuildDataFrame(as_trials_locs_list,
                                         listColumns=["NCT_ID", "Facility", "City", "State", "Zip", "Country", "Lat", "Lon"])
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
        
        #This requires the fork at https://github.com/smtodd/thefuzz
        facilities_dedup = process.dedupe(current_city["Facility"], threshold=70, len_selector="shortest")
        # facilities_dedup = process.dedupe(current_city["Facility"], threshold=70)
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