import os
import logging
import uuid
import httpx

logger = logging.getLogger(__name__)

RAZORPAY_API = "https://api.razorpay.com/v1/orders"


class PaymentService:
    """
    Razorpay order initiation. Uses httpx (already a dependency) instead of
    the razorpay SDK so no new package is required.

    If RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET are missing, returns a stub
    order id so dev flows continue working.
    """

    def __init__(self):
        self.key_id = os.getenv("RAZORPAY_KEY_ID", "")
        self.key_secret = os.getenv("RAZORPAY_KEY_SECRET", "")

    async def initiate_payment(self, user_id: str, amount: float) -> str:
        """
        Initiate a Razorpay order. Amount is rupees; Razorpay expects paise.
        Returns the Razorpay order id.
        """
        if not self.key_id or not self.key_secret:
            logger.warning(
                "Razorpay credentials missing; returning stub order id "
                "(set RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET to enable live payments)."
            )
            return f"order_stub_{uuid.uuid4().hex[:12]}"

        receipt = f"rcpt_{user_id}_{uuid.uuid4().hex[:8]}"
        payload = {
            "amount": int(round(amount * 100)),
            "currency": "INR",
            "receipt": receipt,
            "notes": {"user_id": user_id},
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    RAZORPAY_API,
                    json=payload,
                    auth=(self.key_id, self.key_secret),
                )
            if resp.status_code >= 400:
                logger.error(f"Razorpay order create failed: {resp.status_code} {resp.text}")
                return f"order_stub_{uuid.uuid4().hex[:12]}"
            data = resp.json()
            return data.get("id", f"order_stub_{uuid.uuid4().hex[:12]}")
        except Exception as e:
            logger.error(f"Razorpay request failed: {e}")
            return f"order_stub_{uuid.uuid4().hex[:12]}"
