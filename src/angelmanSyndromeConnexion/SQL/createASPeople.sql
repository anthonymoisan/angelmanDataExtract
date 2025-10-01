CREATE TABLE IF NOT EXISTS T_ASPeople (
  id               INT UNSIGNED NOT NULL AUTO_INCREMENT,

  -- Champs chiffrés (Fernet -> VARBINARY)
  firstname        VARBINARY(1024) NOT NULL,
  lastname         VARBINARY(1024) NOT NULL,
  emailAddress     VARBINARY(1024) NOT NULL,
  dateOfBirth      VARBINARY(256)  NOT NULL,
  genotype         VARBINARY(1024) NOT NULL,
  city             VARBINARY(1024) NOT NULL,
  age              VARBINARY(256)  NOT NULL,
  longitude        VARBINARY(256)  NOT NULL,
  latitude         VARBINARY(256)  NOT NULL,

  -- Unicité déterministe (email normalisé: strip+lower)
  email_sha        BINARY(32)      NOT NULL,
  CONSTRAINT uq_aspeople_emailsha UNIQUE (email_sha),

  -- Authentification (mot de passe haché, format PHC recommandé)
  password_hash    VARBINARY(255)  NOT NULL,
  password_algo    VARCHAR(32)     NOT NULL DEFAULT 'argon2id',
  password_meta    JSON            NULL,
  password_updated_at TIMESTAMP    NULL DEFAULT NULL,

  -- Question secrète : entier 1..3
  -- 1 = "Nom de naissance de la maman ?"
  -- 2 = "Acteur/actrice de cinéma favori ?"
  -- 3 = "Animal de compagnie favori ?"
  secret_question  TINYINT UNSIGNED NOT NULL,
  CONSTRAINT ck_aspeople_secret_q_range
    CHECK (secret_question BETWEEN 1 AND 3),

  -- Réponse secrète (chiffrée)
  secret_answer    VARBINARY(2048) NOT NULL,

  -- Photo et méta non chiffrées
  photo            MEDIUMBLOB NULL,
  photo_mime       VARCHAR(100) NULL,

  -- Métadonnées
  created_at       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

  CONSTRAINT pk_aspeople PRIMARY KEY (id),

  -- Contraintes photo (< 4 MiB, MIME autorisés, cohérence MIME)
  CONSTRAINT ck_aspeople_photo_size
    CHECK (photo IS NULL OR OCTET_LENGTH(photo) <= 4*1024*1024),

  CONSTRAINT ck_aspeople_photo_mime_presence
    CHECK (
      (photo IS NULL AND photo_mime IS NULL) OR
      (photo IS NOT NULL AND photo_mime IS NOT NULL)
    ),

  CONSTRAINT ck_aspeople_photo_mime_allowed
    CHECK (
      photo_mime IS NULL OR
      photo_mime IN ('image/jpeg','image/jpg','image/png','image/webp')
    )
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
