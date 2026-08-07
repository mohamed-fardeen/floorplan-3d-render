import React from 'react';
import { Group, Line, Circle } from 'react-konva';
import { useEditorStore } from '../../store/editorStore';

export const WallLayer: React.FC = () => {
  const { sceneGraph, selectedObjectId, selectObject, updateWall } = useEditorStore();

  if (!sceneGraph) return null;

  return (
    <Group>
      {sceneGraph.walls.map((wall) => {
        if (!wall || !wall.start || !wall.end || !Array.isArray(wall.start) || !Array.isArray(wall.end)) return null;
        const isSelected = selectedObjectId === wall.id;
        const sx = wall.start[0] ?? 0;
        const sy = wall.start[1] ?? 0;
        const ex = wall.end[0] ?? 0;
        const ey = wall.end[1] ?? 0;
        
        return (
          <Group key={wall.id}>
            <Line
              points={[sx, sy, ex, ey]}
              stroke={isSelected ? 'blue' : 'black'}
              strokeWidth={wall.thickness || 10}
              lineCap="square"
              onClick={() => selectObject(wall.id, 'wall')}
              onTap={() => selectObject(wall.id, 'wall')}
            />
            
            {isSelected && (
              <>
                <Circle
                  x={sx}
                  y={sy}
                  radius={8}
                  fill="blue"
                  draggable
                  onDragEnd={(e) => {
                    updateWall(wall.id, { start: [e.target.x(), e.target.y()] });
                  }}
                />
                <Circle
                  x={ex}
                  y={ey}
                  radius={8}
                  fill="blue"
                  draggable
                  onDragEnd={(e) => {
                    updateWall(wall.id, { end: [e.target.x(), e.target.y()] });
                  }}
                />
              </>
            )}
          </Group>
        );
      })}
    </Group>
  );
};
