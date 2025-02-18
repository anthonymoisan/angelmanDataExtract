CREATE TABLE T_ArticlesPubMed (
    id INT PRIMARY KEY AUTO_INCREMENT,
    pmid BIGINT NOT NULL UNIQUE,
    journal VARCHAR(255),
    journal_abbrv VARCHAR(255),
    pub_year INT,
    institution TEXT,
    article_title TEXT,
    abstract TEXT
);