"""
Valora Database Module
SpatiaLite-based spatial database for properties, POIs, and urban data
"""

from .db_service import DatabaseService, get_db_service
from .query_service import DatabaseQueryService, get_query_service
from .community_pulse_schema import (
    CommunityPulseDB,
    get_community_pulse_db,
    init_community_pulse_tables,
    create_family_session,
    get_family_session,
    get_user_family_sessions,
    update_family_session,
    delete_family_session,
    add_family_member,
    get_family_members,
    update_family_member,
    remove_family_member,
    add_to_watchlist,
    get_watchlist,
    update_watchlist_entry,
    remove_from_watchlist,
    cast_vote,
    get_votes_for_property,
    get_vote_summary,
    delete_vote,
    add_timeline_event,
    get_timeline_events,
    get_session_statistics,
)

__all__ = [
    'DatabaseService',
    'get_db_service',
    'DatabaseQueryService',
    'get_query_service',
    # Community Pulse
    'CommunityPulseDB',
    'get_community_pulse_db',
    'init_community_pulse_tables',
    'create_family_session',
    'get_family_session',
    'get_user_family_sessions',
    'update_family_session',
    'delete_family_session',
    'add_family_member',
    'get_family_members',
    'update_family_member',
    'remove_family_member',
    'add_to_watchlist',
    'get_watchlist',
    'update_watchlist_entry',
    'remove_from_watchlist',
    'cast_vote',
    'get_votes_for_property',
    'get_vote_summary',
    'delete_vote',
    'add_timeline_event',
    'get_timeline_events',
    'get_session_statistics',
]

__version__ = '2.1.0'
