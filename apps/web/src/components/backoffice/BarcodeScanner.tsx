
import { useEffect, useRef, useState } from "react";
import { Html5Qrcode } from "html5-qrcode";

type BarcodeScannerProps = {
  onScan: (code: string) => void;
};

export default function BarcodeScanner({
  onScan,
}: BarcodeScannerProps) {
  const [cameraOpen, setCameraOpen] = useState(false);
  const [manualCode, setManualCode] = useState("");
  const [error, setError] = useState("");
  const scannerRef = useRef<Html5Qrcode | null>(null);
  const lastScanRef = useRef("");

  useEffect(() => {
    return () => {
      const scanner = scannerRef.current;

      if (scanner?.isScanning) {
        void scanner.stop().catch(() => {});
      }
    };
  }, []);

  async function startCamera() {
    setError("");

    try {
      const scanner = new Html5Qrcode("fashionos-barcode-reader");
      scannerRef.current = scanner;

      await scanner.start(
        { facingMode: "environment" },
        { fps: 10, qrbox: { width: 250, height: 180 } },
        (decodedText) => {
          if (decodedText !== lastScanRef.current) {
            lastScanRef.current = decodedText;
            onScan(decodedText);
          }
        },
        () => {}
      );

      setCameraOpen(true);
    } catch {
      setError(
        "Camera is not started. please cheak Camera permission aur HTTPS/localhost."
      );
    }
  }

  async function stopCamera() {
    const scanner = scannerRef.current;

    if (scanner?.isScanning) {
      try {
        await scanner.stop();
        await scanner.clear();
      } catch {
        // Scanner already stopped ho sakta hai.
      }
    }

    scannerRef.current = null;
    setCameraOpen(false);
  }

  function submitCode() {
    const code = manualCode.trim();

    if (!code) return;

    onScan(code);
    setManualCode("");
    lastScanRef.current = "";
  }

  return (
    <section className="rounded-xl border border-gray-200 bg-white p-5">
      <h2 className="text-lg font-semibold text-[#111111]">
        Scan Product Barcode
      </h2>

      <p className="mt-1 text-sm text-gray-500">
        Use camera or USB/Bluetooth barcode scanner .
      </p>

      <div className="mt-4 flex flex-wrap gap-3">
        {!cameraOpen ? (
          <button
            onClick={startCamera}
            className="min-h-11 rounded-lg bg-[#111111] px-4 py-2 text-sm text-white"
          >
            Open Camera
          </button>
        ) : (
          <button
            onClick={stopCamera}
            className="min-h-11 rounded-lg border border-gray-300 px-4 py-2 text-sm"
          >
            Stop Camera
          </button>
        )}
      </div>

      <div
        id="fashionos-barcode-reader"
        className="mt-4 w-full max-w-md overflow-hidden"
      />

      {error && (
        <p className="mt-3 text-sm text-red-600">{error}</p>
      )}

      <div className="mt-5 border-t border-gray-200 pt-4">
        <label
          htmlFor="barcode-input"
          className="mb-2 block text-sm font-medium"
        >
          USB / Bluetooth Scanner
        </label>

        <form
          onSubmit={(event) => {
            event.preventDefault();
            submitCode();
          }}
          className="flex flex-col gap-2 sm:flex-row"
        >
          <input
            id="barcode-input"
            autoComplete="off"
            autoFocus
            value={manualCode}
            onChange={(event) => setManualCode(event.target.value)}
            placeholder="Scan barcode here..."
            className="min-h-11 min-w-0 flex-1 rounded-lg border border-gray-300 px-3 text-sm outline-none focus:border-[#111111]"
          />

          <button
            type="submit"
            className="min-h-11 rounded-lg bg-[#111111] px-4 py-2 text-sm text-white"
          >
            Verify Code
          </button>
        </form>

        <p className="mt-2 text-xs text-gray-500">
            scan to keyboard mod
        </p>
      </div>
    </section>
  );
}
