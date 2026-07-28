import React from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import { useEditorStore } from '../../store/editorStore';

const Wall3D: React.FC<{ start: [number, number], end: [number, number], thickness: number }> = ({ start, end, thickness }) => {
  const dx = end[0] - start[0];
  const dy = end[1] - start[1];
  const length = Math.sqrt(dx * dx + dy * dy);
  const angle = Math.atan2(dy, dx);
  
  // Scale down coordinates since pixel coordinates are large
  const scale = 0.01;
  const height = 300 * scale; 
  
  const centerX = (start[0] + end[0]) / 2 * scale;
  const centerZ = (start[1] + end[1]) / 2 * scale; // Note: Y in 2D is Z in 3D

  return (
    <mesh position={[centerX, height / 2, centerZ]} rotation={[0, -angle, 0]}>
      <boxGeometry args={[length * scale, height, thickness * scale]} />
      <meshStandardMaterial color="#eeeeee" />
    </mesh>
  );
};

export const Preview3D: React.FC = () => {
  const { sceneGraph } = useEditorStore();

  if (!sceneGraph) {
    return (
      <div className="absolute bottom-4 right-80 w-64 h-64 bg-white border border-gray-300 shadow-lg p-2 flex items-center justify-center">
        <p className="text-gray-500 text-sm text-center">No Scene Graph</p>
      </div>
    );
  }

  return (
    <div className="absolute bottom-4 right-[340px] w-80 h-80 bg-white border border-gray-300 shadow-lg rounded-lg overflow-hidden">
      <div className="bg-gray-100 p-2 text-xs font-bold text-center border-b border-gray-300">Live 3D Preview</div>
      <div className="w-full h-full relative" style={{ height: 'calc(100% - 33px)' }}>
        <Canvas camera={{ position: [0, 20, 20], fov: 50 }}>
          <ambientLight intensity={0.5} />
          <directionalLight position={[10, 10, 5]} intensity={1} />
          
          <group position={[0, 0, 0]}>
            {sceneGraph.walls.map((wall) => (
              <Wall3D 
                key={wall.id}
                start={wall.start}
                end={wall.end}
                thickness={wall.thickness || 10}
              />
            ))}
          </group>
          
          {/* Base plane */}
          <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.1, 0]}>
            <planeGeometry args={[100, 100]} />
            <meshStandardMaterial color="#cccccc" />
          </mesh>

          <OrbitControls makeDefault />
        </Canvas>
      </div>
    </div>
  );
};
