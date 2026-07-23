import os
import time
import requests
from typing import Dict, Any

class ClawRouterClient:
    def __init__(self, agent_id: str, default_task_type: str = "standard"):
        self.agent_id = agent_id
        self.default_task_type = default_task_type
        # Resolves dynamic endpoint target via our local Infisical/Cloudflare edge proxy settings
        self.gateway_url = os.getenv("CF_GATEWAY_URL", "http://127.0.0.1:8787")

    def _determine_task_type(self, prompt: str) -> str:
        """
        Dynamically analyzes the payload input string to select the correct performance tier,
        minimizing financial token burn on low-priority cycles.
        """
        prompt_lower = prompt.lower()
        if any(marker in prompt_lower for marker in ["heartbeat", "keepalive", "ping", "healthz"]):
            return "heartbeat"
        if any(marker in prompt_lower for marker in ["compile", "refactor", "engineer", "terraform", "cloudbuild"]):
            return "critical-engineering"
        return self.default_task_type

    def execute_inference(self, prompt: str, model_fallback_tier: str = "balanced") -> Dict[str, Any]:
        """
        Transmits tracking metadata directly to the Cloudflare AI Gateway proxy,
        transparently intercepting 429/402 quota overruns.
        """
        task_type = self._determine_task_type(prompt)
        
        # Enforced metadata routing headers for our anti-burn circuit breaker
        headers = {
            "Content-Type": "application/json",
            "X-Agent-ID": self.agent_id,
            "X-Task-Type": task_type,
            "X-Fallback-Tier": model_fallback_tier
        }

        # Structuring standard inference execution payload template
        payload = {
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2 if task_type == "critical-engineering" else 0.7,
            "max_tokens": 4096 if task_type == "critical-engineering" else 512
        }

        try:
            response = requests.post(
                f"{self.gateway_url}/v1/chat/completions",
                json=payload,
                headers=headers,
                timeout=45.0
            )

            # Instantly intercept quota exhaustion or rate limits on current provider tier
            if response.status_code in [429, 402]:
                print(f"[!] Warning: Provider quota limit hit ({response.status_code}). Triggering grid fallback routing...")
                return self._execute_hard_failsafe(prompt, headers)

            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            print(f"[-] Edge communication error encountered: {str(e)}. Escallating to hard failsafe pipeline...")
            return self._execute_hard_failsafe(prompt, headers)

    def _execute_hard_failsafe(self, prompt: str, base_headers: Dict[str, str]) -> Dict[str, Any]:
        """
        Failsafe method that forces immediate escalation to Google Vertex AI nodes.
        """
        base_headers["X-Task-Type"] = "critical-engineering"  # Force high-availability routing rails
        fallback_endpoint = f"{self.gateway_url}/v1/chat/completions"
        
        payload = {
            "messages": [{"role": "user", "content": f"[FAILSAFE MODE COMPLIANCE] {prompt}"}],
            "temperature": 0.1
        }
        
        response = requests.post(fallback_endpoint, json=payload, headers=base_headers, timeout=60.0)
        response.raise_for_status()
        return response.json()

if __name__ == "__main__":
    # Internal component connectivity test stub
    client = ClawRouterClient(agent_id="test-cem-core-agent")
    print("[+] Initializing system loop verification testing...")

