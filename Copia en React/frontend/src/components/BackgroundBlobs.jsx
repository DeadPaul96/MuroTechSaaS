import React from 'react';

const BackgroundBlobs = () => {
  return (
    <div className="bg-blobs">
      <div className="blob"></div>
      <div className="blob blob-2"></div>
      <div className="blob blob-3"></div>
      <canvas id="particles-canvas" style={{ position: 'fixed', top: 0, left: 0, zIndex: -1 }}></canvas>
    </div>
  );
};

export default BackgroundBlobs;
