    async def sync_core_tables_fast(self, bootstrap_data):
        """Sync small core tables (teams, gameweeks, fixtures) frequently for real-time accuracy"""
        try:
            self.logger.info("Syncing core tables with fresh FPL data...")
            
            # Update small core tables (safe to refresh frequently)
            await self.update_teams_table(bootstrap_data)
            await self.update_gameweeks_table(bootstrap_data)
            await self.update_fixtures_table(bootstrap_data)
            
            self.logger.info("Core tables sync completed")
            
        except Exception as e:
            self.logger.error(f"Error syncing core tables: {e}")

    async def update_teams_table(self, bootstrap_data):
        """Update teams table with fresh FPL data (20 records - safe to refresh frequently)"""
        try:
            teams = bootstrap_data.get('teams', [])
            if not teams:
                return
                
            for team in teams:
                # Use UPSERT to handle existing data
                response = requests.post(
                    f'{self.supabase_url}/rest/v1/teams',
                    headers=self.headers,
                    json={
                        'fpl_id': team['id'],
                        'code': team['code'],
                        'name': team['name'],
                        'short_name': team['short_name'],
                        'position': team.get('position'),
                        'played': team.get('played', 0),
                        'win': team.get('win', 0),
                        'draw': team.get('draw', 0),
                        'loss': team.get('loss', 0),
                        'points': team.get('points', 0),
                        'strength': team.get('strength'),
                        'form': team.get('form'),
                        'badge_url': team.get('badge_url')
                    },
                    timeout=10
                )
                
            self.logger.debug(f"Updated {len(teams)} teams")
            
        except Exception as e:
            self.logger.error(f"Error updating teams: {e}")

    async def update_gameweeks_table(self, bootstrap_data):
        """Update gameweeks table with fresh FPL data (38 records - safe to refresh frequently)"""
        try:
            events = bootstrap_data.get('events', [])
            if not events:
                return
                
            for event in events:
                # Use UPSERT to handle existing data
                response = requests.post(
                    f'{self.supabase_url}/rest/v1/gameweeks',
                    headers=self.headers,
                    json={
                        'fpl_id': event['id'],
                        'name': event['name'],
                        'deadline_time': event['deadline_time'],
                        'is_current': event.get('is_current', False),
                        'is_previous': event.get('is_previous', False),
                        'is_next': event.get('is_next', False),
                        'finished': event.get('finished', False),
                        'data_checked': event.get('data_checked', False)
                    },
                    timeout=10
                )
                
            self.logger.debug(f"Updated {len(events)} gameweeks")
            
        except Exception as e:
            self.logger.error(f"Error updating gameweeks: {e}")

    async def update_fixtures_table(self, bootstrap_data):
        """Update fixtures table with fresh FPL data (380 records - safe to refresh frequently)"""
        try:
            fixtures = bootstrap_data.get('fixtures', [])
            if not fixtures:
                return
                
            for fixture in fixtures:
                # Use UPSERT to handle existing data
                response = requests.post(
                    f'{self.supabase_url}/rest/v1/fixtures',
                    headers=self.headers,
                    json={
                        'fpl_id': fixture['id'],
                        'event_id': fixture['event'],
                        'team_h': fixture['team_h'],
                        'team_a': fixture['team_a'],
                        'started': fixture.get('started', False),
                        'finished': fixture.get('finished', False),
                        'kickoff_time': fixture.get('kickoff_time'),
                        'team_h_score': fixture.get('team_h_score'),
                        'team_a_score': fixture.get('team_a_score')
                    },
                    timeout=10
                )
                
            self.logger.debug(f"Updated {len(fixtures)} fixtures")
            
        except Exception as e:
            self.logger.error(f"Error updating fixtures: {e}")

    async def detect_live_matches_fresh(self) -> bool:
        """Check if there are currently live matches using fresh FPL data"""
        try:
            # Use fresh FPL data instead of stale Supabase data
            bootstrap_data = await self.get_fpl_data()
            if not bootstrap_data:
                return False
                
            fixtures = bootstrap_data.get("fixtures", [])
            live_fixtures = [f for f in fixtures if f.get("started", False) and not f.get("finished", False)]
            is_live = len(live_fixtures) > 0
            if is_live:
                self.logger.info(f"Found {len(live_fixtures)} live matches using fresh FPL data")
            return is_live
        except Exception as e:
            self.logger.error(f"Error checking live matches: {e}")
            return False
