CREATE TABLE IF NOT EXISTS T_PointRemarquable (
  id            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  longitude     DECIMAL(9,6)  NOT NULL,  -- [-180, 180]
  latitude      DECIMAL(8,6)  NOT NULL,  -- [-90, 90]
  short_desc    VARCHAR(160)  NOT NULL,
  long_desc     TEXT          NOT NULL,

  -- Photo (option: déplacer dans une table dédiée ou stockage objet)
  photo                MEDIUMBLOB      NULL,
  photo_mime           VARCHAR(100)    NULL,

  -- Colonne spatiale classique (SRID 4326 = WGS84)
  geom POINT SRID 4326 NOT NULL,

  created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

  CONSTRAINT pk_t_point PRIMARY KEY (id),
  CONSTRAINT ck_t_point_lon_range CHECK (longitude BETWEEN -180.0 AND 180.0),
  CONSTRAINT ck_t_point_lat_range CHECK (latitude  BETWEEN  -90.0 AND  90.0),

  CONSTRAINT ck_photo_size2
    CHECK (photo IS NULL OR OCTET_LENGTH(photo) <= 4*1024*1024),
  CONSTRAINT ck_photo_mime_presence2
    CHECK ((photo IS NULL AND photo_mime IS NULL) OR (photo IS NOT NULL AND photo_mime IS NOT NULL)),
  CONSTRAINT ck_photo_mime_allowed2
    CHECK (photo_mime IS NULL OR photo_mime IN ('image/jpeg','image/jpg', 'image/png','image/webp')),

  SPATIAL INDEX spx_t_point_geom (geom),
  INDEX ix_t_point_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
