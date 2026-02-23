CREATE TABLE IF NOT EXISTS T_People_Public (
  id               INT UNSIGNED NOT NULL AUTO_INCREMENT,
  gender           VARCHAR(1)      NOT NULL,
  -- Données “quasi-publiques” / pseudonymisées
  city             VARCHAR(255)    NOT NULL,
  country          VARCHAR(255)    NOT NULL,
  country_code     VARCHAR(2)      NOT NULL,
  lang             VARCHAR(2)      NOT NULL,
  age_years        SMALLINT UNSIGNED NOT NULL, -- ex: 0..130
  pseudo           VARCHAR(255)    NOT NULL,
  
  
  status           ENUM('active','anonymized','deleted') NOT NULL DEFAULT 'active',

  is_connected TINYINT(1) NOT NULL DEFAULT 0,
  is_info TINYINT(1) NOT NULL DEFAULT 0,

  -- Méta
  created_at       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

  CONSTRAINT pk_people_public PRIMARY KEY (id),
  INDEX idx_people_city (city),
  INDEX idx_people_age (age_years),
  INDEX idx_people_connected (is_connected),
  INDEX idx_people_lang (lang)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;