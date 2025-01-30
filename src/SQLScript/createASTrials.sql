CREATE TABLE T_ASTrials (
    NCT_ID VARCHAR(20) PRIMARY KEY,
    Sponsor VARCHAR(255),
    Study_Name TEXT,
    Start_Date DATE,
    End_Date VARCHAR(10),
    Current_Status VARCHAR(50),
    Facility VARCHAR(255),
    Lat DECIMAL(9,6),
    Lon DECIMAL(9,6),
    City VARCHAR(100),
    State VARCHAR(100),
    Zip VARCHAR(20),
    Country VARCHAR(100),
    Hover_City VARCHAR(255),
    Facility_dedupe VARCHAR(255),
    Dedupe_City VARCHAR(255)
);