"""Optional MLflow observability helpers."""

def log_incident_metrics(incident_id: str, metrics: dict[str, float]) -> None:
    """Track quantitative incident observations in MLflow."""
    import mlflow
    with mlflow.start_run(run_name=f"incident-{incident_id}"):
        mlflow.set_tag("incident_id", incident_id)
        for key, value in metrics.items():
            mlflow.log_metric(key, value)
