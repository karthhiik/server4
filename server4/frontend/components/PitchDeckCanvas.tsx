/**
 * Pitch Deck Canvas
 *
 * MVP preview shell for both legacy pitch slides and V4 compiled slides.
 * V4 slides render the backend html_css_js artifact in a sandboxed iframe so
 * preview, regenerated images, design tokens, and export artifacts stay aligned.
 */

import React, { useMemo, useState } from "react";
import {
  AskSlide,
  BusinessModelSlide,
  ExecutiveSummarySlide,
  FinancialsSlide,
  MarketSlide,
  ProductDemoSlide,
  TeamSlide,
  TractionSlide,
} from "./slides";

interface PitchDeckSlide {
  id: string;
  order: number;
  type: string;
  title: string;
  content: Record<string, any>;
  speaker_notes?: string;
}

interface V4CompiledSlide {
  id?: string;
  slide_id?: string;
  index?: number;
  slide_index?: number;
  order?: number;
  artifact_version?: number;
  kit_component?: string;
  source_slide?: {
    headline?: string;
    subheadline?: string;
    speaker_notes?: string;
  };
  artifacts?: {
    html_css_js?: {
      html?: string;
      css?: string;
      js?: string;
      head_meta?: {
        title?: string;
      };
    };
    kit_jsx?: {
      props_json?: Record<string, any>;
    };
  };
}

type CanvasSlide = PitchDeckSlide | V4CompiledSlide;

interface PitchDeckCanvasProps {
  deck: {
    id: string;
    title: string;
    slides?: PitchDeckSlide[];
    compiled_slides?: V4CompiledSlide[];
    theme?: string;
    status: "draft" | "published" | "archived";
  };
  onUpdate?: (updates: any) => void;
  onExport?: (format: "pdf" | "pptx") => void;
}

