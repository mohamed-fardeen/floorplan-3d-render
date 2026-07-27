import React from 'react';
import { Group, Rect, Circle } from 'react-konva';
import { useEditorStore } from '../../store/editorStore';

export const DoorWindowLayer: React.FC = () => {
  const { sceneGraph, selectedObjectId, selectObject, updateDoor, updateWindow } = useEditorStore();

  if (!sceneGraph) return null;

  return (
    <Group>
      {/* Render Doors */}
      {sceneGraph.doors.map((door) => {
        const isSelected = selectedObjectId === door.id;
        
        return (
          <Group 
            key={door.id} 
            x={door.center[0]} 
            y={door.center[1]}
            onClick={() => selectObject(door.id, 'door')} 
            onTap={() => selectObject(door.id, 'door')}
            draggable={isSelected}
            onDragEnd={(e) => {
              updateDoor(door.id, { center: [e.target.x(), e.target.y()] });
            }}
          >
            <Rect
              x={-door.width / 2}
              y={-10}
              width={door.width}
              height={20}
              fill="white"
              stroke={isSelected ? 'blue' : 'orange'}
              strokeWidth={2}
            />
            {/* Simple representation of an open door swing */}
            {door.is_open && (
              <Circle
                x={door.width / 2}
                y={-10}
                radius={door.width}
                stroke="orange"
                strokeWidth={1}
                dash={[5, 5]}
              />
            )}
          </Group>
        );
      })}

      {/* Render Windows */}
      {sceneGraph.windows.map((window) => {
        const isSelected = selectedObjectId === window.id;
        
        return (
          <Group 
            key={window.id} 
            x={window.center[0]} 
            y={window.center[1]}
            onClick={() => selectObject(window.id, 'window')} 
            onTap={() => selectObject(window.id, 'window')}
            draggable={isSelected}
            onDragEnd={(e) => {
              updateWindow(window.id, { center: [e.target.x(), e.target.y()] });
            }}
          >
            <Rect
              x={-window.width / 2}
              y={-5}
              width={window.width}
              height={10}
              fill="lightblue"
              stroke={isSelected ? 'blue' : 'cyan'}
              strokeWidth={2}
            />
          </Group>
        );
      })}
    </Group>
  );
};
