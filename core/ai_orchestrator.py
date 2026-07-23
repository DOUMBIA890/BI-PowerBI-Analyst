# core/ai_orchestrator.py
import json
import os
from pathlib import Path
from openai import OpenAI
import httpx

# Charge les variables d'environnement depuis .env (clés API, etc.)
# Streamlit ne charge pas .env automatiquement pour os.getenv.
try:
    from dotenv import load_dotenv
    _env_path = Path(__file__).resolve().parent.parent / ".env"
    load_dotenv(_env_path)
except Exception:
    # python-dotenv indisponible : on continue, les vars d'env système
    # (ex. TENCENT_API_KEY exportée) restent utilisables.
    pass

class AIOrchestrator:
    def __init__(self, config_path="config/settings.json"):
        with open(config_path, "r") as f:
            self.config = json.load(f)
        self.providers = self.config["ai_providers"]
        self.routing = self.config["routing_rules"]
        self.clients = {}

    def _get_client(self, provider_name):
        if provider_name not in self.clients:
            provider_cfg = self.providers[provider_name]
            # Récupère la clé depuis les variables d'environnement
            api_key = os.getenv(provider_cfg.get("env_key", ""), provider_cfg.get("api_key", ""))
            request_timeout = provider_cfg.get("timeout", 180)
            # Transport HTTP/1 explicite : le client httpx par défaut tente du
            # HTTP/2 et échoue sur certains réseaux (Connection error).
            http_client = httpx.Client(
                timeout=request_timeout,
                transport=httpx.HTTPTransport(retries=2),
            )
            self.clients[provider_name] = OpenAI(
                api_key=api_key,
                base_url=provider_cfg["api_base"],
                timeout=request_timeout,
                http_client=http_client,
            )
        return self.clients[provider_name]

    def generate(self, prompt: str, task_type: str = "default", **kwargs) -> str:
        rule = self.routing.get(task_type, self.routing["default"])
        provider = rule["provider"]
        model_name = rule["model"]

        provider_cfg = self.providers[provider]
        model_cfg = provider_cfg["models"][model_name]

        client = self._get_client(provider)

        params = {
            "model": model_cfg["model_id"],
            "max_tokens": model_cfg.get("max_tokens", 4096),
            "temperature": model_cfg.get("temperature", 0.7),
            "timeout": provider_cfg.get("timeout", 180),
        }
        params.update(kwargs)

        messages = [{"role": "user", "content": prompt}]
        response = client.chat.completions.create(messages=messages, **params)
        return response.choices[0].message.content.strip()

# Singleton
orchestrator = AIOrchestrator()