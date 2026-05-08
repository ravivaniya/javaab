import os
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from azure.cosmos.aio import CosmosClient
from azure.cosmos.exceptions import (
    CosmosHttpResponseError,
    CosmosResourceNotFoundError,
)

logger = logging.getLogger(__name__)


# Container names — keep consistent with deployed Cosmos DB
CONTAINER_USERS = "users"
CONTAINER_CONVERSATIONS = "conversations"
CONTAINER_MESSAGES = "messages"
CONTAINER_BOOKMARKS = "bookmarks"
CONTAINER_USAGE_LOGS = "usage_logs"
CONTAINER_CACHE_CANDIDATES = "cache_candidates"
CONTAINER_REVIEW_TASKS = "review_tasks"
CONTAINER_FEEDBACK = "feedback"
CONTAINER_PAPERS = "papers"
CONTAINER_WORKSHEETS = "worksheets"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class CosmosRepo:
    """
    Async data-access layer for Azure Cosmos DB.

    Lazy-initialised: if AZURE_COSMOS_ENDPOINT/KEY are missing or the SDK
    raises during connect, every method degrades to a logged no-op so the
    backend keeps running in local/dev mode without Azure credentials.
    """

    def __init__(self):
        self._client: Optional[CosmosClient] = None
        self._db = None
        self._containers: Dict[str, Any] = {}
        self._init_attempted = False
        self._available = False

    def _ensure_clients(self):
        if self._init_attempted:
            return
        self._init_attempted = True

        endpoint = os.getenv("AZURE_COSMOS_ENDPOINT", "")
        key = os.getenv("AZURE_COSMOS_KEY", "")
        db_name = os.getenv("AZURE_COSMOS_DATABASE", "javaab")

        if not endpoint or not key or "example" in endpoint:
            logger.warning(
                "Cosmos DB not configured (AZURE_COSMOS_ENDPOINT/KEY empty). "
                "Repository will run in degraded mode."
            )
            return

        try:
            self._client = CosmosClient(endpoint, credential=key)
            self._db = self._client.get_database_client(db_name)
            for name in (
                CONTAINER_USERS,
                CONTAINER_CONVERSATIONS,
                CONTAINER_MESSAGES,
                CONTAINER_BOOKMARKS,
                CONTAINER_USAGE_LOGS,
                CONTAINER_CACHE_CANDIDATES,
                CONTAINER_REVIEW_TASKS,
                CONTAINER_FEEDBACK,
                CONTAINER_PAPERS,
                CONTAINER_WORKSHEETS,
            ):
                self._containers[name] = self._db.get_container_client(name)
            self._available = True
        except Exception as e:
            logger.error(f"Failed to initialise Cosmos client: {e}")
            self._available = False

    def _container(self, name: str):
        self._ensure_clients()
        if not self._available:
            return None
        return self._containers.get(name)

    async def provision_new_containers(self) -> None:
        """Create papers and worksheets containers if they don't exist yet. Call once at startup."""
        self._ensure_clients()
        if not self._available or not self._db:
            return
        for name, partition_key in (
            (CONTAINER_PAPERS, "/teacher_id"),
            (CONTAINER_WORKSHEETS, "/teacher_id"),
        ):
            try:
                container = await self._db.create_container_if_not_exists(
                    id=name,
                    partition_key={"paths": [partition_key], "kind": "Hash"},
                )
                self._containers[name] = container
                logger.info(f"Cosmos container ready: {name}")
            except Exception as e:
                logger.error(f"Failed to provision container '{name}': {e}")

    # ── User operations ──────────────────────────────────────────────────────

    async def get_user(self, user_id: str) -> dict:
        """Fetch a user document; returns a Free-tier default if not found."""
        default = {
            "id": user_id,
            "tier": "Free",
            "monthly_queries_used": 0,
        }
        container = self._container(CONTAINER_USERS)
        if container is None:
            return default
        try:
            return await container.read_item(item=user_id, partition_key=user_id)
        except CosmosResourceNotFoundError:
            return default
        except CosmosHttpResponseError as e:
            logger.error(f"get_user({user_id}) failed: {e}")
            return default

    async def upsert_user(self, user: dict) -> dict:
        """Create or update a user document. Requires `id`."""
        container = self._container(CONTAINER_USERS)
        if container is None:
            return user
        try:
            user.setdefault("tier", "Free")
            user.setdefault("monthly_queries_used", 0)
            user.setdefault("created_at", _now_iso())
            return await container.upsert_item(body=user)
        except CosmosHttpResponseError as e:
            logger.error(f"upsert_user failed: {e}")
            return user

    async def increment_user_usage(self, user_id: str):
        container = self._container(CONTAINER_USERS)
        if container is None:
            logger.info(f"[degraded] increment_user_usage: {user_id}")
            return
        try:
            await container.patch_item(
                item=user_id,
                partition_key=user_id,
                patch_operations=[{"op": "incr", "path": "/monthly_queries_used", "value": 1}],
            )
        except CosmosResourceNotFoundError:
            await self.upsert_user({"id": user_id, "monthly_queries_used": 1})
        except CosmosHttpResponseError as e:
            logger.error(f"increment_user_usage({user_id}) failed: {e}")

    # ── Conversation operations ───────────────────────────────────────────────

    async def create_conversation(self, conversation_data: dict) -> str:
        """Create a new conversation document. Returns conversation id."""
        conv_id = conversation_data.get("id", "")
        container = self._container(CONTAINER_CONVERSATIONS)
        if container is None:
            logger.info(f"[degraded] create_conversation: {conv_id}")
            return conv_id
        try:
            conversation_data.setdefault("created_at", _now_iso())
            await container.create_item(body=conversation_data)
        except CosmosHttpResponseError as e:
            logger.error(f"create_conversation({conv_id}) failed: {e}")
        return conv_id

    async def save_conversation(self, message_data: dict):
        """
        Persist a message document under its conversation. Despite the legacy
        name, this writes to the messages container — see chat.py.
        """
        container = self._container(CONTAINER_MESSAGES)
        if container is None:
            logger.info(f"[degraded] save_conversation/message: {message_data.get('id')}")
            return
        try:
            message_data.setdefault("created_at", _now_iso())
            await container.upsert_item(body=message_data)
        except CosmosHttpResponseError as e:
            logger.error(f"save_conversation failed: {e}")

    async def get_conversation(self, conversation_id: str) -> Optional[dict]:
        """Fetch a conversation document by id."""
        container = self._container(CONTAINER_CONVERSATIONS)
        if container is None:
            return None
        try:
            query = "SELECT TOP 1 * FROM c WHERE c.id = @id"
            params = [{"name": "@id", "value": conversation_id}]
            async for item in container.query_items(query=query, parameters=params):
                return item
            return None
        except CosmosHttpResponseError as e:
            logger.error(f"get_conversation({conversation_id}) failed: {e}")
            return None

    async def update_conversation_title(self, conversation_id: str, title: str):
        """Update the title field of a conversation."""
        container = self._container(CONTAINER_CONVERSATIONS)
        if container is None:
            logger.info(f"[degraded] update_conversation_title: {conversation_id}")
            return
        try:
            conv = await self.get_conversation(conversation_id)
            if not conv:
                return
            student_id = conv.get("student_id", conversation_id)
            await container.patch_item(
                item=conversation_id,
                partition_key=student_id,
                patch_operations=[
                    {"op": "set", "path": "/title", "value": title[:80]},
                    {"op": "set", "path": "/updated_at", "value": _now_iso()},
                ],
            )
        except CosmosHttpResponseError as e:
            logger.error(f"update_conversation_title failed: {e}")

    async def append_message(self, conversation_id: str, message: dict):
        """Append a message document to the messages container."""
        container = self._container(CONTAINER_MESSAGES)
        if container is None:
            logger.info(f"[degraded] append_message: {message.get('id')}")
            return
        try:
            doc = {**message, "conversation_id": conversation_id}
            doc.setdefault("created_at", _now_iso())
            await container.upsert_item(body=doc)
        except CosmosHttpResponseError as e:
            logger.error(f"append_message failed: {e}")

    async def get_conversation_history(
        self,
        conversation_id: str,
        max_turns: int = 6,
        max_tokens: int = 1500,
    ) -> list:
        """
        Return last N turns from a conversation, oldest→newest, trimmed to fit
        within roughly max_tokens (~4 chars/token heuristic).
        """
        container = self._container(CONTAINER_MESSAGES)
        if container is None:
            return []
        try:
            query = (
                "SELECT TOP @top * FROM c WHERE c.conversation_id = @cid "
                "ORDER BY c.created_at DESC"
            )
            params = [
                {"name": "@cid", "value": conversation_id},
                {"name": "@top", "value": max_turns * 2},
            ]
            rows: List[dict] = []
            async for item in container.query_items(
                query=query,
                parameters=params,
                partition_key=conversation_id,
            ):
                rows.append(item)
            rows.reverse()

            # Build OpenAI-style turn list, expanding query/reply pairs.
            history: List[dict] = []
            for r in rows:
                if r.get("role") and r.get("content") is not None:
                    history.append({"role": r["role"], "content": r["content"]})
                    continue
                if r.get("query"):
                    history.append({"role": "user", "content": r["query"]})
                if r.get("reply"):
                    history.append({"role": "assistant", "content": r["reply"]})

            # Trim to max_tokens using a 4-chars-per-token heuristic, keeping tail.
            char_budget = max_tokens * 4
            total = 0
            trimmed: List[dict] = []
            for turn in reversed(history):
                size = len(turn.get("content", ""))
                if total + size > char_budget and trimmed:
                    break
                total += size
                trimmed.append(turn)
            trimmed.reverse()
            return trimmed
        except CosmosHttpResponseError as e:
            logger.error(f"get_conversation_history failed: {e}")
            return []

    # ── Message operations ────────────────────────────────────────────────────

    async def get_message(self, conversation_id: str, message_id: str) -> Optional[dict]:
        container = self._container(CONTAINER_MESSAGES)
        if container is None:
            return None
        try:
            return await container.read_item(
                item=message_id, partition_key=conversation_id
            )
        except CosmosResourceNotFoundError:
            return None
        except CosmosHttpResponseError as e:
            logger.error(f"get_message failed: {e}")
            return None

    async def update_message(self, conversation_id: str, message_id: str, updates: dict):
        container = self._container(CONTAINER_MESSAGES)
        if container is None:
            logger.info(f"[degraded] update_message: {message_id}")
            return
        try:
            ops = [{"op": "set", "path": f"/{k}", "value": v} for k, v in updates.items()]
            if not ops:
                return
            await container.patch_item(
                item=message_id,
                partition_key=conversation_id,
                patch_operations=ops,
            )
        except CosmosResourceNotFoundError:
            logger.warning(f"update_message: {message_id} not found in {conversation_id}")
        except CosmosHttpResponseError as e:
            logger.error(f"update_message failed: {e}")

    async def delete_messages_after(self, conversation_id: str, message_id: str):
        container = self._container(CONTAINER_MESSAGES)
        if container is None:
            logger.info(f"[degraded] delete_messages_after: {message_id}")
            return
        try:
            anchor = await self.get_message(conversation_id, message_id)
            if not anchor:
                return
            anchor_ts = anchor.get("created_at", "")
            query = (
                "SELECT c.id FROM c WHERE c.conversation_id = @cid "
                "AND c.created_at > @ts"
            )
            params = [
                {"name": "@cid", "value": conversation_id},
                {"name": "@ts", "value": anchor_ts},
            ]
            ids: List[str] = []
            async for item in container.query_items(
                query=query, parameters=params, partition_key=conversation_id
            ):
                ids.append(item["id"])
            for mid in ids:
                try:
                    await container.delete_item(item=mid, partition_key=conversation_id)
                except CosmosHttpResponseError as e:
                    logger.warning(f"delete_messages_after: could not delete {mid}: {e}")
        except CosmosHttpResponseError as e:
            logger.error(f"delete_messages_after failed: {e}")

    # ── Feedback operations ───────────────────────────────────────────────────

    async def save_bookmark(self, bookmark_data: dict):
        container = self._container(CONTAINER_BOOKMARKS)
        if container is None:
            logger.info(f"[degraded] save_bookmark: {bookmark_data.get('message_id')}")
            return
        try:
            user_id = bookmark_data.get("user_id", "anon")
            msg_id = bookmark_data.get("message_id", "")
            doc_id = f"{user_id}:{msg_id}"
            doc = {**bookmark_data, "id": doc_id}
            doc.setdefault("bookmarked_at", _now_iso())
            await container.upsert_item(body=doc)
        except CosmosHttpResponseError as e:
            logger.error(f"save_bookmark failed: {e}")

    async def save_feedback(self, feedback: dict):
        """
        Persist a feedback record (positive/negative + reason) for a message.
        Called by chat.py background-logging path on low-confidence flags.
        """
        container = self._container(CONTAINER_FEEDBACK)
        if container is None:
            logger.info(f"[degraded] save_feedback: {feedback.get('message_id')}")
            return
        try:
            msg_id = feedback.get("message_id", "")
            doc = {**feedback, "id": f"{msg_id}:{_now_iso()}"}
            doc.setdefault("created_at", _now_iso())
            await container.upsert_item(body=doc)
        except CosmosHttpResponseError as e:
            logger.error(f"save_feedback failed: {e}")

    async def flag_message_for_review(self, message_id: str):
        container = self._container(CONTAINER_MESSAGES)
        if container is None:
            logger.info(f"[degraded] flag_message_for_review: {message_id}")
            return
        try:
            query = "SELECT TOP 1 c.id, c.conversation_id FROM c WHERE c.id = @id"
            params = [{"name": "@id", "value": message_id}]
            partition_key = None
            async for item in container.query_items(
                query=query, parameters=params, enable_cross_partition_query=True
            ):
                partition_key = item.get("conversation_id")
                break
            if not partition_key:
                return
            await container.patch_item(
                item=message_id,
                partition_key=partition_key,
                patch_operations=[
                    {"op": "set", "path": "/needs_review", "value": True},
                    {"op": "incr", "path": "/dislike_count", "value": 1},
                ],
            )
        except CosmosHttpResponseError as e:
            logger.error(f"flag_message_for_review failed: {e}")

    async def get_message_dislike_count(self, message_id: str) -> int:
        container = self._container(CONTAINER_MESSAGES)
        if container is None:
            return 0
        try:
            query = "SELECT TOP 1 c.dislike_count FROM c WHERE c.id = @id"
            params = [{"name": "@id", "value": message_id}]
            async for item in container.query_items(
                query=query, parameters=params, enable_cross_partition_query=True
            ):
                return int(item.get("dislike_count") or 0)
            return 0
        except CosmosHttpResponseError as e:
            logger.error(f"get_message_dislike_count failed: {e}")
            return 0

    async def create_auto_review_task(self, message_id: str):
        container = self._container(CONTAINER_REVIEW_TASKS)
        if container is None:
            logger.info(f"[degraded] create_auto_review_task: {message_id}")
            return
        try:
            doc = {
                "id": message_id,
                "message_id": message_id,
                "status": "OPEN",
                "auto_flagged": True,
                "created_at": _now_iso(),
            }
            await container.upsert_item(body=doc)
        except CosmosHttpResponseError as e:
            logger.error(f"create_auto_review_task failed: {e}")

    async def add_to_cache_candidate(self, message_id: str):
        container = self._container(CONTAINER_CACHE_CANDIDATES)
        if container is None:
            logger.info(f"[degraded] add_to_cache_candidate: {message_id}")
            return
        try:
            try:
                await container.patch_item(
                    item=message_id,
                    partition_key=message_id,
                    patch_operations=[{"op": "incr", "path": "/like_count", "value": 1}],
                )
            except CosmosResourceNotFoundError:
                await container.create_item(
                    body={
                        "id": message_id,
                        "message_id": message_id,
                        "like_count": 1,
                        "created_at": _now_iso(),
                    }
                )
        except CosmosHttpResponseError as e:
            logger.error(f"add_to_cache_candidate failed: {e}")

    # ── Usage / analytics ────────────────────────────────────────────────────

    async def log_query_usage(self, usage: dict):
        container = self._container(CONTAINER_USAGE_LOGS)
        if container is None:
            logger.info(f"[degraded] log_query_usage: {usage}")
            return
        try:
            ts = usage.get("timestamp") or _now_iso()
            user_id = usage.get("user_id", "system")
            doc = {**usage, "id": f"{user_id}:{ts}", "timestamp": ts}
            await container.upsert_item(body=doc)
        except CosmosHttpResponseError as e:
            logger.error(f"log_query_usage failed: {e}")

    # ── Papers ────────────────────────────────────────────────────────────────

    async def create_paper(self, paper: dict) -> None:
        """Persist a new paper document. Partition key: teacher_id."""
        container = self._container(CONTAINER_PAPERS)
        if container is None:
            logger.info(f"[degraded] create_paper: {paper.get('id')}")
            return
        try:
            await container.upsert_item(body=paper)
        except CosmosHttpResponseError as e:
            logger.error(f"create_paper failed: {e}")

    async def get_paper(self, paper_id: str, teacher_id: str) -> dict | None:
        container = self._container(CONTAINER_PAPERS)
        if container is None:
            return None
        try:
            item = await container.read_item(item=paper_id, partition_key=teacher_id)
            return item if not item.get("deleted") else None
        except CosmosResourceNotFoundError:
            return None
        except CosmosHttpResponseError as e:
            logger.error(f"get_paper failed: {e}")
            return None

    async def list_papers(self, teacher_id: str) -> list[dict]:
        container = self._container(CONTAINER_PAPERS)
        if container is None:
            return []
        try:
            query = (
                "SELECT * FROM c WHERE c.teacher_id = @tid AND (NOT IS_DEFINED(c.deleted) OR c.deleted = false) "
                "ORDER BY c.created_at DESC"
            )
            items = []
            async for item in container.query_items(
                query=query,
                parameters=[{"name": "@tid", "value": teacher_id}],
            ):
                items.append(item)
            return items
        except CosmosHttpResponseError as e:
            logger.error(f"list_papers failed: {e}")
            return []

    async def update_paper_status(
        self,
        paper_id: str,
        teacher_id: str,
        status: str,
        variants: list | None = None,
        generation_stats: dict | None = None,
    ) -> None:
        container = self._container(CONTAINER_PAPERS)
        if container is None:
            logger.info(f"[degraded] update_paper_status: {paper_id} -> {status}")
            return
        try:
            ops = [
                {"op": "set", "path": "/status", "value": status},
                {"op": "set", "path": "/updated_at", "value": _now_iso()},
            ]
            if variants is not None:
                ops.append({"op": "set", "path": "/variants", "value": variants})
            if generation_stats is not None:
                ops.append({"op": "set", "path": "/generation_stats", "value": generation_stats})
            await container.patch_item(
                item=paper_id,
                partition_key=teacher_id,
                patch_operations=ops,
            )
        except CosmosHttpResponseError as e:
            logger.error(f"update_paper_status failed: {e}")

    async def soft_delete_paper(self, paper_id: str, teacher_id: str) -> None:
        container = self._container(CONTAINER_PAPERS)
        if container is None:
            return
        try:
            await container.patch_item(
                item=paper_id,
                partition_key=teacher_id,
                patch_operations=[{"op": "set", "path": "/deleted", "value": True}],
            )
        except CosmosHttpResponseError as e:
            logger.error(f"soft_delete_paper failed: {e}")

    # ── Worksheets ────────────────────────────────────────────────────────────

    async def create_worksheet(self, ws: dict) -> None:
        """Persist a new worksheet document. Partition key: teacher_id."""
        container = self._container(CONTAINER_WORKSHEETS)
        if container is None:
            logger.info(f"[degraded] create_worksheet: {ws.get('id')}")
            return
        try:
            await container.upsert_item(body=ws)
        except CosmosHttpResponseError as e:
            logger.error(f"create_worksheet failed: {e}")

    async def get_worksheet(self, ws_id: str, teacher_id: str) -> dict | None:
        container = self._container(CONTAINER_WORKSHEETS)
        if container is None:
            return None
        try:
            item = await container.read_item(item=ws_id, partition_key=teacher_id)
            return item if not item.get("deleted") else None
        except CosmosResourceNotFoundError:
            return None
        except CosmosHttpResponseError as e:
            logger.error(f"get_worksheet failed: {e}")
            return None

    async def list_worksheets(self, teacher_id: str) -> list[dict]:
        container = self._container(CONTAINER_WORKSHEETS)
        if container is None:
            return []
        try:
            query = (
                "SELECT * FROM c WHERE c.teacher_id = @tid AND (NOT IS_DEFINED(c.deleted) OR c.deleted = false) "
                "ORDER BY c.created_at DESC"
            )
            items = []
            async for item in container.query_items(
                query=query,
                parameters=[{"name": "@tid", "value": teacher_id}],
            ):
                items.append(item)
            return items
        except CosmosHttpResponseError as e:
            logger.error(f"list_worksheets failed: {e}")
            return []

    async def update_worksheet_status(
        self,
        ws_id: str,
        teacher_id: str,
        status: str,
        data: dict | None = None,
    ) -> None:
        container = self._container(CONTAINER_WORKSHEETS)
        if container is None:
            logger.info(f"[degraded] update_worksheet_status: {ws_id} -> {status}")
            return
        try:
            ops = [
                {"op": "set", "path": "/status", "value": status},
                {"op": "set", "path": "/updated_at", "value": _now_iso()},
            ]
            if data:
                for key, value in data.items():
                    ops.append({"op": "set", "path": f"/{key}", "value": value})
            await container.patch_item(
                item=ws_id,
                partition_key=teacher_id,
                patch_operations=ops,
            )
        except CosmosHttpResponseError as e:
            logger.error(f"update_worksheet_status failed: {e}")

    async def soft_delete_worksheet(self, ws_id: str, teacher_id: str) -> None:
        container = self._container(CONTAINER_WORKSHEETS)
        if container is None:
            return
        try:
            await container.patch_item(
                item=ws_id,
                partition_key=teacher_id,
                patch_operations=[{"op": "set", "path": "/deleted", "value": True}],
            )
        except CosmosHttpResponseError as e:
            logger.error(f"soft_delete_worksheet failed: {e}")
