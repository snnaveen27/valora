import React, { useEffect, useRef, useState } from 'react';
import * as Cesium from 'cesium';

/**
 * AnimationController - Storyboard Animation System
 * Orchestrates camera movements and overlay transitions for cinematic storyboards
 */
const AnimationController = ({ viewer, storyboard, onStepChange, onComplete }) => {
  const [currentStep, setCurrentStep] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const animationRef = useRef(null);

  useEffect(() => {
    if (!viewer || !storyboard || storyboard.steps.length === 0) return;

    if (isPlaying) {
      playStoryboard();
    }

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [viewer, storyboard, isPlaying, currentStep]);

  const playStoryboard = () => {
    if (!viewer || !storyboard) return;

    const steps = storyboard.steps;
    if (currentStep >= steps.length) {
      setIsPlaying(false);
      if (onComplete) onComplete();
      return;
    }

    const step = steps[currentStep];
    executeStep(step, () => {
      // Move to next step after duration
      setTimeout(() => {
        const nextStep = currentStep + 1;
        setCurrentStep(nextStep);
        if (onStepChange) onStepChange(nextStep, step);
        
        if (nextStep >= steps.length) {
          setIsPlaying(false);
          if (onComplete) onComplete();
        }
      }, step.duration || 3000);
    });
  };

  const executeStep = (step, onComplete) => {
    const { camera, overlays, narration } = step;

    // Animate camera
    if (camera) {
      animateCamera(viewer, camera, () => {
        // Dispatch narration event
        if (narration) {
          window.dispatchEvent(new CustomEvent('valora-narration-update', {
            detail: { text: narration, step: currentStep }
          }));
        }
        if (onComplete) onComplete();
      });
    } else {
      if (onComplete) onComplete();
    }
  };

  return null; // This component doesn't render DOM elements
};

/**
 * Animate camera to target position
 */
function animateCamera(viewer, cameraConfig, onComplete) {
  const { lat, lng, height = 1000, heading = 0, pitch = -45, duration = 2 } = cameraConfig;

  const destination = Cesium.Cartesian3.fromDegrees(lng, lat, height);

  viewer.camera.flyTo({
    destination: destination,
    orientation: {
      heading: Cesium.Math.toRadians(heading),
      pitch: Cesium.Math.toRadians(pitch),
      roll: 0.0
    },
    duration: duration,
    complete: onComplete
  });
}

/**
 * Storyboard Player Component (UI Controls)
 */
export const StoryboardPlayer = ({ storyboard, onPlay, onPause, onStop, onSeek, currentStep = 0, isPlaying = false }) => {
  if (!storyboard || !storyboard.steps || storyboard.steps.length === 0) {
    return null;
  }

  const totalSteps = storyboard.steps.length;
  const progress = ((currentStep + 1) / totalSteps) * 100;

  return (
    <div className="fixed bottom-20 left-1/2 transform -translate-x-1/2 bg-black/80 backdrop-blur-sm rounded-lg p-4 shadow-xl z-50">
      <div className="flex items-center gap-4">
        {/* Play/Pause Button */}
        <button
          onClick={isPlaying ? onPause : onPlay}
          className="bg-blue-500 hover:bg-blue-600 text-white rounded-full p-3 transition-colors"
        >
          {isPlaying ? (
            <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zM7 8a1 1 0 012 0v4a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v4a1 1 0 102 0V8a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
          ) : (
            <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clipRule="evenodd" />
            </svg>
          )}
        </button>

        {/* Stop Button */}
        <button
          onClick={onStop}
          className="bg-red-500 hover:bg-red-600 text-white rounded-full p-3 transition-colors"
        >
          <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8 7a1 1 0 00-1 1v4a1 1 0 001 1h4a1 1 0 001-1V8a1 1 0 00-1-1H8z" clipRule="evenodd" />
          </svg>
        </button>

        {/* Progress Bar */}
        <div className="flex-1 min-w-[200px]">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-white text-sm">Step {currentStep + 1} / {totalSteps}</span>
          </div>
          <div className="w-full bg-gray-700 rounded-full h-2">
            <div 
              className="bg-blue-500 h-2 rounded-full transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>

        {/* Step Navigation */}
        <div className="flex gap-2">
          <button
            onClick={() => onSeek(Math.max(0, currentStep - 1))}
            disabled={currentStep === 0}
            className="bg-gray-700 hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded p-2 transition-colors"
          >
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M12.707 5.293a1 1 0 010 1.414L9.414 10l3.293 3.293a1 1 0 01-1.414 1.414l-4-4a1 1 0 010-1.414l4-4a1 1 0 011.414 0z" clipRule="evenodd" />
            </svg>
          </button>
          <button
            onClick={() => onSeek(Math.min(totalSteps - 1, currentStep + 1))}
            disabled={currentStep === totalSteps - 1}
            className="bg-gray-700 hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded p-2 transition-colors"
          >
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clipRule="evenodd" />
            </svg>
          </button>
        </div>
      </div>

      {/* Current Step Info */}
      {storyboard.steps[currentStep] && (
        <div className="mt-3 text-white text-sm border-t border-gray-700 pt-3">
          <p className="font-medium">{storyboard.steps[currentStep].title || `Step ${currentStep + 1}`}</p>
          {storyboard.steps[currentStep].narration && (
            <p className="text-gray-300 mt-1">{storyboard.steps[currentStep].narration}</p>
          )}
        </div>
      )}
    </div>
  );
};

export default AnimationController;
