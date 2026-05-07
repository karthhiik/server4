                try:
                    # Set planner mode for re-planning
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
