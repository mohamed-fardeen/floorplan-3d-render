import React, { Suspense } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, useGLTF, Stage } from '@react-three/drei';

interface ModelViewerProps {
  glbUrl: string;
}

const Model: React.FC<{ url: string }> = ({ url }) => {
  const { scene } = useGLTF(url);
  return <primitive object={scene} />;
};

export const ModelViewer: React.FC<ModelViewerProps> = ({ glbUrl }) => {
  if (!glbUrl) return null;

  return (
    <div className="w-full max-w-4xl mx-auto h-[500px] bg-gray-100 rounded-lg shadow-inner mt-6 overflow-hidden relative">
      <div className="absolute top-4 left-4 z-10 bg-white px-3 py-1 rounded shadow text-sm font-bold text-gray-700">
        3D Preview
      </div>
      <Canvas shadows camera={{ position: [0, 5, 10], fov: 50 }}>
        <Suspense fallback={null}>
          <Stage environment="city" intensity={0.5}>
            <Model url={glbUrl} />
          </Stage>
        </Suspense>
        <OrbitControls makeDefault />
      </Canvas>
    </div>
  );
};
