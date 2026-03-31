import { useEffect, useRef } from 'react';
import * as Cesium from 'cesium';

/**
 * OverlayEngine - AI-Driven 3D Overlay System
 * Renders visual annotations (circles, arrows, labels, paths) on the Cesium map
 * based on commands from the AI agents
 */
const OverlayEngine = ({ viewer, overlays = [], onOverlayClick }) => {
  const entitiesRef = useRef([]);

  useEffect(() => {
    if (!viewer || !overlays || overlays.length === 0) return;

    // Clear previous overlays
    entitiesRef.current.forEach(entity => {
      viewer.entities.remove(entity);
    });
    entitiesRef.current = [];

    // Render new overlays
    overlays.forEach(overlay => {
      try {
        const entity = renderOverlay(viewer, overlay);
        if (entity) {
          entitiesRef.current.push(entity);
          
          // Add click handler if provided
          if (onOverlayClick) {
            entity.overlay = overlay;
          }
        }
      } catch (error) {
        console.error('Error rendering overlay:', overlay, error);
      }
    });

    // Cleanup on unmount
    return () => {
      entitiesRef.current.forEach(entity => {
        viewer.entities.remove(entity);
      });
      entitiesRef.current = [];
    };
  }, [viewer, overlays, onOverlayClick]);

  return null; // This component doesn't render DOM elements
};

/**
 * Render individual overlay based on type
 */
function renderOverlay(viewer, overlay) {
  const { type, data, style = {} } = overlay;

  switch (type) {
    case 'circle':
      return renderCircle(viewer, data, style);
    case 'polygon':
      return renderPolygon(viewer, data, style);
    case 'arrow':
      return renderArrow(viewer, data, style);
    case 'label':
      return renderLabel(viewer, data, style);
    case 'path':
      return renderPath(viewer, data, style);
    case 'marker':
      return renderMarker(viewer, data, style);
    case 'heatmap':
      return renderHeatmap(viewer, data, style);
    default:
      console.warn('Unknown overlay type:', type);
      return null;
  }
}

/**
 * Render a circle (radius ring)
 */
function renderCircle(viewer, data, style) {
  const { lat, lng, radius = 1000 } = data;
  const { color = Cesium.Color.CYAN, opacity = 0.3, outline = true } = style;

  return viewer.entities.add({
    position: Cesium.Cartesian3.fromDegrees(lng, lat),
    ellipse: {
      semiMinorAxis: radius,
      semiMajorAxis: radius,
      material: color.withAlpha(opacity),
      outline: outline,
      outlineColor: color,
      outlineWidth: 2,
      height: 0
    }
  });
}

/**
 * Render a polygon (area boundary)
 */
function renderPolygon(viewer, data, style) {
  const { coordinates } = data; // [[lng, lat], [lng, lat], ...]
  const { color = Cesium.Color.YELLOW, opacity = 0.4, outline = true } = style;

  if (!coordinates || coordinates.length < 3) {
    console.warn('Polygon requires at least 3 coordinates');
    return null;
  }

  const positions = coordinates.map(coord => 
    Cesium.Cartesian3.fromDegrees(coord[0], coord[1])
  );

  return viewer.entities.add({
    polygon: {
      hierarchy: new Cesium.PolygonHierarchy(positions),
      material: color.withAlpha(opacity),
      outline: outline,
      outlineColor: color,
      outlineWidth: 2,
      height: 0
    }
  });
}

/**
 * Render an arrow (directional line)
 */
function renderArrow(viewer, data, style) {
  const { from, to } = data; // from: {lat, lng}, to: {lat, lng}
  const { color = Cesium.Color.RED, width = 3 } = style;

  const positions = [
    Cesium.Cartesian3.fromDegrees(from.lng, from.lat),
    Cesium.Cartesian3.fromDegrees(to.lng, to.lat)
  ];

  return viewer.entities.add({
    polyline: {
      positions: positions,
      width: width,
      material: new Cesium.PolylineArrowMaterialProperty(color),
      clampToGround: true
    }
  });
}

/**
 * Render a label (text annotation)
 */
