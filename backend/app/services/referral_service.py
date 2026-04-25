import logging
import uuid
from datetime import datetime, timezone

from app.repositories.cosmos_repo import CosmosRepo

logger = logging.getLogger(__name__)

# Reward both referrer and new user with N days of Pro access on a successful referral.
PRO_DAYS_PER_REFERRAL = 3


class ReferralService:
    """
    Handles the referral system logic to grant Pro day rewards.
    """

    def __init__(self):
        self._cosmos = CosmosRepo()

    async def process_referral(self, referrer_code: str, new_user_id: str):
        """
        On signup, credit the referrer (and the new user) with `PRO_DAYS_PER_REFERRAL`
        days of Pro access. No-op if the referrer code can't be resolved.
        """
        if not referrer_code or not new_user_id:
            return

        referrer = await self._cosmos.get_user_by_referral_code(referrer_code)
        if not referrer:
            logger.info(f"Referral code {referrer_code} not found; ignoring.")
            return

        referrer_id = referrer.get("id")
        if not referrer_id or referrer_id == new_user_id:
            return

        granted_at = datetime.now(timezone.utc).isoformat()

        await self._cosmos.upsert_referral_reward(
            {
                "id": f"ref_{uuid.uuid4().hex}",
                "user_id": referrer_id,
                "code": referrer_code,
                "role": "referrer",
                "new_user_id": new_user_id,
                "days": PRO_DAYS_PER_REFERRAL,
                "granted_at": granted_at,
            }
        )
        await self._cosmos.upsert_referral_reward(
            {
                "id": f"ref_{uuid.uuid4().hex}",
                "user_id": new_user_id,
                "code": referrer_code,
                "role": "referee",
                "referrer_id": referrer_id,
                "days": PRO_DAYS_PER_REFERRAL,
                "granted_at": granted_at,
            }
        )
        logger.info(
            f"Referral processed: referrer={referrer_id} new_user={new_user_id} "
            f"days={PRO_DAYS_PER_REFERRAL}"
        )
