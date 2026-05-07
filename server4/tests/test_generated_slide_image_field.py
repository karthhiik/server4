"""Bug 1 regression — `image_url` must survive `asdict()` serialization.

Before the fix, `image_generator.generate_images()` set the URL via
`setattr(slide, "imageUrl", url)`. The dataclass had no declared
`image_url` / `imageUrl` field, so any artifact dump that goes through
`dataclasses.asdict()` (e.g. the live-pipeline harness) silently
dropped it. Downstream offline tooling — quality reports, audit
scripts — therefore could not see image URLs even when the image
stage had succeeded in-process.

This test pins the contract: setting the snake_case `image_url` field
on `GeneratedSlide` must be preserved by `asdict()`.
"""

from __future__ import annotations

from dataclasses import asdict

from app.services.v4.parallel_writer import GeneratedSlide


def test_generated_slide_declares_image_url_field():
    """The dataclass must declare image_url so asdict() captures it."""
    fields = set(GeneratedSlide.__dataclass_fields__.keys())
    assert "image_url" in fields
    assert "image_source" in fields
    assert "image_position" in fields
    assert "image_intent" in fields


def test_image_url_survives_asdict_roundtrip():
    """Mirrors what the live harness does: build a slide, populate the
    image fields the way `image_generator.generate_images()` does, then
    asdict() and confirm everything round-trips cleanly.
    """
    s = GeneratedSlide(
        index=0,
        intent="hero",
        layout="image-full",
        headline="Real picture",
    )
    # Same code path as image_generator.generate_images() post-fix.
    s.image_url = "https://images.example.test/real-1.png"
    s.image_source = "flux"
    s.image_position = "background"
    s.image_intent = "hero"

    dumped = asdict(s)
    assert dumped["image_url"] == "https://images.example.test/real-1.png"
    assert dumped["image_source"] == "flux"
    assert dumped["image_position"] == "background"
    assert dumped["image_intent"] == "hero"


def test_image_url_default_is_none_no_fake_placeholder():
    """A freshly-created slide must NOT carry a placeholder URL.

    The no-fake-data invariant requires that an un-imaged slide
    serializes with `image_url=None`, never with a stand-in URL.
    """
    s = GeneratedSlide(index=1, intent="x", layout="bullets", headline="No img")
    dumped = asdict(s)
    assert dumped["image_url"] is None
    assert dumped["image_source"] is None
