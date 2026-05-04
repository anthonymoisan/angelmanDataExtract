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
import time
import sys
from configparser import ConfigParser
from pathlib import Path
# met le *parent* du script (souvent .../src) dans sys.path
SRC_DIR = Path(__file__).resolve().parents[1]  # .../src
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
from tools.logger import setup_logger

# Set up logger
logger = setup_logger(debug=False)

BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"

# Load configuration
wkdir = os.path.dirname(__file__)
config = ConfigParser()
config_path = os.path.join(wkdir, "../../angelman_viz_keys/Config.ini") # Adjust to your actual config file name
if config.read(config_path) and 'PubMed' in config:
    NCBI_EMAIL = config['PubMed'].get('email', 'anthony@example.com')
    NCBI_API_KEY = config['PubMed'].get('api_key', None)
else:
    NCBI_EMAIL = "anthony@example.com"
    NCBI_API_KEY = None

def pubmed_details(query_key, web_env, count=20):
    """
    Get details of articles returned by pubmed_by_year
    """
    details_base = requests.get(
        f"{BASE_URL}efetch.fcgi",
        params={
            "db": "pubmed",
            "query_key": query_key,
            "WebEnv": web_env,
            "retmode": "xml",
            "retmax": count,
            "email": NCBI_EMAIL,
            "tool": "angelman_data_extract",
            "api_key": NCBI_API_KEY
        },
    )

    details_list = []
    soup = BeautifulSoup(details_base.content, "lxml-xml")

    pubs = soup.find_all("PubmedArticle")
    for pub in pubs:
        citation = pub.find("MedlineCitation")
        pmid = citation.find("PMID").text if citation and citation.find("PMID") else ""
        article = citation.find("Article") if citation else None
        
        # Initialize metadata values
        journal_title = ""
        journal_abbreviation = ""
        pub_year = "unknown"
        institution = ""
        
        # Extract Journal Info using descendants loop
        journal = article.find("Journal") if article else None
        if journal:
            for elem in journal.descendants:
                if isinstance(elem, Tag):
                    if elem.name == "ISOAbbreviation":
                        journal_abbreviation = elem.text
                    elif elem.name == "Title":
                        journal_title = elem.text
                    elif elem.name == "Year":
                        pub_year = elem.text
                    elif elem.name == "MedlineDate" and pub_year == "unknown":
                        pub_year = elem.text[:4]

        # Extract Authors
        author_names = []
        author_list_tag = article.find("AuthorList") if article else None
        if author_list_tag:
            for author in author_list_tag.find_all("Author"):
                last_name = author.find("LastName")
                fore_name = author.find("ForeName")
                collective = author.find("CollectiveName")

                if collective:
                    author_names.append(collective.get_text())
                elif last_name:
                    name = last_name.get_text()
                    if fore_name:
                        name = f"{name} {fore_name.get_text()}"
                    author_names.append(name)
        authors_str = "; ".join(author_names)

        # Institution from first author
        first_author = author_list_tag.find("Author") if author_list_tag else None
        if first_author:
            aff_info = first_author.find("AffiliationInfo")
            if aff_info:
                aff = aff_info.find("Affiliation")
                institution = aff.get_text() if aff else aff_info.get_text()
            else:
                aff = first_author.find("Affiliation")
                if aff:
                    institution = aff.get_text()
        
        # Article Title and Abstract
        article_title = article.find("ArticleTitle").text if article and article.find("ArticleTitle") else ""
        abstract_texts = article.find_all("AbstractText") if article else []
        abstract_content = " ".join([t.text for t in abstract_texts]) if abstract_texts else ""
        
        article_details_list = [
            pmid,
            authors_str,
            journal_title,
            journal_abbreviation,
            pub_year,
            institution,
            article_title,
            abstract_content
        ]
        details_list.append(article_details_list)

    pubmed_details_df = pd.DataFrame(
        details_list,
        columns=["pmid", "authors", "journal", "journal_abbrv", "pub_year", "institution", "article_title", "abstract"],
    )
    return pubmed_details_df


def pubmed_by_year(minyear):
    search_term = "(('puppet+children'[Title/Abstract:~0]) OR ('happy+puppet+syndrome'[Title/Abstract:~0]) OR ('angelman+syndrome'[Title/Abstract:~0]) OR ('ube3a'[Title/Abstract]))"
    ncbi_base = requests.get(
        f"{BASE_URL}esearch.fcgi",
        params={
            "db": "pubmed",
            "term": search_term,
            "rettype": "uilist",
            "datetype": "pdat",
            "mindate": minyear,
            "retmax": 1000,
            "usehistory": "y",
            "email": NCBI_EMAIL,
            "tool": "angelman_data_extract",
            "api_key": NCBI_API_KEY
        },
    )
    
    pub_tree = etree.fromstring(bytes(ncbi_base.text.strip(), encoding="utf8"))
    try:
        pub_count = int(pub_tree.find(".//Count").text)
        uid_list = [u.text for u in pub_tree.iterfind(".//IdList/Id")]
    except (ValueError, AttributeError, TypeError):
        uid_list = []
        pub_count = 0
        
    if uid_list:
        query_key = int(pub_tree.find(".//QueryKey").text)
        web_env = pub_tree.find(".//WebEnv").text
        details_df = pubmed_details(query_key, web_env, count=pub_count)
    else:
        details_df = pd.DataFrame()
    return details_df
   


if __name__ == "__main__":
    start = time.time()
    # PULL PUBMED DATA
    # Get working directory
    wkdir = os.path.dirname(__file__)
        
    pubmed_df = pubmed_by_year(1965)
    pubmed_df.to_csv(f"{wkdir}/../../data/pub_details_df.csv", index=False)
    logger.info("\nExecute time : %.2fs", time.time() - start)