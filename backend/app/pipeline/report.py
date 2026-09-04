"""Automated report generation: turns a computed equipment result into a
narrative "investigation report" -- the same structured findings, phrased
like an inspector's write-up rather than a raw JSON dump."""
import datetime


def generate_report(result: dict) -> dict:
    rc = result["root_cause"]
    actions = result["recommended_actions"]

    if rc["top_cause"]:
        cause_sentence = (
            f"Analysis points to {rc['top_cause_label']} as the most likely root cause "
            f"(confidence {int(rc['confidence'] * 100)}%), {'corroborated by similar historical failures. ' if rc.get('corroborated_by_history') else ''}"
            f"{rc['description']}"
        )
    else:
        cause_sentence = "No dominant fault signature was identified; telemetry remains within or close to normal healthy ranges."

    similar_sentence = ""
    if result["similar_incidents"]:
        top_sim = result["similar_incidents"][0]
        similar_sentence = (
            f" This pattern is {top_sim['similarity_pct']}% similar to historical incident {top_sim['incident_id']} "
            f"({top_sim['equipment_type']}, root cause: {top_sim['root_cause'].replace('_', ' ')}), which was ultimately resolved by: {top_sim['action_taken']}."
        )

    summary = (
        f"{result['name']} ({result['type']}, {result['location']}) currently carries a risk score of "
        f"{result['risk_score']}/100, classified as {result['severity']} severity. "
        f"The model estimates a {result['risk_components']['failure_probability_pct']}% probability of failure "
        f"within the next 30 operating cycles. {cause_sentence}{similar_sentence}"
    )

    action_lines = []
    if actions["immediate"]:
        action_lines.append({"priority": "Immediate", "items": actions["immediate"]})
    if actions["short_term"]:
        action_lines.append({"priority": "Short-term", "items": actions["short_term"]})
    if actions["monitoring"]:
        action_lines.append({"priority": "Ongoing Monitoring", "items": actions["monitoring"]})

    return {
        "title": f"Safety Investigation Report — {result['name']}",
        "generated_at": datetime.datetime.utcnow().isoformat() + "Z",
        "equipment_id": result["equipment_id"],
        "summary": summary,
        "risk_score": result["risk_score"],
        "severity": result["severity"],
        "urgency": actions["urgency"],
        "root_cause": rc,
        "evidence": result["evidence"],
        "failure_chain": result["failure_chain"],
        "similar_incidents": result["similar_incidents"],
        "action_plan": action_lines,
        "timeline": result["timeline"],
    }
