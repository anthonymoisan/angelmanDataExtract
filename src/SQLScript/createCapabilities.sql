CREATE TABLE T_Capabilitie (
    id INT PRIMARY KEY AUTO_INCREMENT,
    populations VARCHAR(50) NOT NULL,
    therapy VARCHAR(50) NOT NULL,
    phase VARCHAR(50) NOT NULL,
    hospital VARCHAR(255) NOT NULL,
    contact VARCHAR(255) NOT NULL,
    addressLocation VARCHAR(255) NOT NULL,
    longitude DECIMAL(10,4) NOT NULL,
    lattitude DECIMAL(10,4) NOT NULL,
    urlWebSite TEXT
);