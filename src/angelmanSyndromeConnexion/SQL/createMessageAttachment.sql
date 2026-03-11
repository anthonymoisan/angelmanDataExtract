CREATE TABLE IF NOT EXISTS T_Message_Attachment (
  id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  message_id      BIGINT UNSIGNED NOT NULL,
  file_path       VARCHAR(512) NOT NULL,
  mime_type       VARCHAR(100) NOT NULL,
  file_name       VARCHAR(255) NULL,
  file_size       BIGINT NULL,
  created_at      TIMESTAMP NOT NULL,

  CONSTRAINT pk_message_attachment PRIMARY KEY (id),

  CONSTRAINT fk_attach_message
    FOREIGN KEY (message_id) REFERENCES T_Message(id)
    ON DELETE CASCADE,

  INDEX idx_attachment_message (message_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;