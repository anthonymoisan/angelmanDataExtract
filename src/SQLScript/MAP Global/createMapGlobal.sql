CREATE TABLE T_MapGlobal (
    indexation INT PRIMARY KEY AUTO_INCREMENT,
    id INT NOT NULL UNIQUE,
    gender VARCHAR(255) NOT NULL,
    country VARCHAR(255) NOT NULL,
    genotype VARCHAR(255) NOT NULL,
    age INT NOT NULL,
    groupAge VARCHAR(255) NOT NULL,
    linkDashboard TEXT
);