CREATE TABLE IF NOT EXISTS T_Message_Reaction (
  message_id        BIGINT UNSIGNED NOT NULL,
  people_public_id  INT UNSIGNED    NOT NULL,
  emoji             VARCHAR(16)     NOT NULL, -- 1 emoji (UTF-8)

  created_at        TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

  CONSTRAINT pk_message_reaction PRIMARY KEY (message_id, people_public_id, emoji),

  CONSTRAINT fk_reaction_message
    FOREIGN KEY (message_id) REFERENCES T_Message(id)
    ON DELETE CASCADE,

  CONSTRAINT fk_reaction_people
    FOREIGN KEY (people_public_id) REFERENCES T_People_Public(id)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
