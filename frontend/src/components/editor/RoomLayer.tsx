import React from 'react';
import { Group, Line, Text } from 'react-konva';
import { useEditorStore } from '../../store/editorStore';

export const RoomLayer: React.FC = () => {
  const { sceneGraph, selectedObjectId, selectObject } = useEditorStore();

  if (!sceneGraph) return null;

  return (
    <Group>
      {sceneGraph.rooms.map((room) => {
        const isSelected = selectedObjectId === room.id;
        
        // Flatten polygon coordinates for Konva Line component
        const flatPoints = room.polygon.reduce((acc, point) => [...acc, point[0], point[1]], [] as number[]);
        
        return (
          <Group key={room.id} onClick={() => selectObject(room.id, 'room')} onTap={() => selectObject(room.id, 'room')}>
            <Line
              points={flatPoints}
              fill={isSelected ? 'rgba(100, 150, 255, 0.4)' : 'rgba(200, 200, 200, 0.2)'}
              stroke={isSelected ? 'blue' : 'gray'}
              strokeWidth={2}
              closed
            />
            {room.centroid && (
              <Text
                text={room.label || room.type}
                x={room.centroid[0] - 30}
                y={room.centroid[1] - 10}
                fontSize={16}
                fill="black"
              />
            )}
          </Group>
        );
      })}
    </Group>
  );
};
