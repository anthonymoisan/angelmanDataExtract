CREATE TABLE IF NOT EXISTS T_Message (
  id                 BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  conversation_id    BIGINT UNSIGNED NOT NULL,
  sender_people_id   INT UNSIGNED    NOT NULL,
  
  body_text           VARBINARY(65000)            NULL, -- message texte (peut être vide si seulement PJ)
  reply_to_message_id BIGINT UNSIGNED NULL, -- pour les réponses/thread

  has_attachments    TINYINT(1) NOT NULL DEFAULT 0,

  -- statut "soft delete" / édition
  status             ENUM('normal','edited','deleted') NOT NULL DEFAULT 'normal',
  created_at         TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  edited_at          TIMESTAMP NULL DEFAULT NULL,
  deleted_at         TIMESTAMP NULL DEFAULT NULL,

  CONSTRAINT pk_message PRIMARY KEY (id),

  CONSTRAINT fk_message_conv
    FOREIGN KEY (conversation_id) REFERENCES T_Conversation(id)
    ON DELETE CASCADE,

  CONSTRAINT fk_message_sender
    FOREIGN KEY (sender_people_id) REFERENCES T_People_Public(id)
    ON DELETE RESTRICT,

  CONSTRAINT fk_message_reply
    FOREIGN KEY (reply_to_message_id) REFERENCES T_Message(id)
    ON DELETE SET NULL,

  INDEX idx_message_conv_created (conversation_id, created_at),
  INDEX idx_message_sender (sender_people_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
