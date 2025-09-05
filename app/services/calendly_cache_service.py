# app/services/calendly_cache_service.py (FIXED VERSION)
"""
Calendly Cache Service - FIXED to handle data type issues from CalendlyService
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from sqlalchemy import and_, or_, func
from app.models import db
from app.models.calendly_event import CalendlyEvent, CalendlySyncLog
from app.services.calendly_service import CalendlyService
import logging
import json

logger = logging.getLogger(__name__)

class CalendlyCacheService:
    """Service for managing cached Calendly data with intelligent fetching"""
    
    def __init__(self):
        self.calendly_service = CalendlyService()
        self.max_api_batch_size = 100  # Calendly API limit
        self.cache_expiry_hours = 24  # How long to consider cache fresh
    
    def _upsert_event(self, event_data) -> str:
        """
        Insert or update a Calendly event in the database - FIXED to handle string data
        
        Returns:
            'created', 'updated', or 'skipped'
        """
        try:
            # FIXED: Handle case where event_data might be a string
            if isinstance(event_data, str):
                logger.warning(f"Received string event data: {event_data[:100]}...")
                try:
                    event_data = json.loads(event_data)
                except json.JSONDecodeError:
                    logger.error(f"Cannot parse string as JSON: {event_data}")
                    return 'skipped'
            
            if not isinstance(event_data, dict):
                logger.error(f"Event data is not a dictionary: {type(event_data)}")
                return 'skipped'
            
            # Extract event ID
            calendly_uri = event_data.get('uri', '')
            calendly_event_id = calendly_uri.split('/')[-1] if calendly_uri else None
            
            if not calendly_event_id:
                logger.warning("No event ID found, skipping")
                return 'skipped'
            
            # Check if event already exists
            existing_event = db.session.query(CalendlyEvent).filter_by(
                calendly_event_id=calendly_event_id
            ).first()
            
            if existing_event:
                # Update if the event has been modified
                event_updated_at = event_data.get('updated_at')
                if event_updated_at:
                    try:
                        updated_at = datetime.fromisoformat(event_updated_at.replace('Z', '+00:00')).replace(tzinfo=None)
                        if existing_event.updated_at_calendly and updated_at <= existing_event.updated_at_calendly:
                            return 'skipped'  # No changes
                    except (ValueError, TypeError):
                        pass  # Continue with update if date parsing fails
                
                # Update existing event
                self._update_event_from_data(existing_event, event_data)
                db.session.commit()
                return 'updated'
            else:
                # Create new event
                new_event = CalendlyEvent.create_from_calendly_data(event_data)
                db.session.add(new_event)
                db.session.commit()
                return 'created'
                
        except Exception as e:
            logger.error(f"Error upserting event: {e}")
            logger.error(f"Event data type: {type(event_data)}")
            logger.error(f"Event data preview: {str(event_data)[:200]}...")
            db.session.rollback()
            return 'skipped'
    
    def _sync_events_for_range(self, start_date: datetime, end_date: datetime, 
                              sync_type: str = 'incremental', user_email: str = None, 
                              team_id: int = None) -> Dict:
        """
        Sync events for a specific date range - FIXED to handle API response format
        """
        sync_log = CalendlySyncLog(
            sync_type=sync_type,
            start_date=start_date,
            end_date=end_date,
            user_email=user_email,
            team_id=team_id,
            status='running'
        )
        db.session.add(sync_log)
        db.session.commit()
        
        try:
            logger.info(f"Starting {sync_type} sync for {start_date} to {end_date}")
            
            # Fetch events from Calendly API in batches
            all_events = []
            api_calls = 0
            
            # Split large date ranges into smaller chunks to avoid API limits
            current_start = start_date
            chunk_size = timedelta(days=30)  # Process 30 days at a time
            
            while current_start < end_date:
                current_end = min(current_start + chunk_size, end_date)
                
                try:
                    if user_email:
                        # FIXED: Handle the return format from get_events_for_user_email
                        events = self.calendly_service.get_events_for_user_email(
                            user_email, current_start, current_end
                        )
                        
                        # The method returns a list directly, not a response with 'collection'
                        if isinstance(events, list):
                            all_events.extend(events)
                        elif isinstance(events, dict) and 'collection' in events:
                            all_events.extend(events['collection'])
                        else:
                            logger.warning(f"Unexpected events format from get_events_for_user_email: {type(events)}")
                            
                    else:
                        events_response = self.calendly_service.get_scheduled_events(
                            current_start, current_end, count=self.max_api_batch_size
                        )
                        events = events_response.get('collection', []) if events_response else []
                        all_events.extend(events)
                    
                    api_calls += 1
                    
                    logger.info(f"Fetched {len(events)} events for {current_start} to {current_end}")
                    
                except Exception as e:
                    logger.error(f"Error fetching events for chunk {current_start} to {current_end}: {e}")
                    continue
                
                current_start = current_end
            
            # Process and cache events
            events_created = 0
            events_updated = 0
            events_skipped = 0
            
            logger.info(f"Processing {len(all_events)} events for caching...")
            
            for i, event_data in enumerate(all_events):
                try:
                    # Debug log for first few events
                    if i < 3:
                        logger.info(f"Event {i} type: {type(event_data)}, preview: {str(event_data)[:100]}...")
                    
                    result = self._upsert_event(event_data)
                    if result == 'created':
                        events_created += 1
                    elif result == 'updated':
                        events_updated += 1
                    else:
                        events_skipped += 1
                        
                except Exception as e:
                    logger.error(f"Error processing event {i}: {e}")
                    events_skipped += 1
                    continue
            
            # Update sync log
            sync_log.status = 'completed'
            sync_log.completed_at = datetime.utcnow()
            sync_log.duration_seconds = (sync_log.completed_at - sync_log.started_at).total_seconds()
            sync_log.events_fetched = len(all_events)
            sync_log.events_created = events_created
            sync_log.events_updated = events_updated
            sync_log.events_skipped = events_skipped
            sync_log.api_calls_made = api_calls
            
            db.session.commit()
            
            logger.info(f"Sync completed: {events_created} created, {events_updated} updated, {events_skipped} skipped")
            
            return {
                'success': True,
                'events_fetched': len(all_events),
                'events_created': events_created,
                'events_updated': events_updated,
                'events_skipped': events_skipped,
                'api_calls_made': api_calls,
                'duration_seconds': sync_log.duration_seconds
            }
            
        except Exception as e:
            # Update sync log with error
            sync_log.status = 'failed'
            sync_log.completed_at = datetime.utcnow()
            sync_log.error_message = str(e)
            db.session.commit()
            
            logger.error(f"Sync failed: {e}")
            raise
    
    # ... (keep all the other existing methods from the original cache service)
    
    def get_events_for_date_range(self, start_date: datetime, end_date: datetime, 
                                 user_email: str = None, team_id: int = None) -> List[Dict]:
        """
        Get events for date range, using cache when possible and fetching missing data from API
        """
        try:
            logger.info(f"Getting Calendly events for {start_date} to {end_date}")
            
            # Check what data we have in cache
            cached_events = self._get_cached_events(start_date, end_date, user_email)
            
            # Determine if we need to fetch from API
            missing_ranges = self._find_missing_date_ranges(start_date, end_date, user_email)
            
            if missing_ranges:
                logger.info(f"Found {len(missing_ranges)} missing date ranges, fetching from API")
                self._fetch_and_cache_missing_data(missing_ranges, user_email, team_id)
                # Re-fetch cached events after API sync
                cached_events = self._get_cached_events(start_date, end_date, user_email)
            
            logger.info(f"Returning {len(cached_events)} cached events")
            return [event.to_dict() for event in cached_events]
            
        except Exception as e:
            logger.error(f"Error getting events for date range: {e}")
            # Fallback to direct API call if cache fails
            return self._fallback_to_api(start_date, end_date, user_email)
    
    def _get_cached_events(self, start_date: datetime, end_date: datetime, 
                          user_email: str = None) -> List[CalendlyEvent]:
        """Get cached events for date range"""
        query = db.session.query(CalendlyEvent).filter(
            and_(
                CalendlyEvent.start_time >= start_date,
                CalendlyEvent.start_time <= end_date
            )
        ).order_by(CalendlyEvent.start_time)
        
        if user_email:
            query = query.filter(CalendlyEvent.host_email == user_email)
        
        return query.all()
    
    def _find_missing_date_ranges(self, start_date: datetime, end_date: datetime, 
                                 user_email: str = None) -> List[Tuple[datetime, datetime]]:
        """Find date ranges that are not covered by recent successful syncs"""
        try:
            # Check for successful syncs that cover this range
            sync_query = db.session.query(CalendlySyncLog).filter(
                and_(
                    CalendlySyncLog.status == 'completed',
                    CalendlySyncLog.start_date <= start_date,
                    CalendlySyncLog.end_date >= end_date,
                    CalendlySyncLog.completed_at >= datetime.utcnow() - timedelta(hours=self.cache_expiry_hours)
                )
            )
            
            if user_email:
                sync_query = sync_query.filter(
                    or_(
                        CalendlySyncLog.user_email == user_email,
                        CalendlySyncLog.user_email.is_(None)  # Full syncs cover all users
                    )
                )
            
            recent_sync = sync_query.first()
            
            if recent_sync:
                return []  # Range is covered by recent sync
            else:
                return [(start_date, end_date)]  # Need to sync this range
                
        except Exception as e:
            logger.error(f"Error finding missing date ranges: {e}")
            return [(start_date, end_date)]  # Assume we need to sync
    
    def _fetch_and_cache_missing_data(self, missing_ranges: List[Tuple[datetime, datetime]], 
                                     user_email: str = None, team_id: int = None):
        """Fetch missing data from Calendly API and cache it"""
        for start_date, end_date in missing_ranges:
            try:
                self._sync_events_for_range(start_date, end_date, 
                                          sync_type='incremental', 
                                          user_email=user_email, 
                                          team_id=team_id)
            except Exception as e:
                logger.error(f"Error fetching missing data for {start_date} to {end_date}: {e}")
                continue
    
    def get_cache_status(self, start_date: datetime, end_date: datetime) -> Dict:
        """Get status of cached data for a date range"""
        try:
            # Count cached events in range
            cached_count = db.session.query(CalendlyEvent).filter(
                and_(
                    CalendlyEvent.start_time >= start_date,
                    CalendlyEvent.start_time <= end_date
                )
            ).count()
            
            # Find latest sync for this range
            latest_sync = db.session.query(CalendlySyncLog).filter(
                and_(
                    CalendlySyncLog.start_date <= start_date,
                    CalendlySyncLog.end_date >= end_date,
                    CalendlySyncLog.status == 'completed'
                )
            ).order_by(CalendlySyncLog.completed_at.desc()).first()
            
            # Check freshness
            is_fresh = False
            hours_since_sync = None
            if latest_sync and latest_sync.completed_at:
                hours_since_sync = (datetime.utcnow() - latest_sync.completed_at).total_seconds() / 3600
                is_fresh = hours_since_sync < self.cache_expiry_hours
            
            missing_ranges = self._find_missing_date_ranges(start_date, end_date)
            
            return {
                'cached_events_count': cached_count,
                'has_recent_sync': latest_sync is not None,
                'hours_since_last_sync': hours_since_sync,
                'is_fresh': is_fresh,
                'missing_ranges_count': len(missing_ranges),
                'needs_sync': bool(missing_ranges) or not is_fresh,
                'latest_sync': latest_sync.to_dict() if latest_sync else None
            }
            
        except Exception as e:
            logger.error(f"Error getting cache status: {e}")
            return {
                'error': str(e),
                'needs_sync': True
            }
    
    def _fallback_to_api(self, start_date: datetime, end_date: datetime, 
                        user_email: str = None) -> List[Dict]:
        """Fallback to direct API call if cache fails completely"""
        try:
            logger.warning("Falling back to direct API call due to cache failure")
            
            if user_email:
                events = self.calendly_service.get_events_for_user_email(
                    user_email, start_date, end_date
                )
                # Convert events to dict format if they're not already
                if isinstance(events, list):
                    return [event if isinstance(event, dict) else {} for event in events]
                return []
            else:
                events_response = self.calendly_service.get_scheduled_events(
                    start_date, end_date, count=self.max_api_batch_size
                )
                if events_response and 'collection' in events_response:
                    return events_response['collection']
                return []
                
        except Exception as e:
            logger.error(f"Fallback API call also failed: {e}")
            return []
    
    def _update_event_from_data(self, event: CalendlyEvent, event_data: Dict):
        """Update existing CalendlyEvent with new data"""
        try:
            # Update basic fields
            event.name = event_data.get('name')
            event.status = event_data.get('status')
            
            # Update dates
            if event_data.get('start_time'):
                event.start_time = datetime.fromisoformat(event_data['start_time'].replace('Z', '+00:00')).replace(tzinfo=None)
            if event_data.get('end_time'):
                event.end_time = datetime.fromisoformat(event_data['end_time'].replace('Z', '+00:00')).replace(tzinfo=None)
            if event_data.get('updated_at'):
                event.updated_at_calendly = datetime.fromisoformat(event_data['updated_at'].replace('Z', '+00:00')).replace(tzinfo=None)
            
            # Update location
            location = event_data.get('location', {})
            if location:
                event.location_type = location.get('type')
                event.location_value = location.get('location')
            
            # Update meeting notes
            event.meeting_notes_plain = event_data.get('meeting_notes_plain')
            event.meeting_notes_html = event_data.get('meeting_notes_html')
            
            # Update raw data and sync timestamp
            event.raw_data = event_data
            event.last_synced = datetime.utcnow()
            
        except Exception as e:
            logger.error(f"Error updating event from data: {e}")
            raise