-- FPL MOBILE APP DATABASE SCHEMA FOR SUPABASE
-- Enhanced version of the existing schema with user management and mobile features
-- Based on the existing fpl-monitor schema with additions for mobile app

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- ========================================
-- USER MANAGEMENT TABLES
-- ========================================

-- Users table (extends Supabase auth.users)
CREATE TABLE public.users (
    id UUID REFERENCES auth.users(id) PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    fpl_manager_id INTEGER, -- User's FPL manager ID for personalized features
    notification_preferences JSONB DEFAULT '{
        "goals": true,
        "assists": true,
        "clean_sheets": true,
        "bonus": true,
        "red_cards": true,
        "yellow_cards": true,
        "penalties_saved": true,
        "penalties_missed": true,
        "own_goals": true,
        "saves": true,
        "goals_conceded": true,
        "defensive_contribution": true,
        "price_changes": true,
        "status_changes": true,
        "push_enabled": true,
        "email_enabled": false
    }'::jsonb,
    owned_players INTEGER[] DEFAULT '{}', -- Array of FPL player IDs owned by user
    mini_league_ids INTEGER[] DEFAULT '{}', -- Array of mini league IDs user is in
    timezone TEXT DEFAULT 'America/Los_Angeles',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- User notification history for timeline view
CREATE TABLE public.user_notifications (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES public.users(id) ON DELETE CASCADE,
    notification_type TEXT NOT NULL,
    player_id INTEGER,
    player_name TEXT,
    team_name TEXT,
    fixture_id INTEGER,
    gameweek INTEGER,
    old_value INTEGER,
    new_value INTEGER,
    points_change INTEGER,
    message TEXT NOT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ========================================
-- EXISTING FPL TABLES (Enhanced)
-- ========================================

-- 1. TEAMS TABLE (From bootstrap-static)
CREATE TABLE public.teams (
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
    badge_url TEXT,                  -- Team badge image URL
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. PLAYERS TABLE (From bootstrap-static)
CREATE TABLE public.players (
    id SERIAL PRIMARY KEY,
    fpl_id INTEGER UNIQUE NOT NULL,  -- FPL's element_id
    web_name VARCHAR(100) NOT NULL,
    first_name VARCHAR(100),
    second_name VARCHAR(100),
    team_id INTEGER REFERENCES public.teams(id),
    element_type INTEGER NOT NULL,   -- 1=GK, 2=DEF, 3=MID, 4=FWD
    now_cost INTEGER,               -- Current price (55 = £5.5m)
    total_points INTEGER DEFAULT 0,
    event_points INTEGER DEFAULT 0,
    points_per_game DECIMAL(4,1),
    form DECIMAL(4,1),
    selected_by_percent DECIMAL(5,2),
    status VARCHAR(10),
    news TEXT,                      -- Player news/updates from FPL API
    news_added TIMESTAMP WITH TIME ZONE, -- When news was added
    photo_url TEXT,                  -- Player photo URL
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. GAMEWEEKS TABLE (From bootstrap-static)
CREATE TABLE public.gameweeks (
    id INTEGER PRIMARY KEY,          -- FPL's event_id
    name VARCHAR(50) NOT NULL,
    deadline_time TIMESTAMP WITH TIME ZONE,
    finished BOOLEAN DEFAULT FALSE,
    is_previous BOOLEAN DEFAULT FALSE,
    is_current BOOLEAN DEFAULT FALSE,
    is_next BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 4. FIXTURES TABLE (From fixtures endpoint)
CREATE TABLE public.fixtures (
    id INTEGER PRIMARY KEY,          -- FPL's fixture_id
    event_id INTEGER REFERENCES public.gameweeks(id),
    team_h INTEGER REFERENCES public.teams(id),
    team_a INTEGER REFERENCES public.teams(id),
    team_h_score INTEGER,
    team_a_score INTEGER,
    kickoff_time TIMESTAMP WITH TIME ZONE,
    started BOOLEAN DEFAULT FALSE,
    finished BOOLEAN DEFAULT FALSE,
    minutes INTEGER DEFAULT 0,
    team_h_difficulty INTEGER,       -- 1-5 difficulty rating
    team_a_difficulty INTEGER,       -- 1-5 difficulty rating
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 5. GAMEWEEK_STATS TABLE (From live endpoint)
CREATE TABLE public.gameweek_stats (
    id SERIAL PRIMARY KEY,
    player_id INTEGER REFERENCES public.players(id),
    fixture_id INTEGER REFERENCES public.fixtures(id),
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
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- BULLETPROOF: Prevent overwrites with unique constraint
    UNIQUE(player_id, fixture_id, gameweek)
);

-- 6. PLAYER_HISTORY TABLE (For ownership tracking)
CREATE TABLE public.player_history (
    id SERIAL PRIMARY KEY,
    fpl_id INTEGER NOT NULL,
    snapshot_date DATE NOT NULL,
    snapshot_window VARCHAR(50) NOT NULL,
    snapshot_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    now_cost DECIMAL(4,1),
    selected_by_percent DECIMAL(5,2),
    status VARCHAR(10),
    news TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Prevent duplicate snapshots for same player/date/window
    UNIQUE(fpl_id, snapshot_date, snapshot_window)
);

-- 7. LIVE_MONITOR_HISTORY TABLE (For change tracking)
CREATE TABLE public.live_monitor_history (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    player_id INTEGER REFERENCES public.players(id),
    player_name VARCHAR(100),
    team_name VARCHAR(100),
    fixture_id INTEGER REFERENCES public.fixtures(id),
    gameweek INTEGER NOT NULL,
    event_type VARCHAR(50),
    old_value INTEGER,
    new_value INTEGER,
    points_change INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ========================================
-- INDEXES FOR PERFORMANCE
-- ========================================

-- User management indexes
CREATE INDEX idx_users_fpl_manager_id ON public.users(fpl_manager_id);
CREATE INDEX idx_user_notifications_user_id ON public.user_notifications(user_id);
CREATE INDEX idx_user_notifications_created_at ON public.user_notifications(created_at DESC);
CREATE INDEX idx_user_notifications_unread ON public.user_notifications(user_id, is_read) WHERE is_read = FALSE;

-- Teams indexes
CREATE INDEX idx_teams_fpl_id ON public.teams(fpl_id);
CREATE INDEX idx_teams_code ON public.teams(code);

-- Players indexes
CREATE INDEX idx_players_fpl_id ON public.players(fpl_id);
CREATE INDEX idx_players_team ON public.players(team_id);
CREATE INDEX idx_players_element_type ON public.players(element_type);

-- Gameweeks indexes
CREATE INDEX idx_gameweeks_current ON public.gameweeks(is_current);
CREATE INDEX idx_gameweeks_finished ON public.gameweeks(finished);

-- Fixtures indexes
CREATE INDEX idx_fixtures_event ON public.fixtures(event_id);
CREATE INDEX idx_fixtures_teams ON public.fixtures(team_h, team_a);
CREATE INDEX idx_fixtures_finished ON public.fixtures(finished);

-- Gameweek stats indexes
CREATE INDEX idx_gameweek_stats_player ON public.gameweek_stats(player_id);
CREATE INDEX idx_gameweek_stats_fixture ON public.gameweek_stats(fixture_id);
CREATE INDEX idx_gameweek_stats_gameweek ON public.gameweek_stats(gameweek);

-- Player history indexes
CREATE INDEX idx_player_history_fpl_id ON public.player_history(fpl_id);
CREATE INDEX idx_player_history_date ON public.player_history(snapshot_date);
CREATE INDEX idx_player_history_window ON public.player_history(snapshot_window);
CREATE INDEX idx_player_history_date_window ON public.player_history(snapshot_date, snapshot_window);

-- Live monitoring indexes
CREATE INDEX idx_live_monitor_history_gameweek ON public.live_monitor_history(gameweek);
CREATE INDEX idx_live_monitor_history_timestamp ON public.live_monitor_history(timestamp);

-- ========================================
-- TRIGGERS FOR UPDATED_AT
-- ========================================

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON public.users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_teams_updated_at BEFORE UPDATE ON public.teams FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_players_updated_at BEFORE UPDATE ON public.players FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_gameweeks_updated_at BEFORE UPDATE ON public.gameweeks FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_fixtures_updated_at BEFORE UPDATE ON public.fixtures FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_gameweek_stats_updated_at BEFORE UPDATE ON public.gameweek_stats FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ========================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- ========================================

-- Enable RLS on all tables
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.teams ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.players ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.gameweeks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.fixtures ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.gameweek_stats ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.player_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.live_monitor_history ENABLE ROW LEVEL SECURITY;

-- Users can only see their own data
CREATE POLICY "Users can view own profile" ON public.users
    FOR SELECT USING (auth.uid() = id);

CREATE POLICY "Users can update own profile" ON public.users
    FOR UPDATE USING (auth.uid() = id);

-- Users can only see their own notifications
CREATE POLICY "Users can view own notifications" ON public.user_notifications
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can update own notifications" ON public.user_notifications
    FOR UPDATE USING (auth.uid() = user_id);

-- FPL data is public read-only
CREATE POLICY "FPL data is public read-only" ON public.teams
    FOR SELECT USING (true);

CREATE POLICY "FPL data is public read-only" ON public.players
    FOR SELECT USING (true);

CREATE POLICY "FPL data is public read-only" ON public.gameweeks
    FOR SELECT USING (true);

CREATE POLICY "FPL data is public read-only" ON public.fixtures
    FOR SELECT USING (true);

CREATE POLICY "FPL data is public read-only" ON public.gameweek_stats
    FOR SELECT USING (true);

CREATE POLICY "FPL data is public read-only" ON public.player_history
    FOR SELECT USING (true);

CREATE POLICY "FPL data is public read-only" ON public.live_monitor_history
    FOR SELECT USING (true);

-- ========================================
-- FUNCTIONS FOR MOBILE APP
-- ========================================

-- Function to get user's notification timeline
CREATE OR REPLACE FUNCTION get_user_notifications(
    p_user_id UUID,
    p_limit INTEGER DEFAULT 50,
    p_offset INTEGER DEFAULT 0
)
RETURNS TABLE (
    id UUID,
    notification_type TEXT,
    player_name TEXT,
    team_name TEXT,
    points_change INTEGER,
    message TEXT,
    is_read BOOLEAN,
    created_at TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        un.id,
        un.notification_type,
        un.player_name,
        un.team_name,
        un.points_change,
        un.message,
        un.is_read,
        un.created_at
    FROM public.user_notifications un
    WHERE un.user_id = p_user_id
    ORDER BY un.created_at DESC
    LIMIT p_limit
    OFFSET p_offset;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to mark notifications as read
CREATE OR REPLACE FUNCTION mark_notifications_read(
    p_user_id UUID,
    p_notification_ids UUID[]
)
RETURNS INTEGER AS $$
DECLARE
    updated_count INTEGER;
BEGIN
    UPDATE public.user_notifications
    SET is_read = TRUE
    WHERE user_id = p_user_id
    AND id = ANY(p_notification_ids);
    
    GET DIAGNOSTICS updated_count = ROW_COUNT;
    RETURN updated_count;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to get unread notification count
CREATE OR REPLACE FUNCTION get_unread_count(p_user_id UUID)
RETURNS INTEGER AS $$
BEGIN
    RETURN (
        SELECT COUNT(*)
        FROM public.user_notifications
        WHERE user_id = p_user_id
        AND is_read = FALSE
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ========================================
-- COMMENTS FOR DOCUMENTATION
-- ========================================

COMMENT ON TABLE public.users IS 'User profiles extending Supabase auth.users';
COMMENT ON TABLE public.user_notifications IS 'User-specific notification timeline for mobile app';
COMMENT ON TABLE public.teams IS 'Premier League teams from FPL bootstrap-static endpoint';
COMMENT ON TABLE public.players IS 'FPL players from bootstrap-static endpoint';
COMMENT ON TABLE public.gameweeks IS 'FPL gameweeks from bootstrap-static endpoint';
COMMENT ON TABLE public.fixtures IS 'Premier League fixtures from fixtures endpoint';
COMMENT ON TABLE public.gameweek_stats IS 'Player performance stats from live endpoint';
COMMENT ON TABLE public.player_history IS 'Daily snapshots of player ownership, prices, and status for tracking changes';
COMMENT ON TABLE public.live_monitor_history IS 'Audit trail of live events for notifications';

-- ========================================
-- SCHEMA COMPLETE
-- ========================================

-- This enhanced schema provides:
-- 1. User management with Supabase auth integration
-- 2. Personalized notification timeline
-- 3. All existing FPL monitoring capabilities
-- 4. Row Level Security for data protection
-- 5. Mobile-optimized functions and indexes
-- 6. Real-time subscription support
