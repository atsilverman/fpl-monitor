-- MIGRATION: Convert to Scalable Event-Based Architecture
-- =====================================================
--
-- This migration converts the existing user_notifications approach
-- to the new scalable event-based architecture.
--
-- IMPORTANT: Run this on your production Supabase database
-- This will preserve existing data and add new tables

-- ========================================
-- STEP 1: Create New Tables
-- ========================================

-- Create events table (new scalable approach)
CREATE TABLE IF NOT EXISTS public.events (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    event_type TEXT NOT NULL,
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
    fixture TEXT,
    
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

-- Create user ownership table
CREATE TABLE IF NOT EXISTS public.user_ownership (
    user_id UUID PRIMARY KEY,
    fpl_manager_id INTEGER UNIQUE,
    owned_players INTEGER[] DEFAULT '{}',
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create user preferences table
CREATE TABLE IF NOT EXISTS public.user_preferences (
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
-- STEP 2: Create Indexes
-- ========================================

-- Events table indexes
CREATE INDEX IF NOT EXISTS idx_events_type ON public.events(event_type);
CREATE INDEX IF NOT EXISTS idx_events_player ON public.events(player_id);
CREATE INDEX IF NOT EXISTS idx_events_gameweek ON public.events(gameweek);
CREATE INDEX IF NOT EXISTS idx_events_created_at ON public.events(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_events_type_created ON public.events(event_type, created_at DESC);

-- User ownership indexes
CREATE INDEX IF NOT EXISTS idx_user_ownership_players ON public.user_ownership USING GIN (owned_players);
CREATE INDEX IF NOT EXISTS idx_user_ownership_manager ON public.user_ownership(fpl_manager_id);
CREATE INDEX IF NOT EXISTS idx_user_ownership_active ON public.user_ownership(is_active) WHERE is_active = true;

-- User preferences indexes
CREATE INDEX IF NOT EXISTS idx_user_preferences_types ON public.user_preferences USING GIN (notification_types);
CREATE INDEX IF NOT EXISTS idx_user_preferences_push ON public.user_preferences(push_enabled) WHERE push_enabled = true;

-- ========================================
-- STEP 3: Migrate Existing Data
-- ========================================

-- Migrate existing user_notifications to events (if any exist)
-- This creates a single event for each unique notification
INSERT INTO public.events (
    event_type,
    player_id,
    player_name,
    team_name,
    gameweek,
    old_value,
    new_value,
    points_change,
    message,
    title,
    created_at
)
SELECT DISTINCT
    notification_type,
    player_id,
    player_name,
    team_name,
    gameweek,
    old_value,
    new_value,
    points_change,
    message,
    CASE 
        WHEN notification_type = 'goals' THEN '⚽ Goal!'
        WHEN notification_type = 'assists' THEN '🎯 Assist!'
        WHEN notification_type = 'clean_sheets' THEN '🛡️ Clean Sheet!'
        WHEN notification_type = 'bonus' THEN '⭐ Bonus Points!'
        WHEN notification_type = 'red_cards' THEN '🔴 Red Card'
        WHEN notification_type = 'yellow_cards' THEN '🟡 Yellow Card'
        WHEN notification_type = 'price_changes' THEN '💰 Price Change!'
        WHEN notification_type = 'status_changes' THEN '📊 Status Change'
        ELSE '📢 FPL Update'
    END as title,
    created_at
FROM public.user_notifications
WHERE NOT EXISTS (
    SELECT 1 FROM public.events e 
    WHERE e.event_type = user_notifications.notification_type
    AND e.player_id = user_notifications.player_id
    AND e.gameweek = user_notifications.gameweek
    AND e.created_at = user_notifications.created_at
);

-- Migrate existing users to user_preferences
INSERT INTO public.user_preferences (user_id, notification_types, push_enabled, timezone)
SELECT DISTINCT
    u.id,
    COALESCE(u.notification_preferences, '{
        "goals", "assists", "clean_sheets", "bonus", 
        "red_cards", "yellow_cards", "penalties_saved", 
        "penalties_missed", "own_goals", "saves", 
        "goals_conceded", "defensive_contribution", 
        "price_changes", "status_changes"
    }'::jsonb)::text[],
    COALESCE((u.notification_preferences->>'push_enabled')::boolean, true),
    COALESCE(u.timezone, 'America/Los_Angeles')
FROM public.users u
WHERE NOT EXISTS (
    SELECT 1 FROM public.user_preferences up WHERE up.user_id = u.id
);

-- ========================================
-- STEP 4: Create Triggers
-- ========================================

-- Create updated_at trigger if it doesn't exist
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Add triggers
CREATE TRIGGER update_events_updated_at 
    BEFORE UPDATE ON public.events 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_ownership_updated_at 
    BEFORE UPDATE ON public.user_ownership 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_preferences_updated_at 
    BEFORE UPDATE ON public.user_preferences 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ========================================
-- STEP 5: Enable RLS
-- ========================================

-- Enable RLS on new tables
ALTER TABLE public.events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_ownership ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_preferences ENABLE ROW LEVEL SECURITY;

-- Create RLS policies
CREATE POLICY "Events are public read-only" ON public.events
    FOR SELECT USING (true);

CREATE POLICY "Users can view own ownership" ON public.user_ownership
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can update own ownership" ON public.user_ownership
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own ownership" ON public.user_ownership
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can view own preferences" ON public.user_preferences
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can update own preferences" ON public.user_preferences
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own preferences" ON public.user_preferences
    FOR INSERT WITH CHECK (auth.uid() = user_id);

-- ========================================
-- STEP 6: Create Helper Functions
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
    SELECT last_notification_check INTO last_check
    FROM public.user_preferences
    WHERE user_id = p_user_id;
    
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
-- MIGRATION COMPLETE
-- ========================================

-- The migration is now complete! 
-- 
-- What was created:
-- 1. ✅ events table - scalable single source of truth
-- 2. ✅ user_ownership table - lightweight ownership tracking
-- 3. ✅ user_preferences table - notification settings
-- 4. ✅ All indexes for performance
-- 5. ✅ RLS policies for security
-- 6. ✅ Helper functions for the app
-- 7. ✅ Data migration from existing tables
--
-- Next steps:
-- 1. Update the production monitoring service
-- 2. Test with sample data
-- 3. Update the iOS app to use new API