export function PitchDeckCanvas({ deck, onUpdate, onExport }: PitchDeckCanvasProps) {
  const [currentSlideIndex, setCurrentSlideIndex] = useState(0);
  const [isPresenting, setIsPresenting] = useState(false);

  const slides = useMemo<CanvasSlide[]>(() => {
    const compiled = deck.compiled_slides || [];
    if (compiled.length > 0) {
      return [...compiled].sort((a, b) => slideOrder(a) - slideOrder(b));
    }
    return deck.slides || [];
  }, [deck.compiled_slides, deck.slides]);

  const currentSlide = slides[currentSlideIndex];

  const goToNext = () => {
    setCurrentSlideIndex(Math.min(currentSlideIndex + 1, Math.max(slides.length - 1, 0)));
  };

  const goToPrevious = () => {
    setCurrentSlideIndex(Math.max(currentSlideIndex - 1, 0));
  };

  const goToSlide = (index: number) => {
    setCurrentSlideIndex(Math.max(0, Math.min(index, Math.max(slides.length - 1, 0))));
  };

  const renderSlide = (slide: CanvasSlide) => {
    if (isV4Slide(slide)) {
      return <V4SlidePreview slide={slide} />;
    }

    switch (slide.type) {
      case "executive_summary":
        return <ExecutiveSummarySlide data={slide.content as any} onUpdate={onUpdate} />;
      case "product_demo":
        return <ProductDemoSlide data={slide.content as any} onUpdate={onUpdate} />;
      case "market":
        return <MarketSlide data={slide.content as any} onUpdate={onUpdate} />;
      case "business_model":
        return <BusinessModelSlide data={slide.content as any} onUpdate={onUpdate} />;
      case "financials":
        return <FinancialsSlide data={slide.content as any} onUpdate={onUpdate} />;
      case "team":
        return <TeamSlide data={slide.content as any} onUpdate={onUpdate} />;
      case "traction":
        return <TractionSlide data={slide.content as any} onUpdate={onUpdate} />;
      case "ask":
        return <AskSlide data={slide.content as any} onUpdate={onUpdate} />;
      default:
        return (
          <div className="empty-deck">
            <p>Unsupported slide type: {slide.type}</p>
          </div>
        );
    }
  };

  return (
    <div className={`pitch-deck-container ${isPresenting ? "presenting" : ""}`} role="application" aria-label="Pitch Deck Canvas">
      <div className="deck-viewer" role="main">
        <div className="slide-display" role="region" aria-label="Current slide">
          {currentSlide ? renderSlide(currentSlide) : <div className="empty-deck">No slides generated yet.</div>}
        </div>

        <div className="slide-counter" aria-live="polite" aria-atomic="true">
          {slides.length ? currentSlideIndex + 1 : 0} / {slides.length}
        </div>

        <nav className="navigation-controls" role="navigation" aria-label="Pitch deck navigation">
          <button onClick={goToPrevious} disabled={!slides.length || currentSlideIndex === 0} className="nav-button" aria-label="Previous slide">
            Previous
          </button>

          <button onClick={() => setIsPresenting(!isPresenting)} className="present-button" aria-label={isPresenting ? "Exit presentation" : "Start presentation"}>
            {isPresenting ? "Exit" : "Present"}
          </button>

          <button onClick={goToNext} disabled={!slides.length || currentSlideIndex === slides.length - 1} className="nav-button" aria-label="Next slide">
            Next
          </button>
        </nav>

        {currentSlide && slideNotes(currentSlide) ? (
          <aside className="speaker-notes" role="complementary" aria-label="Speaker notes for current slide">
            <h4>Speaker Notes</h4>
            <p>{slideNotes(currentSlide)}</p>
          </aside>
        ) : null}
      </div>

      <aside className="deck-sidebar" role="complementary" aria-label="Pitch deck controls and navigation">
        <h2>{deck.title}</h2>
        <div className="deck-status">
          <span className="status-badge" data-status={deck.status}>
            {deck.status.toUpperCase()}
          </span>
          {deck.theme ? <span className="theme-badge">{deck.theme}</span> : null}
        </div>

        <nav className="slide-thumbnails" role="navigation" aria-label="Slide thumbnails">
          {slides.map((slide, index) => (
            <button
              key={slideKey(slide, index)}
              className={`thumbnail ${index === currentSlideIndex ? "active" : ""}`}
              onClick={() => goToSlide(index)}
              aria-label={`Slide ${index + 1}: ${slideTitle(slide)}`}
              aria-current={index === currentSlideIndex ? "true" : undefined}
            >
              <div className="thumbnail-preview">{slideInitial(slide)}</div>
              <div className="thumbnail-title">{slideTitle(slide)}</div>
              <div className="thumbnail-order">{index + 1}</div>
            </button>
          ))}
        </nav>

        <div className="export-controls">
          <button className="export-btn pdf" onClick={() => onExport?.("pdf")} aria-label="Export pitch deck as PDF">
            Export PDF
          </button>
          <button className="export-btn pptx" onClick={() => onExport?.("pptx")} aria-label="Export pitch deck as PowerPoint presentation">
            Export PPTX
          </button>
        </div>
      </aside>

      <style>{`
        .pitch-deck-container {
          display: grid;
          grid-template-columns: minmax(0, 1fr) 300px;
          gap: 18px;
          min-height: 100vh;
          background: #eef2f7;
          padding: 18px;
        }

        .pitch-deck-container.presenting {
          grid-template-columns: 1fr;
          padding: 0;
          background: #050507;
        }

        .presenting .deck-sidebar,
        .presenting .navigation-controls,
        .presenting .slide-counter,
        .presenting .speaker-notes {
          display: none;
        }

        .deck-viewer {
          display: flex;
          min-width: 0;
          flex-direction: column;
          overflow: hidden;
          background: #ffffff;
          border: 1px solid #d8dee8;
          border-radius: 8px;
          box-shadow: 0 18px 50px rgba(15, 23, 42, 0.12);
        }

        .presenting .deck-viewer {
          height: 100vh;
          border: 0;
          border-radius: 0;
        }

        .slide-display {
          display: grid;
          flex: 1;
          min-height: 0;
          overflow: hidden;
          aspect-ratio: 16 / 9;
          background: #101014;
        }

        .compiled-slide-frame {
          width: 100%;
          height: 100%;
          border: 0;
          background: #ffffff;
        }

        .compiled-slide-fallback,
        .empty-deck {
          display: flex;
          width: 100%;
          height: 100%;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          padding: 48px;
          background: #18181b;
          color: #f8fafc;
          text-align: center;
        }

        .compiled-slide-fallback h1 {
          max-width: 840px;
          margin: 0;
          font-size: 42px;
          line-height: 1.08;
          letter-spacing: 0;
        }

        .compiled-slide-fallback p {
          max-width: 720px;
          margin: 16px 0 0;
          color: #cbd5e1;
          font-size: 18px;
        }

        .fallback-kit {
          margin: 0 0 18px;
          color: #94a3b8;
          font-size: 12px;
          letter-spacing: 0;
          text-transform: uppercase;
        }

        .slide-counter {
          padding: 10px;
          background: #f8fafc;
          color: #475569;
          font-size: 13px;
          font-weight: 600;
          text-align: center;
        }

        .navigation-controls {
          display: flex;
          gap: 10px;
          padding: 14px;
          background: #ffffff;
          border-top: 1px solid #e2e8f0;
        }

        .nav-button,
        .present-button,
        .export-btn {
          min-height: 38px;
          border-radius: 6px;
          font-size: 13px;
          font-weight: 700;
          cursor: pointer;
          transition: background 0.16s ease, border-color 0.16s ease, color 0.16s ease;
        }

        .nav-button {
          flex: 1;
          border: 1px solid #cbd5e1;
          background: #ffffff;
          color: #1e293b;
        }

        .nav-button:hover:not(:disabled) {
          background: #f8fafc;
          border-color: #94a3b8;
        }

        .nav-button:disabled {
          opacity: 0.45;
          cursor: not-allowed;
        }

        .present-button {
          min-width: 96px;
          border: 1px solid #111827;
          background: #111827;
          color: #ffffff;
        }

        .speaker-notes {
          max-height: 128px;
          overflow: auto;
          padding: 14px 18px;
          border-top: 1px solid #e2e8f0;
          background: #f8fafc;
        }

        .speaker-notes h4 {
          margin: 0 0 6px;
          color: #334155;
          font-size: 12px;
          letter-spacing: 0;
          text-transform: uppercase;
        }

        .speaker-notes p {
          margin: 0;
          color: #475569;
          font-size: 14px;
          line-height: 1.45;
        }

        .deck-sidebar {
          display: flex;
          min-width: 0;
          flex-direction: column;
          overflow: hidden;
          background: #ffffff;
          border: 1px solid #d8dee8;
          border-radius: 8px;
        }

        .deck-sidebar h2 {
          margin: 0;
          padding: 18px 18px 10px;
          color: #0f172a;
          font-size: 18px;
          line-height: 1.2;
          letter-spacing: 0;
        }

        .deck-status {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
          padding: 0 18px 14px;
        }

        .status-badge,
        .theme-badge {
          border-radius: 999px;
          padding: 4px 8px;
          font-size: 11px;
          font-weight: 700;
          letter-spacing: 0;
        }

        .status-badge {
          background: #e0f2fe;
          color: #075985;
        }

        .status-badge[data-status="published"] {
          background: #dcfce7;
          color: #166534;
        }

        .status-badge[data-status="archived"] {
          background: #f1f5f9;
          color: #475569;
        }

        .theme-badge {
          background: #f4f4f5;
          color: #3f3f46;
        }

        .slide-thumbnails {
          display: flex;
          min-height: 0;
          flex: 1;
          flex-direction: column;
          gap: 8px;
          overflow: auto;
          padding: 0 12px 12px;
        }

        .thumbnail {
          display: grid;
          grid-template-columns: 42px minmax(0, 1fr) 24px;
          align-items: center;
          gap: 10px;
          width: 100%;
          min-height: 58px;
          border: 1px solid #e2e8f0;
          border-radius: 8px;
          background: #ffffff;
          padding: 8px;
          text-align: left;
          cursor: pointer;
        }

        .thumbnail:hover {
          background: #f8fafc;
          border-color: #cbd5e1;
        }

        .thumbnail.active {
          background: #eff6ff;
          border-color: #2563eb;
        }

        .thumbnail-preview {
          display: grid;
          width: 42px;
          height: 34px;
          place-items: center;
          border-radius: 6px;
          background: #111827;
          color: #ffffff;
          font-size: 13px;
          font-weight: 800;
        }

        .thumbnail-title {
          overflow: hidden;
          color: #0f172a;
          font-size: 13px;
          font-weight: 650;
          line-height: 1.25;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        .thumbnail-order {
          color: #64748b;
          font-size: 12px;
          text-align: right;
        }

        .export-controls {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 8px;
          padding: 12px;
          border-top: 1px solid #e2e8f0;
        }

        .export-btn {
          border: 1px solid #cbd5e1;
          background: #ffffff;
          color: #0f172a;
        }

        .export-btn.pptx {
          border-color: #111827;
          background: #111827;
          color: #ffffff;
        }

        @media (max-width: 900px) {
          .pitch-deck-container {
            grid-template-columns: 1fr;
          }

          .deck-sidebar {
            max-height: 38vh;
          }
        }
      `}</style>
    </div>
  );
}

