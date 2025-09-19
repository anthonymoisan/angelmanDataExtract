CREATE TABLE IF NOT EXISTS T_ASPeople (
  id               INT UNSIGNED NOT NULL AUTO_INCREMENT,

  -- Champs chiffrés (Fernet -> VARBINARY)
  firstname        VARBINARY(1024) NOT NULL,
  lastname         VARBINARY(1024) NOT NULL,
  emailAddress     VARBINARY(1024) NOT NULL,
  dateOfBirth      VARBINARY(256)  NOT NULL,
  genotype         VARBINARY(1024) NOT NULL,
  city             VARBINARY(1024) NULL,

  -- Unicité déterministe (email normalisé: strip+lower)
  email_sha        BINARY(32)      NOT NULL,
  CONSTRAINT uq_aspeople_emailsha UNIQUE (email_sha),

  -- Photo et méta non chiffrées
  photo            MEDIUMBLOB NULL,
  photo_mime       VARCHAR(100) NULL,

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
