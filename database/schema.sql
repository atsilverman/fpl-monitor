-- FPL LEAN DATABASE SCHEMA
-- Only essential tables and columns we actually get from FPL API endpoints

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- ========================================
-- ESSENTIAL TABLES (Only what we actually use)
-- ========================================

-- 1. TEAMS TABLE (From bootstrap-static)
CREATE TABLE teams (
    id SERIAL PRIMARY KEY,
    fpl_id INTEGER UNIQUE NOT NULL,  -- FPL's team ID
    code INTEGER UNIQUE NOT NULL,    -- FPL's team code
    name VARCHAR(100) NOT NULL,
    short_name VARCHAR(10) NOT NULL,
    position INTEGER,
    played INTEGER DEFAULT 0,
    win INTEGER DEFAULT 0,
    draw INTEGER DEFAULT 0,
    loss INTEGER DEFAULT 0,
    points INTEGER DEFAULT 0,
    strength INTEGER,                -- Overall strength (1-5)
    form VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. PLAYERS TABLE (From bootstrap-static)
CREATE TABLE players (
    id SERIAL PRIMARY KEY,
    fpl_id INTEGER UNIQUE NOT NULL,  -- FPL's element_id
    web_name VARCHAR(100) NOT NULL,
    first_name VARCHAR(100),
    second_name VARCHAR(100),
    team_id INTEGER REFERENCES teams(id),
    element_type INTEGER NOT NULL,   -- 1=GK, 2=DEF, 3=MID, 4=FWD
    now_cost INTEGER,               -- Current price (55 = £5.5m)
    total_points INTEGER DEFAULT 0,
    event_points INTEGER DEFAULT 0,
    points_per_game DECIMAL(4,1),
    form DECIMAL(4,1),
    selected_by_percent DECIMAL(5,2),
    status VARCHAR(10),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. GAMEWEEKS TABLE (From bootstrap-static)
CREATE TABLE gameweeks (
    id INTEGER PRIMARY KEY,          -- FPL's event_id
    name VARCHAR(50) NOT NULL,
    deadline_time TIMESTAMP,
    finished BOOLEAN DEFAULT FALSE,
    is_previous BOOLEAN DEFAULT FALSE,
    is_current BOOLEAN DEFAULT FALSE,
    is_next BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. FIXTURES TABLE (From fixtures endpoint)
CREATE TABLE fixtures (
    id INTEGER PRIMARY KEY,          -- FPL's fixture_id
    event_id INTEGER REFERENCES gameweeks(id),
    team_h INTEGER REFERENCES teams(id),
    team_a INTEGER REFERENCES teams(id),
    team_h_score INTEGER,
    team_a_score INTEGER,
    kickoff_time TIMESTAMP,
    started BOOLEAN DEFAULT FALSE,
    finished BOOLEAN DEFAULT FALSE,
    minutes INTEGER DEFAULT 0,
    team_h_difficulty INTEGER,       -- 1-5 difficulty rating
    team_a_difficulty INTEGER,       -- 1-5 difficulty rating
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. GAMEWEEK_STATS TABLE (From live endpoint)
CREATE TABLE gameweek_stats (
    id SERIAL PRIMARY KEY,
    player_id INTEGER REFERENCES players(id),
    fixture_id INTEGER REFERENCES fixtures(id),
    gameweek INTEGER NOT NULL,
    minutes INTEGER DEFAULT 0,
    goals_scored INTEGER DEFAULT 0,
    assists INTEGER DEFAULT 0,
    clean_sheets INTEGER DEFAULT 0,
    goals_conceded INTEGER DEFAULT 0,
    own_goals INTEGER DEFAULT 0,
    penalties_saved INTEGER DEFAULT 0,
    penalties_missed INTEGER DEFAULT 0,
    yellow_cards INTEGER DEFAULT 0,
    red_cards INTEGER DEFAULT 0,
    saves INTEGER DEFAULT 0,
    bonus INTEGER DEFAULT 0,
    bps INTEGER DEFAULT 0,
    influence DECIMAL(5,1),
    creativity DECIMAL(5,1),
    threat DECIMAL(5,1),
    ict_index DECIMAL(5,1),
    expected_goals DECIMAL(4,2),
    expected_assists DECIMAL(4,2),
    expected_goal_involvements DECIMAL(4,2),
    expected_goals_conceded DECIMAL(4,2),
    defensive_contribution INTEGER DEFAULT 0,
    tackles INTEGER DEFAULT 0,
    clearances_blocks_interceptions INTEGER DEFAULT 0,
    recoveries INTEGER DEFAULT 0,
    starts INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- BULLETPROOF: Prevent overwrites with unique constraint
    UNIQUE(player_id, fixture_id, gameweek)
);

-- 6. PLAYER_HISTORY TABLE (For ownership tracking)
CREATE TABLE player_history (
    id SERIAL PRIMARY KEY,
    fpl_id INTEGER NOT NULL,
    snapshot_date DATE NOT NULL,
    snapshot_window VARCHAR(50) NOT NULL,
    snapshot_timestamp TIMESTAMP NOT NULL,
    now_cost DECIMAL(4,1),
    selected_by_percent DECIMAL(5,2),
    status VARCHAR(10),
    news TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Prevent duplicate snapshots for same player/date/window
    UNIQUE(fpl_id, snapshot_date, snapshot_window)
);

-- 7. LIVE_MONITOR_HISTORY TABLE (For change tracking)
CREATE TABLE live_monitor_history (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    player_id INTEGER REFERENCES players(id),
    player_name VARCHAR(100),
    team_name VARCHAR(100),
    fixture_id INTEGER REFERENCES fixtures(id),
    gameweek INTEGER NOT NULL,
    event_type VARCHAR(50),
    old_value INTEGER,
    new_value INTEGER,
    points_change INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ========================================
-- INDEXES FOR PERFORMANCE
-- ========================================

-- Teams indexes
CREATE INDEX idx_teams_fpl_id ON teams(fpl_id);
CREATE INDEX idx_teams_code ON teams(code);

-- Players indexes
CREATE INDEX idx_players_fpl_id ON players(fpl_id);
CREATE INDEX idx_players_team ON players(team_id);
CREATE INDEX idx_players_element_type ON players(element_type);

-- Gameweeks indexes
CREATE INDEX idx_gameweeks_current ON gameweeks(is_current);
CREATE INDEX idx_gameweeks_finished ON gameweeks(finished);

-- Fixtures indexes
CREATE INDEX idx_fixtures_event ON fixtures(event_id);
CREATE INDEX idx_fixtures_teams ON fixtures(team_h, team_a);
CREATE INDEX idx_fixtures_finished ON fixtures(finished);

-- Gameweek stats indexes
CREATE INDEX idx_gameweek_stats_player ON gameweek_stats(player_id);
CREATE INDEX idx_gameweek_stats_fixture ON gameweek_stats(fixture_id);
CREATE INDEX idx_gameweek_stats_gameweek ON gameweek_stats(gameweek);

-- Player history indexes
CREATE INDEX idx_player_history_fpl_id ON player_history(fpl_id);
CREATE INDEX idx_player_history_date ON player_history(snapshot_date);
CREATE INDEX idx_player_history_window ON player_history(snapshot_window);
CREATE INDEX idx_player_history_date_window ON player_history(snapshot_date, snapshot_window);

-- Live monitoring indexes
CREATE INDEX idx_live_monitor_history_gameweek ON live_monitor_history(gameweek);
CREATE INDEX idx_live_monitor_history_timestamp ON live_monitor_history(timestamp);

-- ========================================
-- TRIGGERS FOR UPDATED_AT
-- ========================================

CREATE TRIGGER update_teams_updated_at BEFORE UPDATE ON teams FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_players_updated_at BEFORE UPDATE ON players FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_gameweeks_updated_at BEFORE UPDATE ON gameweeks FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_fixtures_updated_at BEFORE UPDATE ON fixtures FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_gameweek_stats_updated_at BEFORE UPDATE ON gameweek_stats FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ========================================
-- COMMENTS FOR DOCUMENTATION
-- ========================================

COMMENT ON TABLE teams IS 'Premier League teams from FPL bootstrap-static endpoint';
COMMENT ON TABLE players IS 'FPL players from bootstrap-static endpoint';
COMMENT ON TABLE gameweeks IS 'FPL gameweeks from bootstrap-static endpoint';
COMMENT ON TABLE fixtures IS 'Premier League fixtures from fixtures endpoint';
COMMENT ON TABLE gameweek_stats IS 'Player performance stats from live endpoint';
COMMENT ON TABLE player_history IS 'Daily snapshots of player ownership, prices, and status for tracking changes';
COMMENT ON TABLE live_monitor_history IS 'Audit trail of live events for notifications';

-- ========================================
-- SCHEMA COMPLETE
-- ========================================

-- This lean schema provides:
-- 1. Only essential tables we actually use
-- 2. Only columns we get from FPL API
-- 3. Bulletproof data integrity
-- 4. Performance optimization
-- 5. Clean, focused structure