function V4SlidePreview({ slide }: { slide: V4CompiledSlide }) {
  const artifact = slide.artifacts?.html_css_js;
  if (artifact?.html || artifact?.css || artifact?.js) {
    return (
      <iframe
        key={`${slideKey(slide, 0)}-${slide.artifact_version || 0}`}
        className="compiled-slide-frame"
        title={slideTitle(slide)}
        sandbox="allow-scripts"
        srcDoc={buildSlideDocument(artifact)}
      />
    );
  }

  const props = slide.artifacts?.kit_jsx?.props_json || {};
  return (
    <div className="compiled-slide-fallback">
      <p className="fallback-kit">{slide.kit_component || "Compiled slide"}</p>
      <h1>{props.headline || props.title || slide.source_slide?.headline || "Untitled slide"}</h1>
      {props.subheadline || slide.source_slide?.subheadline ? (
        <p>{props.subheadline || slide.source_slide?.subheadline}</p>
      ) : null}
    </div>
  );
}

function buildSlideDocument(artifact: NonNullable<V4CompiledSlide["artifacts"]>["html_css_js"]) {
  return `<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>${escapeHtml(artifact?.head_meta?.title || "Slide")}</title>
  <style>
    html, body { width: 100%; height: 100%; margin: 0; overflow: hidden; background: #fff; }
    body { display: grid; place-items: stretch; }
    ${artifact?.css || ""}
  </style>
</head>
<body>
  ${artifact?.html || ""}
  <script>${artifact?.js || ""}</script>
</body>
</html>`;
}

