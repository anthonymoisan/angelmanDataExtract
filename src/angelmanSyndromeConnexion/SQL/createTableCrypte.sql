CREATE TABLE T_Crypte (
    id INT PRIMARY KEY,
    firstname VARCHAR(255),
    lastname VARCHAR(255),
    email TEXT NOT NULL,
    FOREIGN KEY (id) REFERENCES T_AngelmanSyndromeConnexion(id)
);