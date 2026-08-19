import os
import logging
import threading
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from ..models.case import CaseModel, CaseStatus
from ..config import get_settings
from ..observability.tracer import trace_span

logger = logging.getLogger("subrogate.firestore")


class ConcurrencyConflictError(Exception):
    """Raised when an optimistic concurrency version check fails."""
    pass


class CaseNotFoundError(Exception):
    """Raised when a requested case does not exist in Firestore."""
    pass


class FirestoreCaseRepository:
    """
    Persistent Case Repository with Firestore integration and optimistic concurrency control.
    Supports Google Cloud Firestore in production and provides an in-memory thread-safe store for local testing.
    """

    COLLECTION_NAME = "subrogate_cases"
    _global_memory_store: Dict[str, Dict[str, Any]] = {}
    _global_lock = threading.RLock()

    def __init__(self):
        self.settings = get_settings()
        self._firestore_client = None
        self._memory_store = self._global_memory_store
        self._lock = self._global_lock
        self._initialize_client()

    def _initialize_client(self) -> None:
        """Attempts connection to Google Cloud Firestore if credentials/project are configured."""
        gcp_project = self.settings.GOOGLE_CLOUD_PROJECT or os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCP_PROJECT")
        is_cloud_env = bool(gcp_project or os.getenv("K_SERVICE") or os.getenv("GOOGLE_APPLICATION_CREDENTIALS"))

        if is_cloud_env:
            try:
                from google.cloud import firestore
                if gcp_project:
                    self._firestore_client = firestore.Client(project=gcp_project)
                else:
                    self._firestore_client = firestore.Client()
                logger.info(f"Initialized Google Cloud Firestore repository (project: '{self._firestore_client.project}', collection: '{self.COLLECTION_NAME}')")
                return
            except Exception as e:
                logger.warning(f"Failed to initialize live Firestore client: {e}. Operating in resilient local mode.")
                self._firestore_client = None
        
        logger.info(f"FirestoreCaseRepository operating in resilient memory mode.")

    @property
    def is_cloud_connected(self) -> bool:
        return self._firestore_client is not None

    def save(self, case: CaseModel) -> CaseModel:
        """
        Saves a new case or overwrites an existing case record.
        """
        with trace_span("Firestore Case Persistence", case_id=case.case_id, category="DATABASE"):
            case.updated_at_utc = datetime.now(timezone.utc)
            data = case.model_dump(mode="json")

            if self._firestore_client:
                try:
                    doc_ref = self._firestore_client.collection(self.COLLECTION_NAME).document(case.case_id)
                    doc_ref.set(data)
                    logger.info(f"Persisted case '{case.case_id}' (v{case.version}) to Firestore.")
                    return case
                except Exception as e:
                    logger.error(f"Firestore save failed: {e}. Fallback to memory store.")

            with self._lock:
                self._memory_store[case.case_id] = data

            return case

    def get(self, case_id: str) -> Optional[CaseModel]:
        """
        Retrieves a case by ID from Firestore (or fallback store).
        """
        with trace_span("Firestore Case Query", case_id=case_id, category="DATABASE"):
            if self._firestore_client:
                try:
                    doc_ref = self._firestore_client.collection(self.COLLECTION_NAME).document(case_id)
                    snap = doc_ref.get()
                    if snap.exists:
                        return CaseModel.model_validate(snap.to_dict())
                    return None
                except Exception as e:
                    logger.error(f"Firestore get failed: {e}. Checking memory fallback.")

            with self._lock:
                data = self._memory_store.get(case_id)
                if data:
                    return CaseModel.model_validate(data)
                return None

    def list_cases(self, limit: int = 50, status: Optional[CaseStatus] = None) -> List[CaseModel]:
        """
        Lists recent cases, optionally filtered by status.
        """
        with trace_span("Firestore Case Listing", category="DATABASE", attributes={"limit": limit, "status": status.value if status else None}):
            if self._firestore_client:
                try:
                    col_ref = self._firestore_client.collection(self.COLLECTION_NAME)
                    query = col_ref
                    if status:
                        query = query.where("status", "==", status.value)
                    query = query.order_by("updated_at_utc", direction="DESCENDING").limit(limit)
                    docs = query.stream()
                    return [CaseModel.model_validate(doc.to_dict()) for doc in docs]
                except Exception as e:
                    logger.warning(f"Firestore list failed or unindexed: {e}. Falling back to memory scan.")

            with self._lock:
                cases = [CaseModel.model_validate(d) for d in self._memory_store.values()]
                if status:
                    cases = [c for c in cases if c.status == status]
                cases.sort(key=lambda x: x.updated_at_utc or x.created_at_utc, reverse=True)
                return cases[:limit]

    def update(
        self,
        case_id: str,
        updates: Dict[str, Any],
        expected_version: Optional[int] = None
    ) -> CaseModel:
        """
        Applies updates to a case with optimistic concurrency version control.
        """
        with trace_span("Firestore Case Update", case_id=case_id, category="DATABASE", attributes={"expected_version": expected_version}):
            if self._firestore_client:
                try:
                    from google.cloud import firestore

                    @firestore.transactional
                    def _update_in_transaction(transaction, doc_ref):
                        snapshot = doc_ref.get(transaction=transaction)
                        if not snapshot.exists:
                            raise CaseNotFoundError(f"Case '{case_id}' does not exist in Firestore.")
                        
                        current_data = snapshot.to_dict()
                        curr_ver = current_data.get("version", 1)
                        if expected_version is not None and curr_ver != expected_version:
                            raise ConcurrencyConflictError(
                                f"Optimistic concurrency conflict on case '{case_id}': expected version {expected_version}, found {curr_ver}."
                            )

                        current_data.update(updates)
                        current_data["version"] = curr_ver + 1
                        current_data["updated_at_utc"] = datetime.now(timezone.utc).isoformat()

                        transaction.set(doc_ref, current_data)
                        return CaseModel.model_validate(current_data)

                    doc_ref = self._firestore_client.collection(self.COLLECTION_NAME).document(case_id)
                    tx = self._firestore_client.transaction()
                    return _update_in_transaction(tx, doc_ref)
                except (CaseNotFoundError, ConcurrencyConflictError):
                    raise
                except Exception as e:
                    logger.error(f"Firestore transaction update failed: {e}. Falling back to memory update.")

            with self._lock:
                if case_id not in self._memory_store:
                    raise CaseNotFoundError(f"Case '{case_id}' not found.")

                current_data = self._memory_store[case_id]
                curr_ver = current_data.get("version", 1)

                if expected_version is not None and curr_ver != expected_version:
                    raise ConcurrencyConflictError(
                        f"Optimistic concurrency conflict on case '{case_id}': expected version {expected_version}, found {curr_ver}."
                    )

                current_data.update(updates)
                current_data["version"] = curr_ver + 1
                current_data["updated_at_utc"] = datetime.now(timezone.utc).isoformat()
                self._memory_store[case_id] = current_data

                return CaseModel.model_validate(current_data)

    def delete(self, case_id: str) -> bool:
        """Deletes a case record."""
        with trace_span("Firestore Case Deletion", case_id=case_id, category="DATABASE"):
            if self._firestore_client:
                try:
                    self._firestore_client.collection(self.COLLECTION_NAME).document(case_id).delete()
                except Exception as e:
                    logger.error(f"Firestore delete failed: {e}")

            with self._lock:
                if case_id in self._memory_store:
                    del self._memory_store[case_id]
                    return True
                return False

    def clear(self) -> None:
        """Clears all records (used for test isolation)."""
        with self._lock:
            self._memory_store.clear()
