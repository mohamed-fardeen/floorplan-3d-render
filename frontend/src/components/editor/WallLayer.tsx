import React from 'react';
import { Group, Line, Circle } from 'react-konva';
import { useEditorStore } from '../../store/editorStore';

export const WallLayer: React.FC = () => {
  const { sceneGraph, selectedObjectId, selectObject, updateWall } = useEditorStore();

  if (!sceneGraph) return null;

  return (
    <Group>
      {sceneGraph.walls.map((wall) => {
        const isSelected = selectedObjectId === wall.id;
        
        return (
          <Group key={wall.id}>
            <Line
              points={[wall.start[0], wall.start[1], wall.end[0], wall.end[1]]}
              stroke={isSelected ? 'blue' : 'black'}
              strokeWidth={wall.thickness || 10}
              lineCap="square"
              onClick={() => selectObject(wall.id, 'wall')}
              onTap={() => selectObject(wall.id, 'wall')}
            />
            
            {isSelected && (
              <>
                <Circle
                  x={wall.start[0]}
                  y={wall.start[1]}
                  radius={8}
                  fill="blue"
                  draggable
                  onDragEnd={(e) => {
                    updateWall(wall.id, { start: [e.target.x(), e.target.y()] });
                  }}
                />
                <Circle
                  x={wall.end[0]}
                  y={wall.end[1]}
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
