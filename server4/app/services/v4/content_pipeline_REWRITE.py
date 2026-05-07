                # Hard-gate: If >30% of slides have generic_risk: "high", trigger full re-plan
                if slides:
                    high_risk_count = sum(
                        1 for s in slides
                        if getattr(s, "generic_risk", None) == "high"
                    )
                    risk_ratio = high_risk_count / len(slides)
                    if risk_ratio > 0.3:
                        await emit("stage_start", {"stage": "replan", "reason": "high_generic_risk"})
                        try:
                            # Re-plan with stricter thesis-first enforcement
                            self.planner.model_tier = "premium" if purpose == "investor_pitch" else "standard"
                            skeleton = self.planner.plan(
                                project_id=project_id,
                                user_query=user_query,
                                research=research,
                                slide_count=len(slides_data) if slides_data else None,
                                narrative_arc="investor_pitch" if purpose == "investor_pitch" else "custom",
                            )
                            # Re-write slides with new skeleton
                            slides = await self.writer.write_all(
                                skeleton=skeleton,
                                research=research,
                                mode=mode,
                                purpose=purpose,
                                design_tokens=design_tokens,
                                structured_context=structured_context,
                            )
                            await emit("stage_complete", {
                                "stage": "replan",
                                "slides": len(slides),
                            })
                        except Exception as e:
                            logger.warning("v4_replan_failed", project_id=project_id, error=str(e))
                            await emit("stage_complete", {
                                "stage": "replan",
                                "error": str(e)[:200],
                            })
