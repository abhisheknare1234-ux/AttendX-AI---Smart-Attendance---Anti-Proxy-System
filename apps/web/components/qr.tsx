"use client";

import QRCode from "qrcode";
import { useEffect, useState } from "react";

export function QrSvg({
  value,
  size = 248,
  className,
}: {
  value: string | null | undefined;
  size?: number;
  className?: string;
}) {
  const [svg, setSvg] = useState<string>("");
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setError(false);
    if (!value) {
      setSvg("");
      return;
    }
    QRCode.toString(value, {
      type: "svg",
      margin: 1,
      width: size,
      errorCorrectionLevel: "M",
      color: { dark: "#202938", light: "#FFFFFF" },
    })
      .then((markup) => {
        if (!cancelled) setSvg(markup);
      })
      .catch(() => {
        if (!cancelled) setError(true);
      });
    return () => {
      cancelled = true;
    };
  }, [value, size]);

  if (!value || error) {
    return (
      <div
        className="flex items-center justify-center rounded-xl border border-dashed border-line bg-[#FAFBFD] text-center text-xs text-muted"
        style={{ width: size, height: size }}
      >
        {error ? "QR could not be generated" : "QR will appear when the session opens"}
      </div>
    );
  }

  if (!svg) {
    return (
      <div
        className="animate-pulse rounded-xl bg-[#EDF1F7]"
        style={{ width: size, height: size }}
        aria-label="Generating QR code"
      />
    );
  }

  return (
    <div
      className={className}
      style={{ width: size, height: size }}
      aria-label="Attendance QR code"
      dangerouslySetInnerHTML={{ __html: svg }}
    />
  );
}
