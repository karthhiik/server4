"""
React Component Templates — Phase 6.

Defines the React component library that the ReactCompiler targets.
Each template represents a slide layout component with typed props,
Three.js scene integration points, and Framer Motion animation presets.

This module:
- Maps LayoutType → ComponentTemplate (JSX structure, props, imports)
- Maps ThreeSceneType → SceneTemplate (R3F component, config, dependencies)
- Provides animation preset definitions (Framer Motion variants)
- Defines the slide wrapper and utility component patterns
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


# ═══════════════════════════════════════════════════════════════════
# ANIMATION PRESETS (Framer Motion)
# ═══════════════════════════════════════════════════════════════════


class MotionPreset(str, Enum):
    """Framer Motion animation variants for slide elements."""
    FADE_IN = "fadeIn"
    SLIDE_UP = "slideUp"
    SLIDE_LEFT = "slideLeft"
    SLIDE_RIGHT = "slideRight"
    SCALE_UP = "scaleUp"
    SPRING_IN = "springIn"
    STAGGER_CHILDREN = "staggerChildren"
    FLOAT = "float"
    PULSE = "pulse"
    NONE = "none"


# Animation variant definitions (Framer Motion format)
MOTION_VARIANTS: dict[str, dict[str, Any]] = {
    "fadeIn": {
        "initial": {"opacity": 0},
        "animate": {"opacity": 1},
        "transition": {"duration": 0.6, "ease": "easeOut"},
    },
    "slideUp": {
        "initial": {"opacity": 0, "y": 40},
        "animate": {"opacity": 1, "y": 0},
        "transition": {"duration": 0.6, "ease": [0.25, 0.46, 0.45, 0.94]},
    },
    "slideLeft": {
        "initial": {"opacity": 0, "x": -40},
        "animate": {"opacity": 1, "x": 0},
        "transition": {"duration": 0.5, "ease": "easeOut"},
    },
    "slideRight": {
        "initial": {"opacity": 0, "x": 40},
        "animate": {"opacity": 1, "x": 0},
        "transition": {"duration": 0.5, "ease": "easeOut"},
    },
    "scaleUp": {
        "initial": {"opacity": 0, "scale": 0.85},
        "animate": {"opacity": 1, "scale": 1},
        "transition": {"duration": 0.5, "type": "spring", "stiffness": 200},
    },
    "springIn": {
        "initial": {"opacity": 0, "scale": 0.6},
        "animate": {"opacity": 1, "scale": 1},
        "transition": {"type": "spring", "stiffness": 300, "damping": 20},
    },
    "staggerChildren": {
        "animate": {"transition": {"staggerChildren": 0.1, "delayChildren": 0.2}},
    },
    "float": {
        "animate": {"y": [0, -8, 0]},
        "transition": {"duration": 3, "repeat": "Infinity", "ease": "easeInOut"},
    },
    "pulse": {
        "animate": {"scale": [1, 1.03, 1]},
        "transition": {"duration": 2, "repeat": "Infinity", "ease": "easeInOut"},
    },
    "none": {
        "initial": {},
        "animate": {},
    },
}


# ═══════════════════════════════════════════════════════════════════
# COMPONENT TEMPLATES
# ═══════════════════════════════════════════════════════════════════


@dataclass
class ComponentImport:
    """A single import statement required by a component."""
    module: str         # e.g. "react", "framer-motion", "@react-three/fiber"
    names: list[str]    # e.g. ["Canvas", "useFrame"]
    default: str = ""   # e.g. "React" for default import


@dataclass
class ComponentTemplate:
    """
    Template definition for a React slide component.

    Provides all information needed by the ReactCompiler to generate
    a working React component from DSL data.
    """
    name: str                       # PascalCase component name
    layout_type: str                # Corresponding LayoutType value
    description: str
    default_animation: MotionPreset = MotionPreset.FADE_IN
    supports_3d: bool = False       # Whether this layout has a 3D scene slot
    supports_chart: bool = False    # Whether this layout has a chart container
    container_class: str = ""       # Tailwind classes for the container <div>
    grid_template: str = ""         # CSS grid template (if applicable)
    imports: list[ComponentImport] = field(default_factory=list)
    slot_names: list[str] = field(default_factory=list)  # Named content slots
    props_interface: dict[str, str] = field(default_factory=dict)  # prop → TS type


@dataclass
class SceneTemplate:
    """
    Template for a Three.js scene rendered via @react-three/fiber.

    Contains the React Three Fiber component structure, default config,
    and estimated complexity for performance budgeting.
    """
    name: str                           # PascalCase component name
    scene_type: str                     # ThreeSceneType value
    description: str
    r3f_component: str                  # Main R3F component name
    camera_position: list[float] = field(default_factory=lambda: [0, 0, 5])
    camera_fov: int = 50
    default_config: dict[str, Any] = field(default_factory=dict)
    imports: list[ComponentImport] = field(default_factory=list)
    props_interface: dict[str, str] = field(default_factory=dict)
    estimated_polygons: int = 0
    estimated_particles: int = 0
    supports_interaction: bool = False


# ═══════════════════════════════════════════════════════════════════
# REACT IMPORT SETS
# ═══════════════════════════════════════════════════════════════════


CORE_IMPORTS = [
    ComponentImport(module="react", names=["memo", "useMemo"], default="React"),
]

MOTION_IMPORTS = [
    ComponentImport(module="framer-motion", names=["motion", "AnimatePresence"]),
]

R3F_IMPORTS = [
    ComponentImport(module="@react-three/fiber", names=["Canvas", "useFrame", "useThree"]),
    ComponentImport(module="@react-three/drei", names=[
        "OrbitControls", "Float", "Text3D", "Environment",
        "MeshDistortMaterial", "Sphere",
    ]),
]

CHART_IMPORTS = [
    ComponentImport(module="recharts", names=[
        "ResponsiveContainer", "BarChart", "Bar", "LineChart", "Line",
        "PieChart", "Pie", "Cell", "XAxis", "YAxis", "Tooltip", "Legend",
    ]),
]


# ═══════════════════════════════════════════════════════════════════
# LAYOUT → COMPONENT TEMPLATE REGISTRY
# ═══════════════════════════════════════════════════════════════════


COMPONENT_TEMPLATES: dict[str, ComponentTemplate] = {
    "center-focus": ComponentTemplate(
        name="CenterFocusSlide",
        layout_type="center-focus",
        description="Single focal point centered on slide. Ideal for hero/title slides.",
        default_animation=MotionPreset.SCALE_UP,
        supports_3d=True,
        container_class="flex flex-col items-center justify-center h-full text-center px-16",
        imports=CORE_IMPORTS + MOTION_IMPORTS,
        slot_names=["title", "subtitle", "tagline", "background"],
        props_interface={
            "title": "string",
            "subtitle": "string?",
            "tagline": "string?",
            "backgroundScene": "ThreeSceneConfig?",
        },
    ),
    "split-screen": ComponentTemplate(
        name="SplitScreenSlide",
        layout_type="split-screen",
        description="50/50 left-right split. Text on one side, visual on the other.",
        default_animation=MotionPreset.SLIDE_LEFT,
        supports_3d=True,
        container_class="grid grid-cols-2 h-full",
        grid_template="1fr 1fr",
        imports=CORE_IMPORTS + MOTION_IMPORTS,
        slot_names=["left", "right", "background"],
        props_interface={
            "leftContent": "ReactNode",
            "rightContent": "ReactNode",
            "visualSide": "'left' | 'right'",
        },
    ),
    "full-bleed": ComponentTemplate(
        name="FullBleedSlide",
        layout_type="full-bleed",
        description="Edge-to-edge visual with overlaid content. Dramatic impact.",
        default_animation=MotionPreset.FADE_IN,
        supports_3d=True,
        container_class="relative h-full w-full overflow-hidden",
        imports=CORE_IMPORTS + MOTION_IMPORTS,
        slot_names=["background", "overlay", "content"],
        props_interface={
            "backgroundMedia": "string | ThreeSceneConfig",
            "overlayOpacity": "number?",
            "contentPosition": "'center' | 'bottom-left' | 'bottom-right'",
        },
    ),
    "grid-2x2": ComponentTemplate(
        name="Grid2x2Slide",
        layout_type="grid-2x2",
        description="Four equal quadrants for comparison or feature showcase.",
        default_animation=MotionPreset.STAGGER_CHILDREN,
        container_class="grid grid-cols-2 grid-rows-2 gap-6 h-full p-8",
        grid_template="1fr 1fr / 1fr 1fr",
        imports=CORE_IMPORTS + MOTION_IMPORTS,
        slot_names=["title", "cell_1", "cell_2", "cell_3", "cell_4"],
        props_interface={
            "title": "string?",
            "cells": "GridCell[]",
        },
    ),
    "grid-3x1": ComponentTemplate(
        name="Grid3x1Slide",
        layout_type="grid-3x1",
        description="Three equal columns. Steps, pillars, or comparison.",
        default_animation=MotionPreset.STAGGER_CHILDREN,
        container_class="grid grid-cols-3 gap-6 h-full p-8",
        grid_template="1fr 1fr 1fr",
        imports=CORE_IMPORTS + MOTION_IMPORTS,
        slot_names=["title", "col_1", "col_2", "col_3"],
        props_interface={
            "title": "string?",
            "columns": "ColumnContent[]",
        },
    ),
    "text-left-visual-right": ComponentTemplate(
        name="TextLeftVisualRightSlide",
        layout_type="text-left-visual-right",
        description="Text content on left, visual/image/3D on right.",
        default_animation=MotionPreset.SLIDE_LEFT,
        supports_3d=True,
        supports_chart=True,
        container_class="grid grid-cols-[1.2fr_1fr] h-full",
        grid_template="1.2fr 1fr",
        imports=CORE_IMPORTS + MOTION_IMPORTS,
        slot_names=["text_content", "visual_content"],
        props_interface={
            "heading": "string",
            "body": "string | string[]",
            "visual": "ReactNode",
        },
    ),
    "text-right-visual-left": ComponentTemplate(
        name="TextRightVisualLeftSlide",
        layout_type="text-right-visual-left",
        description="Visual on left, text content on right.",
        default_animation=MotionPreset.SLIDE_RIGHT,
        supports_3d=True,
        supports_chart=True,
        container_class="grid grid-cols-[1fr_1.2fr] h-full",
        grid_template="1fr 1.2fr",
        imports=CORE_IMPORTS + MOTION_IMPORTS,
        slot_names=["visual_content", "text_content"],
        props_interface={
            "heading": "string",
            "body": "string | string[]",
            "visual": "ReactNode",
        },
    ),
    "top-bottom": ComponentTemplate(
        name="TopBottomSlide",
        layout_type="top-bottom",
        description="Stacked layout with header zone and content zone below.",
        default_animation=MotionPreset.SLIDE_UP,
        container_class="flex flex-col h-full",
        grid_template="auto 1fr",
        imports=CORE_IMPORTS + MOTION_IMPORTS,
        slot_names=["header", "content"],
        props_interface={
            "heading": "string",
            "content": "ReactNode",
        },
    ),
    "overlay": ComponentTemplate(
        name="OverlaySlide",
        layout_type="overlay",
        description="Content overlaid on a full-slide background with glassmorphism.",
        default_animation=MotionPreset.FADE_IN,
        supports_3d=True,
        container_class="relative h-full w-full",
        imports=CORE_IMPORTS + MOTION_IMPORTS,
        slot_names=["background", "card"],
        props_interface={
            "background": "string | ThreeSceneConfig",
            "cardContent": "ReactNode",
            "blur": "number?",
        },
    ),
    "bullets": ComponentTemplate(
        name="BulletsSlide",
        layout_type="bullets",
        description="Title with progressively-revealed bullet points.",
        default_animation=MotionPreset.STAGGER_CHILDREN,
        container_class="flex flex-col justify-center h-full px-16 py-12",
        imports=CORE_IMPORTS + MOTION_IMPORTS,
        slot_names=["title", "bullets"],
        props_interface={
            "title": "string",
            "bullets": "string[]",
            "icon": "string?",
        },
    ),
    "comparison": ComponentTemplate(
        name="ComparisonSlide",
        layout_type="comparison",
        description="Side-by-side comparison (us vs them, before/after).",
        default_animation=MotionPreset.STAGGER_CHILDREN,
        container_class="flex flex-col h-full px-12 py-8",
        imports=CORE_IMPORTS + MOTION_IMPORTS,
        slot_names=["title", "left_column", "right_column"],
        props_interface={
            "title": "string",
            "items": "ComparisonItem[]",
            "leftLabel": "string?",
            "rightLabel": "string?",
        },
    ),
    "timeline": ComponentTemplate(
        name="TimelineSlide",
        layout_type="timeline",
        description="Horizontal or vertical timeline with milestones.",
        default_animation=MotionPreset.STAGGER_CHILDREN,
        container_class="flex flex-col h-full px-12 py-8",
        imports=CORE_IMPORTS + MOTION_IMPORTS,
        slot_names=["title", "timeline_items"],
        props_interface={
            "title": "string",
            "items": "TimelineItem[]",
            "orientation": "'horizontal' | 'vertical'",
        },
    ),
    "kpi-dashboard": ComponentTemplate(
        name="KPIDashboardSlide",
        layout_type="kpi-dashboard",
        description="Metrics dashboard with animated counters and trend indicators.",
        default_animation=MotionPreset.STAGGER_CHILDREN,
        supports_chart=True,
        container_class="flex flex-col h-full px-12 py-8",
        imports=CORE_IMPORTS + MOTION_IMPORTS,
        slot_names=["title", "metrics", "chart"],
        props_interface={
            "title": "string",
            "metrics": "KPIMetric[]",
            "chart": "ChartConfig?",
        },
    ),
    "quote": ComponentTemplate(
        name="QuoteSlide",
        layout_type="quote",
        description="Full-slide quote with attribution and decorative marks.",
        default_animation=MotionPreset.FADE_IN,
        container_class="flex flex-col items-center justify-center h-full px-20 text-center",
        imports=CORE_IMPORTS + MOTION_IMPORTS,
        slot_names=["quote_text", "author", "background"],
        props_interface={
            "quote": "string",
            "author": "string?",
            "role": "string?",
        },
    ),
    "team-grid": ComponentTemplate(
        name="TeamGridSlide",
        layout_type="team-grid",
        description="Team member grid with photos, names, and roles.",
        default_animation=MotionPreset.STAGGER_CHILDREN,
        container_class="flex flex-col h-full px-12 py-8",
        imports=CORE_IMPORTS + MOTION_IMPORTS,
        slot_names=["title", "members"],
        props_interface={
            "title": "string",
            "members": "TeamMember[]",
        },
    ),
    "chart": ComponentTemplate(
        name="ChartSlide",
        layout_type="chart",
        description="Data visualization focus slide with full-width chart.",
        default_animation=MotionPreset.SCALE_UP,
        supports_chart=True,
        supports_3d=True,
        container_class="flex flex-col h-full px-12 py-8",
        imports=CORE_IMPORTS + MOTION_IMPORTS + CHART_IMPORTS,
        slot_names=["title", "chart", "footnote"],
        props_interface={
            "title": "string",
            "chartData": "ChartData",
            "chartType": "'bar' | 'line' | 'pie' | 'area'",
            "footnote": "string?",
        },
    ),
    "blank": ComponentTemplate(
        name="BlankSlide",
        layout_type="blank",
        description="Empty canvas for free-form element placement.",
        default_animation=MotionPreset.NONE,
        supports_3d=True,
        container_class="relative h-full w-full",
        imports=CORE_IMPORTS,
        slot_names=["elements"],
        props_interface={
            "elements": "SlideElement[]",
        },
    ),
}


# ═══════════════════════════════════════════════════════════════════
# THREE.JS SCENE TEMPLATES
# ═══════════════════════════════════════════════════════════════════


SCENE_TEMPLATES: dict[str, SceneTemplate] = {
    "globe": SceneTemplate(
        name="AnimatedGlobe",
        scene_type="globe",
        description="Interactive 3D globe for market/geographic data visualization.",
        r3f_component="AnimatedGlobe",
        camera_position=[0, 0, 2.5],
        camera_fov=45,
        default_config={
            "rotationSpeed": 0.001,
            "dotColor": "#38BDF8",
            "arcColor": "#7B2FF7",
            "globeColor": "#1a1a2e",
            "atmosphereColor": "#38BDF8",
            "atmosphereOpacity": 0.15,
            "pointSize": 0.02,
            "arcAltitude": 0.3,
        },
        imports=R3F_IMPORTS + [
            ComponentImport(module="three", names=["SphereGeometry", "MeshStandardMaterial"]),
        ],
        props_interface={
            "data": "GeoDataPoint[]",
            "highlightRegions": "string[]?",
            "rotationSpeed": "number?",
        },
        estimated_polygons=15_000,
        estimated_particles=500,
        supports_interaction=True,
    ),
    "bar-chart": SceneTemplate(
        name="ThreeDBarChart",
        scene_type="bar-chart",
        description="3D bar chart with depth, lighting, and animation.",
        r3f_component="ThreeDBarChart",
        camera_position=[3, 3, 3],
        camera_fov=50,
        default_config={
            "barColor": "#38BDF8",
            "barWidth": 0.4,
            "barGap": 0.2,
            "depth": 0.5,
            "cameraAngle": 25,
            "animate": True,
            "animationDuration": 1.5,
            "gridLines": True,
            "axisLabels": True,
            "lightIntensity": 0.8,
        },
        imports=R3F_IMPORTS,
        props_interface={
            "data": "BarDataPoint[]",
            "barColor": "string?",
            "depth": "number?",
            "animate": "boolean?",
        },
        estimated_polygons=3_000,
        estimated_particles=0,
        supports_interaction=True,
    ),
    "particles": SceneTemplate(
        name="ParticleField",
        scene_type="particles",
        description="Ambient particle field for hero/vision slide backgrounds.",
        r3f_component="ParticleField",
        camera_position=[0, 0, 3],
        camera_fov=60,
        default_config={
            "count": 5_000,
            "color": "#38BDF8",
            "speed": 0.0005,
            "connectionDistance": 150,
            "mouseInteraction": True,
            "particleSize": 0.015,
            "opacity": 0.6,
            "connectionOpacity": 0.1,
            "spread": 10,
        },
        imports=R3F_IMPORTS + [
            ComponentImport(module="three", names=["BufferGeometry", "PointsMaterial"]),
        ],
        props_interface={
            "count": "number?",
            "color": "string?",
            "speed": "number?",
            "mouseInteraction": "boolean?",
        },
        estimated_polygons=100,
        estimated_particles=5_000,
        supports_interaction=True,
    ),
    "scatter": SceneTemplate(
        name="ScatterPlot3D",
        scene_type="scatter",
        description="3D scatter plot for multi-dimensional data visualization.",
        r3f_component="ScatterPlot3D",
        camera_position=[4, 3, 4],
        camera_fov=45,
        default_config={
            "pointColor": "#38BDF8",
            "pointSize": 0.08,
            "axisLength": 3,
            "gridVisible": True,
            "labelVisible": True,
            "animate": True,
        },
        imports=R3F_IMPORTS,
        props_interface={
            "data": "ScatterDataPoint[]",
            "xLabel": "string?",
            "yLabel": "string?",
            "zLabel": "string?",
        },
        estimated_polygons=5_000,
        estimated_particles=200,
        supports_interaction=True,
    ),
    "floating-cards": SceneTemplate(
        name="FloatingCards",
        scene_type="floating-cards",
        description="3D floating cards for team or feature showcases.",
        r3f_component="FloatingCards",
        camera_position=[0, 0, 5],
        camera_fov=50,
        default_config={
            "layout": "orbit",
            "rotationSpeed": 0.003,
            "hoverScale": 1.1,
            "cardWidth": 1.5,
            "cardHeight": 2,
            "cardGap": 0.8,
            "reflective": True,
        },
        imports=R3F_IMPORTS + [
            ComponentImport(
                module="@react-three/drei",
                names=["RoundedBox", "Text", "useTexture"],
            ),
        ],
        props_interface={
            "cards": "CardData[]",
            "layout": "'orbit' | 'grid' | 'line'",
            "rotationSpeed": "number?",
        },
        estimated_polygons=2_000,
        estimated_particles=0,
        supports_interaction=True,
    ),
    "data-flow": SceneTemplate(
        name="DataFlowViz",
        scene_type="data-flow",
        description="Animated data flow visualization for architecture slides.",
        r3f_component="DataFlowViz",
        camera_position=[0, 0, 6],
        camera_fov=50,
        default_config={
            "animateFlow": True,
            "particleSpeed": 2,
            "nodeColor": "#38BDF8",
            "edgeColor": "#7B2FF7",
            "particleColor": "#FFFFFF",
            "nodeSize": 0.3,
            "edgeWidth": 0.02,
        },
        imports=R3F_IMPORTS + [
            ComponentImport(module="@react-three/drei", names=["Line", "Sphere"]),
        ],
        props_interface={
            "nodes": "FlowNode[]",
            "edges": "FlowEdge[]",
            "animateFlow": "boolean?",
        },
        estimated_polygons=4_000,
        estimated_particles=1_000,
        supports_interaction=True,
    ),
}


# ═══════════════════════════════════════════════════════════════════
# SLIDE WRAPPER TEMPLATE
# ═══════════════════════════════════════════════════════════════════


SLIDE_WRAPPER_TEMPLATE = {
    "name": "SlideWrapper",
    "description": "Universal wrapper for all slide components. Provides theme context, "
                   "animation orchestration, and navigation integration.",
    "imports": [
        ComponentImport(module="react", names=["memo", "useCallback", "useRef"], default="React"),
        ComponentImport(module="framer-motion", names=["motion", "AnimatePresence", "useInView"]),
    ],
    "props_interface": {
        "theme": "SlideTheme",
        "layout": "LayoutType",
        "index": "number",
        "isActive": "boolean",
        "transition": "TransitionConfig?",
        "children": "ReactNode",
    },
    "container_class": "slide-wrapper relative w-full h-full overflow-hidden",
}


# ═══════════════════════════════════════════════════════════════════
# UTILITY COMPONENTS
# ═══════════════════════════════════════════════════════════════════


UTILITY_COMPONENTS: dict[str, dict[str, Any]] = {
    "AnimatedCounter": {
        "description": "Animated number counter with easing for KPI metrics.",
        "props": {"value": "number", "duration": "number?", "prefix": "string?", "suffix": "string?"},
    },
    "ProgressBar": {
        "description": "Animated progress bar with percentage label.",
        "props": {"value": "number", "max": "number?", "color": "string?", "label": "string?"},
    },
    "GlassmorphismCard": {
        "description": "Frosted glass effect card with blur and transparency.",
        "props": {"blur": "number?", "opacity": "number?", "children": "ReactNode"},
    },
    "GradientText": {
        "description": "Text with CSS gradient fill.",
        "props": {"gradient": "string", "children": "ReactNode"},
    },
    "IconBadge": {
        "description": "Circular badge with icon and optional label.",
        "props": {"icon": "string", "label": "string?", "color": "string?"},
    },
    "ThreeSceneContainer": {
        "description": "Wrapper for lazy-loaded Three.js Canvas with skeleton placeholder.",
        "props": {
            "sceneType": "ThreeSceneType",
            "config": "ThreeSceneConfig",
            "fallback": "ReactNode?",
            "quality": "QualityLevel?",
        },
    },
}


# ═══════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════


def get_component_template(layout_type: str) -> Optional[ComponentTemplate]:
    """Look up component template by LayoutType value."""
    return COMPONENT_TEMPLATES.get(layout_type)


def get_scene_template(scene_type: str) -> Optional[SceneTemplate]:
    """Look up Three.js scene template by ThreeSceneType value."""
    return SCENE_TEMPLATES.get(scene_type)


def get_motion_variant(preset: str) -> dict[str, Any]:
    """Get Framer Motion variant definition by preset name."""
    return dict(MOTION_VARIANTS.get(preset, MOTION_VARIANTS["none"]))


def list_component_names() -> list[str]:
    """Return all available component template names."""
    return [t.name for t in COMPONENT_TEMPLATES.values()]


def list_scene_names() -> list[str]:
    """Return all available Three.js scene template names."""
    return [t.name for t in SCENE_TEMPLATES.values()]


def get_imports_for_layout(layout_type: str, has_3d: bool = False, has_chart: bool = False) -> list[ComponentImport]:
    """
    Collect all required imports for a layout, optionally including
    Three.js and chart imports.
    """
    template = get_component_template(layout_type)
    if template is None:
        return list(CORE_IMPORTS)

    imports = list(template.imports)

    if has_3d and template.supports_3d:
        # Add R3F imports if not already present
        r3f_modules = {i.module for i in imports}
        for imp in R3F_IMPORTS:
            if imp.module not in r3f_modules:
                imports.append(imp)

    if has_chart and template.supports_chart:
        chart_modules = {i.module for i in imports}
        for imp in CHART_IMPORTS:
            if imp.module not in chart_modules:
                imports.append(imp)

    return imports


def get_3d_capable_layouts() -> list[str]:
    """Return layout types that support Three.js scene integration."""
    return [lt for lt, t in COMPONENT_TEMPLATES.items() if t.supports_3d]


def get_chart_capable_layouts() -> list[str]:
    """Return layout types that support chart rendering."""
    return [lt for lt, t in COMPONENT_TEMPLATES.items() if t.supports_chart]
