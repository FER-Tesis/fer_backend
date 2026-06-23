from datetime import datetime, timedelta
from bson import ObjectId
import httpx

from app.core.config import settings
from app.repositories import (
    emotion_alert_policy_repository,
    emotion_alert_rule_repository,
    emotion_evaluation_state_repository,
    emotion_alert_repository,
)
from app.events.alert_event_bus import alert_event_bus


class EvaluationError(Exception):
    """Errores durante evaluación de reglas"""
    pass


async def _fetch_supervisor_id(agent_id: str) -> str:
    """Obtener supervisor_id del agent_id desde user-service"""
    try:
        async with httpx.AsyncClient() as client:
            url = f"{settings.USER_SERVICE_URL}/relations/{agent_id}/supervisor"
            response = await client.get(url, timeout=5.0)
            
            if response.status_code == 404:
                raise EvaluationError(f"Agent {agent_id} not found")
            
            if response.status_code != 200:
                raise EvaluationError(f"Failed to fetch supervisor for agent {agent_id}")
            
            data = response.json()
            return data.get("supervisor_id")
    except httpx.TimeoutException:
        raise EvaluationError(f"Timeout fetching supervisor for agent {agent_id}")
    except Exception as e:
        raise EvaluationError(f"Error fetching supervisor: {str(e)}")


def _is_negative_emotion(emotion: str) -> bool:
    """Verificar si una emoción es negativa"""
    negative_emotions = {"sad", "anger", "fear", "disgust"}
    return emotion.lower() in negative_emotions


def _remove_expired_emotions(emotions_window: list, window_seconds: int, current_time: datetime) -> list:
    """Remover emociones que ya no pertenecen a la ventana de tiempo"""
    cutoff_time = current_time - timedelta(seconds=window_seconds)

    return [
        e for e in emotions_window
        if (
            datetime.fromisoformat(e["timestamp"])
            if isinstance(e["timestamp"], str)
            else e["timestamp"]
        ) > cutoff_time
    ]


async def _evaluate_negative_count_rule(
    state: dict,
    rule: dict,
    emotion: str,
    timestamp: datetime,
) -> tuple[bool, dict]:
    """
    Evaluar regla de tipo negative_count
    Retorna: (condición_cumplida, estado_actualizado)
    """
    window_seconds = rule["window_seconds"]
    threshold = rule["threshold"]
    target_emotions = rule["emotions"]
    
    # Actualizar ventana deslizante
    emotions_window = state.get("emotions_window", [])
    emotions_window = _remove_expired_emotions(emotions_window, window_seconds, timestamp)
    
    # Agregar nueva emoción si es de las que nos interesan
    if emotion.lower() in target_emotions:
        emotions_window.append({
            "emotion": emotion,
            "timestamp": timestamp.isoformat(),
        })
    
    # Contar emociones en ventana
    count = len(emotions_window)
    
    # Condición cumplida si count >= threshold
    condition_met = count >= threshold
    
    updated_state = {
        "emotions_window": emotions_window,
        "current_count": count,
    }
    
    return condition_met, updated_state


async def _evaluate_continuous_emotion_rule(
    state: dict,
    rule: dict,
    emotion: str,
    timestamp: datetime,
) -> tuple[bool, dict]:
    threshold_seconds = rule["threshold"]
    target_emotions = [e.lower() for e in rule["emotions"]]

    continuous_start = state.get("continuous_emotion_start")

    if isinstance(continuous_start, str):
        continuous_start = datetime.fromisoformat(continuous_start)

    if emotion.lower() in target_emotions:
        if not continuous_start:
            continuous_start = timestamp

        duration = int((timestamp - continuous_start).total_seconds())
        condition_met = duration >= threshold_seconds

        updated_state = {
            "continuous_emotion_start": continuous_start.isoformat(),
            "continuous_duration_seconds": duration,
        }
    else:
        condition_met = False
        updated_state = {
            "continuous_emotion_start": None,
            "continuous_duration_seconds": 0,
        }

    return condition_met, updated_state

async def _check_cooldown(state: dict, current_time: datetime) -> bool:
    """Verificar si el cooldown ha expirado"""
    cooldown_end = state.get("cooldown_end_at")
    if not cooldown_end:
        return True  # Sin cooldown activo
    
    # Convertir string a datetime si es necesario
    if isinstance(cooldown_end, str):
        cooldown_end = datetime.fromisoformat(cooldown_end)
    
    return current_time > cooldown_end


