CREATE TABLE T_MapLatam_Capabilitie (
    id INT PRIMARY KEY AUTO_INCREMENT,
    populations VARCHAR(50) NOT NULL,
    conditions VARCHAR(255),
    therapy VARCHAR(50) NOT NULL,
    hospital VARCHAR(255) NOT NULL,
    contact VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    email2 VARCHAR(255),
    addressLocation VARCHAR(255) NOT NULL,
    country VARCHAR(255) NOT NULL,
    urlWebSite TEXT,
    longitude DECIMAL(10,4) NOT NULL,
    lattitude DECIMAL(10,4) NOT NULL
);