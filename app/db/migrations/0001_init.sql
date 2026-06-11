CREATE TYPE campaign_status AS ENUM ('draft', 'active', 'finished');
CREATE TYPE referral_status AS ENUM ('pending', 'verified', 'rejected');

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT NOT NULL UNIQUE,
    username VARCHAR(255),
    ref_code VARCHAR(64) NOT NULL UNIQUE,
    referred_by INTEGER REFERENCES users(id),
    age INTEGER,
    favorite_sport VARCHAR(128),
    is_blocked BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX ix_users_telegram_id ON users (telegram_id);
CREATE INDEX ix_users_ref_code ON users (ref_code);

CREATE TABLE campaigns (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    starts_at TIMESTAMPTZ NOT NULL,
    ends_at TIMESTAMPTZ NOT NULL,
    status campaign_status NOT NULL DEFAULT 'draft',
    top_k INTEGER NOT NULL DEFAULT 10,
    min_days_subscribed INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX ix_campaigns_status ON campaigns (status);

CREATE TABLE referrals (
    id SERIAL PRIMARY KEY,
    inviter_id INTEGER NOT NULL REFERENCES users(id),
    invitee_id INTEGER NOT NULL REFERENCES users(id),
    campaign_id INTEGER NOT NULL REFERENCES campaigns(id),
    status referral_status NOT NULL DEFAULT 'pending',
    verified_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_referrals_invitee_campaign UNIQUE (invitee_id, campaign_id)
);
CREATE INDEX ix_referrals_inviter_id ON referrals (inviter_id);
CREATE INDEX ix_referrals_invitee_id ON referrals (invitee_id);
CREATE INDEX ix_referrals_campaign_id ON referrals (campaign_id);
CREATE INDEX ix_referrals_status ON referrals (status);

CREATE TABLE tickets (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    campaign_id INTEGER NOT NULL REFERENCES campaigns(id),
    amount INTEGER NOT NULL DEFAULT 1,
    reason VARCHAR(64) NOT NULL DEFAULT 'referral_verified',
    source_referral_id INTEGER REFERENCES referrals(id),
    idempotency_key VARCHAR(128) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_tickets_idempotency_key UNIQUE (idempotency_key)
);
CREATE INDEX ix_tickets_user_id ON tickets (user_id);
CREATE INDEX ix_tickets_campaign_id ON tickets (campaign_id);
CREATE INDEX ix_tickets_idempotency_key ON tickets (idempotency_key);

CREATE TABLE draw_results (
    id SERIAL PRIMARY KEY,
    campaign_id INTEGER NOT NULL REFERENCES campaigns(id),
    winner_user_id INTEGER NOT NULL REFERENCES users(id),
    seed_info VARCHAR(255) NOT NULL,
    drawn_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_draw_campaign_winner UNIQUE (campaign_id, winner_user_id)
);
CREATE INDEX ix_draw_results_campaign_id ON draw_results (campaign_id);
CREATE INDEX ix_draw_results_winner_user_id ON draw_results (winner_user_id);

CREATE TABLE audit_logs (
    id SERIAL PRIMARY KEY,
    action VARCHAR(128) NOT NULL,
    actor_user_id INTEGER REFERENCES users(id),
    target_id VARCHAR(128),
    details VARCHAR(1024) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX ix_audit_logs_action ON audit_logs (action);
