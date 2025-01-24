# -*- coding: utf-8 -*-
"""
Created on Wed Jan 22 09:26:07 2025
Pub Med Methods
@author: antho
"""

import requests
import pandas as pd
import os
from lxml import etree
from bs4 import BeautifulSoup, Tag

def pubmed_details(query_key, web_env):
    """
    Get details of articles returned by pubmed_by_year
    """

    # uid_param = ",".join(uid_list)
    details_base = requests.get(
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi",
        params={
            "db": "pubmed",
            "query_key": query_key,
            "WebEnv": web_env,
            # "ui": uid_param,
            "retmode": "xml",
            "retmax": 10000,
        },
    )

    details_list = []
    soup = BeautifulSoup(details_base.content, "lxml-xml")
    pubs = soup.find_all("MedlineCitation")
    for pub in pubs:
        pmid = pub.find("PMID").text
        journal = pub.find("Journal")
        for elem in journal.descendants:
            if isinstance(elem, Tag):
                if elem.name == "ISOAbbreviation":
                    journal_abbreviation = elem.text
                elif elem.name == "Title":
                    journal_title = elem.text
                elif elem.name == "Year":
                    pub_year = elem.text
        authors = pub.find("AuthorList")
        try:
            institution = authors.find("Affiliation").text
        except AttributeError:
            institution = ""
        article_details_list = [
            pmid,
            journal_title,
            journal_abbreviation,
            pub_year,
            institution,
        ]
        details_list.append(article_details_list)

    pubmed_details_df = pd.DataFrame(
        details_list,
        columns=["pmid", "journal", "journal_abbrv", "pub_year", "institution"],
    )

    return pubmed_details_df


def pubmed_by_year(minyear):
    ncbi_base = requests.get(
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
        params={
            "db": "pubmed",
            "term": "('puppet+children'[Title/Abstract:~0]) OR ('happy+puppet+syndrome'[Title/Abstract:~0]) OR ('angelman+syndrome'[Title/Abstract:~0]) OR ('ube3a'[Title/Abstract]))",
            "rettype": "uilist",
            "datetype": "pdat",
            "mindate": minyear,
            # "maxdate": maxyear,
            "retmax": 20,
            "usehistory": "y",
        },
    )
    
    pub_tree = etree.fromstring(bytes(ncbi_base.text.strip(), encoding="utf8"))
    #pub_count = int(pub_tree.find(".//Count").text)
    #print(pub_count)
    try:
        uid_list = [u.text for u in pub_tree.iterfind(".//IdList/Id")]
    except ValueError:
        uid_list = []
    if uid_list:
        query_key = int(pub_tree.find(".//QueryKey").text)
        web_env = pub_tree.find(".//WebEnv").text
        details_df = pubmed_details(query_key, web_env)
    else:
        details_df = pd.DataFrame()

    return details_df
    

if __name__ == "__main__":
    # PULL PUBMED DATA
    # Get working directory
    wkdir = os.path.dirname(__file__)
        
    pubmed_df = pubmed_by_year(1965)
    pubmed_df.to_csv(f"{wkdir}/../data/pub_details_df.csv")
