import os
import json
import logging
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from ..config import get_settings

logger = logging.getLogger("subrogate.agents")

class AgentExecutionResult(BaseModel):
    """Encapsulates the structured output and audit trail of an agent run."""
    agent_name: str
    model_used: str
    success: bool
    output: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    execution_time_ms: float = 0.0

class BaseForensicAgent:
    """
    Google ADK & Vertex AI / GenAI compatible agent foundation.
    Encapsulates tool definitions, structured prompt execution,
    and deterministic fallback handling.
    """
    def __init__(self, agent_name: str = "BaseForensicAgent"):
        self.agent_name = agent_name
        self.settings = get_settings()
        self.model_name = self.settings.SUBROGATE_GEMINI_MODEL
        self._client = None
        self._initialize_client()

    def _initialize_client(self) -> None:
        """Initializes the official google-genai client with Vertex AI or AI Studio."""
        if self.settings.GEMINI_API_KEY:
            try:
                from google import genai
                self._client = genai.Client(api_key=self.settings.GEMINI_API_KEY)
                logger.info(f"Initialized agent '{self.agent_name}' with model '{self.model_name}' (AI Studio)")
                return
            except Exception as e:
                logger.warning(f"Failed to initialize google-genai AI Studio client: {e}. Checking Vertex AI.")

        gcp_project = self.settings.GOOGLE_CLOUD_PROJECT or os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCP_PROJECT")
        is_cloud_env = bool(gcp_project or os.getenv("K_SERVICE") or os.getenv("GOOGLE_APPLICATION_CREDENTIALS"))

        if is_cloud_env:
            try:
                from google import genai
                if gcp_project:
                    self._client = genai.Client(
                        vertexai=True,
                        project=gcp_project,
                        location=self.settings.GOOGLE_CLOUD_LOCATION
                    )
                else:
                    self._client = genai.Client(vertexai=True, location=self.settings.GOOGLE_CLOUD_LOCATION)
                logger.info(f"Initialized Vertex AI agent '{self.agent_name}' with model '{self.model_name}' (Vertex AI / ADK)")
                return
            except Exception as e:
                logger.warning(f"Failed to initialize Vertex AI client: {e}. Fallback enabled.")
                self._client = None
        
        logger.info(f"Agent '{self.agent_name}' operating in offline deterministic mode.")

    @property
    def is_online(self) -> bool:
        return self._client is not None

    def execute_structured(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        image_bytes: Optional[bytes] = None,
        mime_type: str = "image/jpeg"
    ) -> Optional[Dict[str, Any]]:
        """
        Executes a prompt expecting structured JSON response.
        Compatible with Google ADK tool schemas and response structures.
        """
        if not self.is_online:
            return None

        try:
            from google.genai import types

            contents: List[Any] = []
            if image_bytes:
                contents.append(types.Part.from_bytes(data=image_bytes, mime_type=mime_type))
            contents.append(prompt)

            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.1
            )
            if system_instruction:
                config.system_instruction = system_instruction

            response = self._client.models.generate_content(
                model=self.model_name,
                contents=contents,
                config=config
            )

            if response and response.text:
                return json.loads(response.text)
        except Exception as e:
            logger.error(f"Agent execution error on '{self.agent_name}': {e}")
            return None

    def execute_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None
    ) -> Optional[str]:
        """Executes a prompt expecting raw text (e.g. rebuttal letter drafting)."""
        if not self.is_online:
            return None

        try:
            from google.genai import types

            config = types.GenerateContentConfig(
                temperature=0.2
            )
            if system_instruction:
                config.system_instruction = system_instruction

            response = self._client.models.generate_content(
                model=self.model_name,
                contents=[prompt],
                config=config
            )

            if response and response.text:
                return response.text
        except Exception as e:
            logger.error(f"Agent text execution error on '{self.agent_name}': {e}")
            return None
