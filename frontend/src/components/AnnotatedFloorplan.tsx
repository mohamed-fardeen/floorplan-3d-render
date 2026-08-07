import React, { useRef, useState, useEffect, useCallback } from 'react';
import type { SceneGraph } from '../types/schema';

interface AnnotatedFloorplanProps {
  imageUrl: string;
  sceneGraph: SceneGraph;
}

export const AnnotatedFloorplan: React.FC<AnnotatedFloorplanProps> = ({ imageUrl, sceneGraph }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [imageSize, setImageSize] = useState<{ width: number; height: number } | null>(null);
  const [scale, setScale] = useState(1);

  useEffect(() => {
    const img = new Image();
    img.src = imageUrl;
    img.onload = () => {
      setImageSize({ width: img.naturalWidth, height: img.naturalHeight });
    };
    img.onerror = () => {
      setImageSize(null);
    };
  }, [imageUrl]);

  useEffect(() => {
    const el = containerRef.current;
    if (!el || !imageSize) return;

    const updateScale = () => {
      if (imageSize.width > el.clientWidth) {
        setScale(el.clientWidth / imageSize.width);
      } else {
        setScale(1);
      }
    };

    updateScale();
    const observer = new ResizeObserver(updateScale);
    observer.observe(el);
    return () => observer.disconnect();
  }, [imageSize]);

  const scaleM = sceneGraph.metadata.scale_pixel_to_meter;
  const mToPx = scaleM > 0 ? 1 / scaleM : 51.2;

  /** Scene graph metres (y-up) → image pixels (y-down). */
  const toPx = useCallback(
    (xm: number, ym: number) => {
      if (!imageSize) return { x: 0, y: 0 };
      return {
        x: xm * mToPx,
        y: imageSize.height - ym * mToPx,
      };
    },
    [imageSize, mToPx],
  );

  const scaledHeight = imageSize ? imageSize.height * scale : 0;

  return (
    <div className="w-full max-w-4xl mx-auto mt-8 bg-white p-4 rounded-lg shadow-md">
      <h3 className="text-xl font-bold mb-4">Annotated Floor Plan</h3>
      <div
        ref={containerRef}
        className="relative w-full overflow-auto bg-gray-100 rounded border border-gray-300 flex justify-center"
        style={{ maxHeight: '70vh', minHeight: scaledHeight || 256 }}
      >
        {imageSize ? (
          <div
            className="relative"
            style={{
              width: imageSize.width * scale,
              height: scaledHeight,
              transformOrigin: 'top left',
            }}
          >
            <div
              className="relative"
              style={{
                width: imageSize.width,
                height: imageSize.height,
                transform: scale !== 1 ? `scale(${scale})` : undefined,
                transformOrigin: 'top left',
              }}
            >
              <img
                src={imageUrl}
                alt="Floor plan"
                className="absolute top-0 left-0 block"
                style={{ width: imageSize.width, height: imageSize.height }}
              />
              <svg
                className="absolute top-0 left-0 pointer-events-none"
                width={imageSize.width}
                height={imageSize.height}
                viewBox={`0 0 ${imageSize.width} ${imageSize.height}`}
              >
                {sceneGraph.rooms?.map((room) => {
                  if (!room.polygon || room.polygon.length < 3) return null;
                  const pts = room.polygon
                    .map(([x, y]) => {
                      const p = toPx(x, y);
                      return `${p.x},${p.y}`;
                    })
                    .join(' ');
                  return (
                    <polygon
                      key={room.id}
                      points={pts}
                      fill="rgba(34, 197, 94, 0.15)"
                      stroke="rgba(34, 197, 94, 0.8)"
                      strokeWidth={2}
                    />
                  );
                })}

                {sceneGraph.walls?.map((wall) => {
                  const p1 = toPx(wall.start[0], wall.start[1]);
                  const p2 = toPx(wall.end[0], wall.end[1]);
                  const thickPx = Math.max((wall.thickness || 0.1) * mToPx, 3);
                  // Extend each wall by half its thickness along its own
                  // direction so the two walls at a corner overlap. The raw
                  // wall endpoints often sit a few pixels apart after the
                  // topology snaps to axis, so without this extension the
                  // annotation shows visible gaps at junctions.
                  const dxRaw = p2.x - p1.x;
                  const dyRaw = p2.y - p1.y;
                  const lenPx = Math.hypot(dxRaw, dyRaw) || 1;
                  const ux = dxRaw / lenPx;
                  const uy = dyRaw / lenPx;
                  const halfPx = thickPx / 2;
                  const x1 = p1.x - ux * halfPx;
                  const y1 = p1.y - uy * halfPx;
                  const x2 = p2.x + ux * halfPx;
                  const y2 = p2.y + uy * halfPx;
                  return (
                    <line
                      key={wall.id}
                      x1={x1}
                      y1={y1}
                      x2={x2}
                      y2={y2}
                      stroke="rgba(239, 68, 68, 0.85)"
                      strokeWidth={thickPx}
                      strokeLinecap="butt"
                    />
                  );
                })}

                {sceneGraph.doors?.map((door) => {
                  const c = toPx(door.center[0], door.center[1]);
                  const r = Math.max((door.width / 2) * mToPx, 4);
                  return (
                    <circle
                      key={door.id}
                      cx={c.x}
                      cy={c.y}
                      r={r}
                      fill="rgba(59, 130, 246, 0.55)"
                      stroke="#2563eb"
                      strokeWidth={2}
                    />
                  );
                })}

                {sceneGraph.windows?.map((window) => {
                  const c = toPx(window.center[0], window.center[1]);
                  const halfW = Math.max((window.width / 2) * mToPx, 4);
                  // Orient the window rectangle along its host wall:
                  // windows on vertical walls are drawn as tall rectangles,
                  // windows on horizontal walls as wide ones. We compute
                  // the wall direction in image pixels and rotate the
                  // rectangle so the long edge sits flush with the wall.
                  const hostWall = sceneGraph.walls.find((w) => w.id === window.wall_id);
                  let angleDeg = 0;
                  if (hostWall) {
                    const wA = toPx(hostWall.start[0], hostWall.start[1]);
                    const wB = toPx(hostWall.end[0], hostWall.end[1]);
                    angleDeg = Math.atan2(wB.y - wA.y, wB.x - wA.x) * (180 / Math.PI);
                  }
                  return (
                    <rect
                      key={window.id}
                      x={c.x - halfW}
                      y={c.y - 5}
                      width={halfW * 2}
                      height={10}
                      fill="rgba(6, 182, 212, 0.55)"
                      stroke="#0891b2"
                      strokeWidth={2}
                      transform={`rotate(${angleDeg} ${c.x} ${c.y})`}
                    />
                  );
                })}
              </svg>
            </div>
          </div>
        ) : (
          <div className="flex items-center justify-center h-64 text-gray-500">
            Loading image...
          </div>
        )}
      </div>
    </div>
  );
};