function renderLabel(viewer, data, style) {
  const { lat, lng, text } = data;
  const { 
    color = Cesium.Color.WHITE, 
    fontSize = 14, 
    backgroundColor = Cesium.Color.BLACK.withAlpha(0.7),
    showBackground = true,
    pixelOffset = new Cesium.Cartesian2(0, -20)
  } = style;

  return viewer.entities.add({
    position: Cesium.Cartesian3.fromDegrees(lng, lat),
    label: {
      text: text,
      font: `${fontSize}px sans-serif`,
      fillColor: color,
      showBackground: showBackground,
      backgroundColor: backgroundColor,
      backgroundPadding: new Cesium.Cartesian2(8, 4),
      pixelOffset: pixelOffset,
      disableDepthTestDistance: Number.POSITIVE_INFINITY
    }
  });
}

/**
 * Render a path (polyline)
 */
function renderPath(viewer, data, style) {
  const { coordinates } = data; // [[lng, lat], [lng, lat], ...]
  const { color = Cesium.Color.BLUE, width = 4, dashed = false } = style;

  if (!coordinates || coordinates.length < 2) {
    console.warn('Path requires at least 2 coordinates');
    return null;
  }

  const positions = coordinates.map(coord => 
    Cesium.Cartesian3.fromDegrees(coord[0], coord[1])
  );

  const material = dashed 
    ? new Cesium.PolylineDashMaterialProperty({ color })
    : color;

  return viewer.entities.add({
    polyline: {
      positions: positions,
      width: width,
      material: material,
      clampToGround: true
    }
  });
}

/**
 * Render a marker (pin/point)
 */
function renderMarker(viewer, data, style) {
  const { lat, lng, icon = '📍' } = data;
  const { color = Cesium.Color.RED, scale = 1.0 } = style;

  return viewer.entities.add({
    position: Cesium.Cartesian3.fromDegrees(lng, lat),
    point: {
      pixelSize: 10 * scale,
      color: color,
      outlineColor: Cesium.Color.WHITE,
      outlineWidth: 2,
      disableDepthTestDistance: Number.POSITIVE_INFINITY
    },
    label: {
      text: icon,
      font: `${20 * scale}px sans-serif`,
      pixelOffset: new Cesium.Cartesian2(0, -20),
      disableDepthTestDistance: Number.POSITIVE_INFINITY
    }
  });
}

/**
 * Render a heatmap overlay (grid of colored cells)
 */
function renderHeatmap(viewer, data, style) {
  const { cells } = data; // [{lat, lng, value}, ...]
  const { colorScale = 'heat', opacity = 0.6 } = style;

  if (!cells || cells.length === 0) return null;

  const entities = [];

  cells.forEach(cell => {
    const color = getHeatmapColor(cell.value, colorScale);
    const entity = viewer.entities.add({
      position: Cesium.Cartesian3.fromDegrees(cell.lng, cell.lat),
      ellipse: {
        semiMinorAxis: cell.radius || 100,
        semiMajorAxis: cell.radius || 100,
        material: color.withAlpha(opacity),
        height: 0
      }
    });
    entities.push(entity);
  });

  return entities[0]; // Return first entity as representative
}

/**
 * Get color for heatmap value (0-1 normalized)
 */
function getHeatmapColor(value, colorScale) {
  // Normalize value to 0-1
  const normalized = Math.max(0, Math.min(1, value));

  if (colorScale === 'heat') {
    // Blue -> Green -> Yellow -> Red
    if (normalized < 0.25) {
      return Cesium.Color.BLUE.lerp(Cesium.Color.GREEN, normalized * 4);
    } else if (normalized < 0.5) {
      return Cesium.Color.GREEN.lerp(Cesium.Color.YELLOW, (normalized - 0.25) * 4);
    } else if (normalized < 0.75) {
      return Cesium.Color.YELLOW.lerp(Cesium.Color.ORANGE, (normalized - 0.5) * 4);
    } else {
      return Cesium.Color.ORANGE.lerp(Cesium.Color.RED, (normalized - 0.75) * 4);
    }
  } else if (colorScale === 'green-red') {
    return Cesium.Color.GREEN.lerp(Cesium.Color.RED, normalized);
  } else {
    return Cesium.Color.GRAY.lerp(Cesium.Color.WHITE, normalized);
  }
}

export default OverlayEngine;
