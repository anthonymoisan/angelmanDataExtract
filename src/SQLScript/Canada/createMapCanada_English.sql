CREATE TABLE T_MapCanada_English (
    id INT PRIMARY KEY AUTO_INCREMENT,
    indexation INT NOT NULL UNIQUE,
    gender VARCHAR(255) NOT NULL,
    genotype VARCHAR(255) NOT NULL,
    age INT NOT NULL,
    groupAge VARCHAR(255) NOT NULL
);