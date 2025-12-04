CREATE TABLE IF NOT EXISTS T_Conversation (
  id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  title           VARCHAR(255)     NULL,  -- optionnel (groupes)
  is_group        TINYINT(1)       NOT NULL DEFAULT 0,
  
  -- meta
  created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  last_message_at TIMESTAMP NULL DEFAULT NULL,

  CONSTRAINT pk_conversation PRIMARY KEY (id),
  INDEX idx_conv_last_message (last_message_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