async def _create_alert(
    agent_id: str,
    supervisor_id: str,
    policy_id: str,
    rule: dict,
) -> dict:
    """Crear documento de alerta"""
    alert_data = {
        "agent_id": agent_id,
        "supervisor_id": supervisor_id,
        "policy_id": policy_id,
        "rule_id": str(rule["_id"]),
        "rule_type": rule["type"],
        "severity": rule["severity"],
        "status": "pending",
    }
    return await emotion_alert_repository.create_alert(alert_data)

RULE_EVALUATORS = {
    "negative_count": _evaluate_negative_count_rule,
    "continuous_emotion": _evaluate_continuous_emotion_rule,
}


def _normalize_emotions(emotions: list[str]) -> list[str]:
    return [emotion.lower() for emotion in emotions]


def _rule_matches_emotion(rule: dict, emotion: str) -> bool:
    return emotion.lower() in _normalize_emotions(rule.get("emotions", []))


def _should_create_state_for_rule(rule: dict, emotion: str) -> bool:
    rule_type = rule["type"]

    if rule_type == "negative_count":
        return _rule_matches_emotion(rule, emotion)

    if rule_type == "continuous_emotion":
        return True

    return False


async def evaluate_emotion_event(
    agent_id: str,
    emotion: str,
    timestamp_str: str,
) -> list[dict]:
    try:
        if isinstance(timestamp_str, str):
            current_time = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        else:
            current_time = timestamp_str

        supervisor_id = await _fetch_supervisor_id(agent_id)

        policy = await emotion_alert_policy_repository.get_active_policy_by_supervisor(
            supervisor_id
        )
        if not policy:
            return []

        policy_id = str(policy["_id"])

        rules = await emotion_alert_rule_repository.get_active_rules_by_policy(policy_id)

        alerts_generated = []

        for rule in rules:
            rule_id = str(rule["_id"])
            rule_type = rule["type"]

            evaluator = RULE_EVALUATORS.get(rule_type)
            if not evaluator:
                continue

            if not _should_create_state_for_rule(rule, emotion):
                continue

            state = await emotion_evaluation_state_repository.get_or_create_evaluation_state(
                agent_id=agent_id,
                rule_id=rule_id,
                policy_id=policy_id,
            )

            condition_met, updated_state = await evaluator(
                state,
                rule,
                emotion,
                current_time,
            )

            if condition_met:
                cooldown_ok = await _check_cooldown(state, current_time)

                if cooldown_ok:
                    alert = await _create_alert(
                        agent_id=agent_id,
                        supervisor_id=supervisor_id,
                        policy_id=policy_id,
                        rule=rule,
                    )

                    alerts_generated.append(alert)
                    
                    await alert_event_bus.publish(
                        "emotion-alert-created",
                        {
                            "_id": alert["_id"],
                            "agent_id": alert["agent_id"],
                            "supervisor_id": alert["supervisor_id"],
                            "policy_id": alert["policy_id"],
                            "rule_id": alert["rule_id"],
                            "rule_type": alert["rule_type"],
                            "severity": alert["severity"],
                            "status": alert["status"],
                            "created_at": alert["created_at"].isoformat(),
                            "updated_at": alert["updated_at"].isoformat(),
                        },
                    )
                    
                    cooldown_end = current_time + timedelta(
                        seconds=rule["cooldown_seconds"]
                    )

                    updated_state["last_alert_at"] = current_time.isoformat()
                    updated_state["cooldown_end_at"] = cooldown_end.isoformat()

            await emotion_evaluation_state_repository.update_evaluation_state(
                str(state["_id"]),
                updated_state,
            )

        return alerts_generated

    except EvaluationError as e:
        print(f"Evaluation error for agent {agent_id}: {str(e)}")
        return []

    except Exception as e:
        print(f"Unexpected error evaluating emotion: {str(e)}")
        return []


async def reset_policy_states(policy_id: str):
    """Resetear todos los estados de evaluación de una política"""
    await emotion_evaluation_state_repository.delete_evaluation_states_by_policy(policy_id)

async def delete_emotion_evaluation_states_by_agent(agent_id: str):
    """Eliminar todos los estados de evaluación de un agente"""
    await emotion_evaluation_state_repository.delete_evaluation_states_by_agent(agent_id)