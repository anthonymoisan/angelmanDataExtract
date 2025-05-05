CREATE TABLE T_FAST_Latam_MapLatam_English (
    id INT PRIMARY KEY AUTO_INCREMENT,
    indexation INT NOT NULL UNIQUE,
    gender VARCHAR(255) NOT NULL,
    country VARCHAR(255) NOT NULL,
    city VARCHAR(255) NOT NULL,
    genotype VARCHAR(255) NOT NULL,
    age INT NOT NULL,
    groupAge VARCHAR(255) NOT NULL
);