function isV4Slide(slide: CanvasSlide): slide is V4CompiledSlide {
  return Boolean((slide as V4CompiledSlide).artifacts || (slide as V4CompiledSlide).kit_component);
}

function slideOrder(slide: CanvasSlide) {
  return Number((slide as V4CompiledSlide).slide_index ?? (slide as V4CompiledSlide).index ?? (slide as PitchDeckSlide).order ?? 0);
}

function slideTitle(slide: CanvasSlide) {
  if (isV4Slide(slide)) {
    const props = slide.artifacts?.kit_jsx?.props_json || {};
    return String(props.headline || props.title || slide.source_slide?.headline || slide.kit_component || "Untitled slide");
  }
  return slide.title || "Untitled slide";
}

function slideNotes(slide: CanvasSlide) {
  if (isV4Slide(slide)) {
    return slide.source_slide?.speaker_notes || "";
  }
  return slide.speaker_notes || "";
}

function slideInitial(slide: CanvasSlide) {
  return slideTitle(slide).trim().charAt(0).toUpperCase() || "S";
}

function slideKey(slide: CanvasSlide, index: number) {
  if (isV4Slide(slide)) {
    return `${slide.slide_id || slide.id || index}-${slide.artifact_version || 0}`;
  }
  return slide.id || String(index);
}

function escapeHtml(value: string) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
