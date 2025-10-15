CREATE TABLE T_MapFrance_RegionDepartement_French (
    id INT PRIMARY KEY AUTO_INCREMENT,
    numero_Insee VARBINARY(512) NULL,
    departement VARBINARY(512) NOT NULL,
    region VARBINARY(512) NOT NULL
);