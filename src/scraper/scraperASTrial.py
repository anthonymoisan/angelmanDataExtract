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
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from logger import setup_logger

# Set up logger
logger = setup_logger( debug=False)

# === Fonctions utilitaires internes ===

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
        return ','.join(enumPhases)
    except KeyError:
        return "unknown"

def __getEnrollmentInfo(study):
    try:
        return study["protocolSection"]["designModule"]["enrollmentInfo"]["count"]
    except KeyError:
        return 0

def __getFacility(loc):
    return loc.get("facility", np.nan)

def __getCity(loc):
    return loc.get("city", np.nan)

def __getState(loc):
    return loc.get("state", np.nan)

def __getZip(loc):
    return loc.get("zip", np.nan)

def __getCountry(loc):
    return loc.get("country", np.nan)

def __getGeoPointLat(loc):
    return loc.get("geoPoint", {}).get("lat", np.nan)

def __getGeoPointLon(loc):
    return loc.get("geoPoint", {}).get("lon", np.nan)

def __is_word_in_text(word, text):
    pattern = re.compile(r'(^|[^\w]){}([^\w]|$)'.format(word), re.IGNORECASE)
    return bool(re.search(pattern, text))

def __splitEligibility(text):
    inc = text.find("inclusion criteria:")
    exc = text.find("exclusion criteria:")
    return text[inc:exc-1] if inc != -1 and exc != -1 else text

def __getGenotype(text, studyType):
    if studyType == "OBSERVATIONAL":
        return (True, True, True, True, True)
    text = text.lower()
    inclusion = __splitEligibility(text)
    flags = [
        __is_word_in_text("deletion", inclusion),
        __is_word_in_text("mutation", inclusion),
        __is_word_in_text("upd", inclusion) or __is_word_in_text("disomie", inclusion),
        __is_word_in_text("icd", inclusion) or __is_word_in_text("imprinting defect", inclusion),
        __is_word_in_text("mosaic", inclusion),
    ]
    if not any(flags):
        return (True, True, True, True, True)
    return tuple(flags)

def __buildTrialList(study):
    nct_id = __getNctId(study)
    studyType = __getStudyType(study)
    eligibility = __getEligibilityCriteria(study)
    genotype = __getGenotype(eligibility, studyType)
    return [
        nct_id,
        __getOrganization(study),
        __getTitle(study),
        __getFirstSumbitDate(study),
        __getCompletionDate(study),
        __getOverallStatus(study),
        __getMinimumAge(study),
        __getMaximumAge(study),
        __getSex(study),
        studyType,
        __getPhases(study),
        __getEnrollmentInfo(study),
        *genotype,
        eligibility,
        __getBriefSummary(study),
    ]

def __buildLocsList(nct_id, loc):
    return [
        nct_id,
        __getFacility(loc),
        __getCity(loc),
        __getState(loc),
        __getZip(loc),
        __getCountry(loc),
        __getGeoPointLat(loc),
        __getGeoPointLon(loc),
    ]

def __requestJSON():
    response = requests.get(
        "https://clinicaltrials.gov/api/v2/studies",
        params={
            "query.cond": "Angelman Syndrome",
            "fields": "IdentificationModule,StatusModule,ContactsLocationsModule,EligibilityModule,DesignModule,DescriptionModule",
            "pageSize": 1000,
        },
    )
    return response.json()

def as_trials():
    data = __requestJSON()
    trials, locs = [], []

    for study in data["studies"]:
        nct = __getNctId(study)
        trials.append(__buildTrialList(study))
        for loc in study.get("protocolSection", {}).get("contactsLocationsModule", {}).get("locations", []):
            locs.append(__buildLocsList(nct, loc))

    df_trials = pd.DataFrame(trials, columns=[
        "NCT_ID", "Sponsor", "Study_Name", "Start_Date", "End_Date", "Current_Status",
        "Minimum_Age", "Maximum_Age", "Sex", "StudyType", "Phases", "EnrollmentInfo",
        "IsDeletion", "IsMutation", "IsUPD", "IsID", "IsMosaic",
        "EligibilityCriteria", "BriefSummary"
    ])

    df_locs = pd.DataFrame(locs, columns=[
        "NCT_ID", "Facility", "City", "State", "Zip", "Country", "Lat", "Lon"
    ])

    dedup = df_locs[["NCT_ID", "Facility", "Lat", "Lon"]].copy()
    for loc_type in ["City", "State", "Zip", "Country"]:
        temp = df_locs[["Facility", "Lat", "Lon", loc_type]].sort_values(by=["Facility", "Lat", "Lon", loc_type])
        temp = temp.drop_duplicates(subset=["Facility", "Lat", "Lon"], keep="first")
        dedup = dedup.merge(temp, how="left", on=["Facility", "Lat", "Lon"])

    merged = df_trials.merge(dedup, on="NCT_ID", how="left")
    merged["Hover_City"] = merged[["City", "State", "Country"]].apply(lambda x: x.str.cat(sep=", "), axis=1)

    all_cities = pd.DataFrame()
    for city in merged[["Lat", "Lon"]].drop_duplicates().itertuples(index=False):
        current_city = merged[(merged["Lat"] == city[0]) & (merged["Lon"] == city[1])].copy()
        facilities = process.dedupe(current_city["Facility"], threshold=70, len_selector="shortest")
        current_city["Facility_dedupe"] = current_city["Facility"].apply(lambda x: process.extractOne(x, facilities)[0])
        cities = process.dedupe(current_city["Hover_City"], threshold=70)
        current_city["Dedupe_City"] = current_city["Hover_City"].apply(lambda x: process.extractOne(x, cities)[0])
        all_cities = pd.concat([all_cities, current_city], axis=0)

    return all_cities

if __name__ == "__main__":
    start = time.time()
    wkdir = os.path.dirname(__file__)
    result = as_trials()
    result.to_csv(f"{wkdir}/../../data/all_cities.csv", index=False)
    logger.info("\nExecute time : %.2fs", time.time() - start)
