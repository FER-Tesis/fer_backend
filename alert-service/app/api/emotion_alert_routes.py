from fastapi import APIRouter, HTTPException, Depends
from app.schemas.emotion_alert_schema import (
    EmotionAlertPolicyCreate,
    EmotionAlertPolicyUpdate,
    EmotionAlertPolicyResponse,
    EmotionAlertRuleCreate,
    EmotionAlertRuleUpdate,
    EmotionAlertRuleResponse,
    EmotionAlertResponse,
    EmotionEvaluationStateResponse,
)
from app.enums.emotion_alert_enum import PolicyStatus
from app.repositories import (
    emotion_alert_policy_repository,
    emotion_alert_rule_repository,
    emotion_evaluation_state_repository,
    emotion_alert_repository,
)
from app.services.emotion_alert_evaluation_service import reset_policy_states
from app.services import emotion_alert_service

router = APIRouter()


# ============== POLICY ENDPOINTS ==============

@router.post("/policies", response_model=EmotionAlertPolicyResponse)
async def create_policy(policy: EmotionAlertPolicyCreate):
    """Crear una nueva política de alertas emocionales"""
    policy_data = {
        "supervisor_id": policy.supervisor_id,
        "name": policy.name,
        "status": PolicyStatus.active.value,
    }
    return await emotion_alert_policy_repository.create_policy(policy_data)


@router.get("/policies/{policy_id}", response_model=EmotionAlertPolicyResponse)
async def get_policy(policy_id: str):
    """Obtener una política por ID"""
    policy = await emotion_alert_policy_repository.get_policy_by_id(policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    return policy


@router.get("/supervisors/{supervisor_id}/policies/active", response_model=EmotionAlertPolicyResponse)
async def get_supervisor_active_policy(supervisor_id: str):
    """Obtener la política activa de un supervisor"""
    policy = await emotion_alert_policy_repository.get_active_policy_by_supervisor(supervisor_id)
    if not policy:
        raise HTTPException(status_code=404, detail="No active policy found for this supervisor")
    return policy


@router.patch("/policies/{policy_id}", response_model=EmotionAlertPolicyResponse)
async def update_policy(policy_id: str, update_data: EmotionAlertPolicyUpdate):
    """Actualizar una política"""
    # Si cambia a política activa, desactivar otras del mismo supervisor
    policy = await emotion_alert_policy_repository.get_policy_by_id(policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    if update_data.status == PolicyStatus.active:
        # Desactivar todas las políticas del supervisor
        await emotion_alert_policy_repository.deactivate_all_supervisor_policies(
            str(policy["supervisor_id"])
        )
        
        # Resetear estados de evaluación de políticas anteriores
        # (Asumiendo que la política anterior era la única activa)
        await reset_policy_states(policy_id)
    
    update_dict = update_data.model_dump(exclude_none=True)
    updated_policy = await emotion_alert_policy_repository.update_policy(policy_id, update_dict)
    
    if not updated_policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    return updated_policy


# ============== RULE ENDPOINTS ==============

@router.post("/rules", response_model=EmotionAlertRuleResponse)
async def create_rule(rule: EmotionAlertRuleCreate):
    """Crear una nueva regla de evaluación"""
    rule_data = {
        "policy_id": rule.policy_id,
        "type": rule.type.value,
        "emotions": rule.emotions,
        "threshold": rule.threshold,
        "window_seconds": rule.window_seconds,
        "cooldown_seconds": rule.cooldown_seconds,
        "severity": rule.severity.value,
        "status": PolicyStatus.active.value,
    }
    return await emotion_alert_rule_repository.create_rule(rule_data)


@router.get("/rules/{rule_id}", response_model=EmotionAlertRuleResponse)
async def get_rule(rule_id: str):
    """Obtener una regla por ID"""
    rule = await emotion_alert_rule_repository.get_rule_by_id(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    return rule


@router.get("/policies/{policy_id}/rules")
async def get_policy_rules(policy_id: str):
    """Obtener todas las reglas de una política"""
    rules = await emotion_alert_rule_repository.get_all_rules_by_policy(policy_id)
    return rules


@router.patch("/rules/{rule_id}", response_model=EmotionAlertRuleResponse)
async def update_rule(rule_id: str, update_data: EmotionAlertRuleUpdate):
    """Actualizar una regla"""
    update_dict = update_data.model_dump(exclude_none=True)
    # Convertir enums a valores
    if "type" in update_dict:
        update_dict["type"] = update_dict["type"].value
    if "severity" in update_dict:
        update_dict["severity"] = update_dict["severity"].value
    if "status" in update_dict:
        update_dict["status"] = update_dict["status"].value
    
    updated_rule = await emotion_alert_rule_repository.update_rule(rule_id, update_dict)
    if not updated_rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    return updated_rule


# ============== ALERT ENDPOINTS ==============

@router.get("/alerts/{alert_id}", response_model=EmotionAlertResponse)
async def get_alert(alert_id: str):
    """Obtener una alerta por ID"""
    alert = await emotion_alert_repository.get_alert_by_id(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert


@router.get("/agents/{agent_id}/alerts")
async def get_agent_alerts(agent_id: str, limit: int = 100):
    """Obtener todas las alertas de un agente"""
    alerts = await emotion_alert_repository.get_alerts_by_agent(agent_id, limit)
    return alerts


@router.get("/supervisors/{supervisor_id}/alerts")
async def get_supervisor_alerts(supervisor_id: str, limit: int = 100):
    """Obtener todas las alertas de un supervisor"""
    alerts = await emotion_alert_repository.get_alerts_by_supervisor(supervisor_id, limit)
    return alerts

@router.get("/supervisors/{supervisor_id}/alerts/pending", response_model=list[EmotionAlertResponse])
async def get_supervisor_pending_alerts(supervisor_id: str, limit: int = 100):
    return await emotion_alert_service.list_pending_emotion_alerts_for_supervisor(
        supervisor_id,
        limit,
    )


@router.get("/alerts/status/pending")
async def get_pending_alerts(limit: int = 100):
    """Obtener todas las alertas pendientes"""
    alerts = await emotion_alert_repository.get_pending_alerts(limit)
    return alerts


@router.patch("/alerts/{alert_id}/acknowledge", response_model=EmotionAlertResponse)
async def acknowledge_alert(alert_id: str):
    try:
        return await emotion_alert_service.acknowledge_emotion_alert(alert_id)

    except emotion_alert_service.EmotionAlertDomainError as e:
        if str(e) == "emotion_alert_not_found":
            raise HTTPException(status_code=404, detail="Alert not found")

        raise HTTPException(status_code=400, detail="Invalid request")


# ============== EVALUATION STATE ENDPOINTS ==============

@router.get("/evaluation-states/{agent_id}/{policy_id}")
async def get_agent_policy_evaluation_states(agent_id: str, policy_id: str):
    """Obtener estados de evaluación de un agente en una política"""
    states = await emotion_evaluation_state_repository.get_evaluation_states_by_agent_and_policy(
        agent_id, policy_id
    )
    return states
