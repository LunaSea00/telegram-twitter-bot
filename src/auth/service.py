import logging

logger = logging.getLogger(__name__)

class AuthService:
    def __init__(self, authorized_user_id: str):
        self.authorized_user_id = authorized_user_id
    
    def is_authorized(self, user_id: int) -> bool:
        is_auth = str(user_id) == self.authorized_user_id
        if not is_auth:
            logger.warning(f"Unauthorized access attempt from user ID: {user_id}")
        return is_auth