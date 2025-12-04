CREATE TABLE IF NOT EXISTS T_Message_Attachment (
  id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  message_id      BIGINT UNSIGNED NOT NULL,

  storage_key     VARCHAR(512)  NOT NULL,  -- chemin / clé objet (S3, etc.)
  mime_type       VARCHAR(100)  NOT NULL,
  file_name       VARCHAR(255)  NULL,
  file_size       BIGINT UNSIGNED NULL,    -- en octets

  -- pour les images/vidéos
  width           INT UNSIGNED NULL,
  height          INT UNSIGNED NULL,
  thumbnail_key   VARCHAR(512) NULL,

  created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

  CONSTRAINT pk_message_attachment PRIMARY KEY (id),

  CONSTRAINT fk_attach_message
    FOREIGN KEY (message_id) REFERENCES T_Message(id)
    ON DELETE CASCADE,

  INDEX idx_attachment_message (message_id),
  INDEX idx_attachment_mime (mime_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
