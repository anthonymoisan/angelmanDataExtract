CREATE TABLE T_MapFrance_Capabilitie (
    id INT PRIMARY KEY AUTO_INCREMENT,
    populations VARBINARY(512) NOT NULL,
    therapy VARBINARY(512) NOT NULL,
    phase VARBINARY(512) NOT NULL,
    hospital VARBINARY(512) NOT NULL,
    contact VARBINARY(512) NOT NULL,
    addressLocation VARBINARY(512) NOT NULL,
    longitude DECIMAL(10,4) NOT NULL,
    lattitude DECIMAL(10,4) NOT NULL,
    urlWebSite VARBINARY(512)
);