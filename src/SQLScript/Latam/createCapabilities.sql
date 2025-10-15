CREATE TABLE T_MapLatam_Capabilitie (
    id INT PRIMARY KEY AUTO_INCREMENT,
    populations VARBINARY(512) NOT NULL,
    conditions VARBINARY(512),
    therapy VARBINARY(512) NOT NULL,
    hospital VARBINARY(512) NOT NULL,
    contact VARBINARY(512) NOT NULL,
    email VARBINARY(512) NOT NULL,
    email2 VARBINARY(512),
    addressLocation VARBINARY(512) NOT NULL,
    country VARBINARY(512) NOT NULL,
    urlWebSite VARBINARY(512),
    longitude DECIMAL(10,4) NOT NULL,
    lattitude DECIMAL(10,4) NOT NULL
);