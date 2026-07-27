import React, { useRef, useState, useEffect } from 'react';
import type { SceneGraph } from '../types/schema';

interface AnnotatedFloorplanProps {
  imageUrl: string;
  sceneGraph: SceneGraph;
}

export const AnnotatedFloorplan: React.FC<AnnotatedFloorplanProps> = ({ imageUrl, sceneGraph }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [imageSize, setImageSize] = useState<{ width: number; height: number } | null>(null);

  useEffect(() => {
    const img = new Image();
    img.src = imageUrl;
    img.onload = () => {
      setImageSize({ width: img.naturalWidth, height: img.naturalHeight });
    };
  }, [imageUrl]);

  return (
    <div className="w-full max-w-4xl mx-auto mt-8 bg-white p-4 rounded-lg shadow-md">
      <h3 className="text-xl font-bold mb-4">Annotated Floor Plan</h3>
      <div 
        ref={containerRef}
        className="relative w-full overflow-auto bg-gray-100 rounded border border-gray-300 flex justify-center"
        style={{ maxHeight: '70vh' }}
      >
        {imageSize ? (
          <div 
            className="relative" 
            style={{ 
              width: imageSize.width, 
              height: imageSize.height,
              transformOrigin: 'top left',
              // Scale down to fit width if image is wider than container
              transform: containerRef.current && imageSize.width > containerRef.current.clientWidth 
                ? `scale(${containerRef.current.clientWidth / imageSize.width})` 
                : 'none'
            }}
          >
            <img 
              src={imageUrl} 
              alt="Floor plan" 
              className="absolute top-0 left-0"
              style={{ width: imageSize.width, height: imageSize.height }}
            />
            <svg 
              className="absolute top-0 left-0 pointer-events-none"
              width={imageSize.width} 
              height={imageSize.height}
              viewBox={`0 0 ${imageSize.width} ${imageSize.height}`}
            >
              {/* Walls */}
              {sceneGraph.walls?.map(wall => (
                <line
                  key={wall.id}
                  x1={wall.start[0]}
                  y1={wall.start[1]}
                  x2={wall.end[0]}
                  y2={wall.end[1]}
                  stroke="rgba(0, 0, 255, 0.5)"
                  strokeWidth={wall.thickness || 5}
                  strokeLinecap="round"
                />
              ))}
              
              {/* Doors */}
              {sceneGraph.doors?.map(door => (
                <circle
                  key={door.id}
                  cx={door.center[0]}
                  cy={door.center[1]}
                  r={door.width / 2 || 10}
                  fill="rgba(0, 255, 0, 0.5)"
                  stroke="green"
                  strokeWidth={2}
                />
              ))}

              {/* Windows */}
              {sceneGraph.windows?.map(window => (
                <rect
                  key={window.id}
                  x={window.center[0] - (window.width / 2 || 10)}
                  y={window.center[1] - 5}
                  width={window.width || 20}
                  height={10}
                  fill="rgba(255, 165, 0, 0.5)"
                  stroke="orange"
                  strokeWidth={2}
                />
              ))}
            </svg>
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
