CREATE TABLE IF NOT EXISTS T_People_Identity (
  person_id            INT UNSIGNED NOT NULL,

  -- PII chiffrées
  firstname       VARBINARY(1024) NOT NULL,
  lastname        VARBINARY(1024) NOT NULL,
  dateOfBirth     VARBINARY(256)  NOT NULL,
  emailAddress    VARBINARY(1024) NOT NULL,
  secret_question VARBINARY(256)  NOT NULL,
  secret_answer   VARBINARY(2048) NOT NULL,
  longitude       VARBINARY(256)  NOT NULL,
  latitude        VARBINARY(256)  NOT NULL,
  genotype        VARBINARY(1024) NOT NULL,


  -- Lookup déterministe (email normalisé)
  email_sha            BINARY(32)      NOT NULL,
  CONSTRAINT uq_identity_emailsha UNIQUE (email_sha),

  -- Auth
  password_hash        VARBINARY(255)  NOT NULL,
  password_algo        VARCHAR(32)     NOT NULL DEFAULT 'argon2id',
  password_meta        JSON            NULL,
  password_updated_at  TIMESTAMP       NULL DEFAULT NULL,

  -- Photo (option: déplacer dans une table dédiée ou stockage objet)
  photo                MEDIUMBLOB      NULL,
  photo_mime           VARCHAR(100)    NULL,

  -- Méta
  created_at           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

  CONSTRAINT pk_people_identity PRIMARY KEY (person_id),

  -- FK vers la table publique (adapte le nom si différent)
  CONSTRAINT fk_people_identity_person
    FOREIGN KEY (person_id) REFERENCES T_People_Public (id)
    ON DELETE CASCADE ON UPDATE CASCADE,
  
  -- Contraintes photo comme avant
  CONSTRAINT ck_photo_size
    CHECK (photo IS NULL OR OCTET_LENGTH(photo) <= 4*1024*1024),
  CONSTRAINT ck_photo_mime_presence
    CHECK ((photo IS NULL AND photo_mime IS NULL) OR (photo IS NOT NULL AND photo_mime IS NOT NULL)),
  CONSTRAINT ck_photo_mime_allowed
    CHECK (photo_mime IS NULL OR photo_mime IN ('image/jpeg','image/jpg', 'image/png','image/webp'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;