CREATE TABLE IF NOT EXISTS T_People_Public (
  id               INT UNSIGNED NOT NULL AUTO_INCREMENT,
  -- Données “quasi-publiques” / pseudonymisées
  city             VARCHAR(255)    NOT NULL,
  age_years        SMALLINT UNSIGNED NOT NULL, -- ex: 0..130
  pseudo           VARCHAR(255)    NOT NULL,
  
  status           ENUM('active','anonymized','deleted') NOT NULL DEFAULT 'active',

  -- Méta
  created_at       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

  CONSTRAINT pk_people_public PRIMARY KEY (id),
  INDEX idx_people_city (city),
  INDEX idx_people_age (age_years)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;