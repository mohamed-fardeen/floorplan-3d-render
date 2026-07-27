import React, { useCallback, useState } from 'react';

interface UploadAreaProps {
  onStartPipeline: (file: File) => void;
  disabled: boolean;
}

export const UploadArea: React.FC<UploadAreaProps> = ({ onStartPipeline, disabled }) => {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selected = e.target.files[0];
      setFile(selected);
      setPreview(URL.createObjectURL(selected));
    }
  };

  const handleDrop = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    if (disabled) return;
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const selected = e.dataTransfer.files[0];
      setFile(selected);
      setPreview(URL.createObjectURL(selected));
    }
  }, [disabled]);

  const handleSubmit = () => {
    if (file) onStartPipeline(file);
  };

  return (
    <div className="w-full max-w-2xl mx-auto p-6 bg-white rounded-lg shadow-md">
      <h2 className="text-2xl font-bold mb-4">Upload Floor Plan</h2>
      <div 
        className={`border-2 border-dashed rounded-lg p-8 text-center ${disabled ? 'bg-gray-100 cursor-not-allowed' : 'bg-gray-50 hover:bg-gray-100 cursor-pointer'} ${preview ? 'border-indigo-500' : 'border-gray-300'}`}
        onDragOver={(e) => e.preventDefault()}
        onDrop={handleDrop}
        onClick={() => !disabled && document.getElementById('fileUpload')?.click()}
      >
        <input 
          id="fileUpload" 
          type="file" 
          accept="image/png, image/jpeg, image/jpg" 
          className="hidden" 
          onChange={handleFileChange} 
          disabled={disabled}
        />
        
        {preview ? (
          <img src={preview} alt="Preview" className="max-h-64 mx-auto mb-4" />
        ) : (
          <div className="text-gray-500">
            <p className="mb-2">Drag and drop your floor plan here</p>
            <p className="text-sm">Supports PNG, JPG, JPEG</p>
          </div>
        )}
      </div>

      <div className="mt-6 flex justify-end">
        <button
          onClick={handleSubmit}
          disabled={!file || disabled}
          className="bg-indigo-600 text-white px-6 py-2 rounded-md hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium transition-colors"
        >
          {disabled ? 'Processing...' : 'Generate 3D Model'}
        </button>
      </div>
    </div>
  );
};
