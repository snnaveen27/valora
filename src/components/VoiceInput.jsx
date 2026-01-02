import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Mic, MicOff, Volume2, VolumeX, Loader2, HelpCircle, X } from 'lucide-react';

const API_BASE = 'http://localhost:8000';

const VoiceInput = ({ onTranscript, onError, disabled = false }) => {
  const [isListening, setIsListening] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [interimTranscript, setInterimTranscript] = useState('');
  const [error, setError] = useState(null);
  const [showCommands, setShowCommands] = useState(false);
  const [voiceCommands, setVoiceCommands] = useState([]);
  const [audioLevel, setAudioLevel] = useState(0);
  const [ttsEnabled, setTtsEnabled] = useState(true);
  const [serviceStatus, setServiceStatus] = useState('unknown');

  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const streamRef = useRef(null);
  const analyserRef = useRef(null);
  const animationFrameRef = useRef(null);

  useEffect(() => {
    checkServiceHealth();
    fetchVoiceCommands();
    return () => {
      stopListening();
    };
  }, []);

  const checkServiceHealth = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/voice/health`);
      const data = await response.json();
      setServiceStatus(data.status);
    } catch (err) {
      setServiceStatus('error');
    }
  };

  const fetchVoiceCommands = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/voice/commands`);
      const data = await response.json();
      setVoiceCommands(data.commands || []);
    } catch (err) {
      console.error('Failed to fetch voice commands:', err);
    }
  };

  const startListening = async () => {
    if (disabled || serviceStatus !== 'healthy') {
      setError('Voice service not available');
      return;
    }

    try {
      setError(null);
      setTranscript('');
      setInterimTranscript('');
      audioChunksRef.current = [];

      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: 16000,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        }
      });

      streamRef.current = stream;

      const audioContext = new (window.AudioContext || window.webkitAudioContext)();
      const source = audioContext.createMediaStreamSource(stream);
      const analyser = audioContext.createAnalyser();
      analyser.fftSize = 256;
      source.connect(analyser);
      analyserRef.current = analyser;

      const updateAudioLevel = () => {
        if (!analyserRef.current) return;
        const dataArray = new Uint8Array(analyserRef.current.frequencyBinCount);
        analyserRef.current.getByteFrequencyData(dataArray);
        const average = dataArray.reduce((a, b) => a + b) / dataArray.length;
        setAudioLevel(average / 255);
        animationFrameRef.current = requestAnimationFrame(updateAudioLevel);
      };
      updateAudioLevel();

      const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : 'audio/webm';

      const mediaRecorder = new MediaRecorder(stream, {
        mimeType,
        audioBitsPerSecond: 128000
      });

      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        if (audioChunksRef.current.length > 0) {
          await processAudio();
        }
      };

      mediaRecorder.start(1000);
      setIsListening(true);

    } catch (err) {
      console.error('Microphone access error:', err);
      setError('Could not access microphone. Please grant permission.');
      onError?.(err);
    }
  };

  const stopListening = useCallback(() => {
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
    }

    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
    }

    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }

    setIsListening(false);
    setAudioLevel(0);
  }, []);

  const processAudio = async () => {
    setIsProcessing(true);

    try {
      const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
      
      const base64Audio = await new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onloadend = () => {
          const base64 = reader.result.split(',')[1];
          resolve(base64);
        };
        reader.onerror = reject;
        reader.readAsDataURL(audioBlob);
      });

      const response = await fetch(`${API_BASE}/api/voice/transcribe`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          audio_base64: base64Audio,
          content_type: 'audio/webm',
          language: 'en-IN'
        })
      });

      if (!response.ok) {
        throw new Error(`Transcription failed: ${response.status}`);
      }

      const data = await response.json();

      if (data.success && data.transcription?.transcript) {
        const text = data.transcription.transcript.trim();
        setTranscript(text);
        
        if (text) {
          onTranscript?.(text);
        }
      } else {
        setError('No speech detected. Please try again.');
      }

    } catch (err) {
      console.error('Audio processing error:', err);
      setError('Failed to process audio. Please try again.');
      onError?.(err);
    } finally {
      setIsProcessing(false);
      audioChunksRef.current = [];
    }
  };

  const speakText = async (text) => {
    if (!ttsEnabled || !text) return;

    try {
      const response = await fetch(`${API_BASE}/api/voice/tts`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          text,
          voice: 'aura-asteria-en',
          encoding: 'mp3'
        })
      });

      if (!response.ok) {
        throw new Error('TTS failed');
      }

      const data = await response.json();

      if (data.success && data.audio?.audio_base64) {
        const audioData = `data:audio/mp3;base64,${data.audio.audio_base64}`;
        const audio = new Audio(audioData);
        audio.play();
      }

    } catch (err) {
      console.error('TTS error:', err);
    }
  };

  const toggleListening = () => {
    if (isListening) {
      stopListening();
    } else {
      startListening();
    }
  };

  const getStatusColor = () => {
    switch (serviceStatus) {
      case 'healthy': return 'bg-green-500';
      case 'unconfigured': return 'bg-yellow-500';
      case 'error': return 'bg-red-500';
      default: return 'bg-gray-500';
    }
  };

  return (
    <div className="relative flex items-center gap-2">
      {/* Service Status Indicator */}
      <div 
        className={`w-2 h-2 rounded-full ${getStatusColor()}`}
        title={`Voice service: ${serviceStatus}`}
      />

      {/* Main Voice Button */}
      <button
        onClick={toggleListening}
        disabled={disabled || isProcessing || serviceStatus !== 'healthy'}
        className={`
          relative p-3 rounded-full transition-all duration-200
          ${isListening 
            ? 'bg-red-500 hover:bg-red-600 text-white animate-pulse' 
            : 'bg-indigo-500 hover:bg-indigo-600 text-white'}
          ${(disabled || serviceStatus !== 'healthy') ? 'opacity-50 cursor-not-allowed' : ''}
          ${isProcessing ? 'opacity-75' : ''}
        `}
        title={isListening ? 'Stop listening' : 'Start voice input'}
      >
        {isProcessing ? (
          <Loader2 className="w-5 h-5 animate-spin" />
        ) : isListening ? (
          <MicOff className="w-5 h-5" />
        ) : (
          <Mic className="w-5 h-5" />
        )}

        {/* Audio Level Indicator */}
        {isListening && (
          <div 
            className="absolute inset-0 rounded-full border-2 border-white opacity-50 animate-ping"
            style={{ 
              transform: `scale(${1 + audioLevel * 0.5})`,
              animationDuration: '1s'
            }}
          />
        )}
      </button>

      {/* TTS Toggle */}
      <button
        onClick={() => setTtsEnabled(!ttsEnabled)}
        className={`
          p-2 rounded-full transition-colors
          ${ttsEnabled 
            ? 'bg-indigo-100 text-indigo-600 hover:bg-indigo-200' 
            : 'bg-gray-100 text-gray-400 hover:bg-gray-200'}
        `}
        title={ttsEnabled ? 'Disable voice responses' : 'Enable voice responses'}
      >
        {ttsEnabled ? (
          <Volume2 className="w-4 h-4" />
        ) : (
          <VolumeX className="w-4 h-4" />
        )}
      </button>

      {/* Help Button */}
      <button
        onClick={() => setShowCommands(!showCommands)}
        className="p-2 rounded-full bg-gray-100 text-gray-500 hover:bg-gray-200 transition-colors"
        title="Voice commands help"
      >
        <HelpCircle className="w-4 h-4" />
      </button>

      {/* Status Text */}
      {(isListening || isProcessing || transcript || error) && (
        <div className="flex-1 min-w-0">
          {isListening && (
            <p className="text-sm text-red-500 animate-pulse truncate">
              🎤 Listening... Speak now
            </p>
          )}
          {isProcessing && (
            <p className="text-sm text-indigo-500 truncate">
              Processing audio...
            </p>
          )}
          {!isListening && !isProcessing && transcript && (
            <p className="text-sm text-green-600 truncate" title={transcript}>
              ✓ "{transcript}"
            </p>
          )}
          {error && (
            <p className="text-sm text-red-500 truncate">
              {error}
            </p>
          )}
        </div>
      )}

      {/* Voice Commands Modal */}
      {showCommands && (
        <div className="absolute bottom-full left-0 mb-2 w-80 max-h-96 overflow-y-auto bg-white rounded-lg shadow-xl border border-gray-200 z-50">
          <div className="sticky top-0 bg-white border-b border-gray-200 p-3 flex justify-between items-center">
            <h3 className="font-semibold text-gray-800">Voice Commands</h3>
            <button
              onClick={() => setShowCommands(false)}
              className="p-1 hover:bg-gray-100 rounded"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
          <div className="p-3 space-y-4">
            {voiceCommands.map((category, idx) => (
              <div key={idx}>
                <h4 className="text-xs font-semibold text-indigo-600 uppercase mb-2">
                  {category.category}
                </h4>
                <ul className="space-y-1">
                  {category.commands.map((cmd, cmdIdx) => (
                    <li key={cmdIdx} className="text-sm">
                      <span className="text-gray-700">{cmd.phrase}</span>
                      <span className="text-gray-400 text-xs block ml-2">
                        e.g., "{cmd.example}"
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
            {voiceCommands.length === 0 && (
              <p className="text-sm text-gray-500">Loading commands...</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export const useVoiceTTS = () => {
  const speak = async (text, voice = 'aura-asteria-en') => {
    try {
      const response = await fetch(`${API_BASE}/api/voice/tts`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          text,
          voice,
          encoding: 'mp3'
        })
      });

      if (!response.ok) return;

      const data = await response.json();

      if (data.success && data.audio?.audio_base64) {
        const audioData = `data:audio/mp3;base64,${data.audio.audio_base64}`;
        const audio = new Audio(audioData);
        await audio.play();
      }
    } catch (err) {
      console.error('TTS error:', err);
    }
  };

  return { speak };
};

export default VoiceInput;
