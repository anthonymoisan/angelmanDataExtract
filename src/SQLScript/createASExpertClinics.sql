CREATE TABLE T_ASExpertClinicalTrials (
    NCT_ID VARCHAR(20) PRIMARY KEY,
    Sponsor VARCHAR(255),
    Study_Name TEXT,
    Start_Date DATE,
    End_Date VARCHAR(10),
    Current_Status VARCHAR(50),
    Treatment VARCHAR(50),
    Facility VARCHAR(255),
    Lat_scrape DECIMAL(9,6),
    Lon_scrape DECIMAL(9,6),
    Lat_map DECIMAL(19,14),
    Lon_map DECIMAL(19,14)
);