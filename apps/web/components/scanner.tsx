"use client";

import jsQR from "jsqr";
import { Camera, CameraOff, RefreshCw } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { Alert, Button } from "@/components/ui";

export function QrScanner({ onResult }: { onResult: (value: string) => void }) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const rafRef = useRef<number | null>(null);
  const handlingRef = useRef(false);
  const [scanning, setScanning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [cameraSupported, setCameraSupported] = useState(true);

  const stop = useCallback(() => {
    if (rafRef.current !== null) {
      cancelAnimationFrame(rafRef.current);
      rafRef.current = null;
    }
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    setScanning(false);
  }, []);

  useEffect(() => {
    setCameraSupported(Boolean(navigator.mediaDevices?.getUserMedia));
    return () => stop();
  }, [stop]);

  const tick = useCallback(() => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas) return;
    if (video.readyState === video.HAVE_ENOUGH_DATA && video.videoWidth > 0) {
      const width = 480;
      const height = Math.round((video.videoHeight / video.videoWidth) * width);
      canvas.width = width;
      canvas.height = height;
      const context = canvas.getContext("2d", { willReadFrequently: true });
      if (context) {
        context.drawImage(video, 0, 0, width, height);
        const image = context.getImageData(0, 0, width, height);
        const code = jsQR(image.data, image.width, image.height, {
          inversionAttempts: "dontInvert",
        });
        if (code?.data && !handlingRef.current) {
          handlingRef.current = true;
          stop();
          onResult(code.data);
          return;
        }
      }
    }
    rafRef.current = requestAnimationFrame(tick);
  }, [onResult, stop]);

  async function start() {
    setError(null);
    if (!navigator.mediaDevices?.getUserMedia) {
      setCameraSupported(false);
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: "environment" }, width: { ideal: 1280 } },
        audio: false,
      });
      streamRef.current = stream;
      const video = videoRef.current;
      if (!video) return;
      video.srcObject = stream;
      await video.play();
      handlingRef.current = false;
      setScanning(true);
      rafRef.current = requestAnimationFrame(tick);
    } catch (caught) {
      const name = caught instanceof Error ? caught.name : "CameraError";
      if (name === "NotAllowedError" || name === "SecurityError") {
        setError("Camera permission was denied. Allow camera access in your browser settings, or use your phone's native camera on the classroom QR.");
      } else if (name === "NotFoundError" || name === "OverconstrainedError") {
        setError("No usable camera was found on this device. Use your phone's native camera on the classroom QR instead.");
      } else {
        setError("The camera could not be started. Close other apps using the camera and try again.");
      }
      setScanning(false);
    }
  }

  return (
    <div>
      <div className="relative overflow-hidden rounded-2xl border border-line bg-[#101828]">
        <video
          ref={videoRef}
          className={scanning ? "aspect-square w-full object-cover" : "hidden"}
          playsInline
          muted
          aria-label="Camera preview for QR scanning"
        />
        <canvas ref={canvasRef} className="hidden" />
        {!scanning ? (
          <div className="flex aspect-square w-full flex-col items-center justify-center gap-3 bg-[#101828] p-6 text-center text-white">
            <span className="flex h-14 w-14 items-center justify-center rounded-full bg-white/10">
              {cameraSupported ? <Camera size={26} /> : <CameraOff size={26} />}
            </span>
            <p className="text-sm font-semibold">
              {cameraSupported ? "Ready to scan the classroom QR" : "Camera scanning is unavailable"}
            </p>
            <p className="max-w-xs text-xs leading-relaxed text-[#C9DAFF]">
              {cameraSupported
                ? "Point the camera at the QR displayed on your teacher's screen. Nothing is uploaded until you continue the check-in."
                : "This browser does not expose a camera scanner. Use your phone's native camera to open the QR link instead."}
            </p>
          </div>
        ) : (
          <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
            <div className="relative h-56 w-56 rounded-2xl border-2 border-white/80">
              <span className="absolute -left-1 -top-1 h-6 w-6 rounded-tl-xl border-l-4 border-t-4 border-[#7FA9FF]" />
              <span className="absolute -right-1 -top-1 h-6 w-6 rounded-tr-xl border-r-4 border-t-4 border-[#7FA9FF]" />
              <span className="absolute -bottom-1 -left-1 h-6 w-6 rounded-bl-xl border-b-4 border-l-4 border-[#7FA9FF]" />
              <span className="absolute -bottom-1 -right-1 h-6 w-6 rounded-br-xl border-b-4 border-r-4 border-[#7FA9FF]" />
            </div>
          </div>
        )}
      </div>

      {error ? (
        <div className="mt-3">
          <Alert tone="warning">{error}</Alert>
        </div>
      ) : null}

      <div className="mt-3 flex gap-2">
        {scanning ? (
          <Button variant="secondary" className="flex-1" onClick={stop}>
            <CameraOff size={16} /> Stop camera
          </Button>
        ) : (
          <Button className="flex-1" onClick={() => void start()} disabled={!cameraSupported}>
            <Camera size={16} /> Start camera scanner
          </Button>
        )}
        {scanning ? (
          <Button variant="ghost" onClick={stop} aria-label="Reset scanner">
            <RefreshCw size={16} />
          </Button>
        ) : null}
      </div>
      <p className="mt-2 text-center text-[11px] leading-relaxed text-muted">
        Camera frames are processed only on this device using a QR decoder. They are never recorded
        or sent to the server.
      </p>
    </div>
  );
}
