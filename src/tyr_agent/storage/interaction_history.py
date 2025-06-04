import json
import os
from typing import List


class InteractionHistory:
    def __init__(self, filename: str = "conversation_history.json"):
        self.filename = filename
        if not os.path.exists(self.filename):
            with open(self.filename, "w", encoding="utf-8") as f:
                json.dump({}, f, ensure_ascii=False)

    def save_history(self, agent_name: str, history: dict) -> None:
        try:
            data = self.load_all()

            if data.get(agent_name, False):
                data[agent_name].append(history)
            else:
                data[agent_name] = [history]

            with open(self.filename, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[ERROR] - Erro ao salvar histórico: {e}")

    def load_history(self, agent_name: str) -> List[dict]:
        data = self.load_all()
        return data.get(agent_name, [])

    def load_all(self) -> dict:
        try:
            with open(self.filename, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def clear_history(self) -> None:
        try:
            with open(self.filename, "w", encoding="utf-8") as f:
                json.dump({}, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[ERROR] - Erro ao limpar o histórico.")

    def update_score(self, agent_name: str, interaction_id: str, score: float) -> bool:
        try:
            if not isinstance(score, (int, float)) or not (0 <= score <= 5):
                raise ValueError("Score deve ser um número entre 0 e 5.")

            data = self.load_all()

            if data.get(agent_name, False):
                for interaction in data[agent_name]:
                    if interaction["id"] == interaction_id:
                        interaction["score"] = score

                        with open(self.filename, "w", encoding="utf-8") as f:
                            json.dump(data, f, indent=2, ensure_ascii=False)

                        return True
            else:
                return False
        except Exception as e:
            print(f"[ERROR] - Erro ao salvar histórico: {e}")
            return False
