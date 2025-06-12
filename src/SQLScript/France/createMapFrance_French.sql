CREATE TABLE T_MapFrance_French (
    indexation INT PRIMARY KEY AUTO_INCREMENT,
    id INT NOT NULL UNIQUE,
    annee INT NOT NULL,
    code_Departement VARCHAR(255) NOT NULL,
    genoytype VARCHAR(255) NOT NULL,
    sexe VARCHAR(1) NOT NULL,
    difficultesSA VARCHAR(255) NOT NULL
);