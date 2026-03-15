from __future__ import annotations

from agent_benchmark.storage.models import AggregatedRow, RouterRunResult, SingleMultiRunResult


def flatten_result(result: SingleMultiRunResult | RouterRunResult) -> AggregatedRow:
    if result.strategy == "router":
        return AggregatedRow(
            task_id=result.task_id,
            strategy=result.strategy,
            repetition_index=None,
            batch_id=result.batch_id,
            model=result.model,
            latency_sec=result.latency_sec,
            total_tokens=result.total_tokens,
            estimated_cost=result.estimated_cost,
            status=result.status,
            error_type=result.error_type,
            error_message=result.error_message,
            final_output_path=None,
            workspace_path=None,
            selected_route=result.selected_route,
            route_confidence=result.route_confidence,
            manual_route_was_good_choice=result.manual_eval.route_was_good_choice,
            notes=result.manual_eval.score_notes,
        )
    return AggregatedRow(
        task_id=result.task_id,
        strategy=result.strategy,
        repetition_index=result.repetition_index,
        batch_id=result.batch_id,
        model=result.model,
        latency_sec=result.latency_sec,
        total_tokens=result.total_tokens,
        estimated_cost=result.estimated_cost,
        status=result.status,
        error_type=result.error_type,
        error_message=result.error_message,
        final_output_path=result.final_output_file,
        workspace_path=result.workspace_path,
        selected_route=None,
        route_confidence=None,
        manual_score_overall=result.manual_eval.score_overall,
        manual_pass_fail=result.manual_eval.pass_fail,
        notes=result.manual_eval.score_notes,
    )
