from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import logging

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from .models import MouserApiCache


class MouserApiCacheManager:
    """Manages caching for Mouser API responses."""

    def __init__(self):
        pass

    def get_cached_response(
        self,
        search_term: str,
        search_type: str,
        db: Session,
        max_age_seconds: int = 86400,
    ) -> Optional[Dict[str, Any]]:
        """Checks the cache for a recent response for the given term and type.

        Args:
            search_term: The term used in the search (e.g., keyword or MPN).
            search_type: The type of search performed (e.g., 'keyword', 'mpn').
            db: The database session.
            max_age_seconds: The maximum age of the cached entry in seconds.

        Returns:
            The parsed JSON response data if a valid cache entry is found,
            otherwise None.
        """
        logging.debug(
            f"Checking cache for {search_type}='{search_term}', max_age={max_age_seconds}s"
        )
        try:
            oldest_acceptable_timestamp = datetime.now(timezone.utc) - timedelta(
                seconds=max_age_seconds
            )

            result = (
                db.query(MouserApiCache)
                .filter(
                    MouserApiCache.search_term == search_term,
                    MouserApiCache.search_type == search_type,
                    MouserApiCache.cached_at >= oldest_acceptable_timestamp,
                )
                .order_by(MouserApiCache.cached_at.desc())
                .first()
            )

            if result:
                logging.info(
                    f"Cache hit for {search_type}='{search_term}' (cached at {result.cached_at})"
                )
                return result.response_data
            else:
                logging.debug(
                    f"Cache miss for {search_type}='{search_term}' (no recent entry found)"
                )
                return None

        except SQLAlchemyError as e:
            logging.error(
                f"Database error while fetching cache for term '{search_term}' ({search_type}): {e}"
            )
        except Exception as e:
            # Catch any other unexpected errors
            logging.error(
                f"Unexpected error while fetching cache for term '{search_term}' ({search_type}): {e}"
            )

        return None

    def cache_response(
        self,
        search_term: str,
        search_type: str,
        response_data: Dict[str, Any],
        db: Session,
    ) -> None:
        """Saves a Mouser API response to the cache.

        Args:
            search_term: The term used in the search.
            search_type: The type of search performed.
            response_data: The raw JSON response data from the Mouser API.
            db: The database session.
        """
        logging.debug(f"Attempting to cache response for {search_type}='{search_term}'")
        new_cache_entry = MouserApiCache(
            search_term=search_term,
            search_type=search_type,
            response_data=response_data,
            # cached_at is set by database default
        )
        try:
            db.add(new_cache_entry)
            db.commit()
            logging.info(
                f"Cached response for term '{search_term}' ({search_type})"
            )
        except SQLAlchemyError as e:
            logging.error(
                f"Database error caching response for term '{search_term}' ({search_type}): {e}"
            )
            db.rollback()
        except Exception as e:
            logging.error(
                f"Unexpected error caching response for term '{search_term}' ({search_type}): {e}"
            )
            db.rollback() # Rollback on unexpected errors too 