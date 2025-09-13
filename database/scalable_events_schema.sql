-- SCALABLE EVENT-BASED NOTIFICATION SCHEMA
-- ===========================================
-- 
-- This schema implements a scalable event-based architecture where:
-- 1. Events are stored once and shared by all users
-- 2. User ownership is tracked separately for the isOwned flag
-- 3. Massive scalability: 1 event = 1 record regardless of user count
--
-- Storage efficiency: 1,000 events/day = 1,000 records (not 1,000 × users)

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
-- EVENTS TABLE (Single source of truth)
-- ========================================

CREATE TABLE public.events (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    event_type TEXT NOT NULL,  -- 'goal', 'assist', 'price_change', 'status_change', etc.
    player_id INTEGER NOT NULL,
    player_name TEXT NOT NULL,
    team_name TEXT NOT NULL,
    team_abbreviation TEXT,
    
    -- Points and scoring
    points INTEGER DEFAULT 0,
    points_change INTEGER DEFAULT 0,
    points_category TEXT,
    total_points INTEGER,
    gameweek_points INTEGER,
    
    -- Game context
    gameweek INTEGER NOT NULL,
    fixture_id INTEGER,
    home_team TEXT,
    away_team TEXT,
    fixture TEXT,  -- "LIV vs ARS"
    
    -- Price information
    player_price DECIMAL(4,1),
    price_change DECIMAL(4,1),
    
    -- Status information
    player_status TEXT,
    old_status TEXT,
    news_text TEXT,
    old_news TEXT,
    
    -- Values for tracking changes
    old_value INTEGER,
    new_value INTEGER,
    
    -- Notification content
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ========================================
-- USER OWNERSHIP TRACKING (Lightweight)
-- ========================================

CREATE TABLE public.user_ownership (
    user_id UUID PRIMARY KEY,
    fpl_manager_id INTEGER UNIQUE,
    owned_players INTEGER[] DEFAULT '{}',  -- Array of player IDs user owns
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ========================================
-- USER PREFERENCES (Notification settings)
-- ========================================

CREATE TABLE public.user_preferences (
    user_id UUID PRIMARY KEY,
    notification_types TEXT[] DEFAULT '{
        "goals", "assists", "clean_sheets", "bonus", 
        "red_cards", "yellow_cards", "penalties_saved", 
        "penalties_missed", "own_goals", "saves", 
        "goals_conceded", "defensive_contribution", 
        "price_changes", "status_changes"
    }'::text[],
    push_enabled BOOLEAN DEFAULT true,
    email_enabled BOOLEAN DEFAULT false,
    timezone TEXT DEFAULT 'America/Los_Angeles',
    last_notification_check TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ========================================
-- EXISTING FPL TABLES (Keep for joins)
-- ========================================

-- Keep existing tables for rich data joins
-- (teams, players, gameweeks, fixtures, etc.)

-- ========================================
-- INDEXES FOR PERFORMANCE
-- ========================================

-- Events table indexes
CREATE INDEX idx_events_type ON public.events(event_type);
CREATE INDEX idx_events_player ON public.events(player_id);
CREATE INDEX idx_events_gameweek ON public.events(gameweek);
CREATE INDEX idx_events_created_at ON public.events(created_at DESC);
CREATE INDEX idx_events_type_created ON public.events(event_type, created_at DESC);

-- User ownership indexes
CREATE INDEX idx_user_ownership_players ON public.user_ownership USING GIN (owned_players);
CREATE INDEX idx_user_ownership_manager ON public.user_ownership(fpl_manager_id);
CREATE INDEX idx_user_ownership_active ON public.user_ownership(is_active) WHERE is_active = true;

-- User preferences indexes
CREATE INDEX idx_user_preferences_types ON public.user_preferences USING GIN (notification_types);
CREATE INDEX idx_user_preferences_push ON public.user_preferences(push_enabled) WHERE push_enabled = true;

-- ========================================
-- TRIGGERS FOR UPDATED_AT
-- ========================================

CREATE TRIGGER update_events_updated_at BEFORE UPDATE ON public.events FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_user_ownership_updated_at BEFORE UPDATE ON public.user_ownership FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_user_preferences_updated_at BEFORE UPDATE ON public.user_preferences FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ========================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- ========================================

-- Enable RLS
ALTER TABLE public.events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_ownership ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_preferences ENABLE ROW LEVEL SECURITY;

-- Events are public read-only (everyone sees same events)
CREATE POLICY "Events are public read-only" ON public.events
    FOR SELECT USING (true);

-- Users can only see their own ownership data
CREATE POLICY "Users can view own ownership" ON public.user_ownership
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can update own ownership" ON public.user_ownership
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own ownership" ON public.user_ownership
    FOR INSERT WITH CHECK (auth.uid() = user_id);

-- Users can only see their own preferences
CREATE POLICY "Users can view own preferences" ON public.user_preferences
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can update own preferences" ON public.user_preferences
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own preferences" ON public.user_preferences
    FOR INSERT WITH CHECK (auth.uid() = user_id);

-- ========================================
-- FUNCTIONS FOR MOBILE APP
-- ========================================

-- Function to get user notifications with ownership
CREATE OR REPLACE FUNCTION get_user_notifications(
    p_user_id UUID,
    p_limit INTEGER DEFAULT 50,
    p_offset INTEGER DEFAULT 0
)
RETURNS TABLE (
    id UUID,
    event_type TEXT,
    player_id INTEGER,
    player_name TEXT,
    team_name TEXT,
    team_abbreviation TEXT,
    points INTEGER,
    points_change INTEGER,
    points_category TEXT,
    total_points INTEGER,
    gameweek_points INTEGER,
    gameweek INTEGER,
    fixture_id INTEGER,
    home_team TEXT,
    away_team TEXT,
    fixture TEXT,
    player_price DECIMAL(4,1),
    price_change DECIMAL(4,1),
    player_status TEXT,
    old_status TEXT,
    news_text TEXT,
    old_news TEXT,
    old_value INTEGER,
    new_value INTEGER,
    title TEXT,
    message TEXT,
    is_owned BOOLEAN,
    created_at TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        e.id,
        e.event_type,
        e.player_id,
        e.player_name,
        e.team_name,
        e.team_abbreviation,
        e.points,
        e.points_change,
        e.points_category,
        e.total_points,
        e.gameweek_points,
        e.gameweek,
        e.fixture_id,
        e.home_team,
        e.away_team,
        e.fixture,
        e.player_price,
        e.price_change,
        e.player_status,
        e.old_status,
        e.news_text,
        e.old_news,
        e.old_value,
        e.new_value,
        e.title,
        e.message,
        CASE WHEN e.player_id = ANY(uo.owned_players) THEN true ELSE false END as is_owned,
        e.created_at
    FROM public.events e
    CROSS JOIN public.user_ownership uo
    JOIN public.user_preferences up ON uo.user_id = up.user_id
    WHERE uo.user_id = p_user_id
    AND e.event_type = ANY(up.notification_types)
    ORDER BY e.created_at DESC
    LIMIT p_limit
    OFFSET p_offset;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to update user ownership
CREATE OR REPLACE FUNCTION update_user_ownership(
    p_user_id UUID,
    p_fpl_manager_id INTEGER,
    p_owned_players INTEGER[]
)
RETURNS VOID AS $$
BEGIN
    INSERT INTO public.user_ownership (user_id, fpl_manager_id, owned_players, last_updated)
    VALUES (p_user_id, p_fpl_manager_id, p_owned_players, NOW())
    ON CONFLICT (user_id) 
    DO UPDATE SET 
        fpl_manager_id = EXCLUDED.fpl_manager_id,
        owned_players = EXCLUDED.owned_players,
        last_updated = EXCLUDED.last_updated,
        updated_at = NOW();
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to get unread notification count
CREATE OR REPLACE FUNCTION get_unread_count(p_user_id UUID)
RETURNS INTEGER AS $$
DECLARE
    last_check TIMESTAMP WITH TIME ZONE;
    unread_count INTEGER;
BEGIN
    -- Get user's last check time
    SELECT last_notification_check INTO last_check
    FROM public.user_preferences
    WHERE user_id = p_user_id;
    
    -- Count events since last check
    SELECT COUNT(*) INTO unread_count
    FROM public.events e
    JOIN public.user_preferences up ON up.user_id = p_user_id
    WHERE e.created_at > COALESCE(last_check, '1970-01-01'::timestamp)
    AND e.event_type = ANY(up.notification_types);
    
    RETURN unread_count;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to mark notifications as read
CREATE OR REPLACE FUNCTION mark_notifications_read(p_user_id UUID)
RETURNS VOID AS $$
BEGIN
    UPDATE public.user_preferences
    SET last_notification_check = NOW(),
        updated_at = NOW()
    WHERE user_id = p_user_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ========================================
-- COMMENTS FOR DOCUMENTATION
-- ========================================

COMMENT ON TABLE public.events IS 'Single source of truth for all FPL events - shared by all users';
COMMENT ON TABLE public.user_ownership IS 'Lightweight tracking of which players each user owns';
COMMENT ON TABLE public.user_preferences IS 'User notification preferences and settings';

-- ========================================
-- SCHEMA COMPLETE
-- ========================================

-- This scalable schema provides:
-- 1. Single events table - 1 event = 1 record regardless of user count
-- 2. Lightweight ownership tracking - just array lookups
-- 3. Massive scalability - 1,000 events/day = 1,000 records
-- 4. Rich data - all 25+ SwiftUI fields available
-- 5. Real-time capable - can push events immediately
-- 6. Efficient queries - optimized indexes and functions
