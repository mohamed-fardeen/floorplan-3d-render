import React, { useState } from 'react';
import { Stage, Layer, Text } from 'react-konva';
import { useEditorStore } from '../../store/editorStore';
import { WallLayer } from './WallLayer';
import { RoomLayer } from './RoomLayer';
import { DoorWindowLayer } from './DoorWindowLayer';

export const EditorCanvas: React.FC = () => {
  const { sceneGraph, selectObject } = useEditorStore();
  
  // Basic zoom and pan state
  const [scale, setScale] = useState(1);
  const [position, setPosition] = useState({ x: 0, y: 0 });

  const handleWheel = (e: any) => {
    e.evt.preventDefault();
    const scaleBy = 1.1;
    const stage = e.target.getStage();
    const oldScale = stage.scaleX();
    const pointer = stage.getPointerPosition();

    const mousePointTo = {
      x: (pointer.x - stage.x()) / oldScale,
      y: (pointer.y - stage.y()) / oldScale,
    };

    const newScale = e.evt.deltaY < 0 ? oldScale * scaleBy : oldScale / scaleBy;
    setScale(newScale);
    setPosition({
      x: pointer.x - mousePointTo.x * newScale,
      y: pointer.y - mousePointTo.y * newScale,
    });
  };

  const handleStageClick = (e: any) => {
    // If clicked on empty space, deselect
    if (e.target === e.target.getStage()) {
      selectObject(null, null);
    }
  };

  return (
    <div className="flex-grow bg-gray-200 overflow-hidden relative">
      <Stage
        width={window.innerWidth - 256 - 320} // Subtract Sidebar and PropertiesPanel width (roughly)
        height={window.innerHeight}
        onWheel={handleWheel}
        onClick={handleStageClick}
        scaleX={scale}
        scaleY={scale}
        x={position.x}
        y={position.y}
        draggable
      >
        <Layer>
          {sceneGraph ? (
            <>
              <RoomLayer />
              <WallLayer />
              <DoorWindowLayer />
            </>
          ) : (
            <Text
              text="No Scene Graph Loaded. Please upload an image."
              x={50}
              y={50}
              fontSize={20}
              fill="gray"
            />
          )}
        </Layer>
      </Stage>
    </div>
  );
};

