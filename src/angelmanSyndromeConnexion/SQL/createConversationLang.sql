CREATE TABLE IF NOT EXISTS T_Conversation_Lang (
  conversation_id BIGINT UNSIGNED NOT NULL,
  lang CHAR(2) NOT NULL,
  PRIMARY KEY (conversation_id, lang),
  CONSTRAINT fk_conv_lang_conversation
    FOREIGN KEY (conversation_id)
    REFERENCES T_Conversation(id)
    ON DELETE CASCADE
    ON UPDATE CASCADE,
  INDEX idx_conv_lang_lang (lang)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
