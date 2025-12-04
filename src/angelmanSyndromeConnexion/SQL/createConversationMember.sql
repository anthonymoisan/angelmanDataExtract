CREATE TABLE IF NOT EXISTS T_Conversation_Member (
  conversation_id   BIGINT UNSIGNED NOT NULL,
  people_public_id  INT UNSIGNED    NOT NULL,
  
  role              ENUM('member','admin') NOT NULL DEFAULT 'member',

  -- Pour le fil de lecture / statut dans cette conversation
  last_read_message_id BIGINT UNSIGNED NULL,
  last_read_at         TIMESTAMP NULL DEFAULT NULL,
  is_muted             TINYINT(1) NOT NULL DEFAULT 0,

  joined_at        TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

  CONSTRAINT pk_conv_member PRIMARY KEY (conversation_id, people_public_id),

  CONSTRAINT fk_conv_member_conv
    FOREIGN KEY (conversation_id) REFERENCES T_Conversation(id)
    ON DELETE CASCADE,

  CONSTRAINT fk_conv_member_people
    FOREIGN KEY (people_public_id) REFERENCES T_People_Public(id)
    ON DELETE CASCADE,

  INDEX idx_conv_member_last_read (conversation_id, last_read_message_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
